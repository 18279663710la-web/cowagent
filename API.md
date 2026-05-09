# CowAgent API 接口文档

> Base URL: `http://{host}:9899`
> Content-Type: `application/json; charset=utf-8`
> 所有 `/api/*` 和 `/message` 端点需要登录（Cookie: `cow_auth_token`）

---

## 1. 认证

### POST /auth/login
登录获取 token。

| 参数 | 类型 | 说明 |
|------|------|------|
| password | string | web_password，空则不校验 |

```
Response 200
{"status": "success"}
{"status": "error", "message": "Wrong password"}
```

### GET /auth/check
检查登录状态。

```
Response 200
{"status": "success", "auth_required": false}           // 未设密码
{"status": "success", "auth_required": true, "authenticated": true}   // 已登录
{"status": "success", "auth_required": true, "authenticated": false}  // 未登录
```

### POST /auth/logout
登出。

---

## 2. 对话（核心）

### POST /message
发送消息，返回 request_id 用于获取回复。

| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| session_id | string | session_{timestamp} | 会话 ID，同一 ID 共享上下文 |
| message | string | 必填 | 用户消息 |
| stream | bool | true | true=SSE 流式，false=轮询 |
| attachments | array | [] | 附件列表 [{file_type, file_path}] |

```
Request
POST /message
{"session_id": "web_user", "message": "你好", "stream": true}

Response 200
{"status": "success", "request_id": "req_abc123", "stream": true}
```

### GET /stream
SSE 流式获取回复（stream=true 时使用）。

| Query | 说明 |
|-------|------|
| request_id | POST /message 返回的 ID |

```
SSE Events:
event: reasoning      → 思考过程（DeepSeek V4 深度思考时）
data: {"delta": "..."}

event: delta          → 文本增量
data: {"text": "..."}

event: tool_start     → 工具调用开始
data: {"tool": "read", "input": {...}}

event: tool_end       → 工具调用结束
data: {"tool": "read", "output": "..."}

event: message_end    → 消息生成完成
data: {"text": "完整回复"}

event: done           → 整个请求结束
data: {"final": "最终回复文本"}
```

### POST /poll
轮询获取回复（stream=false 时使用）。

```
Request
POST /poll
{"session_id": "web_user"}

Response 200
{"status": "success", "reply": "回复文本"}
```

---

## 3. 角色管理（Character）

### GET /api/characters
列出所有角色。

```
Response 200
{
  "status": "success",
  "characters": [{
    "id": "abc123",
    "name": "晚晚",
    "gender": "女",
    "age": 25,
    "personality": "外表清冷...",
    "language_style": "自然口语化...",
    "catchphrases": ["别闹。", "笨蛋。"],
    "interests": ["看电影"],
    "background": "晚晚是...",
    "relationship": "女朋友",
    "rules": [],
    "avatar": "",
    "is_active": true,
    "bound_user_id": "web_user",
    "created_at": "2026-05-09 16:46:03",
    "updated_at": "2026-05-09 16:46:23"
  }]
}
```

### POST /api/characters
创建角色。

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | string | 是 | 角色名 |
| gender | string | 否 | 性别（男/女/保密） |
| age | int | 否 | 年龄 |
| personality | string | 是 | 性格描述 |
| language_style | string | 否 | 语言风格 |
| catchphrases | string[] | 否 | 口头禅列表 |
| interests | string[] | 否 | 兴趣爱好 |
| background | string | 否 | 背景故事 |
| relationship | string | 否 | 与用户的关系 |
| rules | string[] | 否 | 行为规则 |

```
Request
POST /api/characters
{"name": "小美", "gender": "女", "age": 22, "personality": "活泼可爱", "relationship": "好朋友"}

Response 200
{"status": "success", "character": {...}}
```

### GET /api/characters/{id}
获取角色详情。

### PUT /api/characters/{id}
更新角色。参数同 POST。

### DELETE /api/characters/{id}
删除角色。

### POST /api/characters/{id}/activate
激活角色。同一时刻只有一个角色处于激活状态。

```
Response 200
{"status": "success", "character": {...}}
```

### POST /api/characters/{id}/deactivate
停用角色。

### GET /api/characters/{id}/history
查看角色历史会话。

| Query | 默认 | 说明 |
|-------|------|------|
| page | 1 | 页码 |
| page_size | 50 | 每页条数 |

### GET /api/characters/{id}/memory
查看角色记忆内容。

```
Response 200
{"status": "success", "character_id": "abc", "memory": "# 记忆内容..."}
```

### GET /api/characters/{id}/export
导出角色对话记录。

| Query | 默认 | 说明 |
|-------|------|------|
| format | json | json 或 markdown |

---

## 4. 会话管理

### GET /api/sessions
列出所有历史会话。

| Query | 默认 | 说明 |
|-------|------|------|
| page | 1 | 页码 |
| page_size | 50 | 每页条数 |

```
Response 200
{"status": "success", "sessions": [{"session_id": "xxx", "title": "你好", "msg_count": 5, ...}], "total": 100}
```

### DELETE /api/sessions/{id}
删除会话及其所有消息。

### PUT /api/sessions/{id}
重命名会话。

```
Request  {"title": "新标题"}
```

### GET /api/sessions/{id}/generate_title
LLM 自动生成会话标题。

### POST /api/sessions/{id}/clear_context
清除会话上下文（保留历史但不再注入 LLM）。

### GET /api/history
分页查看某会话的对话历史。

| Query | 默认 | 说明 |
|-------|------|------|
| session_id | 必填 | 会话 ID |
| page | 1 | 页码 |
| page_size | 50 | 每页条数 |

---

## 5. 配置管理

### GET /config
获取全局配置（API key 脱敏 `sk-*****`）。

```
Response 200
{
  "model": "deepseek-v4-flash",
  "channel_type": "weixin",
  "agent": true,
  "agent_max_context_tokens": 50000,
  "deepseek_api_key": "sk-*****7e9",    // 已脱敏
  ...
}
```

### POST /config
更新配置。API key 为 `*****` 时不更新该项。

```
Request
{"model": "deepseek-v4-flash", "agent": true, "agent_max_context_tokens": 80000}

Response 200
{"status": "success"}
```

---

## 6. 通道管理

### GET /api/channels
列出通道状态。

```
Response 200
{
  "channels": [
    {"name": "weixin", "running": true, "connected": true},
    {"name": "web", "running": true, "connected": true}
  ]
}
```

### POST /api/channels
接入/断开通道。

| 参数 | 说明 |
|------|------|
| action | "connect" / "disconnect" |
| channel | 通道名称 |

### GET /api/weixin/qrlogin
获取微信登录二维码。

| Query | 说明 |
|-------|------|
| action | "fetch"=获取二维码, "status"=查询扫码状态 |

```
// 获取二维码
GET /api/weixin/qrlogin?action=fetch
→ {"status": "success", "qrcode_url": "https://...", "qrcode_data": "data:image/png;base64,..."}

// 查询状态
GET /api/weixin/qrlogin?action=status
→ {"status": "wait"}      // 等待扫码
→ {"status": "scaned"}    // 已扫码待确认
→ {"status": "confirmed"} // 登录成功
→ {"status": "expired"}   // 二维码过期
```

---

## 7. Agent 工具体系

### GET /api/tools
列出所有可用工具（含 MCP 工具）。

```
Response 200
{
  "tools": [
    {"name": "read", "description": "读取文件"},
    {"name": "write", "description": "写入文件"},
    ...
  ]
}
```

### GET /api/skills
列出所有技能（内置+自定义）。

```
Response 200
{"skills": [{"name": "xxx", "enabled": true, "description": "..."}, ...]}
```

### POST /api/skills
启用/禁用技能。

```
Request  {"name": "skill_name", "enabled": true}
```

### GET /api/memory
列出记忆文件。

### GET /api/memory/content
读取记忆文件内容。

| Query | 说明 |
|-------|------|
| file | 文件路径（相对于 workspace/memory） |

### GET /api/scheduler
列出定时任务。

```
Response 200
{"tasks": [{"id": "xxx", "name": "...", "enabled": true, "schedule": "0 9 * * *", ...}]}
```

---

## 8. 知识库

### GET /api/knowledge/list
列出知识库目录树。

### GET /api/knowledge/read
读取知识文件。

| Query | 说明 |
|-------|------|
| path | 文件相对路径 |

### GET /api/knowledge/graph
获取知识库图谱（节点+链接）。

---

## 9. 文件上传

### POST /upload
上传文件（multipart/form-data）。返回文件元数据。

```
Response 200
{
  "status": "success",
  "file_path": "/path/to/uploaded/file",
  "file_type": "image",
  "preview_url": "/uploads/filename"
}
```

### GET /uploads/{filename}
访问已上传文件。

### GET /api/file?path={absolute_path}
访问服务器本地文件（Agent 工具产生的文件）。

---

## 10. 其他

### GET /
重定向到 /chat。

### GET /chat
返回聊天 HTML 页面。

### GET /api/logs
SSE 流式输出 run.log（实时日志）。

### GET /api/version
返回版本号。

```
Response 200
{"version": "1.7.7"}
```

### GET /assets/{path}
静态资源（CSS/JS/图片）。

---

## 快速参考表

| 端点 | 方法 | 说明 |
|------|------|------|
| `/auth/login` | POST | 登录 |
| `/auth/check` | GET | 检查登录 |
| `/message` | POST | 发送消息 |
| `/stream` | GET | SSE 流式回复 |
| `/poll` | POST | 轮询回复 |
| `/api/characters` | GET/POST | 列出/创建角色 |
| `/api/characters/{id}` | GET/PUT/DELETE | 角色 CRUD |
| `/api/characters/{id}/activate` | POST | 激活角色 |
| `/api/characters/{id}/deactivate` | POST | 停用角色 |
| `/api/characters/{id}/history` | GET | 角色对话历史 |
| `/api/characters/{id}/memory` | GET | 角色记忆 |
| `/api/characters/{id}/export` | GET | 导出对话 |
| `/api/sessions` | GET | 会话列表 |
| `/api/sessions/{id}` | PUT/DELETE | 更新/删除会话 |
| `/config` | GET/POST | 全局配置 |
| `/api/channels` | GET/POST | 通道管理 |
| `/api/weixin/qrlogin` | GET | 微信二维码 |
| `/api/tools` | GET | 工具列表 |
| `/api/skills` | GET/POST | 技能管理 |
| `/api/memory` | GET | 记忆文件 |
| `/api/scheduler` | GET | 定时任务 |
| `/api/knowledge/list` | GET | 知识库 |
| `/api/logs` | GET | 实时日志 |
| `/api/version` | GET | 版本号 |
| `/upload` | POST | 上传文件 |
