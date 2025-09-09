import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta
from typing import List, Union

# Set page config
st.set_page_config(
    page_title="💰 Loan Timing Analyzer",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded"
)

def compute_loan_repayment_schedule(
    payment_dates: List[Union[str, datetime]],
    annual_interest_rate: float,
    loan_amount: float
) -> pd.DataFrame:
    """
    Compute a loan repayment schedule with equal payment amounts.
    """
    # Convert string dates to datetime objects if necessary
    dates = []
    for date in payment_dates:
        if isinstance(date, str):
            dates.append(datetime.strptime(date, '%Y-%m-%d'))
        else:
            dates.append(date)
    
    # Sort dates to ensure chronological order
    dates.sort()
    
    if len(dates) < 2:
        raise ValueError("At least 2 payment dates are required")
    
    # Calculate the fixed payment amount using the present value of annuity formula
    pv_factors = []
    cumulative_days = 0
    
    for i in range(1, len(dates)):
        days_between = (dates[i] - dates[i-1]).days
        cumulative_days += days_between
        # Calculate present value factor
        pv_factor = 1 / ((1 + annual_interest_rate) ** (cumulative_days / 365.25))
        pv_factors.append(pv_factor)    # Calculate fixed payment amount
    total_pv_factor = sum(pv_factors)
    payment_amount = loan_amount / total_pv_factor
    
    # Build the repayment schedule
    schedule = []
    remaining_balance = loan_amount
    previous_date = None
    
    for i, current_date in enumerate(dates):
        if i == 0:
            # First entry - loan origination
            schedule.append({
                'payment_date': current_date,
                'days_between': 0,
                'interest_rate': annual_interest_rate,
                'interest_charge': 0.0,
                'principal_payment': 0.0,
                'payment_amount': 0.0,
                'remaining_balance': remaining_balance
            })
            previous_date = current_date
            continue
        
        # Calculate days between payments
        days_between = (current_date - previous_date).days
        
        # Calculate interest charge for this period
        period_interest_rate = (1 + annual_interest_rate) ** (days_between / 365.25) - 1
        interest_charge = remaining_balance * period_interest_rate
        
        # Calculate principal payment
        principal_payment = payment_amount - interest_charge
        
        # Update remaining balance
        remaining_balance -= principal_payment
        
        # Handle final payment (adjust for rounding)
        if i == len(dates) - 1:
            principal_payment += remaining_balance
            payment_amount = interest_charge + principal_payment
            remaining_balance = 0.0
        
        schedule.append({
            'payment_date': current_date,
            'days_between': days_between,
            'interest_rate': period_interest_rate,
            'interest_charge': interest_charge,
            'principal_payment': principal_payment,
            'payment_amount': payment_amount,
            'remaining_balance': remaining_balance
        })
        
        previous_date = current_date
    
    return pd.DataFrame(schedule)

def calculate_loan_scenarios(loan_amount, annual_rate, num_periods, days_to_salary, salary_day=25):
    """
    Calculate loan scenarios based on user inputs
    """
    # Calculate today's date
    today = datetime.now().date()
    
    # Calculate the next salary date based on days_to_salary
    next_salary_date = today + timedelta(days=days_to_salary)
    
    # Scenario 1: Start payments on the calculated salary date
    scenario1_dates = [today.strftime('%Y-%m-%d')]
    current_payment_date = next_salary_date
    
    for i in range(num_periods):
        scenario1_dates.append(current_payment_date.strftime('%Y-%m-%d'))
        # Add one month for next payment
        if current_payment_date.month == 12:
            current_payment_date = current_payment_date.replace(
                year=current_payment_date.year + 1, 
                month=1
            )
        else:
            current_payment_date = current_payment_date.replace(
                month=current_payment_date.month + 1
            )
    
    # Scenario 2: Start payments one month later than scenario 1
    scenario2_dates = [today.strftime('%Y-%m-%d')]
    if next_salary_date.month == 12:
        delayed_start = next_salary_date.replace(year=next_salary_date.year + 1, month=1)
    else:
        delayed_start = next_salary_date.replace(month=next_salary_date.month + 1)
    
    current_payment_date = delayed_start
    for i in range(num_periods):
        scenario2_dates.append(current_payment_date.strftime('%Y-%m-%d'))
        if current_payment_date.month == 12:
            current_payment_date = current_payment_date.replace(
                year=current_payment_date.year + 1, 
                month=1
            )
        else:
            current_payment_date = current_payment_date.replace(
                month=current_payment_date.month + 1
            )
    
    # Calculate schedules
    schedule1 = compute_loan_repayment_schedule(scenario1_dates, annual_rate, loan_amount)
    schedule2 = compute_loan_repayment_schedule(scenario2_dates, annual_rate, loan_amount)
    
    return schedule1, schedule2

def create_payment_visualization(schedule1, schedule2):
    """
    Create visualizations for the payment schedules
    """
    # Prepare data for visualization
    schedule1_viz = schedule1[schedule1['payment_amount'] > 0].copy()
    schedule2_viz = schedule2[schedule2['payment_amount'] > 0].copy()
    
    # Add payment numbers and scenario labels
    schedule1_viz['payment_number'] = range(1, len(schedule1_viz) + 1)
    schedule2_viz['payment_number'] = range(1, len(schedule2_viz) + 1)
    schedule1_viz['scenario'] = 'Start Next Salary Date'
    schedule2_viz['scenario'] = 'Start Month Later'
    
    combined_data = pd.concat([schedule1_viz, schedule2_viz], ignore_index=True)
    
    # Create payment amount comparison chart
    fig_payments = px.bar(
        combined_data,
        x='payment_number',
        y='payment_amount',
        color='scenario',
        title='📊 Payment Amounts by Scenario',
        labels={
            'payment_number': 'Payment Number',
            'payment_amount': 'Payment Amount (R)',
            'scenario': 'Scenario'
        },
        color_discrete_map={
            'Start Next Salary Date': '#2E86AB',
            'Start Month Later': '#A23B72'
        },
        barmode='group'  # This makes bars appear side by side instead of stacked
    )
    fig_payments.update_layout(height=400)
    
    # Create interest vs principal breakdown
    fig_breakdown = go.Figure()
    
    # Scenario 1 data
    fig_breakdown.add_trace(go.Bar(
        name='Interest (Next Salary)',
        x=schedule1_viz['payment_number'],
        y=schedule1_viz['interest_charge'],
        marker_color='#FF6B6B'
    ))
    
    fig_breakdown.add_trace(go.Bar(
        name='Principal (Next Salary)',
        x=schedule1_viz['payment_number'],
        y=schedule1_viz['principal_payment'],
        marker_color='#4ECDC4'
    ))
    
    # Scenario 2 data  
    fig_breakdown.add_trace(go.Bar(
        name='Interest (Month Later)',
        x=schedule2_viz['payment_number'],
        y=schedule2_viz['interest_charge'],
        marker_color='#FFE66D',
        opacity=0.7
    ))
    
    fig_breakdown.add_trace(go.Bar(
        name='Principal (Month Later)',
        x=schedule2_viz['payment_number'],
        y=schedule2_viz['principal_payment'],
        marker_color='#95E1D3',
        opacity=0.7
    ))
    
    fig_breakdown.update_layout(
        title='💸 Interest vs Principal Breakdown',
        xaxis_title='Payment Number',
        yaxis_title='Amount (R)',
        barmode='stack',
        height=400
    )
    
    # Create remaining balance chart
    fig_balance = go.Figure()
    
    fig_balance.add_trace(go.Scatter(
        x=schedule1['payment_date'],
        y=schedule1['remaining_balance'],
        mode='lines+markers',
        name='Next Salary Date',
        line=dict(color='#2E86AB', width=3),
        marker=dict(size=8)
    ))
    
    fig_balance.add_trace(go.Scatter(
        x=schedule2['payment_date'],
        y=schedule2['remaining_balance'],
        mode='lines+markers',
        name='Month Later',
        line=dict(color='#A23B72', width=3, dash='dash'),
        marker=dict(size=8)
    ))
    
    fig_balance.update_layout(
        title='📈 Remaining Loan Balance Over Time',
        xaxis_title='Date',
        yaxis_title='Remaining Balance (R)',
        height=400
    )
    
    return fig_payments, fig_breakdown, fig_balance

# Streamlit App
def main():
    st.title("💰 Loan Timing Analyzer")
    st.markdown("### 🏦 Compare loan repayment scenarios based on timing")
    
    # Sidebar for inputs
    st.sidebar.header("📝 Loan Parameters")
    
    loan_amount = st.sidebar.number_input(
        "💵 Loan Amount (R)",
        min_value=1000,
        max_value=1000000,
        value=100000,
        step=5000,
        help="Enter the total loan amount"
    )
    
    annual_rate = st.sidebar.slider(
        "📈 Annual Interest Rate (%)",
        min_value=1.0,
        max_value=30.0,
        value=10.0,
        step=0.5,
        help="Enter the annual interest rate as a percentage"
    ) / 100.0
    
    num_periods = st.sidebar.selectbox(
        "📅 Number of Payment Periods",
        options=[1, 2, 3, 4, 5, 6, 9, 12],
        index=2,
        help="Select the number of monthly payments"
    )
    
    days_to_salary = st.sidebar.slider(
        "⏰ Days to Next Salary Date",
        min_value=1,
        max_value=30,
        value=16,
        help="Number of days until your next salary/payment date"
    )
    
    salary_day = st.sidebar.selectbox(
        "💳 Salary Day of Month",
        options=list(range(1, 29)),
        index=24,  # 25th day
        help="What day of the month do you receive your salary?"
    ) + 1
    
    # Calculate scenarios automatically (reactive)
    try:
        with st.spinner("Calculating loan scenarios..."):
            schedule1, schedule2 = calculate_loan_scenarios(
                loan_amount, annual_rate, num_periods, days_to_salary, salary_day
            )
            
            # Store in session state
            st.session_state.schedule1 = schedule1
            st.session_state.schedule2 = schedule2
            st.session_state.calculated = True
            
    except Exception as e:
        st.error(f"Error calculating scenarios: {str(e)}")
        st.session_state.calculated = False
    
    # Display results if calculated successfully
    if hasattr(st.session_state, 'calculated') and st.session_state.calculated:
        schedule1 = st.session_state.schedule1
        schedule2 = st.session_state.schedule2
        
        # Calculate totals
        total1 = schedule1['payment_amount'].sum()
        total_interest1 = schedule1['interest_charge'].sum()
        total2 = schedule2['payment_amount'].sum()
        total_interest2 = schedule2['interest_charge'].sum()
        
        # Display key metrics
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(
                "💰 Loan Amount",
                f"R{loan_amount:,.2f}",
                help="Original loan amount"
            )
        
        with col2:
            savings = abs(total_interest2 - total_interest1)
            st.metric(
                "💸 Interest Savings",
                f"R{savings:,.2f}",
                f"{(savings/total_interest2)*100:.1f}% less interest" if total_interest1 < total_interest2 else f"{(savings/total_interest1)*100:.1f}% more interest",
                delta_color="normal" if total_interest1 < total_interest2 else "inverse"
            )
        
        with col3:
            recommendation = "Start Next Salary Date" if total_interest1 < total_interest2 else "Start Month Later"
            st.metric(
                "🎯 Recommendation",
                recommendation,
                help="Best scenario based on total interest cost"
            )
        
        # Comparison table
        st.subheader("📊 Scenario Comparison")
        
        comparison_data = {
            "Metric": [
                "Total Amount Paid",
                "Total Interest",
                "Monthly Payment",
                "First Payment Date"
            ],
            "Start Next Salary Date": [
                f"R{total1:,.2f}",
                f"R{total_interest1:,.2f}",
                f"R{schedule1[schedule1['payment_amount'] > 0]['payment_amount'].iloc[0]:,.2f}",
                schedule1[schedule1['payment_amount'] > 0]['payment_date'].iloc[0].strftime('%Y-%m-%d')
            ],
            "Start Month Later": [
                f"R{total2:,.2f}",
                f"R{total_interest2:,.2f}",
                f"R{schedule2[schedule2['payment_amount'] > 0]['payment_amount'].iloc[0]:,.2f}",
                schedule2[schedule2['payment_amount'] > 0]['payment_date'].iloc[0].strftime('%Y-%m-%d')
            ]
        }
        
        comparison_df = pd.DataFrame(comparison_data)
        st.dataframe(comparison_df, use_container_width=True)
        
        # Visualizations
        st.subheader("📈 Visual Analysis")
        
        fig_payments, fig_breakdown, fig_balance = create_payment_visualization(schedule1, schedule2)
        
        tab1, tab2, tab3 = st.tabs(["💳 Payment Comparison", "📊 Interest vs Principal", "📈 Balance Over Time"])
        
        with tab1:
            st.plotly_chart(fig_payments, use_container_width=True)
            
        with tab2:
            st.plotly_chart(fig_breakdown, use_container_width=True)
            
        with tab3:
            st.plotly_chart(fig_balance, use_container_width=True)
        
        # Detailed schedules
        with st.expander("📋 Detailed Payment Schedules"):
            col1, col2 = st.columns(2)
            
            with col1:
                st.subheader("🟢 Start Next Salary Date")
                display_schedule1 = schedule1.copy()
                display_schedule1['payment_date'] = display_schedule1['payment_date'].dt.strftime('%Y-%m-%d')
                display_schedule1 = display_schedule1.round(2)
                st.dataframe(display_schedule1, use_container_width=True)
            
            with col2:
                st.subheader("🔴 Start Month Later")
                display_schedule2 = schedule2.copy()
                display_schedule2['payment_date'] = display_schedule2['payment_date'].dt.strftime('%Y-%m-%d')
                display_schedule2 = display_schedule2.round(2)
                st.dataframe(display_schedule2, use_container_width=True)
        
        # Key insights
        st.subheader("💡 Key Insights")
        
        if total_interest1 < total_interest2:
            st.success(f"✅ Starting payments on your next salary date saves you R{savings:,.2f} in interest!")
        else:
            st.warning(f"⚠️ Starting payments next month costs an additional R{savings:,.2f} in interest.")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.info(f"📅 **Timing Impact**: {days_to_salary} days to salary date")
            if days_to_salary > 14:
                st.success("🟢 Early application - maximize savings by starting immediately")
            else:
                st.warning("🟡 Late application - savings are smaller but still beneficial")
        
        with col2:
            interest_percentage = (total_interest1 / loan_amount) * 100
            st.info(f"📊 **Total Interest**: {interest_percentage:.2f}% of loan amount")
            if interest_percentage < 5:
                st.success("🟢 Low total interest cost")
            elif interest_percentage < 10:
                st.warning("🟡 Moderate total interest cost") 
            else:
                st.error("🔴 High total interest cost")
    
    else:
        # Instructions for first-time users or when there's an error
        st.info("👈 **Adjust your loan parameters in the sidebar to see the analysis**")
        
        st.markdown("""
        ### 🚀 How to use this app:
        
        1. **📝 Set Parameters**: Use the sidebar to input your loan details
        2. **� Auto-Calculate**: The analysis updates automatically as you change inputs
        3. **📈 Visualize**: Explore interactive charts showing the differences
        4. **💡 Decide**: Use the insights to make the best timing decision
        
        ### 🎯 Key Benefits:
        - **Real-time calculations** that update as you type
        - **Accurate calculations** using compound interest
        - **Visual comparisons** to understand the impact
        - **Clear recommendations** based on your specific situation
        - **Detailed breakdowns** of interest vs principal payments
        """)

if __name__ == "__main__":
    main()
