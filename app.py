import streamlit as st
import sqlite3
import pandas as pd
from datetime import datetime

# Page configuration
st.set_page_config(
    page_title="System Monitor Dashboard",
    page_icon="📊",
    layout="wide"
)

DB_NAME = "log.db"

# Database connection functions
@st.cache_data(ttl=10)
def get_system_logs(ping_filter=None):
    """Fetch system logs from database with optional ping filter"""
    conn = sqlite3.connect(DB_NAME)
    
    if ping_filter and ping_filter != "All":
        query = """
            SELECT * FROM system_log 
            WHERE ping_status = ?
            ORDER BY id DESC
        """
        df = pd.read_sql_query(query, conn, params=(ping_filter,))
    else:
        query = "SELECT * FROM system_log ORDER BY id DESC"
        df = pd.read_sql_query(query, conn)
    
    conn.close()
    return df

@st.cache_data(ttl=10)
def get_alerts_log():
    """Fetch alerts from database"""
    conn = sqlite3.connect(DB_NAME)
    query = "SELECT * FROM alerts_log ORDER BY id DESC LIMIT 20"
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

@st.cache_data(ttl=10)
def get_statistics():
    """Get database statistics"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM system_log")
    log_count = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM alerts_log")
    alert_count = cursor.fetchone()[0]
    
    # Get latest metrics
    cursor.execute("""
        SELECT cpu, memory, disk, ping_status, ping_ms 
        FROM system_log 
        ORDER BY id DESC 
        LIMIT 1
    """)
    latest = cursor.fetchone()
    
    conn.close()
    
    return {
        'log_count': log_count,
        'alert_count': alert_count,
        'latest_cpu': latest[0] if latest else 0,
        'latest_memory': latest[1] if latest else 0,
        'latest_disk': latest[2] if latest else 0,
        'latest_ping_status': latest[3] if latest else "N/A",
        'latest_ping_ms': latest[4] if latest else 0
    }

# Main dashboard
def main():
    st.title("📊 System Monitor Dashboard")
    st.markdown("---")
    
    # Sidebar filters
    st.sidebar.header("⚙️ Filters")
    
    # Ping status filter
    ping_options = ["All", "UP", "DOWN"]
    ping_filter = st.sidebar.selectbox("Ping Status Filter", ping_options)
    
    # Number of records to display
    num_records = st.sidebar.slider("Number of Records to Display", 5, 100, 20)
    
    # Refresh button
    if st.sidebar.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()
    
    # Get data
    try:
        stats = get_statistics()
        
        # Display key metrics
        st.header("📈 Current System Status")
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric("CPU Usage", f"{stats['latest_cpu']:.1f}%", 
                     delta=f"{stats['latest_cpu'] - 80:.1f}%" if stats['latest_cpu'] > 80 else None,
                     delta_color="inverse")
        
        with col2:
            st.metric("Memory Usage", f"{stats['latest_memory']:.1f}%",
                     delta=f"{stats['latest_memory'] - 85:.1f}%" if stats['latest_memory'] > 85 else None,
                     delta_color="inverse")
        
        with col3:
            st.metric("Disk Usage", f"{stats['latest_disk']:.1f}%",
                     delta=f"{stats['latest_disk'] - 90:.1f}%" if stats['latest_disk'] > 90 else None,
                     delta_color="inverse")
        
        with col4:
            ping_status_icon = "🟢" if stats['latest_ping_status'] == "UP" else "🔴"
            st.metric("Ping Status", f"{ping_status_icon} {stats['latest_ping_status']}")
        
        with col5:
            ping_display = f"{stats['latest_ping_ms']:.1f}ms" if stats['latest_ping_ms'] > 0 else "N/A"
            st.metric("Ping Time", ping_display)
        
        st.markdown("---")
        
        # Alerts section
        st.header("🚨 Recent Alerts")
        alerts_df = get_alerts_log()
        
        if not alerts_df.empty:
            # Display alert count
            col1, col2 = st.columns([1, 3])
            with col1:
                st.metric("Total Alerts", stats['alert_count'])
            
            # Display alerts in expandable section
            with st.expander(f"View Latest {len(alerts_df)} Alerts", expanded=True):
                for _, alert in alerts_df.iterrows():
                    alert_color = {
                        'CPU': '🔴',
                        'MEMORY': '🟠',
                        'DISK': '🟡'
                    }.get(alert['alert_type'], '⚪')
                    
                    st.warning(f"{alert_color} **{alert['timestamp']}** - {alert['message']}")
        else:
            st.success("✅ No alerts triggered! All systems operating normally.")
        
        st.markdown("---")
        
        # System logs table
        st.header("📋 System Logs")
        df = get_system_logs(ping_filter if ping_filter != "All" else None)
        
        if not df.empty:
            # Display record count
            st.info(f"Showing {min(num_records, len(df))} of {stats['log_count']} total records")
            
            # Display table
            display_df = df.head(num_records).copy()
            display_df['cpu'] = display_df['cpu'].apply(lambda x: f"{x:.1f}%")
            display_df['memory'] = display_df['memory'].apply(lambda x: f"{x:.1f}%")
            display_df['disk'] = display_df['disk'].apply(lambda x: f"{x:.1f}%")
            display_df['ping_ms'] = display_df['ping_ms'].apply(lambda x: f"{x:.1f}ms" if x > 0 else "N/A")
            
            st.dataframe(
                display_df,
                use_container_width=True,
                hide_index=True
            )
        else:
            st.warning("No data available in the database.")
            return
        
        st.markdown("---")
        
        # Charts section
        st.header("📊 Performance Charts")
        
        # Prepare data for charts (use all data, not filtered)
        chart_df = get_system_logs()  # Get all data for comprehensive charts
        chart_df = chart_df.sort_values('id')  # Sort by ID for chronological order
        
        # Create a DataFrame for line chart with timestamp as index
        chart_data = chart_df[['timestamp', 'cpu', 'memory', 'disk']].copy()
        chart_data = chart_data.rename(columns={
            'cpu': 'CPU %',
            'memory': 'Memory %',
            'disk': 'Disk %'
        })
        chart_data['timestamp'] = pd.to_datetime(chart_data['timestamp'])
        chart_data = chart_data.set_index('timestamp')
        
        # CPU, Memory, Disk Line Chart
        st.subheader("System Resource Usage Over Time")
        st.line_chart(chart_data, height=400)
        
        # Display threshold information
        col1, col2, col3 = st.columns(3)
        with col1:
            st.caption("🔴 CPU Threshold: 80%")
        with col2:
            st.caption("🟠 Memory Threshold: 85%")
        with col3:
            st.caption("🟡 Disk Threshold: 90%")
        
        st.markdown("---")
        
        # Ping Response Time Chart
        st.subheader("Network Ping Response Time")
        
        ping_df = chart_df[chart_df['ping_ms'] > 0].copy()
        
        if not ping_df.empty:
            ping_chart = ping_df[['timestamp', 'ping_ms']].copy()
            ping_chart['timestamp'] = pd.to_datetime(ping_chart['timestamp'])
            ping_chart = ping_chart.set_index('timestamp')
            ping_chart = ping_chart.rename(columns={'ping_ms': 'Ping (ms)'})
            
            st.line_chart(ping_chart, height=300, color='#6C5CE7')
        else:
            st.info("No successful ping data available.")
        
        st.markdown("---")
        
        # Summary statistics
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📊 Average Resource Usage")
            avg_stats = pd.DataFrame({
                'Metric': ['CPU', 'Memory', 'Disk'],
                'Average (%)': [
                    f"{chart_df['cpu'].mean():.2f}",
                    f"{chart_df['memory'].mean():.2f}",
                    f"{chart_df['disk'].mean():.2f}"
                ],
                'Max (%)': [
                    f"{chart_df['cpu'].max():.2f}",
                    f"{chart_df['memory'].max():.2f}",
                    f"{chart_df['disk'].max():.2f}"
                ]
            })
            st.dataframe(avg_stats, use_container_width=True, hide_index=True)
        
        with col2:
            st.subheader("🌐 Ping Status Summary")
            ping_counts = chart_df['ping_status'].value_counts()
            ping_summary = pd.DataFrame({
                'Status': ping_counts.index,
                'Count': ping_counts.values,
                'Percentage': [f"{(count/len(chart_df)*100):.1f}%" for count in ping_counts.values]
            })
            st.dataframe(ping_summary, use_container_width=True, hide_index=True)
        
    except Exception as e:
        st.error(f"Error loading data: {e}")
        st.info("Make sure 'log.db' exists in the same directory. Run your logger script first.")

if __name__ == "__main__":
    main()