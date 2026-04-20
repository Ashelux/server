#!/usr/bin/env python3
"""
Standalone frps status monitor.
Polls frps dashboard API and updates device online status in MySQL.
Run as a separate process from the Flask app.
"""
import base64
import sys
import time
import requests
sys.path.insert(0, '/root/phone_control')

import settings
from app import app, db
from models import DeviceConnection

FRPS_URL = settings.cfg.FRPS_DASHBOARD_URL
FRPS_USER = settings.cfg.FRPS_DASHBOARD_USER
FRPS_PASS = settings.cfg.FRPS_DASHBOARD_PASS

def frps_auth_header():
    creds = base64.b64encode(
        f"{FRPS_USER}:{FRPS_PASS}".encode()
    ).decode()
    return {"Authorization": f"Basic {creds}"}

def sync_frps_status():
    try:
        resp = requests.get(f"{FRPS_URL}/api/proxy/tcp", headers=frps_auth_header(), timeout=5)
        if resp.status_code != 200:
            return
        proxies = resp.json().get("proxies", [])
    except Exception as e:
        print(f"[monitor] Failed to fetch frps proxies: {e}")
        return

    # Build port -> status map
    port_status = {}
    for p in proxies:
        conf = p.get("conf") or {}
        rport = conf.get("remotePort")
        status = p.get("status", "offline")
        if rport:
            port_status[rport] = status

    with app.app_context():
        for conn in DeviceConnection.query.all():
            acc = conn.account
            if acc:
                s = port_status.get(acc.assigned_port, None)
                if s is not None:
                    # Proxy found in frps - use its status
                    conn.frpc_status = s
                    conn.is_online = (s == "online")
                else:
                    # No proxy found in frps - device is definitely offline
                    # (frpc was connected but proxy no longer exists = disconnected)
                    conn.frpc_status = "offline"
                    conn.is_online = False
        db.session.commit()

def main():
    print("[monitor] Started. Polling every 10s...")
    while True:
        sync_frps_status()
        time.sleep(10)

if __name__ == "__main__":
    main()
