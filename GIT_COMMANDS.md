# Git 部署命令指南

## 🚀 快速部署（推荐）

### Windows PowerShell
```powershell
cd "e:\code\A2A相亲"
.\deploy.ps1
```

### Linux/Mac
```bash
cd /path/to/A2A相亲
chmod +x deploy.sh
./deploy.sh
```

---

## 📝 手动执行 Git 命令

如果脚本无法运行，可以手动执行以下命令：

### 1. 初始化 Git 仓库（如果还没有）
```bash
git init
```

### 2. 添加所有文件（.gitignore 会自动排除 .env）
```bash
git add .
```

### 3. 提交更改
```bash
git commit -m "feat: 完善 A2A 相亲功能

- ✅ 关闭未登录浏览功能
- ✅ 修复 LLM 引擎初始化（Kimi 优先）
- ✅ 丰富 NPC 角色库（8 个性格鲜明的角色）
- ✅ 实现全自动匹配 API
- ✅ 大幅优化 AI 对话 Prompt（更自然、有个性）
- ✅ 重写大厅 UI（NPC 卡片 + 匹配揭晓弹窗）
- ✅ 修复 XSS 漏洞、EventSource 内存泄漏等安全问题
- ✅ 添加连接池复用、重试机制、错误处理优化"
```

### 4. 创建 GitHub 仓库并连接（如果还没有）

#### 方式一：HTTPS
```bash
git remote add origin https://github.com/你的用户名/仓库名.git
git branch -M main
git push -u origin main
```

#### 方式二：SSH
```bash
git remote add origin git@github.com:你的用户名/仓库名.git
git branch -M main
git push -u origin main
```

### 5. 后续更新（已有远程仓库）
```bash
git add .
git commit -m "你的提交信息"
git push
```

---

## 🔐 重要提醒

### 环境变量配置
**⚠️ 绝对不要提交 `.env` 文件！**

`.gitignore` 已配置排除：
- `.env`
- `backend/.env`

### Zeabur 部署前检查清单

1. ✅ **GitHub 仓库已创建并推送**
2. ✅ **Zeabur 项目已连接 GitHub 仓库**
3. ✅ **环境变量已配置**：
   - `MOONSHOT_API_KEY`（Kimi API Key）
   - `SECONDME_CLIENT_ID`
   - `SECONDME_CLIENT_SECRET`
   - `SECONDME_REDIRECT_URI`（生产环境 URL）
   - `CORS_ORIGINS`（可选，默认 `*`）
4. ✅ **Root Directory** 设置为项目根目录
5. ✅ **使用 Dockerfile** 自动构建
6. ✅ **Public Networking** 已启用

### 查看详细部署文档
```bash
cat docs/DEPLOY_ZEABUR.md
```

---

## 🐛 常见问题

### Q: 推送时提示需要认证？
A: 使用 GitHub Personal Access Token 或配置 SSH 密钥

### Q: 如何查看当前远程仓库？
A: `git remote -v`

### Q: 如何修改远程仓库地址？
A: `git remote set-url origin 新的仓库地址`

### Q: 如何撤销最后一次提交？
A: `git reset --soft HEAD~1`（保留更改）或 `git reset --hard HEAD~1`（丢弃更改）
