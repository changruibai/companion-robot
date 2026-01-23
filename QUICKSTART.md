# 快速启动指南

## 前置要求

1. **Python 3.8+**
2. **Node.js 16+**
3. **OpenAI API Key**（必需）

## 快速开始

### 1. 安装后端依赖

```bash
cd backend
pip install -r requirements.txt
cd ..
```

### 2. 安装前端依赖

```bash
cd frontend
npm install
cd ..
```

### 3. 配置环境变量

设置 OpenAI API Key：

```bash
export OPENAI_API_KEY="your-openai-api-key"
```

或者创建 `.env` 文件（如果使用 python-dotenv）：

```bash
OPENAI_API_KEY=your-openai-api-key
```

### 4. 启动服务

#### 方式一：使用启动脚本（推荐）

```bash
./start.sh
```

#### 方式二：手动启动

**终端 1 - 启动后端：**
```bash
cd backend
python3 server.py
```

**终端 2 - 启动前端：**
```bash
cd frontend
npm run dev
```

### 5. 访问应用

打开浏览器访问：http://localhost:3000

## 测试查询

尝试以下问题：

- "咖啡推荐"
- "天气怎么样"
- "如何设置提醒"

系统会自动：
1. 查询 VikingDB 记忆库
2. 使用 OpenAI GPT 整合信息
3. 返回智能回答

## 故障排除

### 后端无法启动

- 检查 Python 版本：`python3 --version`
- 检查依赖安装：`pip list | grep fastapi`
- 检查端口 8000 是否被占用

### 前端无法启动

- 检查 Node.js 版本：`node --version`
- 检查依赖安装：`cd frontend && npm list`
- 检查端口 3000 是否被占用

### API 调用失败

- 检查 OpenAI API Key 是否正确设置
- 检查后端服务是否正常运行：访问 http://localhost:8000/api/health
- 检查浏览器控制台的错误信息

### 记忆库查询无结果

- 确保 VikingDB 集合已创建
- 确保集合中包含数据（可运行 `python backend/main.py` 添加示例数据）
- 检查用户 ID 和助手 ID 是否匹配

## 项目结构

```
viking/
├── backend/            # 后端服务（Python FastAPI）
│   ├── main.py         # VikingDB 示例代码
│   ├── server.py       # FastAPI 后端服务器
│   ├── routes.py       # API 路由定义
│   ├── requirements.txt # Python 依赖
│   └── logs/           # 日志文件目录
├── frontend/           # 前端应用（React + Vite）
│   ├── src/
│   │   ├── components/ # React 组件
│   │   ├── App.jsx
│   │   └── main.jsx
│   └── package.json
├── start.sh            # 启动脚本
└── README.md           # 项目说明文档
```
