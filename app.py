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
    # Read the first tab position raw without assuming where headers are
    raw_data = pd.read_excel(base_url, sheet_name=0, header=None)
    
    # Dynamic Header Search: Find the first row that actually contains your data columns
    header_row_index = 0
    for idx, row in raw_data.iterrows():
        row_str = row.astype(str).str.lower().values
        # Search for any core keyword unique to your operational columns
        if 'customer name' in row_str or 'promise qty' in row_str or 'category' in row_str:
            header_row_index = idx
            break
            
    # Reload the file, dropping everything above your actual headers
    cleaned_data = pd.read_excel(base_url, sheet_name=0, skiprows=header_row_index)
    
    # Ensure all column headers are strings and strip out empty spaces
    cleaned_data.columns = [str(col).strip() for col in cleaned_data.columns]
    
    return cleaned_data

try:
    df = load_data()
except Exception as e:
    st.error(f"❌ Could not retrieve data from the 1st sheet tab. Error details: {e}")
    st.info("💡 Quick Check: Double check that your Google Sheet access is set to 'Anyone with the link can view' and click 'Done'.")
    st.stop()

# -----------------------------------------
# AUTODETECT COLUMNS (Bypasses Attribute and KeyErrors)
# -----------------------------------------
# Filter out any unexpected non-string columns just in case
valid_columns = [col for col in df.columns if isinstance(col, str) and not col.startswith("Unnamed:")]
col_map = {col.lower(): col for col in valid_columns}

# Identify operational columns
name_col = col_map.get("customer name", df.columns[0] if len(df.columns) > 0 else "Customer Name")
category_col = col_map.get("category", col_map.get("product category", "Category"))
month_col = col_map.get("month", "Month")

promise_col = col_map.get("promise qty", "Promise Qty")
planned_col = col_map.get("planned customer qty achieved", "Planned Customer Qty Achieved")
unplanned_col = col_map.get("unplanned customer qty achieved", "Unplanned Customer Qty Achieved")
balance_col = col_map.get("balance qty", "Balance Qty")
status_col = col_map.get("status", "Status")
type_col = col_map.get("type", "Type")

# Clean text data cells dynamically for reliable filtering
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

# Dynamic Slider for Promise Qty Range
if promise_col in df.columns:
    # Convert column to numbers safely to find true min and max boundaries
    numeric_promise = pd.to_numeric(df[promise_col], errors='coerce').fillna(0).astype(int)
    min_qty = int(numeric_promise.min())
    max_qty = int(numeric_promise.max())
    
    # Fallback bounds just in case data is flat
    if min_qty == max_qty:
        max_qty = min_qty + 100
        
    st.sidebar.markdown("---")
    st.sidebar.subheader("Filter by Promise Qty Range")
    
    # Creates the dual-handled range slider
    qty_range = st.sidebar.slider(
        "Select Quantity Range",
        min_value=min_qty,
        max_value=max_qty,
        value=(10, 40) if max_qty >= 40 else (min_qty, max_qty), # Defaults to 10 - 40 if possible
        step=1
    )
else:
    qty_range = None

# -----------------------------------------
# Apply filter selections
# -----------------------------------------
filtered_df = df.copy()

if selected_month != "All":
    filtered_df = filtered_df[filtered_df[month_col] == selected_month]
if selected_category != "All":
    filtered_df = filtered_df[filtered_df[category_col] == selected_category]
if selected_type != "All":
    filtered_df = filtered_df[filtered_df[type_col] == selected_type]

# Apply the Promise Qty Range filter logic
if qty_range is not None:
    # Safely evaluate row values numerically
    row_numeric_promise = pd.to_numeric(filtered_df[promise_col], errors='coerce').fillna(0)
    filtered_df = filtered_df[
        (row_numeric_promise >= qty_range[0]) & 
        (row_numeric_promise <= qty_range[1])
    ]

# -----------------------------------------
# CORE KPI METRICS (EXPANDED TO 5 BLOCKS)
# -----------------------------------------
st.subheader("📋 Performance Overview")

# Set up 5 columns side-by-side
kpi1, kpi2, kpi3, kpi4, kpi5 = st.columns(5)

# Safely aggregate data fields while filtering string noise
def safe_sum(dataframe, column_name):
    if column_name in dataframe.columns:
        return int(pd.to_numeric(dataframe[column_name], errors='coerce').fillna(0).sum())
    return 0

total_target = safe_sum(filtered_df, promise_col)
planned_achieved = safe_sum(filtered_df, planned_col)
unplanned_achieved = safe_sum(filtered_df, unplanned_col)

# Calculate total sales volume (Planned + Unplanned Organic Sales)
total_sales_volume = planned_achieved + unplanned_achieved

if type_col in filtered_df.columns and balance_col in filtered_df.columns:
    promise_mask = filtered_df[type_col].str.lower().str.contains("promise", na=False)
    total_balance_lapse = int(pd.to_numeric(filtered_df[promise_mask][balance_col], errors='coerce').fillna(0).sum())
else:
    total_balance_lapse = 0

# Calculate target clearance rate as a clean percentage layout
target_clearance_rate = (planned_achieved / total_target * 100) if total_target > 0 else 100.0

# KPI Box 1: Total Promised Target
with kpi1:
    st.markdown(
        f"""
        <div style="background-color: #f7fafc; padding: 15px 10px; border-radius: 10px; border-left: 5px solid #3182ce; text-align: center; box-shadow: 1px 1px 5px rgba(0,0,0,0.05); min-height: 110px;">
            <p style="margin: 0; font-size: 12px; color: #4a5568; font-weight: bold; text-transform: uppercase;">Total Promised Target</p>
            <h2 style="margin: 8px 0 0 0; color: #2b6cb0; font-size: 24px;">{total_target:,} <span style="font-size: 12px; color: #718096;">units</span></h2>
        </div>
        """, 
        unsafe_allow_html=True
    )

# KPI Box 2: Planned Qty Achieved
with kpi2:
    clearance_color = "#319795" if target_clearance_rate >= 75 else "#dd6b20"
    st.markdown(
        f"""
        <div style="background-color: #f7fafc; padding: 15px 10px; border-radius: 10px; border-left: 5px solid #319795; text-align: center; box-shadow: 1px 1px 5px rgba(0,0,0,0.05); min-height: 110px;">
            <p style="margin: 0; font-size: 12px; color: #4a5568; font-weight: bold; text-transform: uppercase;">Planned Qty Achieved</p>
            <h2 style="margin: 8px 0 0 0; color: #234e52; font-size: 24px;">{planned_achieved:,} <span style="font-size: 12px; color: #718096;">units</span></h2>
            <p style="margin: 3px 0 0 0; font-size: 12px; color: {clearance_color}; font-weight: bold;">🎯 Clearance: {target_clearance_rate:.1f}%</p>
        </div>
        """, 
        unsafe_allow_html=True
    )

# KPI Box 3: Target Deficit Balance
with kpi3:
    st.markdown(
        f"""
        <div style="background-color: #fff5f5; padding: 15px 10px; border-radius: 10px; border-left: 5px solid #e53e3e; text-align: center; box-shadow: 1px 1px 5px rgba(0,0,0,0.05); min-height: 110px;">
            <p style="margin: 0; font-size: 12px; color: #9b2c2c; font-weight: bold; text-transform: uppercase;">Target Deficit Balance</p>
            <h2 style="margin: 8px 0 0 0; color: #9b2c2c; font-size: 24px;">{total_balance_lapse:,} <span style="font-size: 12px; color: #c53030;">units</span></h2>
            <p style="margin: 3px 0 0 0; font-size: 11px; color: #e53e3e; font-weight: bold;">⚠️ Missing from Target</p>
        </div>
        """, 
        unsafe_allow_html=True
    )

# KPI Box 4: Organic Unplanned Sales
with kpi4:
    st.markdown(
        f"""
        <div style="background-color: #f7fafc; padding: 15px 10px; border-radius: 10px; border-left: 5px solid #805ad5; text-align: center; box-shadow: 1px 1px 5px rgba(0,0,0,0.05); min-height: 110px;">
            <p style="margin: 0; font-size: 12px; color: #4a5568; font-weight: bold; text-transform: uppercase;">Organic Unplanned Sales</p>
            <h2 style="margin: 8px 0 0 0; color: #553c9a; font-size: 24px;">{unplanned_achieved:,} <span style="font-size: 12px; color: #718096;">units</span></h2>
        </div>
        """, 
        unsafe_allow_html=True
    )

# KPI Box 5: Total Sales Made (Planned + Organic Gross Volume)
with kpi5:
    st.markdown(
        f"""
        <div style="background-color: #f0fff4; padding: 15px 10px; border-radius: 10px; border-left: 5px solid #38a169; text-align: center; box-shadow: 1px 1px 5px rgba(0,0,0,0.05); min-height: 110px;">
            <p style="margin: 0; font-size: 12px; color: #22543d; font-weight: bold; text-transform: uppercase;">Total Sales Made</p>
            <h2 style="margin: 8px 0 0 0; color: #276749; font-size: 24px;">{total_sales_volume:,} <span style="font-size: 12px; color: #48bb78;">units</span></h2>
            <p style="margin: 3px 0 0 0; font-size: 11px; color: #38a169; font-weight: bold;">📈 Total Output</p>
        </div>
        """, 
        unsafe_allow_html=True
    )

st.markdown("---")

# -----------------------------------------
# VISUAL CHARTS
# -----------------------------------------
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("Target vs Planned Achievement per Client")
    if promise_col in filtered_df.columns and planned_col in filtered_df.columns and name_col in filtered_df.columns:
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
        st.warning("Awaiting clear customer data to generate comparative metrics.")

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
        st.warning("Awaiting operational status metrics.")

# -----------------------------------------
# RAW DATA LEDGER
# -----------------------------------------
st.subheader("🔍 Detailed Target Ledger")
st.dataframe(filtered_df, use_container_width=True)
