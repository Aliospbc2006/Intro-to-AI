# Tokyo Metro Map

Ứng dụng web tìm đường đi trong mạng **Tokyo Metro** bằng thuật toán **A\***. Người dùng chọn ga xuất phát và ga đích trên bản đồ, đặt _Transfer Penalty_ để cân bằng giữa "đi ngắn nhất" và "ít đổi tuyến nhất", rồi xem lộ trình cùng danh sách ga. Ngoài ra có thể duyệt các tuyến, đoạn nối và ga, hoặc cấm (ban) một ga hay đoạn nối để xem đường đi thay đổi ra sao.

Đây là bài tập nhóm môn Nhập môn Trí tuệ nhân tạo (Introduction to AI).

## Mục lục

1. [Tính năng](#1-tính-năng)
2. [Phạm vi](#2-phạm-vi)
3. [Kiến trúc và cấu trúc thư mục](#3-kiến-trúc-và-cấu-trúc-thư-mục)
4. [Thuật toán](#4-thuật-toán)
5. [Dataset](#5-dataset)
6. [Nguồn dữ liệu](#6-nguồn-dữ-liệu)
7. [Cài đặt và chạy](#7-cài-đặt-và-chạy)
8. [Hướng dẫn sử dụng](#8-hướng-dẫn-sử-dụng)
9. [API](#9-api)
10. [Kiểm thử](#10-kiểm-thử)
11. [Hạn chế](#11-hạn-chế)
12. [Khắc phục sự cố](#12-khắc-phục-sự-cố)
13. [Nhóm thực hiện](#13-nhóm-thực-hiện)

## 1. Tính năng

- **Tìm đường A\*** trên đồ thị `(ga, tuyến)`, có tham số Transfer Penalty (mặc định 2000 m).
- **Giao diện dạng bản đồ khám phá**: sidebar bên trái, bản đồ Leaflet bên phải, bốn tab **Path | Lines | Segments | Stations**.
- **Tìm kiếm và lọc** đoạn nối, ga theo tên, ID, tuyến và trạng thái (All / Active / Inactive).
- **Đồng bộ hai chiều** giữa danh sách và bản đồ: hover, chọn, popup.
- **Ban / Unban** ga hoặc đoạn nối (từ danh sách, popup hoặc Ban Mode), có thông báo kèm nút Undo. Phần tử bị cấm không được dùng khi tìm đường.
- **Dataset Tokyo Metro** gồm 9 tuyến, 135 ga (node), 176 đoạn nối, kèm script tạo và kiểm tra dataset.

## 2. Phạm vi

- Chỉ **Tokyo Metro**, gồm 9 tuyến: G (Ginza), M (Marunouchi, gồm cả nhánh Honancho), H (Hibiya), T (Tozai), C (Chiyoda), Y (Yurakucho), Z (Hanzomon), N (Namboku), F (Fukutoshin).
- **Không** gồm JR, Toei Subway hay các tuyến tư nhân. Không mô hình việc tàu chạy liên thông sang mạng khác.

Công nghệ: FastAPI, MongoDB (driver Motor, async), HTML + CSS + JavaScript thuần, Leaflet. Không dùng framework frontend hay công cụ build.

## 3. Kiến trúc và cấu trúc thư mục

```text
Trình duyệt (Leaflet)  ──HTTP/JSON──►  FastAPI  ──Motor──►  MongoDB
  frontend/                            backend/              tokyo_metro_map
```

```text
frontend/
  index.html          Khung trang: sidebar, tab, bản đồ
  css/style.css       Toàn bộ giao diện
  js/
    load_map.js       Khởi tạo bản đồ Leaflet và tile nền
    ui.js             Tiện ích dùng chung (badge, toast, bộ lọc)
    store.js          Tải dữ liệu từ API, lưu ga/đoạn/tuyến, sự kiện
    map_layers.js     Vẽ mạng lưới, hover/chọn, popup, route, ban
    panel_path.js     Tab Path
    panel_lines.js    Tab Lines
    panel_lists.js    Tab Segments và Stations
    app.js            Khởi động, chuyển tab, công tắc
backend/
  app/
    main.py                    Ứng dụng FastAPI
    api/ crud/ schemas/ core/  Endpoint, truy cập MongoDB, schema, cấu hình
    services/path_finding.py   Thuật toán A*
    data/nodes.json            Dữ liệu ga (nạp vào MongoDB khi khởi động)
    data/edges.json            Dữ liệu đoạn nối
scripts/tokyo_metro/
  stations.csv        Bảng ga: tuyến, thứ tự, mã ga, tên Nhật/Anh, cụm chuyển tuyến
  source/             Dữ liệu ga Tokyo Metro trích từ MLIT N02
  build_dataset.py    Tạo output/nodes.json và output/edges.json
  validate_dataset.py Kiểm tra dataset (66 check)
  output/             Kết quả build (giống hệt backend/app/data/)
```

Backend chỉ đọc `nodes.json` và `edges.json`. Thư mục `scripts/` dùng để tạo lại hai file này khi cần và không chạy cùng server.

## 4. Thuật toán

Đồ thị được xây từ dữ liệu như sau:

| Khái niệm                              | Trong project                                                                  |
| -------------------------------------- | ------------------------------------------------------------------------------ |
| Ga                                     | **Node** (một điểm trên bản đồ, tọa độ `[lon, lat]`)                           |
| Đoạn nối hai ga liền kề trên một tuyến | **Edge**, có thuộc tính `line`                                                 |
| Trọng số                               | `length` của edge (mét)                                                        |
| Trạng thái tìm kiếm                    | **`(node, line)`**: đang ở ga nào và đang đi trên tuyến nào                    |
| Heuristic                              | Khoảng cách haversine từ ga hiện tại tới ga đích (bán kính Trái Đất 6371000 m) |
| Transfer penalty                       | Cộng thêm vào cost mỗi khi `line` thay đổi                                     |

Vì trạng thái là `(node, line)` nên thuật toán biết được khi nào hành khách đổi tuyến. Khi đi từ trạng thái `(A, tuyến X)` sang cạnh thuộc tuyến Y khác X, cost cộng thêm `penalty`. Nhờ vậy số lần đổi tuyến được tính trực tiếp mà không cần cấu trúc đặc biệt.

Thuật toán xuất phát từ mọi trạng thái `(ga đầu, tuyến)` với chi phí 0 và dừng khi lần đầu lấy ra một trạng thái ở ga đích. Heuristic haversine không bao giờ vượt quá `length` của edge (dataset đảm bảo `length ≥ haversine`), nên A\* cho kết quả tối ưu.

Các ga và đoạn nối đã bị cấm (`active = false`) bị loại khỏi đồ thị khi tìm đường. Điểm người dùng chọn được quy về ga active gần nhất.

### Transfer Penalty

`Transfer Penalty = 2000` nghĩa là A\* cộng thêm cost tương đương **2000 mét** cho mỗi lần đổi tuyến.

- Penalty nhỏ (gần 0): ưu tiên quãng đường ngắn, chấp nhận đổi tuyến nhiều lần.
- Penalty lớn: ưu tiên ít lần đổi tuyến, dù đường đi dài hơn.
- Penalty = 0: chỉ tối ưu tổng `length`, đổi tuyến không tốn gì.

Đây là **tham số ưu tiên** của thuật toán, không phải thời gian chuyển tuyến thực tế. Giá trị mặc định 2000 chỉ là điểm xuất phát hợp lý, project không khẳng định đây là giá trị tối ưu cho Tokyo.

Ví dụ: Asakusa → Shibuya với penalty 0 cho đường G > Z > C > G (3 lần đổi tuyến, 12.75 km), còn với penalty 2000 cho đường đi trọn tuyến G (0 lần đổi, 13.68 km).

## 5. Dataset

|                           |                      Số lượng |
| ------------------------- | ----------------------------: |
| Graph node (`nodes.json`) |                       **135** |
| Edge (`edges.json`)       |                       **176** |
| Trạng thái `(node, line)` |                       **185** |
| Giá trị `line`            | 9 (G, M, H, T, C, Y, Z, N, F) |

### Vì sao 135 node mà không phải 180?

Tokyo Metro thường được giới thiệu là có khoảng **180 ga**, tính theo từng tuyến. Con số này **không bằng** số node của đồ thị vì node là điểm trên bản đồ, còn "ga" theo cách đếm của nhà vận hành là ga gắn với tuyến:

1. Dữ liệu có **185 mã ga** (G01, M05, ...), mỗi mã là một trạng thái `(node, line)`. Cùng một ga vật lý có thể có nhiều mã, ví dụ Otemachi có 4 mã (M18, T09, C11, Z08).
2. Các mã cùng tên ga được gộp thành 1 node, còn lại **144** tên ga khác nhau.
3. **9 cụm chuyển tuyến** gồm hai ga khác tên được gộp tiếp thành 1 node, nên còn **135** node. Node gộp có tên dạng `Tên A / Tên B`:

| Node gộp                         | Các tuyến     |
| -------------------------------- | ------------- |
| Akasaka-mitsuke / Nagatacho      | G, M, N, Y, Z |
| Tameike-sanno / Kokkai-gijidomae | C, G, M, N    |
| Ginza / Ginza-itchome            | G, H, M, Y    |
| Hibiya / Yurakucho               | C, H, Y       |
| Ueno-hirokoji / Naka-okachimachi | G, H          |
| Awajicho / Shin-ochanomizu       | C, M          |
| Ningyocho / Suitengumae          | H, Z          |
| Tsukiji / Shintomicho            | H, Y          |
| Toranomon / Toranomon Hills      | G, H          |

Dữ liệu **không** có cạnh đi bộ hay tuyến "walk": việc gộp node là cách biểu diễn chuyển tuyến giữa hai ga khác tên.

### Quy ước của dataset

- **Marunouchi:** nhánh Honancho dùng chung `line = "M"` với tuyến chính. Nakano-sakaue là chỗ rẽ nhánh nên có 3 neighbor trên tuyến M.
- **Yurakucho và Fukutoshin:** đoạn Wakoshi đến Ikebukuro được cả hai tuyến phục vụ nên có 8 cặp edge song song (một cạnh `Y`, một cạnh `F`) nối cùng cặp node.
- **ID:** số nguyên, ổn định. `id = chỉ_số_tuyến × 100 + số_ga` của mã ga chính (ví dụ G09 Ginza → 109), tuyến xét theo thứ tự G, M, H, T, C, Y, Z, N, F (nhánh Marunouchi: ID 3xx).
- **Tọa độ:** trung bình tọa độ các đoạn sân ga của ga đó trong dữ liệu MLIT. Với node gộp, lấy trung bình tọa độ các ga thành phần.
- **`length`:** khoảng cách hình học (haversine) giữa tọa độ đại diện của hai ga, làm tròn lên tới 1 mm để luôn lớn hơn hoặc bằng heuristic. Đây **không** phải khoảng cách đường ray thực tế.
- **Màu tuyến:** màu tham khảo để hiển thị (lấy từ Wikidata), **không phải mã HEX chính thức** của Tokyo Metro. Màu không ảnh hưởng thuật toán.

## 6. Nguồn dữ liệu

**Nguồn chính: Ministry of Land, Infrastructure, Transport and Tourism (MLIT), 国土数値情報 鉄道データ N02-25** (dữ liệu tính đến 2025-12-31). Dùng cho danh sách ga và tọa độ. Giấy phép: **CC BY 4.0**.

> Source: National Land Numerical Information (Railway Data), Ministry of Land, Infrastructure, Transport and Tourism, Japan; processed for this project.
> 出典：国土数値情報（鉄道データ）（国土交通省）を加工して作成

Trang dữ liệu: https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-N02-2025.html

**Wikidata** (CC0): dùng phụ trợ cho mã ga, tên tiếng Anh, màu tuyến và đối chiếu chéo. Một số mã ga được đối chiếu thêm với thông tin của Tokyo Metro (cột `code_source` trong `stations.csv`: `wikidata` hoặc `official`).

Thứ tự ga, mã ga và tên tiếng Anh trong `stations.csv` do nhóm tổng hợp từ các nguồn trên.

**OpenStreetMap** chỉ là **bản đồ nền** (tile) trong giao diện, © OpenStreetMap contributors (ODbL), không phải nguồn của dataset. Tile lấy từ `tile.openstreetmap.de` của **OpenStreetMap Deutschland (FOSSGIS e.V.)**: không cần API key, dùng theo [điều khoản của FOSSGIS](https://www.fossgis.de/arbeitsgruppen/osm-server/nutzungsbedingungen/) (phù hợp mục đích học tập, lưu lượng thấp; cần giữ attribution và link báo lỗi bản đồ). Nhãn địa danh hiển thị theo tiếng địa phương kèm tiếng Đức.

## 7. Cài đặt và chạy

Yêu cầu: **Python 3.10+**, **Docker** (hoặc MongoDB cài sẵn), trình duyệt hiện đại và kết nối internet để tải bản đồ nền.

### Backend

1. Chạy **MongoDB** ở cổng 27017. Với Docker, máy mới:
   ```bash
   docker run -d --name tokyo-metro-mongo -p 27017:27017 mongo:7
   ```
   Lần sau chỉ cần:
   ```bash
   docker start tokyo-metro-mongo
   ```
2. Tạo môi trường ảo và cài thư viện:
   ```bash
   cd backend
   python -m venv .venv
   .venv\Scripts\activate          # Windows;  Linux/macOS: source .venv/bin/activate
   pip install -r requirements.txt
   ```
3. Đổi tên `.env.example` thành `.env` và điền biến môi trường. Với MongoDB local không có mật khẩu:
   ```text
   MONGO_HOST=localhost
   MONGO_PORT=27017
   MONGO_DB_NAME=tokyo_metro_map
   ```
   (Nếu không dùng `MONGO_USER`, `MONGO_PASSWORD` thì xóa hai dòng đó.)
4. Chạy server:
   ```bash
   fastapi dev app/main.py
   ```
5. Xem tài liệu API tại http://127.0.0.1:8000/docs

Khi khởi động, backend tự nạp `nodes.json` và `edges.json` vào MongoDB **nếu collection còn trống**. Khi tắt server (kết thúc bình thường), hai collection này bị xóa và được nạp lại ở lần chạy sau, nên các ga/đoạn đã bị ban sẽ được đặt lại về trạng thái active.

### Frontend

Dùng extension **Live Server** của VSCode (mở `frontend/index.html`, cổng 5500), hoặc chạy static server:

```bash
python -m http.server 5500 --directory frontend
```

Mở http://localhost:5500. Backend cho phép CORS từ `localhost:5500` và `127.0.0.1:5500`.

### Tạo lại dataset (không bắt buộc)

```bash
python scripts/tokyo_metro/build_dataset.py      # ghi vào scripts/tokyo_metro/output/
python scripts/tokyo_metro/validate_dataset.py   # in kết quả các check
```

Hai script chỉ dùng thư viện chuẩn của Python. Kết quả build không tự chép vào backend. Muốn dùng, chép `output/nodes.json` và `output/edges.json` vào `backend/app/data/`, rồi xóa collection cũ trong MongoDB vì dữ liệu chỉ được nạp khi collection rỗng.

## 8. Hướng dẫn sử dụng

Giao diện gồm **sidebar bên trái** và **bản đồ bên phải**. Sidebar có ba công tắc ở trên cùng và bốn tab.

**Công tắc**

- **Show All**: hiển thị toàn bộ ga và đoạn nối, tô theo màu tuyến.
- **Show Banned**: hiển thị các ga/đoạn nối đã bị cấm (nét đứt màu đỏ).
- **Ban Mode**: click vào một ga hoặc một đoạn nối trên bản đồ để cấm (`active = false`). Thanh thông báo trên bản đồ cho biết đang ở Ban Mode.

**Tab**

- **Path**: click bản đồ để chọn ga xuất phát (A) và ga đích (B) (hệ thống chọn ga active gần nhất với điểm click), nhập **Transfer Penalty** (mét) rồi bấm **Find path**. Kết quả gồm khoảng cách, số lần đổi tuyến, số ga, chuỗi tuyến và danh sách ga; bản đồ tự thu phóng để thấy trọn đường đi. Có nút đổi chiều A/B và Reset.
- **Lines**: 9 tuyến với màu, số ga và số đoạn nối. Click một tuyến để làm nổi bật trên bản đồ (click lại để bỏ).
- **Segments**: 176 đoạn nối, tìm kiếm theo tên ga/tuyến/ID, lọc theo tuyến và trạng thái. Click một dòng để chọn đoạn nối trên bản đồ và mở popup; nút bên phải mỗi dòng để Ban/Unban.
- **Stations**: 135 ga, tìm kiếm theo tên/ID, lọc theo tuyến và trạng thái. Click một dòng để bản đồ bay tới ga và mở popup; có Ban/Unban tương tự.

Chọn trên bản đồ và chọn trong sidebar luôn đồng bộ hai chiều. Popup của đoạn nối/ga có nút Ban/Unban, và mỗi lần Ban/Unban có thông báo kèm nút Undo. Giao diện ưu tiên màn hình desktop, sidebar cuộn riêng; dưới 860px bản đồ nằm trên, sidebar nằm dưới.

## 9. API

Backend chạy tại `http://localhost:8000` (tài liệu tương tác ở `/docs`).

| Method | Endpoint      | Mô tả                                                                                |
| ------ | ------------- | ------------------------------------------------------------------------------------ |
| GET    | `/nodes/`     | Toàn bộ ga (GeoJSON FeatureCollection). Lọc bằng `?active=true` hoặc `?active=false` |
| GET    | `/edges/`     | Toàn bộ đoạn nối, cùng cách lọc                                                      |
| PATCH  | `/nodes/{id}` | Đặt trạng thái ga, body JSON là `true` hoặc `false`                                  |
| PATCH  | `/edges/{id}` | Đặt trạng thái đoạn nối, body như trên                                               |
| GET    | `/path/`      | Tìm đường: `lon1`, `lat1`, `lon2`, `lat2`, `penalty`                                 |

`/path/` trả về FeatureCollection gồm các edge theo thứ tự đi và các node. Trường `properties` có `id` (ID các ga từ đầu đến cuối), `name`, `line` (tuyến của từng chặng), `total_transfers` và `length` (mét). Nếu không có đường đi, kết quả là `{"message": "Path not found"}`.

## 10. Kiểm thử

- `validate_dataset.py`: 66 check đều PASS, gồm cấu trúc node/edge, đồ thị liên thông, không cạnh trùng, `length ≥ heuristic`, các cụm chuyển tuyến, nhánh Marunouchi và đoạn Y/F song song.
- Dataset tạo lại từ script cho ra file **giống hệt từng byte** với dataset đang dùng.
- A\* được đối chiếu với Dijkstra (heuristic bằng 0) trên các route thử nghiệm: cost tối ưu giống nhau, với cả penalty 0 và 2000.
- Gọi API thật (HTTP) cho cùng kết quả như chạy offline về độ dài, số lần đổi tuyến, thứ tự tuyến và danh sách ga.
- Giao diện được kiểm tra bằng trình duyệt tự động (Chrome headless): bốn tab, tìm kiếm/lọc, chọn đồng bộ với bản đồ, Find Path, Ban Mode, Show Banned và Unban.

Một số route để tự kiểm tra bằng tay (penalty 2000 nếu không ghi khác):

| Từ → Đến                      | Kết quả mong đợi                    |
| ----------------------------- | ----------------------------------- |
| Asakusa → Shibuya             | 13.68 km, 0 lần đổi tuyến (tuyến G) |
| Asakusa → Shibuya (penalty 0) | 12.75 km, 3 lần đổi tuyến           |
| Honancho → Shinjuku           | 4.46 km, 0 lần đổi tuyến (tuyến M)  |

## 11. Hạn chế

- Đoạn nối giữa hai ga là **đường thẳng** nối hai tọa độ, không bám theo đường ray thật.
- Trọng số là khoảng cách hình học (haversine), không phải khoảng cách đường ray thực.
- Không mô hình lịch tàu, tần suất hay các kiểu tàu (nhanh, chậm, chạy liên thông).
- Không mô hình thời gian đi bộ trong các ga chuyển tuyến. Transfer Penalty là tham số ưu tiên, không phải thời gian chuyển tuyến thực.
- Chỉ có Tokyo Metro; chưa có JR, Toei hay tuyến tư nhân.
- Màu tuyến chỉ để hiển thị, không phải màu chính thức.
- Ở mức zoom thấp, các ga nằm sát nhau chồng lên nhau nên click có thể trúng ga nằm trên cùng; zoom gần hơn để chọn chính xác.
- Giao diện ưu tiên desktop, chưa tối ưu cho thao tác cảm ứng.
- Bản đồ nền cần **internet** và máy phải truy cập được `tile.openstreetmap.de`.

## 12. Khắc phục sự cố

| Triệu chứng                                      | Cách xử lý                                                                          |
| ------------------------------------------------ | ----------------------------------------------------------------------------------- |
| Trang báo "Cannot load the network from the API" | Backend hoặc MongoDB chưa chạy. Kiểm tra `docker ps` và terminal chạy `fastapi dev` |
| Backend báo lỗi kết nối MongoDB                  | Chạy `docker start tokyo-metro-mongo`, kiểm tra `.env`                              |
| Vẫn thấy giao diện cũ                            | Bấm Ctrl+F5 để bỏ cache                                                             |
| Bản đồ nền màu xám nhưng ga và đường vẫn hiện    | Trình duyệt không tải được tile, xem bên dưới                                       |

### Bản đồ nền không hiện

Đây là lỗi mạng, không phải lỗi project. Một số mạng (ví dụ DNS của router) chặn domain `openstreetmap.org` bằng cách trả về `127.0.0.1`, vì vậy project dùng server `tile.openstreetmap.de`. Nếu mạng của bạn chặn cả domain này, thử:

- đổi sang mạng khác;
- bật **Secure DNS** (DNS qua HTTPS) trong trình duyệt, hoặc đổi DNS của hệ thống.

Mở thử https://tile.openstreetmap.de/12/3637/1612.png trong trình duyệt: nếu thấy một ô ảnh bản đồ là mạng đã ổn.

## 13. Nhóm thực hiện

**Nhóm 3**

| MSSV      | Họ tên                 |
| --------- | ---------------------- |
| 202416634 | Nguyễn Cảnh Châu Tuấn  |
| 202416469 | Lê Huyền Duy           |
| 202416649 | Nguyễn Đăng Thành Vinh |
| 202416510 | Nguyễn Việt Hưng       |
