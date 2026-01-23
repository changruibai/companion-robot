# VikingDB 智能记忆助手

基于 VikingDB 记忆库和 OpenAI GPT 的智能问答系统，采用前后端分离架构，提供美观的 Web 界面进行交互。

## 📋 目录

- [功能特性](#功能特性)
- [项目结构](#项目结构)
- [环境配置](#环境配置)
- [快速开始](#快速开始)
- [API 接口](#api-接口)
- [技术栈](#技术栈)
- [架构说明](#架构说明)
- [开发指南](#开发指南)
- [故障排除](#故障排除)

## ✨ 功能特性

- 🤖 **AI 智能回答**：使用 OpenAI GPT 理解用户问题并生成回答
- 🧠 **记忆库查询**：自动查询 VikingDB 记忆库获取相关历史信息
- 💬 **智能整合**：将记忆库信息与 AI 知识整合，提供准确回答
- 🎨 **美观界面**：采用 React + Tailwind CSS + DaisyUI，亮色活泼风格
- 🌊 **意识流架构**：采用主观优先、客观校验的意识流处理流程
- 📝 **多库管理**：支持 user、dog、relationship、conversation 多个记忆库

## 📁 项目结构

```
viking/
├── backend/                    # 后端服务（Python FastAPI）
│   ├── main.py                # VikingDB 示例代码
│   ├── server.py              # FastAPI 服务器入口
│   ├── routes.py              # API 路由定义
│   ├── config.py              # 配置模块（环境变量、日志）
│   ├── models.py              # Pydantic 数据模型
│   ├── viking_client.py       # VikingDB 客户端管理
│   ├── ai_utils.py            # AI 工具函数
│   ├── memory_utils.py        # 记忆工具函数
│   ├── memory_writing.py      # 记忆写入模块
│   ├── consciousness_flow.py   # 意识流处理模块
│   ├── state_machine.py       # 状态机模块
│   ├── state_machine_config.json  # 状态机配置
│   ├── requirements.txt       # Python 依赖
│   └── logs/                  # 日志文件目录
│
├── frontend/                   # 前端应用（React + Vite）
│   ├── src/
│   │   ├── components/        # React 组件
│   │   │   ├── ChatInterface.jsx
│   │   │   ├── DebugConsole.jsx
│   │   │   ├── Header.jsx
│   │   │   ├── LoadingSpinner.jsx
│   │   │   └── MessageBubble.jsx
│   │   ├── App.jsx            # 主应用组件
│   │   ├── main.jsx           # 入口文件
│   │   └── index.css          # 全局样式
│   ├── package.json           # Node.js 依赖
│   ├── vite.config.js         # Vite 配置
│   └── tailwind.config.js     # Tailwind CSS 配置
│
├── logs/                       # 根目录日志（可选）
├── data/                       # 数据文件目录
├── .env                        # 环境变量文件（需自行创建）
├── start.sh                    # 一键启动脚本
├── README.md                   # 项目说明文档（本文件）
├── QUICKSTART.md               # 快速启动指南
└── ARCHITECTURE.md             # 架构设计文档
```

## ⚙️ 环境配置

### 1. 系统要求

- **Python 3.8+**
- **Node.js 16+**
- **npm** 或 **yarn**

### 2. 后端环境变量

在项目根目录创建 `.env` 文件：

```bash
# OpenAI API Key（必需）
OPENAI_API_KEY="your-openai-api-key"

# DeepSeek API Key（可选）
DEEPSEEK_API_KEY="your-deepseek-api-key"

# VikingDB 配置（必需）
VIKINGDB_AK="your-vikingdb-ak"
VIKINGDB_SK="your-vikingdb-sk"
VIKINGDB_PROJECT="default"
VIKINGDB_PROFILE_TYPE="profile_v1"

# VikingDB 多库配置（推荐：分别对应 user / dog / relationship / conversation）
VIKINGDB_COLLECTION_USER="user"
VIKINGDB_COLLECTION_DOG="dog"
VIKINGDB_COLLECTION_RELATIONSHIP="relationship"
VIKINGDB_COLLECTION_CONVERSATION="conversation"

# 兼容旧逻辑（可选）：未指定 collection_key 时使用 default
VIKINGDB_COLLECTION="dogbot"
```

### 3. 安装后端依赖

```bash
cd backend
pip install -r requirements.txt
```

### 4. 安装前端依赖

```bash
cd frontend
npm install
```

## 🚀 快速开始

### 方式一：使用启动脚本（推荐）

```bash
# 在项目根目录执行
chmod +x start.sh
./start.sh
```

启动脚本会自动：
1. 加载 `.env` 环境变量
2. 检查 Python 和 Node.js 环境
3. 启动后端服务器（http://localhost:8000）
4. 启动前端开发服务器（http://localhost:3000）

### 方式二：手动启动

**终端 1 - 启动后端：**
```bash
cd backend
python3 server.py
```

后端服务将在 `http://localhost:8000` 启动

**终端 2 - 启动前端：**
```bash
cd frontend
npm run dev
```

前端应用将在 `http://localhost:3000` 启动

### 访问应用

打开浏览器访问：http://localhost:3000

## 📡 API 接口

### 基础接口

#### GET /
健康检查

**响应：**
```json
{
  "status": "ok",
  "message": "VikingDB 智能记忆助手服务运行中"
}
```

#### GET /api/health
健康检查接口（包含 VikingDB 连接状态）

**响应：**
```json
{
  "status": "healthy",
  "vikingdb": "connected"
}
```

#### GET /api/collections
查看后端当前绑定的四个 collection 名称

**响应：**
```json
{
  "project": "default",
  "collections": {
    "user": {
      "collection_name": "user",
      "env": "VIKINGDB_COLLECTION_USER"
    },
    "dog": {
      "collection_name": "dog",
      "env": "VIKINGDB_COLLECTION_DOG"
    }
  }
}
```

### 查询接口

#### POST /api/query
智能查询记忆库并生成回答

**请求体：**
```json
{
  "query": "用户的问题",
  "user_id": "user_001",
  "assistant_id": "assistant_001",
  "limit": 5
}
```

**响应：**
```json
{
  "answer": "AI 生成的回答",
  "memories": [
    {
      "content": "记忆内容",
      "score": 0.95,
      "memory_type": "event_v1"
    }
  ],
  "sources": ["记忆来源摘要..."]
}
```

### 调试聊天接口（意识流架构）

#### POST /api/debug/chat
使用意识流架构生成回答（流式响应）

**请求体：**
```json
{
  "query": "用户输入",
  "user_id": "user_001",
  "dog_id": "dog_001",
  "conversation_id": "conv_001",
  "assistant_id": "assistant_001",
  "model": "chatgpt"
}
```

**响应：** SSE 流式格式
```
data: {"content": "回复片段", "done": false}
data: {"content": "", "done": true, "full_answer": "完整回答"}
```

### 画像管理接口

#### POST /api/profile/add
添加画像记忆（默认写入 user 库）

**请求体：**
```json
{
  "profile_type": "profile_v1",
  "user_id": "user_001",
  "assistant_id": "assistant_001",
  "memory_info": {
    "user_profile": "用户画像文本"
  },
  "is_upsert": true
}
```

#### POST /api/profile/update
更新画像记忆（默认更新 user 库）

**请求体：**
```json
{
  "profile_id": "profile_id_xxx",
  "memory_info": {
    "user_profile": "更新后的画像文本"
  }
}
```

### 多库管理接口

#### POST /api/memory/profile/add
添加画像记忆-多库（支持指定 collection_key）

#### POST /api/memory/profile/update
更新画像记忆-多库（支持指定 collection_key）

#### POST /api/memory/session/add
会话写入-多库（支持指定 collection_key）

#### POST /api/memory/search
记忆检索-多库（支持指定 collection_key）

### 列表查询接口

#### GET /api/users
获取用户列表

#### GET /api/dogs
获取狗列表

#### GET /api/conversations?user_id=xxx&dog_id=xxx
获取历史会话列表

## 🛠️ 技术栈

### 后端
- **FastAPI** - 现代、快速的 Web 框架
- **OpenAI API** - GPT 模型调用
- **VikingDB** - 向量数据库，用于记忆存储和检索
- **Pydantic** - 数据验证和序列化
- **Uvicorn** - ASGI 服务器

### 前端
- **React** - UI 框架
- **Vite** - 构建工具
- **Tailwind CSS** - 实用优先的 CSS 框架
- **DaisyUI** - Tailwind CSS 组件库

## 🏗️ 架构说明

### 前后端分离架构

本项目采用前后端分离架构：

- **后端（backend/）**：提供 RESTful API 服务，处理业务逻辑、AI 调用、记忆库操作
- **前端（frontend/）**：提供用户界面，通过 HTTP 请求与后端通信

### 意识流架构

系统采用**意识流架构**实现陪伴型智能机器狗的核心功能。详细说明请参考 [ARCHITECTURE.md](./ARCHITECTURE.md)。

核心流程包括：
1. **Emotion Grounding**（情绪感受）- 形成当下情绪立场
2. **Subjective Recall**（主观回忆）- 机器狗讲述它以为记得什么
3. **Memory Verification**（Viking 校验）- 为主观回忆提供事实支撑
4. **Response Synthesis**（回复生成）- 生成自然、带有边界感的回复
5. **Memory Consolidation**（记忆沉淀）- 将验证过的记忆写入 dog 库

### 记忆库职责

- **user 库**：存储跨狗稳定事实
- **dog 库**：唯一承载关系变化，存储被验证过的痕迹
- **conversation 库**：作为事实来源，记录每轮对话
- **relationship 库**：用于离线分析或可视化

## 💻 开发指南

### 后端开发

1. **添加新的 API 路由**
   - 在 `backend/routes.py` 中添加路由处理函数
   - 使用 `@app.post()` 或 `@app.get()` 装饰器

2. **添加新的数据模型**
   - 在 `backend/models.py` 中定义 Pydantic 模型

3. **添加新的业务逻辑**
   - 在相应的工具模块中添加函数（如 `ai_utils.py`、`memory_utils.py`）

### 前端开发

1. **添加新的组件**
   - 在 `frontend/src/components/` 中创建新组件

2. **修改 API 调用**
   - 在组件中使用 `fetch()` 调用后端 API
   - API 基础路径已在 `vite.config.js` 中配置代理

3. **修改样式**
   - 使用 Tailwind CSS 类名
   - 全局样式在 `frontend/src/index.css` 中

### 日志查看

后端日志文件位于 `backend/logs/` 目录，按日期命名：
- `query_YYYYMMDD.log` - 查询请求日志
- `viking_YYYYMMDD.log` - VikingDB 相关日志

## 🔧 故障排除

### 后端无法启动

- 检查 Python 版本：`python3 --version`（需要 3.8+）
- 检查依赖安装：`pip list | grep fastapi`
- 检查端口 8000 是否被占用：`lsof -i :8000`
- 检查环境变量是否正确设置：`echo $OPENAI_API_KEY`

### 前端无法启动

- 检查 Node.js 版本：`node --version`（需要 16+）
- 检查依赖安装：`cd frontend && npm list`
- 检查端口 3000 是否被占用：`lsof -i :3000`
- 清除缓存重新安装：`rm -rf node_modules package-lock.json && npm install`

### API 调用失败

- 检查后端服务是否正常运行：访问 http://localhost:8000/api/health
- 检查 OpenAI API Key 是否正确设置
- 检查浏览器控制台的错误信息（F12 打开开发者工具）
- 检查网络请求是否被代理拦截

### 记忆库查询无结果

- 确保 VikingDB 集合已创建
- 确保集合中包含数据（可运行 `python backend/main.py` 添加示例数据）
- 检查用户 ID 和助手 ID 是否匹配
- 检查环境变量中的 collection 名称是否正确

### CORS 错误

- 后端已配置允许所有来源的 CORS，如仍有问题，检查 `backend/server.py` 中的 CORS 配置

## 📝 注意事项

1. **环境变量**：确保 `.env` 文件在项目根目录，且包含所有必需的配置
2. **端口冲突**：确保 8000（后端）和 3000（前端）端口未被占用
3. **API 密钥**：不要将 API 密钥提交到版本控制系统
4. **日志文件**：日志文件会自动创建在 `backend/logs/` 目录
5. **前端代理**：前端通过 Vite 代理访问后端 API，无需配置跨域

## 📚 相关文档

- [快速启动指南](./QUICKSTART.md) - 快速上手指南
- [架构设计文档](./ARCHITECTURE.md) - 详细的架构说明

## 📄 许可证

本项目采用 MIT 许可证。

## 👥 贡献

欢迎提交 Issue 和 Pull Request！

---

**项目作者**：白倡瑞 (changruibai@gmail.com)
