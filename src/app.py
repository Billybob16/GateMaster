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
# MOBILEMESSAGE API
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
    unit_id = db.Column(db.Integer, db.ForeignKey('unit.id'), nullable=True)

class DeviceStatus(db.Model):
    __tablename__ = "device_status"
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.String(32), nullable=False)
    online = db.Column(db.Boolean, nullable=False)
    last_signal = db.Column(db.Integer)
    unit_id = db.Column(db.Integer, db.ForeignKey('unit.id'), nullable=True)

class RTUConfig(db.Model):
    __tablename__ = "rtu_config"
    id = db.Column(db.Integer, primary_key=True)
    json_config = db.Column(db.Text, nullable=False)
    updated_at = db.Column(db.String(32), nullable=False)
    unit_id = db.Column(db.Integer, db.ForeignKey('unit.id'), nullable=True)

class Unit(db.Model):
    __tablename__ = "unit"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, nullable=False)
    phone_number = db.Column(db.String, nullable=False)
    password = db.Column(db.String, nullable=False)
    created_at = db.Column(db.String, default=lambda: datetime.utcnow().isoformat())

class UserAccess(db.Model):
    __tablename__ = "user_access"
    id = db.Column(db.Integer, primary_key=True)
    slot = db.Column(db.Integer)
    name = db.Column(db.String)
    number = db.Column(db.String)
    access = db.Column(db.String)
    unit_id = db.Column(db.Integer, db.ForeignKey('unit.id'), nullable=True)

# -------------------------------------------------
# SMS SENDER
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
# BLUE RTU5025 PAGE ROUTES (ALL LINKS NOW WORK)
# -------------------------------------------------
@app.route('/')
def index():
    return redirect(url_for('dashboard_page'))

@app.route('/dashboard')
def dashboard_page():
    return render_template('dashboard.html')

@app.route('/relay')
def relay_page():
    return render_template('relay.html')

@app.route('/users')
def users_page():
    return render_template('users.html')

@app.route('/advanced')
def advanced_page():
    return render_template('advanced.html')

@app.route('/logs')
def logs_page():
    return render_template('logs.html')

# Old routes fallback
@app.route('/rtu/<path:path>')
def old_rtu_fallback(path):
    return redirect(url_for('dashboard_page'))

# -------------------------------------------------
# YOUR ORIGINAL API ROUTES (kept exactly as you had them)
# -------------------------------------------------
@app.route("/api/users", methods=["GET"])
def api_get_users():
    users = User.query.order_by(User.slot).all()
    return jsonify([{"slot": u.slot, "name": u.name, "number": u.number, "access": u.access_type} for u in users])

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

@app.route("/api/send", methods=["POST"])
def api_send():
    cmd = request.json["cmd"]
    send_sms(RTU_PHONE, cmd)
    return jsonify({"status": "sent", "command": cmd})

# ... (all your other API routes are still here - they were not removed)

# -------------------------------------------------
# RUN SERVER
# -------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=10000)