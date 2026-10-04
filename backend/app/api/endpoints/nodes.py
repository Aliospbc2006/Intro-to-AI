from fastapi import APIRouter, HTTPException, status, Path, Body

from app.schemas.node import NodeFeatureCollection, NodeFeature
from app.crud.node import read_nodes, read_node, update_node_active_status, read_nodes_by_active_status

router = APIRouter(prefix="/nodes", tags=["nodes"])

@router.get("/", response_model=NodeFeatureCollection)
async def get_nodes(active: bool | None = None):
    # Không truyền ?active thì trả tất cả ga; ?active=true/false lọc theo trạng thái ban (false = đang bị ban)
    if active is not None:
        return await read_nodes_by_active_status(is_active=active)
    return await read_nodes()

@router.get("/{id}", response_model=NodeFeature)
async def get_node(id: int = Path(ge=1)):
    node = await read_node(id=id)
    if not node:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Node not found")
    return node

# Ban/unban một ga. Body là giá trị JSON thuần true/false (không bọc trong object) vì Body() chỉ có một tham số.
@router.patch("/{id}")
async def set_node_active_status(id: int = Path(ge=1), active: bool = Body()):
    node = await read_node(id=id)
    if not node:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Node not found")
    if node.properties.active == active:
        return {"message": "No change nedded", "active": active}
    await update_node_active_status(id, active)
    return {"message": "Active status updated", "active": active}