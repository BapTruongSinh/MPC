# Kalman workflow: đọc code từ đầu đến cuối

File này viết để đọc code, không phải để đọc như công thức thuần.

Mục tiêu:

- Biết dữ liệu đi từ ESP32 vào bảng nào.
- Biết hàm nào gọi hàm nào.
- Biết `RawRecord`, `ProcessedRecord`, `EstimationCycle` là gì.
- Biết Kalman tính `kf_x_posterior`, `kf_R`, `kf_K` như thế nào.
- Biết MPC lấy kết quả Kalman ở đâu.

Các file chính cần mở khi đọc:

```text
Green-House/backend/api/views.py
Green-House/backend/api/estimation.py
Green-House/backend/api/models.py
Kalman/kalman/ingestion/loader.py
Kalman/kalman/ingestion/validator.py
Kalman/kalman/ingestion/preprocessor.py
Kalman/kalman/filter/cycle.py
```

## 1. Nói thật đơn giản trước

Hệ thống có 2 bảng quan trọng:

```text
api_sensordata
```

Bảng này lưu dữ liệu thô ESP32 gửi lên. Kalman không tạo bảng này. ESP32 gửi dữ liệu, backend nhận rồi lưu vào đây.

```text
api_estimationcycle
```

Bảng này lưu kết quả sau khi backend chạy Kalman. Kalman không ghi thẳng DB; backend gọi Kalman, lấy kết quả, rồi tạo dòng `EstimationCycle`.

Luồng cực ngắn:

```text
ESP32 gửi dữ liệu
-> backend lưu vào api_sensordata
-> backend lấy dữ liệu đó tạo RawRecord
-> validate dữ liệu
-> preprocess dữ liệu
-> chạy Kalman
-> lưu kết quả vào api_estimationcycle
```

## 2. Điểm bắt đầu: ESP32 gửi dữ liệu vào backend

File:

```text
Green-House/backend/api/views.py
```

Class:

```python
class IngestReadingsView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = IngestReadingSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = {**request.data, **serializer.validated_data}
        reading = ingest_sensor_payload(payload)
        estimation = ensure_estimation_for_reading(reading)

        return Response({
            'id': reading.id,
            'estimation_id': estimation.id,
            'message': 'Đã nhận dữ liệu cảm biến',
        })
```

Giải thích từng dòng quan trọng:

```python
serializer = IngestReadingSerializer(data=request.data)
```

Backend nhận JSON ESP32 gửi lên và đưa vào serializer để kiểm tra format.

Ví dụ ESP32 gửi:

```json
{
  "temperature": 28,
  "humidity": 70,
  "soil_moisture": 25.6,
  "light": 5500
}
```

```python
serializer.is_valid(raise_exception=True)
```

Nếu dữ liệu sai format, API báo lỗi luôn. Nếu đúng thì đi tiếp.

```python
payload = {**request.data, **serializer.validated_data}
```

Gộp dữ liệu gốc và dữ liệu đã được serializer ép kiểu.

```python
reading = ingest_sensor_payload(payload)
```

Hàm này lưu dữ liệu vào bảng `api_sensordata`.

Nói cách khác:

```text
reading chính là một dòng SensorData mới.
```

```python
estimation = ensure_estimation_for_reading(reading)
```

Sau khi có dữ liệu thô, backend chạy Kalman cho mẫu này.

Kết quả trả về là một dòng trong bảng:

```text
api_estimationcycle
```

```python
return Response(...)
```

API trả lại id của dòng sensor và id của dòng Kalman.

## 3. `SensorData` là gì?

File:

```text
Green-House/backend/api/models.py
```

Ý nghĩa:

```text
SensorData = dữ liệu thô từ cảm biến
```

Các cột hay dùng:

```text
temperature
humidity
light
soil_moisture
payload
recorded_at
received_at
owner_id
```

Ví dụ:

```text
soil_moisture = 25.6
temperature = 28
humidity = 70
recorded_at = thời điểm ESP đo
```

Điểm quan trọng:

```text
api_sensordata không phải output của Kalman.
api_sensordata là input cho Kalman.
```

## 4. Từ `SensorData` sang `RawRecord`

File:

```text
Green-House/backend/api/estimation.py
```

Hàm:

```python
def _raw_from_reading(reading: SensorData) -> RawRecord:
    payload = reading.payload if isinstance(reading.payload, dict) else {}

    def flag(field: str, device: str) -> float:
        if field in payload:
            return _number(payload[field])
        if device in payload:
            return _number(payload[device])
        return _device_flag(device)

    return RawRecord(
        timestamp=reading.recorded_at,
        soil_moisture=_number(reading.soil_moisture),
        temperature=_number(reading.temperature),
        humidity=_number(reading.humidity),
        light=_number(reading.light),
        drip=flag('drip', 'pump'),
        mist=flag('mist', 'mist'),
        fan=flag('fan', 'fan'),
        row_index=0,
    )
```

Hàm này làm gì?

Nó biến một dòng database `SensorData` thành một object Python tên là `RawRecord`.

Nói dễ hiểu:

```text
SensorData = dữ liệu đang nằm trong database
RawRecord = gói dữ liệu đưa vào pipeline Kalman
```

Giải thích từng phần:

```python
payload = reading.payload if isinstance(reading.payload, dict) else {}
```

Nếu `payload` là JSON dict thì dùng. Nếu không thì cho `{}` để tránh lỗi.

```python
def flag(field: str, device: str) -> float:
```

Hàm con này lấy trạng thái thiết bị như bơm/phun sương/quạt.

Ví dụ với bơm:

```python
drip=flag('drip', 'pump')
```

Nó thử lấy theo thứ tự:

1. Nếu payload có key `drip` thì dùng.
2. Nếu payload có key `pump` thì dùng.
3. Nếu payload không có, đọc bảng `DeviceState` để xem thiết bị đang bật hay tắt.

```python
timestamp=reading.recorded_at
```

Thời điểm đo là thời điểm sensor ghi nhận.

```python
soil_moisture=_number(reading.soil_moisture)
```

Độ ẩm đất được ép sang `float`.

```python
temperature=_number(reading.temperature)
humidity=_number(reading.humidity)
light=_number(reading.light)
```

Các cảm biến phụ cũng được ép sang số.

```python
row_index=0
```

Tạm thời để `0`. Sau đó `_create_cycle()` sẽ thay bằng `cycle_index` thật.

## 5. `RawRecord` là gì?

File:

```text
Kalman/kalman/ingestion/loader.py
```

Code:

```python
@dataclass(frozen=True)
class RawRecord:
    timestamp: datetime
    soil_moisture: float | None
    temperature: float | None
    humidity: float | None
    light: float | None
    drip: float | None
    fan: float | None
    mist: float | None
    row_index: int
```

Giải thích:

`RawRecord` chỉ là một hộp đựng dữ liệu.

Nó chưa lọc nhiễu, chưa validate, chưa Kalman.

Ví dụ một `RawRecord` có thể hiểu như:

```text
timestamp = 2026-06-09 12:10:00
soil_moisture = 25.6
temperature = 28
humidity = 70
light = 5500
drip = 0
mist = 0
fan = 0
row_index = 17
```

Vì `frozen=True`, sau khi tạo object thì không sửa trực tiếp field của nó. Nếu cần đổi `row_index`, code dùng:

```python
replace(raw, row_index=cycle_index)
```

## 6. Hàm chính tạo một chu kỳ Kalman

File:

```text
Green-House/backend/api/estimation.py
```

Hàm:

```python
def ensure_estimation_for_reading(reading: SensorData) -> EstimationCycle:
    owner = reading.owner
    if owner is None:
        raise ValueError('sensor reading must belong to an owner')
    dedupe_key = f'live|sensor:{owner.pk}|{reading.recorded_at.astimezone().isoformat()}'
    existing = _cycle_query(owner, 'live').filter(ingest_dedupe_key=dedupe_key).first()
    return existing or _create_cycle(_raw_from_reading(reading), owner, dedupe_key, 'live')
```

Hàm này là cửa vào chính khi chạy Kalman cho một mẫu ESP32.

Giải thích:

```python
owner = reading.owner
```

Lấy user sở hữu dữ liệu sensor.

```python
if owner is None:
    raise ValueError(...)
```

Nếu sensor không thuộc user nào thì không chạy. Vì hệ thống cần biết dữ liệu này của ai.

```python
dedupe_key = f'live|sensor:{owner.pk}|{reading.recorded_at.astimezone().isoformat()}'
```

Tạo khóa chống trùng.

Ví dụ:

```text
live|sensor:4|2026-06-09T12:10:00+07:00
```

Ý nghĩa:

```text
Với user 4, tại thời điểm này, chỉ tạo 1 EstimationCycle live.
```

```python
existing = _cycle_query(owner, 'live').filter(ingest_dedupe_key=dedupe_key).first()
```

Tìm xem đã chạy Kalman cho mẫu này chưa.

```python
return existing or _create_cycle(...)
```

Nếu có rồi thì trả lại cái cũ. Nếu chưa thì gọi `_create_cycle()`.

## 7. `_create_cycle()` làm gì?

File:

```text
Green-House/backend/api/estimation.py
```

Code:

```python
def _create_cycle(
    raw: RawRecord,
    owner,
    dedupe_key: str,
    source_type: str,
) -> EstimationCycle:
    estimator, cycle_index = _build_estimator(raw.soil_moisture, owner, source_type)
    raw = replace(raw, row_index=cycle_index)
    validation = validate_live_record(raw)
    result = estimator.step(preprocess_single(raw, validation), cycle_index=cycle_index)
    has_measurement = raw.soil_moisture is not None
    kalman = {
        'arx_predicted': result.arx_predicted,
        'kf_x_prior': result.x_prior,
        'kf_P_prior': result.P_prior,
        'kf_innovation': result.innovation,
        'kf_R': result.R,
        'kf_K': result.K,
        'kf_x_posterior': result.x_posterior,
        'kf_P_posterior': result.P_posterior,
    } if has_measurement else {}
    return EstimationCycle.objects.create(...)
```

Đây là hàm quan trọng nhất ở backend cho Kalman.

Nó làm 5 việc:

```text
1. Dựng estimator Kalman.
2. Validate dữ liệu.
3. Preprocess dữ liệu.
4. Gọi Kalman tính toán.
5. Lưu kết quả vào api_estimationcycle.
```

Giải thích từng dòng:

```python
estimator, cycle_index = _build_estimator(raw.soil_moisture, owner, source_type)
```

Tạo object `AdaptiveKalmanCycle`.

Nói đơn giản:

```text
estimator = bộ lọc Kalman chuẩn bị chạy
cycle_index = số thứ tự chu kỳ Kalman
```

```python
raw = replace(raw, row_index=cycle_index)
```

Gán số thứ tự chu kỳ vào `RawRecord`.

```python
validation = validate_live_record(raw)
```

Kiểm tra dữ liệu có hợp lệ không.

Ví dụ:

```text
soil_moisture phải nằm trong 0-100
temperature phải nằm trong -10 đến 60
humidity phải nằm trong 0-100
```

```python
result = estimator.step(preprocess_single(raw, validation), cycle_index=cycle_index)
```

Dòng này gồm 2 việc:

```text
preprocess_single(...) -> tạo ProcessedRecord
estimator.step(...)    -> chạy Kalman
```

```python
has_measurement = raw.soil_moisture is not None
```

Kiểm tra có độ ẩm đất hay không.

```python
kalman = {...} if has_measurement else {}
```

Nếu có độ ẩm thì lấy các kết quả Kalman để lưu DB. Nếu không có độ ẩm thì không lưu các field `kf_*`.

```python
return EstimationCycle.objects.create(...)
```

Tạo một dòng mới trong bảng:

```text
api_estimationcycle
```

## 8. `_build_estimator()` dựng bộ Kalman như thế nào?

File:

```text
Green-House/backend/api/estimation.py
```

Code:

```python
def _build_estimator(
    initial_soil: float | None,
    owner,
    source_type: str,
) -> tuple[AdaptiveKalmanCycle, int]:
    adapter = _arx_adapter() if source_type == 'live' else None
    estimator = AdaptiveKalmanCycle(_kalman_config(initial_soil), adapter=adapter)
    cycles = _cycle_query(owner, source_type)
    latest = cycles.order_by('-cycle_index', '-id').first()
    cycle_index = latest.cycle_index + 1 if latest else 0
```

Giải thích:

```python
adapter = _arx_adapter() if source_type == 'live' else None
```

Nếu `source_type = "live"` thì có thể gắn adapter dự đoán ARX.

Nếu `source_type = "live_window"` thì không gắn ARX:

```text
adapter = None
```

Điều này quan trọng vì MPC đang ưu tiên `live_window`, tức là Kalman cho MPC thường dùng trạng thái trước làm prior, không dùng ARX.

```python
estimator = AdaptiveKalmanCycle(_kalman_config(initial_soil), adapter=adapter)
```

Tạo bộ lọc Kalman.

`_kalman_config(initial_soil)` tạo cấu hình:

```python
def _kalman_config(initial_soil: float | None) -> KalmanConfig:
    return KalmanConfig(
        x0=initial_soil or 0.0,
        Q=float(getattr(settings, 'KALMAN_LIVE_Q', 12.0)),
        R0=float(getattr(settings, 'KALMAN_LIVE_R0', 1.0)),
        R_min=float(getattr(settings, 'KALMAN_LIVE_R_MIN', 0.25)),
        R_max=float(getattr(settings, 'KALMAN_LIVE_R_MAX', 4.0)),
        forgetting_factor_b=float(getattr(settings, 'KALMAN_LIVE_FORGETTING_FACTOR_B', 0.95)),
    )
```

Nghĩa là:

```text
x0 = độ ẩm ban đầu
Q = nhiễu quá trình
R0 = nhiễu đo ban đầu
R_min = R nhỏ nhất
R_max = R lớn nhất
b = hệ số quên
```

Backend hiện mặc định:

```text
Q = 12.0
R0 = 1.0
R_min = 0.25
R_max = 4.0
b = 0.95
```

Tiếp tục:

```python
cycles = _cycle_query(owner, source_type)
latest = cycles.order_by('-cycle_index', '-id').first()
cycle_index = latest.cycle_index + 1 if latest else 0
```

Lấy các chu kỳ Kalman cũ cùng `owner` và cùng `source_type`.

Nếu đã có chu kỳ cũ, chu kỳ mới tăng thêm 1.

Ví dụ:

```text
latest.cycle_index = 13
cycle_index mới = 14
```

Nếu chưa có chu kỳ nào:

```text
cycle_index = 0
```

### 8.1 Khôi phục trạng thái Kalman cũ

Code:

```python
if latest and all(value is not None for value in (latest.kf_x_posterior, latest.kf_P_posterior, latest.kf_R)):
    config = estimator.config
    estimator._state = KalmanState(
        x_post=float(latest.kf_x_posterior),
        P_post=float(latest.kf_P_posterior),
        R=max(config.R_min, min(config.R_max, float(latest.kf_R))),
        step=cycle_index,
    )
```

Ý nghĩa:

Kalman không chạy độc lập từng mẫu. Nó cần nhớ kết quả lần trước.

Nên backend lấy dòng `EstimationCycle` mới nhất và khôi phục:

```text
x_post lần trước
P_post lần trước
R lần trước
```

Sau đó gán vào estimator hiện tại.

Nói đơn giản:

```text
Lần trước Kalman tính tới đâu, lần này chạy tiếp từ đó.
```

### 8.2 Nạp history

Code:

```python
history_limit = max(getattr(adapter, 'min_history_len', 0), HISTORY_LIMIT)
history = (
    cycles
    .filter(preprocess_status=EstimationCycle.PreprocessStatus.VALID)
    .exclude(raw_soil_moisture__isnull=True)
    .exclude(raw_temperature__isnull=True)
    .exclude(raw_humidity__isnull=True)
    .exclude(raw_light__isnull=True)
    .order_by('-sample_ts', '-id')[:history_limit]
)
estimator._history = [_processed_cycle(cycle) for cycle in reversed(list(history))]
```

Ý nghĩa:

Lấy vài chu kỳ cũ để làm history.

History này chủ yếu phục vụ adapter dự đoán nếu có. Nếu không có adapter, Kalman vẫn chạy được.

`HISTORY_LIMIT = 12`, tức mặc định lấy tối đa 12 mẫu gần nhất.

## 9. Validate: `validate_live_record()`

File:

```text
Kalman/kalman/ingestion/validator.py
```

Code rút gọn:

```python
def validate_live_record(record: RawRecord, config: ValidationConfig = DEFAULT_CONFIG) -> ValidationResult:
    if record.soil_moisture is None:
        return ValidationResult(
            is_valid=False,
            status="missing",
            reason="soil_moisture is absent; Kalman measurement-update step skipped",
        )

    out_of_range = []
    for attr, min_attr, max_attr in _RANGE_CHECKS:
        val = getattr(record, attr)
        if val is None:
            continue
        if not math.isfinite(val):
            out_of_range.append(...)
            continue
        lo = getattr(config, min_attr)
        hi = getattr(config, max_attr)
        if not (lo <= val <= hi):
            out_of_range.append(...)

    if out_of_range:
        return ValidationResult(is_valid=False, status="out_of_range", reason="; ".join(out_of_range))

    return ValidationResult(is_valid=True, status="valid")
```

Giải thích:

```python
if record.soil_moisture is None:
```

Nếu không có độ ẩm đất thì Kalman không thể update bằng sensor.

Trả:

```text
is_valid = False
status = "missing"
```

```python
out_of_range = []
```

Tạo danh sách lỗi.

```python
for attr, min_attr, max_attr in _RANGE_CHECKS:
```

Lặp qua từng field cần kiểm tra.

Các ngưỡng nằm trong `ValidationConfig`:

```text
soil_moisture: 0 -> 100
temperature: -10 -> 60
humidity: 0 -> 100
light: 0 -> 150000
drip/mist/fan: 0 -> 1
```

```python
val = getattr(record, attr)
```

Lấy giá trị field từ `RawRecord`.

Ví dụ:

```text
attr = "soil_moisture"
val = record.soil_moisture
```

```python
if val is None:
    continue
```

Nếu field phụ bị thiếu thì bỏ qua. Nhưng riêng `soil_moisture` đã kiểm tra ở đầu.

```python
if not math.isfinite(val):
```

Nếu là `NaN`, `inf`, `-inf` thì lỗi.

```python
if not (lo <= val <= hi):
```

Nếu vượt ngưỡng vật lý thì lỗi.

Nếu có lỗi:

```text
status = "out_of_range"
```

Nếu không lỗi:

```text
status = "valid"
```

## 10. Preprocess: `preprocess_single()`

File:

```text
Kalman/kalman/ingestion/preprocessor.py
```

Code:

```python
def preprocess_single(
    record: RawRecord,
    validation: ValidationResult,
) -> ProcessedRecord:
    if validation.is_valid:
        effective = {field: getattr(record, field) for field in _FIELDS}
        return _make_processed(record, validation, "valid", effective)
    return _make_processed(
        record,
        validation,
        "skipped",
        {field: None for field in _FIELDS},
    )
```

Giải thích:

```python
if validation.is_valid:
```

Nếu dữ liệu hợp lệ:

```python
effective = {field: getattr(record, field) for field in _FIELDS}
```

Copy các field từ `RawRecord`.

`_FIELDS` gồm:

```text
soil_moisture
temperature
humidity
light
drip
mist
fan
```

```python
return _make_processed(record, validation, "valid", effective)
```

Trả về `ProcessedRecord` có dữ liệu thật.

Nếu validation lỗi:

```python
{field: None for field in _FIELDS}
```

Set tất cả field thành `None`.

```python
return _make_processed(..., "skipped", ...)
```

Trả về `ProcessedRecord` với:

```text
preprocess_status = "skipped"
soil_moisture = None
```

Nói dễ hiểu:

```text
Preprocess không sửa số liệu.
Nếu dữ liệu đúng thì cho đi tiếp.
Nếu dữ liệu sai thì đánh dấu skip để Kalman không dùng mẫu đo đó.
```

## 11. `ProcessedRecord` là gì?

File:

```text
Kalman/kalman/ingestion/preprocessor.py
```

Code:

```python
@dataclass(frozen=True)
class ProcessedRecord:
    raw: RawRecord
    validation: ValidationResult
    preprocess_status: str

    soil_moisture: float | None
    temperature: float | None
    humidity: float | None
    light: float | None
    drip: float | None
    mist: float | None
    fan: float | None
```

Giải thích:

`ProcessedRecord` là bản đã qua cửa kiểm tra.

Nó giữ cả:

```text
raw          -> dữ liệu gốc
validation   -> kết quả validate
field đã xử lý -> dữ liệu được phép đưa vào Kalman
```

Nếu hợp lệ:

```text
ProcessedRecord.soil_moisture = 25.6
preprocess_status = "valid"
```

Nếu lỗi:

```text
ProcessedRecord.soil_moisture = None
preprocess_status = "skipped"
```

## 12. Chạy Kalman: `AdaptiveKalmanCycle.step()`

File:

```text
Kalman/kalman/filter/cycle.py
```

Code:

```python
def step(
    self,
    record: ProcessedRecord,
    *,
    cycle_index: int,
) -> CycleResult:
    started_at = time.perf_counter()
    try:
        result = self._step_impl(record, cycle_index, started_at)
    except Exception as exc:
        logger.exception("KalmanCycle step %d raised unexpectedly", cycle_index)
        result = self._error_result(record, cycle_index, started_at, exc)

    self._append_history(record)
    self._state.step += 1
    return result
```

Giải thích:

```python
started_at = time.perf_counter()
```

Ghi lại thời điểm bắt đầu để tính `latency_ms`.

```python
result = self._step_impl(...)
```

Gọi hàm thật sự tính Kalman.

```python
except Exception as exc:
```

Nếu Kalman bị lỗi bất ngờ, không cho crash toàn hệ thống. Nó tạo `_error_result()`.

```python
self._append_history(record)
```

Lưu record hiện tại vào history trong RAM.

```python
self._state.step += 1
```

Tăng số bước Kalman.

```python
return result
```

Trả kết quả cho backend để lưu DB.

## 13. Hàm thật sự tính Kalman: `_step_impl()`

File:

```text
Kalman/kalman/filter/cycle.py
```

Code:

```python
def _step_impl(
    self,
    record: ProcessedRecord,
    cycle_index: int,
    started_at: float,
) -> CycleResult:
    state = self._state
    arx_predicted = self._adapter_prediction()
    x_prior = arx_predicted if arx_predicted is not None else state.x_post
    P_prior = state.P_post + self._config.Q
```

Giải thích:

```python
state = self._state
```

Lấy trạng thái Kalman hiện tại.

`state` chứa:

```text
x_post: độ ẩm sau lọc ở bước trước
P_post: độ bất định ở bước trước
R: nhiễu đo hiện tại
step: số bước đã chạy
```

```python
arx_predicted = self._adapter_prediction()
```

Thử lấy dự đoán từ adapter nếu có.

Nếu không có adapter hoặc adapter không đủ dữ liệu:

```text
arx_predicted = None
```

```python
x_prior = arx_predicted if arx_predicted is not None else state.x_post
```

Nếu có dự đoán thì dùng dự đoán làm prior.

Nếu không có thì dùng kết quả sau lọc lần trước.

Nói dễ hiểu:

```text
Nếu có model dự đoán: lấy nó làm điểm bắt đầu.
Nếu không: lấy độ ẩm Kalman lần trước làm điểm bắt đầu.
```

```python
P_prior = state.P_post + self._config.Q
```

Tăng độ bất định lên một chút vì thời gian đã trôi qua.

`Q` là nhiễu quá trình.

### 13.1 Nếu mẫu bị skip

Code:

```python
z = record.soil_moisture
preprocess_status = record.preprocess_status
if z is None or preprocess_status == "skipped":
    return self._skip_measurement_result(...)
```

Giải thích:

```python
z = record.soil_moisture
```

`z` là số đo từ cảm biến.

```python
if z is None or preprocess_status == "skipped":
```

Nếu không có số đo hợp lệ, Kalman không thể update bằng sensor.

Khi đó gọi:

```python
_skip_measurement_result(...)
```

Nghĩa là:

```text
Không dùng cảm biến.
Giữ prior làm posterior.
Không cập nhật R.
```

### 13.2 Nếu có mẫu hợp lệ

Code:

```python
innovation = z - x_prior
```

Đây là sai lệch giữa cảm biến và dự đoán trước.

Ví dụ:

```text
z = 26.0
x_prior = 25.5
innovation = 0.5
```

Nếu `innovation` lớn, nghĩa là cảm biến khác dự đoán nhiều.

Code:

```python
adaptive_gain = _iae_adaptive_gain(
    self._config.forgetting_factor_b,
    state.step,
)
```

Tính hệ số thích nghi `d_k`.

Công thức:

```text
d_k = (1 - b) / (1 - b^(k + 1))
```

Trong đó:

```text
b = forgetting_factor_b
k = state.step
```

Code:

```python
R_new = _clip(
    (1.0 - adaptive_gain) * state.R
    + adaptive_gain * (innovation * innovation - P_prior),
    self._config.R_min,
    self._config.R_max,
)
```

Đây là cập nhật nhiễu đo `R`.

Viết lại:

```text
R_new = clip((1 - d_k) * R_old + d_k * (innovation^2 - P_prior), R_min, R_max)
```

Ý nghĩa:

```text
Nếu cảm biến lệch nhiều so với dự đoán, R có xu hướng tăng.
Nếu R tăng, Kalman sẽ bớt tin cảm biến hơn.
Nếu R nhỏ, Kalman tin cảm biến hơn.
```

`_clip(...)` dùng để chặn R không quá nhỏ hoặc quá lớn.

Code:

```python
K = P_prior / (P_prior + R_new)
```

Tính Kalman gain.

Ý nghĩa:

```text
K càng lớn -> kéo kết quả về phía cảm biến nhiều hơn.
K càng nhỏ -> giữ gần dự đoán hơn.
```

Code:

```python
x_post = x_prior + K * innovation
```

Cập nhật độ ẩm sau lọc.

Ví dụ:

```text
x_prior = 25.5
z = 26.0
innovation = 0.5
K = 0.6

x_post = 25.5 + 0.6 * 0.5 = 25.8
```

Kết quả không nhảy thẳng lên 26.0, mà đi tới 25.8. Đây là tác dụng làm mượt.

Code:

```python
P_post = (1.0 - K) * P_prior
```

Cập nhật độ bất định sau khi đã dùng cảm biến.

Code:

```python
state.x_post = x_post
state.P_post = P_post
state.R = R_new
```

Ghi trạng thái mới vào bộ lọc để bước sau dùng tiếp.

Code:

```python
return CycleResult(...)
```

Trả toàn bộ kết quả ra ngoài.

Backend sẽ lấy `CycleResult` này để lưu DB.

## 14. `CycleResult` là gì?

File:

```text
Kalman/kalman/filter/cycle.py
```

Code:

```python
@dataclass(frozen=True)
class CycleResult:
    timestamp: datetime
    cycle_index: int
    raw_soil_moisture: float | None
    preprocess_status: str
    arx_predicted: float | None
    x_prior: float
    P_prior: float
    innovation: float | None
    R: float
    K: float | None
    x_posterior: float
    P_posterior: float
    cycle_status: str
    adaptive_status: str
    latency_ms: float | None = None
    error_message: str | None = None
```

Nói dễ hiểu:

`CycleResult` là phiếu kết quả sau một lần chạy Kalman.

Backend đổi nó thành dòng database:

```text
CycleResult.x_posterior -> api_estimationcycle.kf_x_posterior
CycleResult.R           -> api_estimationcycle.kf_R
CycleResult.K           -> api_estimationcycle.kf_K
CycleResult.innovation  -> api_estimationcycle.kf_innovation
```

## 15. Lưu kết quả vào `api_estimationcycle`

Quay lại file:

```text
Green-House/backend/api/estimation.py
```

Đoạn lưu DB trong `_create_cycle()`:

```python
return EstimationCycle.objects.create(
    sample_ts=result.timestamp,
    cycle_index=result.cycle_index,
    owner=owner,
    slice_type='online',
    source_type=source_type,
    validation_status=validation.status,
    validation_reason=validation.reason,
    preprocess_status=result.preprocess_status,
    cycle_status=result.cycle_status,
    adaptive_status=result.adaptive_status,
    raw_soil_moisture=result.raw_soil_moisture,
    raw_temperature=raw.temperature,
    raw_humidity=raw.humidity,
    raw_light=raw.light,
    raw_drip=raw.drip,
    raw_mist=raw.mist,
    raw_fan=raw.fan,
    latency_ms=result.latency_ms,
    error_message=result.error_message or '',
    ingest_dedupe_key=dedupe_key,
    **kalman,
)
```

Giải thích:

```python
sample_ts=result.timestamp
```

Thời điểm mẫu.

```python
cycle_index=result.cycle_index
```

Số thứ tự chu kỳ Kalman.

```python
source_type=source_type
```

Cho biết dòng này là:

```text
live
```

hoặc:

```text
live_window
```

```python
validation_status=validation.status
validation_reason=validation.reason
```

Lưu kết quả validate.

```python
preprocess_status=result.preprocess_status
cycle_status=result.cycle_status
adaptive_status=result.adaptive_status
```

Lưu trạng thái xử lý.

```python
raw_soil_moisture=result.raw_soil_moisture
```

Lưu lại dữ liệu gốc đã đưa vào Kalman.

```python
**kalman
```

Đổ các field Kalman vào DB:

```text
arx_predicted
kf_x_prior
kf_P_prior
kf_innovation
kf_R
kf_K
kf_x_posterior
kf_P_posterior
```

## 16. `EstimationCycle` là gì?

File:

```text
Green-House/backend/api/models.py
```

Class:

```python
class EstimationCycle(TimeStampedModel):
```

Nói dễ hiểu:

```text
EstimationCycle = một lần backend chạy Kalman
```

Nó lưu:

```text
dữ liệu trước lọc
dữ liệu sau lọc
trạng thái validate
trạng thái Kalman
```

Các cột chính:

```text
sample_ts
cycle_index
owner
source_type
validation_status
preprocess_status
cycle_status
adaptive_status
raw_soil_moisture
kf_x_prior
kf_P_prior
kf_innovation
kf_R
kf_K
kf_x_posterior
kf_P_posterior
```

## 17. `source_type="live"` và `source_type="live_window"` khác gì?

Đây là phần dễ nhầm nhất.

### 17.1 `live`

Được tạo bởi:

```python
ensure_estimation_for_reading(reading)
```

Dùng cho:

```text
một mẫu SensorData riêng lẻ
```

Luồng:

```text
1 dòng api_sensordata
-> 1 dòng api_estimationcycle source_type="live"
```

### 17.2 `live_window`

Được tạo bởi:

```python
ensure_recent_window_estimations(...)
ensure_estimation_for_sensor_window(...)
```

Dùng cho MPC.

MPC có `step_seconds`, ví dụ 300 giây.

Backend lấy các mẫu sensor trong 300 giây đó, tính trung bình, rồi chạy Kalman trên dữ liệu trung bình.

Luồng:

```text
nhiều dòng api_sensordata trong một cửa sổ thời gian
-> tính trung bình
-> 1 dòng api_estimationcycle source_type="live_window"
```

## 18. Code gom dữ liệu cho `live_window`

File:

```text
Green-House/backend/api/estimation.py
```

Hàm:

```python
def ensure_estimation_for_sensor_window(
    *,
    owner,
    window_start: datetime,
    window_end: datetime,
    step_seconds: int,
) -> EstimationCycle | None:
```

Code chính:

```python
readings = list(
    SensorData.objects
    .filter(owner=owner, recorded_at__gt=window_start, recorded_at__lte=window_end)
    .order_by('recorded_at', 'id')
)
if not readings:
    return None

values = {field: _average(readings, field) for field in SENSOR_FIELDS}
flags = {name: _average_flag(readings, direct, state) for name, direct, state in DEVICE_FLAGS}
raw = RawRecord(timestamp=window_end, row_index=0, **values, **flags)
return _create_cycle(raw, owner, dedupe_key, 'live_window')
```

Giải thích:

```python
SensorData.objects.filter(...)
```

Lấy các mẫu sensor trong khoảng:

```text
window_start < recorded_at <= window_end
```

```python
if not readings:
    return None
```

Nếu cửa sổ không có dữ liệu thì không tạo Kalman.

```python
values = {field: _average(readings, field) for field in SENSOR_FIELDS}
```

Tính trung bình:

```text
soil_moisture
temperature
humidity
light
```

`SENSOR_FIELDS` là:

```python
SENSOR_FIELDS = ('soil_moisture', 'temperature', 'humidity', 'light')
```

```python
flags = {name: _average_flag(...) for ...}
```

Tính trung bình trạng thái thiết bị:

```text
drip
mist
fan
```

```python
raw = RawRecord(timestamp=window_end, row_index=0, **values, **flags)
```

Tạo `RawRecord` đại diện cho cả cửa sổ.

```python
return _create_cycle(raw, owner, dedupe_key, 'live_window')
```

Chạy Kalman và lưu vào `api_estimationcycle`.

## 19. Công thức Kalman đang dùng

Code nằm ở:

```text
Kalman/kalman/filter/cycle.py
```

Vì bài toán chỉ lọc một biến độ ẩm đất, code dùng Kalman scalar:

```text
H = 1
```

Ký hiệu:

```text
z_k: độ ẩm cảm biến hiện tại
x^-_k: dự đoán trước
x^+_k: kết quả sau lọc
P^-_k: phương sai trước update
P^+_k: phương sai sau update
R_k: nhiễu đo
Q: nhiễu quá trình
K_k: Kalman gain
e_k: innovation
```

### 19.1 Predict

Code:

```python
x_prior = arx_predicted if arx_predicted is not None else state.x_post
P_prior = state.P_post + self._config.Q
```

Công thức:

```text
x^-_k = prediction nếu có, ngược lại x^+_(k-1)
P^-_k = P^+_(k-1) + Q
```

### 19.2 Innovation

Code:

```python
innovation = z - x_prior
```

Công thức:

```text
e_k = z_k - x^-_k
```

### 19.3 Hệ số thích nghi IAE

Code:

```python
adaptive_gain = _iae_adaptive_gain(
    self._config.forgetting_factor_b,
    state.step,
)
```

Hàm:

```python
def _iae_adaptive_gain(forgetting_factor: float, step_index: int) -> float:
    denominator = 1.0 - forgetting_factor ** (step_index + 1)
    if denominator <= 0.0:
        return 1.0
    return (1.0 - forgetting_factor) / denominator
```

Công thức:

```text
d_k = (1 - b) / (1 - b^(k + 1))
```

Trong đó:

```text
b = forgetting_factor
k = step_index
```

Nói dễ hiểu:

```text
d_k quyết định R mới nghe theo lỗi hiện tại nhiều hay ít.
```

### 19.4 Cập nhật R

Code:

```python
R_new = _clip(
    (1.0 - adaptive_gain) * state.R
    + adaptive_gain * (innovation * innovation - P_prior),
    self._config.R_min,
    self._config.R_max,
)
```

Công thức:

```text
R_k = clip((1 - d_k)R_(k-1) + d_k(e_k^2 - P^-_k), R_min, R_max)
```

Ý nghĩa:

```text
R là độ nhiễu của cảm biến.
R cao -> cảm biến đang bị nghi ngờ hơn.
R thấp -> cảm biến đáng tin hơn.
```

### 19.5 Kalman gain

Code:

```python
K = P_prior / (P_prior + R_new)
```

Công thức:

```text
K_k = P^-_k / (P^-_k + R_k)
```

Ý nghĩa:

```text
K lớn -> kéo kết quả về gần cảm biến.
K nhỏ -> giữ kết quả gần dự đoán.
```

### 19.6 Posterior

Code:

```python
x_post = x_prior + K * innovation
P_post = (1.0 - K) * P_prior
```

Công thức:

```text
x^+_k = x^-_k + K_k e_k
P^+_k = (1 - K_k)P^-_k
```

## 20. Ví dụ số rất nhỏ

Giả sử:

```text
x_prior = 25.5
P_prior = 1.0
z = 26.0
R = 1.5
```

Innovation:

```text
e = 26.0 - 25.5 = 0.5
```

Kalman gain:

```text
K = 1.0 / (1.0 + 1.5) = 0.4
```

Posterior:

```text
x_post = 25.5 + 0.4 * 0.5 = 25.7
```

Cảm biến đo 26.0 nhưng Kalman chỉ đưa kết quả lên 25.7.

Đây là lý do Kalman làm đường mượt hơn:

```text
Nó không tin cảm biến 100%.
Nó kéo kết quả từ từ theo cảm biến.
```

## 21. Khi dữ liệu lỗi thì sao?

Nếu validate lỗi hoặc thiếu `soil_moisture`, `_step_impl()` gọi:

```python
_skip_measurement_result(...)
```

Code:

```python
self._state.x_post = x_prior
self._state.P_post = P_prior
return CycleResult(
    innovation=None,
    R=self._state.R,
    K=None,
    x_posterior=x_prior,
    P_posterior=P_prior,
    cycle_status="skipped_no_measurement",
    adaptive_status="R_skipped",
)
```

Ý nghĩa:

```text
Không có số đo tốt thì không update bằng cảm biến.
Lấy dự đoán trước làm kết quả sau.
R giữ nguyên.
K không có.
```

## 22. MPC lấy Kalman như thế nào?

File:

```text
Green-House/backend/api/ampc.py
```

Luồng:

```text
MPC chạy
-> gọi ensure_recent_window_estimations(...)
-> tạo hoặc lấy EstimationCycle live_window
-> lấy kf_x_posterior làm độ ẩm hiện tại
```

Nếu Kalman không đáng tin, MPC có thể fallback về raw sensor.

Điều này không nằm trong core Kalman, mà nằm ở backend/MPC.

## 23. Tóm tắt theo kiểu dễ nhớ

```text
api_sensordata
= dữ liệu thô do ESP32 gửi lên
```

```text
RawRecord
= đóng gói một mẫu sensor để chuẩn bị đưa vào Kalman
```

```text
validate_live_record()
= kiểm tra dữ liệu có nằm trong ngưỡng vật lý không
```

```text
preprocess_single()
= nếu valid thì cho đi tiếp, nếu lỗi thì set None để Kalman skip
```

```text
AdaptiveKalmanCycle.step()
= chạy một bước Kalman
```

```text
CycleResult
= kết quả sau một bước Kalman
```

```text
api_estimationcycle
= bảng lưu kết quả Kalman
```

```text
source_type="live"
= Kalman cho từng mẫu sensor
```

```text
source_type="live_window"
= Kalman cho dữ liệu đã gom theo step MPC
```

## 24. Công thức gom gọn để ghi báo cáo

```text
x^-_k = x^+_(k-1)
P^-_k = P^+_(k-1) + Q
```

```text
e_k = z_k - x^-_k
```

```text
d_k = (1 - b) / (1 - b^(k + 1))
```

```text
R_k = clip((1 - d_k)R_(k-1) + d_k(e_k^2 - P^-_k), R_min, R_max)
```

```text
K_k = P^-_k / (P^-_k + R_k)
```

```text
x^+_k = x^-_k + K_k e_k
```

```text
P^+_k = (1 - K_k)P^-_k
```

Trong code:

```text
x^-_k -> kf_x_prior
P^-_k -> kf_P_prior
e_k   -> kf_innovation
R_k   -> kf_R
K_k   -> kf_K
x^+_k -> kf_x_posterior
P^+_k -> kf_P_posterior
```
