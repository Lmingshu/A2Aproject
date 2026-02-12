# A2A 相亲项目 - Git 部署脚本 (PowerShell)
# 使用方法：在项目根目录执行 .\deploy.ps1

Write-Host "🚀 开始部署 A2A 相亲项目到 GitHub..." -ForegroundColor Cyan

# 1. 初始化 Git 仓库（如果还没有）
if (-not (Test-Path .git)) {
    Write-Host "📦 初始化 Git 仓库..." -ForegroundColor Yellow
    git init
}

# 2. 检查是否有未提交的更改
$status = git status --porcelain
if ($status) {
    Write-Host "📝 添加所有更改的文件..." -ForegroundColor Yellow
    git add .
    
    Write-Host "💾 提交更改..." -ForegroundColor Yellow
    git commit -m "feat: 完善 A2A 相亲功能

- ✅ 关闭未登录浏览功能
- ✅ 修复 LLM 引擎初始化（Kimi 优先）
- ✅ 丰富 NPC 角色库（8 个性格鲜明的角色）
- ✅ 实现全自动匹配 API
- ✅ 大幅优化 AI 对话 Prompt（更自然、有个性）
- ✅ 重写大厅 UI（NPC 卡片 + 匹配揭晓弹窗）
- ✅ 修复 XSS 漏洞、EventSource 内存泄漏等安全问题
- ✅ 添加连接池复用、重试机制、错误处理优化"
} else {
    Write-Host "✅ 没有需要提交的更改" -ForegroundColor Green
}

# 3. 检查远程仓库
$remotes = git remote
if ($remotes -contains "origin") {
    Write-Host "📤 推送到远程仓库..." -ForegroundColor Yellow
    $branch = git branch --show-current
    if ($branch -eq "main") {
        git push -u origin main
    } elseif ($branch -eq "master") {
        git push -u origin master
    } else {
        Write-Host "⚠️  当前分支: $branch，推送到 origin/$branch" -ForegroundColor Yellow
        git push -u origin $branch
    }
} else {
    Write-Host ""
    Write-Host "⚠️  未配置远程仓库！" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "请先创建 GitHub 仓库，然后执行：" -ForegroundColor Cyan
    Write-Host "  git remote add origin https://github.com/你的用户名/仓库名.git" -ForegroundColor White
    Write-Host "  git branch -M main" -ForegroundColor White
    Write-Host "  git push -u origin main" -ForegroundColor White
    Write-Host ""
    Write-Host "或者如果使用 SSH：" -ForegroundColor Cyan
    Write-Host "  git remote add origin git@github.com:你的用户名/仓库名.git" -ForegroundColor White
    Write-Host "  git branch -M main" -ForegroundColor White
    Write-Host "  git push -u origin main" -ForegroundColor White
}

Write-Host ""
Write-Host "✅ Git 操作完成！" -ForegroundColor Green
Write-Host ""
Write-Host "📋 下一步：" -ForegroundColor Cyan
Write-Host "1. 如果使用 Zeabur 部署，请确保：" -ForegroundColor White
Write-Host "   - 在 Zeabur 项目设置中连接 GitHub 仓库" -ForegroundColor Gray
Write-Host "   - 配置环境变量（MOONSHOT_API_KEY、SECONDME_CLIENT_ID 等）" -ForegroundColor Gray
Write-Host "   - 设置 Root Directory 为项目根目录" -ForegroundColor Gray
Write-Host "   - 使用 Dockerfile 自动构建" -ForegroundColor Gray
Write-Host ""
Write-Host "2. 查看部署文档：docs/DEPLOY_ZEABUR.md" -ForegroundColor White
