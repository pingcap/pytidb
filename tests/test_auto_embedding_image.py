from pathlib import Path
from typing import Optional
import pytest

from pytidb import TiDBClient
from pytidb.schema import TableModel, Field, DistanceMetric
from pytidb.table import Table
from pytidb.embeddings import EmbeddingFunction


pet_images_dir = Path("./tests/fixtures/pet_images")


@pytest.fixture(scope="module")
def image_embed_fn():
    return EmbeddingFunction(model_name="jina_ai/jina-embeddings-v4", timeout=60)


@pytest.fixture(scope="module")
def pet_table(shared_client: TiDBClient, image_embed_fn: EmbeddingFunction):
    class Pet(TableModel):
        __tablename__ = "pets"
        id: int = Field(primary_key=True)
        nickname: str
        breed: str
        image_uri: Optional[str] = Field(default=None)
        image_vec: Optional[list[float]] = image_embed_fn.VectorField(
            distance_metric=DistanceMetric.COSINE,
            source_field="image_uri",
            source_type="image",  # Configure the source field as image.
        )

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


def test_image_search_with_query_text(
    pet_table: Table, image_embed_fn: EmbeddingFunction
):
    results = pet_table.search(query="shiba inu dog").limit(1).to_list()
    assert len(results) == 1
    for pet in results:
        assert pet["nickname"] in ["Pudding"]
        assert pet["breed"] in ["shiba_inu"]
        assert pet["image_uri"].endswith("shiba_inu_16.jpg")
        assert len(pet["image_vec"]) == image_embed_fn.dimensions
        assert pet["_distance"] < 0.3


def test_image_search_with_image_path(
    pet_table: Table, image_embed_fn: EmbeddingFunction
):
    query_image = pet_images_dir / "shiba_inu_15.jpg"
    results = pet_table.search(query=query_image).limit(1).to_list()
    assert len(results) == 1
    for pet in results:
        assert pet["nickname"] in ["Pudding"]
        assert pet["breed"] in ["shiba_inu"]
        assert pet["image_uri"].endswith("shiba_inu_16.jpg")
        assert len(pet["image_vec"]) == image_embed_fn.dimensions
        assert pet["_distance"] < 0.3


def test_image_search_with_pil_image(
    pet_table: Table, image_embed_fn: EmbeddingFunction
):
    from PIL import Image

    query_image = Image.open(pet_images_dir / "shiba_inu_15.jpg")
    results = pet_table.search(query=query_image).limit(1).to_list()

    assert len(results) == 1
    for pet in results:
        assert pet["nickname"] in ["Pudding"]
        assert pet["breed"] in ["shiba_inu"]
        assert pet["image_uri"].endswith("shiba_inu_16.jpg")
        assert len(pet["image_vec"]) == image_embed_fn.dimensions
        assert pet["_distance"] < 0.3


# Bedrock Tests


@pytest.fixture(scope="module")
def bedrock_image_embed_fn():
    return EmbeddingFunction(
        model_name="bedrock/amazon.titan-embed-image-v1", timeout=60
    )


@pytest.fixture(scope="module")
def bedrock_pet_table(client: TiDBClient, bedrock_image_embed_fn: EmbeddingFunction):
    class BedrockPet(TableModel):
        __tablename__ = "bedrock_pets"
        id: int = Field(primary_key=True)
        nickname: str
        breed: str
        image_uri: Optional[str] = Field(default=None)
        image_vec: Optional[list[float]] = bedrock_image_embed_fn.VectorField(
            distance_metric=DistanceMetric.COSINE,
            source_field="image_uri",
            source_type="image",  # Configure the source field as image.
        )

    # Create table.
    tbl = client.create_table(schema=BedrockPet, if_exists="overwrite")

    # INSERT.
    tbl.insert(
        BedrockPet(
            nickname="Cookie",
            breed="scottish_terrier",
            image_uri=pet_images_dir / "scottish_terrier_161.jpg",
        )
    )
    tbl.bulk_insert(
        [
            BedrockPet(
                nickname="Coco",
                breed="scottish_terrier",
                image_uri=pet_images_dir / "scottish_terrier_166.jpg",
            ),
            BedrockPet(
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


def test_bedrock_image_search_with_query_text(
    bedrock_pet_table: Table, bedrock_image_embed_fn: EmbeddingFunction
):
    results = bedrock_pet_table.search(query="shiba inu dog").limit(1).to_list()
    assert len(results) == 1
    for pet in results:
        assert pet["nickname"] in ["Pudding"]
        assert pet["breed"] in ["shiba_inu"]
        assert pet["image_uri"].endswith("shiba_inu_16.jpg")
        assert len(pet["image_vec"]) == bedrock_image_embed_fn.dimensions
        # bedrock's model's ability is not good, so we skip the distance check
        # assert pet["_distance"] < 0.4


def test_bedrock_image_search_with_image_path(
    bedrock_pet_table: Table, bedrock_image_embed_fn: EmbeddingFunction
):
    query_image = pet_images_dir / "shiba_inu_16.jpg"
    results = bedrock_pet_table.search(query=query_image).limit(1).to_list()
    assert len(results) == 1
    # bedrock's model's ability is not good, so we skip the result check
    for pet in results:
        assert pet["nickname"] in ["Pudding"]
        assert pet["breed"] in ["shiba_inu"]
        assert pet["image_uri"].endswith("shiba_inu_16.jpg")
        assert len(pet["image_vec"]) == bedrock_image_embed_fn.dimensions
        assert pet["_distance"] < 0.4


def test_bedrock_image_search_with_pil_image(
    bedrock_pet_table: Table, bedrock_image_embed_fn: EmbeddingFunction
):
    from PIL import Image

    query_image = Image.open(pet_images_dir / "shiba_inu_15.jpg")
    results = bedrock_pet_table.search(query=query_image).limit(1).to_list()

    assert len(results) == 1
    for pet in results:
        assert pet["nickname"] in ["Pudding"]
        assert pet["breed"] in ["shiba_inu"]
        assert pet["image_uri"].endswith("shiba_inu_16.jpg")
        assert len(pet["image_vec"]) == bedrock_image_embed_fn.dimensions
        assert pet["_distance"] < 0.4
