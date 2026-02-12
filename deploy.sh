#!/bin/bash
# A2A 相亲项目 - Git 部署脚本
# 使用方法：在项目根目录执行 ./deploy.sh

echo "🚀 开始部署 A2A 相亲项目到 GitHub..."

# 1. 初始化 Git 仓库（如果还没有）
if [ ! -d .git ]; then
    echo "📦 初始化 Git 仓库..."
    git init
fi

# 2. 检查是否有未提交的更改
if [ -n "$(git status --porcelain)" ]; then
    echo "📝 添加所有更改的文件..."
    git add .
    
    echo "💾 提交更改..."
    git commit -m "feat: 完善 A2A 相亲功能

- ✅ 关闭未登录浏览功能
- ✅ 修复 LLM 引擎初始化（Kimi 优先）
- ✅ 丰富 NPC 角色库（8 个性格鲜明的角色）
- ✅ 实现全自动匹配 API
- ✅ 大幅优化 AI 对话 Prompt（更自然、有个性）
- ✅ 重写大厅 UI（NPC 卡片 + 匹配揭晓弹窗）
- ✅ 修复 XSS 漏洞、EventSource 内存泄漏等安全问题
- ✅ 添加连接池复用、重试机制、错误处理优化"
else
    echo "✅ 没有需要提交的更改"
fi

# 3. 检查远程仓库
if git remote | grep -q "^origin$"; then
    echo "📤 推送到远程仓库..."
    git push -u origin main || git push -u origin master
else
    echo ""
    echo "⚠️  未配置远程仓库！"
    echo ""
    echo "请先创建 GitHub 仓库，然后执行："
    echo "  git remote add origin https://github.com/你的用户名/仓库名.git"
    echo "  git branch -M main"
    echo "  git push -u origin main"
    echo ""
    echo "或者如果使用 SSH："
    echo "  git remote add origin git@github.com:你的用户名/仓库名.git"
    echo "  git branch -M main"
    echo "  git push -u origin main"
fi

echo ""
echo "✅ Git 操作完成！"
echo ""
echo "📋 下一步："
echo "1. 如果使用 Zeabur 部署，请确保："
echo "   - 在 Zeabur 项目设置中连接 GitHub 仓库"
echo "   - 配置环境变量（MOONSHOT_API_KEY、SECONDME_CLIENT_ID 等）"
echo "   - 设置 Root Directory 为项目根目录"
echo "   - 使用 Dockerfile 自动构建"
echo ""
echo "2. 查看部署文档：docs/DEPLOY_ZEABUR.md"
