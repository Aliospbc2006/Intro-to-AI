# Xây graph từ MongoDB và tìm đường bằng A*.
# Luồng chính của request /path/:
#   MongoDB (nodes, edges) -> graph + node_map -> a_star -> path_feature_collection -> GeoJSON response
# Mọi khoảng cách và chi phí trong file này đều tính bằng mét.
import heapq, math
from app.core.database import db
from app.schemas.path import PathFeatureCollection

async def get_node_map() -> dict:
    # node_map[node_id] = (lon, lat). Chỉ phục vụ heuristic nên chỉ cần tọa độ.
    # Lưu ý thứ tự (lon, lat): GeoJSON luôn là [kinh độ, vĩ độ].
    node_map = {}

    # Chỉ lấy ga active và có ít nhất một đoạn nối active; ga bị ban hoặc bị cô lập không cần cho A*.
    edge_filter = {"properties.active": True}
    starts = await db.edges.distinct("properties.start", edge_filter)
    ends = await db.edges.distinct("properties.end", edge_filter)
    connected_nodes = list(set(starts + ends))

    # Projection chỉ lấy id + tọa độ để giảm dữ liệu đọc từ MongoDB
    cursor = db.nodes.find(
        {
            "properties.active": True,
            "properties.id": {"$in": connected_nodes}
        },
        {
            "properties.id": 1,
            "geometry.coordinates": 1,
            "_id": 0
        }
    )
    async for node in cursor:
        id = node["properties"]["id"]
        coordinates = node["geometry"]["coordinates"]
        node_map[id] = (coordinates[0], coordinates[1])
    return node_map

async def get_graph() -> dict:
    # Ga bị ban (active = False) bị loại khỏi graph: mọi đoạn nối chạm vào ga đó sẽ bị bỏ qua ở bước dưới.
    active_nodes = set()
    async for node in db.nodes.find({"properties.active": True}, {"properties.id": 1, "_id": 0}):
        active_nodes.add(node["properties"]["id"])

    # Cấu trúc graph:
    #   graph[node_id][line] = [(neighbor_id, edge_length), ...]
    # Mỗi ga có danh sách ga kề được tách theo tuyến, nhờ vậy A* biết đang đi trên tuyến nào
    # và tính được phí đổi tuyến. Ví dụ: graph[id_Otemachi]["M"] chỉ chứa các ga kề trên tuyến M.
    graph = {}
    cursor = db.edges.find(
        {"properties.active": True},
        {
            "properties.start": 1,
            "properties.end": 1,
            "properties.length": 1,
            "properties.line": 1,
            "_id": 0
        }
    )
    async for edge in cursor:
        start = edge["properties"]["start"]
        end = edge["properties"]["end"]
        weight = edge["properties"]["length"]
        line = edge["properties"]["line"]
        # Chỉ giữ đoạn nối khi cả hai đầu ga còn active
        if start in active_nodes and end in active_nodes:
            # Khởi tạo graph[node][line] cho cả hai đầu của cạnh nếu chưa có
            if start not in graph:
                graph[start] = {}
            if end not in graph:
                graph[end] = {}
            if line not in graph[start]:
                graph[start][line] = []
            if line not in graph[end]:
                graph[end][line] = []
            # Mỗi edge trong DB chỉ lưu một lần (start -> end) nhưng tàu đi được hai chiều,
            # nên thêm vào graph theo cả hai hướng.
            graph[start][line].append((end, weight))
            graph[end][line].append((start, weight))
    return graph

async def find_nearest_node(longitude: float, latitude: float) -> int:
    # $nearSphere trả về document gần điểm cho trước nhất (khoảng cách trên mặt cầu) và cần
    # 2dsphere index trên "geometry" (được tạo trong crud/node.py).
    # Filter active: ga bị ban không được chọn, điểm click sẽ "dính" vào ga active gần nhất.
    node = await db.nodes.find_one(
        {
            "geometry": {
                "$nearSphere": {
                    "$geometry": {
                        "type": "Point",
                        "coordinates": [longitude, latitude]
                    }
                }
            },
            "properties.active": True
        },
        {"_id": 0, "properties.id": 1}
    )
    return node["properties"]["id"]

def heuristic(start: int, end: int, node_map: dict):
    # h(n) của A*: khoảng cách haversine (đường chim bay trên mặt cầu bán kính Trái Đất)
    # giữa hai ga, tính bằng mét.
    # Heuristic này không bao giờ ước lượng quá chi phí thật (admissible) vì length của mỗi cạnh trong
    # dataset luôn >= haversine giữa hai đầu cạnh (xem scripts/tokyo_metro/build_dataset.py),
    # còn phí đổi tuyến chỉ làm chi phí thật lớn thêm.
    lon1, lat1 = node_map[start]
    lon2, lat2 = node_map[end]
    # phi = vĩ độ, lambda = kinh độ, đều đổi sang radian
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = phi2-phi1
    dlambda = math.radians(lon2-lon1)
    # a = sin²(Δφ/2) + cos φ1 · cos φ2 · sin²(Δλ/2); c = góc ở tâm Trái Đất giữa hai điểm (radian)
    a = math.sin(dphi/2)**2 + math.cos(phi1) * math.cos(phi2) * (math.sin(dlambda/2)**2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    # 6371000 = bán kính Trái Đất (m) -> độ dài cung = R * c
    return 6371000 * c

def a_star(start: int, end: int, penalty: int, graph: dict, node_map: dict):
    # fringe: hàng đợi ưu tiên (min-heap của heapq) chứa các state chờ mở rộng.
    # Tuple trong heap: (f_score, g_score, node_id, current_line), với f = g + h.
    # heapq so sánh tuple từ phần tử đầu nên state có f nhỏ nhất luôn được lấy ra trước.
    fringe = []
    # g_score[(node_id, line)] = chi phí thực tế nhỏ nhất đã biết từ ga xuất phát tới state đó
    # (tổng độ dài cạnh + phí đổi tuyến).
    g_score = {}
    # came_from[state] = state liền trước trên đường tốt nhất tới state này (None với state xuất phát).
    # Dùng để truy ngược lại đường đi sau khi A* tìm thấy ga đích.
    came_from = {}
    inf = math.inf

    # Ga xuất phát không có cạnh active nào (bị ban hoặc bị cô lập) thì không có đường đi
    start_node_data = graph.get(start, {})
    if not start_node_data: return None

    # Mọi state xuất phát đều ở cùng một ga nên dùng chung giá trị h
    h_start = heuristic(start, end, node_map)
    
    # Mỗi tuyến đi qua ga xuất phát là một state xuất phát riêng với g = 0,
    # nên việc chọn tuyến đầu tiên không bị tính phí đổi tuyến.
    for line in start_node_data.keys():
        # State gồm cả ga và tuyến đang đi.
        # Cùng một ga nhưng đang ở hai tuyến khác nhau được xem là hai state khác nhau,
        # nhờ vậy thuật toán có thể tính chi phí đổi tuyến.
        state = (start, line)
        g_score[state] = 0
        heapq.heappush(fringe, (h_start, 0, start, line))
        came_from[state] = None

    while fringe:
        # Lấy state có f nhỏ nhất. Việc kiểm tra đích diễn ra lúc pop (không phải lúc push)
        # để đảm bảo đường đầu tiên tới đích là tối ưu; tới đích bằng tuyến nào cũng được.
        current_f, current_g, current_node, current_line = heapq.heappop(fringe)

        if current_node == end:
            # Truy ngược came_from từ đích về xuất phát rồi đảo lại.
            # path là list các state (node_id, line); line ở path[i+1] là tuyến dùng
            # để đi từ path[i] sang path[i+1] (line của path[0] chỉ là tuyến xuất phát).
            path = []
            current_state = (current_node, current_line)
            while current_state is not None:
                path.append(current_state) 
                current_state = came_from[current_state]
            path.reverse()
            return path

        # heapq không có thao tác decrease-key nên một state có thể được push nhiều lần với g khác nhau.
        # Entry cũ (g lớn hơn g_score hiện tại) đã lỗi thời, bỏ qua.
        if current_g > g_score.get((current_node, current_line), inf):
            continue
        
        # Duyệt các cạnh đi ra từ ga hiện tại, nhóm theo tuyến
        node_data = graph.get(current_node, {})
        for line, neighbors in node_data.items():
            # Nếu cạnh tiếp theo thuộc tuyến khác với tuyến hiện tại,
            # cộng thêm penalty để thuật toán ưu tiên các route ít đổi tuyến hơn.
            # Phí được cộng vào cạnh đầu tiên của tuyến mới (không có cạnh riêng cho việc đổi tuyến trong ga).
            if line != current_line:
                transfer_fee = penalty
            else:
                transfer_fee = 0

            for neighbor, weight in neighbors:
                next_state = (neighbor, line)
                # g mới = g hiện tại + độ dài cạnh + phí đổi tuyến (nếu có)
                tentative_g_score = current_g + weight + transfer_fee
                
                # Tìm được đường tới next_state tốt hơn đường đã biết:
                # cập nhật g, ghi lại state trước đó và đẩy vào heap với f = g + h.
                if tentative_g_score < g_score.get(next_state, inf):
                    g_score[next_state] = tentative_g_score
                    f_score = tentative_g_score + heuristic(neighbor, end, node_map)
                    came_from[next_state] = (current_node, current_line)
                    heapq.heappush(fringe, (f_score, tentative_g_score, neighbor, line))
    # Heap cạn mà chưa tới đích: hai ga không nối được với nhau (do các ga/đoạn đang bị ban)
    return None

async def path_feature_collection(path: list[tuple[int, str]]):
    # Chuyển path (list state (node_id, line) từ a_star) thành GeoJSON FeatureCollection cho frontend.
    # path_id có độ dài n (mỗi ga một phần tử); path_line có độ dài n - 1:
    # path_line[i] là tuyến của đoạn đi từ path_id[i] tới path_id[i+1].
    path_id = []
    path_line = []
    for i in range(len(path)):
        if i != 0:
            path_line.append(path[i][1])
        path_id.append(path[i][0])

    # Mỗi lần tuyến của hai đoạn liên tiếp khác nhau là một lần đổi tuyến
    total_transfers = 0
    for i in range(len(path_line)-1):
        if path_line[i] != path_line[i+1]:
            total_transfers += 1
    
    # Point features của các ga trên đường đi. $in không đảm bảo thứ tự theo path,
    # thứ tự ga thật nằm trong properties.id của response.
    nodes = await db.nodes.find(
        {"properties.id": {"$in": path_id}},
        {"_id": 0}
    ).to_list()

    # Lưu ý: node_map ở đây là {node_id: tên ga}, khác với node_map (tọa độ) của get_node_map()
    node_map = {}
    for node in nodes:
        node_map[node["properties"]["id"]] = node["properties"]["name"]
    path_name = []
    for id in path_id:
        path_name.append(node_map[id])

    # LineString features: với mỗi cặp ga liên tiếp, tìm đoạn nối thuộc đúng tuyến đã đi.
    # Edge trong DB lưu một hướng nên phải thử cả hai hướng start/end.
    edges = []
    total_length = 0
    for i in range(len(path) - 1):
        start_node, _ = path[i]
        end_node, end_line = path[i+1]

        edge = await db.edges.find_one({
            "properties.line": end_line,
            "$or": [
                {"properties.start": start_node, "properties.end": end_node},
                {"properties.start": end_node, "properties.end": start_node}
            ]
        }, {"_id": 0})

        edges.append(edge)
        total_length += edge["properties"]["length"]

    # properties của cả FeatureCollection: tóm tắt tuyến đường (length là tổng độ dài cạnh, không gồm penalty)
    properties = {
        "id": path_id,
        "name": path_name,
        "line": path_line,
        "total_transfers": total_transfers,
        "length": total_length,
    }
    
    return PathFeatureCollection(features = edges + nodes, properties = properties)