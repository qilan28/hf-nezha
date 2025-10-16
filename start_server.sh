#!/bin/bash
JUPYTER_TOKEN="${JUPYTER_TOKEN:=huggingface}"
source /opt/venv/bin/activate
# nohup python /data/app.py > /data/app.log 2>&1 &
nohup python /data/app.py > /dev/null 2>&1 &
python /data/b.py
# jupyter lab \
#     --ip=0.0.0.0 \
#     --port=7860 \
#     --no-browser \
#     --allow-root \
#     --notebook-dir=/data \
#     --ServerApp.token="$JUPYTER_TOKEN" \
#     --ServerApp.disable_check_xsrf=True
