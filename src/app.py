import eventlet
eventlet.monkey_patch()

from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime
import json
import os
import random

# -------------------------------------------------
# FLASK APP + DATABASE
# -------------------------------------------------
app = Flask(__name__)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database/rtu_config.db"
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

    id = db.Column(db.Integer, primary_primary=True)
    timestamp = db.Column(db.String(32), nullable=False)
    direction = db.Column(db.String(16), nullable=False)
    number = db.Column(db.String(32), nullable=False)
    message = db.Column(db.Text, nullable=False)


class DeviceStatus(db.Model):
    __tablename__ = "device_status"

    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.String(32), nullable=False)
    online = db.Column(db.Boolean, nullable=False)
    last_signal = db.Column(db.Integer)


# -------------------------------------------------
# RTU CONFIG STORAGE
# -------------------------------------------------
DB_PATH = "database/rtu_config.db"

def get_rtu_config():
    row = db.session.execute(db.text("SELECT json_config FROM rtu_config WHERE id = 1")).fetchone()
    return json.loads(row[0])

def save_rtu_config(cfg):
    db.session.execute(
        db.text("UPDATE rtu_config SET json_config = :cfg, updated_at = :ts WHERE id = 1"),
        {"cfg": json.dumps(cfg), "ts": datetime.utcnow().isoformat()}
    )
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


def send_welcome_sms(number, name):
    msg = (
        f"RJL Commercial has granted you access to their GSM Relay.\n"
        f"Hi {name}, your phone is now authorised for gate control.\n"
        f"Save this number in your contacts.\n"
        f"When you call it, the call will hang up automatically and the gate will open."
    )
    send_sms(number, msg)


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

    send_welcome_sms(data["number"], data["name"])

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
# RTU SETTINGS ROUTES (UNCHANGED)
# -------------------------------------------------
# (Your entire RTU settings section stays the same — it already works)
# I can clean it too if you want.


# -------------------------------------------------
# RUN SERVER
# -------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True)
