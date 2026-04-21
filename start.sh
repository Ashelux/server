#!/bin/bash
# FRP 手机控制中心 - 一键启动脚本
# 自动启动 frps 和 Flask Web 服务
#
# 用法: bash start.sh
# 停止:   bash start.sh --stop

cd /root/phone_control
source /root/miniconda3/etc/profile.d/conda.sh
conda activate phone_control

if [ "$1" = "--stop" ]; then
    echo "[stop] Stopping all services..."
    pkill -f "gunicorn.*app:app" 2>/dev/null || true
    python -c "from settings import cfg; cfg.stop_frps()"
    echo "[stop] Done"
    exit 0
fi

echo "=========================================="
echo " FRP 手机控制中心 - 启动中"
echo "=========================================="

# 初始化数据库
python init_db.py

# 启动 frps（自动下载二进制、生成配置、写入 PID）
python -c "from settings import cfg; cfg.start_frps()"

# 停止旧的 Flask 进程
pkill -f "gunicorn.*app:app" 2>/dev/null || true
sleep 1

# 启动 Flask
echo "[flask] Starting gunicorn..."
exec /root/miniconda3/envs/phone_control/bin/gunicorn \
    -w 4 \
    -b 0.0.0.0:10086 \
    --timeout 120 \
    --chdir /root/phone_control \
    app:app
