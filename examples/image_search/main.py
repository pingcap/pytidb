import os
import requests
from PIL import Image
import dotenv
from pytidb.embeddings import CLIPEmbeddingFunction
from pytidb.schema import TableModel, Field
from pytidb.datatype import Text
from pytidb import TiDBClient

# Load environment variables
dotenv.load_dotenv()

# Connect to database with connection parameters
db = TiDBClient.connect(
    host=os.getenv("TIDB_HOST", "localhost"),
    port=int(os.getenv("TIDB_PORT", "4000")),
    username=os.getenv("TIDB_USERNAME", "root"),
    password=os.getenv("TIDB_PASSWORD", ""),
    database=os.getenv("TIDB_DATABASE", "test"),
)

# Define CLIP embedding function for image and text
print("=== Define CLIP embedding function ===")
clip_embed_fn = CLIPEmbeddingFunction(
    model_name="openai/clip-vit-base-patch32",
    api_key=os.getenv("OPENAI_API_KEY"),
)
print("CLIP embedding function defined")

# Define table schema with image auto embedding
print("\n=== Define table schema ===")


class Pet(TableModel):
    __tablename__ = "pets_with_images"
    id: int = Field(primary_key=True)
    name: str = Field()
    description: str = Field(sa_type=Text)
    image_uri: str = Field()
    # Auto embedding field for images
    image_vector: list[float] = clip_embed_fn.VectorField(
        source_field="image_uri", source_type="image"
    )

    @property
    def image(self):
        """Convenience property to load the image."""
        return Image.open(self.image_uri)


table = db.create_table(schema=Pet, mode="overwrite")
print("Table created")

# Truncate table to start fresh
print("\n=== Truncate table ===")
table.truncate()
print("Table truncated")

# Download sample images for demonstration
print("\n=== Download sample images ===")
sample_images = []
image_urls = [
    "https://upload.wikimedia.org/wikipedia/commons/4/4f/Golden_retriever_eating.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/9/99/Brooks_Chase_Ranger_of_Jolly_Dogs_Jack_Russell.jpg",
    "https://upload.wikimedia.org/wikipedia/commons/e/e8/Siamese_cat_1.jpg",
]

for i, url in enumerate(image_urls):
    try:
        response = requests.get(url)
        if response.status_code == 200:
            image_path = f"sample_image_{i}.jpg"
            with open(image_path, "wb") as f:
                f.write(response.content)
            sample_images.append(image_path)
            print(f"Downloaded: {image_path}")
        else:
            print(f"Failed to download image from {url}")
    except Exception as e:
        print(f"Error downloading image from {url}: {e}")

# If downloading fails, create mock images
if not sample_images:
    print("Creating mock images for demonstration...")
    for i in range(3):
        img = Image.new("RGB", (400, 300), color=(i * 80, i * 80, i * 80))
        image_path = f"mock_image_{i}.jpg"
        img.save(image_path)
        sample_images.append(image_path)
        print(f"Created mock image: {image_path}")

# Insert sample data with images
print("\n=== Insert sample data ===")
pets_data = [
    Pet(
        id=1,
        name="Golden Retriever",
        description="A friendly and energetic golden retriever dog",
        image_uri=sample_images[0],
    ),
    Pet(
        id=2,
        name="Jack Russell Terrier",
        description="A small, energetic terrier breed",
        image_uri=sample_images[1],
    ),
    Pet(
        id=3,
        name="Siamese Cat",
        description="An elegant cat with blue eyes and cream-colored fur",
        image_uri=sample_images[2],
    ),
]

# 👇 The images will be embedded automatically and the vector field will be populated
table.bulk_insert(pets_data)
print("Inserted 3 pets with automatic image embedding")

# Perform text-to-image search
print("\n=== Perform text-to-image search ===")
text_results = table.search("friendly dog").limit(2).to_list()
print("Text-to-image search results:")
for item in text_results:
    print(
        f"  - {item['name']}: {item['description']} (similarity: {1 - item['_distance']:.3f})"
    )

# Perform image-to-image search
print("\n=== Perform image-to-image search ===")
if sample_images:
    query_image = Image.open(sample_images[0])
    image_results = table.search(query_image).limit(2).to_list()
    print("Image-to-image search results:")
    for item in image_results:
        print(
            f"  - {item['name']}: {item['description']} (similarity: {1 - item['_distance']:.3f})"
        )

# Demonstrate using the convenience property
print("\n=== Test convenience property ===")
pet = table.get(1)
if pet:
    print(f"Pet name: {pet.name}")
    print(f"Image size: {pet.image.size}")
    print(f"Image mode: {pet.image.mode}")

# Clean up downloaded images
print("\n=== Clean up ===")
for image_path in sample_images:
    try:
        os.remove(image_path)
        print(f"Removed: {image_path}")
    except Exception as e:
        print(f"Error removing {image_path}: {e}")

print("\n=== Image search example completed ===")
print("This example demonstrated:")
print("1. Setting up CLIP embedding function for images")
print("2. Defining table schema with image auto embedding")
print("3. Automatic image embedding on insert")
print("4. Text-to-image search (semantic search)")
print("5. Image-to-image search (visual similarity)")
print("6. Convenience methods for working with images")
