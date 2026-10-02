from fastapi import APIRouter
from app.api.endpoints import nodes, edges, path

api_router = APIRouter()
api_router.include_router(nodes.router)
api_router.include_router(edges.router)
api_router.include_router(path.router)