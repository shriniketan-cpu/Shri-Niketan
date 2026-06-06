import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(layout="wide", page_title="Fulfillment Dashboard")
st.title("🎯 Customer Target & Fulfillment Dashboard")

# -----------------------------------------
# NO-KEY GOOGLE SHEETS CONNECTION (POSITION BASED)
# -----------------------------------------
SHEET_ID = "PASTE_YOUR_LONG_SHEET_ID_HERE"
base_url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=xlsx"

@st.cache_data(ttl=300)
def load_data():
    # Read the workbook file structure first
    excel_file = pd.ExcelFile(base_url)
    
    # Print the tabs we found onto the Streamlit screen to debug live
    st.sidebar.write("🔍 Tabs found in your sheet:", excel_file.sheet_names)
    
    # CHANGE THIS NUMBER: 0 means 1st tab, 1 means 2nd tab, 2 means 3rd tab from the left
    TARGET_TAB_POSITION = 0 
    
    return pd.read_excel(base_url, sheet_name=TARGET_TAB_POSITION)

try:
    df = load_data()
    
    # Clean up column names automatically by stripping hidden spaces from your headers
    df.columns = df.columns.str.strip()
    
except Exception as e:
    st.error(f"❌ Connection Error: {e}")
    st.info("💡 Troubleshooting: Check if your Sheet ID is correct and 'Anyone with the link' is active.")
    st.stop()

# -----------------------------------------
# SIDEBAR FILTERS
# -----------------------------------------
st.sidebar.header("Dashboard Filters")

months = ["All"] + list(df["Month"].unique())
selected_month = st.sidebar.selectbox("Filter by Month", months)

categories = ["All"] + list(df["Category"].unique())
selected_category = st.sidebar.selectbox("Filter by Product Category", categories)

types = ["All"] + list(df["Type"].unique())
selected_type = st.sidebar.selectbox("Customer Type Filter", types)

# Apply filters
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

total_target = int(filtered_df["Promise Qty"].sum())
planned_achieved = int(filtered_df["Planned Customer Qty Achieved"].sum())
unplanned_achieved = int(filtered_df["Unplanned Customer Qty Achieved"].sum())
total_balance_lapse = int(filtered_df[filtered_df["Type"] == "Promise Customer"]["Balance Qty"].sum())

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
    promise_df = filtered_df[filtered_df["Promise Qty"] > 0]
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
