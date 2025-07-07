# Image Search Demo

This example showcases the new **image auto embedding** feature with PyTiDB Client.

## Features Demonstrated

* **Auto Image Embedding**: Automatically embed images when inserting data
* **Text-to-Image Search**: Search for images using natural language queries
* **Image-to-Image Search**: Search for similar images using an image as the query
* **CLIP Integration**: Use OpenAI's CLIP model for multimodal embeddings

## Prerequisites

- **Python 3.10+**
- **A TiDB Cloud Serverless cluster**: Create a free cluster here: [tidbcloud.com ↗️](https://tidbcloud.com/?utm_source=github&utm_medium=referral&utm_campaign=pytidb_readme)
- **OpenAI API key**: Get your API key from [OpenAI Platform](https://platform.openai.com/api-keys)

## How to run

**Step 1**: Clone the repository

```bash
git clone https://github.com/pingcap/pytidb.git
cd pytidb/examples/image_search/
```

**Step 2**: Install the required packages

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r reqs.txt
```

**Step 3**: Set up environment to connect to database

Go to [TiDB Cloud console](https://tidbcloud.com/clusters) to get the connection parameters and set up the environment variable like this:

```bash
cat > .env <<EOF
TIDB_HOST={gateway-region}.prod.aws.tidbcloud.com
TIDB_PORT=4000
TIDB_USERNAME={prefix}.root
TIDB_PASSWORD={password}
TIDB_DATABASE=test
OPENAI_API_KEY={your-openai-api-key}
EOF
```

**Step 4**: Run the demo

```bash
python main.py
```

## Code Walkthrough

### 1. Define CLIP Embedding Function

```python
from pytidb.embeddings import CLIPEmbeddingFunction

clip_embed_fn = CLIPEmbeddingFunction(
    model_name="openai/clip-vit-base-patch32",
    api_key=os.getenv("OPENAI_API_KEY"),
)
```

### 2. Define Table Schema

```python
class Pet(TableModel):
    __tablename__ = "pets_with_images"
    id: int = Field(primary_key=True)
    name: str = Field()
    description: str = Field(sa_type=Text)
    image_uri: str = Field()
    # Auto embedding field for images
    image_vector: list[float] = clip_embed_fn.VectorField(
        source_field="image_uri",
        source_type="image"  # 👈 Specify image source type
    )

    @property
    def image(self):
        """Convenience property to load the image."""
        return Image.open(self.image_uri)
```

Key features:
- **`source_type="image"`**: Tells PyTiDB to treat the source field as an image path
- **Auto embedding**: When inserting data, images are automatically embedded

### 3. Text-to-Image Search

```python
# Search for images using natural language
text_results = table.search("friendly dog").limit(2).to_list()
```

### 4. Image-to-Image Search

```python
# Search for similar images using an image as query
query_image = Image.open(sample_images[0])
image_results = table.search(query_image).limit(2).to_list()
``` 