from fastapi import APIRouter, Query
from app.services.path_finding import get_node_map, get_graph, find_nearest_node, a_star, path_feature_collection

router = APIRouter(prefix="/path", tags=["path"])

@router.get("/")
async def path_finding(
    lon1: float = Query(ge=-180, le=180),
    lat1: float = Query(ge=-90, le=90),
    lon2: float = Query(ge=-180, le=180),
    lat2: float = Query(ge=-90, le=90),
    # penalty: phí (mét) cộng thêm mỗi lần đổi tuyến, cùng đơn vị với length của cạnh
    penalty: int = Query(default=0, ge=0)
):
    # Frontend gửi tọa độ hai điểm; chuyển thành hai ga active gần nhất làm điểm đầu/cuối
    start = await find_nearest_node(longitude=lon1, latitude=lat1)
    end = await find_nearest_node(longitude=lon2, latitude=lat2)
    # Graph và node_map được dựng lại từ MongoDB ở mỗi request, nên kết quả luôn phản ánh
    # trạng thái ban/unban mới nhất.
    graph = await get_graph()
    node_map = await get_node_map()
    
    path = a_star(start, end, penalty, graph, node_map)
    # Không có đường vẫn trả HTTP 200 với {"message": ...} (không có "features"); frontend dựa vào đó để báo lỗi
    if path is None:
        return {"message": "Path not found"}
    # Thành công: GeoJSON FeatureCollection gồm LineString (đoạn đi qua) + Point (ga) + properties tóm tắt
    return await path_feature_collection(path)

# Hai endpoint dưới đây trả dữ liệu thô để kiểm tra/debug graph và node_map
@router.get("/graph")
async def graph():
    return await get_graph()

@router.get("/nodemap")
async def node_map():
    return await get_node_map()