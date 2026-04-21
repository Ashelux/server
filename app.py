import os
import base64
import json
import requests
from datetime import datetime, timedelta
from functools import wraps

from flask import Flask, render_template, request, redirect, url_for, jsonify, session
from flask_sqlalchemy import SQLAlchemy

import settings
from models import db, AdminUser, AppAccount, DeviceConnection, Command

app = Flask(__name__)
app.config["SQLALCHEMY_DATABASE_URI"] = settings.cfg.SQLALCHEMY_DATABASE_URI
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = settings.cfg.SQLALCHEMY_TRACK_MODIFICATIONS
app.config["SECRET_KEY"] = settings.cfg.SECRET_KEY
db.init_app(app)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if "admin_id" not in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated


def get_used_ports():
    """Return set of assigned ports currently in use."""
    return {acc.assigned_port for acc in AppAccount.query.all()}


def allocate_port():
    """Allocate a free port from the range."""
    used = get_used_ports()
    for port in range(settings.cfg.PORT_RANGE_START, settings.cfg.PORT_RANGE_END + 1):
        if port not in used:
            return port
    return None


# ─── Admin Web Routes ─────────────────────────────────────────────────────────

@app.route("/admin/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = AdminUser.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session["admin_id"] = user.id
            session["admin_username"] = user.username
            return redirect(url_for("dashboard"))
        return render_template("login.html", error="用户名或密码错误")
    return render_template("login.html")


@app.route("/admin/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


@app.route("/admin/dashboard")
@login_required
def dashboard():
    connections = DeviceConnection.query.order_by(DeviceConnection.last_heartbeat.desc()).all()
    return render_template("dashboard.html",
                           connections=connections,
                           username=session.get("admin_username", ""))


@app.route("/admin/accounts")
@login_required
def accounts():
    app_accounts = AppAccount.query.order_by(AppAccount.id.desc()).all()
    return render_template("accounts.html",
                           accounts=app_accounts,
                           username=session.get("admin_username", ""))


@app.route("/admin/accounts/add", methods=["POST"])
@login_required
def add_account():
    username = request.form.get("username", "").strip()
    password = request.form.get("password", "").strip()
    if not username or not password:
        return redirect(url_for("accounts"))
    if AppAccount.query.filter_by(username=username).first():
        return redirect(url_for("accounts"))
    port = allocate_port()
    if not port:
        return "无可用端口", 500
    acc = AppAccount(username=username, assigned_port=port)
    acc.set_password(password)
    db.session.add(acc)
    db.session.commit()
    return redirect(url_for("accounts"))


@app.route("/admin/accounts/<int:aid>/edit", methods=["POST"])
@login_required
def edit_account(aid):
    acc = AppAccount.query.get_or_404(aid)
    new_password = request.form.get("password", "").strip()
    active = request.form.get("is_active", "1") == "1"
    acc.is_active = active
    if new_password:
        acc.set_password(new_password)
    db.session.commit()
    return redirect(url_for("accounts"))


@app.route("/admin/accounts/<int:aid>/delete", methods=["POST"])
@login_required
def delete_account(aid):
    acc = AppAccount.query.get_or_404(aid)
    # 删除关联的连接记录
    DeviceConnection.query.filter_by(account_id=aid).delete()
    db.session.delete(acc)
    db.session.commit()
    return redirect(url_for("accounts"))


@app.route("/admin/commands/send", methods=["POST"])
@login_required
def send_command():
    device_id = request.form.get("device_id", "").strip()
    command = request.form.get("command", "").strip()
    if not device_id or not command:
        return redirect(url_for("dashboard"))
    conn = DeviceConnection.query.filter_by(device_id=device_id).first()
    if not conn:
        return redirect(url_for("dashboard"))
    cmd = Command(connection_id=conn.id, command=command)
    db.session.add(cmd)
    db.session.commit()
    return redirect(url_for("dashboard"))


@app.route("/admin/commands/<device_id>")
@login_required
def command_history(device_id):
    conn = DeviceConnection.query.filter_by(device_id=device_id).first_or_404()
    commands = Command.query.filter_by(connection_id=conn.id).order_by(Command.created_at.desc()).limit(50).all()
    return render_template("commands.html",
                           commands=commands,
                           device_name=conn.device_name,
                           username=session.get("admin_username", ""))


@app.route("/admin/api/status")
@login_required
def api_status():
    # 直接从 frps dashboard API 获取实时状态，不依赖本地数据库
    import base64, requests
    FRPS_URL = settings.cfg.FRPS_DASHBOARD_URL
    creds = base64.b64encode(
        f"{settings.cfg.FRPS_DASHBOARD_USER}:{settings.cfg.FRPS_DASHBOARD_PASS}".encode()
    ).decode()
    headers = {"Authorization": f"Basic {creds}"}

    port_status = {}
    try:
        resp = requests.get(f"{FRPS_URL}/api/proxy/tcp", headers=headers, timeout=5)
        if resp.status_code == 200:
            for p in resp.json().get("proxies", []):
                conf = p.get("conf") or {}
                rport = conf.get("remotePort")
                if rport:
                    port_status[rport] = p.get("status", "offline")
    except Exception as e:
        print(f"[api_status] frps API error: {e}")

    connections = DeviceConnection.query.order_by(DeviceConnection.last_heartbeat.desc()).all()
    data = [{
        "device_id": c.device_id,
        "device_name": c.device_name,
        "username": c.account.username if c.account else "",
        "assigned_port": c.account.assigned_port if c.account else 0,
        "is_online": port_status.get(c.account.assigned_port, "offline") == "online",
        "frpc_status": port_status.get(c.account.assigned_port, "offline"),
        "last_heartbeat": c.last_heartbeat.strftime("%Y-%m-%d %H:%M:%S") if c.last_heartbeat else "",
    } for c in connections]
    return jsonify({"code": 200, "data": data})


# ─── APP REST API ─────────────────────────────────────────────────────────────

@app.route("/api/login", methods=["POST"])
def api_login():
    data = request.get_json() or {}
    username = data.get("username", "").strip()
    password = data.get("password", "")
    device_id = data.get("device_id", "").strip()
    device_name = data.get("device_name", "").strip()

    if not username or not password:
        return jsonify({"code": 400, "msg": "缺少参数"})

    acc = AppAccount.query.filter_by(username=username, is_active=True).first()
    if not acc or not acc.check_password(password):
        return jsonify({"code": 401, "msg": "账号或密码错误"})

    # 获取或创建设备连接
    conn = DeviceConnection.query.filter_by(device_id=device_id).first()
    if not conn:
        conn = DeviceConnection(
            account_id=acc.id,
            device_id=device_id,
            device_name=device_name
        )
        db.session.add(conn)
    else:
        conn.account_id = acc.id
        conn.device_name = device_name
    db.session.commit()

    frpc_config = {
        "server_addr": settings.cfg.FRPS_ADDR,
        "server_port": settings.cfg.FRPS_PORT,
        "token": settings.cfg.FRPS_TOKEN,
        "remote_port": acc.assigned_port,
        "local_port": 5555,
        "proxy_name": f"phone_{acc.id}"
    }
    return jsonify({
        "code": 200,
        "msg": "OK",
        "token": f"device_{conn.id}_{conn.device_id}",
        "frpc_config": frpc_config,
        "account_id": acc.id
    })


@app.route("/api/heartbeat", methods=["POST"])
def api_heartbeat():
    data = request.get_json() or {}
    device_id = data.get("device_id", "").strip()
    if not device_id:
        return jsonify({"code": 400, "msg": "缺少device_id"})

    conn = DeviceConnection.query.filter_by(device_id=device_id).first()
    if not conn:
        return jsonify({"code": 404, "msg": "设备未注册"})

    conn.last_heartbeat = datetime.now()
    db.session.commit()
    return jsonify({"code": 200, "msg": "OK"})


@app.route("/api/test_connection", methods=["GET"])
def api_test_connection():
    """手机可以用这个接口检测是否能访问服务器"""
    import socket
    try:
        # 检测本机端口 connectivity
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(3)
        result = s.connect_ex(('127.0.0.1', 7000))
        s.close()
        return jsonify({
            "code": 200,
            "server_reachable": result == 0,
            "server_ip": settings.cfg.FRPS_ADDR,
            "server_port": settings.cfg.FRPS_PORT,
            "token": settings.cfg.FRPS_TOKEN
        })
    except Exception as e:
        return jsonify({"code": 500, "msg": str(e)})


@app.route("/api/commands", methods=["GET"])
def api_get_commands():
    device_id = request.args.get("device_id", "").strip()
    if not device_id:
        return jsonify({"code": 400, "msg": "缺少device_id"})

    conn = DeviceConnection.query.filter_by(device_id=device_id).first()
    if not conn:
        return jsonify({"code": 404, "msg": "设备未注册", "data": []})

    cmds = Command.query.filter(
        Command.connection_id == conn.id,
        Command.status == 0
    ).order_by(Command.created_at).all()
    result = [{"id": c.id, "command": c.command} for c in cmds]
    for c in cmds:
        c.status = 1
    db.session.commit()
    return jsonify({"code": 200, "data": result})


@app.route("/api/commands/report", methods=["POST"])
def api_report_result():
    data = request.get_json() or {}
    command_id = data.get("command_id")
    result = data.get("result", "")
    status = data.get("status", 2)

    if command_id is None:
        return jsonify({"code": 400, "msg": "缺少command_id"})

    cmd = Command.query.get(command_id)
    if not cmd:
        return jsonify({"code": 404, "msg": "命令不存在"})

    cmd.result = result
    cmd.status = status
    cmd.executed_at = datetime.now()
    db.session.commit()
    return jsonify({"code": 200, "msg": "OK"})


# ─── Init ─────────────────────────────────────────────────────────────────────

def init_db():
    """Create tables and default admin."""
    with app.app_context():
        db.create_all()
        if not AdminUser.query.filter_by(username="admin").first():
            admin = AdminUser(username="admin")
            admin.set_password("admin123")
            db.session.add(admin)
            db.session.commit()
            print("[init] Default admin created: admin / admin123")


if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=10086, debug=False)
