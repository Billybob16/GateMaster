import os
import json
import sqlite3
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, jsonify

app = Flask(__name__)

DB_PATH = os.path.join("database", "rtu_config.db")


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
    if not row:
        return {}
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


@app.before_first_request
def startup():
    init_db()


@app.route("/")
def index():
    return redirect(url_for("rtu_device_identity"))


# ---------- RTU PAGES ----------

@app.route("/rtu/device-identity", methods=["GET"])
def rtu_device_identity():
    s = load_rtu_settings()
    return render_template("rtu_device_identity.html", s=s)


@app.route("/rtu/device-identity/save", methods=["POST"])
def rtu_device_identity_save():
    s = load_rtu_settings()
    s["password"] = request.form.get("password", s["password"])
    s["sim_number"] = request.form.get("sim_number", s["sim_number"])
    s["mqtt_client_id"] = request.form.get("mqtt_client_id", s["mqtt_client_id"])
    save_rtu_settings(s)
    return redirect(url_for("rtu_device_identity"))


@app.route("/rtu/digital-inputs", methods=["GET"])
def rtu_digital_inputs():
    s = load_rtu_settings()
    return render_template("rtu_digital_inputs.html", s=s)


@app.route("/rtu/digital-inputs/save", methods=["POST"])
def rtu_digital_inputs_save():
    s = load_rtu_settings()
    s["din1_type"] = request.form.get("din1_type", s["din1_type"])
    s["din2_type"] = request.form.get("din2_type", s["din2_type"])
    s["din1_alarm"] = request.form.get("din1_alarm", s["din1_alarm"])
    s["din2_alarm"] = request.form.get("din2_alarm", s["din2_alarm"])
    save_rtu_settings(s)
    return redirect(url_for("rtu_digital_inputs"))


@app.route("/rtu/relay-control", methods=["GET"])
def rtu_relay_control():
    s = load_rtu_settings()
    return render_template("rtu_relay_control.html", s=s)


@app.route("/rtu/relay-control/save", methods=["POST"])
def rtu_relay_control_save():
    s = load_rtu_settings()
    s["relay_auth"] = int(request.form.get("relay_auth", s["relay_auth"]))
    s["relay_on_timer"] = int(request.form.get("relay_on_timer", s["relay_on_timer"]))
    s["notify_on_on"] = int(request.form.get("notify_on_on", s["notify_on_on"]))
    s["notify_on_off"] = int(request.form.get("notify_on_off", s["notify_on_off"]))
    s["sms_on"] = request.form.get("sms_on", s["sms_on"])
    s["sms_off"] = request.form.get("sms_off", s["sms_off"])
    save_rtu_settings(s)
    return redirect(url_for("rtu_relay_control"))


@app.route("/rtu/power-system", methods=["GET"])
def rtu_power_system():
    s = load_rtu_settings()
    return render_template("rtu_power_system.html", s=s)


@app.route("/rtu/power-system/save", methods=["POST"])
def rtu_power_system_save():
    s = load_rtu_settings()
    s["auto_arm_after_call"] = int(request.form.get("auto_arm_after_call", s["auto_arm_after_call"]))
    s["arm_after_power_on"] = int(request.form.get("arm_after_power_on", s["arm_after_power_on"]))
    s["power_fail_delay"] = int(request.form.get("power_fail_delay", s["power_fail_delay"]))
    s["self_check_interval"] = int(request.form.get("self_check_interval", s["self_check_interval"]))
    s["heartbeat_interval"] = int(request.form.get("heartbeat_interval", s["heartbeat_interval"]))
    save_rtu_settings(s)
    return redirect(url_for("rtu_power_system"))


@app.route("/rtu/mqtt", methods=["GET"])
def rtu_mqtt():
    s = load_rtu_settings()
    return render_template("rtu_mqtt.html", s=s)


@app.route("/rtu/mqtt/save", methods=["POST"])
def rtu_mqtt_save():
    s = load_rtu_settings()
    s["mqtt_user"] = request.form.get("mqtt_user", s["mqtt_user"])
    s["mqtt_password"] = request.form.get("mqtt_password", s["mqtt_password"])
    s["mqtt_publish"] = request.form.get("mqtt_publish", s["mqtt_publish"])
    s["mqtt_subscribe"] = request.form.get("mqtt_subscribe", s["mqtt_subscribe"])
    s["mqtt_upload_interval"] = int(request.form.get("mqtt_upload_interval", s["mqtt_upload_interval"]))
    save_rtu_settings(s)
    return redirect(url_for("rtu_mqtt"))


@app.route("/rtu/gprs", methods=["GET"])
def rtu_gprs():
    s = load_rtu_settings()
    return render_template("rtu_gprs.html", s=s)


@app.route("/rtu/gprs/save", methods=["POST"])
def rtu_gprs_save():
    s = load_rtu_settings()
    s["server_ip"] = request.form.get("server_ip", s["server_ip"])
    s["server_port"] = int(request.form.get("server_port", s["server_port"]))
    s["gprs_apn"] = request.form.get("gprs_apn", s["gprs_apn"])
    s["gprs_user"] = request.form.get("gprs_user", s["gprs_user"])
    s["gprs_password"] = request.form.get("gprs_password", s["gprs_password"])
    save_rtu_settings(s)
    return redirect(url_for("rtu_gprs"))


# ---------- SIMULATED PUSH + LOGGING ----------

PUSH_LOG = []  # in-memory for now


@app.route("/api/push", methods=["POST"])
def api_push():
    s = load_rtu_settings()
    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "config": s
    }
    PUSH_LOG.append(entry)
    return jsonify({"status": "ok"})


@app.route("/debug")
def debug():
    return "<pre>" + json.dumps(PUSH_LOG, indent=2) + "</pre>"


if __name__ == "__main__":
    app.run(debug=True)
