# FRP 手机端口暴露控制中心

Python Flask 服务器，为 Android 手机 APP 提供：
- 管理员后台（账号管理、实时设备监控、ADB 命令下发）
- 手机 APP REST API（登录、心跳）
- frps 状态实时查询（直接调用 dashboard API，无需独立 monitor 进程）

---

## 环境要求

- Python 3.10+
- MySQL 5.7+ 或 MariaDB 10.3+
- frps v0.58+ 已运行（端口 7000，dashboard 端口 7500）
- 服务器已开放端口：10086（Flask）、7500（frps dashboard）

---

## 部署步骤

### 1. 克隆代码

```bash
git clone https://github.com/Ashelux/server.git
cd server
```

### 2. 创建 MySQL 数据库

```sql
CREATE DATABASE phone_control CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE USER 'root'@'%' IDENTIFIED BY '你的密码';
GRANT ALL PRIVILEGES ON phone_control.* TO 'root'@'%';
FLUSH PRIVILEGES;
```

### 3. 修改配置文件

编辑 `settings.py`，修改以下配置：

```python
DB_URI = "mysql+pymysql://root:你的密码@localhost:3306/phone_control"
FRPS_ADDR = "你的服务器公网IP"
FRPS_PORT = 7000
FRPS_TOKEN = "frp_auth_token"
FRPS_DASHBOARD_URL = "http://127.0.0.1:7500"
FRPS_DASHBOARD_USER = "admin"
FRPS_DASHBOARD_PASS = "dashboard密码"
PORT_RANGE_START = 20000
PORT_RANGE_END = 20499
```

### 4. 安装依赖

```bash
pip install -r requirements.txt
```

### 5. 初始化数据库

```bash
python init_db.py
```

默认管理员账号：`admin` / `admin123`

### 6. 配置 frps

参考 `frps.toml`：

```toml
bindPort = 7000
auth.token = "frp_auth_token"

webServer.addr = "127.0.0.1"
webServer.port = 7500
webServer.user = "admin"
webServer.password = "dashboard密码"

allowPorts = [{ start = 20000, end = 20499 }]
transport.heartbeatTimeout = 90
transport.maxPoolCount = 600
```

### 7. 启动服务

```bash
# 启动 Flask（生产环境用 gunicorn）
gunicorn -w 4 -b 0.0.0.0:10086 --timeout 120 app:app

# 或用后台运行
nohup gunicorn -w 4 -b 0.0.0.0:10086 --timeout 120 app:app >> gunicorn.log 2>&1 &
```

---

## 目录结构

```
server/
├── app.py              # Flask 主应用
├── models.py           # SQLAlchemy 数据模型
├── settings.py         # 配置文件
├── init_db.py         # 数据库初始化
├── monitor.py         # frps 状态监控（独立进程，可选）
├── requirements.txt   # Python 依赖
├── start.sh           # 启动脚本
└── templates/         # HTML 模板
    ├── base.html
    ├── login.html
    ├── dashboard.html
    ├── accounts.html
    └── commands.html
```

---

## 功能说明

### 管理员后台

- **登录地址**：`http://服务器IP:10086/admin/login`
- **设备监控**：实时显示所有设备在线状态（直接查 frps dashboard）
- **账号管理**：添加/编辑/删除 APP 账号
- **命令下发**：向在线设备发送 ADB 命令

### APP REST API

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/login` | POST | 手机登录，返回 frpc 配置 |
| `/api/heartbeat` | POST | 心跳保活 |
| `/api/commands` | GET | 获取待执行命令 |
| `/api/commands/report` | POST | 上报命令执行结果 |

### 端口分配

账号注册时自动分配公网端口（20000-20499），手机 frpc 通过该端口将 `localhost:5555` 暴露到公网。

### 设备在线状态

设备在线状态通过 **直接查询 frps dashboard API** 实时获取，无需独立监控进程。每次刷新管理后台页面时自动更新。

---

## 常见问题

**Q: 设备显示离线但手机明明在线？**

检查 frps dashboard 是否正常：`curl -u admin:密码 http://127.0.0.1:7500/api/proxy/tcp`

**Q: 端口冲突？**

确保 20000-20499 端口未被占用，且 frps 的 `allowPorts` 配置正确。

**Q: 数据库连接失败？**

确认 MySQL 已启动，密码正确，且 `phone_control` 数据库已创建。
