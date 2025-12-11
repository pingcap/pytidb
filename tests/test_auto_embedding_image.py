import os
from pathlib import Path
from typing import Optional
import pytest

from pytidb import TiDBClient
from pytidb.schema import TableModel, Field
from pytidb.table import Table
from pytidb.embeddings import EmbeddingFunction

SKIP_TIDB_TESTS = os.getenv("PYTIDB_SKIP_TIDB_TESTS", "").lower() in (
    "1",
    "true",
    "yes",
)
pytestmark = pytest.mark.skipif(
    SKIP_TIDB_TESTS,
    reason="PYTIDB_SKIP_TIDB_TESTS is set; image embedding tests require TiDB",
)


pet_images_dir = Path("./tests/fixtures/pet_images")


EMBEDDING_MODELS = [
    {
        "id": "jinaai",
        "model_name": "jina_ai/jina-clip-v2",
    },
    {
        "id": "bedrock",
        "model_name": "bedrock/amazon.titan-embed-image-v1",
    },
]


@pytest.fixture(
    scope="module",
    params=EMBEDDING_MODELS,
    ids=[model["id"] for model in EMBEDDING_MODELS],
)
def image_embed(request):
    """Create EmbeddingFunction instances for each model in EMBEDDING_MODELS."""
    model_config = request.param
    embed_fn = EmbeddingFunction(
        model_name=model_config["model_name"],
        multimodal=True,
        timeout=30,
    )
    # Add model config for table naming
    embed_fn._model_config = model_config
    return embed_fn


@pytest.fixture(scope="module")
def pet_table(shared_client: TiDBClient, image_embed: EmbeddingFunction):
    """Pet table fixture that creates tables based on the image_embed fixture."""
    model_id = image_embed._model_config["id"]

    class PetBase(TableModel, table=False):
        __tablename__ = f"test_image_embedding_pets_{model_id}"
        id: int = Field(primary_key=True)
        nickname: str
        breed: str
        image_uri: Optional[str] = Field(default=None)
        image_vec: Optional[list[float]] = image_embed.VectorField(
            distance_metric="l2",
            source_field="image_uri",
            source_type="image",  # Configure the source field as image.
            index=False,
        )

    Pet = type(f"Pet_{model_id}", (PetBase,), {})

    # Create table.
    tbl = shared_client.create_table(schema=Pet, if_exists="overwrite")

    # INSERT.
    tbl.insert(
        Pet(
            nickname="Cookie",
            breed="scottish_terrier",
            image_uri=pet_images_dir / "scottish_terrier_161.jpg",
        )
    )
    tbl.bulk_insert(
        [
            Pet(
                nickname="Coco",
                breed="scottish_terrier",
                image_uri=pet_images_dir / "scottish_terrier_166.jpg",
            ),
            Pet(
                nickname="Pudding",
                breed="shiba_inu",
                # With no image_uri, the image_vec will be None.
            ),
        ]
    )

    # UPDATE.
    original_pet = tbl.query({"nickname": "Pudding"}).to_list()[0]
    assert original_pet["image_vec"] is None
    tbl.update(
        {
            "image_uri": pet_images_dir / "shiba_inu_16.jpg",
        },
        {"nickname": "Pudding"},
    )
    updated_pet = tbl.query({"nickname": "Pudding"}).to_list()[0]
    assert updated_pet["image_vec"] is not None

    return tbl


def test_image_search_with_query_text(pet_table: Table, image_embed: EmbeddingFunction):
    """Unified test for image search with query text for all embedding models."""
    results = (
        pet_table.search(query="shiba inu dog").distance_metric("l2").limit(1).to_list()
    )
    assert len(results) == 1
    for pet in results:
        assert pet["nickname"] in ["Pudding"]
        assert pet["breed"] in ["shiba_inu"]
        assert pet["image_uri"].endswith("shiba_inu_16.jpg")
        assert len(pet["image_vec"]) == image_embed.dimensions
        assert pet["_distance"] < 1.5


def test_image_search_with_image_path(pet_table: Table, image_embed: EmbeddingFunction):
    """Unified test for image search with image path for all embedding models."""
    query_image = pet_images_dir / "shiba_inu_15.jpg"

    results = (
        pet_table.search(query=query_image).distance_metric("l2").limit(1).to_list()
    )
    assert len(results) == 1
    for pet in results:
        assert pet["nickname"] in ["Pudding"]
        assert pet["breed"] in ["shiba_inu"]
        assert pet["image_uri"].endswith("shiba_inu_16.jpg")
        assert len(pet["image_vec"]) == image_embed.dimensions
        assert pet["_distance"] < 0.7


def test_image_search_with_pil_image(pet_table: Table, image_embed: EmbeddingFunction):
    """Unified test for image search with PIL Image for all embedding models."""
    from PIL import Image

    query_image = Image.open(pet_images_dir / "shiba_inu_15.jpg")
    results = (
        pet_table.search(query=query_image).distance_metric("l2").limit(1).to_list()
    )

    assert len(results) == 1
    for pet in results:
        assert pet["nickname"] in ["Pudding"]
        assert pet["breed"] in ["shiba_inu"]
        assert pet["image_uri"].endswith("shiba_inu_16.jpg")
        assert len(pet["image_vec"]) == image_embed.dimensions
        assert pet["_distance"] < 0.7
