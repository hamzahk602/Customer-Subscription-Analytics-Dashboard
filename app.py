import streamlit as st
import pandas as pd
import altair as alt

# --- Page Configuration ---
# Set up the page layout, title, and icon
st.set_page_config(
    page_title="Customer Subscription Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# --- Data Loading and Cleaning ---
# Cache the data loading to improve performance
@st.cache_data
def load_data(file_path):
    """
    Loads and cleans the customer subscription data from a CSV file.
    It converts date columns to datetime objects, fills missing EndDates with the current date,
    and handles potential errors.
    """
    try:
        df = pd.read_csv(file_path)
        
        # Clean column names by removing leading/trailing whitespace
        df.columns = df.columns.str.strip()
        
        # Convert date columns to datetime format. 'coerce' will turn invalid dates into NaT (Not a Time).
        df['StartDate'] = pd.to_datetime(df['StartDate'], errors='coerce')
        df['EndDate'] = pd.to_datetime(df['EndDate'], errors='coerce')
        
        # *** NEW: Fill missing EndDate values with today's date ***
        # This treats active subscriptions as ongoing until the present day.
        df['EndDate'].fillna(pd.to_datetime('today').normalize(), inplace=True)
        
        # Drop rows if critical information like StartDate or CustomerID is missing
        df.dropna(subset=['StartDate', 'CustomerID', 'Status'], inplace=True)
        
        # Clean the 'Status' column data to remove extra whitespace
        df['Status'] = df['Status'].str.strip()
        
        return df
    except FileNotFoundError:
        st.error(f"Error: The file '{file_path}' was not found. Please double-check these two things:")
        st.error("1. The script 'app.py' is in the EXACT same folder as your data file.")
        st.error(f"2. The data file is named EXACTLY: '{file_path}'")
        return None

# --- Main Application Logic ---
def main():
    """
    The main function that runs the Streamlit application.
    """
    st.title("📊 Customer Subscription Analytics Dashboard")
    st.markdown("An interactive dashboard to analyze customer behavior, churn, and revenue trends.")

    # This filename has been updated to 'Analytics.csv' as requested.
    file_to_load = 'Analytics.csv'
    df = load_data(file_to_load)

    # Proceed only if the data is loaded successfully
    if df is not None:
        # --- Sidebar Filters ---
        st.sidebar.header("Dashboard Filters")
        
        # Region Filter in the sidebar
        regions = sorted(df['Region'].unique())
        selected_regions = st.sidebar.multiselect("Region", regions, default=regions)
        
        # Plan Type Filter in the sidebar
        plan_types = sorted(df['PlanType'].unique())
        selected_plan_types = st.sidebar.multiselect("Plan Type", plan_types, default=plan_types)
        
        # Customer Status Filter in the sidebar
        statuses = sorted(df['Status'].unique())
        selected_statuses = st.sidebar.multiselect("Customer Status", statuses, default=statuses)

        # Apply all selected filters to the dataframe
        filtered_df = df[
            df['Region'].isin(selected_regions) &
            df['PlanType'].isin(selected_plan_types) &
            df['Status'].isin(selected_statuses)
        ]
        
        # Display a warning if no data matches the filters
        if filtered_df.empty:
            st.warning("No data matches the selected filters. Please adjust your selection.")
            return

        # --- Key Metrics Display ---
        st.subheader("Key Performance Indicators")
        
        total_customers = filtered_df['CustomerID'].nunique()
        churned_customers = filtered_df[filtered_df['Status'] == 'Churned']['CustomerID'].nunique()
        churn_rate = (churned_customers / total_customers) * 100 if total_customers > 0 else 0
        total_mrr = filtered_df['MonthlyRevenue'].sum()

        # Arrange metrics in columns for a clean layout
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Customers", f"{total_customers:,}")
        with col2:
            st.metric("Total Churned", f"{churned_customers:,}")
        with col3:
            st.metric("Churn Rate", f"{churn_rate:.2f}%")
        with col4:
            st.metric("Total MRR", f"${total_mrr:,.0f}")
        
        st.markdown("---")

        # --- Visualizations ---
        col_left, col_right = st.columns((5, 5), gap="medium")

        with col_left:
            # Chart 1: Monthly Churn Trend
            st.subheader("Monthly Churn Trend")
            churned_data = filtered_df[filtered_df['Status'] == 'Churned'].copy()
            if not churned_data.empty:
                churned_data['ChurnMonth'] = churned_data['EndDate'].dt.to_period('M').astype(str)
                monthly_churn = churned_data.groupby('ChurnMonth').size().reset_index(name='ChurnCount')
                
                churn_chart = alt.Chart(monthly_churn).mark_line(point=True, strokeWidth=3).encode(
                    x=alt.X('ChurnMonth:T', title='Month of Churn'),
                    y=alt.Y('ChurnCount:Q', title='Number of Churned Customers'),
                    tooltip=[alt.Tooltip('ChurnMonth:T', title='Month'), alt.Tooltip('ChurnCount:Q', title='Churn Count')]
                ).interactive()
                st.altair_chart(churn_chart, use_container_width=True)
            else:
                st.info("No churned customers in the selected data to display trend.")
        
        with col_right:
            # Chart 2: MRR by Region
            st.subheader("MRR by Region")
            mrr_by_region = filtered_df.groupby('Region')['MonthlyRevenue'].sum().reset_index()
            
            mrr_chart = alt.Chart(mrr_by_region).mark_bar().encode(
                x=alt.X('Region:N', title='Region', sort='-y'),
                y=alt.Y('MonthlyRevenue:Q', title='Total Monthly Revenue'),
                color=alt.Color('Region:N', legend=None),
                tooltip=[alt.Tooltip('Region:N', title='Region'), alt.Tooltip('MonthlyRevenue:Q', title='MRR', format='$,.0f')]
            ).interactive()
            st.altair_chart(mrr_chart, use_container_width=True)

        st.markdown("---")
        
        col_left2, col_right2 = st.columns((5, 5), gap="medium")
        
        with col_left2:
            # Chart 3: Churn Distribution by Plan Type
            st.subheader("Churn Distribution by Plan Type")
            # Create a subset of churned customers first
            churned_plan_data = filtered_df[filtered_df['Status'] == 'Churned']
            # Only build the chart if there is data
            if not churned_plan_data.empty:
                churn_by_plan = churned_plan_data['PlanType'].value_counts().reset_index()
                
                plan_churn_chart = alt.Chart(churn_by_plan).mark_bar().encode(
                    x=alt.X('PlanType:N', title='Plan Type', sort='-y'),
                    y=alt.Y('count:Q', title='Number of Churned Customers'),
                    color=alt.Color('PlanType:N', legend=None),
                    tooltip=['PlanType', 'count']
                ).interactive()
                st.altair_chart(plan_churn_chart, use_container_width=True)
            else:
                st.info("No churned customers to display for this chart.")

        with col_right2:
            # Chart 4: NPS Score Distribution
            st.subheader("NPS Score Distribution")
            nps_chart = alt.Chart(filtered_df).mark_bar().encode(
                x=alt.X('NPS:Q', bin=alt.Bin(maxbins=10), title='NPS Score'),
                y=alt.Y('count()', title='Number of Customers'),
                tooltip=[alt.Tooltip('NPS:Q', bin=True, title='NPS Range'), 'count()']
            ).interactive()
            st.altair_chart(nps_chart, use_container_width=True)

        # --- Data Table ---
        st.markdown("---")
        with st.expander("View Raw Data Table", expanded=False):
            st.dataframe(filtered_df)

# Entry point for the script
if __name__ == "__main__":
    main()

