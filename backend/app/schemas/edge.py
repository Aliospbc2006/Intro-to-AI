from pydantic import BaseModel

class EdgeGeometry(BaseModel):
    # Danh sách điểm [lon, lat]; mỗi đoạn nối có đúng 2 điểm (tọa độ hai ga)
    coordinates: list[list[float]]
    type: str = "LineString"

# Các schema Edge* mô tả một đoạn nối giữa hai ga theo cấu trúc GeoJSON (LineString = một segment)
class EdgeProperties(BaseModel):
    id: int
    start: int      # id ga đầu (properties.id của node)
    end: int        # id ga cuối
    length: float   # độ dài (mét); là trọng số của cạnh trong A*
    line: str       # mã tuyến: G, M, H, T, C, Y, Z, N, F
    color: str      # màu tuyến dạng hex RRGGBB, không có dấu '#'
    active: bool    # False = đoạn nối đang bị ban

class EdgeFeature(BaseModel):
    type: str = "Feature"
    geometry: EdgeGeometry
    properties: EdgeProperties

class EdgeFeatureCollection(BaseModel):
    type: str = "FeatureCollection"
    features: list[EdgeFeature]