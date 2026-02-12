# A2A 相亲

过年回家相亲面对面尴尬？让 **男女双方 + 双方家长** 先通过 AI 代理（Agent）畅聊，互相了解后再决定是否见面。

- **设计文档**：[docs/DESIGN_A2A_DATING.md](docs/DESIGN_A2A_DATING.md)
- **底层思路**：基于 [Towow](https://github.com/NatureBlueee/Towow) 的投影、轮次制、Center 协调；**已集成 [Second-Me-Skills](https://github.com/mindverse/Second-Me-Skills) 与 SecondMe OAuth2**，支持用 SecondMe 个人信息作为男方/女方档案。

## 参与方（4 个 Agent）

| 角色       | 说明                     |
|------------|--------------------------|
| 男方       | 代表男方本人，基于其填写档案发言 |
| 女方       | 代表女方本人，基于其填写档案发言 |
| 男方家长   | 代表男方家庭，关心儿子婚事、对儿媳期望等 |
| 女方家长   | 代表女方家庭，关心女儿婚事、对女婿期望等 |

每方填写称呼、年龄、职业、爱好、家庭观、对另一半/对子女对象期望等，AI 按角色与档案生成当轮发言；由 **Center** 推进话题并在结束时输出匹配总结与建议。

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 配置（可选）

- **SecondMe OAuth2**（用于「用 SecondMe 登录」男方/女方）  
  在 [MindVerse SecondMe 后台](https://app.mindos.com) 创建 OAuth2 应用，配置回调地址（如 `http://localhost:8080/api/auth/secondme/callback`），在 `backend/.env` 中设置：
  - `SECONDME_CLIENT_ID`
  - `SECONDME_CLIENT_SECRET`
  - `SECONDME_REDIRECT_URI`（与后台一致）
  - 参考 `backend/.env.example`。
- **Claude**（用于 AI 畅聊）：设置 `ANTHROPIC_API_KEY` 或 `TOWOW_ANTHROPIC_API_KEY`；不配置则使用 Mock 回复。

### 3. 启动后端

在**项目根目录**执行：

```bash
python -m uvicorn backend.server:app --reload --port 8080
```

或在 `backend` 目录下：

```bash
cd backend && uvicorn server:app --reload --port 8080
```

### 4. 打开前端

浏览器访问：**http://localhost:8080**

- 填写四方档案（可简填称呼 + 几句介绍）；或点击 **「用 SecondMe 登录（男方）/（女方）」**，授权后自动拉取 SecondMe 个人信息并预填该角色档案。
- 点击「开始 AI 畅聊」→ 创建会话并自动开始多轮对话。
- 页面通过 SSE 实时展示每轮话题与 4 方发言，结束时展示总结。

## 项目结构

```
A2A相亲/
├── backend/
│   ├── server.py          # FastAPI 入口
│   ├── api/
│   │   ├── routes.py      # REST + SSE：创建会话、开始畅聊、事件流
│   │   ├── auth_routes.py # SecondMe OAuth2：登录、回调、/me、登出
│   │   └── events.py      # 内存事件推送（可换 WebSocket）
│   ├── auth/
│   │   ├── secondme.py    # SecondMe OAuth2 与用户信息拉取（参考 Second-Me-Skills）
│   │   └── session_store.py
│   └── dating/
│       ├── adapters.py    # SecondMe 用户信息 → 相亲档案
│       ├── models.py      # AgentRole, DatingProfile, DatingSession, DatingMessage
│       ├── engine.py      # ConversationEngine：多轮对话编排
│       ├── skills.py      # DatingChatSkill（单方发言）、DatingCenterSkill（话题/总结）
│       └── infra/
│           └── llm_client.py  # Claude / Mock LLM
├── website/
│   └── index.html         # 前端：表单 + 畅聊气泡流 + 总结
├── docs/
│   └── DESIGN_A2A_DATING.md
└── requirements.txt
```

## API 摘要

| 方法 | 路径 | 说明 |
|------|------|------|
| GET  | `/api/auth/secondme/login` | 发起 SecondMe 登录（query: role=male\|female, redirect_path=） |
| GET  | `/api/auth/secondme/callback` | SecondMe 授权回调（由 SecondMe 重定向） |
| GET  | `/api/auth/me` | 当前登录用户信息（Cookie 或 query session_id） |
| POST | `/api/auth/logout` | 登出 |
| POST | `/api/dating/sessions` | 创建相亲会话（body: 四方 Profile / secondme_male_session_id / secondme_female_session_id） |
| GET  | `/api/dating/sessions/{id}` | 获取会话详情与消息列表 |
| POST | `/api/dating/sessions/{id}/start` | 开始/继续畅聊（后台异步跑完） |
| GET  | `/api/dating/sessions/{id}/events` | SSE 流：round_start / message / summary |

## 与 Towow 的对应关系

| Towow 概念        | A2A 相亲中的实现                         |
|-------------------|------------------------------------------|
| Scene             | 相亲场景（固定 4 方）                    |
| Agent             | 男方 / 女方 / 男方家长 / 女方家长        |
| 轮次制 + Center   | ConversationEngine + DatingCenterSkill  |
| Offer             | 每轮各 Agent 的发言（DatingChatSkill）   |
| output_plan       | Center 输出最终匹配总结与建议            |

**SecondMe 集成**：网站已支持 SecondMe OAuth2 登录；登录后可获取 SecondMe 个人信息（`/api/secondme/user/info`、`/api/secondme/user/shades`），并映射为相亲档案用于男方/女方。实现参考 [Second-Me-Skills](https://github.com/mindverse/Second-Me-Skills) 与 [SecondMe OAuth2 指南](https://develop-docs.second.me/zh/docs/authentication/oauth2)。  

**部署**：使用 Zeabur 时，可按 [Zeabur 部署指南](docs/DEPLOY_ZEABUR.md) 按步骤完成（从 GitHub 部署 + Dockerfile + 环境变量）。

扩展方向：暴露 A2A 协议 Agent Card、多轮后支持真人接管等，见 [设计文档](docs/DESIGN_A2A_DATING.md)。
