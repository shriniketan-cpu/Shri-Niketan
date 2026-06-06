import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(layout="wide", page_title="Fulfillment Dashboard")
st.title("🎯 Customer Target & Fulfillment Dashboard")

# -----------------------------------------
# NO-KEY GOOGLE SHEETS CONNECTION (FIRST POSITION)
# -----------------------------------------
# 1. Ensure your Sheet ID is pasted perfectly here:
SHEET_ID = "https://docs.google.com/spreadsheets/d/15jP3vpX1cgH84UxmOU55clAU2BEk55hu9UhHHJDT4qk/edit?gid=837089170#gid=837089170"

# 2. Requesting the spreadsheet file directly
base_url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=xlsx"

@st.cache_data(ttl=300) # Refreshes every 5 minutes
def load_data():
    # sheet_name=0 explicitly commands Pandas to pull the leftmost tab
    data = pd.read_excel(base_url, sheet_name=0)
    
    # Data Cleaning: Strip hidden trailing spaces from header column names
    data.columns = data.columns.str.strip()
    
    # Data Cleaning: Strip spaces from text columns to make filters reliable
    text_cols = ["Customer Name", "Category", "Month", "Status", "Type"]
    for col in text_cols:
        if col in data.columns:
            data[col] = data[col].astype(str).str.strip()
            
    return data

try:
    df = load_data()
except Exception as e:
    st.error(f"❌ Could not retrieve data from the 1st sheet tab. Error details: {e}")
    st.info("💡 Quick Check: Double check that your Google Sheet access is set to 'Anyone with the link can view' and click 'Done'.")
    st.stop()

# -----------------------------------------
# SIDEBAR FILTERS
# -----------------------------------------
st.sidebar.header("Dashboard Filters")

months = ["All"] + sorted(list(df["Month"].unique()))
selected_month = st.sidebar.selectbox("Filter by Month", months)

categories = ["All"] + list(df["Category"].unique())
selected_category = st.sidebar.selectbox("Filter by Product Category", categories)

types = ["All"] + list(df["Type"].unique())
selected_type = st.sidebar.selectbox("Customer Type Filter", types)

# Apply filter selections
filtered_df = df.copy()
if selected_month != "All":
    filtered_df = filtered_df[filtered_df["Month"] == selected_month]
if selected_category != "All":
    filtered_df = filtered_df[filtered_df["Category"] == selected_category]
if selected_type != "All":
    filtered_df = filtered_df[filtered_df["Type"] == selected_type]

# -----------------------------------------
# CORE KPI METRICS
# -----------------------------------------
st.subheader("📋 Performance Overview")
kpi1, kpi2, kpi3, kpi4 = st.columns(4)

# Force metrics to numeric types to prevent rendering errors
total_target = int(pd.to_numeric(filtered_df["Promise Qty"], errors='coerce').sum())
planned_achieved = int(pd.to_numeric(filtered_df["Planned Customer Qty Achieved"], errors='coerce').sum())
unplanned_achieved = int(pd.to_numeric(filtered_df["Unplanned Customer Qty Achieved"], errors='coerce').sum())

# Calculate strict target deficit balance
promise_mask = filtered_df["Type"] == "Promise Customer"
total_balance_lapse = int(pd.to_numeric(filtered_df[promise_mask]["Balance Qty"], errors='coerce').sum())

target_clearance_rate = (planned_achieved / total_target * 100) if total_target > 0 else 100.0

with kpi1:
    st.metric("Total Promised Target Qty", f"{total_target} units")
with kpi2:
    st.metric("Planned Qty Achieved", f"{planned_achieved} units", f"Clearance: {target_clearance_rate:.1f}%")
with kpi3:
    st.metric("Target Deficit Balance", f"{total_balance_lapse} units", delta=f"-{total_balance_lapse}", delta_color="inverse")
with kpi4:
    st.metric("Organic Unplanned Sales", f"{unplanned_achieved} units")

st.markdown("---")

# -----------------------------------------
# VISUAL CHARTS
# -----------------------------------------
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("Target vs Planned Achievement per Client")
    promise_df = filtered_df[pd.to_numeric(filtered_df["Promise Qty"], errors='coerce') > 0]
    
    if not promise_df.empty:
        df_melted = promise_df.melt(
            id_vars=["Customer Name"], 
            value_vars=["Promise Qty", "Planned Customer Qty Achieved"],
            var_name="Metric", value_name="Units"
        )
        fig_targets = px.bar(
            df_melted, x="Customer Name", y="Units", color="Metric",
            barmode="group", color_discrete_sequence=["#3182ce", "#319795"]
        )
        st.plotly_chart(fig_targets, use_container_width=True)
    else:
        st.info("No active promise target customers found within the current filter scope.")

with col_right:
    st.subheader("Account Allocation Status Mix")
    status_counts = filtered_df["Status"].value_counts().reset_index()
    status_counts.columns = ["Fulfillment Status", "Count"]
    fig_status = px.pie(
        status_counts, names="Fulfillment Status", values="Count",
        hole=0.4, color_discrete_sequence=px.colors.qualitative.Safe
    )
    st.plotly_chart(fig_status, use_container_width=True)

# -----------------------------------------
# RAW DATA LEDGER
# -----------------------------------------
st.subheader("🔍 Detailed Target Ledger")
st.dataframe(filtered_df, use_container_width=True)
