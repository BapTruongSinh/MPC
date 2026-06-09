# AMPC Q&A và kiểm tra nhánh MPC/BE

Ngày ghi chú: 2026-06-08  
Repo: `D:\HK6\PBL\MPC`

## 1. Cách chạy dự án

App chính là `Green-House`, gồm backend Django và frontend Vite.

Backend:

```powershell
cd D:\HK6\PBL\MPC\Green-House\backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements-local.txt
Copy-Item .env.example .env
python manage.py migrate
python manage.py seed_demo
python manage.py createsuperuser
python manage.py runserver 0.0.0.0:8000
```

Nếu MySQL chạy ở cổng `3306`, sửa `.env`:

```env
DB_PORT=3306
```

Frontend:

```powershell
cd D:\HK6\PBL\MPC\Green-House\frontend
npm install
npm run dev
```

Vào:

```text
http://localhost:5173
```

## 2. `requirements-local.txt` là gì?

Backend không chỉ cần thư viện ngoài như Django. Nó còn cần import 2 package local:

```text
Kalman/
MPC/
```

Vì vậy `Green-House/backend/requirements-local.txt` có dạng:

```text
-r requirements.txt
-e ../../Kalman
-e ../../MPC
```

`-e` là editable install. Nghĩa là Python trỏ trực tiếp vào source local, nên backend import được:

```python
import kalman
import mpc
```

Nếu chỉ cài `requirements.txt`, backend có thể lỗi:

```text
ModuleNotFoundError: No module named 'mpc'
```

## 3. Kalman và MPC được xuất thành module như thế nào?

`Kalman/pyproject.toml` khai báo package `kalman`, nên backend có thể dùng:

```python
from kalman.filter import AdaptiveKalmanCycle, KalmanConfig
from kalman.ingestion import RawRecord
from kalman.prediction import ARXPredictionAdapter
```

`MPC/pyproject.toml` khai báo package `mpc`, nên backend có thể dùng:

```python
from mpc.solver import GridShootingSolver
from mpc.state import ControllerState
from mpc.plant import ARXPlantModel
from mpc.adaptive import BiasCorrectedPlantModel, BiasState
```

Backend hiện đang tự ghép pipeline AMPC từ nhiều class, chưa gom thành một facade duy nhất kiểu `recommend_ampc()`.

## 4. Bias AMPC là gì?

Bias AMPC là phần bù sai lệch dự báo gần đây.

Ví dụ tại thời điểm `k-1`, mô hình dự báo thời điểm `k` là:

```text
58%
```

Nhưng thực tế tại `k` đo được:

```text
55%
```

Sai lệch:

```text
bias = thực tế - dự báo = 55 - 58 = -3%
```

Nếu mô hình dự báo `k+1` là `57%`, AMPC bù bias:

```text
dự báo đã bù = 57 + (-3) = 54%
```

`Số mẫu sai lệch: 12` nghĩa là bias được tính từ tối đa 12 mẫu sai lệch gần nhất, không chỉ từ một mẫu.

## 5. `ControllerState` là gì?

`ControllerState` không phải mô hình dự báo. Nó là snapshot trạng thái hiện tại đưa vào MPC:

```text
timestamp
độ ẩm đất hiện tại
nhiệt độ
độ ẩm không khí
ánh sáng
lệnh bơm lần trước
run_id
```

Phân biệt:

```text
ControllerState    = trạng thái hiện tại
ARXPlantModel      = mô hình dự báo plant
GridShootingSolver = solver MPC chọn lệnh bơm
```

## 6. Vì sao 55% cảm biến không phải 55% nước thật?

`soil_moisture = 55%` trên app là phần trăm theo cảm biến điện dung/app, không phải trực tiếp là:

```text
theta = 0.55 m3/m3
```

FAO-56 dùng độ ẩm thể tích thật của đất:

```text
theta, đơn vị m3/m3
```

Vì vậy cần calibration:

```text
sensor percent -> Dr
```

thay vì lấy `% cảm biến` thế trực tiếp vào công thức FAO.

## 7. `theta_fc` và `theta_wp` là gì?

`theta_fc` là độ ẩm thể tích tại field capacity.

Nói dễ hiểu: đất đã được tưới đủ, nước dư đã thoát đi, phần nước còn lại đất giữ ổn định.

```text
theta_fc = mốc đất đủ ẩm
```

`theta_wp` là độ ẩm thể tích tại wilting point.

Nói dễ hiểu: đất khô tới mức cây gần như không hút được nước nữa.

```text
theta_wp = mốc cây héo / cạn nước hữu dụng
```

Lượng nước hữu dụng trong vùng rễ:

```text
TAW = 1000 * (theta_fc - theta_wp) * Zr
```

## 8. Khi nhập low/high thì hệ thống làm gì?

Người dùng nhập:

```text
low  = ngưỡng thấp cảm biến
high = ngưỡng cao cảm biến
```

Hệ thống coi đây là calibration:

```text
high -> field capacity -> Dr = 0
low  -> RAW threshold  -> Dr = RAW
```

Tính:

```text
TAW = 1000 * (theta_fc - theta_wp) * Zr
RAW = p * TAW
sensor_wp = high - (high - low) / p
```

Đổi độ ẩm cảm biến hiện tại `S` sang `Dr`:

```text
Dr = clamp(
  (high - S) / (high - sensor_wp) * TAW,
  0,
  TAW
)
```

Ví dụ mặc định:

```text
low = 55
high = 65
p = 0.5
theta_fc = 0.32
theta_wp = 0.15
Zr = 0.30
```

Khi đó:

```text
TAW = 51 mm
RAW = 25.5 mm
sensor_wp = 45
```

Mapping:

```text
65% -> Dr = 0
55% -> Dr = RAW = 25.5 mm
50% -> Dr = 38.25 mm > RAW
45% -> Dr = TAW = 51 mm
```

Nếu user đổi low/high, mapping tự đổi theo. Ví dụ:

```text
low = 50
high = 70
p = 0.5
```

thì:

```text
sensor_wp = 30
70% -> Dr = 0
50% -> Dr = RAW
30% -> Dr = TAW
```

## 9. Khi nào nên tưới?

Theo FAO:

```text
Dr <= RAW -> chưa stress
Dr > RAW  -> vượt ngưỡng, nên tưới
```

Với mapping hiện tại:

```text
60% -> Dr = 12.75 mm <= RAW -> chưa cần tưới
55% -> Dr = 25.5 mm ~= RAW -> sát ngưỡng
50% -> Dr = 38.25 mm > RAW -> nên tưới
```

## 10. MPC dự đoán tương lai như thế nào?

MPC không chỉ nhìn hiện tại. Nó nhìn trước nhiều bước.

Nếu:

```text
step_seconds = 300 giây = 5 phút
horizon_steps = 12
```

thì MPC nhìn trước:

```text
5, 10, 15, ..., 60 phút
```

MPC thử nhiều chuỗi bơm:

```text
[0, 0, 0, ...]
[60, 0, 0, ...]
[0, 60, 0, ...]
[210, 0, 0, ...]
```

Với mỗi chuỗi, nó dự đoán `Dr` và `% cảm biến` trong 12 bước, tính chi phí, rồi chọn chuỗi có chi phí thấp nhất.

Nhưng hệ thống chỉ thực thi lệnh đầu tiên. Đến chu kỳ sau, nó đo lại và tối ưu lại. Đây là receding horizon.

## 11. Làm sao biết bơm bao nhiêu giây thì độ ẩm tăng bao nhiêu?

Hệ thống đổi:

```text
pump_seconds -> irrigation_depth_mm -> Dr_next -> sensor_percent
```

Công thức lượng nước tưới:

```text
irrigation_depth_mm =
  pump_efficiency * pump_flow_lps * pump_seconds / irrigation_area_m2
```

Cập nhật Dr:

```text
Dr_next = clamp(Dr + ETc_adj - irrigation_depth_mm, 0, TAW)
```

Đổi Dr về sensor:

```text
S_pred = high - (Dr_pred / TAW) * (high - sensor_wp)
```

Ví dụ:

```text
pump_efficiency = 0.8
pump_flow_lps = 0.02 L/s
area = 0.25 m2
pump_seconds = 60
```

thì:

```text
irrigation_depth_mm = 3.84 mm
```

Với `TAW = 51`, `high = 65`, `sensor_wp = 45`, bơm 60 giây làm sensor tăng xấp xỉ:

```text
3.84 / 51 * 20 ~= 1.5%
```

## 12. ET0_step là gì?

`ET0` là bốc thoát hơi tham chiếu theo chuẩn FAO.

`ET0_step` là ET0 quy đổi về một bước MPC:

```text
ET0_step = ET0_hour * step_seconds / 3600
```

Ví dụ:

```text
ET0_hour = 0.6 mm/hour
step_seconds = 300 giây
```

thì:

```text
ET0_step = 0.05 mm
```

## 13. ETc_adj là gì?

`ETc_adj` là lượng nước cây/đất mất đi trong một bước MPC, đã xét hệ số cây trồng và stress nước.

Công thức:

```text
ETc_adj = Ks * Kc * ET0_step
```

Trong đó:

```text
Ks = hệ số stress nước
Kc = hệ số cây trồng
```

Nếu không stress:

```text
Ks = 1
ETc_adj = Kc * ET0_step
```

Nếu stress:

```text
Ks < 1
ETc_adj nhỏ hơn
```

Stress làm cây hút nước khó hơn, cây đóng bớt khí khổng để giảm mất nước, nên thoát hơi thực tế giảm. Điều này không có nghĩa cây khỏe hơn; nó nghĩa là cây đang bị hạn chế sinh lý.

## 14. Các trọng số MPC là gì?

### Giới hạn bơm/ngày

Ví dụ:

```text
1800 giây = 30 phút/ngày
```

Đây là giới hạn mềm cho tổng thời gian bơm trong ngày.

### Trọng số stress/overwater

Phạt khi:

```text
Dr > RAW
```

hoặc tưới quá nhiều làm:

```text
Dr_raw_next < 0
```

Số càng lớn thì MPC càng ưu tiên tránh thiếu nước/tránh úng.

### Trọng số tiết kiệm nước

Phạt dùng nước. Số càng lớn thì MPC càng tiết kiệm nước hơn.

### Trọng số đổi lệnh

Phạt mức thay đổi giữa lệnh bơm hiện tại và lệnh bơm trước.

Công thức ý tưởng:

```text
switch_cost = weight_switch * ((pump_now - pump_previous) / pump_max)^2
```

Nó giúp tránh lệnh nhảy quá mạnh giữa các chu kỳ:

```text
0s -> 300s -> 0s -> 300s
```

Vì MPC chỉ thực thi bước đầu tiên nhưng sau mỗi 5 phút lại tính lại, relay vẫn có thể nhảy nếu lệnh đầu tiên thay đổi liên tục. Nếu demo không cần làm mượt actuator, có thể đặt trọng số này về `0`.

### Trọng số giới hạn ngày

Không phải số lần bật bơm.

Nó phạt khi tổng số giây bơm trong ngày vượt `Giới hạn bơm/ngày`.

Ví dụ:

```text
daily_cap = 1800s
used_today = 1700s
planned_pump = 300s
```

Tổng là `2000s`, vượt `200s`, nên bị phạt.

### Trọng số cuối chu kỳ

Phạt nếu ở cuối horizon, đất vẫn stress:

```text
Dr cuối > RAW
```

Mục tiêu là tránh phương án hiện tại nhìn ổn nhưng 60 phút sau vẫn khô.

## 15. Vì sao insert dữ liệu xong vẫn báo cảm biến quá cũ?

AMPC kiểm tra `recorded_at`, không kiểm tra `created_at`.

Ví dụ insert lúc `19:20`, nhưng bản ghi có:

```text
recorded_at = 19:00
created_at = 19:20
```

AMPC vẫn tính:

```text
now - recorded_at = 20 phút
```

Nếu quá:

```text
stale_after_seconds = 600 giây
```

thì báo:

```text
stale_sample / dữ liệu cảm biến quá cũ
```

Lý do thiết kế này đúng: nếu thiết bị gửi trễ dữ liệu đo từ lâu, hệ thống không được bật bơm chỉ vì server vừa nhận được.

## 16. WebSocket reject có sao không?

WebSocket reject không làm hỏng `/api/forecast/`, vì forecast dùng HTTP GET vẫn chạy.

Nhưng realtime dashboard sẽ không cập nhật live nếu WebSocket bị reject.

Nguyên nhân đã gặp: frontend mở:

```text
/ws/frontend/
```

trong khi backend yêu cầu JWT token:

```text
/ws/frontend/?token=...
```

Đã sửa frontend để tự gắn `access_token` vào WebSocket URL.

## 17. Kết quả test dữ liệu demo

Đã test chuỗi:

```text
18:45 -> 60.00
18:50 -> 57.50
18:55 -> 55.00
19:00 -> 52.50
19:05 -> 50.00
```

AMPC trả:

```text
safety_status = safe
reason = above_raw_stress
pump_seconds = 210.0
```

Sau đó test chuỗi:

```text
18:45 -> 60.00
18:50 -> 57.50
18:55 -> 55.00
19:00 -> 52.50
19:05 -> 50.00
```

và force scheduler, kết quả scheduler sạch lỗi:

```text
scheduler safe ''
```

## 18. Kiểm tra nhánh MPC và BE

### Kết luận ngắn

`origin/BE` không có quan hệ lịch sử Git trực tiếp với `origin/MPC`: không tìm được merge-base.

```text
git merge-base origin/MPC origin/BE
exit = 1
```

So sánh symmetric diff:

```text
git rev-list --left-right --count origin/MPC...origin/BE
33 5
```

Nghĩa là:

```text
33 commit chỉ có ở origin/MPC
5 commit chỉ có ở origin/BE
```

Vì vậy không thể nói `BE` là nhánh được merge sạch từ `MPC` theo lịch sử Git.

### Nhưng xét theo nội dung code

Các file core MPC/calibration quan trọng đang giống nhau giữa `origin/MPC` và `origin/BE`:

```text
MPC/mpc/config.py
MPC/mpc/fao56.py
MPC/mpc/solver/cost.py
MPC/mpc/solver/grid.py
docs/2026-06-01-sensor-fao56-calibration-plan.md
Green-House/frontend/src/app/components/ForecastPage.tsx
```

Các blob hash của những file này trùng giữa hai nhánh, tức là `BE` có nội dung code mới của MPC cho phần calibration/solver.

### Khác biệt chính của BE

`origin/BE` có 5 commit riêng:

```text
35e70f0 add telegram integration and first-time setup
6efb28e optimize alert system
e608d74 sync websocket
490a61f add timer
aeaa23a new
```

Diff từ `origin/MPC` sang `origin/BE` thay đổi nhiều ở:

```text
Green-House/backend/api/*
Green-House/frontend/src/app/*
Green-House/backend/requirements.txt
```

và thêm các phần như:

```text
TelegramSettings
SunTrackerPage
ActionHistoryPage
api/migrations/0012_remove_greenhouse_device.py
```

### Trả lời câu hỏi "BE có lấy code mới nhất từ MPC để build tiếp không?"

Theo lịch sử Git: **không chứng minh được**, vì `BE` không có merge-base với `MPC` và không nằm trên lịch sử commit của `MPC`.

Theo nội dung file hiện tại: **có vẻ BE đã có phần code MPC/calibration mới nhất**, vì các file core MPC quan trọng trùng nội dung với `origin/MPC`.

Nhận định thực tế:

```text
BE có thể đã copy/cherry-pick/sync nội dung code từ MPC,
nhưng không merge đúng lịch sử Git từ MPC.
```

Nếu muốn chắc chắn và dễ bảo trì, nên tạo lại quan hệ Git sạch:

```text
merge origin/MPC vào BE
hoặc rebase BE lên origin/MPC
```

nhưng trước khi làm cần review conflict vì BE có nhiều thay đổi backend/frontend riêng.
