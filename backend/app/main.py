from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.api.api import api_router
from app.crud.node import create_collection_nodes, drop_collection_nodes
from app.crud.edge import create_collection_edges, drop_collection_edges

# Entry point của backend (chạy bằng `fastapi dev app/main.py`, xem How_to_run.md).
# Luồng dữ liệu: backend/app/data/*.json -> MongoDB -> API (/nodes, /edges, /path) -> frontend (Leaflet)

# lifespan chạy một lần khi server khởi động (trước yield) và một lần khi tắt server (sau yield).
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Khởi động: tạo collection + index và nạp dataset từ file JSON nếu collection còn trống
    await create_collection_nodes()
    await create_collection_edges()
    yield
    # Tắt server: xóa hai collection, nên trạng thái ban/unban (properties.active) không được giữ lại
    # giữa các lần chạy; lần khởi động sau dataset được nạp lại từ file JSON.
    await drop_collection_edges()
    await drop_collection_nodes()

app = FastAPI(lifespan=lifespan)

# Cho phép frontend (static server ở cổng 5500) gọi API khác origin (cổng 8000).
# PATCH cần cho ban/unban, GET cho các truy vấn còn lại.
app.add_middleware(
    CORSMiddleware,
    allow_origins = ["http://localhost:5500", "http://127.0.0.1:5500"],
    allow_methods=["GET", "PATCH"],
    allow_headers=["*"],
    allow_credentials = True
)

app.include_router(api_router)