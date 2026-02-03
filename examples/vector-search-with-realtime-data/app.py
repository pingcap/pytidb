#!/usr/bin/env python3
"""
Vector Search with Real-time Data Demo

This example demonstrates TiDB's vector search capabilities with real-time data updates,
simulating an e-commerce recommendation system based on user preferences.
"""

import os
from typing import List, Dict, Any

import dotenv
import textwrap
import streamlit as st

from pytidb import Table, TiDBClient
from pytidb.schema import TableModel, Field
from pytidb.embeddings import EmbeddingFunction
from pytidb.datatype import TEXT

# Load environment variables
dotenv.load_dotenv()

# Page configuration
st.set_page_config(
    page_title="Vector Search with Real-time Data",
    page_icon="🛍️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize session state
if "db" not in st.session_state:
    st.session_state.db = None
if "embed_func" not in st.session_state:
    st.session_state.embed_func = None
if "table" not in st.session_state:
    st.session_state.table = None
if "user_profile" not in st.session_state:
    st.session_state.user_profile = None
if "edit_mode" not in st.session_state:
    st.session_state.edit_mode = {}


def connect_to_tidb() -> TiDBClient:
    """Connect to TiDB database"""
    try:
        db = TiDBClient.connect(
            host=os.getenv("TIDB_HOST", "localhost"),
            port=int(os.getenv("TIDB_PORT", "4000")),
            username=os.getenv("TIDB_USERNAME", "root"),
            password=os.getenv("TIDB_PASSWORD", ""),
            database=os.getenv("TIDB_DATABASE", "vector_search_realtime"),
            ensure_db=True,
        )
        return db
    except Exception as e:
        st.error(f"Failed to connect to TiDB: {str(e)}")
        st.stop()


def setup_embedding_function(db: TiDBClient) -> EmbeddingFunction:
    """Setup embedding function for text vectorization"""
    try:
        # Configure OpenAI provider
        db.configure_embedding_provider(
            provider="openai",
            api_key=os.getenv("OPENAI_API_KEY"),
        )

        # Use OpenAI embedding model
        embed_func = EmbeddingFunction(
            model_name="openai/text-embedding-3-small",
        )
        return embed_func
    except Exception as e:
        st.error(f"Failed to setup embedding function: {str(e)}")
        st.stop()


def setup_table(db: TiDBClient, embed_func: EmbeddingFunction) -> Table:
    """Setup or open products table"""
    try:
        # Try to open existing table
        table = db.open_table("products")

        if table is None:
            # Define table schema
            class Product(TableModel):
                __tablename__ = "products"

                id: int = Field(primary_key=True)
                name: str = Field(sa_type=TEXT)
                description: str = Field(sa_type=TEXT)
                description_vec: list[float] = embed_func.VectorField(
                    source_field="description"
                )
                category: str = Field(sa_type=TEXT)
                price: float = Field()

            # Create table
            table = db.create_table(schema=Product, if_exists="overwrite")

        return table
    except Exception as e:
        st.error(f"Failed to setup table: {str(e)}")
        st.stop()


def load_initial_data(table: Table):
    """Load initial sample products (3 sports items + 2 unrelated items)"""

    # Check if table already has data
    if table.rows() > 0:
        return

    Product = table.table_model

    initial_products = [
        # Sports-related items (should match user profile "a user likes sports")
        Product(
            name="Professional Basketball",
            description="High-quality basketball for professional and amateur players. Perfect for indoor and outdoor courts. Official size and weight.",
            category="Sports",
            price=29.99,
        ),
        Product(
            name="Running Shoes",
            description="Lightweight running shoes with excellent cushioning and support. Ideal for marathon training and daily jogging.",
            category="Sports",
            price=89.99,
        ),
        Product(
            name="Yoga Mat",
            description="Premium non-slip yoga mat for fitness, exercise, and meditation. Extra thick for comfort during workouts.",
            category="Sports",
            price=24.99,
        ),
        # Unrelated items (should NOT match user profile)
        Product(
            name="Cooking Pot Set",
            description="Stainless steel cooking pot set with non-stick coating. Perfect for preparing delicious meals and soups in your kitchen.",
            category="Kitchen",
            price=79.99,
        ),
        Product(
            name="Gardening Tools Kit",
            description="Complete gardening tools set including shovel, rake, and pruning shears. Essential for maintaining your garden and plants.",
            category="Garden",
            price=44.99,
        ),
    ]

    try:
        table.bulk_insert(initial_products)
    except Exception as e:
        st.error(f"Failed to load initial data: {str(e)}")


def get_recommendations(
    table: Table, user_profile: str, limit: int = 5, distance_threshold: float = 0.85
) -> List[Dict[str, Any]]:
    """Get product recommendations based on user profile using vector search"""
    try:
        # Perform vector search with user profile as query
        search_query = table.search(user_profile)

        # Only apply distance_threshold if > 0
        if distance_threshold > 0:
            search_query = search_query.distance_threshold(distance_threshold)

        results = search_query.limit(limit).to_list()

        # Debug: Log distances
        if results:
            distances = [r.get("_distance", "N/A") for r in results]
            print(
                f"[DEBUG] Threshold: {distance_threshold}, Found: {len(results)}, Distances: {distances}"
            )

        return results
    except Exception as e:
        if "st" in globals():
            st.error(f"Failed to get recommendations: {str(e)}")
        else:
            print(f"Failed to get recommendations: {str(e)}")
        return []


def get_all_products(table: Table) -> List[Dict[str, Any]]:
    """Get all products from the database"""
    try:
        # Use table.query() to get all products
        products = table.query().to_list()
        # table.query().to_list() returns a list of dicts already
        return products
    except Exception as e:
        st.error(f"Failed to get all products: {str(e)}")
        return []


def add_product(table: Table, name: str, description: str, category: str, price: float):
    """Add a new product to the database"""
    try:
        Product = table.table_model
        new_product = Product(
            name=name, description=description, category=category, price=price
        )
        table.insert(new_product)
        return True
    except Exception as e:
        st.error(f"Failed to add product: {str(e)}")
        return False


def update_product(
    table: Table,
    db: TiDBClient,
    product_id: int,
    name: str,
    description: str,
    category: str,
    price: float,
):
    """Update an existing product - delete and re-insert to trigger auto-embedding"""
    try:
        Product = table.table_model
        # Use transaction to ensure atomicity
        with db.session() as session:
            # Delete old product
            db.execute(f"DELETE FROM {table.table_name} WHERE id = %s", (product_id,))
            # Insert updated product with same ID (auto-embedding will be triggered)
            updated_product = Product(
                id=product_id,
                name=name,
                description=description,
                category=category,
                price=price,
            )
            table.insert(updated_product)
            session.commit()
        return True
    except Exception as e:
        if "st" in globals():
            st.error(f"Failed to update product: {str(e)}")
        else:
            print(f"Failed to update product: {str(e)}")
        return False


def delete_product(table: Table, product_id: int):
    """Delete a product from the database"""
    try:
        # Use table.delete() to delete product
        table.delete(filters={"id": product_id})
        return True
    except Exception as e:
        if "st" in globals():
            st.error(f"Failed to delete product: {str(e)}")
        else:
            print(f"Failed to delete product: {str(e)}")
        return False


def render_mobile_ui(recommendations: List[Dict[str, Any]], user_profile: str):
    """Render the left side mobile shopping app UI"""

    st.markdown(
        """
        <style>
        .mobile-container {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 30px;
            padding: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            max-width: 420px;
            margin: 0 auto;
        }
        .mobile-screen {
            background: white;
            border-radius: 20px;
            padding: 20px;
            min-height: 600px;
        }
        .mobile-header {
            font-size: 24px;
            font-weight: bold;
            color: #333;
            margin-bottom: 5px;
            text-align: center;
        }
        .mobile-subtitle {
            font-size: 12px;
            color: #999;
            margin-bottom: 15px;
            text-align: center;
        }
        .product-card {
            background: #f8f9fa;
            border-radius: 12px;
            padding: 15px;
            margin-bottom: 12px;
            border-left: 4px solid #667eea;
        }
        .product-name {
            font-size: 16px;
            font-weight: bold;
            color: #333;
            margin-bottom: 5px;
        }
        .product-price {
            font-size: 18px;
            font-weight: bold;
            color: #667eea;
            display: inline-block;
            margin-right: 10px;
        }
        .product-category {
            font-size: 11px;
            background: #667eea;
            color: white;
            padding: 3px 8px;
            border-radius: 10px;
            display: inline-block;
        }
        .product-distance {
            font-size: 11px;
            color: #999;
            margin-top: 8px;
        }
        .product-desc {
            font-size: 13px;
            color: #666;
            margin-top: 8px;
            line-height: 1.4;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    html_body_content = textwrap.dedent(f"""
        <div class="mobile-header">🛍️ For You</div>
        <div class="mobile-subtitle">"{user_profile}"</div>
    """)

    if not recommendations:
        html_body_content += '<div style="text-align: center; padding: 40px; color: #999;">No recommendations found. Try adjusting the threshold.</div>'
    else:
        for product in recommendations:
            distance = product.get("_distance", 0)
            desc = product["description"]
            if len(desc) > 100:
                desc = desc[:100] + "..."

            product_html = f"""
                <div class="product-card">
                    <div class="product-name">{product["name"]}</div>
                    <div>
                        <span class="product-price">${product["price"]:.2f}</span>
                        <span class="product-category">{product["category"]}</span>
                    </div>
                    <div class="product-desc">{desc}</div>
                    <div class="product-distance">📏 Distance: {distance:.4f}</div>
                </div>
                """
            html_body_content += textwrap.dedent(product_html)

    final_html = textwrap.dedent(f"""
        <div class="mobile-container">
            <div class="mobile-screen">
                {html_body_content}
    """)
    st.markdown(final_html, unsafe_allow_html=True)


def render_admin_panel(table: Table):
    """Render the right side admin panel for managing products."""

    # This CSS block is updated to specifically target and align the columns.
    st.markdown(
        """
        <style>
        /* Main container styling for the admin panel */
        div[data-testid="stVerticalBlock"] div[data-testid="stVerticalBlock"] > div[data-testid="stVerticalBlock"] > div:nth-child(1) {
             background: #232526;
             border-radius: 15px;
             padding: 20px;
             box-shadow: 0 10px 40px rgba(0,0,0,0.3);
        }

        .st-emotion-cache-1l26guv {
            align-items: center;
        }

        /* Style the form to ensure it fits well */
        div[data-testid="stForm"] {
            border: none;
            padding: 0;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("### 📊 Product Management")

    all_products = get_all_products(table)

    if not all_products:
        st.info("No products in database. Add some products below!")
    else:
        st.markdown(f"**Total Products:** {len(all_products)}")

        for product in all_products:
            # Each product is in its own container
            with st.container():
                col1, col2, col3 = st.columns([6, 1, 1])

                with col1:
                    edit_key = f"edit_{product['id']}"
                    if st.session_state.edit_mode.get(edit_key, False):
                        # --- EDIT MODE ---
                        with st.form(key=f"edit_form_{product['id']}"):
                            new_name = st.text_input(
                                "Name",
                                value=product["name"],
                                label_visibility="collapsed",
                            )
                            new_desc = st.text_area(
                                "Description",
                                value=product["description"],
                                height=100,
                                label_visibility="collapsed",
                            )

                            sub_col_a, sub_col_b = st.columns(2)
                            with sub_col_a:
                                new_category = st.text_input(
                                    "Category",
                                    value=product["category"],
                                    label_visibility="collapsed",
                                )
                            with sub_col_b:
                                new_price = st.number_input(
                                    "Price",
                                    value=product["price"],
                                    min_value=0.0,
                                    step=0.01,
                                    label_visibility="collapsed",
                                )

                            btn_col_save, btn_col_cancel = st.columns(2)
                            with btn_col_save:
                                if st.form_submit_button(
                                    "💾 Save", use_container_width=True
                                ):
                                    if update_product(
                                        table,
                                        st.session_state.db,
                                        product["id"],
                                        new_name,
                                        new_desc,
                                        new_category,
                                        new_price,
                                    ):
                                        st.success("Product updated!")
                                        st.session_state.edit_mode[edit_key] = False
                                        st.rerun()
                            with btn_col_cancel:
                                if st.form_submit_button(
                                    "❌ Cancel",
                                    use_container_width=True,
                                    type="secondary",
                                ):
                                    st.session_state.edit_mode[edit_key] = False
                                    st.rerun()
                    else:
                        # --- VIEW MODE ---
                        st.markdown(f"**{product['name']}** (${product['price']:.2f})")
                        st.caption(f"Category: {product['category']}")
                        st.text(
                            product["description"][:100] + "..."
                            if len(product["description"]) > 100
                            else product["description"]
                        )

                # These buttons will now be vertically centered with the content in col1
                with col2:
                    if not st.session_state.edit_mode.get(edit_key, False):
                        if st.button(
                            "✏️",
                            key=f"edit_btn_{product['id']}",
                            help="Edit",
                            use_container_width=True,
                        ):
                            st.session_state.edit_mode[edit_key] = True
                            st.rerun()
                with col3:
                    if not st.session_state.edit_mode.get(edit_key, False):
                        if st.button(
                            "🗑️",
                            key=f"delete_btn_{product['id']}",
                            help="Delete",
                            use_container_width=True,
                        ):
                            if delete_product(table, product["id"]):
                                st.success("Product deleted!")
                                st.rerun()
                st.divider()

    # --- ADD NEW PRODUCT FORM ---
    st.markdown("### ➕ Add New Product")
    with st.form(key="add_product_form", clear_on_submit=True):
        new_name = st.text_input("Product Name")
        new_description = st.text_area("Description", height=100)
        col1, col2 = st.columns(2)
        with col1:
            new_category = st.text_input("Category")
        with col2:
            new_price = st.number_input("Price ($)", min_value=0.0, step=0.01)

        if st.form_submit_button("Add Product", use_container_width=True):
            if not new_name or not new_description or not new_category:
                st.error("Please fill in all fields!")
            else:
                if add_product(
                    table, new_name, new_description, new_category, new_price
                ):
                    st.success(f"Product '{new_name}' added successfully!")
                    st.rerun()


def setup():
    """Initialize database connection and setup"""
    # Connect to database
    if st.session_state.db is None:
        with st.spinner("Connecting to TiDB..."):
            st.session_state.db = connect_to_tidb()

    # Setup embedding function
    if st.session_state.embed_func is None:
        with st.spinner("Setting up embedding function..."):
            st.session_state.embed_func = setup_embedding_function(st.session_state.db)

    # Setup table
    if st.session_state.table is None:
        with st.spinner("Setting up products table..."):
            st.session_state.table = setup_table(
                st.session_state.db, st.session_state.embed_func
            )

    # Load user profile
    if st.session_state.user_profile is None:
        st.session_state.user_profile = os.getenv("USER_PROFILE", "a user likes sports")

    # Load initial data
    table = st.session_state.table
    if table.rows() == 0:
        with st.spinner("Loading initial products..."):
            load_initial_data(table)


def main():
    """Main application"""

    # Setup
    setup()

    # Sidebar with logo and settings
    with st.sidebar:
        st.logo(
            "../assets/logo-full.svg",
            size="large",
            link="https://pingcap.github.io/ai/",
        )

        st.markdown(
            """#### Overview

**Vector search with real-time data** demonstrates TiDB's auto-embedding and semantic search capabilities.
Products are matched based on similarity to user preferences, with instant updates when data changes.
        """
        )

        st.markdown("#### Settings")

        user_profile = st.text_input(
            "User Profile",
            value=st.session_state.user_profile,
            help="Describe the user's preferences for personalized recommendations",
        )
        if user_profile != st.session_state.user_profile:
            st.session_state.user_profile = user_profile

        distance_threshold = st.slider(
            "Distance Threshold",
            min_value=0.0,
            max_value=2.0,
            value=0.85,
            step=0.01,
            help="Maximum distance to consider a match. 0 = no filter. Lower values = stricter matching.",
        )

        st.info(
            "💡 **Lower distance = better match**\n\n"
            f"Current: {'No filtering' if distance_threshold == 0 else f'Max distance: {distance_threshold}'}"
        )

    # Title
    st.markdown(
        '<h2 style="text-align: center;">🛍️ Vector Search with Real-time Data</h2>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<p style="text-align: center; color: #666;">Experience TiDB\'s vector search with live product recommendations</p>',
        unsafe_allow_html=True,
    )

    st.divider()

    # Main layout: Left (Mobile UI) and Right (Admin Panel)
    left_col, right_col = st.columns([1, 1], gap="large")

    with left_col:
        st.markdown("### 📱 User View (Shopping App)")
        # Get recommendations
        recommendations = get_recommendations(
            st.session_state.table,
            st.session_state.user_profile,
            limit=5,
            distance_threshold=distance_threshold,
        )
        render_mobile_ui(recommendations, st.session_state.user_profile)

    with right_col:
        render_admin_panel(st.session_state.table)


if __name__ == "__main__":
    main()
