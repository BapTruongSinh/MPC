# Sensor-Calibrated FAO-56 AMPC

Ngày tạo: 2026-06-01  
Phạm vi: `MPC` package + `Green-House` backend/frontend

## 1. Vấn đề đã gặp

Khi chèn dữ liệu sensor giảm từ `70%` về `50%`, dashboard hiển thị đường dự báo đã xuống dưới vùng mục tiêu `55-65%`, nhưng AMPC vẫn đề xuất:

```text
pump_seconds = 0
safety_status = safe
reason = within_raw
```

Nguyên nhân không nằm ở công thức FAO-56. Công thức FAO dùng độ ẩm thể tích thật của đất:

```text
Dr = 1000 * (theta_FC - theta) * Zr
TAW = 1000 * (theta_FC - theta_WP) * Zr
RAW = p * TAW
```

Trong khi đó `soil_moisture = 55%` trên dashboard là phần trăm theo thang đo cảm biến điện dung/app, không phải `theta = 0.55 m3/m3`.

Mapping cũ đang giả định:

```text
0% sensor   -> theta_WP
100% sensor -> theta_SAT
```

Với cấu hình loam mặc định:

```text
theta_FC = 0.32
theta_WP = 0.15
theta_SAT = 0.45
Zr = 0.30
p = 0.50
```

mapping cũ cho kết quả:

```text
55% sensor -> Dr ~= 1.5 mm
50% sensor -> Dr ~= 6.0 mm
RAW        -> 25.5 mm
```

Vì vậy AMPC kết luận `50%` vẫn chưa stress nước. Điều này lệch với nghiệp vụ demo, vì người dùng hiểu vùng an toàn là `55-65% sensor`.

## 2. Quyết định calibration mới

Giữ FAO-56 làm mô hình tính toán lượng nước, nhưng thay mapping từ `% cảm biến` sang `Dr`.

Quy ước:

```text
target_high -> field capacity -> Dr = 0
target_low  -> RAW threshold  -> Dr = RAW
```

Từ `target_low`, `target_high`, và `p = depletion_fraction_p`, suy ra mốc sensor tại wilting point:

```text
sensor_wp = target_high - (target_high - target_low) / p
```

Sau đó đổi sensor percent sang Dr:

```text
TAW = 1000 * (theta_FC - theta_WP) * Zr
RAW = p * TAW
Dr = clamp((target_high - sensor_percent) / (target_high - sensor_wp) * TAW, 0, TAW)
```

Với mặc định:

```text
target_low = 55
target_high = 65
p = 0.5
TAW = 51 mm
RAW = 25.5 mm
```

ta có:

```text
65% sensor -> Dr = 0 mm
55% sensor -> Dr = 25.5 mm = RAW
50% sensor -> Dr = 38.25 mm > RAW
45% sensor -> Dr = 51 mm = TAW
```

Như vậy khi sensor xuống dưới `55%`, AMPC vẫn tối ưu theo `Dr/RAW/TAW`, nhưng ngưỡng tưới khớp với ngôn ngữ người dùng thấy trên dashboard.

## 3. Thay đổi implement

- `MPC/mpc/fao56.py`
  - Giữ các hàm legacy `theta_from_sensor_percent`, `state_from_sensor_percent`.
  - Thêm calibration target-band:
    - `sensor_calibration_from_target_band`
    - `calibrated_depletion_from_sensor_percent`
    - `calibrated_sensor_percent_from_depletion_mm`
    - `state_from_calibrated_sensor_percent`
- `MPC/mpc/solver/cost.py`
  - `score_fao56_trajectory` và daily reset dùng mapping calibrated.
  - Prediction trả về lại `% sensor` theo calibration mới để dashboard vẫn vẽ percent.
- `MPC/mpc/config.py`
  - Validate `sensor_wp >= 0` cho target band hiện tại.
- `Green-House/backend/api/serializers.py`
  - Validate target band không tạo `sensor_wp < 0`.
- `Green-House/frontend`
  - Audit panel hiển thị thêm:
    - `sensor_fc`
    - `sensor_raw`
    - `sensor_wp`

## 4. Kỳ vọng sau sửa

Với dữ liệu demo:

```text
18:00 -> 70.00%
18:05 -> 66.67%
18:10 -> 63.33%
18:15 -> 60.00%
18:20 -> 56.67%
18:25 -> 53.33%
18:30 -> 50.00%
```

AMPC phải coi `50%` là vượt RAW, không còn `within_raw`. Nếu pump limits và cấu hình actuator cho phép, recommendation phải có `pump_seconds > 0`.

## 5. Ghi chú

Không thêm field DB trong v1. `target_low` và `target_high` hiện có vừa là ngưỡng dashboard vừa là calibration đầu vào cho FAO runtime.
