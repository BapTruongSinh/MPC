import type { ControlProfile, FaoSoilType } from "../api/endpoints";

export type AutoSettingsNumericField = keyof Pick<
  ControlProfile,
  | "crop_kc"
  | "latitude"
  | "longitude"
  | "root_depth_m"
  | "depletion_fraction_p"
  | "pump_efficiency"
  | "pump_flow_lps"
  | "irrigation_area_m2"
  | "target_low"
  | "target_high"
  | "step_seconds"
  | "horizon_steps"
  | "weight_band"
  | "weight_water"
  | "weight_switch"
  | "weight_terminal"
>;

export type AutoSettingsPayloadField =
  | AutoSettingsNumericField
  | "soil_type"
  | "actuator_enabled";

export type NumericFieldConfig = {
  field: AutoSettingsNumericField;
  label: string;
  suffix: string;
  step: string;
  min?: number;
  max?: number;
  helper?: string;
};

export type NumericFieldGroup = {
  title: string;
  description: string;
  fields: NumericFieldConfig[];
};

export const FAO_SOIL_PRESETS: Record<
  FaoSoilType,
  { label: string; theta_fc: number; theta_wp: number }
> = {
  sand: { label: "Cát", theta_fc: 0.1, theta_wp: 0.04 },
  light_loam: { label: "Thịt nhẹ", theta_fc: 0.15, theta_wp: 0.06 },
  loam: { label: "Đất thịt", theta_fc: 0.32, theta_wp: 0.15 },
  clay_loam: { label: "Thịt sét", theta_fc: 0.35, theta_wp: 0.23 },
};

export const FAO_SOIL_OPTIONS: FaoSoilType[] = ["sand", "light_loam", "loam", "clay_loam"];

export const AUTO_SETTINGS_NUMERIC_GROUPS: NumericFieldGroup[] = [
  {
    title: "FAO-56",
    description: "Thông số vật lý cho mô hình Dr/RAW.",
    fields: [
      { field: "crop_kc", label: "Kc cây trồng", helper: "Hệ số cây trồng, ứng với mỗi loại cây sẽ có một hệ số riêng", suffix: "", step: "0.01", min: 0 },
      { field: "root_depth_m", label: "Zr độ sâu rễ", helper: "Độ sâu vùng rễ, đối với mỗi loại cây thì rễ chính sẽ dài khác nhau", suffix: "m", step: "0.01", min: 0.01 },
      { field: "depletion_fraction_p", label: "p depletion", helper: "Tỉ lệ nước nước quanh rễ cây mà cây có thể sử dụng được", suffix: "", step: "0.01", min: 0.01, max: 0.99 },
      { field: "pump_flow_lps", label: "Q lưu lượng bơm", helper: "Lưu lượng nước bơm theo lít mỗi giây của máy bơm.", suffix: "L/s", step: "0.001", min: 0.001 },
      { field: "irrigation_area_m2", label: "A diện tích tưới", helper: "Diện tích đất mà máy bơm có thể tưới được.", suffix: "m2", step: "0.01", min: 0.01 },
      { field: "pump_efficiency", label: "eta hiệu suất bơm", helper: "Tỉ lệ nước bơm ra đi tới vùng rễ của cây", suffix: "", step: "0.01", min: 0.01, max: 1 },
    ],
  },
  {
    title: "Vị trí",
    description: "Tọa độ nhà kính dùng cho ET0.",
    fields: [
      { field: "latitude", label: "Vĩ độ", helper: "Tọa độ hiện tại của nhà kính", suffix: "deg", step: "0.0001", min: -90, max: 90 },
      { field: "longitude", label: "Kinh độ", helper: "Tọa độ hiện tại của nhà kính", suffix: "deg", step: "0.0001", min: -180, max: 180 },
    ],
  },
  {
    title: "Dự báo và điều khiển",
    description: "Ngưỡng cảm biến, chu kỳ dự báo và trọng số tối ưu.",
    fields: [
      { field: "target_low", label: "Ngưỡng sensor thấp", helper: "Độ ẩm trong đất ở mức thấp, đảm bảo cây phát triển bình thường", suffix: "%", step: "1", min: 0, max: 100 },
      { field: "target_high", label: "Ngưỡng sensor cao", helper: "Độ ẩm trong đất ở mức cao, đảm bảo cây không bị ngập nước", suffix: "%", step: "1", min: 0, max: 100 },
      { field: "step_seconds", label: "Thời gian mỗi bước", helper: "Độ dài một bước dự báo", suffix: "giây", step: "5", min: 5 },
      { field: "horizon_steps", label: "Số bước dự báo", helper: "Số bước tương lai để dự đoán", suffix: "bước", step: "1", min: 1 },
      { field: "weight_band", label: "Trọng số stress/overwater", helper: "Mức phạt khi đất quá khô hoặc quá ẩm.", suffix: "", step: "0.1", min: 0 },
      { field: "weight_water", label: "Trọng số tiết kiệm nước", helper: "Mức phạt cho việc dùng nhiều nước.", suffix: "", step: "0.1", min: 0 },
      { field: "weight_switch", label: "Trọng số đổi lệnh", helper: "Mức phạt khi lệnh bơm thay đổi mạnh so với lần trước.", suffix: "", step: "0.1", min: 0 },
      { field: "weight_terminal", label: "Trọng số cuối chu kỳ", helper: "Mức phạt trạng thái đất ở cuối dự báo.", suffix: "", step: "0.1", min: 0 },
    ],
  },
];

export const AUTO_SETTINGS_PAYLOAD_FIELDS: AutoSettingsPayloadField[] = [
  "crop_kc",
  "latitude",
  "longitude",
  "soil_type",
  "root_depth_m",
  "depletion_fraction_p",
  "pump_efficiency",
  "pump_flow_lps",
  "irrigation_area_m2",
  "target_low",
  "target_high",
  "step_seconds",
  "horizon_steps",
  "weight_band",
  "weight_water",
  "weight_switch",
  "weight_terminal",
  "actuator_enabled",
];

export function applySoilPreset(profile: ControlProfile, soilType: FaoSoilType): ControlProfile {
  const preset = FAO_SOIL_PRESETS[soilType];
  return {
    ...profile,
    soil_type: soilType,
    theta_fc: preset.theta_fc,
    theta_wp: preset.theta_wp,
  };
}

export function isFaoSoilType(value: string): value is FaoSoilType {
  return value === "sand" || value === "light_loam" || value === "loam" || value === "clay_loam";
}

export function buildAutoSettingsPayload(profile: ControlProfile): Partial<ControlProfile> {
  return AUTO_SETTINGS_PAYLOAD_FIELDS.reduce<Partial<ControlProfile>>((payload, field) => {
    return { ...payload, [field]: profile[field] };
  }, {});
}

const FINITE_NUMERIC_LABELS: Array<[AutoSettingsNumericField, string]> = [
  ["crop_kc", "Kc cây trồng"],
  ["latitude", "Vĩ độ"],
  ["longitude", "Kinh độ"],
  ["root_depth_m", "Zr độ sâu rễ"],
  ["depletion_fraction_p", "p depletion"],
  ["pump_efficiency", "eta hiệu suất bơm"],
  ["pump_flow_lps", "Q lưu lượng bơm"],
  ["irrigation_area_m2", "A diện tích tưới"],
  ["target_low", "Ngưỡng sensor thấp"],
  ["target_high", "Ngưỡng sensor cao"],
  ["step_seconds", "Thời gian mỗi bước"],
  ["horizon_steps", "Số bước dự báo"],
  ["weight_band", "Trọng số stress/overwater"],
  ["weight_water", "Trọng số tiết kiệm nước"],
  ["weight_switch", "Trọng số đổi lệnh"],
  ["weight_terminal", "Trọng số cuối chu kỳ"],
];

const NON_NEGATIVE_NUMERIC_LABELS: Array<[AutoSettingsNumericField, string]> = [
  ["crop_kc", "Kc cây trồng"],
  ["weight_band", "Trọng số stress/overwater"],
  ["weight_water", "Trọng số tiết kiệm nước"],
  ["weight_switch", "Trọng số đổi lệnh"],
  ["weight_terminal", "Trọng số cuối chu kỳ"],
];

function validateFiniteNumbers(profile: ControlProfile): string {
  for (const [field, label] of FINITE_NUMERIC_LABELS) {
    if (!Number.isFinite(profile[field])) {
      return `${label} phải là số hữu hạn.`;
    }
  }
  return "";
}

function validateNonNegativeNumbers(profile: ControlProfile): string {
  for (const [field, label] of NON_NEGATIVE_NUMERIC_LABELS) {
    if (profile[field] < 0) {
      return `${label} phải lớn hơn hoặc bằng 0.`;
    }
  }
  return "";
}

export function validateAutoSettings(profile: ControlProfile): string {
  const finiteError = validateFiniteNumbers(profile);
  if (finiteError) return finiteError;

  const nonNegativeError = validateNonNegativeNumbers(profile);
  if (nonNegativeError) return nonNegativeError;

  if (profile.root_depth_m <= 0) return "Zr độ sâu rễ phải lớn hơn 0.";
  if (profile.pump_flow_lps <= 0) return "Q lưu lượng bơm phải lớn hơn 0.";
  if (profile.irrigation_area_m2 <= 0) return "A diện tích tưới phải lớn hơn 0.";
  if (profile.pump_efficiency <= 0 || profile.pump_efficiency > 1) {
    return "eta hiệu suất bơm phải trong khoảng 0-1.";
  }
  if (profile.depletion_fraction_p <= 0 || profile.depletion_fraction_p >= 1) {
    return "p depletion phải trong khoảng 0-1.";
  }
  if (profile.latitude < -90 || profile.latitude > 90) return "Vĩ độ phải trong khoảng -90 đến 90.";
  if (profile.longitude < -180 || profile.longitude > 180) return "Kinh độ phải trong khoảng -180 đến 180.";
  if (!(0 <= profile.target_low && profile.target_low < profile.target_high && profile.target_high <= 100)) {
    return "Ngưỡng sensor phải thỏa 0 <= thấp < cao <= 100.";
  }
  if (
    !Number.isInteger(profile.step_seconds) ||
    profile.step_seconds < 5 ||
    profile.step_seconds % 5 !== 0
  ) {
    return "Thời gian mỗi bước phải là bội số 5 giây.";
  }
  if (!Number.isInteger(profile.horizon_steps) || profile.horizon_steps < 1) {
    return "Số bước dự báo phải là số nguyên >= 1.";
  }
  return "";
}

export function readAutoSettingsError(error: unknown): string {
  if (typeof error === "object" && error !== null && "response" in error) {
    const responseValue = error.response;
    const response = typeof responseValue === "object" && responseValue !== null ? responseValue : null;
    const data = response && "data" in response ? response.data : undefined;
    if (typeof data === "string") return data;
    if (typeof data === "object" && data !== null) {
      const detail = "detail" in data ? data.detail : undefined;
      if (typeof detail === "string") return detail;
      const firstValue = Object.values(data)[0];
      if (Array.isArray(firstValue) && typeof firstValue[0] === "string") return firstValue[0];
      if (typeof firstValue === "string") return firstValue;
    }
  }
  return "Lưu cấu hình thất bại.";
}
