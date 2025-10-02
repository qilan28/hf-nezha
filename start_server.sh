#!/bin/bash
source /opt/venv/bin/activate
nohup python /data/app.py > /data/app.log 2>&1 &
jupyter lab \
    --ip=0.0.0.0 \
    --port=7860 \
    --no-browser \
    --allow-root \
    --notebook-dir=/data \
    --NotebookApp.token=${JUPYTER_TOKEN} \
    --ServerApp.disable_check_xsrf=True
