#本项目基于CowAgent开发（https://github.com/zhayujie/CowAgent），增加了自定义角色模块
基于大模型的 AI 角色陪伴助理，支持自主任务规划、长期记忆、文件操作、浏览器工具等能力，可通过网页、微信、飞书等渠道使用。

---

## 环境要求

| 依赖 | 版本 | 说明 | 必需 |
|------|------|------|------|
| Python | 3.9 ~ 3.13 | 运行环境 | 是 |
| Git | 任意 | 克隆和管理项目 | 是 |
| ffmpeg | 任意 | 语音消息处理（pydub 依赖） | 否 |

支持 Windows 和 macOS。

---

## 安装

### Windows

**方式一：一键安装（推荐）**

以管理员身份打开 PowerShell，执行：

```powershell
irm https://raw.githubusercontent.com/18279663710la-web/cowagent/master/scripts/setup.ps1 | iex
```

脚本自动安装 Python、Git、ffmpeg，克隆项目，创建虚拟环境，安装全部依赖。

可选参数：`-SkipSystem`（跳过系统依赖）、`-WithBrowser`（附带浏览器工具）。

**方式二：手动安装**

```powershell
# 1. 安装 Python 3.12
#    从 https://www.python.org/downloads/ 下载，勾选 "Add to PATH"

# 2. 安装 Git
#    从 https://git-scm.com/download/win 下载

# 3. 安装 ffmpeg（可选，语音功能需要）
winget install ffmpeg

# 4. 克隆项目
git clone https://github.com/18279663710la-web/cowagent.git
cd cowagent

# 5. 创建虚拟环境
python -m venv venv
venv\Scripts\activate

# 6. 安装依赖
pip install -r requirements.txt
pip install -r requirements-optional.txt
pip install -e .
```

### macOS

**方式一：一键安装（推荐）**

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/18279663710la-web/cowagent/master/scripts/setup.sh)
```

脚本自动安装 Homebrew、Python、Git、ffmpeg，克隆项目，创建虚拟环境，安装全部依赖。

可选参数：`--skip-system`、`--with-browser`、`--dev`。

**方式二：手动安装**

```bash
# 1. 安装 Homebrew（如未安装）
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 2. 安装系统依赖
brew install python@3.12 git ffmpeg

# 3. 克隆项目
git clone https://github.com/18279663710la-web/cowagent.git
cd cowagent

# 4. 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 5. 安装依赖
pip3 install -r requirements.txt
pip3 install -r requirements-optional.txt
pip3 install -e .
```

---

## 配置

复制配置模板并编辑：

```bash
cp config-template.json config.json
```

在 `config.json` 中填入模型 API Key：

```json
{
  "model": "deepseek-v4-flash",
  "deepseek_api_key": "sk-你的APIKey",
  "agent": true
}
```

支持的模型及完整配置项参考 [config-template.json](config-template.json)。

---

## 运行

```bash
cow start          # 后台启动（推荐）
python app.py      # 直接运行
```

启动后访问 `http://localhost:9899/chat` 进入 Web 控制台，在这里配置模型、角色和通道。

常用命令：

```bash
cow stop           # 停止
cow restart        # 重启
cow status         # 状态
cow logs           # 日志
```

## 项目结构

```
cowagent/
├── app.py                   # 入口
├── config.py                # 配置系统
├── config-template.json     # 配置模板
├── agent/                   # Agent 系统（工具、技能、记忆）
├── bridge/                  # 桥接层
├── channel/                 # 通道（web, weixin, feishu, dingtalk, qq...）
├── characters/              # 角色系统
├── models/                  # 模型适配（DeepSeek, Claude, Gemini...）
├── common/                  # 公共模块
├── skills/                  # Agent 技能
├── tests/                   # 项目测试
└── scripts/
    ├── setup.ps1            # Windows 一键环境安装
    └── setup.sh             # macOS/Linux 一键环境安装
```
