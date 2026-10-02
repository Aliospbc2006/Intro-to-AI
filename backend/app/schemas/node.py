from pydantic import BaseModel

class NodeGeometry(BaseModel):
    coordinates: list[float]
    type: str = "Point"

class NodeProperties(BaseModel):
    id: int
    name: str
    active: bool

class NodeFeature(BaseModel):
    type: str = "Feature"
    geometry: NodeGeometry
    properties: NodeProperties

class NodeFeatureCollection(BaseModel):
    type: str = "FeatureCollection"
    features: list[NodeFeature]