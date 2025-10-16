# Vector Search with Real-time Data

This example demonstrates TiDB's vector search capabilities with real-time data updates, simulating an e-commerce recommendation system. It showcases how TiDB automatically embeds product descriptions and uses vector similarity search to provide personalized recommendations based on user preferences.

<p align="center">
  <img width="700" alt="Vector Search with Real-time Data" src="https://github.com/user-attachments/assets/c946ec9c-73ff-4694-b8f8-a622329ff367" />
  <p align="center"><i>Vector Search with Real-time Data</i></p>
</p>

## Features

- **🔍 Vector Search**: Semantic similarity search using auto-embedding
- **📱 Real-time Updates**: Instant recommendation refresh when products are added, updated, or deleted
- **🛍️ Shopping Experience**: Mobile app UI showing personalized product recommendations
- **⚙️ Admin Panel**: Full CRUD operations on products
- **🎯 Smart Filtering**: Adjustable similarity threshold for recommendation precision
- **🤖 Auto-Embedding**: TiDB automatically generates vector embeddings for product descriptions

## UI Layout

The application features a two-column layout:

### Left Column: Shopping App (User View)

- Mobile phone mockup showing personalized recommendations
- Displays up to 5 products that match the user's profile
- Results filtered by similarity threshold
- Clean, modern design with product cards showing name, description, price, and category

### Right Column: Admin Panel

- **Top Section**: Product list with edit and delete functionality
  - Edit products inline with a form
  - Delete products with one click
- **Bottom Section**: Add new products form
  - Input fields for name, description, category, and price
  - Auto-embedding happens automatically when products are added

## How It Works

1. **User Profile**: A text description of user preferences (e.g., "a user likes sports")
2. **Auto-Embedding**: Product descriptions are automatically converted to vector embeddings by TiDB
3. **Vector Search**: The system searches for products similar to the user profile using vector similarity
4. **Threshold Filtering**: Only products within the similarity threshold are shown
5. **Real-time Updates**: Any changes to products trigger automatic recommendation refresh

### Initial State

The application starts with 5 sample products:

- **3 sports-related items** (matching the default profile "a user likes sports")
  - Professional Basketball
  - Running Shoes
  - Yoga Mat
- **2 unrelated items** (filtered out by default threshold)
  - Cooking Pot Set
  - Gardening Tools Kit

With the default threshold (0.5), only the 3 sports items appear in recommendations.

## Prerequisites

- **Python 3.10+**
- **A TiDB Cloud Serverless cluster**: Create a free cluster here: [tidbcloud.com](https://tidbcloud.com/?utm_source=github&utm_medium=referral&utm_campaign=pytidb_examples)
- **OpenAI API Key**: Required for embedding generation

## Setup Instructions

### Step 1: Clone the repository

```bash
git clone https://github.com/pingcap/pytidb.git
cd pytidb/examples/vector-search-with-realtime-data/
```

### Step 2: Install dependencies

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Step 3: Configure environment variables

The `.env.example` file is already in the directory. Create a `.env` file based on it:

```bash
cp .env.example .env
```

Then edit `.env` with your credentials:

```env
# TiDB Connection (get from https://tidbcloud.com/clusters)
TIDB_HOST=gateway01.ap-southeast-1.prod.aws.tidbcloud.com
TIDB_PORT=4000
TIDB_USERNAME=your-username.root
TIDB_PASSWORD=your-password
TIDB_DATABASE=test

# OpenAI API Key (for embeddings)
OPENAI_API_KEY=your-openai-api-key

# User Profile (customize as needed)
USER_PROFILE=a user likes sports
```

### Step 4: Run the application

```bash
streamlit run app.py
```

### Step 5: Open in browser

Open your browser and visit `http://localhost:8501`

## Usage Guide

### Viewing Recommendations

1. The left side shows a mobile app interface with personalized recommendations
2. Recommendations are based on the USER_PROFILE from your `.env` file
3. Only products within the similarity threshold are displayed

### Adjusting Settings

Click the "⚙️ Settings" expander at the top to:

- **Change User Profile**: Modify preferences to see different recommendations
  - Try: "a user likes cooking", "someone interested in fitness", "outdoor enthusiast"
- **Adjust Threshold**: Control how strictly products must match the profile
  - Lower values (0.3-0.4): Stricter matching, fewer results
  - Higher values (0.6-0.8): Looser matching, more results

### Managing Products

#### Adding Products

1. Scroll to the bottom of the right panel
2. Fill in the "Add New Product" form:
   - Product Name
   - Description (this will be embedded automatically)
   - Category
   - Price
3. Click "Add Product"
4. Watch recommendations update automatically!

#### Editing Products

1. Find the product in the list
2. Click the ✏️ (edit) button
3. Modify the fields in the form
4. Click "💾 Save" to update, or "❌ Cancel" to discard changes
5. Updated products will be re-embedded and recommendations will refresh

#### Deleting Products

1. Find the product in the list
2. Click the 🗑️ (delete) button
3. Product is removed immediately
4. Recommendations update automatically

## Example Experiments

### Experiment 1: Add a Sports Item

1. Add a new product: "Tennis Racket" with description about tennis and sports
2. Observe it appears in recommendations (if profile is sports-related)

### Experiment 2: Add an Unrelated Item

1. Add a product: "Classical Music CD" with description about music
2. Observe it doesn't appear in recommendations (filtered by threshold)

### Experiment 3: Change User Profile

1. Open Settings and change profile to "a user likes cooking"
2. Watch recommendations switch to show the Cooking Pot Set
3. Sports items should no longer appear

### Experiment 4: Adjust Threshold

1. Lower threshold to 0.3 (stricter matching)
2. Fewer products appear in recommendations
3. Raise threshold to 0.7 (looser matching)
4. More products appear, including less relevant ones

## Technical Details

### Database Schema

```python
class Product(TableModel):
    id: int                           # Primary key (auto-increment)
    name: str                         # Product name
    description: str                  # Product description
    description_vec: list[float]      # Auto-generated embedding vector
    category: str                     # Product category
    price: float                      # Product price
```

### Vector Search Query

The application uses TiDB's vector search with distance threshold:

```python
results = (
    table.search(user_profile)              # Search using user profile as query
    .distance_threshold(distance_threshold) # Filter by similarity
    .limit(5)                               # Return top 5 results
    .to_list()
)
```

### Embedding Model

- **Model**: OpenAI `text-embedding-3-small`
- **Dimensions**: 1536
- **Provider**: OpenAI API
- **Auto-embedding**: Triggered automatically on insert/update

## Learn More

- [PyTiDB Documentation](https://pingcap.github.io/ai/)
- [TiDB Vector Search](https://docs.pingcap.com/tidb/stable/vector-search-overview)
- [Vector Search Examples](https://github.com/pingcap/pytidb/tree/main/examples)

## License

This example is part of the PyTiDB project and follows the same license.
