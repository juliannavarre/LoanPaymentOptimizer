import streamlit as st
import pandas as pd
import calendar
from datetime import datetime
from io import BytesIO
from pulp import LpProblem, LpVariable, lpSum, LpMinimize, LpBinary, PULP_CBC_CMD

st.markdown(
    """
    <h1 style='margin-bottom: 0.2em;'>📉 Loan Payment Optimizer</h1>
    <p style='font-size: 0.9rem; color: #31708f; background-color: #d9edf7; border: 1px solid #bce8f1; padding: 0.5em; border-radius: 4px;'>
        Enter your loan details and monthly budget to generate a personalized payment plan that minimizes interest and accelerates your debt-free date.
    </p>
    """,
    unsafe_allow_html=True
)

# Inputs
st.sidebar.subheader("Monthly Budget")
budget = st.sidebar.number_input("Enter Budget", min_value=0.0, value=0.0, step=10.0)
st.sidebar.subheader("Number of Loans")
num_loans = st.sidebar.selectbox("Choose # of Loans", list(range(1, 11)), index=0)

initial_balances = []
aprs = []
min_payments = []
deferment_months = []  # New: months of interest deferral per loan

for i in range(num_loans):
    with st.sidebar.expander(f"Loan #{i + 1}", expanded=True):
        bal = st.number_input(f"Balance₍{i + 1}₎", min_value=0.0, step=100.0, key=f"bal{i}")
        apr = st.number_input(f"APR₍{i + 1}₎ (%)", min_value=0.0, step=0.01, key=f"apr{i}")
        min_pay = st.number_input(f"Min Monthly Payment₍{i + 1}₎", min_value=0.0, step=1.0, value=0.0, key=f"minpay{i}")
        defer_months = st.number_input(
            f"Months Interest Deferred₍{i + 1}₎", min_value=0, max_value=240, value=0, step=1, key=f"defer_months_{i}"
        )
        initial_balances.append(bal)
        aprs.append(apr / 100)
        min_payments.append(min_pay)
        deferment_months.append(defer_months)

def all_loans_paid(B, month, num_loans):
    return all(
        B[(month, i)].value() is not None and B[(month, i)].value() < 0.01
        for i in range(num_loans)
    )

# Optimization
if st.sidebar.button("Run Optimization"):
    now = datetime.now()
    current_year = now.year
    current_month = now.month - 1  # zero-based for indexing into month_names
    month_names = list(calendar.month_name)[1:]  # 1→Jan ... 12→Dec

    T = 0
    max_months = 240

    model = LpProblem("Loan_Optimizer", LpMinimize)
    B = {}
    p = {}
    I = {}
    z = {}

    # initial balance constraints
    for i in range(num_loans):
        B[(0, i)] = LpVariable(f"B_0_{i}", lowBound=0)
        model += B[(0, i)] == initial_balances[i]

    # big M and epsilon for binary variable linking
    M = 1_000_000
    epsilon = 0.01

    # build model month by month
    while T < max_months:
        T += 1
        for i in range(num_loans):
            B[(T, i)] = LpVariable(f"B_{T}_{i}", lowBound=0)
            p[(T, i)] = LpVariable(f"p_{T}_{i}", lowBound=0)
            z[(T, i)] = LpVariable(f"z_{T}_{i}", cat=LpBinary)

            # Interest accrual depends on deferment period
            if T <= deferment_months[i]:
                I[(T, i)] = 0
            else:
                I[(T, i)] = (aprs[i] / 12) * B[(T - 1, i)]

            # Payment cannot exceed balance + interest
            model += p[(T, i)] <= B[(T - 1, i)] + I[(T, i)]
            # Balance update
            model += B[(T, i)] == B[(T - 1, i)] + I[(T, i)] - p[(T, i)]

            # Link binary z with balance to enforce min payment only if balance > epsilon
            model += B[(T - 1, i)] - epsilon >= -M * (1 - z[(T, i)])
            model += B[(T - 1, i)] - epsilon <= M * z[(T, i)]
            # Minimum payment if loan is active
            model += p[(T, i)] >= min_payments[i] * z[(T, i)]

        # Total payment can't exceed budget
        model += lpSum(p[(T, i)] for i in range(num_loans)) <= budget

        # Stop if all loans paid off
        if T > 1 and all_loans_paid(B, T - 1, num_loans):
            break

    # Objective: minimize total interest
    model += lpSum(I[(m, i)] for m in range(1, T + 1) for i in range(num_loans))
    model.solve(PULP_CBC_CMD(msg=0))

    # Payoff date calculation
    total_months = len([m for m in range(1, T + 1) if not all_loans_paid(B, m, num_loans)])
    payoff_index = current_month + total_months - 1
    payoff_year = current_year + payoff_index // 12
    payoff_month = month_names[payoff_index % 12]

    total_interest = sum((I[(m, i)] if isinstance(I[(m, i)], (int, float)) else I[(m, i)].value())
                         for m in range(1, total_months + 1) for i in range(num_loans))
    months_remaining = total_months

    st.markdown("---")
    col1, col2, col3 = st.columns([2, 3, 1])
    with col1:
        st.metric("Total Interest Accrued", f"${total_interest:,.2f}")
    with col2:
        st.metric("Payoff Date", f"{payoff_month}, {payoff_year}")
    with col3:
        st.metric("Months Remaining", f"{months_remaining}")

    # Build amortization table
    rows = []
    for m in range(1, total_months + 1):
        row = {}
        idx = current_month + m - 1
        row["Year"] = current_year + idx // 12
        row["Month"] = month_names[idx % 12]
        for i in range(num_loans):
            bal_prev = B[(m - 1, i)].value()
            interest = 0 if m <= deferment_months[i] else (aprs[i] / 12) * bal_prev
            pay = p[(m, i)].value()
            bal_post = B[(m, i)].value()
            row.update({
                f"Balance₍{i + 1}₎": round(bal_prev, 2),
                f"Interest₍{i + 1}₎": round(interest, 2),
                f"Pay₍{i + 1}₎": round(pay, 2),
                f"Remaining₍{i + 1}₎": round(bal_post, 2),
            })
        rows.append(row)

    df = pd.DataFrame(rows)
    money_cols = [c for c in df.columns if any(k in c for k in ["Balance", "Interest", "Pay", "Remaining"])]
    df_display = df.style.format({col: "${:,.2f}" for col in money_cols})

    st.subheader("📆 Full Payment Schedule (Until Paid Off)")
    st.dataframe(df_display, height=600, use_container_width=True)
    st.success(f"✅ Loans paid off in {months_remaining} months "
               f"({months_remaining // 12} years, {months_remaining % 12} months)")

    # Export to Excel
    towrite = BytesIO()
    df.to_excel(towrite, index=False, sheet_name="Amortization")
    towrite.seek(0)
    st.download_button(
        label="📥 Download Schedule as Excel",
        data=towrite,
        file_name="loan_schedule.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
