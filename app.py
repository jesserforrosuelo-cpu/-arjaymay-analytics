"""
Arjay May Hardware — Python Sales Analytics Dashboard

This is a standalone Python app (built with Streamlit) that reads live
sales data from the existing PHP/MySQL system through a small, secured
PHP "data bridge" (admin/api/analytics.php). It never touches the
database directly — InfinityFree (the PHP site's free host) blocks
external connections straight to the database, so this app instead calls
that PHP endpoint over HTTPS and gets JSON back, the same way any other
API integration works.

Run locally with:   streamlit run app.py
Deployed for free on Streamlit Community Cloud (share.streamlit.io).
"""

import streamlit as st
import pandas as pd
import cloudscraper
import plotly.express as px
from datetime import datetime

st.set_page_config(
    page_title="Arjay May Hardware — Analytics",
    page_icon="📊",
    layout="wide",
)

# ---- Configuration (read from Streamlit secrets, never hardcoded) ----
# Set these in Streamlit Cloud under "Secrets":
#   API_BASE_URL = "https://amhardware2026.wuaze.com/admin/api/analytics.php"
#   API_KEY = "the long random key from config.php"
API_BASE_URL = st.secrets.get("API_BASE_URL", "")
API_KEY = st.secrets.get("API_KEY", "")


@st.cache_resource
def get_scraper():
    """
    A cloudscraper session, reused across reruns. cloudscraper acts just
    like a requests.Session but automatically solves the kind of
    JavaScript anti-bot challenge InfinityFree puts in front of automated
    (non-browser) requests — it runs the same math the challenge's JS
    would, gets the resulting cookie, and retries, all under the hood.
    """
    return cloudscraper.create_scraper(browser={"custom": "chrome"})


def fetch(report: str, **params) -> list | dict:
    """Calls the PHP data bridge and returns the parsed JSON."""
    if not API_BASE_URL or not API_KEY:
        st.error(
            "Missing configuration. Set API_BASE_URL and API_KEY in "
            "Streamlit Cloud's Secrets settings."
        )
        st.stop()

    params["report"] = report
    params["key"] = API_KEY
    scraper = get_scraper()

    try:
        resp = scraper.get(API_BASE_URL, params=params, timeout=20)
    except Exception as e:
        st.error(f"Couldn't connect to the store's server at all ({report}): {e}")
        st.stop()

    # Got a response — but is it actually JSON? (Requests' resp.json() can
    # itself raise an error that looks like a connection error, so we check
    # manually here instead of relying on exception type.)
    try:
        return resp.json()
    except ValueError:
        st.error(f"Got a response, but it wasn't valid JSON for report '{report}'.")
        st.code(
            f"Status code: {resp.status_code}\n\n"
            f"Headers: {dict(resp.headers)}\n\n"
            f"Body (first 1000 chars):\n{resp.text[:1000]}"
        )
        st.stop()


# ==================== HEADER ====================
st.title("📊 Arjay May Hardware — Sales Analytics")
st.caption(f"Live data · Last refreshed {datetime.now().strftime('%b %d, %Y %I:%M %p')}")

if st.button("🔄 Refresh now"):
    st.rerun()

st.divider()

# ==================== KPI SUMMARY ====================
summary = fetch("summary")

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Total Revenue", f"₱{summary['total_revenue']:,.2f}")
col2.metric("Total Orders", f"{int(summary['total_orders']):,}")
col3.metric("Avg Order Value", f"₱{summary['avg_order_value']:,.2f}")
col4.metric("Today's Revenue", f"₱{summary['revenue_today']:,.2f}", f"{int(summary['orders_today'])} orders today")
col5.metric("Low Stock Items", int(summary['low_stock_count']), delta_color="inverse")

st.divider()

# ==================== SALES TREND ====================
st.subheader("Sales Trend")
days = st.slider("Show last N days", min_value=7, max_value=180, value=30, step=1)

trend_data = fetch("sales_trend", days=days)
if trend_data:
    df_trend = pd.DataFrame(trend_data)
    df_trend["date"] = pd.to_datetime(df_trend["date"])
    df_trend["revenue"] = df_trend["revenue"].astype(float)
    df_trend["orders"] = df_trend["orders"].astype(int)

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
    st.info("No sales recorded in this date range yet.")

st.divider()

# ==================== TOP PRODUCTS & CATEGORY BREAKDOWN ====================
left, right = st.columns(2)

with left:
    st.subheader("Top Selling Products")
    top_n = st.number_input("Show top", min_value=5, max_value=30, value=10, step=1)
    top_products = fetch("top_products", limit=top_n)
    if top_products:
        df_top = pd.DataFrame(top_products)
        df_top["units_sold"] = df_top["units_sold"].astype(int)
        df_top["revenue"] = df_top["revenue"].astype(float)
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
    cat_data = fetch("sales_by_category")
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
    st.subheader("⚠️ Low Stock Alert")
    threshold = st.number_input("Alert threshold (units)", min_value=1, max_value=100, value=10, step=1)
    low_stock = fetch("low_stock", threshold=threshold)
    if low_stock:
        df_low = pd.DataFrame(low_stock)
        st.dataframe(df_low, use_container_width=True, hide_index=True)
    else:
        st.success("No products below this stock threshold. 🎉")

with right2:
    st.subheader("Inventory Value by Category")
    inv_data = fetch("inventory_value")
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
    "This dashboard is a separate Python service. It reads data from the "
    "main PHP/MySQL system through a secured API bridge — it never "
    "stores or modifies any data itself."
)
