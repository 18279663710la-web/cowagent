# CowAgent — AI 角色陪伴平台

基于大模型的 AI 角色陪伴助理，支持自主任务规划、长期记忆、文件操作、浏览器工具等能力，可通过网页、微信、飞书等渠道使用。

---

## 环境要求

| 依赖 | 说明 | 必需 |
|------|------|------|
| Python 3.9 ~ 3.13 | 运行环境 | 是 |
| Git | 克隆项目 | 是 |
| ffmpeg | 语音消息处理 | 否（推荐安装） |

支持 Windows 和 macOS。

---

## 快速安装

### Windows

**方式一：一键安装（推荐）**

以管理员身份打开 PowerShell，执行：

```powershell
irm https://raw.githubusercontent.com/18279663710la-web/cowagent/master/scripts/setup.ps1 | iex
```

脚本自动安装 Python、Git、ffmpeg，克隆项目，创建虚拟环境，安装全部依赖。

**方式二：手动安装**

```powershell
# 1. 安装 Python (python.org 下载，勾选 Add to PATH)
# 2. 安装 Git (git-scm.com 下载)
# 3. 安装 ffmpeg (winget install ffmpeg)

# 4. 克隆项目
git clone https://github.com/18279663710la-web/cowagent.git
cd cowagent

# 5. 创建虚拟环境并安装
python -m venv venv
venv\Scripts\activate
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

**方式二：手动安装**

```bash
# 1. 安装 Homebrew（如未安装）
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# 2. 安装依赖
brew install python@3.12 git ffmpeg

# 3. 克隆项目
git clone https://github.com/18279663710la-web/cowagent.git
cd cowagent

# 4. 创建虚拟环境并安装
python3 -m venv venv
source venv/bin/activate
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

---

## 桌面安装器

将项目打包成一个独立安装程序（.exe / .app），用户双击即可安装，无需手动配置任何环境。

### 构建

```bash
pip install pyinstaller

# Windows 版
python scripts/installer/build.py --platform windows

# macOS 版（需在 Mac 上运行）
python scripts/installer/build.py --platform macos
```

构建完成后在 `scripts/installer/dist/` 目录下：
- Windows: `CowAgent-Installer.exe`（~460 MB）
- macOS: `CowAgent-Installer.app`

### 安装包使用说明

1. 双击 `CowAgent-Installer.exe`（Windows）或 `.app`（macOS）
2. 选择安装路径（默认 `C:\Program Files\CowAgent`）
3. 点击「安装」，等待进度条完成
4. 点击「启动 CowAgent」，浏览器自动打开配置页面
5. 在网页中填入 API Key 即可开始使用

以后每次使用只需双击桌面上的 CowAgent 快捷方式。

### 安装目录结构

```
安装目录/
├── python/              # 自带 Python，不影响系统环境
├── cowagent/            # 项目文件
├── tools/ffmpeg/        # ffmpeg
├── scripts/
│   ├── start.bat        # 启动
│   └── uninstall.bat    # 卸载
└── workspace/           # 运行时数据
```

### 卸载

运行安装目录下的 `uninstall.bat`（Windows）或 `uninstall.command`（macOS），或直接删除安装目录加桌面快捷方式。不写注册表，不影响系统环境。

### 测试

```bash
pytest scripts/installer/tests/ -v               # 安装器单元测试
python scripts/installer/installer_gui.py        # 开发模式直接打开 GUI
```

---

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
    ├── setup.sh             # macOS/Linux 一键环境安装
    └── installer/           # 桌面安装器
        ├── installer_gui.py #   安装器 GUI
        ├── install_engine.py#   安装引擎
        ├── build.py         #   构建脚本
        ├── installer.spec   #   PyInstaller 配置
        ├── payload/         #   载荷模板
        └── tests/           #   测试
```
