#!/usr/bin/env python3
"""Initialize database and create default admin."""
import sys
sys.path.insert(0, '/root/phone_control')

import settings
settings.cfg.FRPS_ADDR = "47.243.209.93"

from app import app, db
from models import AdminUser

def main():
    with app.app_context():
        db.create_all()
        print("[init] Tables created.")

        if AdminUser.query.filter_by(username="admin").first():
            print("[init] Admin user 'admin' already exists.")
        else:
            admin = AdminUser(username="admin")
            admin.set_password("admin123")
            db.session.add(admin)
            db.session.commit()
            print("[init] Admin created: admin / admin123")

    print("[init] Done. Run 'bash start.sh' to start the server on :10086")

if __name__ == "__main__":
    main()
