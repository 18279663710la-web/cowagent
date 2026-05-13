# 阿里云服务器 Docker 部署指南

## 前提条件

- 阿里云轻量应用服务器（2 vCPU / 2GB 内存 / 40GB SSD），Ubuntu 22.04
- 一个已配置 API key 的 AI 模型账号（DeepSeek / OpenAI / Claude 等）
- 本地能连接 SSH

---

## 1. 购买并初始化服务器

### 1.1 购买

阿里云控制台 → 轻量应用服务器 → 创建实例：

| 配置项 | 选择 |
|--------|------|
| 地域 | 离你最近的（如华东1-杭州） |
| 镜像 | Ubuntu 22.04 |
| 套餐 | 2 vCPU / 2GB 内存 / 40GB SSD（约 ¥58/月） |
| 时长 | 先买 1 个月试用 |

### 1.2 获取登录信息

购买完成后，在控制台获取：
- **公网 IP**（如 `47.xx.xx.xx`）
- **root 密码**（控制台"重置密码"设置一个）

---

## 2. SSH 连接服务器

在本地终端执行：

```bash
ssh root@47.xx.xx.xx
# 输入密码后登录
```

---

## 3. 安装 Docker

```bash
# 更新包列表
apt update

# 安装依赖
apt install -y ca-certificates curl

# 添加 Docker 官方 GPG 密钥
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc

# 添加 Docker 仓库
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | tee /etc/apt/sources.list.d/docker.list > /dev/null

# 安装 Docker
apt update
apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# 验证安装
docker --version
```

---

## 4. 上传项目到服务器

### 方式 A：通过 Git 克隆（推荐）

先在 GitHub/Gitee 上创建一个私有仓库，把本地项目推送上去，然后在服务器克隆：

```bash
# 服务器上执行
cd /opt
git clone <你的仓库地址> chatgpt-on-wechat
cd chatgpt-on-wechat
```

### 方式 B：通过 SCP 直接上传

在本地 PowerShell 执行（把整个项目上传到服务器）：

```powershell
scp -r C:\cowagent\chatgpt-on-wechat root@47.xx.xx.xx:/opt/chatgpt-on-wechat
```

---

## 5. 配置

### 5.1 创建配置文件

```bash
cd /opt/chatgpt-on-wechat
nano config.json
```

填入以下内容（替换 `your-api-key-here` 为真实的 API key）：

```json
{
  "channel_type": "web",
  "model": "deepseek-v4-flash",
  "deepseek_api_key": "your-api-key-here",
  "deepseek_api_base": "https://api.deepseek.com/v1",
  "web_port": 9899,
  "web_password": "",
  "agent": true,
  "agent_max_context_tokens": 50000,
  "agent_max_context_turns": 20,
  "agent_max_steps": 20,
  "character_active": true,
  "knowledge": true,
  "conversation_persistence": true
}
```

> 如果用其他模型，替换 `model` 和对应的 `*_api_key` 即可。
> `web_password` 留空表示不设密码，任何人知道 IP:端口 都能访问。如需保护，请设置一个密码。

### 5.2 创建 docker-compose.yml

```bash
nano docker-compose.yml
```

```yaml
version: "3.8"
services:
  cowagent:
    build:
      context: .
      dockerfile: docker/Dockerfile.latest
      args:
        USE_CN_MIRROR: "true"
    container_name: cowagent
    restart: always
    ports:
      - "9899:9899"
    volumes:
      - ./config.json:/app/config.json
      - cow_data:/app/data
      - cow_workspace:/home/agent/cow

volumes:
  cow_data:
  cow_workspace:
```

> 注意：`/app/data` 使用命名卷而非 bind mount，避免宿主机权限问题导致角色系统初始化失败。

> `restart: always` 保证服务器重启或进程崩溃后自动恢复。
> `cow_workspace` 卷持久化 agent 工作空间（skills、memory、characters），容器重建不丢失。

---

## 6. 构建并启动

```bash
# 构建镜像（首次约 5-10 分钟，取决于网络）
docker compose build

# 后台启动
docker compose up -d

# 查看日志确认启动成功
docker logs -f cowagent
```

看到类似输出说明成功：

```
[INIT] Channel: web
[INIT] Model: deepseek-v4-flash
[App] Starting channels: ['web']
```

按 `Ctrl+C` 退出日志查看（容器不会停止）。

---

## 7. 开放防火墙端口

### 7.1 阿里云控制台开放端口

阿里云轻量服务器控制台 → 你的实例 → 防火墙 → 添加规则：

| 应用类型 | 协议 | 端口 |
|----------|------|------|
| 自定义 | TCP | 9899 |

### 7.2 服务器本地防火墙（如果有）

```bash
ufw allow 9899
```

---

## 8. 访问 Web 控制台

浏览器打开：

```
http://47.xx.xx.xx:9899
```

看到聊天界面即部署成功。

---

## 9. 常用运维命令

```bash
# 查看日志
docker logs -f cowagent

# 查看最近 50 行日志
docker logs --tail 50 cowagent

# 重启容器（修改 config.json 后执行）
docker compose restart

# 停止容器
docker compose down

# 重新构建并启动（更新代码后）
docker compose up -d --build

# 查看容器状态
docker ps
```

---

## 10. 更新项目

当本地有新版本代码需要更新到服务器时：

### 方式 A：Git 方式

```bash
cd /opt/chatgpt-on-wechat
git pull
docker compose up -d --build
```

### 方式 B：SCP 方式

在本地重新上传，然后：

```bash
cd /opt/chatgpt-on-wechat
docker compose up -d --build
```

---

## 11. 安全建议（可选）

### 11.1 设置 Web 密码

编辑 `config.json`，设置 `web_password`：

```json
"web_password": "your-strong-password"
```

重启容器：`docker compose restart`

### 11.2 配置 HTTPS（可选）

如果你有域名，可以通过 Nginx 反向代理 + Let's Encrypt 免费证书实现 HTTPS。此处略，需要时再补充。
