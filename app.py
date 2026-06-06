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
# CORE KPI METRICS (EXPANDED TO 5
