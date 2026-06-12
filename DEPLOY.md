# 灵析 AI 智能投顾助手 — 生产环境部署指南

本文档面向**第一次部署本项目**的同学，按顺序操作即可完成上线。

- **方案 A（默认）**：阿里云 ECS + Docker Compose，对外提供 HTTP（80 端口）
- **方案 B**：秒悟（Meoo）云平台一键部署，见 [第 11 节](#11-秒悟meoo云部署)

文末附 HTTPS 与常见问题排查。

---

## 目录

1. [部署架构概览](#1-部署架构概览)
2. [购买与配置阿里云 ECS](#2-购买与配置阿里云-ecs)
3. [登录服务器并完成基础配置](#3-登录服务器并完成基础配置)
4. [安装 Docker 与 Docker Compose](#4-安装-docker-与-docker-compose)
5. [拉取代码并配置环境变量](#5-拉取代码并配置环境变量)
6. [构建并启动服务](#6-构建并启动服务)
7. [验证部署是否成功](#7-验证部署是否成功)
8. [配置 HTTPS（可选）](#8-配置-https可选)
9. [日常运维命令](#9-日常运维命令)
10. [常见问题排查](#10-常见问题排查)
11. [秒悟（Meoo）云部署](#11-秒悟meoo云部署)

---

## 1. 部署架构概览

```
用户浏览器
    │
    ▼  :80
┌─────────────────┐
│  frontend 容器   │  Nginx 托管 Vue 静态页，/api 反向代理到后端
└────────┬────────┘
         │  Docker 内网
         ▼  :8000
┌─────────────────┐
│  backend 容器    │  FastAPI + SQLite + ML 模型
└────────┬────────┘
         │
         ▼
  Docker 卷 lingxi-db  →  /app/persist/lingxi.db（数据库持久化）
  宿主机目录挂载       →  backend/models、backend/data（只读）
```

| 组件 | 容器端口 | 宿主机端口 | 说明 |
|------|----------|------------|------|
| 前端 | 80 | 80 | 用户访问入口 |
| 后端 | 8000 | 8000 | API 与 Swagger 文档（可选对外开放） |

---

## 2. 购买与配置阿里云 ECS

### 2.1 登录阿里云

1. 打开 [阿里云官网](https://www.aliyun.com/) 并登录。
2. 进入控制台 → **云服务器 ECS** → **实例** → **创建实例**。

### 2.2 推荐配置

| 项目 | 推荐值 | 说明 |
|------|--------|------|
| 地域 | 离用户最近的地域（如华东1） | 降低访问延迟 |
| 实例规格 | **2 核 4 GiB** 起步，建议 **4 核 8 GiB** | 后端含 TensorFlow，首次构建较吃内存 |
| 操作系统 | **Ubuntu 22.04 LTS** 或 **Alibaba Cloud Linux 3** | 与下文命令兼容 |
| 系统盘 | **40 GiB** 及以上 | Docker 镜像与模型文件占用空间 |
| 公网 IP | 勾选 **分配公网 IPv4** | 需固定带宽或按量 |
| 带宽 | 3~5 Mbps 起步 | 按实际访问量调整 |

### 2.3 安全组（非常重要）

创建实例时或事后在 **安全组规则** 中放行：

| 方向 | 协议 | 端口 | 授权对象 | 用途 |
|------|------|------|----------|------|
| 入方向 | TCP | 22 | 你的办公 IP/32 | SSH 登录（勿对 0.0.0.0/0 长期开放） |
| 入方向 | TCP | 80 | 0.0.0.0/0 | HTTP 网站访问 |
| 入方向 | TCP | 443 | 0.0.0.0/0 | HTTPS（若启用） |
| 入方向 | TCP | 8000 | 你的办公 IP/32 | 后端调试（生产可不放行） |

> **提示**：22 端口仅对你的 IP 开放，可显著降低被暴力破解风险。

### 2.4 设置登录方式

- **推荐**：创建时绑定 **SSH 密钥对**，本地用私钥登录。
- **或**：设置 **root 密码**（务必使用强密码）。

记录以下信息，后续会用到：

- 公网 IP：例如 `47.96.xxx.xxx`
- 登录用户：Ubuntu 默认为 `ubuntu`，部分镜像为 `root`

---

## 3. 登录服务器并完成基础配置

### 3.1 SSH 登录（Windows PowerShell / macOS / Linux）

```bash
# 密钥登录（将路径和 IP 换成你的）
ssh -i "C:\Users\你的用户名\.ssh\你的密钥.pem" ubuntu@47.96.xxx.xxx

# 密码登录
ssh ubuntu@47.96.xxx.xxx
```

### 3.2 更新系统并安装常用工具

**Ubuntu 22.04：**

```bash
sudo apt-get update
sudo apt-get upgrade -y
sudo apt-get install -y git curl vim
```

**Alibaba Cloud Linux 3：**

```bash
sudo yum update -y
sudo yum install -y git curl vim
```

### 3.3 内存不足时增加 Swap（2 核 4G 机器建议执行）

首次 `docker compose build` 安装 TensorFlow 时可能内存吃紧，可先加 4G 交换分区：

```bash
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab
free -h
```

---

## 4. 安装 Docker 与 Docker Compose

以下命令适用于 **Ubuntu 22.04**（官方推荐方式）：

```bash
# 1. 卸载旧版本（如有）
sudo apt-get remove -y docker docker-engine docker.io containerd runc 2>/dev/null || true

# 2. 安装依赖
sudo apt-get install -y ca-certificates curl gnupg

# 3. 添加 Docker 官方 GPG 与软件源
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# 4. 安装 Docker Engine 与 Compose 插件
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# 5. 当前用户加入 docker 组（免 sudo）
sudo usermod -aG docker $USER

# 6. 重新登录 SSH 一次，然后验证
docker --version
docker compose version
```

**Alibaba Cloud Linux 3** 可使用：

```bash
sudo yum install -y docker
sudo systemctl enable docker
sudo systemctl start docker
sudo usermod -aG docker $USER
# Compose 插件若缺失，见 Docker 官方文档安装 compose-plugin
```

验证：

```bash
docker run hello-world
```

看到 `Hello from Docker!` 即安装成功。

---

## 5. 拉取代码并配置环境变量

### 5.1 克隆项目

```bash
cd ~
git clone https://github.com/WENNA-cpu/linxiAiFinance.git
cd linxiAiFinance
```

若仓库为私有，需先配置 GitHub SSH 密钥或 Personal Access Token。

### 5.2 确认模型与数据文件存在

部署依赖以下目录（`docker-compose.yml` 会挂载到后端容器）：

```bash
ls backend/models/lstm_cycle.h5
ls backend/models/rf_risk.pkl
ls backend/data/knowledge_base.json
```

若文件缺失，周期分析、风险诊断等功能会报错。请从开发环境拷贝，或在服务器上按 `backend` 内训练脚本生成。

### 5.3 创建环境变量文件

在项目**根目录**创建 `.env`（Compose 会读取并注入后端）：

```bash
cp .env.example .env
vim .env
```

**生产环境至少修改以下项：**

```bash
# 必改：随机强密钥（可用 openssl rand -hex 32 生成）
SECRET_KEY=请替换为至少32位随机字符串

# 行情数据（持仓诊断、周期分析等需要）
TUSHARE_TOKEN=你的_tushare_pro_token

# 投教 AI 问答（DeepSeek）
DEEPSEEK_API_KEY=你的_deepseek_api_key

# 可选：新模型灰度流量百分比
NEW_MODEL_RATIO=5
```

生成随机密钥示例：

```bash
openssl rand -hex 32
```

**密钥获取方式：**

| 变量 | 获取地址 |
|------|----------|
| `TUSHARE_TOKEN` | https://tushare.pro/ 注册后在「个人中心」复制 |
| `DEEPSEEK_API_KEY` | https://platform.deepseek.com/ 创建 API Key |

> `.env` 已在 `.gitignore` 中，**切勿提交到 Git**。

### 5.4 环境变量说明（与 docker-compose 的关系）

`docker-compose.yml` 中后端使用：

```yaml
DATABASE_URL=sqlite:////app/persist/lingxi.db   # 容器内 SQLite，数据写入 Docker 卷
SECRET_KEY=${SECRET_KEY}
TUSHARE_TOKEN=${TUSHARE_TOKEN}
DEEPSEEK_API_KEY=${DEEPSEEK_API_KEY}
```

**无需**在 `.env` 里改 `DATABASE_URL`（Compose 已写死为持久化路径）。  
本地开发用的 `sqlite:///./lingxi.db` 与生产 Docker 路径不同，属正常现象。

---

## 6. 构建并启动服务

在项目根目录执行：

```bash
cd ~/linxiAiFinance

# 方式一：一键脚本
chmod +x start.sh
./start.sh

# 方式二：手动命令（推荐，便于观察输出）
docker compose up --build -d
```

**首次构建说明：**

- 后端需下载 TensorFlow 等依赖，**可能耗时 10~30 分钟**，请耐心等待。
- 若构建失败并提示 OOM，请确认已配置 Swap（见 3.3）或升级实例内存。

查看构建/启动进度：

```bash
docker compose logs -f
```

看到 backend 出现 `Uvicorn running on http://0.0.0.0:8000`、frontend 无报错即可 `Ctrl+C` 退出日志跟踪（容器继续运行）。

---

## 7. 验证部署是否成功

将 `47.96.xxx.xxx` 换成你的 ECS 公网 IP：

```bash
# 1. 容器状态（应为 Up）
docker compose ps

# 2. 后端健康检查
curl -s http://127.0.0.1:8000/docs | head

# 3. 经 Nginx 代理访问 API
curl -s http://127.0.0.1/api/market/sentiment

# 4. 前端页面
curl -I http://127.0.0.1/
```

浏览器访问：

| 地址 | 说明 |
|------|------|
| `http://你的公网IP/` | 灵析首页 |
| `http://你的公网IP/api/market/sentiment` | 市场情绪 API |
| `http://你的公网IP:8000/docs` | Swagger（若 8000 已放行） |

首页能打开、市场情绪有数据，即部署成功。

---

## 8. 配置 HTTPS（可选）

当前 Docker 内 Nginx 默认占用宿主机 **80** 端口。要启用 HTTPS，推荐：

1. 把 Docker 前端改到 **8080**
2. 宿主机 Nginx 监听 **80/443**，反向代理到 `127.0.0.1:8080`

### 8.1 域名解析

在域名服务商处添加 **A 记录**：`lingxi.example.com` → ECS 公网 IP。

### 8.2 调整 Docker 端口映射

编辑 `docker-compose.yml`，将 frontend 端口改为：

```yaml
  frontend:
    ports:
      - "8080:80"   # 原来是 "80:80"
```

重新启动：

```bash
docker compose up -d
```

### 8.3 安装 Certbot 与 Nginx（Ubuntu）

```bash
sudo apt-get install -y nginx certbot python3-certbot-nginx
```

### 8.4 Nginx 反向代理配置

```bash
sudo vim /etc/nginx/sites-available/lingxi
```

写入：

```nginx
server {
    listen 80;
    server_name lingxi.example.com;

    location / {
        proxy_pass http://127.0.0.1:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

启用并重载：

```bash
sudo ln -sf /etc/nginx/sites-available/lingxi /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default   # 避免与 Docker 争用配置
sudo nginx -t
sudo systemctl reload nginx
```

### 8.5 申请 SSL 证书

```bash
sudo certbot --nginx -d lingxi.example.com
```

按提示填写邮箱并选择强制 HTTPS。证书自动续期：

```bash
sudo certbot renew --dry-run
```

**阿里云替代方案**：在「SSL 证书」服务申请免费证书，挂到 **负载均衡 SLB** 或 **CDN**，后端指向 ECS **8080** 端口。

---

## 9. 日常运维命令

```bash
cd ~/linxiAiFinance

# 查看状态
docker compose ps

# 查看日志（全部 / 单个服务）
docker compose logs -f
docker compose logs -f backend
docker compose logs -f frontend

# 更新代码后重新部署
git pull
docker compose up --build -d

# 停止服务
docker compose down

# 停止并删除数据卷（⚠️ 会清空数据库，慎用）
docker compose down -v
```

### 9.1 备份 SQLite 数据库

数据库位于 Docker 卷 `lingxi-db`，容器内路径 `/app/persist/lingxi.db`：

```bash
# 查看卷名
docker volume ls | grep lingxi

# 备份到当前目录（卷名一般为 linxiaifinance_lingxi-db 或 项目目录名_lingxi-db）
docker run --rm \
  -v linxiaifinance_lingxi-db:/data \
  -v $(pwd):/backup \
  alpine cp /data/lingxi.db /backup/lingxi-$(date +%Y%m%d).db
```

### 9.2 开机自启

```bash
sudo systemctl enable docker
```

`docker-compose.yml` 中已设置 `restart: unless-stopped`，宿主机重启后容器会自动拉起。

---

## 10. 常见问题排查

### 10.1 浏览器无法访问，但服务器上 curl 正常

| 检查项 | 命令 / 操作 |
|--------|-------------|
| 阿里云安全组 | 控制台确认 **80** 已对 `0.0.0.0/0` 放行 |
| 系统防火墙 | `sudo ufw status`；若 active，执行 `sudo ufw allow 80/tcp` |
| 容器是否运行 | `docker compose ps` |

### 10.2 端口冲突（80 或 8000 已被占用）

```bash
# 查看占用进程
sudo ss -tlnp | grep -E ':80|:8000'

# 若系统 Nginx/Apache 占用了 80，可停掉或改 Docker 映射
# 编辑 docker-compose.yml，例如改为：
#   frontend ports: "8080:80"
#   backend  ports: "8001:8000"
docker compose up --build -d
```

### 10.3 构建失败：内存不足 / Killed

- 增加 Swap（见 [3.3](#33-内存不足时增加-swap2-核-4g-机器建议执行)）
- 升级 ECS 至 4 核 8G
- 单独构建：`docker compose build backend` 观察报错

### 10.4 后端启动失败：数据库 / 路径问题

**现象**：日志出现 `unable to open database file` 或 SQLite 相关错误。

**原因与处理：**

1. Docker 卷未正确挂载 — 确认 `docker-compose.yml` 中有：
   ```yaml
   volumes:
     - lingxi-db:/app/persist
   ```
2. 误把本地路径 `sqlite:///./lingxi.db` 写进 Compose 环境变量 — 生产应使用 `sqlite:////app/persist/lingxi.db`（Compose 已配置，勿覆盖）。
3. 权限问题 — 重建卷：
   ```bash
   docker compose down
   docker volume rm linxiaifinance_lingxi-db   # 卷名以 docker volume ls 为准
   docker compose up -d
   ```

### 10.5 模型文件找不到

**现象**：周期分析、诊断接口 500，日志含 `No such file` 或 `lstm_cycle.h5`。

```bash
ls -la backend/models/lstm_cycle.h5 backend/models/rf_risk.pkl
docker compose exec backend ls -la /app/models/
```

确保宿主机 `backend/models` 存在且 Compose 挂载：

```yaml
- ./backend/models:/app/models:ro
```

修改模型后需重启：`docker compose restart backend`

### 10.6 Tushare / DeepSeek 接口无数据或报未配置

```bash
# 进入后端容器检查环境变量是否注入
docker compose exec backend env | grep -E 'TUSHARE|DEEPSEEK|SECRET'

# 修改 .env 后必须重建/重启
docker compose up -d --force-recreate backend
```

- 未配置 `TUSHARE_TOKEN`：行情、周期分析可能降级或报错。
- 未配置 `DEEPSEEK_API_KEY`：投教 AI 问答会提示未配置密钥。

### 10.7 前端能打开，但 API 请求 502 / 504

```bash
docker compose logs backend --tail 100
docker compose ps
```

常见原因：后端仍在启动（TensorFlow 加载慢）、后端崩溃、Nginx 无法解析 `backend` 主机名（需在同一 Compose 网络，一般自动配置）。

在 frontend 容器内测试连通性：

```bash
docker compose exec frontend wget -qO- http://backend:8000/docs | head
```

### 10.8 SSL 证书问题

| 现象 | 处理 |
|------|------|
| 证书过期 | `sudo certbot renew` |
| 域名与证书不匹配 | 重新 `certbot --nginx -d 你的域名` |
| 混合内容 / HTTPS 下 API 失败 | 确保全站走 HTTPS，Nginx 设置 `X-Forwarded-Proto` |
| 阿里云证书 | 在 SLB/CDN 控制台绑定，源站指向 ECS |

### 10.9 Git pull 后页面未更新

```bash
git pull
docker compose up --build -d
docker compose logs frontend --tail 20
```

前端为构建时打包进镜像，**必须 `--build`** 才会更新静态资源。

### 10.10 磁盘空间不足

```bash
df -h
docker system df
docker system prune -a   # ⚠️ 会删除未使用的镜像，确认后再执行
```

---

## 11. 秒悟（Meoo）云部署

本节适用于在 [秒悟 Meoo](https://docs.meoo.com/) 平台发布本项目，**无需自行购买 ECS 或安装 Docker**。平台会自动构建前端、启动后端，并生成可访问的预览/发布链接。

### 11.1 与 ECS 方案的区别

| 对比项 | ECS + Docker Compose | 秒悟（Meoo） |
|--------|----------------------|--------------|
| 服务器 | 自行购买 ECS | 平台托管 |
| 环境变量 | 根目录 `.env` + Compose 注入 | 项目内 `.env` 文件或云服务密钥 |
| 数据库 | Docker 卷 `/app/persist/lingxi.db` | `backend/lingxi.db`（SQLite 相对路径） |
| 发布方式 | `docker compose up` | 编辑器内「发布 → 立即发布」 |
| 环境变量模板 | `.env.example` | **`.env.cloud`**（秒悟专用精简版） |

### 11.2 部署前准备

1. 在秒悟中打开/导入本项目（项目根目录为 **`/home/project/`**）。
2. 确认以下文件存在（周期分析、诊断等功能依赖）：
   ```bash
   ls backend/models/lstm_cycle.h5
   ls backend/models/rf_risk.pkl
   ls backend/data/knowledge_base.json
   ```
3. 准备好以下密钥（见 [11.3](#113-环境变量说明envcloud)）：
   - [Tushare Pro](https://tushare.pro/) → `TUSHARE_TOKEN`
   - [DeepSeek](https://platform.deepseek.com/) → `DEEPSEEK_API_KEY`
   - 自行生成 → `SECRET_KEY`（可用 `openssl rand -hex 32`）

### 11.3 环境变量说明（`.env.cloud`）

项目根目录提供了秒悟专用模板 **[`.env.cloud`](.env.cloud)**，相比 `.env.example` 更精简，并标注了必填/可选。

**复制为 `.env`：**

在秒悟编辑器终端或本地执行：

```bash
cp .env.cloud .env
# 编辑 .env，填入真实密钥
```

**变量清单：**

| 变量 | 是否必填 | 用途 |
|------|----------|------|
| `TUSHARE_TOKEN` | **必填** | 行情、持仓诊断、周期分析、市场情绪 |
| `DEEPSEEK_API_KEY` | **必填** | 投教 AI 问答、诊断追问 |
| `SECRET_KEY` | **必填** | 本地持仓加密存储 |
| `DATABASE_URL` | 推荐 | 默认 `sqlite:///./lingxi.db` 即可 |
| `NEW_MODEL_RATIO` | 推荐 | 新模型灰度比例，默认 `5` |
| `DEEPSEEK_BASE_URL` | 可选 | 默认 `https://api.deepseek.com` |
| `DEEPSEEK_MODEL` | 可选 | 默认 `deepseek-chat` |
| `MEOO_PROJECT_API_KEY` | 可选 | Meoo AI / Edge Function；当前主流程走 DeepSeek，可暂不填 |
| `ENVIRONMENT` | 可选 | 建议 `production` |
| `LOG_LEVEL` | 可选 | 建议 `INFO` |

> **说明**：`.env.example` 同样包含上述变量；秒悟部署优先参考 `.env.cloud`。  
> `.env` 已在 `.gitignore` 中，**切勿提交到 Git 或公开发布**。

### 11.4 配置 `.env` 的三种方式

#### 方式 A：在编辑器中创建文件（推荐）

秒悟项目根目录为 `/home/project/`。后端 `env_loader.py` 会**依次加载**：

1. `/home/project/.env`
2. `/home/project/backend/.env`

**操作步骤：**

1. 在秒悟左侧文件树，于**项目根目录**新建 `.env`
2. 复制 `.env.cloud` 内容，填入真实密钥
3. （建议）在 `backend/` 下再建一份相同内容的 `.env`
4. 保存后重新发布或重启后端

#### 方式 B：在对话中让 AI 创建

在秒悟对话框发送（密钥私发，不要贴在公开对话里）：

> 请在项目根目录和 backend 目录各创建 .env，参考 .env.cloud 模板，填入 TUSHARE_TOKEN、DEEPSEEK_API_KEY、SECRET_KEY。

#### 方式 C：云服务密钥（Secret）

适用于 **Edge Function / Meoo AI** 场景，见 [秒悟云服务能力介绍](https://docs.meoo.com/file-6)：

1. 项目设置 → 开启「**云服务**」
2. 在「**密钥管理**」创建 Secret（如 `TUSHARE_TOKEN`、`DEEPSEEK_API_KEY`、`MEOO_PROJECT_API_KEY`）
3. Edge Function 通过 `Deno.env.get('变量名')` 读取

> **注意**：当前 Python FastAPI 后端通过 `dotenv` 读取 **`.env` 文件**，不会自动读取云服务 Secret。  
> 若仅使用 FastAPI 后端，请用方式 A；若同时使用 Edge Function，Secret 与 `.env` 可并存。

### 11.5 发布与验证

1. 右上角点击 **发布 → 立即发布**
2. 等待构建完成，打开生成的访问链接
3. 在终端验证环境变量是否生效（**不要** `echo` 完整密钥）：

```bash
ls -la /home/project/.env /home/project/backend/.env

cd /home/project/backend && python -c "
import os
from dotenv import load_dotenv
load_dotenv('../.env')
load_dotenv('.env')
print('TUSHARE configured:', bool(os.getenv('TUSHARE_TOKEN')))
print('DEEPSEEK configured:', bool(os.getenv('DEEPSEEK_API_KEY')))
print('SECRET_KEY configured:', bool(os.getenv('SECRET_KEY')))
"
```

4. 浏览器检查：
   - 首页「市场情绪简报」有数据
   - 「投教」或「诊断追问」AI 能正常回复

### 11.6 秒悟常见问题

| 现象 | 可能原因 | 处理 |
|------|----------|------|
| 市场情绪无数据 / API 报错 | `TUSHARE_TOKEN` 未配置或无效 | 检查 `.env`，重新发布 |
| 投教 / 诊断 AI 提示未配置密钥 | `DEEPSEEK_API_KEY` 缺失 | 检查 `backend/.env`，重启后端 |
| 修改 `.env` 后仍不生效 | 未重启或未重新发布 | 保存文件 → 重新发布 |
| 加密持仓异常 | `SECRET_KEY` 变更 | 更换密钥会导致旧数据无法解密，生产环境勿随意修改 |
| Edge Function 报环境变量错误 | Secret 未在云服务中创建 | 在「云服务 → 密钥」补建，并 `cloud deploy-function` 重新部署 |
| 周期分析 500 | 模型文件缺失 | 确认 `backend/models/*.h5`、`*.pkl` 存在 |

更多平台级问题见 [秒悟 FAQ](https://docs.meoo.com/faq)。

---

## 附录：最小命令清单（复制即用）

```bash
# === 在全新 Ubuntu 22.04 ECS 上 ===
sudo apt-get update && sudo apt-get install -y git curl
# … 按第 4 节安装 Docker …

git clone https://github.com/WENNA-cpu/linxiAiFinance.git
cd linxiAiFinance
cp .env.example .env
vim .env    # 填入 SECRET_KEY、TUSHARE_TOKEN、DEEPSEEK_API_KEY

docker compose up --build -d
docker compose ps
curl http://127.0.0.1/api/market/sentiment
```

浏览器打开：`http://<ECS公网IP>/`

### 秒悟（Meoo）最小步骤

```bash
# 在秒悟项目 /home/project/ 下
cp .env.cloud .env
cp .env backend/.env
# 编辑两处 .env，填入 TUSHARE_TOKEN、DEEPSEEK_API_KEY、SECRET_KEY
# 然后在平台点击「发布 → 立即发布」
```

---

## 附录：相关文件索引

| 文件 | 作用 |
|------|------|
| `docker-compose.yml` | ECS 服务编排、端口、卷、环境变量 |
| `.env` | 生产密钥（根目录，不提交 Git） |
| `.env.example` | 完整环境变量模板（ECS / 本地开发） |
| `.env.cloud` | **秒悟专用**精简环境变量模板 |
| `frontend/nginx.conf` | 前端静态资源 + `/api` 反向代理 |
| `backend/Dockerfile` | 后端镜像构建 |
| `frontend/Dockerfile` | 前端构建 + Nginx |
| `start.sh` | 一键 `docker compose up --build -d` |
| `backend/app/core/env_loader.py` | 后端加载 `.env` 的入口 |

---

如有部署问题：

- **ECS 方案**：先执行 `docker compose logs -f` 保存日志，对照 [第 10 节](#10-常见问题排查)
- **秒悟方案**：对照 [第 11.6 节](#116-秒悟常见问题)，并查阅 [秒悟文档](https://docs.meoo.com/)
