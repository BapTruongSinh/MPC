import { useState, FormEvent, useEffect } from "react";
import { useAuth } from "../contexts/AuthContext";
import { Leaf, AlertCircle, ShieldCheck } from "lucide-react";
import { authSetup, authSetupStatus } from "../api/endpoints";

export function LoginPage() {
  const { login } = useAuth();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [setupMode, setSetupMode] = useState(false);
  const [checkingSetup, setCheckingSetup] = useState(true);

  useEffect(() => {
    authSetupStatus()
      .then((res) => {
        setSetupMode(res.data.setup_required);
      })
      .catch((err) => console.error("Error checking setup status:", err))
      .finally(() => setCheckingSetup(false));
  }, []);

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError("");
    setLoading(true);
    try {
      if (setupMode) {
        await authSetup(username, password);
        await login(username, password); // Auto login after setup
      } else {
        await login(username, password);
      }
    } catch (err: any) {
      if (setupMode) {
        setError(err.response?.data?.detail || "Không thể khởi tạo tài khoản.");
      } else {
        setError("Tên đăng nhập hoặc mật khẩu không đúng.");
      }
    } finally {
      setLoading(false);
    }
  };

  if (checkingSetup) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="flex items-center gap-2 text-slate-500 font-medium">
          <Leaf className="w-5 h-5 animate-pulse" /> Đang khởi tạo...
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex items-center justify-center relative overflow-hidden">
      <div className="pointer-events-none absolute top-20 right-[15%] h-72 w-72 rounded-full bg-blue-100 blur-3xl opacity-60" />
      <div className="pointer-events-none absolute bottom-20 left-[10%] h-64 w-64 rounded-full bg-slate-200 blur-3xl opacity-60" />

      <div className="elevated-card rounded-3xl p-10 w-full max-w-sm relative z-10">
        <div className="flex flex-col items-center mb-8 text-center">
          <div className={`w-14 h-14 rounded-2xl flex items-center justify-center mb-4 shadow-lg ${setupMode ? "bg-emerald-500" : "gradient-action"}`}>
            {setupMode ? <ShieldCheck className="w-7 h-7 text-white" /> : <Leaf className="w-7 h-7 text-white" />}
          </div>
          <h1 className="text-slate-900" style={{ fontSize: "22px", fontWeight: 800 }}>
            {setupMode ? "Thiết lập ban đầu" : "Smart Greenhouse"}
          </h1>
          <p className="text-slate-500 mt-1" style={{ fontSize: "13px" }}>
            {setupMode ? "Hệ thống chưa có tài khoản, vui lòng tạo tài khoản Admin đầu tiên." : "Đăng nhập để quản lý nhà kính"}
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-slate-700 mb-1.5" style={{ fontSize: "13px", fontWeight: 600 }}>
              Tên đăng nhập
            </label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
              autoFocus
              className="w-full px-4 py-2.5 rounded-xl border border-slate-200 bg-slate-50 text-slate-900 outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100 transition-all"
              style={{ fontSize: "14px" }}
              placeholder="admin"
            />
          </div>

          <div>
            <label className="block text-slate-700 mb-1.5" style={{ fontSize: "13px", fontWeight: 600 }}>
              Mật khẩu
            </label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="w-full px-4 py-2.5 rounded-xl border border-slate-200 bg-slate-50 text-slate-900 outline-none focus:border-blue-400 focus:ring-2 focus:ring-blue-100 transition-all"
              style={{ fontSize: "14px" }}
              placeholder="••••••••"
            />
          </div>

          {error && (
            <div className="flex items-center gap-2 px-3 py-2.5 bg-red-50 border border-red-100 rounded-xl">
              <AlertCircle className="w-4 h-4 text-red-500 flex-shrink-0" />
              <p className="text-red-600" style={{ fontSize: "13px" }}>{error}</p>
            </div>
          )}

          <button
            type="submit"
            disabled={loading}
            className={`w-full py-2.5 text-white rounded-xl transition-all duration-300 hover:-translate-y-0.5 disabled:opacity-60 disabled:translate-y-0 mt-2 ${setupMode ? "bg-emerald-500 hover:bg-emerald-600 shadow-emerald-200 shadow-lg" : "gradient-action"}`}
            style={{ fontSize: "14px", fontWeight: 700 }}
          >
            {loading ? "Đang xử lý..." : setupMode ? "Khởi tạo Admin" : "Đăng nhập"}
          </button>
        </form>
      </div>
    </div>
  );
}
