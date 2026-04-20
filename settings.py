import os

class Settings:
    # MySQL
    MYSQL_HOST = os.environ.get("MYSQL_HOST", "localhost")
    MYSQL_PORT = int(os.environ.get("MYSQL_PORT", 3306))
    MYSQL_USER = os.environ.get("MYSQL_USER", "root")
    MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD", "111111a!")
    MYSQL_DB = os.environ.get("MYSQL_DB", "phone_control")

    SECRET_KEY = os.environ.get("SECRET_KEY", "frp-phone-control-secret-key-2024")
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # frps
    FRPS_ADDR = os.environ.get("FRPS_ADDR", "47.243.209.93")
    FRPS_PORT = int(os.environ.get("FRPS_PORT", 7000))
    FRPS_TOKEN = os.environ.get("FRPS_TOKEN", "frp_control_token_2024")
    FRPS_DASHBOARD_URL = os.environ.get("FRPS_DASHBOARD_URL", "http://127.0.0.1:7500")
    FRPS_DASHBOARD_USER = os.environ.get("FRPS_DASHBOARD_USER", "admin")
    FRPS_DASHBOARD_PASS = os.environ.get("FRPS_DASHBOARD_PASS", "frpadmin2024")

    # Port range for phones
    PORT_RANGE_START = 20000
    PORT_RANGE_END = 20499

    @property
    def SQLALCHEMY_DATABASE_URI(self):
        return (f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}"
                f"@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DB}?charset=utf8mb4")

cfg = Settings()
