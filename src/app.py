import eventlet
eventlet.monkey_patch()
from flask import Flask, render_template, request, jsonify, redirect, url_for
import sqlite3
import json
from datetime import datetime
import random
import os

app = Flask(__name__)

DB_PATH = os.path.join("database", "rtu_config.db")


# -----------------------------
# DATABASE HELPERS
# -----------------------------
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    os.makedirs("database", exist_ok=True)
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS rtu_config (
            id INTEGER PRIMARY KEY,
            json_config TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
    """)

    conn.commit()

    cur.execute("SELECT COUNT(*) AS c FROM rtu_config")
    row = cur.fetchone()

    if row["c"] == 0:
        default_config = {
            "password": "6666",
            "sim_number": "",
            "din1_type": "1:NO",
            "din2_type": "1:NO",
            "din1_alarm": "Unauthorized door opened",
            "din2_alarm": "DIN2 Alarm",
            "auto_arm_after_call": 10,
            "arm_after_power_on": 0,
            "relay_auth": 1,
            "relay_on_timer": 0,
            "notify_on_on": 3,
            "notify_on_off": 3,
            "sms_on": "Relay ON!",
            "sms_off": "Relay OFF!",
            "power_fail_delay": 999,
            "self_check_interval": 0,
            "mqtt_upload_interval": 60,
            "server_ip": "",
            "server_port": 0,
            "gprs_apn": "",
            "gprs_user": "",
            "gprs_password": "",
            "heartbeat_interval": 60,
            "mqtt_client_id": "",
            "mqtt_user": "",
            "mqtt_password": "",
            "mqtt_publish": "",
            "mqtt_subscribe": ""
        }

        cur.execute(
            "INSERT INTO rtu_config (json_config, updated_at) VALUES (?, ?)",
            (json.dumps(default_config), datetime.utcnow().isoformat())
        )
        conn.commit()

    conn.close()


def load_rtu_settings():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("SELECT json_config FROM rtu_config WHERE id = 1")
    row = cur.fetchone()
    conn.close()
    return json.loads(row["json_config"])


def save_rtu_settings(settings):
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        "UPDATE rtu_config SET json_config = ?, updated_at = ? WHERE id = 1",
        (json.dumps(settings), datetime.utcnow().isoformat())
    )
    conn.commit()
    conn.close()


# -----------------------------
# INITIALIZE DATABASE ON STARTUP
# -----------------------------
with app.app_context():
    init_db()


# -----------------------------
# ROUTES — MAIN REDIRECT
# -----------------------------
@app.route("/")
def index():
    return redirect(url_for("rtu_device_identity"))


# -----------------------------
# RTU SETTINGS PAGES
# -----------------------------
@app.route("/rtu/device-identity")
def rtu_device_identity():
    return render_template("rtu_device_identity.html", s=load_rtu_settings())


@app.route("/rtu/device-identity/save", methods=["POST"])
def rtu_device_identity_save():
    s = load_rtu_settings()
    s["password"] = request.form["password"]
    s["sim_number"] = request.form["sim_number"]
    s["mqtt_client_id"] = request.form["mqtt_client_id"]
    save_rtu_settings(s)
    return redirect(url_for("rtu_device_identity"))


@app.route("/rtu/digital-inputs")
def rtu_digital_inputs():
    return render_template("rtu_digital_inputs.html", s=load_rtu_settings())


@app.route("/rtu/digital-inputs/save", methods=["POST"])
def rtu_digital_inputs_save():
    s = load_rtu_settings()
    s["din1_type"] = request.form["din1_type"]
    s["din2_type"] = request.form["din2_type"]
    s["din1_alarm"] = request.form["din1_alarm"]
    s["din2_alarm"] = request.form["din2_alarm"]
    save_rtu_settings(s)
    return redirect(url_for("rtu_digital_inputs"))


@app.route("/rtu/relay-control")
def rtu_relay_control():
    return render_template("rtu_relay_control.html", s=load_rtu_settings())


@app.route("/rtu/relay-control/save", methods=["POST"])
def rtu_relay_control_save():
    s = load_rtu_settings()
    s["relay_auth"] = int(request.form["relay_auth"])
    s["relay_on_timer"] = int(request.form["relay_on_timer"])
    s["notify_on_on"] = int(request.form["notify_on_on"])
    s["notify_on_off"] = int(request.form["notify_on_off"])
    s["sms_on"] = request.form["sms_on"]
    s["sms_off"] = request.form["sms_off"]
    save_rtu_settings(s)
    return redirect(url_for("rtu_relay_control"))


@app.route("/rtu/power-system")
def rtu_power_system():
    return render_template("rtu_power_system.html", s=load_rtu_settings())


@app.route("/rtu/power-system/save", methods=["POST"])
def rtu_power_system_save():
    s = load_rtu_settings()
    s["auto_arm_after_call"] = int(request.form["auto_arm_after_call"])
    s["arm_after_power_on"] = int(request.form["arm_after_power_on"])
    s["power_fail_delay"] = int(request.form["power_fail_delay"])
    s["self_check_interval"] = int(request.form["self_check_interval"])
    s["heartbeat_interval"] = int(request.form["heartbeat_interval"])
    save_rtu_settings(s)
    return redirect(url_for("rtu_power_system"))


@app.route("/rtu/mqtt")
def rtu_mqtt():
    return render_template("rtu_mqtt.html", s=load_rtu_settings())


@app.route("/rtu/mqtt/save", methods=["POST"])
def rtu_mqtt_save():
    s = load_rtu_settings()
    s["mqtt_user"] = request.form["mqtt_user"]
    s["mqtt_password"] = request.form["mqtt_password"]
    s["mqtt_publish"] = request.form["mqtt_publish"]
    s["mqtt_subscribe"] = request.form["mqtt_subscribe"]
    s["mqtt_upload_interval"] = int(request.form["mqtt_upload_interval"])
    save_rtu_settings(s)
    return redirect(url_for("rtu_mqtt"))


@app.route("/rtu/gprs")
def rtu_gprs():
    return render_template("rtu_gprs.html", s=load_rtu_settings())


@app.route("/rtu/gprs/save", methods=["POST"])
def rtu_gprs_save():
    s = load_rtu_settings()
    s["server_ip"] = request.form["server_ip"]
    s["server_port"] = int(request.form["server_port"])
    s["gprs_apn"] = request.form["gprs_apn"]
    s["gprs_user"] = request.form["gprs_user"]
    s["gprs_password"] = request.form["gprs_password"]
    save_rtu_settings(s)
    return redirect(url_for("rtu_gprs"))


# -----------------------------
# RESET DEFAULTS
# -----------------------------
@app.route("/rtu/reset-defaults", methods=["POST"])
def rtu_reset_defaults():
    default_config = {
        "password": "6666",
        "sim_number": "",
        "din1_type": "1:NO",
        "din2_type": "1:NO",
        "din1_alarm": "Unauthorized door opened",
        "din2_alarm": "DIN2 Alarm",
        "auto_arm_after_call": 10,
        "arm_after_power_on": 0,
        "relay_auth": 1,
        "relay_on_timer": 0,
        "notify_on_on": 3,
        "notify_on_off": 3,
        "sms_on": "Relay ON!",
        "sms_off": "Relay OFF!",
        "power_fail_delay": 999,
        "self_check_interval": 0,
        "mqtt_upload_interval": 60,
        "server_ip": "",
        "server_port": 0,
        "gprs_apn": "",
        "gprs_user": "",
        "gprs_password": "",
        "heartbeat_interval": 60,
        "mqtt_client_id": "",
        "mqtt_user": "",
        "mqtt_password": "",
        "mqtt_publish": "",
        "mqtt_subscribe": ""
    }

    save_rtu_settings(default_config)
    return redirect(request.referrer or "/rtu/device-identity")


# -----------------------------
# SIMULATED PUSH + LOGGING
# -----------------------------
PUSH_LOG = []
SIGNAL_POINTS = []
HISTORY_LOG = []


@app.route("/api/push", methods=["POST"])
def api_push():
    cfg = load_rtu_settings()
    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "config": cfg,
        "event": "Config pushed to device"
    }
    PUSH_LOG.append(entry)
    HISTORY_LOG.append(entry)
    return jsonify({"status": "ok"})


@app.route("/debug")
def debug():
    return "<pre>" + json.dumps(PUSH_LOG, indent=2) + "</pre>"


# -----------------------------
# DASHBOARD + SIGNAL + HISTORY PAGES
# -----------------------------
@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")


@app.route("/signal")
def signal():
    return render_template("signal.html")


@app.route("/history")
def history():
    return render_template("history.html")


# -----------------------------
# SIGNAL + HISTORY APIs
# -----------------------------
@app.route("/api/signal-data")
def api_signal_data():
    if len(SIGNAL_POINTS) > 50:
        SIGNAL_POINTS.pop(0)
    SIGNAL_POINTS.append({
        "t": datetime.utcnow().isoformat(),
        "value": random.randint(40, 100)
    })
    return jsonify(SIGNAL_POINTS)


@app.route("/api/history")
def api_history():
    return jsonify(HISTORY_LOG)


# -----------------------------
# RUN SERVER
# -----------------------------
if __name__ == "__main__":
    app.run(debug=True)
