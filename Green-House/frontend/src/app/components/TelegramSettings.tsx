import { useEffect, useRef, useState } from "react";
import {
  CheckCircle2,
  HelpCircle,
  Save,
  Send,
  XCircle,
} from "lucide-react";
import { getTelegramSettings, updateTelegramSettings } from "../api/endpoints";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Label } from "./ui/label";

function HelpTooltip({ content }: { content: React.ReactNode }) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  return (
    <div className="relative inline-flex" ref={ref}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="w-5 h-5 rounded-full bg-slate-100 hover:bg-blue-100 text-slate-400 hover:text-blue-600 flex items-center justify-center transition-colors"
        aria-label="Hướng dẫn"
      >
        <HelpCircle className="w-3.5 h-3.5" />
      </button>
      {open && (
        <div className="absolute left-0 bottom-full mb-2 z-50 w-80 rounded-2xl bg-white border border-slate-200 shadow-xl p-4 text-slate-600 text-xs leading-relaxed shadow-slate-200/50">
          <div className="font-bold text-slate-800 mb-2 flex items-center gap-1.5">
            📌 Hướng dẫn lấy mã
          </div>
          <div className="text-slate-600 text-[13px] leading-relaxed">
            {content}
          </div>
          <div className="absolute -bottom-2 left-2 w-4 h-4 bg-white border-r border-b border-slate-200 rotate-45" />
        </div>
      )}
    </div>
  );
}

export function TelegramSettings() {
  const [loading, setLoading] = useState(true);
  const [tokenConfigured, setTokenConfigured] = useState(false);
  const [chatIdConfigured, setChatIdConfigured] = useState(false);
  const [token, setToken] = useState("");
  const [chatId, setChatId] = useState("");
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    getTelegramSettings()
      .then((res) => {
        setTokenConfigured(res.data.token_configured);
        setChatIdConfigured(res.data.chat_id_configured);
        setChatId(res.data.chat_id || "");
      })
      .catch(() => {
        setError("Không tải được cấu hình Telegram.");
      })
      .finally(() => setLoading(false));
  }, []);

  const save = async () => {
    if (!token && !chatId) {
      setError("Vui lòng nhập Bot Token hoặc Chat ID.");
      return;
    }
    setSaving(true);
    setMessage("");
    setError("");
    try {
      const payload: Record<string, string> = {};
      if (token) payload.telegram_bot_token = token;
      if (chatId) payload.telegram_chat_id = chatId;
      await updateTelegramSettings(payload);
      if (token) setTokenConfigured(true);
      if (chatId) setChatIdConfigured(true);
      setToken("");
      setMessage("Đã lưu thành công! Hệ thống sẽ gửi tin nhắn Telegram khi có cảnh báo.");
    } catch {
      setError("Không lưu được cấu hình. Kiểm tra lại server.");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="elevated-card rounded-3xl p-5">
        <p className="text-slate-400 animate-pulse" style={{ fontSize: "13px" }}>
          Đang tải cấu hình Telegram...
        </p>
      </div>
    );
  }

  return (
    <div className="elevated-card rounded-3xl p-5 space-y-5">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-2xl bg-sky-50 border border-sky-100 flex items-center justify-center flex-shrink-0">
          <Send className="w-5 h-5 text-sky-500" />
        </div>
        <div>
          <p className="text-slate-800 font-extrabold" style={{ fontSize: "15px" }}>
            Thông báo qua Telegram
          </p>
          <p className="text-slate-500" style={{ fontSize: "12px" }}>
            Nhận cảnh báo khẩn cấp trực tiếp vào điện thoại qua tin nhắn Telegram.
          </p>
        </div>
      </div>

      {/* Status badges */}
      <div className="flex flex-wrap gap-2">
        <span
          className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full border font-semibold ${
            tokenConfigured
              ? "bg-emerald-50 text-emerald-700 border-emerald-100"
              : "bg-slate-50 text-slate-400 border-slate-200"
          }`}
          style={{ fontSize: "11px" }}
        >
          {tokenConfigured ? (
            <CheckCircle2 className="w-3.5 h-3.5" />
          ) : (
            <XCircle className="w-3.5 h-3.5" />
          )}
          Bot Token {tokenConfigured ? "đã cấu hình" : "chưa cấu hình"}
        </span>
        <span
          className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full border font-semibold ${
            chatIdConfigured
              ? "bg-emerald-50 text-emerald-700 border-emerald-100"
              : "bg-slate-50 text-slate-400 border-slate-200"
          }`}
          style={{ fontSize: "11px" }}
        >
          {chatIdConfigured ? (
            <CheckCircle2 className="w-3.5 h-3.5" />
          ) : (
            <XCircle className="w-3.5 h-3.5" />
          )}
          Chat ID {chatIdConfigured ? "đã cấu hình" : "chưa cấu hình"}
        </span>
      </div>

      {/* Form */}
      <div className="space-y-4">
        <div className="space-y-1.5">
          <div className="flex items-center gap-1.5">
            <Label className="text-slate-700 font-bold" style={{ fontSize: "12px" }}>
              Bot Token
            </Label>
            <HelpTooltip 
              content={
                <ul className="list-decimal pl-4 space-y-1.5 marker:text-slate-400">
                  <li>Mở ứng dụng Telegram, tìm kiếm <strong>@BotFather</strong>.</li>
                  <li>Gõ lệnh <strong>/newbot</strong> và làm theo hướng dẫn để đặt tên bot.</li>
                  <li>Sau khi tạo xong, BotFather sẽ cấp một đoạn mã Token (HTTP API). Copy và dán vào đây.</li>
                  <li className="text-slate-400 italic list-none -ml-4 mt-1">VD: 7123456789:AAG_xxx...</li>
                </ul>
              } 
            />
          </div>
          <Input
            id="telegram-bot-token"
            type="password"
            placeholder={tokenConfigured ? "••••••••••• (đã lưu, nhập lại để đổi)" : "Dán Bot Token vào đây"}
            value={token}
            onChange={(e) => setToken(e.target.value)}
            className="font-mono text-sm"
          />
        </div>

        <div className="space-y-1.5">
          <div className="flex items-center gap-1.5">
            <Label className="text-slate-700 font-bold" style={{ fontSize: "12px" }}>
              Chat ID
            </Label>
            <HelpTooltip 
              content={
                <ul className="list-decimal pl-4 space-y-1.5 marker:text-slate-400">
                  <li>Mở ứng dụng Telegram, tìm kiếm <strong>@userinfobot</strong>.</li>
                  <li>Bấm nút <strong>Start</strong> (hoặc gõ lệnh /start).</li>
                  <li>Bot sẽ trả về thông tin của bạn. Copy dãy số ở dòng <strong>Id</strong> và dán vào đây.</li>
                  <li className="text-slate-400 italic list-none -ml-4 mt-1">VD: 123456789</li>
                </ul>
              } 
            />
          </div>
          <Input
            id="telegram-chat-id"
            type="password"
            placeholder={chatIdConfigured ? "••••••••••• (đã lưu)" : "Dán Chat ID của bạn vào đây"}
            value={chatId}
            onChange={(e) => setChatId(e.target.value)}
            className="font-mono text-sm"
          />
        </div>
      </div>

      <div className="flex items-center justify-between">
        <Button
          onClick={save}
          disabled={saving}
          size="sm"
          id="telegram-settings-save"
        >
          <Save className="w-4 h-4 mr-2" />
          {saving ? "Đang lưu..." : "Lưu cấu hình"}
        </Button>
      </div>

      {(message || error) && (
        <p
          className={`rounded-xl px-4 py-3 font-semibold ${
            error
              ? "bg-red-50 text-red-700 border border-red-100"
              : "bg-emerald-50 text-emerald-700 border border-emerald-100"
          }`}
          style={{ fontSize: "12px" }}
          role={error ? "alert" : "status"}
          id="telegram-settings-message"
        >
          {error || message}
        </p>
      )}
    </div>
  );
}
