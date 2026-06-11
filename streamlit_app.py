import streamlit as st
import pandas as pd
import altair as alt
import sqlite3
import requests
from datetime import datetime, timedelta
import base64

st.set_page_config(page_title="POS Demo", layout="wide")

# ---------------------------------------------------------
# DATABASE SETUP
# ---------------------------------------------------------
conn = sqlite3.connect("inventory.db", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS inventory (
    id INTEGER PRIMARY KEY AUTOINCREMENT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS sales (
    id INTEGER PRIMARY KEY AUTOINCREMENT
)
""")

# ---------------------------------------------------------
# AUTO-MIGRATION: INVENTORY
# ---------------------------------------------------------
cursor.execute("PRAGMA table_info(inventory)")
inv_cols = [col[1] for col in cursor.fetchall()]

inv_required = {
    "item": "TEXT DEFAULT ''",
    "price": "REAL DEFAULT 0",
    "cost": "REAL DEFAULT 0",
    "stock": "INTEGER DEFAULT 0",
    "image": "TEXT DEFAULT 'https://via.placeholder.com/70'",
    "category": "TEXT DEFAULT 'General'",
    "barcode": "TEXT DEFAULT ''"
}

for col, col_type in inv_required.items():
    if col not in inv_cols:
        cursor.execute(f"ALTER TABLE inventory ADD COLUMN {col} {col_type}")
        conn.commit()

# ---------------------------------------------------------
# AUTO-MIGRATION: SALES
# ---------------------------------------------------------
cursor.execute("PRAGMA table_info(sales)")
sales_cols = [col[1] for col in cursor.fetchall()]

sales_required = {
    "date": "TEXT",
    "item": "TEXT",
    "qty": "INTEGER",
    "total": "REAL",
    "cost": "REAL",
    "profit": "REAL"
}

for col, col_type in sales_required.items():
    if col not in sales_cols:
        cursor.execute(f"ALTER TABLE sales ADD COLUMN {col} {col_type}")
        conn.commit()

# ---------------------------------------------------------
# IMAGE HELPERS
# ---------------------------------------------------------
def fetch_image(query: str) -> str:
    try:
        url = f"https://duckduckgo.com/i.js?q={query.replace(' ', '+')}"
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers).json()
        return res["results"][0]["image"]
    except:
        return "https://via.placeholder.com/70"

def file_to_data_url(file) -> str:
    data = file.read()
    b64 = base64.b64encode(data).decode("utf-8")
    return f"data:image/png;base64,{b64}"

# ---------------------------------------------------------
# LOADERS
# ---------------------------------------------------------
def load_inventory():
    return pd.read_sql("SELECT * FROM inventory", conn)

def load_sales():
    return pd.read_sql("SELECT * FROM sales", conn)

# ---------------------------------------------------------
# SAVE / UPDATE
# ---------------------------------------------------------
def save_inventory(item, price, cost, stock, image, category, barcode):
    cursor.execute(
        "INSERT INTO inventory (item, price, cost, stock, image, category, barcode) VALUES (?, ?, ?, ?, ?, ?, ?)",
        (item, price, cost, stock, image, category, barcode),
    )
    conn.commit()

def update_stock(item, qty):
    cursor.execute("UPDATE inventory SET stock = stock - ? WHERE item = ?", (qty, item))
    conn.commit()

def save_sale(item, qty, total, cost, profit):
    cursor.execute(
        "INSERT INTO sales (date, item, qty, total, cost, profit) VALUES (?, ?, ?, ?, ?, ?)",
        (datetime.now().isoformat(), item, qty, total, cost, profit),
    )
    conn.commit()

# ---------------------------------------------------------
# SIMPLE PDF GENERATOR (NO EXTERNAL LIBS)
# ---------------------------------------------------------
def generate_pdf(filtered: pd.DataFrame, metrics: dict) -> bytes:
    text = "Sales Report\n\n"
    for label, value in metrics.items():
        text += f"{label}: {value}\n"
    text += "\nSales Details:\n"
    for _, row in filtered.iterrows():
        line = f"{row['date']} | {row['item']} | Qty: {row['qty']} | Total: ${row['total']:.2f}"
        text += line + "\n"

    pdf = f"""%PDF-1.4
1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj
2 0 obj << /Type /Pages /Kids [3 0 R] /Count 1 >> endobj
3 0 obj << /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792]
/Contents 4 0 R /Resources << >> >> endobj
4 0 obj << /Length {len(text)+50} >> stream
BT /F1 12 Tf 50 750 Td ({text.replace('(', '[').replace(')', ']')}) Tj ET
endstream endobj
xref
0 5
0000000000 65535 f 
0000000010 00000 n 
0000000060 00000 n 
0000000110 00000 n 
0000000200 00000 n 
trailer << /Size 5 /Root 1 0 R >>
startxref
300
%%EOF
"""
    return pdf.encode("latin1")

# ---------------------------------------------------------
# CSS THEME
# ---------------------------------------------------------
st.markdown("""
<style>
body { background-color: #ECECEC; }
.big-title { font-size: 42px; font-weight: 800; text-align: center; padding: 15px; color: #333; }
.section-title { font-size: 24px; font-weight: 700; margin-top: 20px; color: #444; }
.item-card { background: #F7F7F7; padding: 18px; border-radius: 12px; border: 1px solid #CCC; transition: 0.2s; text-align: center; }
.item-card:hover { border-color: #666; box-shadow: 0px 4px 12px rgba(0,0,0,0.08); }
.receipt-box { background: #FAFAFA; padding: 20px; border-radius: 0px; border: none; }
</style>
""", unsafe_allow_html=True)

# ---------------------------------------------------------
# LOGIN
# ---------------------------------------------------------
if "role" not in st.session_state:
    st.session_state.role = None

st.markdown('<div class="big-title">🛒 Convenience Store POS Demo</div>', unsafe_allow_html=True)

if st.session_state.role is None:
    st.subheader("Login")

    col1, col2 = st.columns(2)
    with col1:
        role = st.selectbox("Role", ["Cashier", "Admin"])
    with col2:
        password = st.text_input("Password", type="password")

    if st.button("Login"):
        if role == "Admin" and password == "admin123":
            st.session_state.role = "Admin"
        elif role == "Cashier" and password == "cashier123":
            st.session_state.role = "Cashier"
        else:
            st.error("Invalid credentials.")

    st.markdown("""
    <br><br>
    <small>
    <b>Demo Credentials:</b><br>
    Admin → <code>admin123</code><br>
    Cashier → <code>cashier123</code>
    </small>
    """, unsafe_allow_html=True)

    st.stop()

st.write(f"**Logged in as:** {st.session_state.role}")
if st.button("Logout"):
    st.session_state.role = None
    st.experimental_rerun()

# ---------------------------------------------------------
# TABS
# ---------------------------------------------------------
tab1, tab2, tab3 = st.tabs(["🧾 Cashier (POS)", "📦 Inventory", "📊 Sales Report"])

# ---------------------------------------------------------
# TAB 1 — CASHIER POS
# ---------------------------------------------------------
with tab1:
    st.markdown('<div class="section-title">🛍️ Select Products</div>', unsafe_allow_html=True)

    inventory = load_inventory()

    if inventory.empty:
        st.warning("No inventory yet. Add items in the Inventory tab.")
    else:
        categories = ["All"] + sorted(inventory["category"].unique().tolist())
        selected_cat = st.selectbox("Filter by Category", categories)
        if selected_cat != "All":
            inventory = inventory[inventory["category"] == selected_cat]

        barcode_input = st.text_input("Scan or enter barcode")
        if barcode_input:
            match = inventory[inventory["barcode"] == barcode_input]
            if not match.empty:
                st.success(f"Found: {match.iloc[0]['item']}")

        cols = st.columns(3)
        selected_items = []
        quantities = {}

        for idx, (_, row) in enumerate(inventory.iterrows()):
            col = cols[idx % 3]
            with col:
                st.markdown(f"""
                <div class="item-card">
                    <img src="{row['image']}" style="width:70px; height:70px; object-fit:contain;">
                    <strong>{row['item']}</strong><br>
                    <span>${row['price']:.2f}</span><br>
                    <small>Stock: {row['stock']}</small><br>
                    <small>Category: {row['category']}</small>
                </div>
                """, unsafe_allow_html=True)

                qty = st.number_input(
                    f"Qty ({row['item']})",
                    min_value=0,
                    max_value=int(row["stock"]),
                    key=f"qty_{idx}",
                )
                if qty > 0:
                    selected_items.append(row)
                    quantities[row["item"]] = qty

        st.markdown('<div class="section-title">🧾 Receipt</div>', unsafe_allow_html=True)

        with st.container():
            st.markdown('<div class="receipt-box">', unsafe_allow_html=True)

            if not selected_items:
                st.info("No items selected.")
            else:
                total = 0
                total_cost = 0

                for item in selected_items:
                    qty = quantities[item["item"]]
                    line_total = qty * item["price"]
                    line_cost = qty * item["cost"]
                    total += line_total
                    total_cost += line_cost
                    st.write(f"**{item['item']}** × {qty} — ${line_total:.2f}")

                profit = total - total_cost

                st.write(f"### Revenue: ${total:.2f}")
                st.write(f"### Cost: ${total_cost:.2f}")
                st.write(f"### Profit: ${profit:.2f}")

                if st.button("Complete Transaction"):
                    for item in selected_items:
                        update_stock(item["item"], quantities[item["item"]])
                        save_sale(
                            item["item"],
                            quantities[item["item"]],
                            quantities[item["item"]] * item["price"],
                            quantities[item["item"]] * item["cost"],
                            quantities[item["item"]] * item["price"] - quantities[item["item"]] * item["cost"],
                        )
                    st.success("Transaction saved!")

            st.markdown("</div>", unsafe_allow_html=True)

# ---------------------------------------------------------
# TAB 2 — INVENTORY (ADMIN ONLY, CLICK TO EDIT)
# ---------------------------------------------------------
with tab2:
    if st.session_state.role != "Admin":
        st.warning("Admin only.")
    else:
        st.markdown('<div class="section-title">📦 Inventory</div>', unsafe_allow_html=True)

        inv = load_inventory()

        if inv.empty:
            st.info("No inventory yet.")
        else:
            st.write("### Inventory Table (select row to edit)")

            inv_display = inv.copy()
            inv_display["select"] = False

            edited = st.data_editor(
                inv_display,
                hide_index=True,
                column_config={
                    "image": st.column_config.ImageColumn("Image", width="small"),
                    "select": st.column_config.CheckboxColumn("Select"),
                },
                disabled=["id"],
                use_container_width=True
            )

            selected_rows = edited[edited["select"] == True]

            st.markdown("---")
            st.write("### ✏️ Edit Selected Item")

            if selected_rows.empty:
                st.info("Select a row above to load it into the editor.")
            else:
                row = selected_rows.iloc[0]

                new_name = st.text_input("Item Name", value=row["item"])
                new_price = st.number_input("Price", value=float(row["price"]))
                new_cost = st.number_input("Cost", value=float(row["cost"]))
                new_stock = st.number_input("Stock", value=int(row["stock"]))
                new_category = st.text_input("Category", value=row["category"])
                new_barcode = st.text_input("Barcode", value=row["barcode"])

                st.write("#### Image Options")
                uploaded_edit_img = st.file_uploader("Upload new image", type=["png", "jpg", "jpeg"])
                manual_edit_url = st.text_input("Image URL", value=row["image"])
                delete_image = st.checkbox("Delete image (use placeholder)")

                if st.button("Save Changes"):
                    if delete_image:
                        final_img = "https://via.placeholder.com/70"
                    elif uploaded_edit_img:
                        final_img = file_to_data_url(uploaded_edit_img)
                    else:
                        final_img = manual_edit_url.strip() or "https://via.placeholder.com/70"

                    cursor.execute("""
                        UPDATE inventory
                        SET item=?, price=?, cost=?, stock=?, image=?, category=?, barcode=?
                        WHERE id=?
                    """, (new_name, new_price, new_cost, new_stock, final_img, new_category, new_barcode, int(row["id"])))
                    conn.commit()

                    st.success("Item updated successfully!")
                    st.experimental_rerun()

        st.markdown("---")
        st.write("### ➕ Add New Item")

        new_item = st.text_input("New Item Name")
        new_price = st.number_input("New Price", min_value=0.0)
        new_cost = st.number_input("New Cost", min_value=0.0)
        new_stock = st.number_input("New Stock", min_value=0)
        new_category = st.text_input("New Category", value="General")
        new_barcode = st.text_input("New Barcode (optional)")

        manual_image_url = st.text_input("New Image URL (optional)")
        uploaded_image = st.file_uploader("Upload New Image (optional)", type=["png", "jpg", "jpeg"])

        if st.button("Fetch Image Automatically"):
            if new_item.strip():
                img_url = fetch_image(new_item)
                st.image(img_url, width=100)
                st.session_state["new_image"] = img_url
            else:
                st.warning("Enter item name first.")

        if st.button("Add Item"):
            img = "https://via.placeholder.com/70"
            if uploaded_image is not None:
                img = file_to_data_url(uploaded_image)
            elif manual_image_url.strip():
                img = manual_image_url.strip()
            else:
                img = st.session_state.get("new_image", img)

            save_inventory(new_item, new_price, new_cost, new_stock, img, new_category, new_barcode)
            st.success("Item saved to database!")
            st.experimental_rerun()

# ---------------------------------------------------------
# TAB 3 — SALES REPORT
# ---------------------------------------------------------
with tab3:
    st.markdown('<div class="section-title">📊 Sales Report</div>', unsafe_allow_html=True)

    sales = load_sales()

    if sales.empty:
        st.info("No sales yet.")
    else:
        sales["date"] = pd.to_datetime(sales["date"], errors="coerce")

        start_date = st.date_input("Start Date", datetime.now() - timedelta(days=7))
        end_date = st.date_input("End Date", datetime.now())

        filtered = sales[
            (sales["date"].dt.date >= start_date)
            & (sales["date"].dt.date <= end_date)
        ]

        total_revenue = filtered["total"].sum()
        total_cost = filtered["cost"].sum()
        total_profit = filtered["profit"].sum()
        total_items = filtered["qty"].sum()
        total_stock = load_inventory()["stock"].sum()

        colA, colB, colC, colD, colE = st.columns(5)
        colA.metric("Revenue", f"${total_revenue:.2f}")
        colB.metric("Cost", f"${total_cost:.2f}")
        colC.metric("Profit", f"${total_profit:.2f}")
        colD.metric("Items Sold", int(total_items))
        colE.metric("Stock Left", int(total_stock))

        st.markdown("### Sales Table")
        st.dataframe(filtered, use_container_width=True)

        if not filtered.empty:
            st.markdown("### Revenue Over Time")
            rev_chart = (
                alt.Chart(filtered)
                .mark_line(point=True)
                .encode(
                    x="date:T",
                    y="total:Q",
                    tooltip=["date:T", "total:Q"],
                )
            )
            st.altair_chart(rev_chart, use_container_width=True)

        st.markdown("### Export PDF")
        metrics = {
            "Revenue": f"${total_revenue:.2f}",
            "Cost": f"${total_cost:.2f}",
            "Profit": f"${total_profit:.2f}",
            "Items Sold": int(total_items),
            "Stock Left": int(total_stock),
        }
        pdf_bytes = generate_pdf(filtered, metrics)
        st.download_button(
            "Download Sales Report PDF",
            data=pdf_bytes,
            file_name="sales_report.pdf",
            mime="application/pdf",
        )
