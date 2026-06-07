import {
  LayoutDashboard,
  Thermometer,
  Cpu,
  Settings,
  BarChart3,
  Bell,
  HelpCircle,
  ChevronRight,
  History,
  TrendingUp,
  Sun,
  ListOrdered,
} from "lucide-react";

interface SidebarProps {
  activeMenu: string;
  setActiveMenu: (menu: string) => void;
  open: boolean;
}

const menuItems = [
  { id: "dashboard", label: "Tổng quan", icon: LayoutDashboard, badge: null },
  { id: "sensors", label: "Cảm biến", icon: Thermometer, badge: null },
  { id: "history", label: "Lịch sử cảm biến", icon: History, badge: null },
  { id: "forecast", label: "Dự báo", icon: TrendingUp, badge: null },
  { id: "suntracker", label: "SunTracker", icon: Sun, badge: null },
  { id: "action-history", label: "Lịch sử thao tác", icon: ListOrdered, badge: null },
  { id: "alerts", label: "Cảnh báo", icon: Bell, badge: null },
  { id: "settings", label: "Cài đặt", icon: Settings, badge: null },
];

const bottomMenu = [{ id: "help", label: "Trợ giúp", icon: HelpCircle }];

export function Sidebar({ activeMenu, setActiveMenu, open }: SidebarProps) {
  return (
    <>
      {open && (
        <div
          className="fixed inset-0 bg-slate-900/20 z-20 lg:hidden"
          onClick={() => {}}
        />
      )}

      <aside
        className={`
          fixed top-0 lg:top-0 left-0 h-full z-40 w-64 bg-white border-r border-slate-200
          flex flex-col transition-transform duration-300
          ${open ? "translate-x-0" : "-translate-x-full lg:translate-x-0"}
        `}
      >
        <div className="h-16 flex items-center px-5 border-b border-slate-200">
          <div>
            <p className="text-slate-900" style={{ fontSize: "14px", fontWeight: 700 }}>
              Greenhouse
            </p>
            <p className="text-slate-500" style={{ fontSize: "11px" }}>
              Operations workspace
            </p>
          </div>
        </div>

        <nav className="flex-1 px-3 pb-4 overflow-y-auto">
          <p
            className="text-slate-400 px-3 mb-2"
            style={{
              fontSize: "10px",
              fontWeight: 600,
              textTransform: "uppercase",
              letterSpacing: "0.08em",
            }}
          >
            Navigation
          </p>

          <ul className="space-y-1">
            {menuItems.map((item) => {
              const Icon = item.icon;
              const isActive = activeMenu === item.id;

              return (
                <li key={item.id}>
                  <button
                    onClick={() => setActiveMenu(item.id)}
                    className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl border transition-all duration-200 group ${
                      isActive
                        ? "bg-blue-50 text-blue-700 border-blue-100"
                        : "text-slate-600 border-transparent hover:bg-slate-50 hover:border-slate-200"
                    }`}
                  >
                    <div
                      className={`w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0 ${
                        isActive ? "bg-blue-100" : "bg-slate-100 group-hover:bg-white"
                      }`}
                    >
                      <Icon className="w-4 h-4" />
                    </div>

                    <span style={{ fontSize: "13px", fontWeight: isActive ? 600 : 500 }}>
                      {item.label}
                    </span>

                    <div className="ml-auto flex items-center gap-1">
                      {isActive && <ChevronRight className="w-3.5 h-3.5 text-blue-500" />}
                    </div>
                  </button>
                </li>
              );
            })}
          </ul>
        </nav>

        <div className="p-4 border-t border-slate-200">
          <div className="flex items-center gap-3 p-3 rounded-2xl bg-slate-50 border border-slate-200">
            <div className="w-8 h-8 bg-slate-900 rounded-full flex items-center justify-center flex-shrink-0">
              <span className="text-white" style={{ fontSize: "11px", fontWeight: 700 }}>
                A
              </span>
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-slate-900 truncate" style={{ fontSize: "12px", fontWeight: 600 }}>
                Admin
              </p>
            </div>
          </div>
        </div>
      </aside>
    </>
  );
}