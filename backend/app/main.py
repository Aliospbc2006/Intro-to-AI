from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.api.api import api_router
from app.crud.node import create_collection_nodes, drop_collection_nodes
from app.crud.edge import create_collection_edges, drop_collection_edges

@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_collection_nodes()
    await create_collection_edges()
    yield
    await drop_collection_edges()
    await drop_collection_nodes()

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins = ["http://localhost:5500", "http://127.0.0.1:5500"],
    allow_methods=["GET", "PATCH"],
    allow_headers=["*"],
    allow_credentials = True
)

app.include_router(api_router)