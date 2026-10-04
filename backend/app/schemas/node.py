from pydantic import BaseModel

# Các schema Node* mô tả một ga theo cấu trúc GeoJSON (Point = một station)
class NodeGeometry(BaseModel):
    coordinates: list[float]    # [lon, lat]
    type: str = "Point"

class NodeProperties(BaseModel):
    id: int
    name: str
    active: bool    # False = ga đang bị ban

class NodeFeature(BaseModel):
    type: str = "Feature"
    geometry: NodeGeometry
    properties: NodeProperties

class NodeFeatureCollection(BaseModel):
    type: str = "FeatureCollection"
    features: list[NodeFeature]