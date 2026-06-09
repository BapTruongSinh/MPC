import { createContext, useContext, useEffect, useMemo, useRef, useState } from "react";
import { toast } from "sonner";
import type {
  AlertItem,
  ControlState,
  DeviceItem,
  GreenhouseMessage,
  GreenhouseStatePacket,
  SensorErrors,
  SensorReading,
  SunTrackerMode,
  SunTrackerState,
} from "../lib/greenhouse.types";

export type DashboardOverview = {
  latest: SensorReading | null;
  control: ControlState;
  device_count: number;
  online_devices: number;
  unread_alerts: number;
  uptime_hint: string;
  recent_alerts: AlertItem[];
  esp32_online: boolean;
};

type RealtimeContextType = {
  overview: DashboardOverview | null;
  latest: SensorReading | null;
  devices: DeviceItem[];
  alerts: AlertItem[];
  chartHistory: SensorReading[];
  sensorErrors: SensorErrors;
  connected: boolean;
  lastUpdated: Date | null;
  sunTracker: SunTrackerState;
  sunChartHistory: SunTrackerState[];
  sendMode: (mode: "AUTO" | "MANUAL") => void;
  sendDeviceControl: (device: "fan" | "pump" | "light" | "mist", state: "ON" | "OFF", durationSeconds?: number) => void;
  sendSunMode: (mode: SunTrackerMode) => void;
  sendSunServo: (servo: "vertical" | "horizontal", angle: number) => void;
  markAlertRead: (id: number) => void;
  markAllAlertsRead: () => void;
};

const RealtimeContext = createContext<RealtimeContextType | null>(null);

const WS_URL =
  (import.meta as any).env?.VITE_WS_URL ||
  `${window.location.protocol === "https:" ? "wss" : "ws"}://${window.location.hostname}:8000/ws/frontend/`;

const MAX_CHART_POINTS = 20;
const RECONNECT_DELAY = 1500;
const MAX_SUN_CHART_POINTS = 20;

function formatUptime(updatedAt?: string | null) {
  if (!updatedAt) return "—";
  const diff = Date.now() - new Date(updatedAt).getTime();
  const mins = Math.max(0, Math.floor(diff / 60000));
  if (mins < 1) return "vừa xong";
  if (mins < 60) return `${mins} phút`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs} giờ`;
  return `${Math.floor(hrs / 24)} ngày`;
}

const defaultSensorErrors: SensorErrors = {
  dht: false,
  soil: false,
  light: false,
  gas: false,
};

const defaultSunTracker: SunTrackerState = {
  mode: "sun_manual",
  ldr_lt: 0,
  ldr_rt: 0,
  ldr_ld: 0,
  ldr_rd: 0,
  servo_vertical: 90,
  servo_horizontal: 90,
  updated_at: null,
};

function normalizeSunTracker(value: Partial<SunTrackerState> | null | undefined): SunTrackerState {
  return {
    ...defaultSunTracker,
    ...(value ?? {}),
    mode: value?.mode === "sun_auto" ? "sun_auto" : "sun_manual",
    ldr_lt: Number(value?.ldr_lt ?? 0),
    ldr_rt: Number(value?.ldr_rt ?? 0),
    ldr_ld: Number(value?.ldr_ld ?? 0),
    ldr_rd: Number(value?.ldr_rd ?? 0),
    servo_vertical: Number(value?.servo_vertical ?? 90),
    servo_horizontal: Number(value?.servo_horizontal ?? 90),
    updated_at: value?.updated_at ?? null,
  };
}

function appendSunReading(prev: SunTrackerState[], reading: SunTrackerState) {
  const last = prev[prev.length - 1];
  if (last && last.updated_at === reading.updated_at) return prev;
  return [...prev, reading].slice(-MAX_SUN_CHART_POINTS);
}

function makePlaceholderReading(index: number): SensorReading {
  return {
    id: -(index + 1),
    temperature: 0,
    humidity: 0,
    light: 0,
    soil_moisture: 0,
    gas: 0,
    recorded_at: `0-${index + 1}`,
  };
}

function buildInitialChartHistory() {
  return Array.from({ length: MAX_CHART_POINTS }, (_, index) =>
    makePlaceholderReading(index)
  );
}

function isSameReading(a: SensorReading, b: SensorReading) {
  if (a.id != null && b.id != null) {
    return a.id === b.id;
  }
  return a.recorded_at === b.recorded_at;
}

function appendReading(prev: SensorReading[], reading: SensorReading | null) {
  if (!reading) return prev;

  if (prev.length > 0 && isSameReading(prev[prev.length - 1], reading)) {
    return prev;
  }

  return [...prev, reading].slice(-MAX_CHART_POINTS);
}

function websocketUrlWithToken() {
  const token = localStorage.getItem("access_token");
  if (!token) return WS_URL;

  const url = new URL(WS_URL);
  url.searchParams.set("token", token);
  return url.toString();
}

export function RealtimeProvider({ children }: { children: React.ReactNode }) {
  const socketRef = useRef<WebSocket | null>(null);

  const [overview, setOverview] = useState<DashboardOverview | null>(null);
  const [latest, setLatest] = useState<SensorReading | null>(null);
  const [devices, setDevices] = useState<DeviceItem[]>([]);
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [chartHistory, setChartHistory] = useState<SensorReading[]>(() =>
    buildInitialChartHistory()
  );
  const [sensorErrors, setSensorErrors] = useState<SensorErrors>(defaultSensorErrors);
  const [connected, setConnected] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [sunTracker, setSunTracker] = useState<SunTrackerState>(defaultSunTracker);
  const [sunChartHistory, setSunChartHistory] = useState<SunTrackerState[]>([]);

  const rebuildOverview = (
    nextLatest: SensorReading | null,
    nextDevices: DeviceItem[],
    nextAlerts: AlertItem[],
    nextControl: ControlState,
    updatedAt: string | null,
    esp32Online: boolean,
  ) => {
    setOverview({
      latest: nextLatest,
      control: nextControl,
      device_count: nextDevices.filter((d) => d.device_type !== "controller").length,
      online_devices: nextDevices.filter(
        (d) => d.device_type !== "controller" && d.status === "online"
      ).length,
      unread_alerts: nextAlerts.filter((a) => !a.is_read).length,
      uptime_hint: formatUptime(updatedAt),
      recent_alerts: nextAlerts.slice(0, 5),
      esp32_online: esp32Online,
    });
  };

  const applyStatePacket = (payload: GreenhouseStatePacket) => {
    const nextLatest = payload.latest ?? null;
    const nextDevices = payload.devices ?? [];
    const nextAlerts = payload.alerts ?? [];
    const nextControl = payload.control;
    const nextSensorErrors = payload.sensor_errors ?? defaultSensorErrors;
    const nextSunTracker = normalizeSunTracker(payload.sun_tracker);

    setLatest(nextLatest);
    setDevices(nextDevices);
    
    setAlerts((prevAlerts) => {
      if (prevAlerts.length > 0) {
        const prevIds = new Set(prevAlerts.map((a) => a.id));
        const newAlerts = nextAlerts.filter((a) => !prevIds.has(a.id) && !a.is_read);
        newAlerts.forEach((alert) => {
          if (alert.level === "error") {
            toast.error(alert.title, { description: alert.message });
          } else if (alert.level === "warning") {
            toast.warning(alert.title, { description: alert.message });
          } else if (alert.level === "success") {
            toast.success(alert.title, { description: alert.message });
          } else {
            toast.info(alert.title, { description: alert.message });
          }
        });
      }
      return nextAlerts;
    });

    setSensorErrors(nextSensorErrors);
    setSunTracker(nextSunTracker);
    setChartHistory((prev) => appendReading(prev, nextLatest));
    setSunChartHistory((prev) => appendSunReading(prev, nextSunTracker));

    rebuildOverview(
      nextLatest,
      nextDevices,
      nextAlerts,
      nextControl,
      payload.updated_at,
      !!payload.esp32_online,
    );

    setLastUpdated(new Date());
  };

  useEffect(() => {
    let ws: WebSocket | null = null;
    let reconnectTimer: number | null = null;
    let manuallyClosed = false;

    const connect = () => {
      if (
        ws &&
        (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)
      ) {
        return;
      }

      ws = new WebSocket(websocketUrlWithToken());
      socketRef.current = ws;

      ws.onopen = () => {
        setConnected(true);
      };

      ws.onclose = (event) => {
        setConnected(false);
        socketRef.current = null;
        ws = null;

        if (event.code === 4003) {
          localStorage.removeItem("access_token");
          localStorage.removeItem("refresh_token");
          window.location.href = "/";
          return;
        }

        if (!manuallyClosed) {
          if (reconnectTimer) {
            window.clearTimeout(reconnectTimer);
          }

          reconnectTimer = window.setTimeout(() => {
            connect();
          }, RECONNECT_DELAY);
        }
      };

      ws.onerror = () => {
        setConnected(false);
      };

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data) as GreenhouseMessage;
          console.log("Message:", msg);

          if (msg.type === "bootstrap" || msg.type === "state") {
            applyStatePacket(msg.data);
          }
        } catch {
          // ignore invalid message
        }
      };
    };

    connect();

    return () => {
      manuallyClosed = true;

      if (reconnectTimer) {
        window.clearTimeout(reconnectTimer);
        reconnectTimer = null;
      }

      if (ws) {
        ws.onopen = null;
        ws.onclose = null;
        ws.onerror = null;
        ws.onmessage = null;
        ws.close();
      }

      socketRef.current = null;
      ws = null;
    };
  }, []);

  const sendRaw = (payload: unknown) => {
    const ws = socketRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) return false;
    ws.send(JSON.stringify(payload));
    return true;
  };

  const value = useMemo<RealtimeContextType>(
    () => ({
      overview,
      latest,
      devices,
      alerts,
      chartHistory,
      sensorErrors,
      connected,
      lastUpdated,
      sunTracker,
      sunChartHistory,
      sendMode: (mode) => {
        sendRaw({ type: "mode", value: mode });
      },
      sendDeviceControl: (device, state, duration) => {
        sendRaw({ type: "device_control", device, state, duration });
      },
      sendSunMode: (mode) => {
        setSunTracker((prev) => ({ ...prev, mode }));
        sendRaw({ type: "sun_mode", mode });
      },
      sendSunServo: (servo, angle) => {
        const safeAngle = Math.max(0, Math.min(180, Math.round(angle)));
        setSunTracker((prev) => ({
          ...prev,
          [servo === "vertical" ? "servo_vertical" : "servo_horizontal"]: safeAngle,
        }));
        sendRaw({ type: "sun_servo_control", servo, angle: safeAngle });
      },
      markAlertRead: (id) => {
        setAlerts((prev) => {
          const nextAlerts = prev.map((a) => (a.id === id ? { ...a, is_read: true } : a));
          setOverview((prevOverview) =>
            prevOverview
              ? {
                  ...prevOverview,
                  unread_alerts: nextAlerts.filter((a) => !a.is_read).length,
                  recent_alerts: nextAlerts.slice(0, 5),
                }
              : prevOverview
          );
          return nextAlerts;
        });

        sendRaw({ type: "alert_mark_read", id });
      },
      markAllAlertsRead: () => {
        setAlerts((prev) => {
          const nextAlerts = prev.map((a) => ({ ...a, is_read: true }));
          setOverview((prevOverview) =>
            prevOverview
              ? {
                  ...prevOverview,
                  unread_alerts: 0,
                  recent_alerts: nextAlerts.slice(0, 5),
                }
              : prevOverview
          );
          return nextAlerts;
        });

        sendRaw({ type: "alert_mark_all_read" });
      },
    }),
    [overview, latest, devices, alerts, chartHistory, sensorErrors, connected, lastUpdated, sunTracker, sunChartHistory]
  );

  return <RealtimeContext.Provider value={value}>{children}</RealtimeContext.Provider>;
}

export function useRealtime() {
  const context = useContext(RealtimeContext);
  if (!context) {
    throw new Error("useRealtime must be used within RealtimeProvider");
  }
  return context;
}