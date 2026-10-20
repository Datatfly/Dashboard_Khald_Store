import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from datetime import date

# ======================================================
# CONFIG & THEME
# ======================================================

st.set_page_config(
    page_title="WeSell | Khaled Store Analytics",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
.stApp {
    background-color: #0B1120;
    color: #F1F5F9;
}
[data-testid="stSidebar"] {
    background-color: #111827;
}
[data-testid="stMetric"] {
    background-color: #172033;
    border: 1px solid #263449;
    padding: 18px;
    border-radius: 14px;
}
[data-testid="stMetricLabel"] {
    color: #A5B4CC;
}
[data-testid="stMetricValue"] {
    color: #38BDF8;
}
h1, h2, h3 {
    color: #F8FAFC;
}
div.stButton > button {
    background-color: #2563EB;
    color: white;
    border-radius: 10px;
    border: none;
}
</style>
""", unsafe_allow_html=True)

# ======================================================
# API SETTINGS
# ======================================================

SUBDOMAIN = "khaled22"
BASE_URL = f"https://{SUBDOMAIN}.wesell.world/api/v1/orders"

# Paste your API key here. Do not publish it.
API_KEY = "422|8T2SKD6Xpb8w4WfXPtLHZEVSKeB4RwLXB2JnYkA37a5bb893"

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Accept": "application/json"
}

MAX_ORDERS = 10000
PER_PAGE = 100

# ======================================================
# HELPERS
# ======================================================

def first_value(record, keys):
    """Return the first non-empty value from candidate fields."""
    if not isinstance(record, dict):
        return None

    for key in keys:
        value = record.get(key)

        if value is not None and value != "":
            if isinstance(value, dict):
                value = (
                    value.get("name")
                    or value.get("title")
                    or value.get("id")
                )

            if value is not None and value != "":
                return value

    return None


def campaign_value(order):
    """
    Try common campaign/source field names.
    Adjust the candidates if the API uses another field name.
    """
    candidates = [
        "campaign_name",
        "campaign_id",
        "campaign",
        "utm_campaign",
        "source_name",
        "source",
        "traffic_source",
        "marketing_source",
        "campaign_number",
        "campaign_uuid"
    ]

    value = first_value(order, candidates)

    # Some APIs nest campaign information in another object.
    if value is None:
        for parent_key in ["marketing", "attribution", "tracking"]:
            nested = order.get(parent_key)

            value = first_value(nested, candidates)

            if value is not None:
                break

    return value if value is not None else "Unknown"


# ======================================================
# LOAD UP TO 10,000 ORDERS
# ======================================================

@st.cache_data(ttl=300, show_spinner=False)
def load_data(api_key, max_orders=10000, per_page=100):

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json"
    }

    all_orders = []
    page = 1
    total_pages = None

    while len(all_orders) < max_orders:

        response = requests.get(
            BASE_URL,
            headers=headers,
            params={
                "page": page,
                "per_page": min(
                    per_page,
                    max_orders - len(all_orders)
                )
            },
            timeout=60
        )

        response.raise_for_status()
        result = response.json()

        if result.get("success") is False:
            raise RuntimeError(
                result.get("message", "API returned an error.")
            )

        page_orders = result.get("data", [])

        if not isinstance(page_orders, list):
            raise RuntimeError(
                "Unexpected API response: data is not a list."
            )

        if not page_orders:
            break

        all_orders.extend(page_orders)

        meta = result.get("meta") or {}

        if meta.get("last_page") is not None:
            total_pages = int(meta["last_page"])

        if total_pages is not None and page >= total_pages:
            break

        if len(page_orders) < min(
            per_page,
            max_orders - (len(all_orders) - len(page_orders))
        ):
            break

        page += 1

    return all_orders[:max_orders]


# ======================================================
# HEADER
# ======================================================

st.title("📊 WeSell Analytics")
st.caption(
    "Khaled Store | Orders, Campaigns & Sales Performance"
)

if not API_KEY or API_KEY == "PASTE_YOUR_API_KEY_HERE":
    st.error("ضع مفتاح WeSell API في متغير API_KEY داخل الكود.")
    st.stop()

refresh_col, info_col = st.columns([1, 4])

with refresh_col:
    if st.button("🔄 Refresh Data", use_container_width=True):
        load_data.clear()
        st.rerun()

with info_col:
    st.caption("Maximum 10,000 orders | Cache: 5 minutes")

# ======================================================
# FETCH DATA
# ======================================================

try:
    with st.spinner("Loading orders from WeSell..."):
        orders = load_data(
            API_KEY,
            MAX_ORDERS,
            PER_PAGE
        )

except Exception as error:
    st.error(f"Unable to load orders: {error}")
    st.stop()

if not orders:
    st.warning("No orders found.")
    st.stop()

st.success(f"Loaded {len(orders):,} orders.")

# ======================================================
# BUILD ORDER DATAFRAME
# ======================================================

order_rows = []

for order in orders:

    customer = order.get("customer") or {}
    address = order.get("address") or {}

    city = address.get("city") or {}
    area = address.get("area") or {}

    if not isinstance(city, dict):
        city = {}

    if not isinstance(area, dict):
        area = {}

    order_rows.append({
        "order_uuid": order.get("uuid"),
        "order_number": order.get("order_number"),

        "status": order.get("status"),
        "status_label": order.get("status_label") or order.get("status"),

        "payment_method": order.get("payment_method"),

        "amount": order.get("amount"),
        "amount_to_collect": order.get("amount_to_collect"),
        "deposit": order.get("deposit"),
        "shipping_price": order.get("shipping_price"),

        "customer_name": customer.get("name"),
        "customer_mobile": customer.get("mobile"),

        "city": city.get("name"),
        "area": area.get("name"),

        "campaign": campaign_value(order),

        "created_at": order.get("created_at"),
        "updated_at": order.get("updated_at")
    })

orders_df = pd.DataFrame(order_rows)

# ======================================================
# CLEAN DATA
# ======================================================

for column in ["created_at", "updated_at"]:
    orders_df[column] = pd.to_datetime(
        orders_df[column],
        errors="coerce",
        utc=True
    ).dt.tz_convert("Africa/Cairo")

orders_df["date"] = orders_df["created_at"].dt.date

for column in [
    "amount",
    "amount_to_collect",
    "deposit",
    "shipping_price"
]:
    orders_df[column] = pd.to_numeric(
        orders_df[column],
        errors="coerce"
    ).fillna(0)

# ======================================================
# BUILD ITEMS DATAFRAME
# ======================================================

item_rows = []

for order in orders:

    for item in (order.get("items") or []):

        item_rows.append({
            "order_uuid": order.get("uuid"),
            "product_name": item.get("product_name") or "Unknown",
            "sku": item.get("sku"),
            "quantity": item.get("quantity"),
            "price": item.get("price"),
            "total": item.get("total")
        })

items_df = pd.DataFrame(
    item_rows,
    columns=[
        "order_uuid",
        "product_name",
        "sku",
        "quantity",
        "price",
        "total"
    ]
)

for column in ["quantity", "price", "total"]:
    items_df[column] = pd.to_numeric(
        items_df[column],
        errors="coerce"
    ).fillna(0)

# ======================================================
# SIDEBAR FILTERS
# ======================================================

st.sidebar.title("🎛️ Dashboard Filters")

status_options = sorted(
    orders_df["status_label"].dropna().unique().tolist()
)

selected_status = st.sidebar.multiselect(
    "Order Status",
    status_options
)

city_options = sorted(
    orders_df["city"].dropna().unique().tolist()
)

selected_city = st.sidebar.multiselect(
    "City",
    city_options
)

campaign_options = sorted(
    orders_df["campaign"].dropna().unique().tolist()
)

selected_campaign = st.sidebar.multiselect(
    "Campaign / Source",
    campaign_options
)

available_dates = sorted(
    orders_df["date"].dropna().unique().tolist(),
    reverse=True
)

date_options = ["All Days"] + available_dates

selected_date = st.sidebar.selectbox(
    "📅 Select Day",
    date_options,
    format_func=lambda value: (
        value.strftime("%Y-%m-%d")
        if isinstance(value, date)
        else value
    )
)

# ======================================================
# APPLY FILTERS
# ======================================================

filtered = orders_df.copy()

if selected_status:
    filtered = filtered[
        filtered["status_label"].isin(selected_status)
    ]

if selected_city:
    filtered = filtered[
        filtered["city"].isin(selected_city)
    ]

if selected_campaign:
    filtered = filtered[
        filtered["campaign"].isin(selected_campaign)
    ]

if selected_date != "All Days":
    filtered = filtered[
        filtered["date"] == selected_date
    ]

filtered_ids = set(filtered["order_uuid"].dropna())

filtered_items = items_df[
    items_df["order_uuid"].isin(filtered_ids)
].copy()

# ======================================================
# KPI CALCULATIONS
# ======================================================

total_orders = len(filtered)

delivered = int(
    (filtered["status"] == "delivered").sum()
)

canceled = int(
    filtered["status"].isin([
        "canceled_by_customer",
        "canceled_by_admin"
    ]).sum()
)

returned = int(
    filtered["status"].isin([
        "return_on_process",
        "returned_to_warehouse"
    ]).sum()
)

pending = int(
    filtered["status"].isin([
        "pending",
        "pending_customer_confirmation",
        "created"
    ]).sum()
)

delivery_rate = (
    delivered / total_orders * 100
    if total_orders
    else 0
)

total_amount = filtered["amount"].sum()

# ======================================================
# KPI DISPLAY
# ======================================================

st.subheader("📌 Business Overview")

k1, k2, k3, k4, k5, k6 = st.columns(6)

k1.metric("Total Orders", f"{total_orders:,}")
k2.metric("Delivered", f"{delivered:,}")
k3.metric("Canceled", f"{canceled:,}")
k4.metric("Returned", f"{returned:,}")
k5.metric("Pending", f"{pending:,}")
k6.metric("Delivery Rate", f"{delivery_rate:.1f}%")

st.metric("Total Order Amount", f"{total_amount:,.2f}")

# ======================================================
# PLOTLY THEME
# ======================================================

CHART_COLORS = [
    "#38BDF8",
    "#34D399",
    "#FBBF24",
    "#F87171",
    "#A78BFA",
    "#FB923C",
    "#2DD4BF",
    "#F472B6"
]

def style_chart(fig, height=380):
    fig.update_layout(
        template="plotly_dark",
        height=height,
        paper_bgcolor="#0B1120",
        plot_bgcolor="#111827",
        font=dict(
            family="Arial",
            color="#E5E7EB",
            size=12
        ),
        margin=dict(l=15, r=15, t=45, b=15),
        legend_title_text="",
        hoverlabel=dict(
            bgcolor="#172033",
            font_size=13
        )
    )

    fig.update_xaxes(
        gridcolor="#263449",
        zerolinecolor="#263449"
    )

    fig.update_yaxes(
        gridcolor="#263449",
        zerolinecolor="#263449"
    )

    return fig

# ======================================================
# ORDERS BY STATUS
# ======================================================

st.divider()
st.subheader("📦 Order Status Analysis")

status_data = (
    filtered["status_label"]
    .fillna("Unknown")
    .value_counts()
    .rename_axis("Status")
    .reset_index(name="Orders")
)

if not status_data.empty:

    fig_status = px.bar(
        status_data,
        x="Status",
        y="Orders",
        color="Status",
        color_discrete_sequence=CHART_COLORS,
        text="Orders",
        title="Orders by Status"
    )

    fig_status.update_traces(
        textposition="outside",
        marker_line_width=0
    )

    fig_status.update_layout(
        showlegend=False
    )

    st.plotly_chart(
        style_chart(fig_status),
        use_container_width=True
    )

# ======================================================
# DAILY TREND
# ======================================================

st.subheader("📈 Orders Trend")

daily = (
    filtered.dropna(subset=["date"])
    .groupby("date")
    .size()
    .reset_index(name="Orders")
    .sort_values("date")
)

if not daily.empty:

    fig_trend = px.line(
        daily,
        x="date",
        y="Orders",
        markers=True,
        title="Orders Created per Day",
        color_discrete_sequence=["#38BDF8"]
    )

    fig_trend.update_traces(
        line=dict(width=3),
        marker=dict(size=7)
    )

    st.plotly_chart(
        style_chart(fig_trend),
        use_container_width=True
    )

# ======================================================
# CITY & PRODUCT ANALYSIS
# ======================================================

left, right = st.columns(2)

with left:

    st.subheader("📍 Orders by City")

    city_data = (
        filtered["city"]
        .fillna("Unknown")
        .value_counts()
        .head(15)
        .rename_axis("City")
        .reset_index(name="Orders")
    )

    if not city_data.empty:

        fig_city = px.bar(
            city_data,
            x="Orders",
            y="City",
            orientation="h",
            text="Orders",
            color="Orders",
            color_continuous_scale="Blues",
            title="Top 15 Cities"
        )

        fig_city.update_layout(
            yaxis={"categoryorder": "total ascending"}
        )

        st.plotly_chart(
            style_chart(fig_city),
            use_container_width=True
        )

with right:

    st.subheader("🛍️ Top Products")

    if not filtered_items.empty:

        product_data = (
            filtered_items
            .groupby("product_name")["quantity"]
            .sum()
            .nlargest(15)
            .reset_index()
        )

        fig_products = px.bar(
            product_data,
            x="quantity",
            y="product_name",
            orientation="h",
            text="quantity",
            color="quantity",
            color_continuous_scale="Teal",
            title="Top 15 Products by Quantity"
        )

        fig_products.update_layout(
            yaxis={"categoryorder": "total ascending"}
        )

        st.plotly_chart(
            style_chart(fig_products),
            use_container_width=True
        )

    else:
        st.info("No product data available.")

# ======================================================
# CAMPAIGN PERFORMANCE
# ======================================================

st.divider()
st.subheader("🎯 Campaign Performance")

campaign_data = filtered.copy()

campaign_data["delivered_flag"] = (
    campaign_data["status"] == "delivered"
).astype(int)

campaign_data["canceled_flag"] = (
    campaign_data["status"].isin([
        "canceled_by_customer",
        "canceled_by_admin"
    ])
).astype(int)

campaign_data["returned_flag"] = (
    campaign_data["status"].isin([
        "return_on_process",
        "returned_to_warehouse"
    ])
).astype(int)

campaign_summary = (
    campaign_data
    .groupby("campaign", dropna=False)
    .agg(
        Orders=("order_uuid", "nunique"),
        Delivered=("delivered_flag", "sum"),
        Canceled=("canceled_flag", "sum"),
        Returned=("returned_flag", "sum"),
        Order_Amount=("amount", "sum")
    )
    .reset_index()
)

if not campaign_summary.empty:

    campaign_summary["Delivery_Rate_%"] = (
        campaign_summary["Delivered"]
        / campaign_summary["Orders"].replace(0, pd.NA)
        * 100
    ).fillna(0).round(2)

    campaign_summary = campaign_summary.sort_values(
        "Orders",
        ascending=False
    )

    campaign_left, campaign_right = st.columns(2)

    with campaign_left:

        fig_campaign_orders = px.bar(
            campaign_summary.head(20),
            x="campaign",
            y="Orders",
            color="Orders",
            text="Orders",
            color_continuous_scale="Blues",
            title="Top Campaigns by Order Count"
        )

        st.plotly_chart(
            style_chart(fig_campaign_orders),
            use_container_width=True
        )

    with campaign_right:

        fig_campaign_delivery = px.bar(
            campaign_summary.head(20),
            x="campaign",
            y="Delivery_Rate_%",
            color="Delivery_Rate_%",
            text="Delivery_Rate_%",
            color_continuous_scale="Teal",
            title="Campaign Delivery Rate (%)"
        )

        st.plotly_chart(
            style_chart(fig_campaign_delivery),
            use_container_width=True
        )

    st.markdown("#### Campaign Comparison Table")

    st.dataframe(
        campaign_summary,
        use_container_width=True,
        hide_index=True
    )

else:

    st.info("No campaign data available.")

# ======================================================
# PRODUCT PERFORMANCE TABLE
# ======================================================

st.divider()
st.subheader("🧾 Product Performance Table")

if not filtered_items.empty:

    product_performance = (
        filtered_items
        .groupby("product_name", dropna=False)
        .agg(
            Orders=("order_uuid", "nunique"),
            Quantity=("quantity", "sum"),
            Product_Total=("total", "sum")
        )
        .reset_index()
        .sort_values("Quantity", ascending=False)
    )

    st.dataframe(
        product_performance,
        use_container_width=True,
        hide_index=True
    )

# ======================================================
# ORDER DETAILS
# ======================================================

st.divider()
st.subheader("📋 Order Details")

display_columns = [
    "order_number",
    "status_label",
    "campaign",
    "amount",
    "amount_to_collect",
    "shipping_price",
    "payment_method",
    "customer_name",
    "customer_mobile",
    "city",
    "area",
    "created_at",
    "updated_at"
]

st.dataframe(
    filtered[display_columns].sort_values(
        "created_at",
        ascending=False,
        na_position="last"
    ),
    use_container_width=True,
    hide_index=True
)

# ======================================================
# SELECT AN ORDER
# ======================================================

st.subheader("🔎 Individual Order")

choices = filtered.dropna(
    subset=["order_number"]
).copy()

choices["order_number"] = choices["order_number"].astype(str)
choices = choices.drop_duplicates("order_number")

if not choices.empty:

    selected_number = st.selectbox(
        "Select Order Number",
        choices["order_number"].tolist()
    )

    selected = choices[
        choices["order_number"] == selected_number
    ].iloc[0]

    a, b = st.columns(2)

    with a:
        st.write("**Order:**", selected["order_number"])
        st.write("**Status:**", selected["status_label"])
        st.write("**Campaign:**", selected["campaign"])
        st.write("**Amount:**", selected["amount"])
        st.write("**Amount to Collect:**", selected["amount_to_collect"])

    with b:
        st.write("**Customer:**", selected["customer_name"])
        st.write("**Mobile:**", selected["customer_mobile"])
        st.write("**City:**", selected["city"])
        st.write("**Area:**", selected["area"])
        st.write("**Created At:**", str(selected["created_at"]))

    order_items = filtered_items[
        filtered_items["order_uuid"] == selected["order_uuid"]
    ]

    st.markdown("#### Products in this Order")

    if not order_items.empty:
        st.dataframe(
            order_items[
                ["product_name", "sku", "quantity", "price", "total"]
            ],
            use_container_width=True,
            hide_index=True
        )
    else:
        st.info("No products found for this order.")

else:
    st.info("No orders available for the current filters.")

# ======================================================
# FOOTER
# ======================================================

st.divider()
st.caption(
    "WeSell Analytics | Khaled Store | Built with Python & Streamlit"
)
