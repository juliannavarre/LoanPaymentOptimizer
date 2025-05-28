Loan Payment Optimizer
======================
https://loanoptimizer-jnavarre.streamlit.app/

Description:
------------
This app helps you create a personalized loan payment plan based on your loan details and monthly budget.
It optimizes payments to minimize total interest and accelerate your debt-free date.

Features:
---------
- Supports multiple loans (up to 10).
- Input loan balances, APRs, minimum payments, and interest deferment periods.
- Monthly budget constraint to fit your financial plan.
- Calculates optimized monthly payments using linear programming.
- Displays a full amortization schedule until all loans are paid off.
- Shows key metrics: total interest accrued, payoff date, and months remaining.
- Download the payment schedule as an Excel file.

How to Use:
-----------
1. Enter your monthly budget in the sidebar.
2. Select the number of loans.
3. For each loan, input:
   - Current balance
   - APR (annual percentage rate)
   - Minimum monthly payment
   - Months interest is deferred (if applicable)
4. Click "Run Optimization" to generate your payment plan.
5. Review the results and download the amortization schedule if desired.

Requirements:
-------------
- Python 
- Streamlit
- pandas
- pulp


Author:
-------
[Julian Navarre juliannavarre@gmail.com]
