# VikingDB 智能记忆助手

基于 VikingDB 记忆库和 OpenAI GPT 的智能问答系统，提供美观的 Web 界面进行交互。

## 功能特性

- 🤖 **AI 智能回答**：使用 OpenAI GPT 理解用户问题并生成回答
- 🧠 **记忆库查询**：自动查询 VikingDB 记忆库获取相关历史信息
- 💬 **智能整合**：将记忆库信息与 AI 知识整合，提供准确回答
- 🎨 **美观界面**：采用 React + Tailwind CSS + DaisyUI，亮色活泼风格

## 项目结构

```
viking/
├── main.py              # 原始 VikingDB 示例代码
├── server.py            # FastAPI 后端服务器
├── requirements.txt     # Python 依赖
├── frontend/           # React 前端应用
│   ├── src/
│   │   ├── components/ # React 组件
│   │   ├── App.jsx     # 主应用组件
│   │   └── main.jsx    # 入口文件
│   ├── package.json    # Node.js 依赖
│   └── vite.config.js  # Vite 配置
└── README.md
```

## 环境配置

### 1. 后端环境变量

创建 `.env` 文件或设置环境变量：

```bash
# OpenAI API Key
export OPENAI_API_KEY="your-openai-api-key"

# VikingDB 配置（已在代码中设置默认值，可覆盖）
export VIKINGDB_AK="your-vikingdb-ak"
export VIKINGDB_SK="your-vikingdb-sk"
export VIKINGDB_PROJECT="default"

# VikingDB 多库（推荐：分别对应 user / dog / relationship / conversation）
export VIKINGDB_COLLECTION_USER="user"
export VIKINGDB_COLLECTION_DOG="dog"
export VIKINGDB_COLLECTION_RELATIONSHIP="relationship"
export VIKINGDB_COLLECTION_CONVERSATION="conversation"

# 兼容旧逻辑（可选）：未指定 collection_key 时使用 default
export VIKINGDB_COLLECTION="dogbot"
```

### 2. 安装 Python 依赖

```bash
pip install -r requirements.txt
```

### 3. 安装前端依赖

```bash
cd frontend
npm install
```

## 运行项目

### 启动后端服务器

```bash
python server.py
```

后端服务将在 `http://localhost:8000` 启动

### 启动前端开发服务器

```bash
cd frontend
npm run dev
```

前端应用将在 `http://localhost:3000` 启动

## API 接口

### POST /api/query

查询记忆库并获取 AI 回答

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

### GET /api/health

健康检查接口

### 多用户 / 多狗 / 多对话调试接口（新）

- `GET /api/collections`：查看后端当前绑定的四个 collection 名称（便于确认写入目标）
- `POST /api/memory/profile/add`：指定 `collection_key` 写入画像（profile_v1）
- `POST /api/memory/session/add`：指定 `collection_key` 写入会话（event_v1）
- `POST /api/memory/search`：指定 `collection_key` 检索记忆
- `POST /api/debug/chat`：跨 `user/dog/relationship/conversation` 四库召回上下文并回答，同时把本轮写入 `conversation` 库

## 使用说明

1. 启动后端和前端服务
2. 在浏览器中打开前端应用
3. 输入问题，系统会：
   - 自动查询 VikingDB 记忆库
   - 使用 OpenAI GPT 整合信息
   - 返回智能回答并显示记忆库来源

## 技术栈

- **后端**：FastAPI, OpenAI API, VikingDB
- **前端**：React, Vite, Tailwind CSS, DaisyUI
- **样式**：亮色、活泼、高级的设计风格

## 注意事项

- 确保已配置 OpenAI API Key
- 确保 VikingDB 集合已创建并包含数据
- 前端通过代理访问后端 API（已在 vite.config.js 中配置）
