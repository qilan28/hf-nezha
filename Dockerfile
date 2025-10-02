FROM alpine:latest

# 安装必要的依赖
RUN apk update && \
    apk add --no-cache \
    wget \
    gcc \
    g++ \
    make \
    pcre-dev \
    openssl-dev \
    zlib-dev \
    linux-headers

# 下载 NGINX 源码包
RUN mkdir -p /data/tools && \
    wget -P /data/tools/ http://nginx.org/download/nginx-1.24.0.tar.gz

# 解压源码包
RUN tar -xf /data/tools/nginx-1.24.0.tar.gz -C /data/tools/

# 编译和安装 NGINX
RUN cd /data/tools/nginx-1.24.0 && \
    ./configure --prefix=/data/nginx1.24 \
                --with-http_ssl_module \
                --with-http_v2_module \
                --with-http_stub_status_module \
                --with-threads \
                --with-file-aio \
                --error-log-path=/data/nginx1.24/logs/error.log \
                --http-log-path=/data/nginx1.24/logs/access.log \
                --pid-path=/data/nginx1.24/nginx.pid \
                --http-client-body-temp-path=/data/nginx1.24/client_body_temp \
                --http-proxy-temp-path=/data/nginx1.24/proxy_temp \
                --http-fastcgi-temp-path=/data/nginx1.24/fastcgi_temp \
                --http-uwsgi-temp-path=/data/nginx1.24/uwsgi_temp \
                --http-scgi-temp-path=/data/nginx1.24/scgi_temp && \
    make && \
    make install

# # 创建所有必要的临时目录和日志目录
# RUN mkdir -p /data/nginx1.24 && \
#     echo "types {" > /data/nginx1.24/mime.types && \
#     echo "    text/html                             html htm shtml;" >> /data/nginx1.24/mime.types && \
#     echo "    text/css                              css;" >> /data/nginx1.24/mime.types && \
#     echo "    text/javascript                       js;" >> /data/nginx1.24/mime.types && \
#     echo "    image/gif                             gif;" >> /data/nginx1.24/mime.types && \
#     echo "    image/jpeg                            jpeg jpg;" >> /data/nginx1.24/mime.types && \
#     echo "    image/png                             png;" >> /data/nginx1.24/mime.types && \
#     echo "    text/plain                            txt;" >> /data/nginx1.24/mime.types && \
#     echo "    application/json                      json;" >> /data/nginx1.24/mime.types && \
#     echo "    application/xml                       xml;" >> /data/nginx1.24/mime.types && \
#     echo "}" >> /data/nginx1.24/mime.types




# 设置所有目录的权限
RUN chmod -R 777 /data/nginx1.24 && \
    chown -R nobody:nobody /data/nginx1.24

# 创建基本的 nginx.conf 配置文件
RUN echo "user nobody nobody;" > /data/nginx1.24/conf/nginx.conf && \
    echo "worker_processes auto;" >> /data/nginx1.24/conf/nginx.conf && \
    echo "error_log /data/nginx1.24/logs/error.log;" >> /data/nginx1.24/conf/nginx.conf && \
    echo "pid /data/nginx1.24/nginx.pid;" >> /data/nginx1.24/conf/nginx.conf && \
    echo "" >> /data/nginx1.24/conf/nginx.conf && \
    echo "events {" >> /data/nginx1.24/conf/nginx.conf && \
    echo "    worker_connections 1024;" >> /data/nginx1.24/conf/nginx.conf && \
    echo "}" >> /data/nginx1.24/conf/nginx.conf && \
    echo "" >> /data/nginx1.24/conf/nginx.conf && \
    echo "http {" >> /data/nginx1.24/conf/nginx.conf && \
    echo "    include mime.types;" >> /data/nginx1.24/conf/nginx.conf && \
    echo "    default_type application/octet-stream;" >> /data/nginx1.24/conf/nginx.conf && \
    echo "    server {" >> /data/nginx1.24/conf/nginx.conf && \
    echo "        listen 80;" >> /data/nginx1.24/conf/nginx

# RUN mkdir -p /data/nginx1.24 && \
#     printf "text/html                             html htm shtml;\n\
# text/css                              css;\n\
# text/javascript                       js;\n\
# image/gif                             gif;\n\
# image/jpeg                            jpeg jpg;\n\
# image/png                             png;\n\
# text/plain                            txt;\n\
# application/json                      json;\n\
# application/xml                       xml;\n" > /data/nginx1.24/mime.types

# 安装必要依赖
RUN apk update && \
    apk add --no-cache \
    ca-certificates \
    curl \
    wget \
    bzip2 \
    p7zip \
    pigz \
    pv \
    git \
    sudo \
    python3 \
    python3-dev \
    py3-pip \
    build-base \
    linux-headers \
    gcc \
    musl-dev \
    libffi-dev \
    openssl-dev \
    nodejs \
    npm \
    bash \
    py3-requests \
    py3-flask \
    py3-pexpect \
    py3-psutil
    

# 创建必要的目录并设置权限
RUN mkdir -p /tmp/app /tmp/app/frp /.kaggle /data /root/.kaggle && \
    chmod -R 777 /tmp/app /tmp/app/frp /.kaggle /data /root/.kaggle

# 设置工作目录
WORKDIR /data

# 创建虚拟环境并安装 Python 包
RUN python3 -m venv /opt/venv && \
    . /opt/venv/bin/activate && \
    pip install --upgrade pip && \
    pip install --no-cache-dir \
    jupyterlab \
    notebook \
    pexpect \
    psutil \
    requests \
    pytz \
    flask \
    kaggle \
    PyYAML \
    ipykernel
    

# 安装 configurable-http-proxy
RUN npm install -g configurable-http-proxy

# 配置 sudo
RUN echo "root ALL=(ALL) NOPASSWD:ALL" >> /etc/sudoers && \
    chmod 0440 /etc/sudoers

# 设置环境变量
ENV JUPYTER_RUNTIME_DIR=/tmp/app/runtime
ENV JUPYTER_DATA_DIR=/tmp/app/data
ENV HOME=/tmp/app
ENV PATH="/opt/venv/bin:$PATH"
ENV JUPYTER_TOKEN=${JUPYTER_TOKEN}

# 创建运行时目录
RUN mkdir -p /tmp/app/runtime && \
    chmod 777 /tmp/app/runtime

# 暴露端口
EXPOSE 7860
RUN wget -O '/data/app.py' 'https://raw.githubusercontent.com/qilan28/hf-nezha/refs/heads/main/app.py' && \
    wget -O '/data/start_server.sh' 'https://raw.githubusercontent.com/qilan28/hf-nezha/refs/heads/main/start_server.sh' && \
    chmod +x /data/start_server.sh
    
CMD ["/data/start_server.sh"]
# 启动 Jupyterlab
# CMD ["jupyter", "lab", \
#     "--ip=0.0.0.0", \
#     "--port=7860", \
#     "--no-browser", \
#     "--allow-root", \
#     "--notebook-dir=/data", \
#     "--NotebookApp.token='123'", \
#     "--ServerApp.disable_check_xsrf=True"]
