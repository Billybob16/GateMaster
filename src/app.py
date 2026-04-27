import os
import json
from datetime import datetime
from flask import Flask, request, jsonify, render_template, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
import requests

# -------------------------------------------------
# RTU CONFIG
# -------------------------------------------------
RTU_PHONE = "+61494652971"
RTU_PWD = "6666"

# -------------------------------------------------
# MOBILEMESSAGE API (INSERT YOUR REAL VALUES)
# -------------------------------------------------
MOBILEMESSAGE_USERNAME = "<LFKfOM>"
MOBILEMESSAGE_API_KEY = "<6tCVC8GFN4XPIQRJbrcAd1sXyR6WD4gVLxMjqqqYiU8>"

# -------------------------------------------------
# FLASK APP + DATABASE
# -------------------------------------------------
app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///rtu_config.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)

# -------------------------------------------------
# DATABASE MODELS
# -------------------------------------------------

class User(db.Model):
    __tablename__ = "users"

    slot = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    number = db.Column(db.String(32), nullable=False)
    access_type = db.Column(db.String(32), nullable=False)
    start_date = db.Column(db.String(16))
    start_time = db.Column(db.String(16))
    end_date = db.Column(db.String(16))
    end_time = db.Column(db.String(16))


class History(db.Model):
    __tablename__ = "history"

    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.String(32), nullable=False)
    event = db.Column(db.String(255), nullable=False)
    details = db.Column(db.Text)


class SignalData(db.Model):
    __tablename__ = "signal_data"

    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.String(32), nullable=False)
    rssi = db.Column(db.Integer, nullable=False)


class SMSLog(db.Model):
    __tablename__ = "sms_log"

    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.String(32), nullable=False)
    sender = db.Column(db.String(32), nullable=False)
    message = db.Column(db.Text, nullable=False)


class DeviceStatus(db.Model):
    __tablename__ = "device_status"

    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.String(32), nullable=False)
    online = db.Column(db.Boolean, nullable=False)
    last_signal = db.Column(db.Integer)


class RTUConfig(db.Model):
    __tablename__ = "rtu_config"

    id = db.Column(db.Integer, primary_key=True)
    json_config = db.Column(db.Text, nullable=False)
    updated_at = db.Column(db.String(32), nullable=False)


# -------------------------------------------------
# SMS SENDER (MobileMessage)
# -------------------------------------------------

def send_sms(number, message):
    url = "https://api.mobilemessage.com.au/sms/send"
    payload = {
        "username": MOBILEMESSAGE_USERNAME,
        "apikey": MOBILEMESSAGE_API_KEY,
        "to": number,
        "message": message
    }

    try:
        r = requests.post(url, json=payload, timeout=10)
        print("SMS SENT:", r.text)
    except Exception as e:
        print("SMS ERROR:", e)


# -------------------------------------------------
# RTU CONFIG HELPERS
# -------------------------------------------------

def get_rtu_config():
    cfg = RTUConfig.query.get(1)
    return json.loads(cfg.json_config)


def save_rtu_config(cfg):
    row = RTUConfig.query.get(1)
    row.json_config = json.dumps(cfg)
    row.updated_at = datetime.utcnow().isoformat()
    db.session.commit()


# -------------------------------------------------
# USER ACCESS HELPERS
# -------------------------------------------------

def next_free_slot():
    used = [u.slot for u in User.query.all()]
    for i in range(1, 256):
        if i not in used:
            return i
    return None


def build_add_user_sms(slot, data):
    name = data["name"]
    number = data["number"]

    sd = data["start_date"].replace("-", "") if data["start_date"] else ""
    st = data["start_time"].replace(":", "") if data["start_time"] else ""
    ed = data["end_date"].replace("-", "") if data["end_date"] else ""
    et = data["end_time"].replace(":", "") if data["end_time"] else ""

    if sd and st and ed and et:
        return f"#PWD{RTU_PWD}#A{slot:02d}ID{name}NUM{number}SD{sd}ST{st}ED{ed}ET{et}#"
    else:
        return f"#PWD{RTU_PWD}#A{slot:02d}ID{name}NUM{number}ALWAYS#"


def build_delete_user_sms(slot):
    return f"#PWD{RTU_PWD}#DEL{slot:02d}#"


# -------------------------------------------------
# USER ACCESS API
# -------------------------------------------------

@app.route("/api/users", methods=["GET"])
def api_get_users():
    users = User.query.order_by(User.slot).all()
    return jsonify([
        {
            "slot": u.slot,
            "name": u.name,
            "number": u.number,
            "access": u.access_type
        }
        for u in users
    ])


@app.route("/api/users", methods=["POST"])
def api_add_user():
    data = request.json
    slot = next_free_slot()

    if slot is None:
        return jsonify({"error": "No free slots"}), 400

    sms_cmd = build_add_user_sms(slot, data)
    send_sms(RTU_PHONE, sms_cmd)

    user = User(
        slot=slot,
        name=data["name"],
        number=data["number"],
        access_type="timed" if data["start_date"] else "always",
        start_date=data["start_date"],
        start_time=data["start_time"],
        end_date=data["end_date"],
        end_time=data["end_time"]
    )
    db.session.add(user)
    db.session.commit()

    return jsonify({"status": "sent", "command": sms_cmd})


@app.route("/api/users/<number>", methods=["DELETE"])
def api_delete_user(number):
    user = User.query.filter_by(number=number).first()
    if not user:
        return jsonify({"error": "User not found"}), 404

    sms_cmd = build_delete_user_sms(user.slot)
    send_sms(RTU_PHONE, sms_cmd)

    db.session.delete(user)
    db.session.commit()

    return jsonify({"status": "sent", "command": sms_cmd})


# -------------------------------------------------
# INBOUND SMS WEBHOOK
# -------------------------------------------------

@app.route("/sms/inbound", methods=["POST"])
def sms_inbound():
    sender = request.form.get("from")
    message = request.form.get("message")

    log = SMSLog(
        timestamp=datetime.utcnow().isoformat(),
        sender=sender,
        message=message
    )
    db.session.add(log)
    db.session.commit()

    print("INBOUND SMS:", sender, message)

    return "OK"


# -------------------------------------------------
# RUN SERVER
# -------------------------------------------------

if __name__ == "__main__":
    app.run(debug=True)
@app.route("/dashboard")
def dashboard_page():
    return render_template("dashboard.html")
@app.route("/users")
def users_page():
    return render_template("users.html")
@app.route("/logs")
def logs_page():
    return render_template("logs.html")

@app.route("/api/logs")
def api_logs():
    logs = SMSLog.query.order_by(SMSLog.id.desc()).all()
    return jsonify([
        {
            "timestamp": l.timestamp,
            "sender": l.sender,
            "message": l.message
        }
        for l in logs
    ])
@app.route("/status")
def status_page():
    return render_template("status.html")

@app.route("/api/status")
def api_status():
    s = DeviceStatus.query.order_by(DeviceStatus.id.desc()).first()
    if not s:
        return jsonify({
            "online": False,
            "last_signal": None,
            "timestamp": None
        })
    return jsonify({
        "online": s.online,
        "last_signal": s.last_signal,
        "timestamp": s.timestamp
    })
@app.route("/settings")
def settings_page():
    return render_template("settings.html")

@app.route("/api/config", methods=["GET"])
def api_get_config():
    cfg = RTUConfig.query.get(1)
    if not cfg:
        return jsonify({})
    return jsonify(json.loads(cfg.json_config))

@app.route("/api/config", methods=["POST"])
def api_save_config():
    data = request.get_json()
    row = RTUConfig.query.get(1)
    if not row:
        row = RTUConfig(id=1, json_config=json.dumps(data), updated_at=datetime.utcnow().isoformat())
        db.session.add(row)
    else:
        row.json_config = json.dumps(data)
        row.updated_at = datetime.utcnow().isoformat()
    db.session.commit()
    return jsonify({"status": "saved"})
from flask import render_template

@app.route("/dashboard")
def dashboard_page():
    return render_template("dashboard.html")

@app.route("/users")
def users_page():
    return render_template("users.html")

@app.route("/logs")
def logs_page():
    return render_template("logs.html")

@app.route("/status")
def status_page():
    return render_template("status.html")

@app.route("/settings")
def settings_page():
    return render_template("settings.html")

@app.route("/test")
def test_page():
    return render_template("test.html")

@app.route("/api/logs")
def api_logs():
    logs = SMSLog.query.order_by(SMSLog.id.desc()).all()
    return jsonify([
        {"timestamp": l.timestamp, "sender": l.sender, "message": l.message}
        for l in logs
    ])

@app.route("/api/status")
def api_status():
    s = DeviceStatus.query.order_by(DeviceStatus.id.desc()).first()
    if not s:
        return jsonify({"online": False, "last_signal": None, "timestamp": None})
    return jsonify({
        "online": s.online,
        "last_signal": s.last_signal,
        "timestamp": s.timestamp
    })

@app.route("/api/config", methods=["GET"])
def api_get_config():
    cfg = RTUConfig.query.get(1)
    if not cfg:
        return jsonify({})
    return jsonify(json.loads(cfg.json_config))

@app.route("/api/config", methods=["POST"])
def api_save_config():
    data = request.get_json()
    row = RTUConfig.query.get(1)
    if not row:
        row = RTUConfig(id=1, json_config=json.dumps(data), updated_at=datetime.utcnow().isoformat())
        db.session.add(row)
    else:
        row.json_config = json.dumps(data)
        row.updated_at = datetime.utcnow().isoformat()
    db.session.commit()
    return jsonify({"status": "saved"})

@app.route("/api/send", methods=["POST"])
def api_send():
    cmd = request.json["cmd"]
    send_sms(RTU_PHONE, cmd)
    return jsonify({"status": "sent", "command": cmd})

from flask import redirect, url_for
@app.route('/')
def index():
    return redirect(url_for('dashboard_page'))


import json
from datetime import datetime
@app.route('/api/config', methods=['GET'])
def api_config_get():
    cfg = RTUConfig.query.get(1)
    if not cfg:
        return jsonify({})
    return jsonify(json.loads(cfg.json_config))
@app.route('/api/config', methods=['POST'])
def api_config_post():
    data = request.get_json()
    row = RTUConfig.query.get(1)
    if not row:
        row = RTUConfig(id=1, json_config=json.dumps(data), updated_at=datetime.utcnow().isoformat())
        db.session.add(row)
    else:
        row.json_config = json.dumps(data)
        row.updated_at = datetime.utcnow().isoformat()
    db.session.commit()
    return jsonify({'status': 'saved'})
@app.route('/api/status')
def api_status_fallback():
    s = DeviceStatus.query.order_by(DeviceStatus.id.desc()).first()
    if not s:
        return jsonify({'online': False, 'last_signal': None, 'timestamp': None})
    return jsonify({'online': s.online, 'last_signal': s.last_signal, 'timestamp': s.timestamp})

