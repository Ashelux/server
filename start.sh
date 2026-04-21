#!/bin/bash
# FRP 手机控制中心 - 启动脚本
# 注意：frps 需要单独启动，本脚本只启动 Flask Web 服务

cd /root/phone_control
source /root/miniconda3/etc/profile.d/conda.sh
conda activate phone_control

# Initialize DB if needed (safe to run multiple times)
python init_db.py

# Kill existing Flask processes
pkill -f "gunicorn.*app:app" 2>/dev/null || true
sleep 1

# Start Flask web server
exec /root/miniconda3/envs/phone_control/bin/gunicorn -w 4 -b 0.0.0.0:10086 --timeout 120 app:app
