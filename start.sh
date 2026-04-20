#!/bin/bash
cd /root/phone_control
source /root/miniconda3/etc/profile.d/conda.sh
conda activate phone_control

# Initialize DB if needed (safe to run multiple times)
python init_db.py

# Kill existing processes
pkill -f "gunicorn.*app:app" 2>/dev/null || true
pkill -f "monitor.py" 2>/dev/null || true
sleep 1

# Start monitor (background) - use full path to python
nohup /root/miniconda3/envs/phone_control/bin/python /root/phone_control/monitor.py >> /root/phone_control/monitor.log 2>&1 &
echo "[start] Monitor PID: $!"

# Start web server
exec /root/miniconda3/envs/phone_control/bin/gunicorn -w 4 -b 0.0.0.0:10086 --timeout 120 app:app
