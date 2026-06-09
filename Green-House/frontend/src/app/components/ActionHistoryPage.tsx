import { useEffect, useState } from "react";
import {
  ChevronLeft,
  ChevronRight,
  Database,
  Clock3,
  Cpu,
  TerminalSquare,
  CheckCircle2,
  XCircle,
  Clock,
  Timer,
  Bot,
  User,
} from "lucide-react";
import { apiClient } from "../api/client";

interface DeviceCommand {
  id: number;
  device_code: string;
  command: string;
  value: string;
  payload: any;
  status: string;
  created_at: string;
  acked_at: string | null;
}

interface ActionHistoryResponse {
  items: DeviceCommand[];
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
}

function getStatusInfo(status: string) {
  switch (status) {
    case "ack":
      return { label: "Thành công", color: "text-green-600", bg: "bg-green-50", icon: CheckCircle2 };
    case "failed":
      return { label: "Thất bại", color: "text-red-600", bg: "bg-red-50", icon: XCircle };
    case "pending":
    default:
      return { label: "Đang chờ", color: "text-amber-600", bg: "bg-amber-50", icon: Clock };
  }
}

function formatDeviceName(code: string) {
  const mapping: Record<string, string> = {
    pump: "Máy bơm",
    fan: "Quạt thông gió",
    mist: "Máy phun sương",
    light: "Đèn chiếu sáng",
    "esp32-main": "ESP32 Main",
  };
  return mapping[code] || code;
}

function formatCommand(command: string, value: string) {
  if (command === "set_power") {
    return value === "on" ? "Bật thiết bị" : "Tắt thiết bị";
  }
  return `${command} ${value ? `(${value})` : ""}`;
}

function formatDuration(payload: any) {
  if (!payload || typeof payload !== 'object' || !payload.duration) return "Không hẹn giờ";
  const sec = payload.duration;
  if (sec < 60) return `${sec} giây`;
  return `${Math.round(sec / 60)} phút`;
}

function getCommandSource(row: DeviceCommand) {
  if (row.payload && row.payload.source === 'mpc') {
    return { label: "Hệ thống MPC", icon: Bot, color: "text-purple-700", bg: "bg-purple-50", border: "border-purple-200" };
  }
  return { label: "Người dùng", icon: User, color: "text-blue-700", bg: "bg-blue-50", border: "border-blue-200" };
}

export function ActionHistoryPage() {
  const [rows, setRows] = useState<DeviceCommand[]>([]);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(true);
  const [pageLoading, setPageLoading] = useState(false);
  const [error, setError] = useState("");

  const loadData = async (nextPage = page) => {
    const isFirstLoad = rows.length === 0 && nextPage === 1;

    try {
      setError("");

      if (isFirstLoad) {
        setLoading(true);
      } else {
        setPageLoading(true);
      }

      const res = await apiClient.get<ActionHistoryResponse>(
        `/device-commands/history/?page=${nextPage}&page_size=${pageSize}`
      );

      const data = res.data;
      setRows(data.items ?? []);
      setPage(data.page ?? 1);
      setTotalPages(Math.max(data.total_pages ?? 1, 1));
    } catch {
      setError("Không tải được lịch sử thao tác.");
      if (isFirstLoad) {
        setRows([]);
        setTotalPages(1);
      }
    } finally {
      setLoading(false);
      setPageLoading(false);
    }
  };

  useEffect(() => {
    void loadData(page);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page]);

  const handlePrev = () => {
    if (page > 1 && !pageLoading) {
      setPage((prev) => prev - 1);
    }
  };

  const handleNext = () => {
    if (page < totalPages && !pageLoading) {
      setPage((prev) => prev + 1);
    }
  };

  return (
    <div className="space-y-5">
      <div className="elevated-card rounded-3xl overflow-hidden">
        <div className="px-5 py-4 border-b border-slate-200">
          <h4 className="text-slate-900" style={{ fontSize: "15px", fontWeight: 700 }}>
            Lịch sử điều khiển thiết bị
          </h4>
        </div>

        {loading ? (
          <div className="p-10 text-center text-slate-400" style={{ fontSize: "13px" }}>
            Đang tải lịch sử thao tác...
          </div>
        ) : error ? (
          <div
            className="p-10 text-center text-red-500"
            style={{ fontSize: "13px", fontWeight: 600 }}
          >
            {error}
          </div>
        ) : rows.length === 0 ? (
          <div className="p-10 text-center">
            <div className="w-16 h-16 bg-slate-50 rounded-2xl flex items-center justify-center mx-auto mb-3 border border-slate-200">
              <Database className="w-7 h-7 text-slate-400" />
            </div>
            <p className="text-slate-700" style={{ fontSize: "15px", fontWeight: 700 }}>
              Chưa có lịch sử thao tác
            </p>
            <p className="text-slate-500 mt-1" style={{ fontSize: "13px" }}>
              Các lệnh điều khiển thiết bị sẽ được lưu tại đây
            </p>
          </div>
        ) : (
          <div
            className={`overflow-x-auto transition-opacity duration-200 ${
              pageLoading ? "opacity-60" : "opacity-100"
            }`}
          >
            <table className="w-full min-w-[760px]">
              <thead>
                <tr className="bg-gradient-to-r from-blue-50 to-blue-100 border-b border-slate-200">
                  <th
                    className="text-left px-5 py-4 text-slate-700"
                    style={{ fontSize: "14px", fontWeight: 700 }}
                  >
                    <div className="flex items-center gap-2">
                      <Clock3 className="w-4 h-4 text-blue-600" />
                      Thời gian
                    </div>
                  </th>
                  <th
                    className="text-left px-5 py-4 text-slate-700"
                    style={{ fontSize: "14px", fontWeight: 700 }}
                  >
                    <div className="flex items-center gap-2">
                      <Cpu className="w-4 h-4 text-indigo-600" />
                      Thiết bị
                    </div>
                  </th>
                  <th
                    className="text-left px-5 py-4 text-slate-700"
                    style={{ fontSize: "14px", fontWeight: 700 }}
                  >
                    <div className="flex items-center gap-2">
                      <TerminalSquare className="w-4 h-4 text-purple-600" />
                      Lệnh điều khiển
                    </div>
                  </th>
                  <th
                    className="text-left px-5 py-4 text-slate-700"
                    style={{ fontSize: "14px", fontWeight: 700 }}
                  >
                    <div className="flex items-center gap-2">
                      <Bot className="w-4 h-4 text-pink-600" />
                      Nguồn
                    </div>
                  </th>
                  <th
                    className="text-left px-5 py-4 text-slate-700"
                    style={{ fontSize: "14px", fontWeight: 700 }}
                  >
                    <div className="flex items-center gap-2">
                      <Timer className="w-4 h-4 text-emerald-600" />
                      Hẹn giờ tự tắt
                    </div>
                  </th>
                </tr>
              </thead>

              <tbody>
                {rows.map((row, index) => {
                  const createdAt = new Date(row.created_at);
                  const statusInfo = getStatusInfo(row.status);
                  const StatusIcon = statusInfo.icon;

                  return (
                    <tr
                      key={row.id}
                      className={`border-b border-slate-100 hover:bg-blue-50/30 transition-colors ${
                        index % 2 === 0 ? "bg-white" : "bg-slate-50/50"
                      }`}
                    >
                      <td className="px-5 py-4">
                        <div>
                          <p
                            className="text-slate-800"
                            style={{ fontSize: "15px", fontWeight: 600 }}
                          >
                            {Number.isNaN(createdAt.getTime())
                              ? "--"
                              : createdAt.toLocaleDateString("vi-VN")}
                          </p>
                          <p className="text-slate-500" style={{ fontSize: "13px" }}>
                            {Number.isNaN(createdAt.getTime())
                              ? "--"
                              : createdAt.toLocaleTimeString("vi-VN", {
                                  hour: "2-digit",
                                  minute: "2-digit",
                                  second: "2-digit",
                                })}
                          </p>
                        </div>
                      </td>

                      <td className="px-5 py-4">
                        <span
                          className="font-semibold text-slate-700"
                          style={{ fontSize: "15px" }}
                        >
                          {formatDeviceName(row.device_code)}
                        </span>
                      </td>

                      <td className="px-5 py-4">
                        <span
                          className="text-slate-700 font-medium"
                          style={{ fontSize: "15px" }}
                        >
                          {formatCommand(row.command, row.value)}
                        </span>
                      </td>

                      <td className="px-5 py-4">
                        {(() => {
                          const src = getCommandSource(row);
                          const Icon = src.icon;
                          return (
                            <span
                              className={`inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-sm font-semibold border ${src.bg} ${src.color} ${src.border}`}
                            >
                              <Icon className="w-4 h-4" />
                              {src.label}
                            </span>
                          );
                        })()}
                      </td>

                      <td className="px-5 py-4">
                        <span
                          className={`inline-flex items-center px-2.5 py-1 rounded-md text-sm font-medium ${
                            row.payload && row.payload.duration ? "bg-emerald-50 text-emerald-700" : "bg-slate-100 text-slate-600"
                          }`}
                        >
                          {formatDuration(row.payload)}
                        </span>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        <div className="px-5 py-4 border-t border-slate-200 flex items-center justify-between">
          <button
            onClick={handlePrev}
            disabled={page <= 1 || pageLoading}
            className="px-3 py-2 rounded-xl border border-slate-200 bg-white text-slate-700 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-slate-50 flex items-center gap-2"
            style={{ fontSize: "13px", fontWeight: 600 }}
          >
            <ChevronLeft className="w-4 h-4" />
            Trước
          </button>

          <div className="text-slate-600" style={{ fontSize: "13px", fontWeight: 600 }}>
            Trang {page} / {totalPages}
          </div>

          <button
            onClick={handleNext}
            disabled={page >= totalPages || pageLoading}
            className="px-3 py-2 rounded-xl border border-slate-200 bg-white text-slate-700 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-slate-50 flex items-center gap-2"
            style={{ fontSize: "13px", fontWeight: 600 }}
          >
            Sau
            <ChevronRight className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
