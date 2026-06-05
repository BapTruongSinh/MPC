import asyncio
import websockets
import json
import random
import time

# Đường dẫn đến Server Django của bạn (đổi lại port nếu cần)
WS_URL = "ws://127.0.0.1:8000/ws/esp/"

# Biến lưu trạng thái giả lập của phần cứng
state = {
    "fanOn": False,
    "pumpOn": False,
    "lightOn": False,
    "mistOn": False,
    "isAutoMode": False,
    "sunMode": "sun_manual",
    "servo_h": 90,
    "servo_v": 90
}

async def send_telemetry(ws):
    while True:
        payload = {
            "type": "telemetry",
            "data": {
                "soil_moisture": random.randint(40, 80), # Ẩm đất ngẫu nhiên 40-80%
                "temperature": round(random.uniform(25.0, 35.0), 1),
                "humidity": round(random.uniform(50.0, 80.0), 1),
                "fan": state["fanOn"],
                "pump": state["pumpOn"],
                "light_device": state["lightOn"],
                "mist": state["mistOn"],
                "mode": "auto" if state["isAutoMode"] else "manual",
                "auto_mode": state["isAutoMode"],
                "payload": {
                    "sun_tracker": {
                        "mode": state["sunMode"],
                        "ldr_lt": random.randint(100, 1000),
                        "ldr_rt": random.randint(100, 1000),
                        "ldr_ld": random.randint(100, 1000),
                        "ldr_rd": random.randint(100, 1000),
                        "servo_horizontal": state["servo_h"],
                        "servo_vertical": state["servo_v"]
                    }
                },
                "device_states": {
                    "fan_on": state["fanOn"],
                    "pump_on": state["pumpOn"],
                    "light_on": state["lightOn"],
                    "mist_on": state["mistOn"]
                },
                "sensor_errors": {
                    "dht": False, "soil": False, "light": False
                }
            }
        }
        await ws.send(json.dumps(payload))
        print(f"[Telemetry] Đã gửi dữ liệu giả lập - Bơm: {'BẬT' if state['pumpOn'] else 'TẮT'}")
        await asyncio.sleep(5)

async def send_heartbeat(ws):
    while True:
        payload = {
            "type": "heartbeat",
            "data": {
                "uptime_ms": int(time.time() * 1000),
                "free_heap": 200000,
                "fan": state["fanOn"],
                "pump": state["pumpOn"],
                "light_device": state["lightOn"],
                "mist": state["mistOn"],
                "mode": "auto" if state["isAutoMode"] else "manual",
                "auto_mode": state["isAutoMode"],
                "payload": {
                    "sun_tracker": {
                        "mode": state["sunMode"],
                        "ldr_lt": 500, "ldr_rt": 500, "ldr_ld": 500, "ldr_rd": 500,
                        "servo_horizontal": state["servo_h"],
                        "servo_vertical": state["servo_v"]
                    }
                }
            }
        }
        await ws.send(json.dumps(payload))
        await asyncio.sleep(15)

async def receive_commands(ws):
    async for message in ws:
        doc = json.loads(message)
        msg_type = doc.get("type")
        data = doc.get("data", {})
        
        print(f"\n[NHẬN LỆNH TỪ WEB] Type: {msg_type}")
        
        if msg_type == "mode":
            mode_val = data.get("value", "").lower()
            state["isAutoMode"] = (mode_val == "auto")
            print(f" ---> Cập nhật chế độ: {mode_val.upper()}")
            
        elif msg_type == "sun_control":
            cmd = data.get("command")
            if cmd == "set_mode":
                state["sunMode"] = data.get("mode")
                print(f" ---> Sun Tracker Mode: {state['sunMode']}")
            elif cmd == "set_servo":
                servo = data.get("servo")
                angle = data.get("angle")
                if servo == "horizontal": state["servo_h"] = angle
                else: state["servo_v"] = angle
                print(f" ---> Xoay bệ mặt trời {servo} góc {angle} độ")
                
        elif msg_type == "pending_commands":
            commands = data.get("commands", [])
            for cmd in commands:
                cmd_id = cmd.get("id")
                device = cmd.get("device_code")
                val = cmd.get("value")
                
                print(f" ---> Ra lệnh: {device} = {val.upper()}")
                
                # Sửa trạng thái ảo nội bộ
                if device == "fan": state["fanOn"] = (val == "on")
                if device == "pump": state["pumpOn"] = (val == "on")
                if device == "light": state["lightOn"] = (val == "on")
                if device == "mist": state["mistOn"] = (val == "on")
                
                # Trả lời lại là đã bật xong
                ack_payload = {
                    "type": "ack",
                    "data": {
                        "id": cmd_id,
                        "status": "ack",
                        "actual_state": (val == "on")
                    }
                }
                await ws.send(json.dumps(ack_payload))
                print(f" ---> Đã gửi ACK cho Server (ID: {cmd_id})")

async def main():
    print(f"Đang kết nối giả lập tới {WS_URL} ...")
    try:
        async with websockets.connect(WS_URL) as ws:
            print("====================================")
            print("✅ KẾT NỐI THÀNH CÔNG!")
            print("🚀 ESP32 ẢO ĐANG CHẠY...")
            print("====================================\n")
            
            await asyncio.gather(
                send_telemetry(ws),
                send_heartbeat(ws),
                receive_commands(ws)
            )
    except Exception as e:
        print(f"Lỗi: Không thể kết nối. Hãy chắc chắn Server Django đang chạy.\nChi tiết lỗi: {e}")

if __name__ == "__main__":
    asyncio.run(main())
