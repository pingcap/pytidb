#!/usr/bin/env python3
import os
from pathlib import Path
from typing import List, Optional, Dict, Any
from urllib.parse import urlparse
from urllib.request import url2pathname

import streamlit as st
from PIL import Image
import dotenv

from pytidb import TiDBClient, Table
from pytidb.schema import TableModel, Field, DistanceMetric
from pytidb.embeddings import EmbeddingFunction
import data_loader


DATASET_NAME = "oxford_pets"
DATABASE_NAME = "pet_image_search"

# Load environment variables
dotenv.load_dotenv()

# Page configuration
st.set_page_config(
    page_title="Pet Image Search",
    page_icon="🐕",
    layout="wide",
    initial_sidebar_state="expanded",
)


# Initialize session state
if "db" not in st.session_state:
    st.session_state.db = None
if "embed_fn" not in st.session_state:
    st.session_state.embed_fn = None
if "table" not in st.session_state:
    st.session_state.table = None


def connect_to_tidb() -> Optional[TiDBClient]:
    try:
        db = TiDBClient.connect(
            host=os.getenv("TIDB_HOST", "localhost"),
            port=int(os.getenv("TIDB_PORT", "4000")),
            username=os.getenv("TIDB_USERNAME", "root"),
            password=os.getenv("TIDB_PASSWORD", ""),
            database=os.getenv("TIDB_DATABASE", DATABASE_NAME),
            ensure_db=True,
        )
        return db
    except Exception as e:
        st.error(f"Failed to connect to TiDB: {str(e)}")
        st.stop()
        return None


def setup_embed_fn() -> EmbeddingFunction:
    try:
        embed_fn = EmbeddingFunction(
            model_name="jina_ai/jina-embeddings-v4", timeout=20
        )
        return embed_fn
    except Exception as e:
        st.error(f"Failed to initialize embedding function: {str(e)}")
        st.stop()
        return None


def setup_table(db: TiDBClient, embed_fn: EmbeddingFunction) -> Table:
    try:

        class Pet(TableModel):
            """Pet model for image search."""

            __tablename__ = "pets"
            __table_args__ = {"extend_existing": True}

            id: int = Field(primary_key=True)
            breed: str = Field()
            image_uri: str = Field()
            image_name: str = Field()
            image_vec: Optional[List[float]] = embed_fn.VectorField(
                distance_metric=DistanceMetric.L2,
                source_field="image_uri",
                source_type="image",
            )

        table = db.create_table(schema=Pet, if_exists="skip")
        return table
    except Exception as e:
        st.error(f"Failed to create table: {str(e)}")
        st.stop()
        return None


def search_images(table, query, limit: int = 20) -> List[Dict[str, Any]]:
    try:
        results = (
            table.search(query=query)
            .distance_metric(DistanceMetric.L2)
            .limit(limit)
            .to_list()
        )
        return results
    except Exception as e:
        st.error(f"Search error: {str(e)}")
        return []


def reset_data(table):
    """Reset all data in the table."""
    try:
        # Clear all rows from the table
        table.truncate()
        st.success("All data has been cleared from the database.")
    except Exception as e:
        st.error(f"Failed to reset data: {str(e)}")


def display_search_results(
    results: List[Dict[str, Any]], search_method: str, query: str
):
    if not results:
        st.info("No results found")
        return

    if search_method == "Text":
        st.write(f"Found {len(results)} results for term: {query}")
    else:
        st.write(f"Found {len(results)} results")

    # Create columns for waterfall layout
    cols_per_row = 4
    cols = st.columns(cols_per_row)

    # Distribute images to columns in a waterfall pattern
    for i, result in enumerate(results):
        col_index = i % cols_per_row
        with cols[col_index]:
            try:
                # Convert file:// URL back to file path for image loading
                img_uri = result["image_uri"]
                if img_uri.startswith("file://"):
                    # Convert file:// URL to Path object
                    parsed = urlparse(img_uri)
                    file_path = Path(url2pathname(parsed.path))
                else:
                    # Fallback for non-URL paths
                    file_path = Path(img_uri)

                if file_path.exists():
                    image = Image.open(file_path)
                    st.image(image, use_container_width=True)

                    # Display metadata
                    similarity = result.get("_score", 0)
                    st.markdown(
                        f"""
                        <div style="line-height: 1.2; margin-bottom: 20px;">
                            <strong>{result["breed"]}</strong><br>
                            <small>Similarity: {similarity:.3f}</small><br>
                            <small>File: {result["image_name"]}</small>
                        </div>
                    """,
                        unsafe_allow_html=True,
                    )
                else:
                    st.error(f"Image not found: {file_path}")
            except Exception as e:
                st.error(f"Error loading image: {e}")


def main():
    # Header
    st.title("🐕 Pet Image Search")
    st.markdown(
        """
        Upload a photo or describe your ideal pet - find your perfect furry friend!
    """
    )

    # Initialize...
    if st.session_state.db is None:
        with st.spinner("Connecting to TiDB..."):
            st.session_state.db = connect_to_tidb()
    if st.session_state.embed_fn is None:
        with st.spinner("Setting up embedding function..."):
            st.session_state.embed_fn = setup_embed_fn()
    if st.session_state.table is None:
        with st.spinner("Setting up table..."):
            st.session_state.table = setup_table(
                st.session_state.db, st.session_state.embed_fn
            )

    # Load data section.
    table = st.session_state.table
    total_count = table.rows()
    if total_count == 0:
        st.warning("No images in database. Please load data first.")

        # Data loading buttons
        st.markdown("#### Load Data")
        st.markdown(
            "In this demo, we will load pet images from the Oxford Pets dataset (`./oxford_pets/images` directory) to the database."
        )

        st.markdown("Load one image per breed (~37 images total):")
        if st.button("Load Sample Data", type="primary"):
            data_loader.load_images_to_db(table, True)
            st.rerun()

        st.markdown("Load all images from the dataset (~7,000 images total):")
        if st.button("Load All Data", type="primary"):
            data_loader.load_images_to_db(table, False)
            st.rerun()
        return

    # Sidebar
    with st.sidebar:
        st.logo(
            "../assets/logo-full.svg",
            size="large",
            link="https://pingcap.github.io/ai/",
        )

        # st.markdown("#### 🔍 Search")

        # Search interface
        search_method = st.radio(
            "Search Type",
            ["Image", "Text"],
            key="search_method",
            horizontal=True,
        )

        if search_method == "Image":
            # Image-to-image search
            uploaded_file = st.file_uploader(
                "Upload an image:",
                type=["png", "jpg", "jpeg", "bmp", "tiff"],
                key="image_upload",
                label_visibility="collapsed",
            )
            if uploaded_file is not None:
                query_image = Image.open(uploaded_file)
                col1, col2, col3 = st.columns([0.1, 0.8, 0.1])
                with col2:
                    st.image(query_image, use_container_width=True)
            else:
                query_image = None
            query_text = None
        else:
            # Text-to-image search
            query_text = st.text_input(
                "Search query",
                placeholder="e.g., 'fluffy white cat', 'golden retriever'",
                key="text_search",
                label_visibility="collapsed",
            )
            query_image = None

        max_results = st.slider(
            "Max Results", min_value=4, max_value=32, value=16, step=2
        )

        # Search button
        search_button = st.button("Search", type="primary", use_container_width=True)

        # Reset data button
        if st.button("Reset Data", type="secondary", use_container_width=True):
            reset_data(st.session_state.table)
            st.rerun()

    # Handle search results
    if not search_button:
        st.success(
            f"Ready to search! Currently, the database contains {total_count} images."
        )
        return

    if search_method == "Text" and query_text:
        query = query_text
        spinner_text = f"Searching images for '{query_text}'..."
    elif search_method == "Image" and query_image is not None:
        query = query_image
        spinner_text = "Finding similar images for uploaded image..."
    else:
        st.warning("Please enter a search query or upload an image to search.")
        return

    # Perform search and display results
    with st.spinner(spinner_text):
        results = search_images(table, query, max_results)

    if results:
        display_search_results(results, search_method, query)
    else:
        st.info("No results found. Try a different search term or image.")


if __name__ == "__main__":
    main()
