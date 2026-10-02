from pydantic import BaseModel

class EdgeGeometry(BaseModel):
    coordinates: list[list[float]]
    type: str = "LineString"

class EdgeProperties(BaseModel):
    id: int
    start: int
    end: int
    length: float
    line: str
    color: str
    active: bool

class EdgeFeature(BaseModel):
    type: str = "Feature"
    geometry: EdgeGeometry
    properties: EdgeProperties

class EdgeFeatureCollection(BaseModel):
    type: str = "FeatureCollection"
    features: list[EdgeFeature]