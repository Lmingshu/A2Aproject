# 使用 Zeabur 部署 A2A 相亲

按以下步骤将项目部署到 [Zeabur](https://zeabur.com)，获得公网可访问的链接（含 SecondMe 登录与 Claude 畅聊）。

- **Zeabur 官方文档**：[部署 Python 项目](https://zeabur.com/docs/zh-CN/guides/python)、[根目录](https://zeabur.com/docs/zh-CN/deploy/root-directory)、[Dockerfile 部署](https://zeabur.com/docs/zh-CN/deploy/dockerfile)、[环境变量](https://zeabur.com/docs/zh-CN/deploy/variables)、[运行命令](https://zeabur.com/docs/zh-CN/deploy/command-execution)。

---

## 一、前置准备

1. **Zeabur 账号**  
   打开 [Zeabur](https://zeabur.com) 注册/登录（可用 GitHub 登录）。

2. **代码在 GitHub**  
   将本仓库推送到你的 GitHub（如 `your-username/A2A相亲` 或改名为 `a2a-dating` 等）。  
   Zeabur 通过「与 GitHub 集成」从仓库拉取代码并自动部署，详见 [与 GitHub 集成](https://zeabur.com/docs/zh-CN/deploy/github)。

3. **（可选）SecondMe OAuth**  
   若要用「用 SecondMe 登录」：在 [MindVerse SecondMe 后台](https://app.mindos.com) 创建 OAuth2 应用，记下 **Client ID**、**Client Secret**，并准备**生产环境回调地址**（见下文）。

4. **（可选）Claude API**  
   若要用真实 AI 畅聊：准备 [Anthropic](https://www.anthropic.com/) 的 API Key。不配置则使用 Mock 回复。

---

## 二、在 Zeabur 的详细部署步骤

### 步骤 1：创建项目

1. 登录 [Zeabur Dashboard](https://dash.zeabur.com)。
2. 点击 **Create Project**（创建项目）。
3. 输入项目名称（如 `a2a-dating`），确认创建。

### 步骤 2：创建服务并从 GitHub 选择仓库

1. 进入刚创建的项目，点击 **Add Service** 或 **Create Service**（创建服务）。
2. 在服务类型中选择 **GitHub**。
3. **若首次使用 GitHub**：
   - 点击 **Configure GitHub**，跳转到 GitHub 安装 **Zeabur** 应用。
   - 选择要授权给 Zeabur 的账号/组织，并选择「All repositories」或指定仓库。
   - 授权完成后回到 Zeabur。
4. 在搜索框中输入你的**仓库名**或**仓库 URL**（例如 `A2A相亲` 或 `your-username/a2a-dating`），从列表中选择该仓库，确认添加。

### 步骤 3：设置根目录（Root Directory）

本仓库是「前后端一体」：根目录下既有 `backend/`（FastAPI）又有 `website/`（静态前端），部署时必须使用**整个仓库**作为构建上下文。

1. 点击已添加的服务，进入该服务。
2. 打开 **Settings**（设置）标签。
3. 找到 **Root Directory**（根目录）：
   - **保持为空**，表示使用仓库根目录。  
   - 不要填写 `backend` 或其它子目录，否则会缺少 `website/` 导致前端无法访问。  

Zeabur 说明：[根目录](https://zeabur.com/docs/zh-CN/deploy/root-directory)。

### 步骤 4：选择 Dockerfile 部署

本项目的应用入口是 **`backend.server:app`**（FastAPI 的 app 在 `backend/server.py` 中），而不是根目录下的单文件 `app.py` 或 `server.py`。根据 [Zeabur Python 文档](https://zeabur.com/docs/zh-CN/guides/python)，默认识别的入口是 `main.py`、`app.py`、`manage.py`、`server.py`、`app/__init__.py` 等；要使用 `backend.server:app` 并同时挂载 `website/`，最稳妥的方式是用 **Dockerfile** 自定义构建与启动。

1. 在服务的 **Settings** 中，找到 **Build Method** / **Deploy with Dockerfile**（或「部署方式」）。
2. 选择 **Dockerfile**（使用仓库根目录下的 `Dockerfile` 部署）。
3. 确认 **Root Directory** 仍为空（仓库根目录），这样 Docker 构建会包含 `backend/` 与 `website/`。

仓库中的 `Dockerfile` 会：

- 使用 Python 3.11，安装 `requirements.txt`，拷贝 `backend/` 和 `website/`。
- 启动命令：`uvicorn backend.server:app --host 0.0.0.0 --port ${PORT}`（Zeabur 会注入 `PORT`）。

Zeabur 说明：[Dockerfile 部署](https://zeabur.com/docs/zh-CN/deploy/dockerfile)。

### 步骤 5：配置环境变量（Variables）

在 Zeabur 中，环境变量在服务级别配置，部署后生效（无需在代码里提交 `.env`）。

1. 在该服务下打开 **Variables**（环境变量）标签。
2. 添加以下变量（键值对）：

| 变量名 | 必填 | 说明 |
|--------|------|------|
| `PORT` | 否 | Zeabur 通常会**自动注入**，一般无需手动添加。 |
| `ANTHROPIC_API_KEY` 或 `TOWOW_ANTHROPIC_API_KEY` | 否 | Claude 畅聊用的 API Key；**不填则使用 Mock 回复**。 |
| `SECONDME_CLIENT_ID` | 可选 | SecondMe OAuth 应用的 Client ID（要用 SecondMe 登录时必填）。 |
| `SECONDME_CLIENT_SECRET` | 可选 | SecondMe OAuth 应用的 Client Secret。 |
| `SECONDME_REDIRECT_URI` | 可选 | **必须**与 MindVerse 后台配置的回调地址**完全一致**（见下文）。 |
| `FRONTEND_BASE_URL` | 可选 | 前后端同域时留空；若前端单独域名可填前端完整地址。 |

**生产环境 SecondMe 回调地址：**

- Zeabur 分配域名一般为：`https://<服务名>.zeabur.app` 或你绑定的自定义域名。
- 回调地址应填：`https://<你的 Zeabur 域名>/api/auth/secondme/callback`
- 在 [MindVerse SecondMe 后台](https://app.mindos.com) 该 OAuth2 应用的「重定向 URI」中**添加上述地址**（与 Zeabur 中的 `SECONDME_REDIRECT_URI` 完全一致）。

Zeabur 说明：[环境变量](https://zeabur.com/docs/zh-CN/deploy/variables)。

### 步骤 6：构建与部署

1. 保存上述设置后，Zeabur 会**自动触发构建**（从 GitHub 拉取代码并按 Dockerfile 构建）。
2. 在 **Deployments** / 部署列表中可查看构建日志；若失败可根据日志排查（常见问题见下文）。
3. 构建成功后会自动部署并启动服务。

### 步骤 7：开启公网访问

1. 在该服务下打开 **Networking**（网络）或 **Public Networking**（公网存取）。
2. 开启**公网访问**（或为服务生成公网域名）。
3. 记下 Zeabur 提供的访问地址，例如：`https://xxx.zeabur.app`。

### 步骤 8：再次核对 SecondMe（若使用）

1. 在 MindVerse 后台确认「重定向 URI」为：`https://<你记下的 Zeabur 域名>/api/auth/secondme/callback`。
2. 在 Zeabur 的 **Variables** 中确认 `SECONDME_REDIRECT_URI` 与上述地址**一字不差**（含 `https`、无末尾斜杠）。

---

## 三、可选：自定义运行命令

若你**未使用 Dockerfile**，而是用 Zeabur 的 Python 自动检测（Nixpacks/zbpack），则需要在 [运行命令](https://zeabur.com/docs/zh-CN/deploy/command-execution) 中自定义启动命令，并保证能从**仓库根目录**运行：

- 启动命令需能执行：`uvicorn backend.server:app --host 0.0.0.0 --port $PORT`  
- 且工作目录为仓库根目录（这样 `backend/` 与 `website/` 都存在）。

**推荐**：直接使用仓库中的 **Dockerfile** 部署，无需再改运行命令。

---

## 四、本地与生产差异速查

| 项目 | 本地 | Zeabur 生产 |
|------|------|-------------|
| 端口 | 8080 | 由 Zeabur 注入 `PORT` |
| 前端 | 同域 `http://localhost:8080` | 同域 `https://xxx.zeabur.app` |
| SecondMe 回调 | `http://localhost:8080/...` | `https://xxx.zeabur.app/api/auth/secondme/callback` |
| 环境变量 | `backend/.env` | Zeabur 控制台 **Variables** |

---

## 五、常见问题

**1. 部署失败：找不到 `backend.server` 或模块错误**  
- 确认 **Root Directory** 为空（使用仓库根目录），且部署方式为 **Dockerfile**，这样镜像内同时包含 `backend/` 和 `website/`。

**2. 前端能打开但接口 404**  
- 确认未把 Root Directory 设为 `backend`；必须使用根目录，由 FastAPI 挂载 `website/` 提供静态页和接口。

**3. SecondMe 登录回调报错**  
- 检查 Zeabur 上的 `SECONDME_REDIRECT_URI` 与 MindVerse 后台「重定向 URI」**完全一致**（协议、域名、路径、无多余斜杠）。
- 确认该服务已开启公网访问且使用 HTTPS。

**4. AI 不回复或报错**  
- 在 Zeabur **Variables** 中配置 `ANTHROPIC_API_KEY` 或 `TOWOW_ANTHROPIC_API_KEY`；未配置时为 Mock 回复。

**5. 想用自定义域名**  
- 在该服务的 **Networking / Domain** 中绑定自定义域名，并在 SecondMe 后台把回调地址改为 `https://<自定义域名>/api/auth/secondme/callback`。

**6. Python 版本 / 包管理器**  
- 当前使用 Dockerfile，镜像内已固定为 Python 3.11 和 `pip`。若改用 Zeabur 的 Python 自动检测，可参考 [部署 Python 项目](https://zeabur.com/docs/zh-CN/guides/python) 中的「设置 Python 版本」「自定义包管理器」。

---

部署完成后，用 Zeabur 提供的 `https://xxx.zeabur.app` 访问即可使用 A2A 相亲（首页、SecondMe 登录、匹配大厅、AI 畅聊、结算页）。
