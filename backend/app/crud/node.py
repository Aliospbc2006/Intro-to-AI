import json

from app.core.config import settings
from app.core.database import db
from app.schemas.node import NodeFeature, NodeFeatureCollection

async def create_collection_nodes():
    collections = await db.list_collection_names()
    if "nodes" not in collections:
        await db.create_collection("nodes")
        await db.nodes.create_index({"geometry": "2dsphere"})
        await db.nodes.create_index({"properties.id": 1})
    if await db.nodes.count_documents({}) > 0:
        return
    with open(settings.BASE_DIR / "data" / "nodes.json", "r", encoding="utf-8") as f:
        data = json.load(f)
        await db.nodes.insert_many(data)

async def drop_collection_nodes():
    collections = await db.list_collection_names()
    if "nodes" in collections:
        await db.drop_collection("nodes")

async def read_nodes() -> NodeFeatureCollection:
    nodes = await db.nodes.find({}, {"_id": 0}).to_list()
    return NodeFeatureCollection(features=nodes)

async def read_node(id: int) -> NodeFeature:
    node = await db.nodes.find_one({"properties.id": id}, {"_id": 0})
    if not node:
        return None
    return NodeFeature.model_validate(node)

async def update_node_active_status(id: int, active: bool):
    await db.nodes.update_one({"properties.id": id}, {"$set": {"properties.active": active}})

async def read_nodes_by_active_status(is_active: bool = False) -> NodeFeatureCollection:
    cursor = db.nodes.find({"properties.active": is_active}, {"_id": 0})
    nodes = await cursor.to_list()
    return NodeFeatureCollection(features=nodes)