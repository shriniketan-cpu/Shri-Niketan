import streamlit as st
import pandas as pd
import plotly.express as px

st.set_page_config(layout="wide", page_title="Fulfillment Dashboard")
st.title("🎯 Customer Target & Fulfillment Dashboard")

# -----------------------------------------
# NO-KEY GOOGLE SHEETS CONNECTION (FIRST POSITION)
# -----------------------------------------
# 1. Ensure your Sheet ID is pasted perfectly here:
SHEET_ID = "15jP3vpX1cgH84UxmOU55clAU2BEk55hu9UhHHJDT4qk"

# 2. Requesting the spreadsheet file directly as an Excel workbook
base_url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=xlsx"

@st.cache_data(ttl=300) # Refreshes and grabs fresh data every 5 minutes
def load_data():
    # sheet_name=0 explicitly commands Pandas to pull the leftmost tab
    data = pd.read_excel(base_url, sheet_name=0)
    
    # Data Cleaning: Strip hidden trailing spaces from header column names
    data.columns = data.columns.str.strip()
    return data

try:
    df = load_data()
except Exception as e:
    st.error(f"❌ Could not retrieve data from the 1st sheet tab. Error details: {e}")
    st.info("💡 Quick Check: Double check that your Google Sheet access is set to 'Anyone with the link can view' and click 'Done'.")
    st.stop()

# -----------------------------------------
# AUTODETECT COLUMNS (Fixes KeyErrors dynamically)
# -----------------------------------------
# Map column names to lowercase to bypass capitalization mismatches
col_map = {col.lower(): col for col in df.columns}

# Identify key columns by matching lowercase variants or falling back to positional order
name_col = col_map.get("customer name", df.columns[0])
category_col = col_map.get("category", df.columns[1] if len(df.columns) > 1 else df.columns[0])
month_col = col_map.get("month", df.columns[2] if len(df.columns) > 2 else df.columns[0])

promise_col = col_map.get("promise qty", "Promise Qty")
planned_col = col_map.get("planned customer qty achieved", "Planned Customer Qty Achieved")
unplanned_col = col_map.get("unplanned customer qty achieved", "Unplanned Customer Qty Achieved")
total_achieved_col = col_map.get("total achieved qty", "Total Achieved Qty")
balance_col = col_map.get("balance qty", "Balance Qty")
status_col = col_map.get("status", "Status")
type_col = col_map.get("type", "Type")

# Clean text variables dynamically to ensure sidebar filters match data clean-cut
text_cols_to_clean = [name_col, category_col, month_col, status_col, type_col]
for col in text_cols_to_clean:
    if col in df.columns:
        df[col] = df[col].astype(str).str.strip()

# -----------------------------------------
# SIDEBAR FILTERS
# -----------------------------------------
st.sidebar.header("Dashboard Filters")

# Filter by Month
if month_col in df.columns:
    months = ["All"] + sorted(list(df[month_col].dropna().unique()))
    selected_month = st.sidebar.selectbox("Filter by Month", months)
else:
    selected_month = "All"

# Filter by Category
if category_col in df.columns:
    categories = ["All"] + list(df[category_col].dropna().unique())
    selected_category = st.sidebar.selectbox("Filter by Product Category", categories)
else:
    selected_category = "All"

# Filter by Type
if type_col in df.columns:
    types = ["All"] + list(df[type_col].dropna().unique())
    selected_type = st.sidebar.selectbox("Customer Type Filter", types)
else:
    selected_type = "All"

# Apply filter selections
filtered_df = df.copy()
if selected_month != "All":
    filtered_df = filtered_df[filtered_df[month_col] == selected_month]
if selected_category != "All":
    filtered_df = filtered_df[filtered_df[category_col] == selected_category]
if selected_type != "All":
    filtered_df = filtered_df[filtered_df[type_col] == selected_type]

# -----------------------------------------
# CORE KPI METRICS
# -----------------------------------------
st.subheader("📋 Performance Overview")
kpi1, kpi2, kpi3, kpi4 = st.columns(4)

# Safely convert target/achievement strings to real numeric fields for calculations
total_target = int(pd.to_numeric(filtered_df[promise_col], errors='coerce').fillna(0).sum())
planned_achieved = int(pd.to_numeric(filtered_df[planned_col], errors='coerce').fillna(0).sum())
unplanned_achieved = int(pd.to_numeric(filtered_df[unplanned_col], errors='coerce').fillna(0).sum())

# Isolate target lapses strictly from core Promise Customers
if type_col in filtered_df.columns and balance_col in filtered_df.columns:
    promise_mask = filtered_df[type_col].str.lower().str.contains("promise", na=False)
    total_balance_lapse = int(pd.to_numeric(filtered_df[promise_mask][balance_col], errors='coerce').fillna(0).sum())
else:
    total_balance_lapse = 0

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
    
    # Isolate accounts where targets exist for a focused side-by-side comparison
    if promise_col in filtered_df.columns and planned_col in filtered_df.columns:
        promise_df = filtered_df[pd.to_numeric(filtered_df[promise_col], errors='coerce').fillna(0) > 0]
        
        if not promise_df.empty:
            df_melted = promise_df.melt(
                id_vars=[name_col], 
                value_vars=[promise_col, planned_col],
                var_name="Metric", value_name="Units"
            )
            fig_targets = px.bar(
                df_melted, x=name_col, y="Units", color="Metric",
                barmode="group", color_discrete_sequence=["#3182ce", "#319795"]
            )
            st.plotly_chart(fig_targets, use_container_width=True)
        else:
            st.info("No active promise target customers found within the current filter scope.")
    else:
        st.warning("Could not build bar chart: Column mismatch on target metrics.")

with col_right:
    st.subheader("Account Allocation Status Mix")
    if status_col in filtered_df.columns:
        status_counts = filtered_df[status_col].value_counts().reset_index()
        status_counts.columns = ["Fulfillment Status", "Count"]
        
        fig_status = px.pie(
            status_counts, names="Fulfillment Status", values="Count",
            hole=0.4, color_discrete_sequence=px.colors.qualitative.Safe
        )
        st.plotly_chart(fig_status, use_container_width=True)
    else:
        st.warning("Could not build status breakdown: 'Status' column not discovered.")

# -----------------------------------------
# RAW DATA LEDGER
# -----------------------------------------
st.subheader("🔍 Detailed Target Ledger")
st.dataframe(filtered_df, use_container_width=True)

