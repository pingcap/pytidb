from pathlib import Path
import pytest

from sqlmodel import Field

from pytidb import TiDBClient
from pytidb.schema import TableModel, DistanceMetric
from pytidb.table import Table
from pytidb.embeddings import EmbeddingFunction


@pytest.fixture
def image_embed_fn():
    return EmbeddingFunction(model_name="jina_ai/jina-embeddings-v4")


@pytest.fixture
def pet_table(client: TiDBClient, image_embed_fn: EmbeddingFunction):
    class Pet(TableModel):
        __tablename__ = "pets"
        id: int = Field(primary_key=True)
        nickname: str = Field()  # Pet nickname
        breed: str = Field()  # Pet breed
        image_uri: str = Field()
        image_vec: list[float] = image_embed_fn.VectorField(
            distance_metric=DistanceMetric.COSINE,
            source_field="image_uri",
            source_type="image",
        )

    tbl = client.create_table(schema=Pet, mode="overwrite")
    return tbl


def test_image_search_with_local_path(
    pet_table: Table, image_embed_fn: EmbeddingFunction
):
    Pet = pet_table.table_model
    pet_images_dir = Path("./tests/fixtures/pet_images")
    pet_table.insert(
        Pet(
            nickname="Cookie",
            breed="scottish_terrier",
            image_uri=pet_images_dir / "scottish_terrier_161.jpg",
        )
    )
    pet_table.bulk_insert(
        [
            Pet(
                nickname="Coco",
                breed="scottish_terrier",
                image_uri=pet_images_dir / "scottish_terrier_166.jpg",
            ),
            Pet(
                nickname="Pudding",
                breed="shiba_inu",
                image_uri=pet_images_dir / "shiba_inu_15.jpg",
            ),
        ]
    )

    # Text to image search.
    results = (
        pet_table.search(query="shiba inu dog", search_type="vector")
        .distance_metric(DistanceMetric.COSINE)
        .limit(1)
        .to_list()
    )
    assert len(results) == 1
    for pet in results:
        assert pet["nickname"] in ["Pudding"]
        assert pet["breed"] in ["shiba_inu"]
        assert pet["image_uri"].endswith("shiba_inu_15.jpg")
        assert len(pet["image_vec"]) == image_embed_fn.dimensions
        assert pet["_distance"] < 0.2

    # Image to image search.
    query_image = pet_images_dir / "shiba_inu_4.jpg"
    results = (
        pet_table.search(query=query_image, search_type="vector")
        .distance_metric(DistanceMetric.COSINE)
        .limit(1)
        .to_list()
    )
    assert len(results) == 1
    for pet in results:
        assert pet["nickname"] in ["Pudding"]
        assert pet["breed"] in ["shiba_inu"]
        assert pet["image_uri"].endswith("shiba_inu_15.jpg")
        assert len(pet["image_vec"]) == image_embed_fn.dimensions
        assert pet["_distance"] < 0.1
