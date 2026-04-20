from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

db = SQLAlchemy()


class AdminUser(db.Model):
    __tablename__ = "admin_users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)


class AppAccount(db.Model):
    __tablename__ = "app_accounts"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    assigned_port = db.Column(db.Integer, unique=True, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    connections = db.relationship("DeviceConnection", backref="account", lazy=True)


class DeviceConnection(db.Model):
    __tablename__ = "device_connections"
    id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey("app_accounts.id"), nullable=False)
    device_id = db.Column(db.String(64), unique=True, nullable=False)
    device_name = db.Column(db.String(128), default="")
    last_heartbeat = db.Column(db.DateTime, default=datetime.utcnow)
    is_online = db.Column(db.Boolean, default=False)
    frpc_status = db.Column(db.String(20), default="offline")

    commands = db.relationship("Command", backref="connection", lazy=True)


class Command(db.Model):
    __tablename__ = "commands"
    id = db.Column(db.Integer, primary_key=True)
    connection_id = db.Column(db.Integer, db.ForeignKey("device_connections.id"), nullable=False)
    command = db.Column(db.String(512), nullable=False)
    result = db.Column(db.Text, nullable=True)
    status = db.Column(db.SmallInteger, default=0)  # 0=pending 1=dispatched 2=done 3=failed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    executed_at = db.Column(db.DateTime, nullable=True)
