from pydantic import BaseModel
from app.schemas.node import NodeFeature
from app.schemas.edge import EdgeFeature

# Kết quả tìm đường: GeoJSON FeatureCollection chứa cả Point (ga) và LineString (đoạn nối)
class PathFeatureCollectionProperties(BaseModel):
    id: list[int]       # id các ga theo thứ tự đi (n phần tử)
    name: list[str]     # tên ga, cùng thứ tự với id
    line: list[str]     # tuyến của từng đoạn, line[i] nối id[i] -> id[i+1] (n - 1 phần tử)
    total_transfers: int
    length: float       # tổng độ dài các đoạn (mét), không tính phí đổi tuyến

class PathFeatureCollection(BaseModel):
    type: str = "FeatureCollection"
    # Union: mỗi feature được validate là NodeFeature hoặc EdgeFeature tùy geometry
    features: list[NodeFeature | EdgeFeature]
    properties: PathFeatureCollectionProperties