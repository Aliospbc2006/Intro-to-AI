from pydantic import BaseModel
from app.schemas.node import NodeFeature
from app.schemas.edge import EdgeFeature

class PathFeatureCollectionProperties(BaseModel):
    id: list[int]
    name: list[str]
    line: list[str]
    total_transfers: int
    length: float

class PathFeatureCollection(BaseModel):
    type: str = "FeatureCollection"
    features: list[NodeFeature | EdgeFeature]
    properties: PathFeatureCollectionProperties