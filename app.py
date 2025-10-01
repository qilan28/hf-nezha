import subprocess
import os
import threading
import time
import yaml
ARGO_DOMAIN = os.environ.get('ARGO_DOMAIN', '')        # Argo固定隧道域名,留空即使用临时隧道
ARGO_AUTH = os.environ.get('ARGO_AUTH', '')            # Argo固定隧道密钥,留空即使用临时隧道

agent_config = {
    'client_secret': 'MLcD6YnifhoY08B9n129UP5cg2139NYa',
    'debug': True,
    'disable_auto_update': False,
    'disable_command_execute': False,
    'disable_force_update': False,
    'disable_nat': False,
    'disable_send_query': False,
    'gpu': False,
    'insecure_tls': False,
    'ip_report_period': 1800,
    'report_delay': 3,
    'self_update_period': 0,
    'server': '{ARGO_DOMAIN}',
    'skip_connection_count': False,
    'skip_procs_count': False,
    'temperature': False,
    'tls': True,
    'use_gitee_to_upgrade': False,
    'use_ipv6_country_code': False,
    'uuid': '18a49016-bc2d-4be9-0ddb-5357fdbf0b3d'
}
dashboard_config = {
    'admin_template': 'admin-dist',
    'agent_secret_key': '',  
    'avg_ping_count': 2,
    'cover': 1,
    'https': {},  # 空字典
    'install_host': '{ARGO_DOMAIN}:443',
    'ip_change_notification_group_id': 0,
    'jwt_secret_key': '', 
    'jwt_timeout': 1,
    'language': 'zh_CN',
    'listen_port': 8008,
    'location': 'Asia/Shanghai',
    'site_name': '鸡子探针平台-柒蓝',
    'tls': True,
    'user_template': 'user-dist'
}

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
def nginx():
    
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
def dv1():
    os.system("rm -r /data/dashboard-linux-amd64.zip /data/dashboard-linux-amd64")
    if not os.path.exists('/data/data'):
        os.makedirs('/data/data')
        with open('/data/data/config.yaml', 'w') as file:
            yaml.dump(dashboard_config, file, default_flow_style=False)
        print("配置文件已写入 /data/data/config.yaml")
        
        # os.system("wget -O '/data/data/config.yaml' -q 'https://raw.githubusercontent.com/qilan28/hf-nezha/refs/heads/main/config.yaml'")
        os.system("wget -O '/data/data/sqlite.db' -q 'https://github.com/qilan28/hf-nezha/raw/refs/heads/main/sqlite.db'")
    
    os.system("wget -O '/data/dashboard-linux-amd64.zip' -q 'https://github.com/nezhahq/nezha/releases/download/v1.13.2/dashboard-linux-amd64.zip'")
    os.system("unzip /data/dashboard-linux-amd64.zip")
    os.system("rm -r /data/dashboard-linux-amd64.zip")
    os.system("chmod +x  /data/dashboard-linux-amd64")
    os.system("mv /data/dashboard-linux-amd64 /data/dv1")
    threading.Thread(target=nginx, daemon=True).start()
    threading.Thread(target=nv1_agent, daemon=True).start()
    os.system('/data/dv1 jwt_timeout 48')
def nv1_agent():
    time.sleep(30)
    os.system("rm -r /data/nezha-agent_linux_amd64.zip /data/nezha-agent")
    os.system("wget -O '/data/nezha-agent_linux_amd64.zip' -q 'https://github.com/nezhahq/agent/releases/download/v1.13.1/nezha-agent_linux_amd64.zip'")
    os.system("unzip /data/nezha-agent_linux_amd64.zip")
    os.system("chmod +x  /data/nezha-agent")
    os.makedirs('/data', exist_ok=True)
    # 写入 YAML 文件
    with open('/data/config.yml', 'w') as file:
        yaml.dump(agent_config, file, default_flow_style=False)
    print("配置文件已写入 /data/config.yml")
    os.system("rm -r /data/nezha-agent_linux_amd64.zip")
    os.system("mv /data/nezha-agent /data/nv1")
    os.system("/data/nv1 -c /data/config.yml")
    
    
def cloudflared():
    os.system("rm -r /data/cloudflared-linux-amd64")
    os.system("wget -O '/data/cloudflared-linux-amd64' -q 'https://github.com/cloudflare/cloudflared/releases/download/2025.9.0/cloudflared-linux-amd64'")
    os.system("chmod +x  /data/cloudflared-linux-amd64")
    os.system(f'/data/cloudflared-linux-amd64 tunnel run --protocol http2 --token {ARGO_AUTH}')

threading.Thread(target=cloudflared, daemon=True).start()
dv1()
