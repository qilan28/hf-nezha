#!/bin/sh

NZ_BASE_PATH="/app"
NZ_AGENT_PATH="${NZ_BASE_PATH}/nv1"


red='\033[0;31m'
green='\033[0;32m'
yellow='\033[0;33m'
plain='\033[0m'

err() {
    printf "${red}%s${plain}\n" "$*" >&2
}

success() {
    printf "${green}%s${plain}\n" "$*"
}

info() {
    printf "${yellow}%s${plain}\n" "$*"
}



deps_check() {
    local deps="curl unzip grep"
    local _err=0
    local missing=""

    for dep in $deps; do
        if ! command -v "$dep" >/dev/null 2>&1; then
            _err=1
            missing="${missing} $dep"
        fi
    done

    if [ "$_err" -ne 0 ]; then
        err "Missing dependencies:$missing. Please install them and try again."
        exit 1
    fi
}

geo_check() {
    api_list="https://blog.cloudflare.com/cdn-cgi/trace https://developers.cloudflare.com/cdn-cgi/trace"
    ua="Mozilla/5.0 (X11; Linux x86_64; rv:60.0) Gecko/20100101 Firefox/81.0"
    set -- "$api_list"
    for url in $api_list; do
        text="$(curl -A "$ua" -m 10 -s "$url")"
        endpoint="$(echo "$text" | sed -n 's/.*h=\([^ ]*\).*/\1/p')"
        if echo "$text" | grep -qw 'CN'; then
            isCN=true
            break
        elif echo "$url" | grep -q "$endpoint"; then
            break
        fi
    done
}

env_check() {
    mach=$(uname -m)
    case "$mach" in
        amd64|x86_64)
            os_arch="amd64"
            ;;
        i386|i686)
            os_arch="386"
            ;;
        aarch64|arm64)
            os_arch="arm64"
            ;;
        *arm*)
            os_arch="arm"
            ;;
        s390x)
            os_arch="s390x"
            ;;
        riscv64)
            os_arch="riscv64"
            ;;
        mips)
            os_arch="mips"
            ;;
        mipsel|mipsle)
            os_arch="mipsle"
            ;;
        *)
            err "Unknown architecture: $mach"
            exit 1
            ;;
    esac

    system=$(uname)
    case "$system" in
        *Linux*)
            os="linux"
            ;;
        *Darwin*)
            os="darwin"
            ;;
        *FreeBSD*)
            os="freebsd"
            ;;
        *)
            err "Unknown architecture: $system"
            exit 1
            ;;
    esac
}

init() {
    deps_check
    env_check

    ## China_IP
    if [ -z "$CN" ]; then
        geo_check
        if [ -n "$isCN" ]; then
            CN=true
        fi
    fi

    if [ -z "$CN" ]; then
        GITHUB_URL="github.com"
    else
        GITHUB_URL="gitee.com"
    fi
}

install() {
    echo "Installing..."

    if [ -z "$CN" ]; then
        NZ_AGENT_URL="https://${GITHUB_URL}/nezhahq/agent/releases/latest/download/nezha-agent_${os}_${os_arch}.zip"
    else
        _version=$(curl -m 10 -sL "https://gitee.com/api/v5/repos/naibahq/agent/releases/latest" | awk -F '"' '{for(i=1;i<=NF;i++){if($i=="tag_name"){print $(i+2)}}}')
        NZ_AGENT_URL="https://${GITHUB_URL}/naibahq/agent/releases/download/${_version}/nezha-agent_${os}_${os_arch}.zip"
    fi

    if command -v wget >/dev/null 2>&1; then
        _cmd="wget --timeout=60 -O ./nv1_${os}_${os_arch}.zip \"$NZ_AGENT_URL\" >/dev/null 2>&1"
    elif command -v curl >/dev/null 2>&1; then
        _cmd="curl --max-time 60 -fsSL \"$NZ_AGENT_URL\" -o ./nv1_${os}_${os_arch}.zip >/dev/null 2>&1"
    fi

    if ! eval "$_cmd"; then
        err "Download nv1 release failed, check your network connectivity"
        exit 1
    fi
    mkdir -p $NZ_AGENT_PATH
    unzip -qo ./nv1_${os}_${os_arch}.zip -d $NZ_AGENT_PATH &&
    rm -rf ./nv1_${os}_${os_arch}.zip
    mv $NZ_AGENT_PATH/nezha-agent $NZ_AGENT_PATH/nv1
    # echo $NZ_AGENT_PATH/nezha-agent $NZ_AGENT_PATH/nv1
    path="$NZ_AGENT_PATH/config.yml"
    if [ -f "$path" ]; then
        random=$(LC_ALL=C tr -dc a-z0-9 </dev/urandom | head -c 5)
        path=$(printf "%s" "$NZ_AGENT_PATH/config-$random.yml")
    fi

    if [ -z "$NZ_SERVER" ]; then
        err "NZ_SERVER should not be empty"
        exit 1
    fi

    if [ -z "$NZ_CLIENT_SECRET" ]; then
        err "NZ_CLIENT_SECRET should not be empty"
        exit 1
    fi
# NZ_DEBUG=true
    env="NZ_UUID=$UUID NZ_SERVER=$NZ_SERVER NZ_CLIENT_SECRET=$NZ_CLIENT_SECRET NZ_TLS=true  NZ_TEMPERATURE=true NZ_DISABLE_AUTO_UPDATE=$NZ_DISABLE_AUTO_UPDATE NZ_DISABLE_FORCE_UPDATE=$DISABLE_FORCE_UPDATE NZ_DISABLE_COMMAND_EXECUTE=$NZ_DISABLE_COMMAND_EXECUTE NZ_SKIP_CONNECTION_COUNT=$NZ_SKIP_CONNECTION_COUNT"
    "${NZ_AGENT_PATH}"/nv1 service -c "$path" uninstall >/dev/null 2>&1
    _cmd="env $env $NZ_AGENT_PATH/nv1 service -c $path install"
    info  "----"
    info  $env
    info  "----"
    # echo $_cmd
    if ! eval "$_cmd"; then
        err "Install nv1 service failed"
        # nohup "$NZ_AGENT_PATH/nv1" -c "$file" > "/app/nv1_$(basename "$file").log" 2>&1 &
        nohup "$NZ_AGENT_PATH/nv1" -c "$file" > "/app/nv1.log" 2>&1 &
        "${NZ_AGENT_PATH}"/mv1 service -c "$path" uninstall >/dev/null 2>&1
         myEUID=$(id -ru)
        if [ "$myEUID" -ne 0 ]; then
            info "启动nv1"
            exit 1
        fi
    fi

    success "nv1 successfully installed"
   

}
info "程序路径：$NZ_AGENT_PATH/nv1"
info "配置文件路径：$file" 
uninstall() {
# 检查是否已经有 nv1 进程在运行
    if pgrep -f "nv1" > /dev/null; then
        info "nv1 进程已在运行，跳过启动"
        exit 1
    fi
    myEUID=$(id -ru)
    if [ "$myEUID" -ne 0 ]; then
        if command -v sudo > /dev/null 2>&1; then
            info "没有root权限，nohup后台运行1"
            "$NZ_AGENT_PATH/nv1" -c "$file" 
            # nohup "$NZ_AGENT_PATH/nv1" -c "$file" > /app/nv1.log 2>&1 &
            # nohup "$NZ_AGENT_PATH/nv1" -c "$file" >/dev/null 2>&1 &
            # rm "$file"
        fi
    else
        find "$NZ_AGENT_PATH" -type f -name "*config*.yml" | while read -r file; do
            "$NZ_AGENT_PATH/nv1" -c "$file" 
            # nohup "$NZ_AGENT_PATH/nv1" -c "$file" >/dev/null 2>&1 &
            # nohup "$NZ_AGENT_PATH/nv1" -c "$file" > /app/nv1.log 2>&1 &
            # rm "$file"
        done
        info "没有root权限，nohup后台运行2"
    fi
}


if [ "$1" = "uninstall" ]; then
    uninstall
    exit
fi

init
install
uninstall
