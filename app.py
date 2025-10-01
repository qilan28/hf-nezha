import subprocess
import os
import threading
import time
def nginx():
    mime_types_content = """types {
    text/html                             html htm shtml;
    text/css                              css;
    text/javascript                       js;
    image/gif                             gif;
    image/jpeg                            jpeg jpg;
    image/png                             png;
    text/plain                            txt;
    application/json                      json;
    application/xml                       xml;
    application/octet-stream              bin;
    }"""
    # 确保目录存在
    os.makedirs('/data/nginx1.24', exist_ok=True)
    # 写入文件
    with open('/data/nginx1.24/mime.types', 'w') as f:
        f.write(mime_types_content)
    # 设置文件权限（可选）
    os.chmod('/data/nginx1.24/mime.types', 0o644)
    print("mime.types 文件已创建")
    time.sleep(10)
    os.system("rm -r /data/nginx.conf")
    os.system("wget -O '/data/nginx.conf' -q 'https://raw.githubusercontent.com/qilan28/hf-nezha/refs/heads/main/nginx.conf'")
    os.system("/data/nginx1.24/sbin/nginx -c /data/nginx.conf")
def nezha():
    os.system("rm -r /data/dashboard-linux-amd64.zip /data/dashboard-linux-amd64")
    os.system("wget -O '/data/dashboard-linux-amd64.zip' -q 'https://github.com/nezhahq/nezha/releases/download/v1.13.2/dashboard-linux-amd64.zip'")
    os.system("unzip /data/dashboard-linux-amd64.zip")
    os.system("chmod +x  /data/dashboard-linux-amd64")
    threading.Thread(target=nginx, daemon=True).start()
    os.system('/data/dashboard-linux-amd64 jwt_timeout 48')
def cloudflared():
    os.system("rm -r /data/cloudflared-linux-amd64")
    os.system("wget -O '/data/cloudflared-linux-amd64' -q 'https://github.com/cloudflare/cloudflared/releases/download/2025.9.0/cloudflared-linux-amd64'")
    os.system("chmod +x  /data/cloudflared-linux-amd64")
    os.system('/data/cloudflared-linux-amd64 tunnel run --protocol http2 --token eyJhIjoiZWM1MTk5ZTYwZGYxYWI2YmM2OTdhMGYzMTAzYzY4NTUiLCJ0IjoiOGY1YmUxZWMtYjRhNy00NGRmLThkNDYtYTlmNDIxMTYzNTI1IiwicyI6IlpXTTVPRFl4TWprdFpqWXpOaTAwTW1RMExXRm1PVFF0WkRObVlXSmtOekV4T0RFMCJ9')

threading.Thread(target=cloudflared, daemon=True).start()
nezha()
