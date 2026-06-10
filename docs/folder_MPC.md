# Folder MPC: nên đọc file nào trước

Tài liệu này dùng để đọc code MPC theo đúng luồng chạy hiện tại. MPC ở đây là package Python trong:

```text
MPC/mpc/
```

Luồng tổng quát:

```text
Backend đọc config + dữ liệu Kalman
-> tạo ControllerConfig và ControllerState
-> gọi ScipyMpcSolver
-> solver thử chuỗi thời gian bơm
-> FAO-56 mô phỏng Dr/RAW/TAW theo từng bước
-> cost chọn chuỗi có chi phí thấp nhất
-> trả Recommendation cho backend
```

## 1. Đọc `mpc/core/` trước

Đây là phần định nghĩa dữ liệu đầu vào/đầu ra của MPC.

### 1.1. `MPC/mpc/core/config.py`

Nên đọc đầu tiên.

File này định nghĩa cấu hình MPC:

```text
TargetBand
PumpLimits
CostWeights
SafetyConfig
ActuatorConfig
ControllerConfig
controller_config_from_mapping()
load_controller_config()
```

Ý nghĩa:

```text
TargetBand:
  ngưỡng độ ẩm cảm biến thấp/cao, ví dụ low/high.

PumpLimits:
  giới hạn thời gian bơm trong một bước.

CostWeights:
  trọng số phạt trong hàm chi phí.

SafetyConfig:
  cấu hình an toàn, ví dụ dữ liệu quá cũ thì không chạy.

ActuatorConfig:
  cấu hình gửi lệnh xuống thiết bị.

ControllerConfig:
  object gom toàn bộ config mà solver cần.
```

Hàm quan trọng:

```python
controller_config_from_mapping(...)
```

Hàm này nhận dữ liệu dạng dict từ backend/config rồi chuyển thành `ControllerConfig`.

### 1.2. `MPC/mpc/core/state.py`

Đọc sau config.

File này định nghĩa trạng thái hiện tại của hệ trước khi MPC chạy.

Class chính:

```text
ControllerState
```

Nó chứa các dữ liệu như:

```text
timestamp
kf_x_posterior
raw_soil_moisture
temperature
humidity
light
last_pump_seconds
```

Ý nghĩa:

```text
ControllerState = ảnh chụp trạng thái hiện tại của nhà kính
```

MPC không tự đọc DB. Backend đọc DB trước, rồi đóng gói thành `ControllerState`.

### 1.3. `MPC/mpc/core/types.py`

File này định nghĩa kết quả đầu ra của MPC.

Class chính:

```text
Recommendation
```

Nó chứa:

```text
pump_seconds
predicted_soil_moisture
cost
status
reason
fao56 audit
```

Ý nghĩa:

```text
Recommendation = kết quả MPC đề xuất cho backend
```

### 1.4. `MPC/mpc/core/schema.py`

File này phục vụ schema/config UI.

Nó mô tả các field config để frontend/backend biết có những cấu hình nào.

Không phải lõi thuật toán, nên đọc sau.

## 2. Đọc `mpc/control/fao56.py`

Đây là file rất quan trọng.

Nó chứa mô hình FAO-56 dùng để biến độ ẩm cảm biến thành đại lượng vật lý:

```text
TAW
RAW
Dr
ET0_step
ETc
irrigation_depth_mm
```

Các class chính:

```text
Fao56Config
Fao56State
SensorCalibration
Fao56Step
```

Các hàm nên đọc theo thứ tự:

```text
soil_preset()
fao56_config_from_mapping()
sensor_calibration_from_target_band()
calibrated_depletion_from_sensor_percent()
calibrated_sensor_percent_from_depletion_mm()
total_available_water_mm()
readily_available_water_mm()
water_stress_coefficient()
et0_step_mm()
adjusted_crop_et_mm()
irrigation_depth_mm()
advance_depletion_mm()
state_from_calibrated_sensor_percent()
```

Luồng chính trong file này:

```text
target_low / target_high
-> calibration sensor sang Dr
-> tính TAW và RAW
-> dùng FAO water balance cập nhật Dr theo thời gian
```

Công thức quan trọng:

```text
TAW = 1000 * (theta_fc - theta_wp) * root_depth_m
RAW = depletion_fraction_p * TAW
```

Mapping calibration hiện tại:

```text
target_high -> Dr = 0
target_low  -> Dr = RAW
sensor_wp   -> Dr = TAW
```

## 3. Đọc `mpc/solver/cost.py`

File này tính điểm chi phí cho một chuỗi lệnh bơm.

Class chính:

```text
TrajectoryCost
Fao56Trajectory
```

Hàm chính:

```python
score_fao56_trajectory(...)
```

Luồng:

```text
nhận state hiện tại
nhận sequence pump_seconds tương lai
-> dùng FAO-56 mô phỏng Dr từng bước
-> đổi Dr về sensor %
-> tính phạt stress/overwater/water/switching/terminal
-> trả tổng cost
```

Các thành phần cost hiện tại:

```text
stress_total:
  phạt khi Dr vượt RAW, tức đất bị khô/stress.

overwater_total:
  phạt khi dự báo vượt target_high hoặc quá ẩm.

water_total:
  phạt dùng nước/bơm nhiều.

switching_total:
  phạt thay đổi lệnh bơm quá gắt so với lệnh trước.

terminal_total:
  phạt trạng thái cuối horizon nếu vẫn lệch vùng mục tiêu.
```

## 4. Đọc `mpc/solver/scipy_solver.py`

Đây là file solver MPC chính.

Class chính:

```text
ScipyMpcSolver
```

Hàm chính:

```python
recommend(...)
```

Luồng:

```text
recommend()
-> validate state
-> _solve()
-> scipy.optimize.minimize()
-> _objective()
-> _score_sequence()
-> score_fao56_trajectory()
-> lấy chuỗi bơm có cost thấp nhất
-> trả Recommendation
```

Các hàm nên đọc:

```text
ScipyMpcSolver.recommend()
ScipyMpcSolver._solve()
ScipyMpcSolver._objective()
ScipyMpcSolver._score_sequence()
ScipyMpcSolver._validate_state()
ScipyMpcSolver._fail_closed()
_initial_pump_guess()
_pump_bounds()
_snapped_sequence()
_snap_pump_seconds()
```

Ý nghĩa:

```text
Solver không tự quyết bằng if/else đơn giản.
Nó thử tối ưu chuỗi pump_seconds tương lai,
rồi chọn chuỗi có cost thấp nhất.
```

## 5. Đọc `mpc/control/closed_loop.py`

File này dùng khi muốn chạy MPC rồi gửi lệnh xuống actuator.

Hàm chính:

```python
run_closed_loop(...)
```

Luồng:

```text
ControllerState + ControllerConfig
-> ScipyMpcSolver.recommend()
-> tạo ActuatorCommand
-> gửi qua ActuatorClient
-> trả ClosedLoopResult
```

Nếu chỉ muốn hiểu thuật toán MPC thì đọc file này sau cùng.

## 6. Đọc `mpc/actuator/`

Folder này liên quan tới gửi lệnh bơm ra thiết bị.

### 6.1. `mpc/actuator/base.py`

Định nghĩa dữ liệu lệnh:

```text
ActuatorCommand
ActuatorResult
```

### 6.2. `mpc/actuator/http.py`

Client gửi lệnh qua HTTP.

Nếu backend hiện tại gửi lệnh theo cơ chế riêng thì file này có thể không phải luồng chính.

## 7. Đọc `mpc/__init__.py`

File này export các class/hàm quan trọng ra ngoài package.

Nó giúp backend import kiểu:

```python
from mpc import ControllerConfig, ControllerState, ScipyMpcSolver
```

Không chứa thuật toán chính, nên đọc sau khi hiểu các file ở trên.

## 8. Backend gọi MPC ở đâu

Sau khi đọc package MPC, đọc tiếp backend:

```text
Green-House/backend/api/ampc.py
```

Dù tên file còn `ampc.py`, hiện tại nó là nơi backend gọi MPC.

Các hàm cần đọc:

```text
_controller_config()
_latest_estimation()
_controller_state()
run_auto_recommendation()
```

Luồng backend:

```text
DB ControlProfile
-> ControllerConfig

DB EstimationCycle mới nhất
-> ControllerState

ControllerConfig + ControllerState
-> ScipyMpcSolver
-> Recommendation
-> lưu AMPCRecommendation/MPC recommendation
-> có thể gửi lệnh bơm nếu actuator_enabled
```

## 9. Thứ tự đọc khuyến nghị

Nếu muốn hiểu nhanh mà không bị rối, đọc theo thứ tự này:

```text
1. MPC/mpc/core/config.py
2. MPC/mpc/core/state.py
3. MPC/mpc/core/types.py
4. MPC/mpc/control/fao56.py
5. MPC/mpc/solver/cost.py
6. MPC/mpc/solver/scipy_solver.py
7. Green-House/backend/api/ampc.py
8. MPC/mpc/control/closed_loop.py
9. MPC/mpc/actuator/base.py
10. MPC/mpc/actuator/http.py
11. MPC/mpc/core/schema.py
12. MPC/mpc/__init__.py
```

## 10. File ít cần đọc trước

Các file/folder sau không nên đọc đầu tiên:

```text
MPC/tests/
MPC/docs/
MPC/examples/
MPC/reports/
MPC/.tasks/
MPC/greenhouse_mpc.egg-info/
MPC/.pytest_cache/
```

Lý do:

```text
tests/ dùng để kiểm tra sau khi hiểu code.
docs/ dùng để tham khảo.
examples/ là dữ liệu ví dụ.
reports/ là báo cáo.
.tasks/ là lịch sử task.
egg-info và pytest_cache là metadata/cache, không phải code thuật toán.
```

## 11. Tóm tắt một dòng

```text
Muốn hiểu MPC: đọc config/state trước, đọc FAO-56 để hiểu vật lý, đọc cost để hiểu mục tiêu tối ưu, rồi đọc scipy_solver để hiểu cách chọn lệnh bơm.
```
