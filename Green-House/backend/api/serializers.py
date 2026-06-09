from __future__ import annotations

from math import isfinite

from django.conf import settings
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import (
    AMPCRecommendation,
    AMPCSchedulerState,
    Alert,
    ControlState,
    DeviceCommand,
    DeviceState,
    EstimationCycle,
    FAO56_SOIL_PRESETS,
    GreenhouseControlProfile,
    SensorData,
)

FAO56_THETA_FIELDS = ("theta_fc", "theta_wp")
FAO56_PHYSICAL_FIELDS = [
    "latitude",
    "longitude",
    "soil_type",
    "theta_fc",
    "theta_wp",
    "root_depth_m",
    "depletion_fraction_p",
    "pump_efficiency",
    "pump_flow_lps",
    "irrigation_area_m2",
]
FAO56_NUMERIC_DEFAULTS = {
    "latitude": 16.0471,
    "longitude": 108.2068,
    "theta_fc": 0.32,
    "theta_wp": 0.15,
    "root_depth_m": 0.30,
    "depletion_fraction_p": 0.5,
    "pump_efficiency": 0.8,
    "pump_flow_lps": 0.001,
    "irrigation_area_m2": 0.25,
}
GREENHOUSE_RUNTIME_NUMERIC_DEFAULTS = {
    "crop_kc": 1.0,
    "target_low": 55.0,
    "target_high": 65.0,
    "step_seconds": 300,
    "horizon_steps": 12,
    "pump_min_seconds": 0.0,
    "pump_max_seconds": 300.0,
    "cost_band_violation": 10.0,
    "cost_water_use": 0.2,
    "cost_switching": 0.5,
    "cost_terminal_band_violation": 20.0,
    "safety_stale_after_seconds": 600,
    "actuator_timeout_seconds": 5.0,
}
SENSOR_FIELD_BOUNDS = {
    "soil_moisture": (0.0, 100.0),
    "humidity": (0.0, 100.0),
    "temperature": (-99.99, 99.99),
    "light": (0.0, 99999999.99),
}
DEVICE_FIRMWARE_MAX_LENGTH = 50
DEVICE_COMMAND_TEXT_MAX_LENGTH = 50
MANUAL_REASON_MAX_LENGTH = 255
KNOWN_SENSOR_ERROR_KEYS = frozenset({"dht", "soil", "light", "gas"})
COMMAND_STATUS_VALUES = tuple(value for value, _label in DeviceCommand.CommandStatus.choices)


def _current_or_default(instance, attrs, field, default):
    if field in attrs:
        return attrs[field]
    return getattr(instance, field, default)


def _finite_fao_value(instance, attrs, field):
    value = float(_current_or_default(instance, attrs, field, FAO56_NUMERIC_DEFAULTS[field]))
    if not isfinite(value):
        raise serializers.ValidationError({field: f"{field} must be finite"})
    return value


def _finite_runtime_value(instance, attrs, field, defaults):
    value = float(_current_or_default(instance, attrs, field, defaults[field]))
    if not isfinite(value):
        raise serializers.ValidationError({field: f"{field} must be finite"})
    return value


def _validate_numeric_bounds(attrs, bounds):
    for field, (min_value, max_value) in bounds.items():
        value = attrs.get(field)
        if value is None:
            continue
        value = float(value)
        if not isfinite(value):
            raise serializers.ValidationError({field: f"{field} must be finite"})
        if not (min_value <= value <= max_value):
            raise serializers.ValidationError({
                field: f"{field} must satisfy {min_value} <= value <= {max_value}"
            })


def validate_sensor_numeric_fields(attrs):
    _validate_numeric_bounds(attrs, SENSOR_FIELD_BOUNDS)


def validate_json_finite(value, field_name: str):
    def walk(node, path):
        if isinstance(node, dict):
            for key, child in node.items():
                walk(child, f"{path}.{key}")
            return
        if isinstance(node, list):
            for index, child in enumerate(node):
                walk(child, f"{path}[{index}]")
            return
        if isinstance(node, float) and not isfinite(node):
            raise serializers.ValidationError(
                {field_name: f"{field_name} contains non-finite number at {path}"}
            )

    walk(value, field_name)
    return value


def _validate_sensor_error_keys(value):
    unknown = sorted(str(key) for key in value.keys() if str(key) not in KNOWN_SENSOR_ERROR_KEYS)
    if unknown:
        raise serializers.ValidationError(
            f"sensor_errors only supports keys: {', '.join(sorted(KNOWN_SENSOR_ERROR_KEYS))}"
        )
    return value


def _apply_soil_preset(attrs):
    if "soil_type" not in attrs:
        return attrs

    soil_type = str(attrs["soil_type"]).strip().lower()
    if soil_type not in FAO56_SOIL_PRESETS:
        allowed = ", ".join(sorted(FAO56_SOIL_PRESETS))
        raise serializers.ValidationError({"soil_type": f"soil_type must be one of: {allowed}"})

    attrs["soil_type"] = soil_type
    attrs.update(FAO56_SOIL_PRESETS[soil_type])
    return attrs


def _validate_fao56_physical_config(instance, attrs):
    latitude = _finite_fao_value(instance, attrs, "latitude")
    longitude = _finite_fao_value(instance, attrs, "longitude")
    theta_fc = _finite_fao_value(instance, attrs, "theta_fc")
    theta_wp = _finite_fao_value(instance, attrs, "theta_wp")
    root_depth_m = _finite_fao_value(instance, attrs, "root_depth_m")
    depletion_fraction_p = _finite_fao_value(instance, attrs, "depletion_fraction_p")
    pump_efficiency = _finite_fao_value(instance, attrs, "pump_efficiency")
    pump_flow_lps = _finite_fao_value(instance, attrs, "pump_flow_lps")
    irrigation_area_m2 = _finite_fao_value(instance, attrs, "irrigation_area_m2")
    soil_type = str(_current_or_default(instance, attrs, "soil_type", "loam")).strip().lower()

    if soil_type not in FAO56_SOIL_PRESETS:
        allowed = ", ".join(sorted(FAO56_SOIL_PRESETS))
        raise serializers.ValidationError({"soil_type": f"soil_type must be one of: {allowed}"})
    if not (-90.0 <= latitude <= 90.0):
        raise serializers.ValidationError({"latitude": "latitude must satisfy -90 <= value <= 90"})
    if not (-180.0 <= longitude <= 180.0):
        raise serializers.ValidationError({"longitude": "longitude must satisfy -180 <= value <= 180"})
    if not (0.0 <= theta_wp < theta_fc <= 0.8):
        raise serializers.ValidationError({
            "theta_fc": "theta values must satisfy 0 <= theta_wp < theta_fc <= 0.8"
        })
    if root_depth_m <= 0:
        raise serializers.ValidationError({"root_depth_m": "root_depth_m must be > 0"})
    if not (0.0 < depletion_fraction_p < 1.0):
        raise serializers.ValidationError({"depletion_fraction_p": "depletion_fraction_p must satisfy 0 < p < 1"})
    if not (0.0 < pump_efficiency <= 1.0):
        raise serializers.ValidationError({"pump_efficiency": "pump_efficiency must satisfy 0 < value <= 1"})
    if pump_flow_lps <= 0:
        raise serializers.ValidationError({"pump_flow_lps": "pump_flow_lps must be > 0"})
    if irrigation_area_m2 <= 0:
        raise serializers.ValidationError({"irrigation_area_m2": "irrigation_area_m2 must be > 0"})


def _validate_runtime_common(
    instance,
    attrs,
    defaults,
    cost_fields,
    stale_field,
    actuator_timeout_field=None,
):
    crop_kc = _finite_runtime_value(instance, attrs, "crop_kc", defaults)
    target_low = _finite_runtime_value(instance, attrs, "target_low", defaults)
    target_high = _finite_runtime_value(instance, attrs, "target_high", defaults)
    step_seconds = _finite_runtime_value(instance, attrs, "step_seconds", defaults)
    horizon_steps = _finite_runtime_value(instance, attrs, "horizon_steps", defaults)
    pump_min = _finite_runtime_value(instance, attrs, "pump_min_seconds", defaults)
    pump_max = _finite_runtime_value(instance, attrs, "pump_max_seconds", defaults)
    stale_after_seconds = _finite_runtime_value(instance, attrs, stale_field, defaults)

    if crop_kc < 0:
        raise serializers.ValidationError({"crop_kc": "crop_kc must be >= 0"})
    if not (0.0 <= target_low < target_high <= 100.0):
        raise serializers.ValidationError("target_low/target_high must satisfy 0 <= low < high <= 100")
    depletion_fraction_p = _current_or_default(
        instance,
        attrs,
        "depletion_fraction_p",
        FAO56_NUMERIC_DEFAULTS["depletion_fraction_p"],
    )
    if not (0.0 < depletion_fraction_p < 1.0):
        raise serializers.ValidationError({"depletion_fraction_p": "depletion_fraction_p must satisfy 0 < p < 1"})
    sensor_wp = target_high - ((target_high - target_low) / depletion_fraction_p)
    if sensor_wp < 0.0:
        raise serializers.ValidationError({
            "target_low": (
                "target_low/target_high cannot map to FAO RAW with current "
                "depletion_fraction_p; narrow the band or increase depletion_fraction_p"
            )
        })
    if step_seconds < 5 or int(step_seconds) != step_seconds or int(step_seconds) % 5 != 0:
        raise serializers.ValidationError({
            "step_seconds": "step_seconds must be an integer multiple of 5 seconds"
        })
    if horizon_steps < 1 or int(horizon_steps) != horizon_steps:
        raise serializers.ValidationError({"horizon_steps": "horizon_steps must be >= 1"})
    if pump_min < 0 or pump_max <= pump_min:
        raise serializers.ValidationError("pump_max_seconds must be greater than pump_min_seconds")
    for field in cost_fields:
        value = _finite_runtime_value(instance, attrs, field, defaults)
        if value < 0:
            raise serializers.ValidationError({field: f"{field} must be >= 0"})
    if stale_after_seconds <= 0:
        raise serializers.ValidationError({stale_field: f"{stale_field} must be > 0"})
    if actuator_timeout_field is not None:
        actuator_timeout = _finite_runtime_value(instance, attrs, actuator_timeout_field, defaults)
        if actuator_timeout <= 0:
            raise serializers.ValidationError({actuator_timeout_field: f"{actuator_timeout_field} must be > 0"})


class LoginSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["username"] = user.get_username()
        return token


class DeviceStateSerializer(serializers.ModelSerializer):
    device_type = serializers.CharField(source='device_code')
    status = serializers.SerializerMethodField()
    state = serializers.SerializerMethodField()
    name = serializers.SerializerMethodField()
    code = serializers.CharField(source='device_code')

    class Meta:
        model = DeviceState
        fields = ["id", "name", "code", "device_type", "status", "state", "device_code", "is_on", "desired_on", "last_command", "last_value", "extra", "updated_at"]

    def get_status(self, obj):
        from .services import is_esp32_online
        return 'online' if is_esp32_online() else 'offline'
        
    def get_state(self, obj):
        return {
            'is_on': obj.is_on,
            'updated_at': obj.updated_at
        }

    def get_name(self, obj):
        names = {
            'fan': 'Quạt thông gió',
            'light': 'Đèn chiếu sáng',
            'pump': 'Bơm tưới nước',
            'mist': 'Máy phun sương',
        }
        return names.get(obj.device_code, obj.device_code)


class SensorDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = SensorData
        fields = [
            "id",
            "temperature",
            "humidity",
            "light",
            "soil_moisture",
            "payload",
            "recorded_at",
        ]


class ControlStateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ControlState
        fields = ["mode", "manual_reason", "manual_changed_at", "updated_at"]


class AMPCSchedulerStateSerializer(serializers.ModelSerializer):
    class Meta:
        model = AMPCSchedulerState
        fields = [
            "is_enabled",
            "interval_seconds",
            "is_executing",
            "last_started_at",
            "last_stopped_at",
            "last_run_at",
            "next_run_at",
            "last_status",
            "last_error",
            "updated_at",
        ]


class EstimationCycleSerializer(serializers.ModelSerializer):
    class Meta:
        model = EstimationCycle
        fields = [
            "id",
            "sample_ts",
            "cycle_index",
            "slice_type",
            "source_type",
            "validation_status",
            "validation_reason",
            "preprocess_status",
            "cycle_status",
            "adaptive_status",
            "raw_soil_moisture",
            "raw_temperature",
            "raw_humidity",
            "raw_light",
            "raw_drip",
            "raw_mist",
            "raw_fan",
            "arx_predicted",
            "kf_x_prior",
            "kf_P_prior",
            "kf_innovation",
            "kf_x_posterior",
            "kf_P_posterior",
            "kf_R",
            "kf_K",
            "latency_ms",
            "error_message",
            "ingest_dedupe_key",
        ]


class GreenhouseControlProfileSerializer(serializers.ModelSerializer):
    actuator_configured = serializers.BooleanField(read_only=True)

    class Meta:
        model = GreenhouseControlProfile
        fields = [
            "id",
            "owner",
            "crop_name",
            "crop_kc",
            *FAO56_PHYSICAL_FIELDS,
            "target_low",
            "target_high",
            "pump_max_seconds",
            "actuator_enabled",
            "step_seconds",
            "horizon_steps",
            "pump_min_seconds",
            "cost_band_violation",
            "cost_water_use",
            "cost_switching",
            "cost_terminal_band_violation",
            "safety_stale_after_seconds",
            "actuator_timeout_seconds",
            "actuator_configured",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "owner", "theta_fc", "theta_wp", "created_at", "updated_at"]

    def validate(self, attrs):
        initial_keys = set(getattr(self, "initial_data", {}) or {})
        manual_derived = sorted(initial_keys & set(FAO56_THETA_FIELDS))
        if "pump_max_seconds" in initial_keys and "step_seconds" not in initial_keys:
            manual_derived.append("pump_max_seconds")
        if manual_derived:
            raise serializers.ValidationError({
                field: f"{field} is derived from other settings and cannot be set directly"
                for field in manual_derived
            })
        attrs = _apply_soil_preset(attrs)
        if "step_seconds" in attrs:
            attrs["pump_max_seconds"] = attrs["step_seconds"]
        _validate_runtime_common(
            self.instance,
            attrs,
            GREENHOUSE_RUNTIME_NUMERIC_DEFAULTS,
            (
                "cost_band_violation",
                "cost_water_use",
                "cost_switching",
                "cost_terminal_band_violation",
            ),
            "safety_stale_after_seconds",
            "actuator_timeout_seconds",
        )
        _validate_fao56_physical_config(self.instance, attrs)
        return attrs


ESP32_THRESHOLD_FIELDS = [
    "thresh_temp_fan_on",
    "thresh_temp_fan_off",
    "thresh_hum_fan_on",
    "thresh_hum_fan_off",
    "thresh_hum_mist_on",
    "thresh_hum_mist_off",
    "thresh_soil_pump_on",
    "thresh_soil_pump_off",
    "thresh_light_on_ldr",
    "thresh_light_off_ldr",
]


class ESP32ThresholdSerializer(serializers.ModelSerializer):
    """Serializer riêng cho ngưỡng điều khiển ESP32."""

    class Meta:
        model = GreenhouseControlProfile
        fields = ESP32_THRESHOLD_FIELDS + ["updated_at"]

    def validate(self, attrs):
        t_on = attrs.get("thresh_temp_fan_on", getattr(self.instance, "thresh_temp_fan_on", 32.0))
        t_off = attrs.get("thresh_temp_fan_off", getattr(self.instance, "thresh_temp_fan_off", 30.0))
        if t_on <= t_off:
            raise serializers.ValidationError(
                {"thresh_temp_fan_on": "Ngưỡng bật quạt (nhiệt độ) phải lớn hơn ngưỡng tắt"}
            )

        h_fan_on = attrs.get("thresh_hum_fan_on", getattr(self.instance, "thresh_hum_fan_on", 80.0))
        h_fan_off = attrs.get("thresh_hum_fan_off", getattr(self.instance, "thresh_hum_fan_off", 70.0))
        if h_fan_on <= h_fan_off:
            raise serializers.ValidationError(
                {"thresh_hum_fan_on": "Ngưỡng bật quạt (độ ẩm) phải lớn hơn ngưỡng tắt"}
            )

        h_mist_on = attrs.get("thresh_hum_mist_on", getattr(self.instance, "thresh_hum_mist_on", 55.0))
        h_mist_off = attrs.get("thresh_hum_mist_off", getattr(self.instance, "thresh_hum_mist_off", 65.0))
        if h_mist_on >= h_mist_off:
            raise serializers.ValidationError(
                {"thresh_hum_mist_off": "Ngưỡng tắt phun sương phải lớn hơn ngưỡng bật"}
            )

        s_on = attrs.get("thresh_soil_pump_on", getattr(self.instance, "thresh_soil_pump_on", 35.0))
        s_off = attrs.get("thresh_soil_pump_off", getattr(self.instance, "thresh_soil_pump_off", 40.0))
        if s_on >= s_off:
            raise serializers.ValidationError(
                {"thresh_soil_pump_off": "Ngưỡng tắt bơm phải lớn hơn ngưỡng bật"}
            )

        l_on = attrs.get("thresh_light_on_ldr", getattr(self.instance, "thresh_light_on_ldr", 20))
        l_off = attrs.get("thresh_light_off_ldr", getattr(self.instance, "thresh_light_off_ldr", 40))
        if l_on >= l_off:
            raise serializers.ValidationError(
                {"thresh_light_off_ldr": "Ngưỡng tắt đèn (LDR) phải lớn hơn ngưỡng bật"}
            )
        return attrs

class AMPCRecommendationSerializer(serializers.ModelSerializer):
    class Meta:
        model = AMPCRecommendation
        fields = [
            "id",
            "owner",
            "sensor_data",
            "estimation",
            "device_command",
            "mode",
            "pump_seconds",
            "step_seconds",
            "predicted_soil_moisture",
            "target_band",
            "objective_cost",
            "safety_status",
            "reason",
            "command_created",
            "actuator_status",
            "config_snapshot",
            "state_snapshot",
            "created_at",
        ]


class LegacyAMPCRecommendationSerializer(serializers.ModelSerializer):
    predicted_soil_moisture = serializers.JSONField()
    target_band = serializers.JSONField()
    actuator = serializers.SerializerMethodField()
    state_cycle_id = serializers.IntegerField(source="estimation_id", read_only=True)
    cost = serializers.FloatField(source="objective_cost", read_only=True)

    class Meta:
        model = AMPCRecommendation
        fields = [
            "id",
            "mode",
            "state_cycle_id",
            "pump_seconds",
            "step_seconds",
            "predicted_soil_moisture",
            "target_band",
            "cost",
            "safety_status",
            "reason",
            "actuator",
            "state_snapshot",
            "created_at",
        ]

    def get_actuator(self, obj):
        return {
            "status": obj.actuator_status,
            "command_created": obj.command_created,
            "device_command_id": obj.device_command_id,
        }


class IngestReadingSerializer(serializers.Serializer):
    owner_id = serializers.IntegerField(required=False, min_value=1)
    admin_id = serializers.IntegerField(required=False, min_value=1)
    user_id = serializers.IntegerField(required=False, min_value=1)
    recorded_at = serializers.DateTimeField(required=False)
    soil_moisture = serializers.FloatField(required=False, allow_null=True)
    temperature = serializers.FloatField(required=False, allow_null=True)
    humidity = serializers.FloatField(required=False, allow_null=True)
    light = serializers.FloatField(required=False, allow_null=True)
    payload = serializers.DictField(required=False)
    metadata = serializers.DictField(required=False)
    sensor_errors = serializers.DictField(required=False)
    device_states = serializers.DictField(required=False)
    firmware_version = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=DEVICE_FIRMWARE_MAX_LENGTH,
    )
    overwrite = serializers.BooleanField(required=False)
    auto_mode = serializers.BooleanField(required=False)
    mode = serializers.CharField(required=False, allow_blank=True)
    manual_reason = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=MANUAL_REASON_MAX_LENGTH,
    )

    def validate(self, attrs):
        validate_sensor_numeric_fields(attrs)
        return attrs

    def validate_payload(self, value):
        return validate_json_finite(value, "payload")

    def validate_metadata(self, value):
        return validate_json_finite(value, "metadata")

    def validate_sensor_errors(self, value):
        return validate_json_finite(_validate_sensor_error_keys(value), "sensor_errors")

    def validate_device_states(self, value):
        return validate_json_finite(value, "device_states")





class ControlModeInputSerializer(serializers.Serializer):
    mode = serializers.CharField(max_length=10)
    reason = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=MANUAL_REASON_MAX_LENGTH,
    )

    def validate_mode(self, value):
        mode = value.upper().strip()
        if mode not in ControlState.Mode.values:
            raise serializers.ValidationError("mode must be AUTO or MANUAL")
        return mode


class DeviceCommandInputSerializer(serializers.Serializer):
    command = serializers.CharField(
        allow_blank=False,
        trim_whitespace=True,
        max_length=DEVICE_COMMAND_TEXT_MAX_LENGTH,
    )
    value = serializers.CharField(
        required=False,
        allow_blank=True,
        max_length=DEVICE_COMMAND_TEXT_MAX_LENGTH,
    )
    payload = serializers.DictField(required=False)

    def validate_payload(self, value):
        return validate_json_finite(value, "payload")


class DeviceCommandAckInputSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=COMMAND_STATUS_VALUES, required=False)
    actual_state = serializers.BooleanField(required=False, allow_null=True)


class AlertSerializer(serializers.ModelSerializer):
    zone = serializers.SerializerMethodField()
    zone_name = serializers.SerializerMethodField()
    device_name = serializers.SerializerMethodField()

    class Meta:
        model = Alert
        fields = [
            "id",
            "zone",
            "zone_name",
            "device_code",
            "device_name",
            "level",
            "title",
            "message",
            "is_read",
            "happened_at",
        ]

    def get_zone(self, obj):
        return getattr(settings, "APP_ZONE_ID", 1)

    def get_zone_name(self, obj):
        return getattr(settings, "APP_ZONE_NAME", "Nhà kính chính")

    def get_device_name(self, obj):
        return obj.device_code or ''


class DeviceCommandSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeviceCommand
        fields = [
            "id",
            "device_code",
            "command",
            "value",
            "payload",
            "status",
            "created_at",
            "acked_at",
        ]
