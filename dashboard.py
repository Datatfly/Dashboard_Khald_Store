import streamlit as st
import requests
import pandas as pd
from pathlib import Path


# =========================================================
# PAGE CONFIG
# =========================================================

st.set_page_config(
    page_title="WeSell Live Dashboard",
    page_icon="📊",
    layout="wide"
)


# =========================================================
# SETTINGS
# =========================================================

SUBDOMAIN = "khaled22"

BASE_URL = f"https://{SUBDOMAIN}.wesell.world/api/v1/orders"

API_KEY = "422|8T2SKD6Xpb8w4WfXPtLHZEVSKeB4RwLXB2JnYkA37a5bb893"

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Accept": "application/json"
}


# =========================================================
# LOAD FIRST 100 ORDERS ONLY
# =========================================================

@st.cache_data(ttl=300)
def load_data():

    response = requests.get(
        BASE_URL,
        headers=HEADERS,
        params={
            "page": 1,
            "per_page": 100
        },
        timeout=60
    )

    response.raise_for_status()

    result = response.json()

    orders = result.get("data", [])
    meta = result.get("meta", {})

    return orders, meta


# =========================================================
# HEADER
# =========================================================

st.title("📊 WeSell Live Dashboard")

st.caption(
    "Khaled Store | First 100 Orders | Daily Analysis"
)


# =========================================================
# API KEY CHECK
# =========================================================

if not API_KEY:

    st.error(
        "API Key is missing. Add API_KEY to "
        ".streamlit/secrets.toml"
    )

    st.stop()


# =========================================================
# REFRESH BUTTON
# =========================================================

col_refresh, col_info = st.columns([1, 5])

with col_refresh:

    if st.button(
        "🔄 Refresh Data",
        use_container_width=True
    ):

        load_data.clear()
        st.rerun()


with col_info:

    st.caption(
        "Data cache: 5 minutes. Refresh to fetch the latest first page."
    )


# =========================================================
# GET DATA
# =========================================================

try:

    with st.spinner("Loading first 100 orders..."):

        orders, meta = load_data()

except requests.RequestException as e:

    st.error(f"API connection error: {e}")
    st.stop()

except ValueError:

    st.error("The API returned an invalid JSON response.")
    st.stop()


if not orders:

    st.warning("No orders found.")
    st.stop()


st.success(
    f"Loaded {len(orders)} orders from page 1."
)


# =========================================================
# ORDERS DATAFRAME
# =========================================================

orders_rows = []

for order in orders:

    customer = order.get("customer") or {}
    address = order.get("address") or {}

    city = address.get("city") or {}
    area = address.get("area") or {}

    if not isinstance(city, dict):
        city = {}

    if not isinstance(area, dict):
        area = {}

    orders_rows.append({

        "order_uuid": order.get("uuid"),
        "order_number": order.get("order_number"),

        "status": order.get("status"),
        "status_label": order.get("status_label"),

        "payment_method": order.get("payment_method"),

        "amount": order.get("amount"),
        "amount_to_collect": order.get("amount_to_collect"),
        "deposit": order.get("deposit"),
        "shipping_price": order.get("shipping_price"),

        "shipping_method": order.get("shipping_method"),
        "tracking_number": order.get("tracking_number"),
        "reference_number": order.get("reference_number"),

        "customer_name": customer.get("name"),
        "customer_mobile": customer.get("mobile"),
        "customer_mobile2": customer.get("mobile2"),
        "customer_email": customer.get("email"),

        "street": address.get("street"),
        "city": city.get("name"),
        "area": area.get("name"),

        "no_answer_count": order.get("no_answer_count"),
        "delay_days": order.get("delay_days"),

        "created_at": order.get("created_at"),
        "updated_at": order.get("updated_at")
    })


orders_df = pd.DataFrame(orders_rows)


# =========================================================
# DATE PROCESSING
# =========================================================

orders_df["created_at"] = pd.to_datetime(
    orders_df["created_at"],
    errors="coerce",
    utc=True
)

orders_df["updated_at"] = pd.to_datetime(
    orders_df["updated_at"],
    errors="coerce",
    utc=True
)

# Convert timestamps to Egypt local time
orders_df["created_at"] = (
    orders_df["created_at"]
    .dt.tz_convert("Africa/Cairo")
)

orders_df["updated_at"] = (
    orders_df["updated_at"]
    .dt.tz_convert("Africa/Cairo")
)

orders_df["date"] = orders_df["created_at"].dt.date

orders_df["hour"] = orders_df["created_at"].dt.hour


# =========================================================
# NUMERIC COLUMNS
# =========================================================

numeric_columns = [
    "amount",
    "amount_to_collect",
    "deposit",
    "shipping_price",
    "no_answer_count",
    "delay_days"
]

for column in numeric_columns:

    orders_df[column] = pd.to_numeric(
        orders_df[column],
        errors="coerce"
    ).fillna(0)


# =========================================================
# ORDER ITEMS DATAFRAME
# =========================================================

items_rows = []

for order in orders:

    order_uuid = order.get("uuid")
    order_number = order.get("order_number")

    items = order.get("items") or []

    for item in items:

        items_rows.append({

            "order_uuid": order_uuid,
            "order_number": order_number,

            "product_uuid": item.get("product_uuid"),
            "product_name": item.get("product_name"),
            "sku": item.get("sku"),

            "quantity": item.get("quantity"),
            "price": item.get("price"),
            "total": item.get("total")
        })


items_df = pd.DataFrame(
    items_rows,
    columns=[
        "order_uuid",
        "order_number",
        "product_uuid",
        "product_name",
        "sku",
        "quantity",
        "price",
        "total"
    ]
)


# =========================================================
# ITEM NUMERIC COLUMNS
# =========================================================

for column in ["quantity", "price", "total"]:

    items_df[column] = pd.to_numeric(
        items_df[column],
        errors="coerce"
    ).fillna(0)


# =========================================================
# SIDEBAR FILTERS
# =========================================================

st.sidebar.header("🎛️ Filters")


# STATUS FILTER

status_options = sorted(
    orders_df["status_label"]
    .dropna()
    .unique()
    .tolist()
)

selected_status = st.sidebar.multiselect(
    "Order Status",
    options=status_options,
    default=[]
)


# CITY FILTER

city_options = sorted(
    orders_df["city"]
    .dropna()
    .unique()
    .tolist()
)

selected_city = st.sidebar.multiselect(
    "City",
    options=city_options,
    default=[]
)


# DAILY FILTER

available_dates = sorted(
    orders_df["date"].dropna().unique().tolist(),
    reverse=True
)

date_options = ["All Days"] + available_dates

selected_date = st.sidebar.selectbox(
    "📅 Select Day",
    options=date_options,
    format_func=lambda d: (
        d.strftime("%Y-%m-%d")
        if hasattr(d, "strftime")
        else d
    )
)


# =========================================================
# APPLY FILTERS
# =========================================================

filtered_orders = orders_df.copy()


# STATUS FILTER

if selected_status:

    filtered_orders = filtered_orders[
        filtered_orders["status_label"].isin(selected_status)
    ]


# CITY FILTER

if selected_city:

    filtered_orders = filtered_orders[
        filtered_orders["city"].isin(selected_city)
    ]


# DATE FILTER

if selected_date != "All Days":

    filtered_orders = filtered_orders[
        filtered_orders["date"] == selected_date
    ]


# =========================================================
# FILTER ITEMS USING FILTERED ORDERS
# =========================================================

filtered_order_ids = set(
    filtered_orders["order_uuid"].dropna()
)

filtered_items = items_df[
    items_df["order_uuid"].isin(filtered_order_ids)
].copy()


# =========================================================
# KPIs
# =========================================================

total_orders = len(filtered_orders)


delivered_orders = len(
    filtered_orders[
        filtered_orders["status"] == "delivered"
    ]
)


canceled_orders = len(
    filtered_orders[
        filtered_orders["status"].isin([
            "canceled_by_customer",
            "canceled_by_admin"
        ])
    ]
)


returned_orders = len(
    filtered_orders[
        filtered_orders["status"].isin([
            "return_on_process",
            "returned_to_warehouse"
        ])
    ]
)


pending_orders = len(
    filtered_orders[
        filtered_orders["status"].isin([
            "pending",
            "pending_customer_confirmation",
            "created"
        ])
    ]
)


delivery_rate = (
    delivered_orders / total_orders * 100
    if total_orders > 0
    else 0
)


total_amount = filtered_orders["amount"].sum()


# =========================================================
# KPI DISPLAY
# =========================================================

st.subheader("📌 Overview")

c1, c2, c3, c4, c5, c6 = st.columns(6)

c1.metric("Total Orders", f"{total_orders:,}")
c2.metric("Delivered", f"{delivered_orders:,}")
c3.metric("Canceled", f"{canceled_orders:,}")
c4.metric("Returned", f"{returned_orders:,}")
c5.metric("Pending", f"{pending_orders:,}")
c6.metric("Delivery Rate", f"{delivery_rate:.2f}%")


st.metric(
    "Total Order Amount",
    f"{total_amount:,.2f}"
)


# =========================================================
# ORDERS BY STATUS
# =========================================================

st.divider()

st.subheader("📦 Orders by Status")

status_chart = (
    filtered_orders["status_label"]
    .fillna("Unknown")
    .value_counts()
    .rename_axis("Status")
    .reset_index(name="Orders")
)

if not status_chart.empty:

    st.bar_chart(
        status_chart.set_index("Status")
    )

else:

    st.info("No status data for the selected filters.")


# =========================================================
# DAILY ORDERS TREND
# =========================================================

st.subheader("📈 Orders Trend")

daily_orders = (
    filtered_orders
    .dropna(subset=["date"])
    .groupby("date")
    .size()
    .rename("Orders")
    .reset_index()
)

if not daily_orders.empty:

    daily_orders["date"] = pd.to_datetime(
        daily_orders["date"]
    )

    daily_orders = daily_orders.set_index("date")

    st.line_chart(daily_orders["Orders"])

else:

    st.info("No orders for the selected date.")


# =========================================================
# CITY AND PRODUCT ANALYSIS
# =========================================================

col1, col2 = st.columns(2)


# CITY ANALYSIS

with col1:

    st.subheader("📍 Orders by City")

    city_chart = (
        filtered_orders["city"]
        .fillna("Unknown")
        .value_counts()
        .head(15)
    )

    if not city_chart.empty:

        st.bar_chart(city_chart)

    else:

        st.info("No city data available.")


# PRODUCT ANALYSIS

with col2:

    st.subheader("🛍️ Top Products")

    if not filtered_items.empty:

        product_chart = (
            filtered_items
            .groupby("product_name")["quantity"]
            .sum()
            .sort_values(ascending=False)
            .head(15)
        )

        st.bar_chart(product_chart)

    else:

        st.info("No product data available.")


# =========================================================
# PRODUCT PERFORMANCE TABLE
# =========================================================

st.divider()

st.subheader("🛍️ Product Performance")

if not filtered_items.empty:

    product_performance = (
        filtered_items
        .groupby(
            ["product_uuid", "product_name", "sku"],
            dropna=False
        )
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

else:

    st.info("No product performance data available.")


# =========================================================
# ORDER DETAILS TABLE
# =========================================================

st.divider()

st.subheader("📋 Order Details")

display_columns = [
    "order_number",
    "status_label",
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
    filtered_orders[display_columns].sort_values(
        "created_at",
        ascending=False,
        na_position="last"
    ),
    use_container_width=True,
    hide_index=True
)


# =========================================================
# SELECT ORDER
# =========================================================

st.divider()

st.subheader("🔎 Order Details")

order_choices = filtered_orders.dropna(
    subset=["order_number"]
).copy()

if not order_choices.empty:

    order_choices["order_number"] = (
        order_choices["order_number"].astype(str)
    )

    order_choices = order_choices.drop_duplicates(
        subset=["order_number"]
    )

    selected_order = st.selectbox(
        "Select Order",
        options=order_choices["order_number"].tolist()
    )

    selected_order_row = order_choices[
        order_choices["order_number"] == selected_order
    ].iloc[0]

    detail_col1, detail_col2 = st.columns(2)

    with detail_col1:

        st.write("**Order Number:**", selected_order_row["order_number"])
        st.write("**Status:**", selected_order_row["status_label"])
        st.write("**Amount:**", selected_order_row["amount"])
        st.write("**Amount to Collect:**", selected_order_row["amount_to_collect"])
        st.write("**Shipping:**", selected_order_row["shipping_price"])
        st.write("**Payment Method:**", selected_order_row["payment_method"])

    with detail_col2:

        st.write("**Customer:**", selected_order_row["customer_name"])
        st.write("**Mobile:**", selected_order_row["customer_mobile"])
        st.write("**City:**", selected_order_row["city"])
        st.write("**Area:**", selected_order_row["area"])
        st.write("**Created At:**", str(selected_order_row["created_at"]))
        st.write("**Updated At:**", str(selected_order_row["updated_at"]))

    # PRODUCTS IN SELECTED ORDER

    selected_uuid = selected_order_row["order_uuid"]

    order_items = filtered_items[
        filtered_items["order_uuid"] == selected_uuid
    ]

    st.write("### Products in this Order")

    if not order_items.empty:

        st.dataframe(
            order_items[
                [
                    "product_name",
                    "sku",
                    "quantity",
                    "price",
                    "total"
                ]
            ],
            use_container_width=True,
            hide_index=True
        )

    else:

        st.info("No products found for this order.")

else:

    st.info("No orders available for the selected filters.")


# =========================================================
# FOOTER
# =========================================================

st.divider()

st.caption("BY Eng/Abdulraman Mohamed")
