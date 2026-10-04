import json

from app.core.config import settings
from app.core.database import db
from app.schemas.node import NodeFeature, NodeFeatureCollection

async def create_collection_nodes():
    collections = await db.list_collection_names()
    if "nodes" not in collections:
        await db.create_collection("nodes")
        # 2dsphere: bắt buộc cho truy vấn $nearSphere (tìm ga gần nhất) trong services/path_finding.py
        await db.nodes.create_index({"geometry": "2dsphere"})
        # properties.id không phải _id của MongoDB nên cần index riêng để tra cứu theo id nhanh
        await db.nodes.create_index({"properties.id": 1})
    # Đã có dữ liệu thì không seed lại, tránh nhân đôi document và giữ trạng thái active hiện tại
    if await db.nodes.count_documents({}) > 0:
        return
    # Seed: mỗi phần tử của nodes.json là một GeoJSON Feature (Point) và được lưu nguyên làm một document
    with open(settings.BASE_DIR / "data" / "nodes.json", "r", encoding="utf-8") as f:
        data = json.load(f)
        await db.nodes.insert_many(data)

async def drop_collection_nodes():
    collections = await db.list_collection_names()
    if "nodes" in collections:
        await db.drop_collection("nodes")

async def read_nodes() -> NodeFeatureCollection:
    # Projection {"_id": 0}: bỏ ObjectId do MongoDB tự thêm vì không thuộc schema GeoJSON trả về
    nodes = await db.nodes.find({}, {"_id": 0}).to_list()
    return NodeFeatureCollection(features=nodes)

async def read_node(id: int) -> NodeFeature:
    node = await db.nodes.find_one({"properties.id": id}, {"_id": 0})
    if not node:
        return None
    return NodeFeature.model_validate(node)

async def update_node_active_status(id: int, active: bool):
    # Ban/unban chỉ đổi cờ properties.active; document không bị xóa.
    # get_graph / find_nearest_node lọc theo cờ này nên ga bị ban sẽ không xuất hiện trong kết quả tìm đường.
    await db.nodes.update_one({"properties.id": id}, {"$set": {"properties.active": active}})

async def read_nodes_by_active_status(is_active: bool = False) -> NodeFeatureCollection:
    cursor = db.nodes.find({"properties.active": is_active}, {"_id": 0})
    nodes = await cursor.to_list()
    return NodeFeatureCollection(features=nodes)