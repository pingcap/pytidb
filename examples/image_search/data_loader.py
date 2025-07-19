"""
Data loading utilities for PyTiDB Image Search Demo.

This module handles loading image data from the Oxford Pets dataset
into the TiDB database with progress tracking.
"""

import random
from pathlib import Path
from typing import List, Dict
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

import streamlit as st

# Constant to control concurrency level
CONCURRENT_WORKERS = 5


def extract_breed_from_filename(filename: str) -> str:
    """Extract breed name from image filename."""
    # Remove file extension and split by underscore
    name_parts = filename.rsplit(".", 1)[0].split("_")[:-1]  # Exclude the number part
    # Join parts and replace underscores with spaces, then title case
    breed = " ".join(name_parts).replace("_", " ").title()
    return breed


def process_single_image(img_path: Path, table) -> Dict:
    """
    Process a single image and insert it into the database.

    Args:
        img_path: Path to the image file
        table: The database table to insert data into

    Returns:
        Dict with success status and error message if any
    """
    try:
        # Extract breed from filename
        breed = extract_breed_from_filename(img_path.name)

        # Create absolute path URI
        absolute_path = img_path.resolve()
        image_uri = f"file://{absolute_path}"

        # Insert into database (embeddings will be generated automatically)
        table.insert(
            {"breed": breed, "image_uri": image_uri, "image_name": img_path.name}
        )

        return {"success": True, "filename": img_path.name}

    except Exception as e:
        return {"success": False, "filename": img_path.name, "error": str(e)}


def load_images_to_db(table, one_per_breed: bool = False):
    """
    Load images from the Oxford Pets dataset into database with concurrent processing.

    Args:
        table: The database table to insert data into
        one_per_breed: If True, load only one image per breed; if False, load all images
    """
    if not table:
        st.error("Table not initialized. Please refresh the page.")
        return

    # Get data directory
    data_dir = Path("oxford_pets/images")
    if not data_dir.exists():
        st.error(f"Data directory not found: {data_dir}")
        return

    # Get all image files
    image_files = [
        f for f in data_dir.iterdir() if f.suffix.lower() in [".jpg", ".jpeg", ".png"]
    ]

    if not image_files:
        st.error("No image files found in the data directory.")
        return

    # Create containers for messages
    loading_message = st.empty()
    progress_bar = st.progress(0)
    status_text = st.empty()
    result_message = st.empty()

    # Select images to process
    if one_per_breed:
        breed_images: Dict[str, List[Path]] = defaultdict(list)

        # Group images by breed
        for img_file in image_files:
            breed = extract_breed_from_filename(img_file.name)
            breed_images[breed].append(img_file)

        # Select one image per breed
        selected_images = []
        for breed, breed_files in breed_images.items():
            selected_images.append(random.choice(breed_files))

        loading_message.info(
            "Loading sample images (one per breed) in Oxford Pets dataset..."
        )
        images_to_process = selected_images
    else:
        loading_message.info(
            f"Loading all {len(image_files)} images in Oxford Pets dataset..."
        )
        images_to_process = image_files

    success_count = 0
    total_count = len(images_to_process)
    processed_count = 0

    # Thread lock for updating progress
    progress_lock = threading.Lock()

    def update_progress(filename: str):
        nonlocal processed_count
        with progress_lock:
            processed_count += 1
            progress = processed_count / total_count
            progress_bar.progress(progress)
            status_text.text(f"Processing {processed_count}/{total_count}: {filename}")

    # Process images concurrently
    with ThreadPoolExecutor(max_workers=CONCURRENT_WORKERS) as executor:
        # Submit all tasks
        future_to_image = {
            executor.submit(process_single_image, img_path, table): img_path
            for img_path in images_to_process
        }

        # Process completed tasks
        for future in as_completed(future_to_image):
            img_path = future_to_image[future]
            try:
                result = future.result()
                update_progress(result["filename"])

                if result["success"]:
                    success_count += 1
                else:
                    st.error(
                        f"Failed to process {result['filename']}: {result['error']}"
                    )

            except Exception as e:
                update_progress(img_path.name)
                st.error(f"Failed to process {img_path.name}: {str(e)}")

    # Cleanup progress indicators and loading message
    loading_message.empty()
    progress_bar.empty()
    status_text.empty()

    # Show final result message
    if success_count > 0:
        result_message.success(
            f"Successfully loaded {success_count}/{total_count} images!"
        )
    else:
        result_message.error("No images were successfully loaded.")
