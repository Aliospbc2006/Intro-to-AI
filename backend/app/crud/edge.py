import json

from app.core.config import settings
from app.core.database import db
from app.schemas.edge import EdgeFeature, EdgeFeatureCollection

async def create_collection_edges():
    collections = await db.list_collection_names()
    if "edges" not in collections:
        await db.create_collection("edges")
        await db.edges.create_index({"geometry": "2dsphere"})
        await db.edges.create_index({"properties.id": 1})
        await db.edges.create_index({"properties.start": 1, "properties.end": 1})
    if await db.edges.count_documents({}) > 0:
        return
    with open(settings.BASE_DIR / "data" / "edges.json", "r", encoding="utf-8") as f:
        data = json.load(f)
        await db.edges.insert_many(data)

async def drop_collection_edges():
    collections = await db.list_collection_names()
    if "edges" in collections:
        await db.drop_collection("edges")

async def read_edges() -> EdgeFeatureCollection:
    edges = await db.edges.find({}, {"_id": 0}).to_list()
    return EdgeFeatureCollection(features=edges)

async def read_edge(id: int) -> EdgeFeature:
    edge = await db.edges.find_one({"properties.id": id}, {"_id": 0})
    if not edge:
        return None
    return EdgeFeature.model_validate(edge)

async def update_edge_active_status(id: int, active: bool):
    await db.edges.update_one({"properties.id": id}, {"$set": {"properties.active": active}})

async def read_edges_by_active_status(is_active: bool = False) -> EdgeFeatureCollection:
    cursor = db.edges.find({"properties.active": is_active}, {"_id": 0})
    edges = await cursor.to_list()
    return EdgeFeatureCollection(features=edges)