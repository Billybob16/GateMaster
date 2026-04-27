Write-Host "============================================"
Write-Host "   BUILDING FULL GATEMASTER V3 UI PACK"
Write-Host "============================================"

# Ensure folders exist
New-Item -ItemType Directory -Force -Path "templates" | Out-Null
New-Item -ItemType Directory -Force -Path "src" | Out-Null
New-Item -ItemType Directory -Force -Path "database" | Out-Null

# ---------------------------
# layout.html
# ---------------------------
@"
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>GateMaster V3</title>
<style>
body { margin:0; font-family:Arial; background:#111; color:#eee; }
.sidebar { width:220px; background:#000; height:100vh; position:fixed; top:0; left:0; padding:20px; }
.sidebar a { display:block; padding:10px; color:#0f0; text-decoration:none; margin-bottom:5px; }
.sidebar a:hover { background:#0f0; color:#000; }
.header { margin-left:220px; padding:15px; background:#222; color:#0f0; }
.content { margin-left:220px; padding:20px; }
</style>
</head>
<body>
{% include 'sidebar.html' %}
<div class="header">GateMaster V3 Control Panel</div>
<div class="content">
{% block content %}{% endblock %}
</div>
</body>
</html>
"@ | Out-File "templates/layout.html" -Encoding utf8

# ---------------------------
# sidebar.html
# ---------------------------
@"
<div class="sidebar">
<h3 style="color:#0f0;">MENU</h3>
<a href="/dashboard">Dashboard</a>
<a href="/devices">Devices</a>
<a href="/events">Event Log</a>
<a href="/access">Access Manager</a>
<a href="/settings">Settings</a>
<a href="/users">Users</a>
<a href="/logout">Logout</a>
</div>
"@ | Out-File "templates/sidebar.html" -Encoding utf8

# ---------------------------
# device_detail.html
# ---------------------------
@"
{% extends 'layout.html' %}
{% block content %}
<h2>Device: {{ device.name }}</h2>
<p>Phone: {{ device.phone }}</p>
<p>Location: {{ device.location }}</p>

<h3>Access List</h3>
<ul>
{% for a in access %}
<li>{{ a.slot }} - {{ a.name }} ({{ a.number }})</li>
{% endfor %}
</ul>

<a href="/devices">Back</a>
{% endblock %}
"@ | Out-File "templates/device_detail.html" -Encoding utf8

# ---------------------------
# access_manager.html
# ---------------------------
@"
{% extends 'layout.html' %}
{% block content %}
<h2>Access Manager</h2>
<p>Select a device to manage access.</p>
<ul>
{% for d in devices %}
<li><a href="/access/{{ d.id }}">{{ d.name }}</a></li>
{% endfor %}
</ul>
{% endblock %}
"@ | Out-File "templates/access_manager.html" -Encoding utf8

# ---------------------------
# event_log.html
# ---------------------------
@"
{% extends 'layout.html' %}
{% block content %}
<h2>Event Log</h2>
<ul>
{% for e in events %}
<li>[{{ e.timestamp }}] {{ e.level }} - {{ e.message }}</li>
{% endfor %}
</ul>
{% endblock %}
"@ | Out-File "templates/event_log.html" -Encoding utf8

# ---------------------------
# settings.html
# ---------------------------
@"
{% extends 'layout.html' %}
{% block content %}
<h2>Settings</h2>
<p>System settings will go here.</p>
{% endblock %}
"@ | Out-File "templates/settings.html" -Encoding utf8

# ---------------------------
# users.html
# ---------------------------
@"
{% extends 'layout.html' %}
{% block content %}
<h2>User Management</h2>
<ul>
{% for u in users %}
<li>{{ u.email }} ({{ u.role }})</li>
{% endfor %}
</ul>
{% endblock %}
"@ | Out-File "templates/users.html" -Encoding utf8

# ---------------------------
# WRITE FULL APP.PY
# ---------------------------
@"
import os
if os.environ.get("FLASK_RUN_FROM_CLI") != "true":
    import eventlet
    eventlet.monkey_patch()

from flask import Flask, render_template, request, redirect, url_for, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime

app = Flask(__name__)
app.secret_key = "supersecret"

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database/gatemaster_v3.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)
migrate = Migrate(app, db)

class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(32), default="admin")

class RTUDevice(db.Model):
    __tablename__ = "rtu_devices"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255), nullable=False)
    phone = db.Column(db.String(32), nullable=False)
    location = db.Column(db.String(255))

class AccessEntry(db.Model):
    __tablename__ = "access_entries"
    id = db.Column(db.Integer, primary_key=True)
    device_id = db.Column(db.Integer, db.ForeignKey("rtu_devices.id"))
    name = db.Column(db.String(255), nullable=False)
    number = db.Column(db.String(32), nullable=False)
    slot = db.Column(db.Integer, nullable=False)

class EventLog(db.Model):
    __tablename__ = "event_log"
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.String(32), nullable=False)
    level = db.Column(db.String(16), nullable=False)
    message = db.Column(db.String(255), nullable=False)
    details = db.Column(db.Text)

def log_event(level, message, details=None):
    entry = EventLog(
        timestamp=datetime.utcnow().isoformat(),
        level=level,
        message=message,
        details=details
    )
    db.session.add(entry)
    db.session.commit()

@app.route("/")
def home():
    if "user_id" in session:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))

@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        if email == "admin@master.com" and password == "1234":
            session["user_id"] = 1
            session["role"] = "superadmin"
            log_event("INFO","Admin login",f"email={email}")
            return redirect(url_for("dashboard"))

        return "Invalid login"

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))

    devices = RTUDevice.query.all()
    events = EventLog.query.order_by(EventLog.id.desc()).limit(10).all()

    return render_template("dashboard.html", devices=devices, events=events)

@app.route("/devices")
def devices_page():
    if "user_id" not in session:
        return redirect(url_for("login"))

    devices = RTUDevice.query.all()
    return render_template("devices.html", devices=devices)

@app.route("/devices/add", methods=["POST"])
def devices_add():
    if "user_id" not in session:
        return redirect(url_for("login"))

    name = request.form.get("name")
    phone = request.form.get("phone")
    location = request.form.get("location")

    d = RTUDevice(name=name, phone=phone, location=location)
    db.session.add(d)
    db.session.commit()

    log_event("INFO","Device added",f"name={name},phone={phone}")
    return redirect(url_for("devices_page"))

@app.route("/devices/<int:device_id>")
def device_detail(device_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    device = RTUDevice.query.get(device_id)
    access = AccessEntry.query.filter_by(device_id=device_id).all()

    return render_template("device_detail.html", device=device, access=access)

@app.route("/access")
def access_manager():
    if "user_id" not in session:
        return redirect(url_for("login"))

    devices = RTUDevice.query.all()
    return render_template("access_manager.html", devices=devices)

@app.route("/access/<int:device_id>")
def access_for_device(device_id):
    if "user_id" not in session:
        return redirect(url_for("login"))

    device = RTUDevice.query.get(device_id)
    access = AccessEntry.query.filter_by(device_id=device_id).all()

    return render_template("device_detail.html", device=device, access=access)

@app.route("/events")
def events_page():
    if "user_id" not in session:
        return redirect(url_for("login"))

    events = EventLog.query.order_by(EventLog.id.desc()).all()
    return render_template("event_log.html", events=events)

@app.route("/settings")
def settings_page():
    if "user_id" not in session:
        return redirect(url_for("login"))

    return render_template("settings.html")

@app.route("/users")
def users_page():
    if "user_id" not in session:
        return redirect(url_for("login"))

    users = User.query.all()
    return render_template("users.html", users=users)

@app.route("/api/devices", methods=["GET"])
def api_devices():
    devices = RTUDevice.query.all()
    return jsonify([
        {"id":d.id,"name":d.name,"phone":d.phone,"location":d.location}
        for d in devices
    ])

@app.route("/api/access/<int:device_id>", methods=["GET"])
def api_access_list(device_id):
    entries = AccessEntry.query.filter_by(device_id=device_id).all()
    return jsonify([
        {"id":e.id,"name":e.name,"number":e.number,"slot":e.slot}
        for e in entries
    ])

@app.route("/api/access/<int:device_id>", methods=["POST"])
def api_access_add(device_id):
    data = request.json
    entry = AccessEntry(
        device_id=device_id,
        name=data["name"],
        number=data["number"],
        slot=data["slot"]
    )
    db.session.add(entry)
    db.session.commit()

    log_event("INFO","Access added",f"device_id={device_id},number={data['number']}")
    return jsonify({"status":"ok"})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000, debug=True)
"@ | Out-File "src/app.py" -Encoding utf8

Write-Host "UI templates and app.py written."

Write-Host "Resetting database..."
Remove-Item -Recurse -Force "migrations" -ErrorAction SilentlyContinue
Remove-Item -Force "database/gatemaster_v3.db" -ErrorAction SilentlyContinue

Write-Host "Rebuilding migrations..."
$env:FLASK_APP = "src/app.py"

flask db init
flask db migrate -m "ui build"
flask db upgrade

Write-Host "============================================"
Write-Host "   UI PACK INSTALLED — STARTING SERVER"
Write-Host "============================================"

python src/app.py
