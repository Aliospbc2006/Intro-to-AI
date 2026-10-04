"""Build a Tokyo Metro dataset in the same GeoJSON shape as backend/app/data/nodes.json and edges.json.

This script only converts DATA. It contains no routing logic and is not used by the backend at runtime.

Inputs
  stations.csv
      Curated mapping, one row per station on a route, in route order.
      route        G, M, Mb, H, T, C, Y, Z, N, F (Mb = Marunouchi Honancho branch, written from the
                   junction outwards: M06 Nakano-sakaue, Mb05, Mb04, Mb03 Honancho)
      seq          position on the route (consecutive rows = one edge)
      code         official station number (M06 appears twice: on route M and as the junction of route Mb)
      line         graph line value written to edges.json (route Mb -> "M", decision D1)
      name_ja      station name as written in MLIT N02 (join key with the N02 file)
      name_en      English/Romaji name (Tokyo Metro style, no macrons)
      complex      approved different-name interchange complex (decision D3), empty otherwise
      code_source  wikidata = code found on Wikidata (CC0); official = checked against Tokyo Metro official
                   information during review (Phase 2A.1); junction = repeated M06 row of route Mb
  source/N02-25_Station_TokyoMetro.geojson
      MLIT 国土数値情報 鉄道データ N02-25, Station layer, features with N02_004 == 東京地下鉄 copied
      unchanged from N02-25_Station.geojson (https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-N02-2025.html).
      License CC BY 4.0. Attribution: 出典：国土数値情報（鉄道データ）（国土交通省）を加工して作成

Outputs
  output/nodes.json, output/edges.json

Rules
  Node     one node per physical station (same name_ja = same station, e.g. Otemachi on M/T/C/Z);
           the 9 approved complexes merge their two stations into one node named "Name A / Name B".
  Node id  primary code = member code with the lowest (prefix order, number);
           prefix order G=1 M=2 Mb=3 H=4 T=5 C=6 Y=7 Z=8 N=9 F=10;  id = order * 100 + number
           (G09 Ginza -> 109, Mb03 Honancho -> 303).
  Coord    N02 station feature -> mean of its vertices; station -> mean of its distinct N02 features
           (all lines); complex -> mean of its stations. Rounded to 6 decimals ([lon, lat], WGS84/JGD2011).
  Edge     consecutive rows of a route; ids 1..N in route order G, M, Mb, H, T, C, Y, Z, N, F.
           geometry = 2-point LineString [start coord, end coord].
           length = haversine(start, end) with R = 6371000 (same formula as path_finding.heuristic),
           rounded UP to 1 mm, so length >= heuristic(start, end) always holds.
  Color    visual/reference colors only (Wikidata P465, CC0), not verified official HEX.

Usage
  python scripts/tokyo_metro/build_dataset.py
"""
import csv
import json
import math
from pathlib import Path

HERE = Path(__file__).parent
STATIONS_CSV = HERE / "stations.csv"
N02_FILE = HERE / "source" / "N02-25_Station_TokyoMetro.geojson"
OUTPUT_DIR = HERE / "output"

ROUTE_ORDER = ["G", "M", "Mb", "H", "T", "C", "Y", "Z", "N", "F"]
CODE_PREFIX_ORDER = {"G": 1, "M": 2, "Mb": 3, "H": 4, "T": 5, "C": 6, "Y": 7, "Z": 8, "N": 9, "F": 10}

# N02_003 line name used for each route
N02_LINE = {
    "G": "3号線銀座線", "M": "4号線丸ノ内線", "Mb": "4号線丸ノ内線分岐線", "H": "2号線日比谷線",
    "T": "5号線東西線", "C": "9号線千代田線", "Y": "8号線有楽町線", "Z": "11号線半蔵門線",
    "N": "7号線南北線", "F": "13号線副都心線",
}
# N02 files F01-F05 (Wakoshi - Hikawadai) under 有楽町線 only, so these rows have no 副都心線 feature.
# Their coordinates come from the same station's Y01-Y05 features.
NOT_IN_N02 = {"F01", "F02", "F03", "F04", "F05"}

# Visual/reference colors (Wikidata P465, CC0). NOT official HEX values.
LINE_COLORS = {
    "G": "ff9501", "M": "f62f36", "H": "a0acad", "T": "019bbf", "C": "00a650",
    "Y": "bb8b38", "Z": "8f75d6", "N": "00ad9c", "F": "9c5d31",
}

EARTH_RADIUS_M = 6371000


# Phải dùng cùng công thức và bán kính với heuristic() của A* để có length >= heuristic ở từng cạnh
def haversine(a, b):
    """Same formula as heuristic() in backend/app/services/path_finding.py. a, b = [lon, lat]."""
    lon1, lat1 = a
    lon2, lat2 = b
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = phi2 - phi1
    dlambda = math.radians(lon2 - lon1)
    h = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * (math.sin(dlambda / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(h), math.sqrt(1 - h))
    return EARTH_RADIUS_M * c


def ceil_mm(meters):
    """Round up to 1 mm; never return a value below `meters`."""
    millimeters = math.ceil(meters * 1000)
    # Phép chia số thực có thể làm kết quả nhỏ hơn giá trị gốc một chút; cộng thêm 1 mm để bảo đảm không bao giờ nhỏ hơn
    if millimeters / 1000 < meters:
        millimeters += 1
    return millimeters / 1000


# Khóa sắp xếp mã ga theo (thứ tự tuyến, số ga) thay vì theo chuỗi, ví dụ "G09" -> (1, 9) và "Mb03" -> (3, 3).
# Dùng để chọn mã chính của ga và sinh node id ổn định.
def code_sort_key(code):
    prefix = code.rstrip("0123456789")  # "Mb03" -> "Mb"
    return CODE_PREFIX_ORDER[prefix], int(code[len(prefix):])


def mean_point(points):
    return [sum(p[0] for p in points) / len(points), sum(p[1] for p in points) / len(points)]


def main():
    # 1. read source/reference
    with STATIONS_CSV.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        row["seq"] = int(row["seq"])
    n02_features = [
        feature for feature in json.loads(N02_FILE.read_text(encoding="utf-8"))["features"]
        if feature["properties"]["N02_004"] == "東京地下鉄"
    ]

    # 2. station mapping: name_ja -> station (one physical station, possibly on several lines)
    # Mỗi dòng CSV là một ga trên một tuyến; các dòng cùng name_ja (ví dụ Otemachi trên M/T/C/Z) gộp thành một station.
    stations = {}
    for row in rows:
        station = stations.setdefault(row["name_ja"], {"name_en": row["name_en"], "complex": row["complex"],
                                                        "codes": set(), "features": []})
        if row["name_en"] != station["name_en"] or row["complex"] != station["complex"]:
            raise SystemExit(f"inconsistent name_en/complex for {row['name_ja']}")
        # Dòng "junction" chỉ lặp lại ga nối nhánh (M06) nên không tính là mã riêng của ga
        if row["code_source"] != "junction":
            station["codes"].add(row["code"])

        # Tìm feature trong file N02 của đúng tuyến + đúng tên ga để lấy tọa độ
        matches = [ft for ft in n02_features
                   if ft["properties"]["N02_003"] == N02_LINE[row["route"]]
                   and ft["properties"]["N02_005"] == row["name_ja"]]
        if not matches and row["code"] not in NOT_IN_N02:
            raise SystemExit(f"no N02 feature for {row['code']} {row['name_ja']} on {N02_LINE[row['route']]}")
        # Bỏ feature trùng tọa độ để mỗi vị trí vật lý chỉ được tính một lần khi lấy trung bình ở bước 6
        for ft in matches:
            if ft["geometry"]["coordinates"] not in [g["geometry"]["coordinates"] for g in station["features"]]:
                station["features"].append(ft)

    # 3. same-name merge already done by keying stations on name_ja
    # 4. merge approved interchange complexes: node key = complex name, else the station's own name
    nodes = {}
    for name_ja, station in stations.items():
        key = station["complex"] or name_ja
        node = nodes.setdefault(key, {"name": station["complex"] or station["name_en"], "stations": []})
        node["stations"].append(station)

    # Tra ngược từ tên tiếng Nhật của ga sang node cuối cùng (sau khi gộp complex), dùng khi dựng edge ở bước 7-10
    node_of = {name_ja: nodes[station["complex"] or name_ja] for name_ja, station in stations.items()}

    # 5. deterministic node ids from the primary code
    # 6. node coordinates
    for node in nodes.values():
        codes = sorted((c for st in node["stations"] for c in st["codes"]), key=code_sort_key)
        order, number = code_sort_key(codes[0])
        node["id"] = order * 100 + number
        node["primary_code"] = codes[0]
        # Tọa độ lấy trung bình theo ba cấp: các đỉnh của một feature -> các feature của một ga -> các ga của một complex
        station_points = []
        for st in node["stations"]:
            feature_points = [mean_point(ft["geometry"]["coordinates"]) for ft in st["features"]]
            station_points.append(mean_point(feature_points))
        lon, lat = mean_point(station_points)
        node["coord"] = [round(lon, 6), round(lat, 6)]

    # 7-10. edges: consecutive rows of each route (Y and F both list Wakoshi..Ikebukuro, which gives the
    # parallel Y/F edges; route Mb carries line "M", which gives the Marunouchi branch)
    edges = []
    for route in ROUTE_ORDER:
        # zip(route_rows, route_rows[1:]) ghép từng cặp ga liền kề trên tuyến thành một edge
        route_rows = sorted((r for r in rows if r["route"] == route), key=lambda r: r["seq"])
        for a, b in zip(route_rows, route_rows[1:]):
            start, end = node_of[a["name_ja"]], node_of[b["name_ja"]]
            edges.append({
                "start": start["id"], "end": end["id"], "line": a["line"],
                "coords": [start["coord"], end["coord"]],
                # length = haversine giữa hai ga, làm tròn lên: đây là trọng số cạnh mà A* dùng
                "length": ceil_mm(haversine(start["coord"], end["coord"])),
            })

    # 11. GeoJSON (same structure as backend/app/data)
    node_features = [
        {"type": "Feature",
         "geometry": {"coordinates": node["coord"], "type": "Point"},
         "properties": {"id": node["id"], "name": node["name"], "active": True}}
        for node in sorted(nodes.values(), key=lambda n: n["id"])
    ]
    edge_features = [
        {"type": "Feature",
         "geometry": {"coordinates": edge["coords"], "type": "LineString"},
         "properties": {"id": i, "start": edge["start"], "end": edge["end"], "length": edge["length"],
                        "line": edge["line"], "color": LINE_COLORS[edge["line"]], "active": True}}
        for i, edge in enumerate(edges, start=1)
    ]
    # Ghi ra output/; file này sau đó được kiểm bằng validate_dataset.py. Dùng newline="\n" và ensure_ascii=False
    # để file luôn là UTF-8 với kết thúc dòng LF, không phụ thuộc hệ điều hành.
    OUTPUT_DIR.mkdir(exist_ok=True)
    for name, data in (("nodes.json", node_features), ("edges.json", edge_features)):
        with (OUTPUT_DIR / name).open("w", encoding="utf-8", newline="\n") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
            f.write("\n")

    special = sum(1 for node in nodes.values() if len(node["stations"]) > 1)
    print(f"station entries (codes):            {len({r['code'] for r in rows})}")
    print(f"physical nodes before special merge: {len(stations)}")
    print(f"special merges:                      {special}")
    print(f"final physical nodes:                {len(node_features)}")
    print(f"A* (node,line) states:               {len({(e['start'], e['line']) for e in edges} | {(e['end'], e['line']) for e in edges})}")
    print(f"edges:                               {len(edge_features)}")
    print(f"written: {OUTPUT_DIR / 'nodes.json'}, {OUTPUT_DIR / 'edges.json'}")


if __name__ == "__main__":
    main()
