from fastapi import APIRouter, Query
from app.services.path_finding import get_node_map, get_graph, find_nearest_node, a_star, path_feature_collection

router = APIRouter(prefix="/path", tags=["path"])

@router.get("/")
async def path_finding(
    lon1: float = Query(ge=-180, le=180),
    lat1: float = Query(ge=-90, le=90),
    lon2: float = Query(ge=-180, le=180),
    lat2: float = Query(ge=-90, le=90),
    penalty: int = Query(default=0, ge=0)
):
    start = await find_nearest_node(longitude=lon1, latitude=lat1)
    end = await find_nearest_node(longitude=lon2, latitude=lat2)
    graph = await get_graph()
    node_map = await get_node_map()
    
    path = a_star(start, end, penalty, graph, node_map)
    if path is None:
        return {"message": "Path not found"}
    return await path_feature_collection(path)

@router.get("/graph")
async def graph():
    return await get_graph()

@router.get("/nodemap")
async def node_map():
    return await get_node_map()