from fastapi import APIRouter, HTTPException, status, Path, Body

from app.schemas.edge import EdgeFeatureCollection, EdgeFeature
from app.crud.edge import read_edges, read_edge, update_edge_active_status, read_edges_by_active_status

router = APIRouter(prefix="/edges", tags=["edges"])

@router.get("/", response_model=EdgeFeatureCollection)
async def get_edges(active: bool | None = None):
    # Không truyền ?active thì trả tất cả đoạn nối; ?active=true/false lọc theo trạng thái ban
    if active is not None:
        return await read_edges_by_active_status(is_active=active)
    return await read_edges()

@router.get("/{id}", response_model=EdgeFeature)
async def get_edge(id: int = Path(ge=1)):
    edge = await read_edge(id=id)
    if not edge:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Edge not found")
    return edge

# Ban/unban một đoạn nối. Body là giá trị JSON thuần true/false (không bọc trong object) vì Body() chỉ có một tham số.
@router.patch("/{id}")
async def set_edge_active_status(id: int = Path(ge=1), active: bool = Body()):
    edge = await read_edge(id)
    if not edge:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Edge not found")
    if edge.properties.active == active:
        return {"message": "No change nedded", "active": active}
    await update_edge_active_status(id, active)
    return {"message": "Active status updated", "active": active}