import os
import subprocess
import urllib.request
import tarfile
import shutil

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

    # frps binary auto-download
    FRPS_VERSION = "0.58.0"
    FRPS_BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    FRPS_BINARY_DIR = os.path.join(FRPS_BASE_DIR, "bin")
    FRPS_BINARY_PATH = os.path.join(FRPS_BINARY_DIR, "frps")
    FRPS_CONFIG_PATH = os.path.join(FRPS_BASE_DIR, "frps.toml")
    FRPS_PID_PATH = os.path.join(FRPS_BASE_DIR, "frps.pid")

    @property
    def SQLALCHEMY_DATABASE_URI(self):
        return (f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}"
                f"@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DB}?charset=utf8mb4")

    def generate_frps_config(self):
        return f"""bindPort = {self.FRPS_PORT}
auth.token = "{self.FRPS_TOKEN}"

webServer.addr = "127.0.0.1"
webServer.port = 7500
webServer.user = "{self.FRPS_DASHBOARD_USER}"
webServer.password = "{self.FRPS_DASHBOARD_PASS}"

allowPorts = [
  {{ start = {self.PORT_RANGE_START}, end = {self.PORT_RANGE_END} }}
]

transport.heartbeatTimeout = 90
transport.maxPoolCount = 600

log.to = "{self.FRPS_BASE_DIR}/logs/frps.log"
log.level = "info"
log.maxDays = 7
"""

    def ensure_frps_binary(self):
        """Download frps binary if not exists"""
        if os.path.exists(self.FRPS_BINARY_PATH):
            print(f"[frps] Binary already exists: {self.FRPS_BINARY_PATH}")
            return

        os.makedirs(self.FRPS_BINARY_DIR, exist_ok=True)
        url = f"https://github.com/fatedier/frp/releases/download/v{self.FRPS_VERSION}/frp_{self.FRPS_VERSION}_linux_amd64.tar.gz"
        tar_path = os.path.join(self.FRPS_BINARY_DIR, "frps.tar.gz")

        print(f"[frps] Downloading {url} ...")
        urllib.request.urlretrieve(url, tar_path)

        print(f"[frps] Extracting frps binary...")
        with tarfile.open(tar_path, "r:gz") as tar:
            members = [m for m in tar.getmembers() if m.name.endswith("/frps")]
            if not members:
                for m in tar.getmembers():
                    if "frps" in m.name and not m.name.endswith(".toml") and not m.name.endswith(".md"):
                        m.name = os.path.basename(m.name)
                        tar.extract(m, self.FRPS_BINARY_DIR)
                        os.rename(os.path.join(self.FRPS_BINARY_DIR, os.path.basename(m.name)),
                                  self.FRPS_BINARY_PATH)
                        break
            else:
                tar.extract(members[0], self.FRPS_BINARY_DIR)
                src = os.path.join(self.FRPS_BINARY_DIR, members[0].name)
                os.rename(src, self.FRPS_BINARY_PATH)

        os.chmod(self.FRPS_BINARY_PATH, 0o755)
        os.remove(tar_path)
        print(f"[frps] Binary installed: {self.FRPS_BINARY_PATH}")

    def is_frps_running(self):
        """Check if frps process is already running"""
        if not os.path.exists(self.FRPS_PID_PATH):
            return False
        try:
            with open(self.FRPS_PID_PATH) as f:
                pid = int(f.read().strip())
            os.kill(pid, 0)
            return True
        except (ValueError, FileNotFoundError, ProcessLookupError, PermissionError):
            return False

    def start_frps(self):
        """Ensure frps is running, download if needed"""
        if self.is_frps_running():
            print("[frps] Already running")
            return

        self.ensure_frps_binary()

        # Create logs dir
        logs_dir = os.path.join(self.FRPS_BASE_DIR, "logs")
        os.makedirs(logs_dir, exist_ok=True)

        # Write config
        config_content = self.generate_frps_config()
        with open(self.FRPS_CONFIG_PATH, "w") as f:
            f.write(config_content)
        print(f"[frps] Config written: {self.FRPS_CONFIG_PATH}")

        # Kill old process if exists
        if os.path.exists(self.FRPS_PID_PATH):
            try:
                with open(self.FRPS_PID_PATH) as f:
                    os.kill(int(f.read().strip()), 9)
            except:
                pass

        # Start frps
        log_file = open(os.path.join(logs_dir, "frps.log"), "a")
        proc = subprocess.Popen(
            [self.FRPS_BINARY_PATH, "-c", self.FRPS_CONFIG_PATH],
            stdout=log_file,
            stderr=subprocess.STDOUT,
            preexec_fn=os.setsid
        )

        # Save PID
        with open(self.FRPS_PID_PATH, "w") as f:
            f.write(str(proc.pid))

        print(f"[frps] Started, PID={proc.pid}")

        # Wait for frps to be ready
        import time
        import urllib.error
        for i in range(15):
            try:
                urllib.request.urlopen(f"http://127.0.0.1:{7500}", timeout=2)
                print("[frps] Ready")
                return
            except (urllib.error.URLError, urllib.error.HTTPError):
                time.sleep(1)
        print("[frps] Started (dashboard may take a moment)")

    def stop_frps(self):
        """Stop frps process"""
        if not os.path.exists(self.FRPS_PID_PATH):
            return
        try:
            with open(self.FRPS_PID_PATH) as f:
                pid = int(f.read().strip())
            os.kill(pid, 15)
            print(f"[frps] Stopped PID={pid}")
        except (ValueError, FileNotFoundError, ProcessLookupError, PermissionError):
            pass
        finally:
            if os.path.exists(self.FRPS_PID_PATH):
                os.remove(self.FRPS_PID_PATH)

cfg = Settings()
