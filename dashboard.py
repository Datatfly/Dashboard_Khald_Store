import streamlit as st
import requests
import pandas as pd
from datetime import datetime


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

API_KEY = "422|8T2SKD6Xpb8w4WfXPtLHZEVSKeB4RwLXB2JnYkA37a5bb893"

BASE_URL = f"https://{SUBDOMAIN}.wesell.world/api/v1/orders"

HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Accept": "application/json"
}


# =========================================================
# FUNCTIONS
# =========================================================

def get_orders_from_api(per_page=100):

    all_orders = []

    page = 1

    progress = st.progress(0)

    status_text = st.empty()

    while True:

        response = requests.get(
            BASE_URL,
            headers=HEADERS,
            params={
                "page": page,
                "per_page": per_page
            },
            timeout=60
        )

        if response.status_code != 200:

            st.error(
                f"API Error on page {page}: "
                f"{response.status_code}"
            )

            st.stop()

        result = response.json()

        orders = result.get("data", [])

        meta = result.get("meta", {})

        all_orders.extend(orders)

        last_page = meta.get("last_page", page)

        status_text.text(
            f"Loading orders... Page {page} / {last_page}"
        )

        progress.progress(
            min(page / last_page, 1.0)
        )

        if page >= last_page:
            break

        page += 1

    progress.empty()
    status_text.empty()

    return all_orders, meta


# =========================================================
# CACHE
# =========================================================

@st.cache_data(ttl=300)
def load_data():

    orders, meta = get_orders_from_api(
        per_page=100
    )

    return orders, meta


# =========================================================
# LOAD DATA
# =========================================================

st.title("📊 WeSell Live Dashboard")

st.caption(
    "Live data from WeSell SKhaled Store API"
)


# =========================================================
# REFRESH BUTTON
# =========================================================

col1, col2 = st.columns([1, 5])

with col1:

    if st.button(
        "🔄 Refresh Data",
        use_container_width=True
    ):

        st.cache_data.clear()

        st.rerun()


# =========================================================
# GET DATA
# =========================================================

orders, meta = load_data()


if not orders:

    st.warning("No orders found.")

    st.stop()


# =========================================================
# ORDERS DATAFRAME
# =========================================================

orders_rows = []


for order in orders:

    customer = order.get("customer") or {}

    address = order.get("address") or {}

    city = address.get("city") or {}

    area = address.get("area") or {}

    orders_rows.append({

        "order_uuid":
            order.get("uuid"),

        "order_number":
            order.get("order_number"),

        "status":
            order.get("status"),

        "status_label":
            order.get("status_label"),

        "payment_method":
            order.get("payment_method"),

        "amount":
            order.get("amount"),

        "amount_to_collect":
            order.get("amount_to_collect"),

        "deposit":
            order.get("deposit"),

        "shipping_price":
            order.get("shipping_price"),

        "shipping_method":
            order.get("shipping_method"),

        "tracking_number":
            order.get("tracking_number"),

        "reference_number":
            order.get("reference_number"),

        "customer_name":
            customer.get("name"),

        "customer_mobile":
            customer.get("mobile"),

        "customer_mobile2":
            customer.get("mobile2"),

        "customer_email":
            customer.get("email"),

        "street":
            address.get("street"),

        "city":
            city.get("name"),

        "area":
            area.get("name"),

        "no_answer_count":
            order.get("no_answer_count"),

        "delay_days":
            order.get("delay_days"),

        "created_at":
            order.get("created_at"),

        "updated_at":
            order.get("updated_at")
    })


orders_df = pd.DataFrame(orders_rows)


# =========================================================
# DATE PROCESSING
# =========================================================

orders_df["created_at"] = pd.to_datetime(
    orders_df["created_at"],
    errors="coerce"
)

orders_df["updated_at"] = pd.to_datetime(
    orders_df["updated_at"],
    errors="coerce"
)


orders_df["date"] = (
    orders_df["created_at"]
    .dt.date
)


orders_df["hour"] = (
    orders_df["created_at"]
    .dt.hour
)


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

    order_number = order.get(
        "order_number"
    )

    items = order.get("items") or []


    for item in items:

        items_rows.append({

            "order_uuid":
                order_uuid,

            "order_number":
                order_number,

            "product_uuid":
                item.get("product_uuid"),

            "product_name":
                item.get("product_name"),

            "sku":
                item.get("sku"),

            "quantity":
                item.get("quantity"),

            "price":
                item.get("price"),

            "total":
                item.get("total")
        })


items_df = pd.DataFrame(items_rows)


# =========================================================
# ITEM NUMERIC COLUMNS
# =========================================================

if not items_df.empty:

    items_df["quantity"] = pd.to_numeric(
        items_df["quantity"],
        errors="coerce"
    ).fillna(0)

    items_df["price"] = pd.to_numeric(
        items_df["price"],
        errors="coerce"
    ).fillna(0)

    items_df["total"] = pd.to_numeric(
        items_df["total"],
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
)


selected_status = st.sidebar.multiselect(
    "Order Status",
    status_options,
    default=[]
)


# CITY FILTER

city_options = sorted(
    orders_df["city"]
    .dropna()
    .unique()
)


selected_city = st.sidebar.multiselect(
    "City",
    city_options,
    default=[]
)


# DATE FILTER

min_date = orders_df["date"].min()

max_date = orders_df["date"].max()


date_range = st.sidebar.date_input(
    "Date Range",
    value=(min_date, max_date),
    min_value=min_date,
    max_value=max_date
)


# =========================================================
# APPLY FILTERS
# =========================================================

filtered_orders = orders_df.copy()


if selected_status:

    filtered_orders = filtered_orders[
        filtered_orders["status_label"]
        .isin(selected_status)
    ]


if selected_city:

    filtered_orders = filtered_orders[
        filtered_orders["city"]
        .isin(selected_city)
    ]


if len(date_range) == 2:

    start_date = date_range[0]

    end_date = date_range[1]

    filtered_orders = filtered_orders[
        (
            filtered_orders["date"]
            >= start_date
        )
        &
        (
            filtered_orders["date"]
            <= end_date
        )
    ]


# =========================================================
# FILTERED ORDER IDS
# =========================================================

filtered_order_ids = set(
    filtered_orders["order_uuid"]
)


if not items_df.empty:

    filtered_items = items_df[
        items_df["order_uuid"]
        .isin(filtered_order_ids)
    ].copy()

else:

    filtered_items = items_df.copy()


# =========================================================
# KPIs
# =========================================================

total_orders = len(filtered_orders)


delivered_orders = len(
    filtered_orders[
        filtered_orders["status"]
        == "delivered"
    ]
)


canceled_orders = len(
    filtered_orders[
        filtered_orders["status"]
        .isin([
            "canceled_by_customer",
            "canceled_by_admin"
        ])
    ]
)


returned_orders = len(
    filtered_orders[
        filtered_orders["status"]
        .isin([
            "return_on_process",
            "returned_to_warehouse"
        ])
    ]
)


pending_orders = len(
    filtered_orders[
        filtered_orders["status"]
        .isin([
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


# =========================================================
# KPI DISPLAY
# =========================================================

st.subheader("📌 Overview")


c1, c2, c3, c4, c5, c6 = st.columns(6)


with c1:

    st.metric(
        "Total Orders",
        f"{total_orders:,}"
    )


with c2:

    st.metric(
        "Delivered",
        f"{delivered_orders:,}"
    )


with c3:

    st.metric(
        "Canceled",
        f"{canceled_orders:,}"
    )


with c4:

    st.metric(
        "Returned",
        f"{returned_orders:,}"
    )


with c5:

    st.metric(
        "Pending",
        f"{pending_orders:,}"
    )


with c6:

    st.metric(
        "Delivery Rate",
        f"{delivery_rate:.2f}%"
    )


# =========================================================
# ORDER STATUS
# =========================================================

st.divider()

st.subheader("📦 Orders by Status")


status_chart = (

    filtered_orders[
        "status_label"
    ]
    .value_counts()
    .rename_axis("Status")
    .reset_index(name="Orders")

)


st.bar_chart(
    status_chart.set_index("Status")
)


# =========================================================
# ORDERS TREND
# =========================================================

st.subheader("📈 Orders Trend")


daily_orders = (

    filtered_orders
    .groupby("date")
    .size()
    .rename("Orders")
    .reset_index()

)


if not daily_orders.empty:

    daily_orders["date"] = pd.to_datetime(
        daily_orders["date"]
    )

    daily_orders = daily_orders.set_index(
        "date"
    )

    st.line_chart(
        daily_orders["Orders"]
    )


# =========================================================
# TWO COLUMNS
# =========================================================

col1, col2 = st.columns(2)


# =========================================================
# CITY ANALYSIS
# =========================================================

with col1:

    st.subheader("📍 Orders by City")


    city_chart = (

        filtered_orders["city"]
        .fillna("Unknown")
        .value_counts()
        .head(15)
        .rename_axis("City")
        .reset_index(name="Orders")

    )


    st.bar_chart(
        city_chart.set_index("City")
    )


# =========================================================
# PRODUCT ANALYSIS
# =========================================================

with col2:

    st.subheader("🛍️ Top Products")


    if not filtered_items.empty:

        product_chart = (

            filtered_items
            .groupby("product_name")["quantity"]
            .sum()
            .sort_values(
                ascending=False
            )
            .head(15)

        )


        st.bar_chart(
            product_chart
        )

    else:

        st.info(
            "No product data available."
        )


# =========================================================
# PRODUCT TABLE
# =========================================================

st.divider()

st.subheader("🛍️ Product Performance")


if not filtered_items.empty:

    product_performance = (

        filtered_items
        .groupby(
            [
                "product_uuid",
                "product_name",
                "sku"
            ],
            dropna=False
        )
        .agg(
            Orders=(
                "order_uuid",
                "nunique"
            ),
            Quantity=(
                "quantity",
                "sum"
            ),
            Product_Total=(
                "total",
                "sum"
            )
        )
        .reset_index()
        .sort_values(
            "Quantity",
            ascending=False
        )

    )


    st.dataframe(
        product_performance,
        use_container_width=True,
        hide_index=True
    )


# =========================================================
# ORDER DETAILS
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


display_columns = [

    column

    for column in display_columns

    if column in filtered_orders.columns

]


st.dataframe(
    filtered_orders[
        display_columns
    ].sort_values(
        "created_at",
        ascending=False
    ),
    use_container_width=True,
    hide_index=True
)


# =========================================================
# SELECT ORDER
# =========================================================

st.divider()

st.subheader("🔎 Order Details")


order_numbers = (

    filtered_orders[
        "order_number"
    ]
    .dropna()
    .tolist()

)


if order_numbers:

    selected_order = st.selectbox(
        "Select Order",
        order_numbers
    )


    selected_order_row = filtered_orders[
        filtered_orders["order_number"]
        == selected_order
    ].iloc[0]


    detail_col1, detail_col2 = st.columns(2)


    with detail_col1:

        st.write(
            "**Order Number:**",
            selected_order_row[
                "order_number"
            ]
        )

        st.write(
            "**Status:**",
            selected_order_row[
                "status_label"
            ]
        )

        st.write(
            "**Amount:**",
            selected_order_row[
                "amount"
            ]
        )

        st.write(
            "**Amount to Collect:**",
            selected_order_row[
                "amount_to_collect"
            ]
        )

        st.write(
            "**Shipping:**",
            selected_order_row[
                "shipping_price"
            ]
        )


    with detail_col2:

        st.write(
            "**City:**",
            selected_order_row[
                "city"
            ]
        )

        st.write(
            "**Area:**",
            selected_order_row[
                "area"
            ]
        )

        st.write(
            "**Created At:**",
            selected_order_row[
                "created_at"
            ]
        )

        st.write(
            "**Updated At:**",
            selected_order_row[
                "updated_at"
            ]
        )


    # ---------------------------------------------
    # ORDER ITEMS
    # ---------------------------------------------

    selected_uuid = selected_order_row[
        "order_uuid"
    ]


    order_items = filtered_items[
        filtered_items["order_uuid"]
        == selected_uuid
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


# =========================================================
# FOOTER
# =========================================================

st.divider()

st.caption(
    
    f"BY Eng/Abdulraman Mohamed"
)