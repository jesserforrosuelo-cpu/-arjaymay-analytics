"""
Arjay May Hardware — Python Sales Analytics Dashboard

This app reads sales data that the PHP admin dashboard pushes into a
small public GitHub Gist (see admin/includes/analytics_sync.php in the
PHP project for why it works this way — InfinityFree's anti-bot system
blocks automated requests going directly INTO the PHP site from cloud
servers like this one, but PHP pushing data OUT works fine).

Run locally with:   streamlit run app.py
Deployed for free on Streamlit Community Cloud (share.streamlit.io).
"""

import streamlit as st
import pandas as pd
import requests
import plotly.express as px
from datetime import datetime

st.set_page_config(
    page_title="Arjay May Hardware — Analytics",
    page_icon="📊",
    layout="wide",
)

# ---- Configuration (read from Streamlit secrets) ----
# Set this in Streamlit Cloud under Settings -> Secrets:
#   GIST_RAW_URL = "https://gist.githubusercontent.com/USERNAME/GIST_ID/raw/analytics_data.json"
GIST_RAW_URL = st.secrets.get("GIST_RAW_URL", "")


@st.cache_data(ttl=60)
def load_data() -> dict:
    """Fetches the latest pushed data from the Gist. Cached for 60s so a
    burst of page interactions doesn't refetch on every widget change."""
    if not GIST_RAW_URL:
        st.error("Missing configuration. Set GIST_RAW_URL in Streamlit Cloud's Secrets settings.")
        st.stop()
    try:
        # Cache-bust query param so GitHub's CDN doesn't serve a stale copy.
        resp = requests.get(GIST_RAW_URL, params={"_": datetime.now().timestamp()}, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.RequestException as e:
        st.error(f"Couldn't load analytics data: {e}")
        st.stop()
    except ValueError:
        st.error("The data file exists but isn't valid JSON yet — open the PHP admin dashboard once to trigger the first sync.")
        st.stop()


# ==================== HEADER ====================
st.title("📊 Arjay May Hardware — Sales Analytics")

data = load_data()
generated_at = data.get("generated_at", "unknown")
st.caption(f"Data last synced from the store: {generated_at}")

if st.button("🔄 Refresh now"):
    load_data.clear()
    st.rerun()

st.info(
    "This data updates whenever someone opens the PHP admin dashboard "
    "(or clicks 'Sync Analytics Now' there) — not live, but refreshed "
    "regularly during business use.",
    icon="ℹ️",
)

st.divider()

# ==================== KPI SUMMARY ====================
summary = data.get("summary", {})

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Total Revenue", f"₱{float(summary.get('total_revenue', 0)):,.2f}")
col2.metric("Total Orders", f"{int(summary.get('total_orders', 0)):,}")
col3.metric("Avg Order Value", f"₱{float(summary.get('avg_order_value', 0)):,.2f}")
col4.metric("Today's Revenue", f"₱{float(summary.get('revenue_today', 0)):,.2f}", f"{int(summary.get('orders_today', 0))} orders today")
col5.metric("Low Stock Items", int(summary.get('low_stock_count', 0)), delta_color="inverse")

st.divider()

# ==================== SALES TREND ====================
st.subheader("Sales Trend")
trend_data = data.get("sales_trend", [])

if trend_data:
    df_trend = pd.DataFrame(trend_data)
    df_trend["date"] = pd.to_datetime(df_trend["date"])
    df_trend["revenue"] = df_trend["revenue"].astype(float)
    df_trend["orders"] = df_trend["orders"].astype(int)

    days = st.slider("Show last N days", min_value=7, max_value=180, value=30, step=1)
    cutoff = pd.Timestamp.now() - pd.Timedelta(days=days)
    df_trend = df_trend[df_trend["date"] >= cutoff]

    tab1, tab2 = st.tabs(["Revenue", "Order Count"])
    with tab1:
        fig = px.line(df_trend, x="date", y="revenue", markers=True,
                       labels={"date": "Date", "revenue": "Revenue (₱)"})
        fig.update_traces(line_color="#d32f2f")
        st.plotly_chart(fig, use_container_width=True)
    with tab2:
        fig2 = px.bar(df_trend, x="date", y="orders",
                       labels={"date": "Date", "orders": "Orders"})
        fig2.update_traces(marker_color="#f57c00")
        st.plotly_chart(fig2, use_container_width=True)
else:
    st.info("No sales recorded yet.")

st.divider()

# ==================== TOP PRODUCTS & CATEGORY BREAKDOWN ====================
left, right = st.columns(2)

with left:
    st.subheader("Top Selling Products")
    top_products = data.get("top_products", [])
    if top_products:
        df_top = pd.DataFrame(top_products)
        df_top["units_sold"] = df_top["units_sold"].astype(int)
        top_n = st.number_input("Show top", min_value=5, max_value=min(30, len(df_top)), value=min(10, len(df_top)), step=1)
        df_top = df_top.sort_values("units_sold", ascending=False).head(top_n)
        fig3 = px.bar(
            df_top.sort_values("units_sold"),
            x="units_sold", y="product_name", orientation="h",
            labels={"units_sold": "Units Sold", "product_name": ""},
        )
        fig3.update_traces(marker_color="#d32f2f")
        st.plotly_chart(fig3, use_container_width=True)
    else:
        st.info("No product sales recorded yet.")

with right:
    st.subheader("Revenue by Category")
    cat_data = data.get("sales_by_category", [])
    if cat_data:
        df_cat = pd.DataFrame(cat_data)
        df_cat["revenue"] = df_cat["revenue"].astype(float)
        fig4 = px.pie(df_cat, names="category", values="revenue", hole=0.4)
        st.plotly_chart(fig4, use_container_width=True)
    else:
        st.info("No category sales recorded yet.")

st.divider()

# ==================== INVENTORY HEALTH ====================
left2, right2 = st.columns(2)

with left2:
    st.subheader("⚠️ Low Stock Alert (10 units or fewer)")
    low_stock = data.get("low_stock", [])
    if low_stock:
        df_low = pd.DataFrame(low_stock)
        st.dataframe(df_low, use_container_width=True, hide_index=True)
    else:
        st.success("No products below 10 units. 🎉")

with right2:
    st.subheader("Inventory Value by Category")
    inv_data = data.get("inventory_value", [])
    if inv_data:
        df_inv = pd.DataFrame(inv_data)
        df_inv["stock_value"] = df_inv["stock_value"].astype(float)
        fig5 = px.bar(
            df_inv.sort_values("stock_value"),
            x="stock_value", y="category", orientation="h",
            labels={"stock_value": "Stock Value (₱)", "category": ""},
        )
        fig5.update_traces(marker_color="#f57c00")
        st.plotly_chart(fig5, use_container_width=True)
    else:
        st.info("No inventory data available yet.")

st.divider()
st.caption(
    "This dashboard is a separate Python service. It reads a snapshot of "
    "data that the PHP admin dashboard publishes — it never connects to "
    "or modifies the store's database directly."
)
