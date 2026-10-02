import heapq, math
from app.core.database import db
from app.schemas.path import PathFeatureCollection

async def get_node_map() -> dict:
    node_map = {}

    edge_filter = {"properties.active": True}
    starts = await db.edges.distinct("properties.start", edge_filter)
    ends = await db.edges.distinct("properties.end", edge_filter)
    connected_nodes = list(set(starts + ends))

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
    active_nodes = set()
    async for node in db.nodes.find({"properties.active": True}, {"properties.id": 1, "_id": 0}):
        active_nodes.add(node["properties"]["id"])

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
        if start in active_nodes and end in active_nodes:
            if start not in graph:
                graph[start] = {}
            if end not in graph:
                graph[end] = {}
            if line not in graph[start]:
                graph[start][line] = []
            if line not in graph[end]:
                graph[end][line] = []
            graph[start][line].append((end, weight))
            graph[end][line].append((start, weight))
    return graph

async def find_nearest_node(longitude: float, latitude: float) -> int:
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
    lon1, lat1 = node_map[start]
    lon2, lat2 = node_map[end]
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = phi2-phi1
    dlambda = math.radians(lon2-lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1) * math.cos(phi2) * (math.sin(dlambda/2)**2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return 6371000 * c

def a_star(start: int, end: int, penalty: int, graph: dict, node_map: dict):
    fringe = []
    g_score = {}
    came_from = {}
    inf = math.inf

    start_node_data = graph.get(start, {})
    if not start_node_data: return None

    h_start = heuristic(start, end, node_map)
    
    for line in start_node_data.keys():
        state = (start, line)
        g_score[state] = 0
        heapq.heappush(fringe, (h_start, 0, start, line))
        came_from[state] = None

    while fringe:
        current_f, current_g, current_node, current_line = heapq.heappop(fringe)

        if current_node == end:
            path = []
            current_state = (current_node, current_line)
            while current_state is not None:
                path.append(current_state) 
                current_state = came_from[current_state]
            path.reverse()
            return path

        if current_g > g_score.get((current_node, current_line), inf):
            continue
        
        node_data = graph.get(current_node, {})
        for line, neighbors in node_data.items():
            if line != current_line:
                transfer_fee = penalty
            else:
                transfer_fee = 0

            for neighbor, weight in neighbors:
                next_state = (neighbor, line)
                tentative_g_score = current_g + weight + transfer_fee
                
                if tentative_g_score < g_score.get(next_state, inf):
                    g_score[next_state] = tentative_g_score
                    f_score = tentative_g_score + heuristic(neighbor, end, node_map)
                    came_from[next_state] = (current_node, current_line)
                    heapq.heappush(fringe, (f_score, tentative_g_score, neighbor, line))
    return None

async def path_feature_collection(path: list[tuple[int, str]]):
    path_id = []
    path_line = []
    for i in range(len(path)):
        if i != 0:
            path_line.append(path[i][1])
        path_id.append(path[i][0])

    total_transfers = 0
    for i in range(len(path_line)-1):
        if path_line[i] != path_line[i+1]:
            total_transfers += 1
    
    nodes = await db.nodes.find(
        {"properties.id": {"$in": path_id}},
        {"_id": 0}
    ).to_list()

    node_map = {}
    for node in nodes:
        node_map[node["properties"]["id"]] = node["properties"]["name"]
    path_name = []
    for id in path_id:
        path_name.append(node_map[id])

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

    properties = {
        "id": path_id,
        "name": path_name,
        "line": path_line,
        "total_transfers": total_transfers,
        "length": total_length,
    }
    
    return PathFeatureCollection(features = edges + nodes, properties = properties)