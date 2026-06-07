import { useMemo, useState } from "react";
import {
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  Activity,
  Loader2,
  MoveHorizontal,
  MoveVertical,
  Power,
  Sun,
} from "lucide-react";
import { useRealtime } from "../contexts/RealtimeContext";
import type { SunTrackerMode } from "../lib/greenhouse.types";

const SUN_SERVO_HORIZONTAL_MIN = 10;
const SUN_SERVO_HORIZONTAL_MAX = 170;

const SUN_SERVO_VERTICAL_MIN = 10;
const SUN_SERVO_VERTICAL_MAX = 80;

function clamp(value: number, min: number, max: number) {
  return Math.min(max, Math.max(min, value));
}

function clampServoHorizontal(value: number) {
  return clamp(Math.round(value), SUN_SERVO_HORIZONTAL_MIN, SUN_SERVO_HORIZONTAL_MAX);
}

function clampServoVertical(value: number) {
  return clamp(Math.round(value), SUN_SERVO_VERTICAL_MIN, SUN_SERVO_VERTICAL_MAX);
}

function formatTime(value: string | null, index: number) {
  if (!value) return `#${index + 1}`;

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return `#${index + 1}`;

  return parsed.toLocaleTimeString("vi-VN", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

function polarToCartesian(cx: number, cy: number, r: number, angleDeg: number) {
  const rad = (angleDeg * Math.PI) / 180;

  return {
    x: cx + r * Math.cos(rad),
    y: cy - r * Math.sin(rad),
  };
}

function describeArc(
  cx: number,
  cy: number,
  r: number,
  startAngle: number,
  endAngle: number,
  sweepFlag = 1,
) {
  const start = polarToCartesian(cx, cy, r, startAngle);
  const end = polarToCartesian(cx, cy, r, endAngle);
  const largeArcFlag = Math.abs(endAngle - startAngle) > 180 ? 1 : 0;

  return `M ${start.x} ${start.y} A ${r} ${r} 0 ${largeArcFlag} ${sweepFlag} ${end.x} ${end.y}`;
}

function SensorSunIcon() {
  return (
    <svg
      width="22"
      height="22"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2v2" />
      <path d="M12 20v2" />
      <path d="m4.93 4.93 1.41 1.41" />
      <path d="m17.66 17.66 1.41 1.41" />
      <path d="M2 12h2" />
      <path d="M20 12h2" />
      <path d="m6.34 17.66-1.41 1.41" />
      <path d="m19.07 4.93-1.41 1.41" />
    </svg>
  );
}

type SensorTheme = "orange" | "blue" | "green" | "red";

const themeMap: Record<
  SensorTheme,
  {
    icon: string;
    tag: string;
    text: string;
  }
> = {
  orange: {
    icon: "bg-orange-50 text-orange-500",
    tag: "bg-orange-50 text-orange-500",
    text: "text-orange-500",
  },
  blue: {
    icon: "bg-blue-50 text-blue-600",
    tag: "bg-blue-50 text-blue-600",
    text: "text-blue-600",
  },
  green: {
    icon: "bg-emerald-50 text-emerald-600",
    tag: "bg-emerald-50 text-emerald-600",
    text: "text-emerald-600",
  },
  red: {
    icon: "bg-red-50 text-red-500",
    tag: "bg-red-50 text-red-500",
    text: "text-red-500",
  },
};

function SensorCard({
  tag,
  label,
  value,
  theme,
}: {
  tag: string;
  label: string;
  value: number;
  theme: SensorTheme;
}) {
  const classes = themeMap[theme];

  return (
    <article className="rounded-[24px] bg-white border border-slate-200 shadow-sm p-5 min-h-[150px]">
      <div className="flex items-start justify-between gap-3">
        <div
          className={`w-12 h-12 rounded-xl flex items-center justify-center ${classes.icon}`}
        >
          <SensorSunIcon />
        </div>

        <span
          className={`rounded-full px-3 py-1 text-xs font-bold ${classes.tag}`}
        >
          {tag}
        </span>
      </div>

      <p className="mt-5 mb-0 text-slate-500 text-sm font-semibold">
        {label}
      </p>

      <div className="mt-2 flex items-end gap-2">
        <span className="text-slate-900 text-[30px] leading-none font-black tracking-[-0.03em]">
          {Math.round(value)}
        </span>
        <small className="mb-1 text-slate-400 text-xs font-bold">Lux</small>
      </div>
    </article>
  );
}

function VerticalAxisControl({
  value,
  disabled,
  busy,
  onChange,
}: {
  value: number;
  disabled: boolean;
  busy: boolean;
  onChange: (value: number) => void;
}) {
  const visualValue = clamp(value, SUN_SERVO_VERTICAL_MIN, SUN_SERVO_VERTICAL_MAX);
  const minY = 145;
  const maxY = 35;
  const range = SUN_SERVO_VERTICAL_MAX - SUN_SERVO_VERTICAL_MIN;
  const y = minY - ((visualValue - SUN_SERVO_VERTICAL_MIN) / range) * (minY - maxY);

  const updateFromPointer = (
    event:
      | React.PointerEvent<SVGSVGElement>
      | React.MouseEvent<SVGSVGElement, MouseEvent>,
  ) => {
    if (disabled) return;

    const rect = event.currentTarget.getBoundingClientRect();
    const pointerY = ((event.clientY - rect.top) / rect.height) * 178;
    const fraction = (minY - pointerY) / (minY - maxY);
    const next = Math.round(SUN_SERVO_VERTICAL_MIN + fraction * range);

    onChange(clampServoVertical(next));
  };

  return (
    <section
      className={`rounded-[22px] border p-5 transition ${
        disabled
          ? "bg-slate-50 border-slate-200 opacity-60"
          : "bg-white border-slate-200 shadow-sm"
      }`}
    >
      <div className="flex items-start justify-between gap-4">
        <div>
          <h3 className="m-0 text-slate-900 text-[17px] font-black">
            Trục dọc
          </h3>
          <p className="mt-1 mb-0 text-slate-500 text-sm font-medium">
            Điều chỉnh lên / xuống
          </p>
        </div>

        <div className="flex items-center gap-1 text-slate-900 font-black">
          {busy ? (
            <Loader2 className="w-4 h-4 animate-spin text-blue-600" />
          ) : (
            <input
              type="text"
              value={visualValue}
              disabled={disabled}
              onChange={(event) => onChange(clampServoVertical(Number(event.target.value)))}
              className="w-[54px] h-9 rounded-xl border border-slate-200 bg-slate-50 text-center text-slate-900 text-lg font-black outline-none focus:border-blue-400 disabled:cursor-not-allowed"
            />
          )}
          <span>°</span>
        </div>
      </div>

      <svg
        className={`mt-4 w-full h-[178px] ${disabled ? "cursor-not-allowed" : "cursor-pointer"}`}
        viewBox="0 0 300 178"
        onPointerDown={(event) => {
          updateFromPointer(event);
          event.currentTarget.setPointerCapture(event.pointerId);
        }}
        onPointerMove={(event) => {
          if (event.buttons !== 1) return;
          updateFromPointer(event);
        }}
      >
        <text x="105" y="150" className="fill-slate-400 text-xs font-bold">
          10°
        </text>
        <text x="100" y="94" className="fill-slate-400 text-xs font-bold">
          45°
        </text>
        <text x="105" y="38" className="fill-slate-400 text-xs font-bold">
          80°
        </text>

        <line
          x1="150"
          y1="145"
          x2="150"
          y2="35"
          stroke="#e2e8f0"
          strokeWidth="10"
          strokeLinecap="round"
        />

        <line
          x1="150"
          y1="145"
          x2="150"
          y2={y}
          stroke="#2563eb"
          strokeWidth="10"
          strokeLinecap="round"
        />

        <circle cx="150" cy={y} r="14" fill="#dbeafe" />
        <circle cx="150" cy={y} r="5" fill="#2563eb" />

        <text
          x="150"
          y="166"
          textAnchor="middle"
          className="fill-slate-500 text-xs font-bold"
        >
          Trục dọc
        </text>
      </svg>
    </section>
  );
}

function HorizontalAxisControl({
  value,
  disabled,
  busy,
  onChange,
}: {
  value: number;
  disabled: boolean;
  busy: boolean;
  onChange: (value: number) => void;
}) {
  const visualValue = clamp(value, SUN_SERVO_HORIZONTAL_MIN, SUN_SERVO_HORIZONTAL_MAX);

  const center = { x: 150, y: 126 };
  const radius = 66;
  const visualAngle = visualValue;
  const dot = polarToCartesian(center.x, center.y, radius, visualAngle);
  const fullArc = describeArc(center.x, center.y, radius, SUN_SERVO_HORIZONTAL_MAX, SUN_SERVO_HORIZONTAL_MIN, 1);
  const activeArc = describeArc(center.x, center.y, radius, SUN_SERVO_HORIZONTAL_MAX, visualAngle, 1);

  const updateFromPointer = (event: React.PointerEvent<SVGSVGElement>) => {
    if (disabled) return;

    const rect = event.currentTarget.getBoundingClientRect();
    const x = ((event.clientX - rect.left) / rect.width) * 300;
    const y = ((event.clientY - rect.top) / rect.height) * 178;

    const dx = x - center.x;
    const dy = center.y - y;

    let angle = (Math.atan2(dy, dx) * 180) / Math.PI;
    angle = clamp(angle, SUN_SERVO_HORIZONTAL_MIN, SUN_SERVO_HORIZONTAL_MAX);

    const next = Math.round(angle);

    onChange(clampServoHorizontal(next));
  };

  return (
    <section
      className={`rounded-[22px] border p-5 transition ${
        disabled
          ? "bg-slate-50 border-slate-200 opacity-60"
          : "bg-white border-slate-200 shadow-sm"
      }`}
    >
      <div className="flex items-start justify-between gap-4">
        <div>
          <h3 className="m-0 text-slate-900 text-[17px] font-black">
            Trục ngang
          </h3>
          <p className="mt-1 mb-0 text-slate-500 text-sm font-medium">
            Điều chỉnh trái / phải
          </p>
        </div>

        <div className="flex items-center gap-1 text-slate-900 font-black">
          {busy ? (
            <Loader2 className="w-4 h-4 animate-spin text-blue-600" />
          ) : (
            <input
              type="text"
              value={visualValue}
              disabled={disabled}
              onChange={(event) => onChange(clampServoHorizontal(Number(event.target.value)))}
              className="w-[54px] h-9 rounded-xl border border-slate-200 bg-slate-50 text-center text-slate-900 text-lg font-black outline-none focus:border-blue-400 disabled:cursor-not-allowed"
            />
          )}
          <span>°</span>
        </div>
      </div>

      <svg
        className={`mt-4 w-full h-[178px] ${disabled ? "cursor-not-allowed" : "cursor-pointer"}`}
        viewBox="0 0 300 178"
        onPointerDown={(event) => {
          updateFromPointer(event);
          event.currentTarget.setPointerCapture(event.pointerId);
        }}
        onPointerMove={(event) => {
          if (event.buttons !== 1) return;
          updateFromPointer(event);
        }}
      >
        <text x="38" y="131" className="fill-slate-400 text-xs font-bold">
          170°
        </text>
        <text x="145" y="46" className="fill-slate-400 text-xs font-bold">
          90°
        </text>
        <text x="252" y="131" className="fill-slate-400 text-xs font-bold">
          10°
        </text>

        <path
          d={fullArc}
          fill="none"
          stroke="#e2e8f0"
          strokeWidth="10"
          strokeLinecap="round"
        />

        <path
          d={activeArc}
          fill="none"
          stroke="#2563eb"
          strokeWidth="10"
          strokeLinecap="round"
        />

        <circle cx={center.x} cy={center.y} r="14" fill="#e0e7ff" />
        <circle cx={center.x} cy={center.y} r="5" fill="#4f46e5" />

        <circle cx={dot.x} cy={dot.y} r="14" fill="#dbeafe" />
        <circle cx={dot.x} cy={dot.y} r="5" fill="#2563eb" />

        <text
          x="150"
          y="162"
          textAnchor="middle"
          className="fill-slate-500 text-xs font-bold"
        >
          Trục ngang
        </text>
      </svg>
    </section>
  );
}

export function SunTrackerPage() {
  const { sunTracker, sunChartHistory, sendSunMode, sendSunServo } = useRealtime();
  const [busy, setBusy] = useState<"mode" | "vertical" | "horizontal" | null>(null);

  const isAuto = sunTracker.mode === "sun_auto";
  const canManualControl = !isAuto;

  const chartData = useMemo(() => {
    const source = sunChartHistory.length > 0 ? sunChartHistory : [sunTracker];

    return source.map((item, index) => ({
      name: formatTime(item.updated_at, index),
      lt: Math.round(item.ldr_lt),
      rt: Math.round(item.ldr_rt),
      ld: Math.round(item.ldr_ld),
      rd: Math.round(item.ldr_rd),
    }));
  }, [sunChartHistory, sunTracker]);

  const setMode = (mode: SunTrackerMode) => {
    setBusy("mode");
    sendSunMode(mode);
    window.setTimeout(() => setBusy(null), 350);
  };

  const setServo = (servo: "vertical" | "horizontal", value: number) => {
    const safeAngle = servo === "vertical" ? clampServoVertical(value) : clampServoHorizontal(value);

    setBusy(servo);
    sendSunServo(servo, safeAngle);
    window.setTimeout(() => setBusy(null), 250);
  };

  return (
    <div className="h-[calc(100vh-116px)] min-h-[720px] overflow-hidden">
      <div className="h-full grid grid-cols-1 xl:grid-cols-[minmax(0,1fr)_390px] gap-4">
        <section className="min-h-0 grid grid-rows-[auto_minmax(0,1fr)] gap-4">
          <section className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <SensorCard
              tag="LDR 1"
              label="Top Left Sensor"
              value={sunTracker.ldr_lt}
              theme="orange"
            />

            <SensorCard
              tag="LDR 2"
              label="Top Right Sensor"
              value={sunTracker.ldr_rt}
              theme="blue"
            />

            <SensorCard
              tag="LDR 3"
              label="Bottom Left Sensor"
              value={sunTracker.ldr_ld}
              theme="green"
            />

            <SensorCard
              tag="LDR 4"
              label="Bottom Right Sensor"
              value={sunTracker.ldr_rd}
              theme="red"
            />
          </section>

          <article className="min-h-0 rounded-[24px] bg-white border border-slate-200 shadow-sm p-5 flex flex-col">
            <div className="flex items-center gap-3 mb-4">
              <div className="w-11 h-11 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center">
                <Activity className="w-5 h-5" />
              </div>

              <div>
                <h3 className="m-0 text-slate-900 text-[18px] font-black">
                  Biểu đồ ánh sáng
                </h3>
                <p className="m-0 text-slate-500 text-sm font-semibold">
                  4 cảm biến LDR
                </p>
              </div>
            </div>

            <div className="min-h-0 flex-1 rounded-[20px] border border-slate-100 bg-slate-50/70 p-4">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={chartData} margin={{ left: 0, right: 12, top: 12, bottom: 0 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
                  <XAxis dataKey="name" tick={{ fontSize: 11, fill: "#64748b" }} />
                  <YAxis tick={{ fontSize: 11, fill: "#64748b" }} />
                  <Tooltip />
                  <Line
                    type="monotone"
                    dataKey="lt"
                    name="Top Left"
                    stroke="#f97316"
                    strokeWidth={3}
                    dot={false}
                  />
                  <Line
                    type="monotone"
                    dataKey="rt"
                    name="Top Right"
                    stroke="#2563eb"
                    strokeWidth={3}
                    dot={false}
                  />
                  <Line
                    type="monotone"
                    dataKey="ld"
                    name="Bottom Left"
                    stroke="#059669"
                    strokeWidth={3}
                    dot={false}
                  />
                  <Line
                    type="monotone"
                    dataKey="rd"
                    name="Bottom Right"
                    stroke="#ef4444"
                    strokeWidth={3}
                    dot={false}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </article>
        </section>

        <aside className="rounded-[24px] bg-white border border-slate-200 shadow-sm p-5 min-h-0 overflow-y-auto">
          <div className="flex items-center justify-between gap-4 mb-5">
            <h2 className="m-0 text-slate-900 text-[22px] font-black tracking-[-0.03em]">
              Điều khiển thiết bị
            </h2>

            <div className="flex items-center gap-3">
              <span className="text-slate-900 text-sm font-black">
                {isAuto ? "AUTO" : "MANUAL"}
              </span>

              <button
                type="button"
                disabled={busy === "mode"}
                onClick={() => setMode(isAuto ? "sun_manual" : "sun_auto")}
                className={`relative w-[58px] h-[32px] rounded-full transition border disabled:opacity-60 ${
                  isAuto
                    ? "bg-blue-600 border-blue-600"
                    : "bg-slate-200 border-slate-300"
                }`}
              >
                <span
                  className={`absolute top-[4px] w-[24px] h-[24px] rounded-full bg-white shadow transition ${
                    isAuto ? "left-[28px]" : "left-[4px]"
                  }`}
                />
              </button>
            </div>
          </div>

          <div className="space-y-4">
            <div className="flex items-center gap-2 text-slate-500 text-xs font-bold">
              <MoveVertical className="w-4 h-4" />
              <span>Điều khiển dọc</span>
            </div>

            <VerticalAxisControl
              value={sunTracker.servo_vertical}
              disabled={!canManualControl}
              busy={busy === "vertical"}
              onChange={(value) => setServo("vertical", value)}
            />

            <div className="flex items-center gap-2 text-slate-500 text-xs font-bold pt-1">
              <MoveHorizontal className="w-4 h-4" />
              <span>Điều khiển ngang</span>
            </div>

            <HorizontalAxisControl
              value={sunTracker.servo_horizontal}
              disabled={!canManualControl}
              busy={busy === "horizontal"}
              onChange={(value) => setServo("horizontal", value)}
            />


          </div>
        </aside>
      </div>
    </div>
  );
}