import subprocess
import os
import threading
import time
import yaml
from datetime import datetime
import signal
import psutil
import glob
import re
import pytz

N_PORT = os.environ.get('N_PORT', '8008') # N Z端口 默认8008
ARGO_PORT = os.environ.get('ARGO_PORT', '8009') # Argo（nginx的反代端口）固定隧道端口,留空默认8009
ARGO_DOMAIN = os.environ.get('ARGO_DOMAIN', '') # Argo固定隧道域名,留空即使用临时隧道
ARGO_AUTH = os.environ.get('ARGO_AUTH', '')  # Argo固定隧道密钥,留空即使用临时隧道
DASHBOARD_VERSION = os.environ.get('DASHBOARD_VERSION', 'v1.13.2')#	指定面板的版本，以 v0.00.00 的格式，后续将固定在该版本不会升级，不填则使用默认的 v1.13.2
NZV1_VERSION = os.environ.get('NZV1_VERSION', 'v1.13.1')#  哪吒V1的版本默认v1.13.1
BACKUP_TIME = os.environ.get('BACKUP_TIME', '10800')# 备份时间 10800秒 2小时
BACKUP_TIME =30

HF_USER1 = os.environ.get('HF_USER1', '')# HF 备份仓库的用户名
HF_REPO	= os.environ.get('HF_REPO', '')#HF 备份的Models仓库名
HF_EMAIL = os.environ.get('HF_EMAIL', '') #HF的邮箱
HF_TOKEN1 = os.environ.get('HF_TOKEN1', '')#HF备份账号的TOKEN

HF_USER2 = os.environ.get('HF_USER2', '')# huggingface 用户名
HF_ID = os.environ.get('HF_ID', '')# huggingface space 名
HF_TOKEN2 = os.environ.get('HF_TOKEN2', '')# huggingface TOKEN
#JUPYTER_TOKEN  
agent_config = {
    'client_secret': 'MLcD6YnifhoY08B9n129UP5cg2139NYa',
    'debug': False,
    'disable_auto_update': True,
    'disable_command_execute': False,
    'disable_force_update': False,
    'disable_nat': False,
    'disable_send_query': False,
    'gpu': False,
    'insecure_tls': False,
    'ip_report_period': 1800,
    'report_delay': 3,
    'self_update_period': 0,
    'server': f'{ARGO_DOMAIN}:443',
    'skip_connection_count': False,
    'skip_procs_count': False,
    'temperature': True,
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
    'install_host': f'{ARGO_DOMAIN}:443',
    'ip_change_notification_group_id': 0,
    'jwt_secret_key': '', 
    'jwt_timeout': 300,
    'language': 'zh_CN',
    'listen_port': f'{N_PORT}',
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

nginx_conf = """
# 全局配置
worker_processes auto;
pid /tmp/nginx.pid;
error_log /tmp/nginx_error.log;

events {
    worker_connections 768;
}

http {
    sendfile on;
    tcp_nopush on;
    tcp_nodelay on;
    keepalive_timeout 65;
    types_hash_max_size 2048;

    # 修改 mime.types 路径
    include /data/nginx1.24/mime.types;
    default_type application/octet-stream;

    # SSL配置
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;

    access_log /tmp/nginx_access.log;
    gzip on;

    # 上游服务器配置
    upstream dashboard {
        server 127.0.0.1:%s;
        keepalive 512;
    }

    # 服务器块
    server {
        listen %s;
        listen [::]:%s;

        server_name %s;

        # 删除所有 real_ip 相关配置
        underscores_in_headers on;

        # gRPC相关
        location ^~ /proto.NezhaService/ {
            grpc_set_header Host $host;
            grpc_read_timeout 600s;
            grpc_send_timeout 600s;
            grpc_socket_keepalive on;
            client_max_body_size 10m;
            grpc_buffer_size 4m;
            grpc_pass grpc://dashboard;
        }

        # WebSocket相关
        location ~* ^/api/v1/ws/(server|terminal|file)(.*)$ {
            proxy_set_header Host $host;
            proxy_set_header Origin https://$host;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection "upgrade";
            proxy_read_timeout 3600s;
            proxy_send_timeout 3600s;
            proxy_pass http://127.0.0.1:%s;
        }

        # Web请求处理
        location / {
            proxy_set_header Host $host;
            proxy_read_timeout 3600s;
            proxy_send_timeout 3600s;
            proxy_buffer_size 128k;
            proxy_buffers 4 256k;
            proxy_busy_buffers_size 256k;
            proxy_max_temp_file_size 0;
            proxy_pass http://127.0.0.1:%s;
        }

        # 安全头部
        add_header X-Frame-Options SAMEORIGIN;
        add_header X-Content-Type-Options nosniff;
        add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    }
}
""" % (N_PORT, ARGO_PORT, ARGO_PORT, ARGO_DOMAIN, N_PORT, N_PORT)

stop_event = threading.Event()

def kill_processes():
    # 要结束的进程名列表
    target_processes = [
        'cf', 
        'nv1', 
        'dv1', 
        'nginx'
    ]
    
    # 存储已结束的进程
    killed_processes = []
    
    # 遍历所有正在运行的进程
    for proc in psutil.process_iter(['name']):
        try:
            # 检查进程名是否在目标列表中
            if proc.info['name'] in target_processes:
                # 获取进程ID
                pid = proc.pid
                
                # 先尝试优雅地结束进程
                proc.terminate()
                
                # 等待进程结束
                try:
                    proc.wait(timeout=3)
                except psutil.TimeoutExpired:
                    # 如果进程未响应，强制杀死
                    proc.kill()
                
                killed_processes.append(f"{proc.info['name']} (PID: {pid})")
        
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
            pass
    
    # 打印已结束的进程
    if killed_processes:
        print("已结束以下进程:")
        for process in killed_processes:
            print(process)
    else:
        print("未找到匹配的进程")
kill_processes()
def get_latest_local_package(directory, pattern='*.tar.gz'):
    try:
        # 构建完整的搜索路径
        search_pattern = os.path.join(directory, pattern)
        
        # 查找所有匹配的文件
        files = glob.glob(search_pattern)
        
        if not files:
            print("未找到匹配的 nezha-hf 压缩包")
            return None
        
        # 获取最新的文件
        latest_file = max(files, key=os.path.getmtime)
        
        print(f"找到最新的包: {latest_file}")
        return latest_file
    
    except Exception as e:
        print(f"获取最新包时发生错误: {e}")
        return None

def compress_folder(folder_path, output_dir, keep_count=3):
    try:
        # 确保输出目录存在
        os.makedirs(output_dir, exist_ok=True)
        
        # 使用 pytz 获取中国时区的当前时间戳（毫秒级）
        import pytz
        from datetime import datetime
        
        # 设置中国时区
        china_tz = pytz.timezone('Asia/Shanghai')
        
        # 获取当前中国时间的时间戳
        timestamp = str(int(datetime.now(china_tz).timestamp() * 1000))
        output_path = os.path.join(output_dir, f'{timestamp}.tar.gz')
        
        # 获取所有压缩包
        existing_archives = glob.glob(os.path.join(output_dir, '*.tar.gz'))
        
        # 安全地提取时间戳
        def extract_timestamp(filename):
            # 提取文件名中的数字部分
            match = re.search(r'(\d+)\.tar\.gz$', filename)
            return int(match.group(1)) if match else 0
        
        # 如果压缩包数量超过保留数量，删除最旧的
        if len(existing_archives) >= keep_count:
            # 按时间戳排序（从小到大，最旧的在前面）
            existing_archives.sort(key=extract_timestamp)
            
            # 计算需要删除的数量
            delete_count = len(existing_archives) - keep_count + 1
            
            # 删除最旧的压缩包
            for i in range(delete_count):
                oldest_archive = existing_archives[i]
                try:
                    os.remove(oldest_archive)
                    print(f"删除最旧的压缩包：{os.path.basename(oldest_archive)}")
                except Exception as e:
                    print(f"删除失败 {oldest_archive}: {e}")
        
        # tar.gz 压缩
        result = subprocess.run(
            ['tar', '-czvf', output_path, folder_path], 
            capture_output=True, 
            text=True
        )
        
        if result.returncode == 0:
            # 计算压缩包大小
            file_size = os.path.getsize(output_path) / 1024 / 1024
            
            # 格式化中国时区的时间
            china_time = datetime.now(china_tz)
            formatted_time = china_time.strftime('%Y-%m-%d %H:%M:%S')
            
            print(f"压缩成功：{output_path}")
            print(f"压缩大小：{file_size:.2f} MB")
            print(f"压缩时间：{formatted_time}")
            print(f"保留策略：最多保留 {keep_count} 个备份包")
            
            # 返回压缩包名和大小信息
            return f"{os.path.basename(output_path)} MB：{file_size:.2f} MB TIME：{formatted_time}"
        else:
            print("压缩失败")
            print("错误信息:", result.stderr)
            return None
    
    except Exception as e:
        print(f"压缩出错: {e}")
        return None


# 调用函数
# new_archive = compress_folder('/data/dv1', 'nezha-hf')
def github(type):
    if type == 1:
        os.system(f'rm -rf /data/{HF_REPO}') 
    if not os.path.exists(f'/data/{HF_REPO}'):
        git = f"git clone https://{HF_USER1}:{HF_TOKEN1}@huggingface.co/{HF_USER1}/{HF_REPO}"
        print(git)
        os.system(git)
        os.system(f'git config --global user.email "{HF_EMAIL}"')
        os.system(f'git config --global user.name "{HF_USER1}"') 
    os.chdir(f'/data/{HF_REPO}')
    if type == 2:
        os.chdir(f'/data/{HF_REPO}')
        print("开始备份上传HF")
        # 清理 LFS 存储
        os.system('git lfs prune')
        # 备份上传仓库
        new_archive_info = compress_folder('/data/dv1', f'/data/{HF_REPO}', keep_count=3)
        if new_archive_info:
            new_archive, file_size_info = new_archive_info.split(' MB：')
            os.system(f'git add .')
            os.system(f'git commit -m "{file_size_info}"')
            # os.system('git push -u origin main')
            # 使用强制推送并清理
            os.system('git push -f origin main')
            os.system('git gc --prune=now')
        else:
            print("压缩失败，无法提交")
def nginx():    
    # 确保目录存在
    os.makedirs('/data/nginx1.24', exist_ok=True)
    # 写入文件
    with open('/data/nginx1.24/mime.types', 'w') as f:
        f.write(mime_types_content)
    # 设置文件权限（可选）
    os.chmod('/data/nginx1.24/mime.types', 0o644)
    print("mime.types 文件已创建")
    # time.sleep(10)
    # os.system("rm -rf /data/nginx.conf")
    # os.system("wget -O '/data/nginx.conf' -q 'https://raw.githubusercontent.com/qilan28/hf-nezha/refs/heads/main/nginx.conf'")
    with open('/data/nginx.conf', 'w') as f:
        f.write(nginx_conf)
    os.system("/data/nginx1.24/sbin/nginx -c /data/nginx.conf")
def dv1():
    os.system("rm -rf /data/dv1.zip /data/dashboard-linux-amd64 /data/dv1 /data/data")
    latest_package = get_latest_local_package(f'/data/{HF_REPO}')
    if latest_package:

        print(f"最新压缩包路径: {latest_package}")
        print("通过备份包启动")
        # tar -xzvf /data/nezha-hf/1759393184994.tar.gz -C /data
        # tar -xzvf /data/nezha-hf/1759393184994.tar.gz --strip-components=2 -C /data dv1/
        print(f"解压：tar -xzvf {latest_package} -C /data")
        os.system(f"tar -xzvf {latest_package} -C /data")
        
        os.system("mv /data/data/dv1/ /data")
        os.system("rm -rf /data/data")

        os.chdir('/data/dv1')
    else:
        print("通过下载程序启动")
        if not os.path.exists('/data/dv1'):
            os.makedirs('/data/dv1')
        if not os.path.exists('/data/dv1/data'):
            os.system("rm -rf /data/dv1/data/config.yaml  /data/dv1/data/sqlite.db")
            os.makedirs('/data/dv1/data')
            with open('/data/dv1/data/config.yaml', 'w') as file:
                yaml.dump(dashboard_config, file, default_flow_style=False)
            print("配置文件已写入 /data/dv1/data/config.yaml")
            print("下载'https://github.com/qilan28/hf-nezha/raw/refs/heads/main/sqlite.db'")
            os.system("wget -O '/data/dv1/data/sqlite.db'  'https://github.com/qilan28/hf-nezha/raw/refs/heads/main/sqlite.db'")
        os.chdir('/data/dv1')
        print(f"下载'https://github.com/nezhahq/nezha/releases/download/{DASHBOARD_VERSION}/dashboard-linux-amd64.zip'")
        os.system(f"wget -O '/data/dv1/dv1.zip' -q 'https://github.com/nezhahq/nezha/releases/download/{DASHBOARD_VERSION}/dashboard-linux-amd64.zip'")
        os.system("unzip -o /data/dv1/dv1.zip -d /data/dv1")
        os.system("rm -rf /data/dv1/dv1.zip")
        os.system("chmod +x /data/dv1/dashboard-linux-amd64")
        os.system("mv /data/dv1/dashboard-linux-amd64 /data/dv1/dv1")
    if os.path.exists('/data/dv1/dv1') and os.path.isfile('/data/dv1/dv1'):
        print("dv1存在开始启动")
        threading.Thread(target=repeat_task, daemon=True).start()
        threading.Thread(target=nginx, daemon=True).start()
        threading.Thread(target=cf, daemon=True).start()
        threading.Thread(target=nv1_agent, daemon=True).start()
        threading.Thread(target=check_system_resources, daemon=True).start()
        # os.system('/data/dv1/dv1 jwt_timeout 48')
        os.system('nohup /data/dv1/dv1 >> /dev/null 2>&1 &')
    else:
        print("dv1不存在")
        
def nv1_agent():
    # time.sleep(10)
    os.system("rm -rf /data/nv1.zip /data/nezha-agent /data/nv1")
    print(f"下载'https://github.com/nezhahq/agent/releases/download/{NZV1_VERSION}/nezha-agent_linux_amd64.zip'")
    os.system(f"wget -O '/data/nv1.zip' -q 'https://github.com/nezhahq/agent/releases/download/{NZV1_VERSION}/nezha-agent_linux_amd64.zip'")
    time.sleep(2)
    os.system("unzip -o /data/nv1.zip -d /data")
    os.system("chmod +x  /data/nezha-agent")
    os.makedirs('/data', exist_ok=True)
    # 写入 YAML 文件
    with open('/data/config.yml', 'w') as file:
        yaml.dump(agent_config, file, default_flow_style=False)
    print("配置文件已写入 /data/config.yml")
    time.sleep(2)
    os.system("rm -rf /data/nv1.zip")
    os.system("mv /data/nezha-agent /data/nv1")
    os.system("nohup /data/nv1 -c /data/config.yml >> /dev/null 2>&1 &")
    
def cf():
    os.system("rm -rf /data/cf")
    os.system("wget -O '/data/cf' -q  'https://github.com/cloudflare/cloudflared/releases/download/2025.9.0/cloudflared-linux-amd64'")
    os.system("chmod +x  /data/cf")
    os.system(f'nohup /data/cf tunnel run --protocol http2 --token {ARGO_AUTH} >> /dev/null 2>&1 &')
def _reconstruct_token(partial_token):
    return partial_token.replace(" ", "")
def restart_huggingface_space(space_name, space_id, partial_token):
    token = _reconstruct_token(partial_token)
    url = f"https://huggingface.co/api/spaces/{space_name}/{space_id}/restart?factory=true"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36"
    }
    try:
        response = requests.post(url, headers=headers, json={})
        return {
            "status_code": response.status_code,
            "success": response.status_code == 200,
            "message": response.text
        }
    except requests.RequestException as e:
        return {
            "status_code": None,
            "success": False,
            "message": str(e)
        }
def check_system_resources():
    time.sleep(120)
    cpu_usage = psutil.cpu_percent(interval=1)
    memory = psutil.virtual_memory()
    memory_usage = memory.percent
    # if cpu_usage >= 90:
    if cpu_usage >= 90 or memory_usage >= 95:
        print("占用过高")
        print(HF_USER2, HF_ID, HF_TOKEN2)
        result = restart_huggingface_space(HF_USER2, HF_ID, HF_TOKEN2)
        print(result)
    else:
        print("系统资源正常")
   
def repeat_task():
    print('备份线程启动')
    while True:
        print(f"打包时间：{BACKUP_TIME} 秒")
        time.sleep(int(BACKUP_TIME))# 2小时
        github(2)
github(1)
os.chdir('/data/')
dv1()
if os.path.exists('/data/dv1/dv1') and os.path.isfile('/data/dv1/dv1'):
    print('等待重启中。。。')
    while True:
        time.sleep(14400)# 4小时 14400 6小时 21600
        github(2)
        print(HF_USER2, HF_ID, HF_TOKEN2)
        result = restart_huggingface_space(HF_USER2, HF_ID, HF_TOKEN2)
        print(result)
        # break
# github(2)
# nv1_agent()
