import datetime
import json
import threading
import time

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# ----------------- APP SETUP -----------------

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------- IN-MEMORY STATE -----------------

devices = {
    "rtu-001": {
        "id": "rtu-001",
        "name": "Front Gate",
        "location": "Driveway",
        "last_seen": None,
        "relay_state": "OFF",
        "door_state": "unknown",
        "signal_raw": None,
        "serving_cell_raw": None,
        "settings": {
            "password": "1234",
            "sim_number": "",
            "din1_type": "NO",
            "din2_type": "NO",
            "din1_alarm": "Unauthorized door opened",
            "din2_alarm": "DIN2 Alarm",
            "auto_arm": 10,
            "arm_on_powerup": 0,
            "relay_authorization": 1,
            "relay_on_timer": 0,
            "notify_on_on": 3,
            "notify_on_off": 3,
            "sms_text_on": "Relay ON!",
            "sms_text_off": "Relay OFF!",
            "power_fail_delay": 999,
            "self_check_interval": 0,
            "mqtt_upload_interval": 60,
            "server_ip": "",
            "server_port": 0,
            "apn": "",
            "apn_user": "",
            "apn_pass": "",
            "heartbeat": 60,
            "mqtt_client_id": "",
            "mqtt_user": "",
            "mqtt_pass": "",
            "mqtt_pub": "",
            "mqtt_sub": "",
            "firmware": "1.0.0",
            "imei": "8616307054XXXXX"
        }
    }
}

authorized_users = {
    "rtu-001": [
        {"slot": 1, "phone_number": "+61400111222", "always_allowed": True},
        {"slot": 2, "phone_number": "+61400333444", "always_allowed": True},
    ]
}

events = {
    "rtu-001": [
        {
            "timestamp": "2026-04-24T07:30:00Z",
            "source": "Telephone",
            "action": "Relay ON",
            "executant": "+61400111222",
            "content": "DoorOpen",
        }
    ]
}

telemetry_history = {
    "rtu-001": []  # list of {timestamp, signal_dbm}
}

agent_connections = {}  # device_id -> WebSocket

# ----------------- CSS + LAYOUT -----------------

BASE_CSS = """
body { font-family: Arial; background:#0b0c10; color:#c5c6c7; margin:0; }
header { background:#1f2833; padding:10px 20px; display:flex; justify-content:space-between; align-items:center; }
header h1 { margin:0; color:#66fcf1; font-size:20px; }
nav a { color:#c5c6c7; margin-left:15px; text-decoration:none; }
nav a:hover { color:#66fcf1; }
main { padding:20px; }
.card { background:#1f2833; padding:15px; border-radius:8px; margin-bottom:15px; }
.card h2 { margin-top:0; color:#66fcf1; }
.table { width:100%; border-collapse:collapse; margin-top:10px; }
.table th, .table td { border-bottom:1px solid #333; padding:6px 4px; font-size:13px; }
.badge { padding:2px 6px; border-radius:4px; font-size:11px; }
.badge-online { background:#45a29e; color:#0b0c10; }
.badge-offline { background:#c3073f; color:#fff; }
.small { font-size:12px; color:#888; }
button { padding:6px 12px; border:none; border-radius:4px; background:#45a29e; color:#0b0c10; cursor:pointer; }
button:hover { background:#66fcf1; }
a.btn { padding:6px 12px; border-radius:4px; background:#45a29e; color:#0b0c10; text-decoration:none; font-size:13px; }
a.btn:hover { background:#66fcf1; }
input, select, textarea { width:100%; padding:6px; margin:4px 0 10px 0; background:#0b0c10; color:#c5c6c7; border:1px solid #333; border-radius:4px; }
label { font-size:13px; color:#66fcf1; }
"""

def layout(title, body, extra_head=""):
    return (
        "<!doctype html><html><head><title>GateMaster – " + title + "</title>"
        "<style>" + BASE_CSS + "</style>" + extra_head + "</head><body>"
        "<header><h1>GateMaster</h1>"
        "<nav>"
        "<a href='/'>Devices</a>"
        "</nav></header>"
        "<main>" + body + "</main></body></html>"
    )
# ----------------- UI PAGES -----------------

@app.get("/", response_class=HTMLResponse)
def page_devices():
    rows = ""
    for d in devices.values():
        online = d["last_seen"] is not None
        badge = "<span class='badge badge-online'>ONLINE</span>" if online else "<span class='badge badge-offline'>OFFLINE</span>"
        rows += (
            "<tr>"
            "<td><a href='/devices/" + d["id"] + "'>" + (d["name"] or d["id"]) + "</a></td>"
            "<td>" + (d["location"] or "") + "</td>"
            "<td>" + badge + "</td>"
            "<td class='small'>" + (d["last_seen"] or "never") + "</td>"
            "</tr>"
        )

    body = (
        "<div class='card'><h2>Devices</h2>"
        "<table class='table'>"
        "<tr><th>Name</th><th>Location</th><th>Status</th><th>Last seen</th></tr>"
        + (rows or "<tr><td colspan='4' class='small'>No devices.</td></tr>") +
        "</table></div>"
    )
    return layout("Devices", body)


@app.get("/devices/{device_id}", response_class=HTMLResponse)
def page_device_overview(device_id: str):
    d = devices.get(device_id)
    if not d:
        return layout("Not found", "<div class='card'><h2>Device not found</h2></div>")

    online = d["last_seen"] is not None
    badge = "<span class='badge badge-online'>ONLINE</span>" if online else "<span class='badge badge-offline'>OFFLINE</span>"

    body = (
        "<div class='card'><h2>" + d["name"] + " " + badge + "</h2>"
        "<div class='small'>ID: " + d["id"] + "</div>"
        "<div class='small'>Location: " + (d["location"] or "") + "</div>"
        "<div class='small'>Relay: " + d["relay_state"] + "</div>"
        "<div class='small'>Door: " + d["door_state"] + "</div>"
        "<div class='small'>Signal: " + str(d["signal_raw"]) + "</div>"
        "<div class='small'>Cell: " + str(d["serving_cell_raw"]) + "</div>"
        "<div class='small'>Last seen: " + str(d["last_seen"]) + "</div>"
        "<p>"
        "<a class='btn' href='/devices/" + device_id + "/history'>History</a> "
        "<a class='btn' href='/devices/" + device_id + "/signal'>Signal Graph</a> "
        "<a class='btn' href='/devices/" + device_id + "/users'>Authorized Users</a> "
        "<a class='btn' href='/devices/" + device_id + "/settings'>Settings</a> "
        "<a class='btn' href='/devices/" + device_id + "/system'>System Info</a> "
        "<a class='btn' href='/devices/" + device_id + "/debug'>Debug Console</a>"
        "</p>"
        "<p><button onclick=\"fetch('/api/devices/" + device_id + "/command', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({action:'relay_on'})}).then(()=>alert('Command sent'))\">Open Gate</button></p>"
        "</div>"
    )
    return layout("Device " + device_id, body)


@app.get("/devices/{device_id}/history", response_class=HTMLResponse)
def page_device_history(device_id: str):
    evs = events.get(device_id, [])
    rows = ""
    for e in evs:
        rows += (
            "<tr><td>" + e["timestamp"] + "</td>"
            "<td>" + e["source"] + "</td>"
            "<td>" + e["action"] + "</td>"
            "<td>" + e["executant"] + "</td>"
            "<td>" + e["content"] + "</td></tr>"
        )
    body = (
        "<div class='card'><h2>History – " + device_id + "</h2>"
        "<p><a class='btn' href='/devices/" + device_id + "'>Back</a></p>"
        "<table class='table'><tr><th>Time</th><th>Source</th><th>Action</th><th>Phone</th><th>Content</th></tr>"
        + (rows or "<tr><td colspan='5' class='small'>No events.</td></tr>") +
        "</table></div>"
    )
    return layout("History " + device_id, body)


@app.get("/devices/{device_id}/users", response_class=HTMLResponse)
def page_device_users(device_id: str):
    users = authorized_users.get(device_id, [])
    rows = ""
    for u in users:
        rows += (
            "<tr><td>" + str(u["slot"]) + "</td>"
            "<td>" + u["phone_number"] + "</td>"
            "<td>" + ("Yes" if u["always_allowed"] else "No") + "</td></tr>"
        )
    body = (
        "<div class='card'><h2>Authorized Users – " + device_id + "</h2>"
        "<p><a class='btn' href='/devices/" + device_id + "'>Back</a></p>"
        "<table class='table'><tr><th>Slot</th><th>Phone</th><th>Always</th></tr>"
        + (rows or "<tr><td colspan='3' class='small'>No users.</td></tr>") +
        "</table></div>"
    )
    return layout("Users " + device_id, body)


@app.get("/devices/{device_id}/signal", response_class=HTMLResponse)
def page_device_signal(device_id: str):
    extra_head = "<script src='https://cdn.jsdelivr.net/npm/chart.js'></script>"
    body = (
        "<div class='card'><h2>Signal – " + device_id + "</h2>"
        "<p><a class='btn' href='/devices/" + device_id + "'>Back</a></p>"
        "<canvas id='sigChart' height='120'></canvas>"
        "<script>"
        "async function loadData(){"
        " const res = await fetch('/api/devices/" + device_id + "/telemetry');"
        " const data = await res.json();"
        " const labels = data.map(d=>d.timestamp);"
        " const values = data.map(d=>d.signal_dbm);"
        " const ctx = document.getElementById('sigChart').getContext('2d');"
        " new Chart(ctx,{type:'line',data:{labels:labels,datasets:[{label:'Signal dBm',data:values,borderColor:'#66fcf1',tension:0.1}]},options:{scales:{x:{ticks:{color:'#c5c6c7'}},y:{ticks:{color:'#c5c6c7'}}},plugins:{legend:{labels:{color:'#c5c6c7'}}}}});"
        "}"
        "loadData();"
        "</script>"
        "</div>"
    )
    return layout("Signal " + device_id, body, extra_head=extra_head)


@app.get("/devices/{device_id}/settings", response_class=HTMLResponse)
def page_device_settings(device_id: str):
    d = devices.get(device_id)
    if not d:
        return layout("Not found", "<div class='card'><h2>Device not found</h2></div>")

    s = d["settings"]

    form = ""
    for key in s:
        form += (
            "<label>" + key.replace("_", " ").title() + "</label>"
            "<input value='" + str(s[key]) + "'>"
        )

    body = (
        "<div class='card'><h2>Settings – " + device_id + "</h2>"
        "<p><a class='btn' href='/devices/" + device_id + "'>Back</a></p>"
        "<form>" + form + "</form>"
        "<p class='small'>Note: Saving settings will be implemented when real agent is connected.</p>"
        "</div>"
    )
    return layout("Settings " + device_id, body)


@app.get("/devices/{device_id}/system", response_class=HTMLResponse)
def page_device_system(device_id: str):
    d = devices.get(device_id)
    s = d["settings"]

    body = (
        "<div class='card'><h2>System Info – " + device_id + "</h2>"
        "<p><a class='btn' href='/devices/" + device_id + "'>Back</a></p>"
        "<div class='small'>Firmware: " + s["firmware"] + "</div>"
        "<div class='small'>IMEI: " + s["imei"] + "</div>"
        "<div class='small'>Heartbeat: " + str(s["heartbeat"]) + "</div>"
        "<div class='small'>MQTT Upload Interval: " + str(s["mqtt_upload_interval"]) + "</div>"
        "</div>"
    )
    return layout("System " + device_id, body)


@app.get("/devices/{device_id}/debug", response_class=HTMLResponse)
def page_device_debug(device_id: str):
    body = (
        "<div class='card'><h2>Debug Console – " + device_id + "</h2>"
        "<p><a class='btn' href='/devices/" + device_id + "'>Back</a></p>"
        "<textarea rows='10' placeholder='Debug output will appear here soon...'></textarea>"
        "</div>"
    )
    return layout("Debug " + device_id, body)
# ----------------- REST API -----------------

@app.get("/api/devices")
def api_list_devices():
    return list(devices.values())


@app.get("/api/devices/{device_id}/telemetry")
def api_get_telemetry(device_id: str):
    return telemetry_history.get(device_id, [])


@app.post("/api/devices/{device_id}/command")
async def api_send_command(device_id: str, body: dict):
    ws = agent_connections.get(device_id)
    if not ws:
        return {"ok": False, "error": "agent_offline"}

    cmd = {
        "type": "command",
        "command_id": device_id + "-" + str(time.time()),
        "action": body.get("action"),
        "parameters": body.get("parameters") or {},
    }

    await ws.send_text(json.dumps(cmd))
    return {"ok": True}


# ----------------- WEBSOCKET FOR AGENT -----------------

@app.websocket("/ws/agent")
async def agent_ws(ws: WebSocket):
    await ws.accept()
    device_id = None

    try:
        while True:
            raw = await ws.receive_text()
            data = json.loads(raw)
            msg_type = data.get("type")

            # HELLO HANDSHAKE
            if msg_type == "hello":
                device_id = data["device_id"]
                agent_connections[device_id] = ws

            # TELEMETRY
            elif msg_type == "telemetry":
                d = devices.setdefault(device_id, {"id": device_id})
                d["last_seen"] = datetime.datetime.utcnow().isoformat()

                rtu = data.get("rtu", {})
                modem = data.get("modem", {})

                d["relay_state"] = rtu.get("relay", d.get("relay_state"))
                d["door_state"] = rtu.get("door", d.get("door_state"))
                d["signal_raw"] = modem.get("signal_raw")
                d["serving_cell_raw"] = modem.get("serving_cell_raw")

                # Parse signal dBm from raw string
                sig_raw = modem.get("signal_raw") or ""
                sig_dbm = None
                try:
                    parts = sig_raw.split(",")
                    if len(parts) >= 2:
                        sig_dbm = int(parts[1])
                except Exception:
                    sig_dbm = None

                if sig_dbm is not None:
                    hist = telemetry_history.setdefault(device_id, [])
                    hist.append({
                        "timestamp": datetime.datetime.utcnow().isoformat(),
                        "signal_dbm": sig_dbm
                    })
                    if len(hist) > 200:
                        del hist[0:len(hist)-200]

            # COMMAND RESULT
            elif msg_type == "command_result":
                events.setdefault(device_id, []).append({
                    "timestamp": datetime.datetime.utcnow().isoformat(),
                    "source": "Agent",
                    "action": "Command Result",
                    "executant": "Device",
                    "content": str(data.get("result"))
                })

    except WebSocketDisconnect:
        if device_id and agent_connections.get(device_id) is ws:
            del agent_connections[device_id]


# ----------------- BUILT-IN FAKE AGENT -----------------

def fake_agent_loop():
    import websocket  # websocket-client
    url = "ws://localhost:8000/ws/agent"
    device_id = "rtu-001"

    while True:
        try:
            ws = websocket.create_connection(url)
            ws.send(json.dumps({"type": "hello", "device_id": device_id}))

            last_telemetry = 0

            while True:
                now = time.time()

                # Send telemetry every 5 seconds
                if now - last_telemetry > 5:
                    telem = {
                        "type": "telemetry",
                        "device_id": device_id,
                        "timestamp": datetime.datetime.utcnow().isoformat(),
                        "modem": {
                            "imei": "8616307054XXXXX",
                            "iccid": "8944XXXXXXXXXXXX",
                            "signal_raw": '+QCSQ: "LTE",-85,-10,-6,15',
                            "serving_cell_raw": '+QENG: "servingcell",...'
                        },
                        "rtu": {
                            "relay": "OFF",
                            "door": "closed",
                            "din2": "normal",
                            "power": "ok"
                        }
                    }
                    ws.send(json.dumps(telem))
                    last_telemetry = now

                # Check for commands
                ws.settimeout(1)
                try:
                    raw = ws.recv()
                    if raw:
                        msg = json.loads(raw)
                        if msg.get("type") == "command":
                            result = {
                                "type": "command_result",
                                "command_id": msg.get("command_id"),
                                "device_id": device_id,
                                "result": {
                                    "success": True,
                                    "rtu_reply": "Simulated " + str(msg.get("action"))
                                }
                            }
                            ws.send(json.dumps(result))
                except websocket.WebSocketTimeoutException:
                    pass

        except Exception:
            time.sleep(5)


# ----------------- MAIN RUNNER -----------------

if __name__ == "__main__":
    # Start fake agent in background
    t = threading.Thread(target=fake_agent_loop, daemon=True)
    t.start()

    uvicorn.run("gatemaster:app", host="0.0.0.0", port=8000, reload=False)
