import streamlit as st
import pandas as pd
import plotly.express as px
import re
from logic.parsers import categorize_transaction

def render_metrics(df):
    """Calculates and displays KPIs for the SPECIFIC data passed to it."""
    
    df = df[df['amount'].abs() != df['balance'].abs()].copy()
    
    df = df.drop_duplicates(subset=['date', 'description', 'amount', 'balance'])
    
    # Apply logic
    df['category'] = df.apply(lambda x: categorize_transaction(x['description'], x['amount']), axis=1)
    
    # Filter out "Reversals" and "Transfers" from real performance metrics
    # Update your metrics logic to filter out internal account transfers
    real_income_df = df[
       (df['category'] == 'Monthly Income') & 
       (~df['description'].str.contains('Transfer from', case=False))
    ]
    total_income = real_income_df['amount'].sum()
    
    excluded_categories = ['Internal Transfer', 'Credit Card Payment', 'Payment Reversal', 'Savings Transfer']
    
    real_expenses = df[
        (df['amount'] < 0) & 
        (~df['category'].isin(excluded_categories))
    ]['amount'].sum()
    
    # This is what is actually left in your pocket after cost of living
    net_surplus = total_income + real_expenses

    # 4. DISPLAY THE REFLECTION
    st.markdown(f"### 💳 Monthly Money Reflection")
    c1, c2, c3 = st.columns(3)
    
    c1.metric("Total Income", f"R {total_income:,.2f}")
    
    c2.metric("Real Expenses", f"R {abs(real_expenses):,.2f}", 
              help="Excludes Credit Card payments and transfers to avoid double-counting.")
    
    # Net Savings
    c3.metric("Net Savings", f"R {net_surplus:,.2f}", 
              delta=f"{((net_surplus/total_income)*100 if total_income > 0 else 0):.1f}% of income")
    
    return df

def render_charts(df):
    """Visualizing the spend with high efficiency for SA users."""
    # Data is grouped to be lightweight for rendering
    c1, c2 = st.columns(2)
    
    with c1:
        st.write("#### 🍰 Expense Breakdown")
        expenses = df[df['amount'] < 0].copy()
        expenses['amount'] = expenses['amount'].abs()
        cat_data = expenses.groupby("category")["amount"].sum().reset_index()
        fig = px.pie(cat_data, values='amount', names='category', hole=0.4,
                     color_discrete_sequence=px.colors.qualitative.Bold)
        st.plotly_chart(fig, use_container_width=True)
    
    with c2:
        st.write("#### 📊 Daily Cash Flow")
        # Separate Income and Expense bars to clearly see your Salary deposits
        df['Type'] = df['amount'].apply(lambda x: 'Income' if x > 0 else 'Expense')
        daily_flow = df.groupby([df['date'].dt.date, 'Type'])['amount'].sum().abs().reset_index()
        
        fig_bar = px.bar(daily_flow, x='date', y='amount', color='Type',
                         barmode='group',
                         color_discrete_map={'Income': '#2ecc71', 'Expense': '#e74c3c'})
        st.plotly_chart(fig_bar, use_container_width=True)

def render_monthly_view(df):
    """Dynamic Month-by-Month Analysis"""
    df['date'] = pd.to_datetime(df['date'])
    df['Month'] = df['date'].dt.strftime('%B %Y')
    
    st.markdown("### 📅 Select Month to Analyze")
    month_list = df['Month'].unique()
    selected_month = st.selectbox("Focus on:", month_list)
    
    monthly_df = df[df['Month'] == selected_month]
    
    # Monthly Breakdown Chart
    st.write(f"#### Where your money went in {selected_month}")
    chart_data = monthly_df[monthly_df['amount'] < 0].groupby('category')['amount'].sum().abs().reset_index()
    fig = px.bar(chart_data, x='category', y='amount', color='category', text_auto='.2s')
    st.plotly_chart(fig, use_container_width=True)
    
    return monthly_df