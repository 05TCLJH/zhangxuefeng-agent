# 雪峰常在 - 张雪峰升学规划智能体

基于大语言模型的张雪峰风格升学规划智能助手，提供高考志愿填报、专业选择等教育咨询服务。

## 功能特点

- 张雪峰风格的语言表达和思维方式
- 实时流式对话，提供打字机效果
- 基于分数和省份的精准院校推荐
- 专业就业前景分析和数据支持
- 个性化升学规划建议
- 完善的会话管理和状态跟踪

## 技术栈

### 后端
- Python 3.10+
- FastAPI - 高性能异步 Web 框架
- Pydantic - 数据验证和设置管理
- DashScope - 通义千问 API 客户端
- Python-dotenv - 环境变量管理

### 前端
- HTML5 - 页面结构
- CSS3 - 样式设计
- JavaScript (原生) - 前端逻辑
- Fetch API - HTTP 请求
- ReadableStream - SSE 流式处理

### Agent 核心
- 会话状态管理
- 信息收集流程
- 决策逻辑
- 工具集成（数据检索）
- 流式响应处理

## 快速开始

### 环境要求

- Python 3.10 或更高版本
- 通义 API 密钥（DASHSCOPE_API_KEY）
- 网络连接（用于调用通义千问 API）

### 安装步骤

#### 1. 克隆仓库

```bash
git clone https://github.com/yourusername/zhangxuefeng-agent.git
cd zhangxuefeng-agent
```

#### 2. 创建虚拟环境（推荐）

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

#### 3. 安装依赖

```bash
pip install -r requirements.txt
```

#### 4. 配置 API 密钥

1. 复制 `.env.example` 文件并重命名为 `.env`
2. 在 `.env` 文件中填入你的通义 API 密钥：

```
DASHSCOPE_API_KEY=your_actual_api_key_here
```

#### 5. 启动后端服务

```bash
uvicorn main:app --reload
```

后端服务将在 `http://localhost:8000` 启动。

#### 6. 打开前端页面

直接在浏览器中打开 `frontend/index.html` 文件，或使用 Live Server 等工具启动前端服务。

## API 接口说明

### 1. 非流式聊天接口

- **端点**：`POST /chat`
- **请求体**：
```json
{
  "message": "你的问题",
  "session_id": "可选的会话ID"
}
```
- **响应**：完整的聊天回复和会话信息

### 2. 流式聊天接口

- **端点**：`POST /chat/stream`
- **请求体**：同上
- **响应**：SSE 格式的流式回复，适合前端实时显示

### 3. 结束会话接口

- **端点**：`POST /chat/end`
- **请求体**：
```json
{
  "session_id": "要结束的会话ID"
}
```
- **响应**：告别消息

## 项目结构

```
.
├── main.py                    # FastAPI 主应用
├── backend/
│   ├── agent/                 # 智能体核心逻辑
│   │   └── zhangxuefeng_agent.py
│   ├── model/                 # 模型调用
│   │   └── model_qwen.py
│   ├── skills/                # 角色技能
│   │   └── zhangxuefeng/
│   │       ├── skill.py
│   │       └── zhangxuefeng_prompt.txt
│   └── data/                  # 数据文件
│       ├── gaokao_scores/     # 高考分数线数据
│       ├── professional_market/  # 专业就业市场数据
│       └── zhangxuefeng_quotes/  # 张雪峰经典语录
├── frontend/
│   ├── index.html             # 前端主页面
│   ├── css/
│   │   └── style-new.css      # 样式文件
│   ├── js/
│   │   └── app.js             # 前端逻辑
│   └── images/                # 图片资源
├── requirements.txt           # 依赖清单
├── .env.example               # 环境变量示例
├── .gitignore                 # Git 忽略配置
├── LICENSE                    # 开源许可证
└── README.md                  # 项目说明
```

## 故障排除

### 常见问题

1. **API 密钥错误**：确保 `.env` 文件中的 API 密钥正确
2. **依赖安装失败**：确保 Python 版本 >= 3.10
3. **端口被占用**：使用 `uvicorn main:app --reload --port 8001` 更换端口
4. **模型调用失败**：检查网络连接和 API 密钥权限
5. **跨域问题**：后端已配置 CORS，允许所有来源访问

## 许可证

MIT License