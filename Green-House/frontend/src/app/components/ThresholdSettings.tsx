import { useEffect, useState } from "react";
import { Save, AlertCircle, CheckCircle2 } from "lucide-react";
import type { ESP32Thresholds } from "../api/endpoints";
import { getThresholds, updateThresholds } from "../api/endpoints";

type ThresholdKey = keyof Omit<ESP32Thresholds, "updated_at">;

interface ThresholdRow {
  key: ThresholdKey;
  label: string;
  unit: string;
  min: number;
  max: number;
  step: number;
}

interface ThresholdGroup {
  title: string;
  dot: string;
  rows: ThresholdRow[];
}

const GROUPS: ThresholdGroup[] = [
  {
    title: "Quạt thông gió",
    dot: "#f97316",
    rows: [
      { key: "thresh_temp_fan_on",  label: "Bật quạt khi nhiệt độ ≥", unit: "°C", min: 20, max: 50, step: 0.5 },
      { key: "thresh_temp_fan_off", label: "Tắt quạt khi nhiệt độ ≤",  unit: "°C", min: 18, max: 49, step: 0.5 },
      { key: "thresh_hum_fan_on",   label: "Bật quạt khi độ ẩm ≥",     unit: "%",  min: 50, max: 100, step: 1  },
      { key: "thresh_hum_fan_off",  label: "Tắt quạt khi độ ẩm ≤",     unit: "%",  min: 40, max: 99,  step: 1  },
    ],
  },
  {
    title: "Phun sương",
    dot: "#0ea5e9",
    rows: [
      { key: "thresh_hum_mist_on",  label: "Bật phun sương khi độ ẩm ≤", unit: "%", min: 10, max: 90, step: 1 },
      { key: "thresh_hum_mist_off", label: "Tắt phun sương khi độ ẩm ≥", unit: "%", min: 11, max: 95, step: 1 },
    ],
  },
  {
    title: "Bơm tưới nước",
    dot: "#10b981",
    rows: [
      { key: "thresh_soil_pump_on",  label: "Bật bơm khi độ ẩm đất ≤", unit: "%", min: 5,  max: 80, step: 1 },
      { key: "thresh_soil_pump_off", label: "Tắt bơm khi độ ẩm đất ≥", unit: "%", min: 6,  max: 90, step: 1 },
    ],
  },
  {
    title: "Đèn chiếu sáng",
    dot: "#eab308",
    rows: [
      { key: "thresh_light_on_ldr",  label: "Bật đèn khi LDR ≤", unit: "/1000", min: 0,  max: 500, step: 5 },
      { key: "thresh_light_off_ldr", label: "Tắt đèn khi LDR ≥", unit: "/1000", min: 1,  max: 999, step: 5 },
    ],
  },
];

type DraftValues = Record<ThresholdKey, string>;

function toStringDraft(vals: Omit<ESP32Thresholds, "updated_at">): DraftValues {
  return Object.fromEntries(
    Object.entries(vals).map(([k, v]) => [k, String(v)])
  ) as DraftValues;
}

export function ThresholdSettings() {
  // Lưu numeric values (source of truth khi save)
  const [saved, setSaved] = useState<Omit<ESP32Thresholds, "updated_at"> | null>(null);
  // Lưu string values cho input (để user gõ tự do không bị reset về 0)
  const [draft, setDraft] = useState<DraftValues | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    getThresholds()
      .then((res) => {
        if (!cancelled) {
          const { updated_at, ...rest } = res.data;
          setSaved(rest);
          setDraft(toStringDraft(rest));
        }
      })
      .catch(() => { if (!cancelled) setError("Không tải được ngưỡng điều khiển."); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, []);

  // Khi user gõ: chỉ cập nhật string draft, không convert sang number ngay
  const handleChange = (key: ThresholdKey, value: string) => {
    setDraft((prev) => prev ? { ...prev, [key]: value } : prev);
  };

  // Khi user rời input: clamp/validate và sync lại string nếu cần
  const handleBlur = (key: ThresholdKey, row: ThresholdRow) => {
    setDraft((prev) => {
      if (!prev) return prev;
      const num = parseFloat(prev[key]);
      if (isNaN(num)) {
        // Trả về giá trị đã lưu trước đó (tránh để trống)
        const fallback = saved ? String(saved[key]) : "0";
        return { ...prev, [key]: fallback };
      }
      const clamped = Math.min(row.max, Math.max(row.min, num));
      return { ...prev, [key]: String(clamped) };
    });
  };

  const save = async () => {
    if (!draft || !saved) return;

    // Chuyển draft string → number để gửi lên server
    const payload = Object.fromEntries(
      Object.entries(draft).map(([k, v]) => {
        const num = parseFloat(v);
        return [k, isNaN(num) ? (saved as any)[k] : num];
      })
    ) as Omit<ESP32Thresholds, "updated_at">;

    setSaving(true);
    setMessage(""); setError("");
    try {
      const res = await updateThresholds(payload);
      const { updated_at, ...rest } = res.data;
      setSaved(rest);
      setDraft(toStringDraft(rest));
      setMessage("Đã lưu và gửi xuống ESP32!");
    } catch (err: any) {
      const detail = err?.response?.data;
      if (detail && typeof detail === "object") {
        const first = Object.values(detail).flat()[0];
        setError(typeof first === "string" ? first : "Lỗi validation.");
      } else {
        setError("Không thể lưu ngưỡng điều khiển.");
      }
    } finally {
      setSaving(false);
    }
  };

  if (loading) return (
    <div className="elevated-card rounded-3xl p-5">
      <p className="text-slate-500" style={{ fontSize: "14px" }}>Đang tải...</p>
    </div>
  );

  if (!draft) return (
    <div className="elevated-card rounded-3xl p-5">
      <p className="text-red-700" style={{ fontSize: "14px", fontWeight: 700 }}>
        {error || "Không tải được ngưỡng điều khiển."}
      </p>
    </div>
  );

  return (
    <div className="elevated-card rounded-3xl p-5">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
        <div>
          <p className="text-slate-800" style={{ fontSize: "16px", fontWeight: 800 }}>
            Ngưỡng điều khiển tự động
          </p>
        </div>
        <button
          onClick={save}
          disabled={saving}
          className="flex items-center gap-2 px-4 py-2 rounded-xl text-white gradient-action hover:-translate-y-0.5 transition-all duration-200 disabled:opacity-60 disabled:translate-y-0 shadow-md"
          style={{ fontSize: "14px", fontWeight: 700 }}
        >
          <Save className="w-4 h-4" />
          {saving ? "Đang lưu..." : "Lưu"}
        </button>
      </div>

      {/* Grid 2 cột */}
      <div className="grid grid-cols-1 xl:grid-cols-2 gap-4 mt-2">
        {GROUPS.map((group) => (
          <div
            key={group.title}
            className="rounded-2xl border border-slate-100 bg-slate-50/60 p-4"
          >
            {/* Group title */}
            <div className="flex items-center gap-2 mb-3">
              <span
                className="w-2.5 h-2.5 rounded-full flex-shrink-0"
                style={{ backgroundColor: group.dot }}
              />
              <span className="text-slate-700" style={{ fontSize: "14px", fontWeight: 700 }}>
                {group.title}
              </span>
            </div>

            {/* Rows */}
            <div className="space-y-2.5">
              {group.rows.map((row) => (
                <div key={row.key} className="flex items-center gap-3">
                  <label
                    htmlFor={`thresh-${row.key}`}
                    className="flex-1 text-slate-600 min-w-0"
                    style={{ fontSize: "13px" }}
                  >
                    {row.label}
                  </label>
                  <div className="flex items-center gap-1.5 flex-shrink-0">
                    <input
                      id={`thresh-${row.key}`}
                      type="number"
                      value={draft[row.key]}
                      min={row.min}
                      max={row.max}
                      step={row.step}
                      onChange={(e) => handleChange(row.key, e.target.value)}
                      onBlur={() => handleBlur(row.key, row)}
                      className="w-22 px-2 py-1.5 rounded-lg border border-slate-200 bg-white text-slate-900 text-right outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100 transition-all"
                      style={{ fontSize: "14px", width: "5.5rem" }}
                    />
                    <span className="text-slate-400 w-12 text-left" style={{ fontSize: "12px" }}>
                      {row.unit}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </div>
        ))}
      </div>

      {/* Status */}
      {(message || error) && (
        <div
          className={`mt-4 flex items-center gap-2 px-4 py-2.5 rounded-xl border ${
            error
              ? "bg-red-50 border-red-100 text-red-700"
              : "bg-emerald-50 border-emerald-100 text-emerald-700"
          }`}
          style={{ fontSize: "14px", fontWeight: 600 }}
        >
          {error
            ? <AlertCircle className="w-4 h-4 flex-shrink-0" />
            : <CheckCircle2 className="w-4 h-4 flex-shrink-0" />}
          {error || message}
        </div>
      )}
    </div>
  );
}
