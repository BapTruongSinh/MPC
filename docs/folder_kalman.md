# Folder Kalman

File này giải thích các folder bên trong:

```text
Kalman/kalman/
```

## 1. Tổng quan

Trong `Kalman/kalman` hiện có các folder chính:

```text
Kalman/kalman/
├── evaluation/
├── filter/
├── ingestion/
├── prediction/
└── __pycache__/
```

Ý nghĩa ngắn gọn:

```text
ingestion   = nhận và chuẩn bị dữ liệu đầu vào
filter      = thuật toán Kalman chính
prediction  = mô hình dự đoán phụ, ví dụ ARX
evaluation  = tính chỉ số đánh giá kết quả lọc
__pycache__ = cache Python tự sinh, không cần đọc
```

## 2. Folder `ingestion/`

Đường dẫn:

```text
Kalman/kalman/ingestion/
```

Folder này dùng để chuẩn bị dữ liệu trước khi đưa vào Kalman.

Các file chính:

```text
loader.py
validator.py
preprocessor.py
```

### `loader.py`

File này định nghĩa `RawRecord`.

`RawRecord` có thể hiểu là:

```text
một mẫu dữ liệu thô chuẩn bị đưa vào Kalman
```

Ví dụ dữ liệu thô gồm:

```text
timestamp
soil_moisture
temperature
humidity
light
drip
mist
fan
row_index
```

Trong backend, dữ liệu từ bảng `api_sensordata` sẽ được đổi sang `RawRecord`.

### `validator.py`

File này kiểm tra dữ liệu có hợp lệ không.

Ví dụ:

```text
soil_moisture có bị thiếu không?
soil_moisture có nhỏ hơn 0 không?
soil_moisture có lớn hơn 100 không?
temperature, humidity, light có hợp lệ không?
```

Hàm hay gặp:

```python
validate_live_record(raw)
```

Nếu dữ liệu hợp lệ, Kalman mới dùng mẫu đó để cập nhật.

### `preprocessor.py`

File này chuyển dữ liệu từ `RawRecord` thành `ProcessedRecord`.

`ProcessedRecord` có thể hiểu là:

```text
dữ liệu đã qua bước kiểm tra và tiền xử lý
```

Hàm hay gặp:

```python
preprocess_single(raw, validation)
```

Nếu dữ liệu hợp lệ, nó giữ lại giá trị cảm biến.

Nếu dữ liệu lỗi, nó đánh dấu mẫu đó là `skipped`.

Luồng của `ingestion`:

```text
RawRecord
-> validate_live_record()
-> preprocess_single()
-> ProcessedRecord
```

## 3. Folder `filter/`

Đường dẫn:

```text
Kalman/kalman/filter/
```

Folder này chứa phần Kalman chính.

File chính:

```text
cycle.py
```

Trong `cycle.py` có các thành phần quan trọng:

```text
KalmanConfig
KalmanState
AdaptiveKalmanCycle
CycleResult
```

### `KalmanConfig`

Đây là cấu hình của Kalman.

Ví dụ:

```text
x0   = giá trị độ ẩm ban đầu
P0   = độ không chắc chắn ban đầu
Q    = nhiễu mô hình
R0   = nhiễu đo ban đầu
R_min = giới hạn nhỏ nhất của R
R_max = giới hạn lớn nhất của R
forgetting_factor_b = hệ số quên
```

### `KalmanState`

Đây là trạng thái hiện tại của Kalman.

Nó lưu các giá trị như:

```text
x_post = độ ẩm sau lọc ở bước hiện tại
P_post = độ không chắc chắn sau lọc
R      = nhiễu đo hiện tại
step   = số bước đã chạy
```

### `AdaptiveKalmanCycle`

Đây là class chạy Kalman từng bước.

Mỗi khi có một mẫu dữ liệu mới, backend gọi Kalman để xử lý mẫu đó.

Nói đơn giản:

```text
AdaptiveKalmanCycle nhận ProcessedRecord
-> tính prior
-> tính innovation
-> cập nhật R
-> tính Kalman gain K
-> tính posterior
-> trả về CycleResult
```

### `CycleResult`

Đây là kết quả sau một lần chạy Kalman.

Nó chứa các giá trị như:

```text
x_prior
P_prior
innovation
R
K
x_posterior
P_posterior
status
```

## 4. Folder `prediction/`

Đường dẫn:

```text
Kalman/kalman/prediction/
```

Folder này chứa phần mô hình dự đoán phụ.

Các file chính:

```text
base.py
arx_adapter.py
```

### `base.py`

File này định nghĩa interface chung cho model dự đoán.

Các class hay gặp:

```text
PredictionInput
PredictionResult
PredictionAdapter
```

Ý nghĩa:

```text
PredictionInput  = dữ liệu đầu vào cho model dự đoán
PredictionResult = kết quả dự đoán
PredictionAdapter = class nền để các model dự đoán kế thừa
```

### `arx_adapter.py`

File này định nghĩa:

```python
ARXPredictionAdapter
```

Nó dùng để đọc model ARX đã train từ file `.json`.

Ví dụ backend gọi:

```python
ARXPredictionAdapter.load_artifact(Path(path))
```

Ý nghĩa:

```text
đọc file model ARX
-> tạo object ARXPredictionAdapter
-> dùng object đó để dự đoán giá trị trước cho Kalman
```

Lưu ý:

```text
Folder prediction không phải thuật toán Kalman chính.
Nó chỉ là phần model dự đoán phụ có thể hỗ trợ Kalman.
```

## 5. Folder `evaluation/`

Đường dẫn:

```text
Kalman/kalman/evaluation/
```

Folder này dùng để đánh giá kết quả lọc.

File chính:

```text
metrics.py
```

Ý nghĩa:

```text
tính các chỉ số đánh giá sai số
tính thống kê kết quả
hỗ trợ kiểm tra chất lượng Kalman
```

Folder này không phải luồng runtime chính.

Nó chủ yếu phục vụ phân tích và đánh giá.

## 6. Folder `__pycache__/`

Đường dẫn:

```text
Kalman/kalman/__pycache__/
```

Đây là folder Python tự sinh ra khi chạy code.

Nó chứa file cache `.pyc`.

Không cần đọc folder này khi tìm hiểu code.

Không nên coi đây là phần logic của dự án.

## 7. Luồng tổng thể

Luồng Kalman trong dự án có thể hiểu như sau:

```text
ESP32 gửi dữ liệu
-> backend lưu vào api_sensordata
-> backend đổi SensorData thành RawRecord
-> ingestion kiểm tra và tiền xử lý
-> filter chạy Kalman
-> backend lưu kết quả vào api_estimationcycle
-> MPC đọc kết quả Kalman để dự báo/tính lệnh bơm
```

Tương ứng với folder:

```text
api_sensordata
-> ingestion/
-> filter/
-> api_estimationcycle
-> MPC
```

Nếu có ARX:

```text
prediction/
-> hỗ trợ tạo giá trị dự đoán trước cho Kalman
```

Nhưng Kalman core vẫn nằm ở:

```text
filter/cycle.py
```

## 8. Nên đọc các folder theo thứ tự nào?

Nếu mới đọc code Kalman, nên đọc theo thứ tự này:

```text
1. ingestion/
2. filter/
3. prediction/
4. evaluation/
```

### Bước 1: đọc `ingestion/` trước

Đọc folder này trước vì đây là nơi dữ liệu đi vào Kalman.

Thứ tự file nên đọc:

```text
Kalman/kalman/ingestion/loader.py
Kalman/kalman/ingestion/validator.py
Kalman/kalman/ingestion/preprocessor.py
```

Sau khi đọc xong cần hiểu:

```text
RawRecord là gì
dữ liệu được kiểm tra hợp lệ như thế nào
ProcessedRecord là gì
```

### Bước 2: đọc `filter/`

Đây là phần quan trọng nhất vì chứa thuật toán Kalman chính.

File cần đọc:

```text
Kalman/kalman/filter/cycle.py
```

Sau khi đọc xong cần hiểu:

```text
KalmanConfig
KalmanState
AdaptiveKalmanCycle
CycleResult
cách tính R
cách tính K
cách tính x_posterior
```

### Bước 3: đọc `prediction/`

Đọc folder này sau `filter/` vì nó chỉ là phần hỗ trợ dự đoán trước.

Thứ tự file nên đọc:

```text
Kalman/kalman/prediction/base.py
Kalman/kalman/prediction/arx_adapter.py
```

Sau khi đọc xong cần hiểu:

```text
PredictionAdapter là gì
PredictionInput là gì
PredictionResult là gì
ARXPredictionAdapter đọc file model .json như thế nào
```

### Bước 4: đọc `evaluation/`

Folder này dùng để đánh giá kết quả Kalman.

File cần đọc:

```text
Kalman/kalman/evaluation/metrics.py
```

Nó không phải luồng chạy chính.

Chỉ cần đọc khi muốn hiểu:

```text
cách tính sai số
cách đánh giá kết quả lọc
cách tạo chỉ số phục vụ báo cáo
```

## 9. Nếu chỉ muốn hiểu nhanh

Nếu chỉ muốn hiểu Kalman chạy như thế nào trong hệ thống, đọc 2 folder này trước là đủ:

```text
ingestion/
filter/
```

Vì luồng chính là:

```text
dữ liệu thô
-> ingestion chuẩn hóa dữ liệu
-> filter chạy Kalman
-> backend lưu kết quả
```
