"""Validate output/nodes.json and output/edges.json produced by build_dataset.py.

Expectations are derived again from stations.csv (not taken from the builder), and edge lengths are checked
against the unmodified heuristic() of backend/app/services/path_finding.py (read with ast, not imported,
so the backend app / Mongo is not needed). Exit code 1 if any check fails.

Usage
  python scripts/tokyo_metro/validate_dataset.py
"""
import ast
import csv
import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).parent
ROOT = HERE.parent.parent
NODES_FILE = HERE / "output" / "nodes.json"
EDGES_FILE = HERE / "output" / "edges.json"
STATIONS_CSV = HERE / "stations.csv"
PATH_FINDING = ROOT / "backend" / "app" / "services" / "path_finding.py"

LINES = {"G", "M", "H", "T", "C", "Y", "Z", "N", "F"}
CODE_PREFIX_ORDER = {"G": 1, "M": 2, "Mb": 3, "H": 4, "T": 5, "C": 6, "Y": 7, "Z": 8, "N": 9, "F": 10}
TOKYO_BBOX = (139.5, 35.5, 140.1, 35.9)  # lon_min, lat_min, lon_max, lat_max

# Line membership required by the Phase 2A instructions for these complexes
REQUIRED_COMPLEX_LINES = {
    "Akasaka-mitsuke / Nagatacho": {"G", "M", "Y", "Z", "N"},
    "Tameike-sanno / Kokkai-gijidomae": {"G", "N", "M", "C"},
    "Hibiya / Yurakucho": {"H", "C", "Y"},
}
# Codes checked against Tokyo Metro official information during review (Phase 2A.1)
OFFICIAL_CODES = {
    "Y18": "Yurakucho", "Y23": "Tatsumi", "N01": "Meguro", "N03": "Shirokane-takanawa", "N14": "Komagome",
    "Z05": "Hanzomon", "Z06": "Kudanshita", "Z07": "Jimbocho", "Z08": "Otemachi", "Z09": "Mitsukoshimae",
    "Z10": "Suitengumae", "Z11": "Kiyosumi-shirakawa", "Z12": "Sumiyoshi",
}
APPROVED_COMPLEXES = {
    "Akasaka-mitsuke / Nagatacho", "Tameike-sanno / Kokkai-gijidomae", "Ueno-hirokoji / Naka-okachimachi",
    "Hibiya / Yurakucho", "Awajicho / Shin-ochanomizu", "Ningyocho / Suitengumae", "Tsukiji / Shintomicho",
    "Ginza / Ginza-itchome", "Toranomon / Toranomon Hills",
}

results = []


# Ghi lại kết quả một phép kiểm tra; không dừng ngay khi lỗi để report() in đủ danh sách PASS/FAIL ở cuối
def check(name, ok, detail=""):
    results.append((name, bool(ok), detail))


# Lấy đúng hàm heuristic() đang chạy trong backend để kiểm tra dataset mà không cần import cả app (tránh phải có MongoDB):
# parse file bằng ast, tách riêng FunctionDef heuristic rồi exec trong namespace chỉ có `math`.
def load_heuristic():
    tree = ast.parse(PATH_FINDING.read_text(encoding="utf-8"))
    func = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "heuristic")
    namespace = {"math": math}
    exec(compile(ast.Module(body=[func], type_ignores=[]), str(PATH_FINDING), "exec"), namespace)
    return namespace["heuristic"]


def is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def valid_lon_lat(c):
    return (isinstance(c, list) and len(c) == 2 and all(isinstance(v, (int, float)) for v in c)
            and -180 <= c[0] <= 180 and -90 <= c[1] <= 90)


def main():
    nodes = json.loads(NODES_FILE.read_text(encoding="utf-8"))
    edges = json.loads(EDGES_FILE.read_text(encoding="utf-8"))
    with STATIONS_CSV.open(encoding="utf-8", newline="") as f:
        rows = list(csv.DictReader(f))
    heuristic = load_heuristic()

    # ---------------- Node ----------------
    check("node: is GeoJSON Feature", all(n.get("type") == "Feature" for n in nodes))
    check("node: geometry Point", all(n["geometry"]["type"] == "Point" for n in nodes))
    ids = [n["properties"]["id"] for n in nodes]
    check("node: id int >= 1", all(is_int(i) and i >= 1 for i in ids))
    check("node: id unique", len(ids) == len(set(ids)))
    names = [n["properties"]["name"] for n in nodes]
    check("node: name non-empty str", all(isinstance(s, str) and s.strip() for s in names))
    check("node: name unique", len(names) == len(set(names)))
    coords = [n["geometry"]["coordinates"] for n in nodes]
    check("node: coordinate valid [lon, lat]", all(valid_lon_lat(c) for c in coords))
    lon_min, lat_min, lon_max, lat_max = TOKYO_BBOX
    check("node: coordinate inside Tokyo bbox", all(lon_min <= c[0] <= lon_max and lat_min <= c[1] <= lat_max for c in coords))
    check("node: coordinates distinct", len({tuple(c) for c in coords}) == len(coords))
    check("node: active is true", all(n["properties"]["active"] is True for n in nodes))
    node_by_id = {n["properties"]["id"]: n for n in nodes}
    node_by_name = {n["properties"]["name"]: n for n in nodes}
    coord_of = {i: n["geometry"]["coordinates"] for i, n in node_by_id.items()}
    node_map = {i: tuple(c) for i, c in coord_of.items()}  # same shape as get_node_map()

    # ---------------- Edge ----------------
    check("edge: is GeoJSON Feature", all(e.get("type") == "Feature" for e in edges))
    check("edge: geometry LineString", all(e["geometry"]["type"] == "LineString" for e in edges))
    props = [e["properties"] for e in edges]
    eids = [p["id"] for p in props]
    check("edge: id int >= 1, unique", all(is_int(i) and i >= 1 for i in eids) and len(eids) == len(set(eids)))
    check("edge: start/end exist", all(p["start"] in node_by_id and p["end"] in node_by_id for p in props))
    check("edge: start != end", all(p["start"] != p["end"] for p in props))
    check("edge: length > 0", all(isinstance(p["length"], (int, float)) and p["length"] > 0 for p in props))
    check("edge: line in 9 values", {p["line"] for p in props} <= LINES, sorted({p["line"] for p in props}))
    check("edge: no line 'Mb'", all(p["line"] != "Mb" for p in props))
    check("edge: color RRGGBB lowercase, no '#'", all(re.fullmatch(r"[0-9a-f]{6}", p["color"]) for p in props))
    line_colors = defaultdict(set)
    for p in props:
        line_colors[p["line"]].add(p["color"])
    check("edge: one color per line", all(len(c) == 1 for c in line_colors.values()))
    check("edge: active is true", all(p["active"] is True for p in props))
    check("edge: LineString = [start coord, end coord]",
          all(e["geometry"]["coordinates"] == [coord_of[e["properties"]["start"]], coord_of[e["properties"]["end"]]]
              for e in edges))

    # ---------------- A* admissibility ----------------
    # Heuristic admissible nếu không bao giờ lớn hơn chi phí thật. slack = length - heuristic phải >= 0 ở mọi cạnh
    # (và < 1 mm vì length chỉ được làm tròn lên tối đa 1 mm).
    slack = [p["length"] - heuristic(p["start"], p["end"], node_map) for p in props]
    check("A*: length >= heuristic(start, end) for every edge (tolerance 0)", all(s >= 0 for s in slack),
          f"min slack {min(slack):.6f} m, max slack {max(slack):.6f} m")
    check("A*: rounding up adds < 1 mm", all(s < 0.001 + 1e-9 for s in slack))

    # ---------------- Graph ----------------
    # adjacency: ga -> các ga kề (bỏ qua tuyến) để kiểm tra liên thông; lines_at: ga -> các tuyến đi qua ga
    adjacency = defaultdict(set)
    lines_at = defaultdict(set)
    for p in props:
        adjacency[p["start"]].add(p["end"])
        adjacency[p["end"]].add(p["start"])
        lines_at[p["start"]].add(p["line"])
        lines_at[p["end"]].add(p["line"])
    # Duyệt DFS từ một ga bất kỳ; graph liên thông nếu duyệt được hết mọi ga
    seen, stack = {ids[0]}, [ids[0]]
    while stack:
        for nxt in adjacency[stack.pop()]:
            if nxt not in seen:
                seen.add(nxt)
                stack.append(nxt)
    check("graph: connected", len(seen) == len(nodes), f"{len(seen)}/{len(nodes)}")
    check("graph: no orphan nodes", all(i in adjacency for i in ids))
    # Cạnh là vô hướng nên chuẩn hóa (min, max) để (a, b) và (b, a) cùng tuyến được tính là một cạnh
    keys = Counter((min(p["start"], p["end"]), max(p["start"], p["end"]), p["line"]) for p in props)
    check("graph: no duplicate (min, max, line)", all(c == 1 for c in keys.values()))
    check("graph: all 9 lines present", {p["line"] for p in props} == LINES)

    # Lines other than M are simple paths; M has exactly one branch node
    per_line_degree = defaultdict(Counter)
    for p in props:
        per_line_degree[p["line"]][p["start"]] += 1
        per_line_degree[p["line"]][p["end"]] += 1
    check("graph: lines except M are linear (degree <= 2)",
          all(max(d.values()) <= 2 for line, d in per_line_degree.items() if line != "M"))
    m_branch_nodes = [node_by_id[i]["properties"]["name"] for i, d in per_line_degree["M"].items() if d > 2]
    check("graph: M has exactly one branch node (Nakano-sakaue)", m_branch_nodes == ["Nakano-sakaue"], m_branch_nodes)

    # ---------------- Mapping from stations.csv (independent re-derivation) ----------------
    # Tự tính lại kết quả mong đợi từ stations.csv bằng code riêng (không dùng code của build_dataset.py),
    # nên nếu builder sai thì hai bên sẽ lệch nhau và check báo FAIL.
    node_key = {}  # name_ja -> expected node name
    for r in rows:
        node_key[r["name_ja"]] = r["complex"] or r["name_en"]
    expected_names = set(node_key.values())
    check("mapping: node names == stations.csv (same-name + complex merges)", expected_names == set(names),
          f"expected {len(expected_names)}, got {len(names)}; missing {sorted(expected_names - set(names))[:3]}")
    if expected_names != set(names):
        report(nodes, edges, "?")  # the checks below look nodes up by name

    codes_of = defaultdict(set)
    for r in rows:
        if r["code_source"] != "junction":
            codes_of[node_key[r["name_ja"]]].add(r["code"])
    def code_key(code):
        prefix = code.rstrip("0123456789")
        return CODE_PREFIX_ORDER[prefix], int(code[len(prefix):])
    expected_id = {}
    for name, codes in codes_of.items():
        order, number = min(code_key(c) for c in codes)
        expected_id[name] = order * 100 + number
    check("mapping: node id = primary-code rule", all(node_by_name[n]["properties"]["id"] == i for n, i in expected_id.items()))

    expected_edges = Counter()
    by_route = defaultdict(list)
    for r in rows:
        by_route[r["route"]].append(r)
    for route_rows in by_route.values():
        route_rows.sort(key=lambda r: int(r["seq"]))
        for a, b in zip(route_rows, route_rows[1:]):
            s, t = expected_id[node_key[a["name_ja"]]], expected_id[node_key[b["name_ja"]]]
            expected_edges[(min(s, t), max(s, t), a["line"])] += 1
    check("mapping: edge set == consecutive stations in stations.csv", expected_edges == keys,
          f"expected {sum(expected_edges.values())}, got {len(props)}")

    for route, route_rows in by_route.items():
        numbers = [int(r["code"][len(r["code"].rstrip("0123456789")):]) for r in route_rows if r["code_source"] != "junction"]
        if route == "Mb":
            numbers.reverse()
        check(f"mapping: route {route} station numbers contiguous", numbers == list(range(numbers[0], numbers[0] + len(numbers))),
              f"{route_rows[0]['code']}..{route_rows[-1]['code']}")

    station_rows = [r for r in rows if r["code_source"] != "junction"]
    check("mapping: (line, code) unique", len({(r["line"], r["code"]) for r in station_rows}) == len(station_rows))
    name_of_code = {r["code"]: r["name_en"] for r in station_rows}
    wrong = {c: name_of_code.get(c) for c, n in OFFICIAL_CODES.items() if name_of_code.get(c) != n}
    check("mapping: official codes (Y18 Y23 N01 N03 N14 Z05-Z12)", not wrong, wrong or "")

    # Station order sanity, independent of codes: along a route, a -> b -> c must not turn back,
    # i.e. dist(a, c) >= max(dist(a, b), dist(b, c)). Catches swapped stations such as Z07/Z08.
    backtracks = []
    for route, route_rows in by_route.items():
        route_ids = [expected_id[node_key[r["name_ja"]]] for r in route_rows]
        for a, b, c in zip(route_ids, route_ids[1:], route_ids[2:]):
            if heuristic(a, c, node_map) < max(heuristic(a, b, node_map), heuristic(b, c, node_map)):
                backtracks.append(f"{route}:{node_by_id[b]['properties']['name']}")
    check("mapping: no route turns back (station order vs geometry)", not backtracks, backtracks or "")

    # A* làm việc trên state (node, line): mỗi cặp (ga, tuyến đi qua ga) là một state
    states = {(i, line) for i in ids for line in lines_at[i]}
    code_states = Counter((expected_id[node_key[r["name_ja"]]], r["line"]) for r in rows if r["code_source"] != "junction")
    check("mapping: each station code is its own (node, line) state", all(c == 1 for c in code_states.values()),
          f"{len(code_states)} codes -> {len(states)} states")

    # ---------------- Interchanges ----------------
    multi = [n for n in names if len(lines_at[node_by_name[n]["properties"]["id"]]) >= 2]
    same_name_multi = {r["name_en"] for r in rows if not r["complex"]
                       and len({x["line"] for x in rows if x["name_ja"] == r["name_ja"]}) >= 2}
    check("interchange: same-name multi-line stations are single nodes with >= 2 lines",
          all(len(lines_at[node_by_name[n]["properties"]["id"]]) >= 2 for n in same_name_multi), f"{len(same_name_multi)} stations")
    check("interchange: 9 approved complexes exist as merged nodes", APPROVED_COMPLEXES <= set(names)
          and {n for n in names if " / " in n} == APPROVED_COMPLEXES)
    for name in sorted(APPROVED_COMPLEXES):
        expected_lines = {r["line"] for r in rows if r["complex"] == name}
        actual = lines_at[node_by_name[name]["properties"]["id"]]
        required = REQUIRED_COMPLEX_LINES.get(name, expected_lines)
        check(f"interchange: {name} lines", actual == expected_lines == required, "".join(sorted(actual)))
    check("interchange: nodes with >= 2 lines (info)", True, f"{len(multi)}")

    # ---------------- Marunouchi branch ----------------
    def m_neighbors(name):
        nid = node_by_name[name]["properties"]["id"]
        return {node_by_id[p["end"] if p["start"] == nid else p["start"]]["properties"]["name"]
                for p in props if p["line"] == "M" and nid in (p["start"], p["end"])}
    check("M branch: Nakano-sakaue -M- {Shin-nakano, Nishi-shinjuku, Nakano-shimbashi}",
          m_neighbors("Nakano-sakaue") == {"Shin-nakano", "Nishi-shinjuku", "Nakano-shimbashi"})
    check("M branch: Nakano-shimbashi -M- {Nakano-sakaue, Nakano-fujimicho}",
          m_neighbors("Nakano-shimbashi") == {"Nakano-sakaue", "Nakano-fujimicho"})
    check("M branch: Nakano-fujimicho -M- {Nakano-shimbashi, Honancho}",
          m_neighbors("Nakano-fujimicho") == {"Nakano-shimbashi", "Honancho"})
    check("M branch: Honancho is a terminus on M only",
          m_neighbors("Honancho") == {"Nakano-fujimicho"} and lines_at[node_by_name["Honancho"]["properties"]["id"]] == {"M"})
    check("M branch: Nakano-sakaue lines == {M}", lines_at[node_by_name["Nakano-sakaue"]["properties"]["id"]] == {"M"})

    # ---------------- Yurakucho / Fukutoshin ----------------
    y_pairs = {k[:2] for k in expected_edges if k[2] == "Y"}
    f_pairs = {k[:2] for k in expected_edges if k[2] == "F"}
    expected_parallel = y_pairs & f_pairs
    actual_parallel = {k[:2] for k in keys if k[2] == "Y"} & {k[:2] for k in keys if k[2] == "F"}
    check("Y/F: parallel Y+F edge pairs == stations.csv", actual_parallel == expected_parallel and expected_parallel,
          f"{len(actual_parallel)} pairs")
    shared = {node_by_id[i]["properties"]["name"] for pair in actual_parallel for i in pair}
    check("Y/F: shared section is Wakoshi..Ikebukuro",
          shared == {"Wakoshi", "Chikatetsu-narimasu", "Chikatetsu-akatsuka", "Heiwadai", "Hikawadai",
                     "Kotake-mukaihara", "Senkawa", "Kanamecho", "Ikebukuro"}, f"{len(shared)} nodes")

    report(nodes, edges, len(states))


def report(nodes, edges, states):
    width = max(len(r[0]) for r in results)
    for name, ok, detail in results:
        print(f"{'PASS' if ok else 'FAIL'}  {name.ljust(width)}  {detail}")
    failed = [r for r in results if not r[1]]
    print(f"\nnodes={len(nodes)} edges={len(edges)} states={states} checks={len(results)} failed={len(failed)}")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
