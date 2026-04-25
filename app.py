from flask import Flask, render_template, request, redirect, session, jsonify
from flask_socketio import SocketIO
import eventlet
import random
import datetime
from threading import Thread, Lock
import time

eventlet.monkey_patch()

app = Flask(__name__)
app.secret_key = "supersecret"
socketio = SocketIO(app, async_mode="eventlet")

# -----------------------------
# Fake in-memory data
# -----------------------------
lock = Lock()

devices = [
    {"id": 1, "name": "RTU5025-A", "site": "Warehouse 1", "status": "Online", "signal": 75},
    {"id": 2, "name": "RTU5025-B", "site": "Depot 3", "status": "Online", "signal": 62},
    {"id": 3, "name": "RTU5025-C", "site": "Yard 2", "status": "Offline", "signal": 0},
]

history = []
signal_points = []

settings = {
    "admin_phone": "+61400000000",
    "timezone": "Australia/Sydney",
    "heartbeat_interval": 60,
    "signal_threshold": 30,
    "relay_pulse_ms": 800,
}

system_info = {
    "agent_version": "1.0.0",
    "backend_version": "1.0.0",
    "uptime": "0h 0m",
    "host": "Render Dyno",
}

# -----------------------------
# Fake telemetry generator
# -----------------------------
def telemetry_loop():
    while True:
        with lock:
            now = datetime.datetime.utcnow().strftime("%H:%M:%S")

            # Update signals
            for d in devices:
                if d["status"] == "Online":
                    jitter = random.randint(-4, 4)
                    d["signal"] = max(0, min(100, d["signal"] + jitter))

            # Add signal point
            avg = int(sum(d["signal"] for d in devices if d["status"] == "Online") /
                      max(1, len([d for d in devices if d["status"] == "Online"])))

            signal_points.append({"time": now, "value": avg})
            if len(signal_points) > 60:
                signal_points.pop(0)

            # Random history event
            if random.random() < 0.25:
                dev = random.choice(devices)
                evt = random.choice(["Gate opened", "Gate closed", "Power fail", "Power restored"])
                history.insert(0, {
                    "time": now,
                    "device": dev["name"],
                    "event": evt,
                    "signal": dev["signal"]
                })
                if len(history) > 200:
                    history.pop()

        socketio.emit("telemetry", {"devices": devices, "signal": signal_points})
        time.sleep(3)

Thread(target=telemetry_loop, daemon=True).start()

# -----------------------------
# Authentication
# -----------------------------
@app.route("/")
def index():
    if "user" not in session:
        return redirect("/login")
    return redirect("/dashboard")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        if email == "admin@gatemaster.com" and password == "admin":
            session["user"] = "superadmin"
            return redirect("/dashboard")

        session["user"] = "client"
        return redirect("/dashboard")

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# -----------------------------
# Pages
# -----------------------------
@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")

@app.route("/devices")
def devices_page():
    return render_template("devices.html")

@app.route("/history")
def history_page():
    return render_template("history.html")

@app.route("/signal")
def signal_page():
    return render_template("signal.html")

@app.route("/settings")
def settings_page():
    return render_template("settings.html")

@app.route("/system")
def system_page():
    return render_template("system.html")

@app.route("/debug")
def debug_page():
    return render_template("debug.html")

# -----------------------------
# APIs
# -----------------------------
@app.route("/api/devices")
def api_devices():
    return jsonify(devices)

@app.route("/api/history")
def api_history():
    return jsonify(history)

@app.route("/api/signal")
def api_signal():
    return jsonify(signal_points)

@app.route("/api/system")
def api_system():
    return jsonify(system_info)

@app.route("/api/settings")
def api_settings():
    return jsonify(settings)

# -----------------------------
# Run
# -----------------------------
if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000)
