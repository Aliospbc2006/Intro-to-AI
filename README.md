# Tokyo Metro Map

## 1. Project overview

Project tìm đường đi trong mạng **Tokyo Metro** bằng thuật toán **A\***, có thêm tham số *Transfer Penalty* để cân bằng giữa "đi ngắn" và "ít đổi tuyến".

Project được chuyển từ một dataset metro khác sang Tokyo bằng cách **chỉ thay dữ liệu, cấu hình và giao diện**. Thuật toán A\*, kiến trúc backend và API giữ nguyên.

Phạm vi:

- Chỉ **Tokyo Metro**, gồm 9 tuyến: G (Ginza), M (Marunouchi, gồm cả nhánh Honancho), H (Hibiya), T (Tozai), C (Chiyoda), Y (Yurakucho), Z (Hanzomon), N (Namboku), F (Fukutoshin).
- **Không** gồm JR, Toei Subway hay các tuyến tư nhân. Không mô hình việc tàu chạy liên thông sang các mạng khác.

Tech stack: FastAPI, MongoDB (driver Motor, async), HTML + JavaScript thuần, Leaflet (không dùng framework/CDN CSS nào khác).

## 2. Project structure

```text
frontend/             Giao diện web (HTML + CSS + JS thuần + Leaflet): store.js, map_layers.js, panel_*.js, app.js
backend/
  app/
    services/path_finding.py   Thuật toán A* (không sửa khi chuyển sang dữ liệu Tokyo)
    data/nodes.json            Dữ liệu ga Tokyo (seed vào MongoDB)
    data/edges.json            Dữ liệu đoạn nối Tokyo
scripts/tokyo_metro/  Công cụ tạo và kiểm tra dataset Tokyo (không chạy khi server hoạt động)
  stations.csv        Bảng ánh xạ: tuyến, thứ tự ga, mã ga, tên Nhật/Anh, cụm chuyển tuyến
  source/             Dữ liệu ga Tokyo Metro trích từ MLIT N02
  build_dataset.py    Tạo output/nodes.json và output/edges.json
  validate_dataset.py Kiểm tra dataset (66 check)
  output/             Kết quả build (giống hệt backend/app/data/)
```

Backend chỉ đọc `nodes.json` và `edges.json`. Thư mục `scripts/` dùng để tạo lại hai file này khi cần.

## 3. Algorithm

Đồ thị được xây từ dữ liệu như sau:

| Khái niệm | Trong project |
|---|---|
| Ga | **Node** (một điểm trên bản đồ, một tọa độ `[lon, lat]`) |
| Đoạn nối hai ga liền kề trên một tuyến | **Edge**, có thuộc tính `line` |
| Trọng số | `length` của edge (mét) |
| Trạng thái tìm kiếm | **`(node, line)`**: đang ở ga nào và đang đi trên tuyến nào |
| Heuristic | Khoảng cách haversine từ ga hiện tại tới ga đích (bán kính Trái Đất 6371000 m) |
| Transfer penalty | Cộng thêm vào cost mỗi khi `line` thay đổi |

Vì trạng thái là `(node, line)` nên thuật toán biết được khi nào hành khách đổi tuyến. Khi đi từ trạng thái `(A, tuyến X)` sang cạnh thuộc tuyến Y khác X, cost cộng thêm `penalty`. Điều này cho phép tính số lần chuyển tuyến mà không cần thêm cấu trúc đặc biệt.

Thuật toán xuất phát từ mọi trạng thái `(ga đầu, tuyến)` với chi phí 0, và dừng khi lần đầu lấy ra một trạng thái ở ga đích.

### Transfer Penalty

`Transfer Penalty = 2000` nghĩa là: A\* cộng thêm cost tương đương **2000 mét** cho mỗi lần đổi tuyến.

- Penalty nhỏ (gần 0): ưu tiên quãng đường hình học ngắn, chấp nhận đổi tuyến nhiều lần.
- Penalty lớn: ưu tiên ít lần đổi tuyến, dù đường đi dài hơn.
- Penalty = 0: chỉ tối ưu tổng `length`, đổi tuyến không tốn gì.

Đây là một **tham số ưu tiên** của thuật toán, không phải thời gian chuyển tuyến thực tế của Tokyo Metro. Giá trị mặc định 2000 được giữ nguyên từ cấu hình gốc của project, và project **không** khẳng định đây là giá trị tối ưu cho Tokyo.

Ví dụ trên dữ liệu Tokyo: Asakusa → Shibuya với penalty 0 cho đường G > Z > C > G (3 lần đổi tuyến, 12.75 km), còn với penalty 2000 cho đường đi trọn tuyến G (0 lần đổi, 13.68 km).

## 4. Tokyo dataset

| | Số lượng |
|---|---:|
| Graph node (`nodes.json`) | **135** |
| Edge (`edges.json`) | **176** |
| Trạng thái `(node, line)` | **185** |
| Giá trị `line` | 9 (G, M, H, T, C, Y, Z, N, F) |

### Vì sao 135 node mà không phải 180?

Tokyo Metro thường được giới thiệu là có khoảng **180 ga**, tính theo từng tuyến. Con số này **không bằng** số node của đồ thị vì node là điểm trên bản đồ, còn "ga" theo cách đếm của nhà vận hành là ga gắn với tuyến:

1. Dữ liệu có **185 mã ga** (G01, M05, ...), mỗi mã là một trạng thái `(node, line)`. Cùng một ga vật lý có thể có nhiều mã, ví dụ Otemachi có 4 mã (M18, T09, C11, Z08).
2. Các mã cùng tên ga được gộp thành 1 node, còn lại **144** tên ga khác nhau.
3. **9 cụm chuyển tuyến** gồm hai ga khác tên được gộp tiếp thành 1 node, nên còn **135** node. Node gộp có tên dạng `Tên A / Tên B`:

| Node gộp | Các tuyến |
|---|---|
| Akasaka-mitsuke / Nagatacho | G, M, N, Y, Z |
| Tameike-sanno / Kokkai-gijidomae | C, G, M, N |
| Ginza / Ginza-itchome | G, H, M, Y |
| Hibiya / Yurakucho | C, H, Y |
| Ueno-hirokoji / Naka-okachimachi | G, H |
| Awajicho / Shin-ochanomizu | C, M |
| Ningyocho / Suitengumae | H, Z |
| Tsukiji / Shintomicho | H, Y |
| Toranomon / Toranomon Hills | G, H |

Dữ liệu **không** có cạnh đi bộ hay tuyến "walk": việc gộp node là cách duy nhất biểu diễn chuyển tuyến giữa hai ga khác tên.

### Các quy ước khác của dataset

- **Marunouchi:** nhánh Honancho dùng chung `line = "M"` với tuyến chính. Nakano-sakaue là chỗ rẽ nhánh, nên có 3 neighbor trên tuyến M.
- **Yurakucho và Fukutoshin:** đoạn Wakoshi đến Ikebukuro được cả hai tuyến phục vụ nên có 8 cặp edge song song (một cạnh `Y`, một cạnh `F`) nối cùng cặp node.
- **ID:** số nguyên, ổn định. Công thức `id = chỉ_số_tuyến × 100 + số_ga` của mã ga chính (ví dụ G09 Ginza → 109), tuyến xét theo thứ tự G, M, H, T, C, Y, Z, N, F (nhánh Mb: ID 3xx).
- **Tọa độ:** trung bình tọa độ các đoạn sân ga của ga đó trong dữ liệu MLIT. Với node gộp, lấy trung bình tọa độ các ga thành phần.
- **`length`:** *khoảng cách hình học giữa tọa độ đại diện của hai ga* (haversine), làm tròn lên tới 1 mm để luôn lớn hơn hoặc bằng heuristic. Đây **không** phải khoảng cách đường ray thực tế.
- **Màu tuyến:** màu tham khảo để hiển thị (lấy từ Wikidata), **không phải mã HEX chính thức** của Tokyo Metro. Màu không ảnh hưởng thuật toán.

## 5. Data sources

**Nguồn chính — Ministry of Land, Infrastructure, Transport and Tourism (MLIT), 国土数値情報 鉄道データ N02-25** (dữ liệu tính đến 2025-12-31). Dùng cho danh sách ga và tọa độ. Giấy phép: **CC BY 4.0**.

> Source: National Land Numerical Information (Railway Data), Ministry of Land, Infrastructure, Transport and Tourism, Japan; processed for this project.
> 出典：国土数値情報（鉄道データ）（国土交通省）を加工して作成

Trang dữ liệu: https://nlftp.mlit.go.jp/ksj/gml/datalist/KsjTmplt-N02-2025.html

**Wikidata** (CC0): dùng phụ trợ cho mã ga, tên tiếng Anh và đối chiếu chéo. Một số mã ga đã được đối chiếu thêm với thông tin của Tokyo Metro trong quá trình rà soát (cột `code_source` trong `stations.csv`: `wikidata` hoặc `official`).

Thứ tự ga, mã ga và tên tiếng Anh trong `stations.csv` do project tổng hợp từ các nguồn trên.

**OpenStreetMap** chỉ là **bản đồ nền** (tile) trong giao diện, © OpenStreetMap contributors (ODbL). Nó không phải nguồn của dataset. Tile lấy từ server `tile.openstreetmap.de` của **OpenStreetMap Deutschland (FOSSGIS e.V.)**, không cần API key, dùng theo [điều khoản của FOSSGIS](https://www.fossgis.de/arbeitsgruppen/osm-server/nutzungsbedingungen/) (phù hợp mục đích học tập, lưu lượng thấp; cần giữ attribution và link báo lỗi bản đồ). Nhãn địa danh hiển thị theo tiếng địa phương kèm tiếng Đức.

## 6. Setup

### Backend

1. Cài **MongoDB** và chạy ở cổng 27017. Nếu dùng Docker, máy mới:
   ```bash
   docker run -d --name tokyo-metro-mongo -p 27017:27017 mongo:7
   ```
   Máy đã có container:
   ```bash
   docker start tokyo-metro-mongo
   ```
2. Vào thư mục `backend`, tạo môi trường ảo và cài thư viện (Python 3.10 trở lên):
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
   (Nếu chưa dùng `MONGO_USER`, `MONGO_PASSWORD` thì xóa hai dòng đó.)
4. Chạy server:
   ```bash
   fastapi dev app/main.py
   ```
5. Xem API ở http://127.0.0.1:8000/docs

Khi khởi động, backend tự nạp `nodes.json` và `edges.json` vào MongoDB **nếu collection còn trống**. Khi tắt server (kết thúc bình thường), hai collection này bị xóa và sẽ được nạp lại ở lần chạy sau.

### Frontend

Dùng extension **Live Server** của VSCode (mở `frontend/index.html`, cổng 5500), hoặc chạy static server:

```bash
python -m http.server 5500 --directory frontend
```

Sau đó mở http://localhost:5500. Backend cho phép CORS từ `localhost:5500` và `127.0.0.1:5500`.

### Tạo lại dataset (không bắt buộc)

```bash
python scripts/tokyo_metro/build_dataset.py      # ghi vào scripts/tokyo_metro/output/
python scripts/tokyo_metro/validate_dataset.py   # in kết quả các check
```

Hai script chỉ dùng thư viện chuẩn của Python. Kết quả build không tự chép vào backend, muốn dùng thì chép `output/nodes.json` và `output/edges.json` vào `backend/app/data/` (rồi xóa collection cũ trong MongoDB vì dữ liệu chỉ được nạp khi collection rỗng).

## 7. Usage

Giao diện gồm **sidebar bên trái** và **bản đồ bên phải**. Sidebar có ba công tắc ở trên cùng và bốn tab:

**Công tắc**

- **Show All**: hiển thị toàn bộ ga và đoạn nối, tô theo màu tuyến.
- **Show Banned**: hiển thị các ga/đoạn nối đã bị cấm (nét đứt màu đỏ).
- **Ban Mode**: click vào một ga hoặc một đoạn nối trên bản đồ để cấm (`active = false`). Phần tử bị cấm không được dùng khi tìm đường. Thanh thông báo trên bản đồ cho biết đang ở Ban Mode.

**Tab**

- **Path**: click bản đồ để chọn ga xuất phát (A) và ga đích (B) (hệ thống chọn ga active gần nhất với điểm click), nhập **Transfer Penalty** (mét, mặc định 2000) rồi bấm **Find path**. Kết quả gồm khoảng cách, số lần đổi tuyến, số ga, chuỗi tuyến và danh sách ga; bản đồ tự thu phóng để thấy trọn đường đi. Có nút đổi chiều A/B và Reset.
- **Lines**: 9 tuyến với màu, số ga và số đoạn nối. Click một tuyến để làm nổi bật trên bản đồ (click lại để bỏ).
- **Segments**: 176 đoạn nối, tìm kiếm theo tên ga/tuyến/ID, lọc theo tuyến và trạng thái (All/Active/Inactive). Click một dòng để chọn đoạn nối trên bản đồ và mở popup; nút bên phải mỗi dòng để Ban/Unban.
- **Stations**: 135 ga, tìm kiếm theo tên/ID, lọc theo tuyến và trạng thái. Click một dòng để bản đồ bay tới ga và mở popup; có Ban/Unban tương tự.

Chọn trên bản đồ và chọn trong sidebar luôn đồng bộ hai chiều. Popup của đoạn nối/ga có nút Ban/Unban, và mỗi lần Ban/Unban có thông báo kèm nút Undo. Giao diện ưu tiên màn hình desktop, sidebar cuộn riêng; dưới 860px bản đồ nằm trên, sidebar nằm dưới.

## 8. Validation

- `validate_dataset.py`: 66 check đều PASS, gồm cấu trúc node/edge, đồ thị liên thông, không cạnh trùng, `length ≥ heuristic`, các cụm chuyển tuyến, nhánh Marunouchi và đoạn Y/F song song.
- Dataset tạo lại từ script cho ra file **giống hệt từng byte** với dataset đang dùng.
- A\* được đối chiếu với Dijkstra (heuristic bằng 0) trên các route thử nghiệm: cost tối ưu giống nhau, với cả penalty 0 và 2000.
- Gọi API thật (HTTP) cho cùng kết quả như chạy offline về độ dài, số lần đổi tuyến, thứ tự tuyến và danh sách ga.
- Giao diện đã được kiểm tra bằng trình duyệt tự động (Chrome headless): bốn tab, tìm kiếm/lọc, chọn đồng bộ với bản đồ, Find Path, Ban Mode, Show Banned và Unban.

## 9. Known limitations

- Đoạn nối giữa hai ga là **đường thẳng** nối hai tọa độ, không bám theo đường ray thật.
- Trọng số là khoảng cách hình học (haversine) giữa các tọa độ đại diện, không phải khoảng cách đường ray thực.
- Không mô hình lịch tàu, tần suất hay các kiểu tàu (nhanh, chậm, chạy liên thông).
- Không mô hình thời gian đi bộ trong các ga chuyển tuyến. Transfer Penalty là tham số ưu tiên, không phải thời gian chuyển tuyến thực.
- Chỉ có Tokyo Metro; chưa có JR, Toei hay tuyến tư nhân.
- Màu tuyến chỉ để hiển thị, không phải màu chính thức.
- Bản đồ nền cần **internet** và máy phải truy cập được `tile.openstreetmap.de`.

### Nếu bản đồ nền (basemap) không hiện

Bản đồ nền màu xám nhưng ga và đường đi vẫn hiển thị là lỗi mạng chứ không phải lỗi project: trình duyệt không tải được tile. Project dùng `tile.openstreetmap.de` thay vì `tile.openstreetmap.org` vì có mạng (DNS của router) chặn cả domain `openstreetmap.org` bằng cách trả về `127.0.0.1`. Nếu mạng của bạn chặn cả `tile.openstreetmap.de`, bạn thử:

- đổi sang mạng khác;
- bật **Secure DNS** (DNS qua HTTPS) trong trình duyệt, hoặc đổi DNS của hệ thống.

Mở thử https://tile.openstreetmap.de/12/3637/1612.png trong trình duyệt: nếu thấy một ô ảnh bản đồ là mạng đã ổn.
