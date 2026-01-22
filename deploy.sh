#!/bin/bash

# Video API - GitHub 部署脚本
# 用途：快速初始化 Git 仓库并推送到 GitHub

set -e

echo "=========================================="
echo "Video API - GitHub 部署脚本"
echo "=========================================="
echo ""

# 检查是否已经初始化 Git
if [ ! -d ".git" ]; then
    echo "📦 初始化 Git 仓库..."
    git init
    echo "✅ Git 仓库初始化完成"
else
    echo "✅ Git 仓库已存在"
fi

# 检查是否有远程仓库
if git remote | grep -q "origin"; then
    echo "✅ 远程仓库已配置"
    git remote -v
else
    echo ""
    echo "⚠️  未配置远程仓库"
    echo "请输入 GitHub 仓库地址（例如：https://github.com/username/video-api.git）："
    read REPO_URL
    
    if [ -z "$REPO_URL" ]; then
        echo "❌ 仓库地址不能为空"
        exit 1
    fi
    
    echo "🔗 添加远程仓库..."
    git remote add origin "$REPO_URL"
    echo "✅ 远程仓库配置完成"
fi

echo ""
echo "📝 添加文件到 Git..."
git add .

echo ""
echo "💬 提交更改..."
git commit -m "feat: add Docker support and GitHub Actions CI/CD" || echo "⚠️  没有新的更改需要提交"

echo ""
echo "🚀 推送到 GitHub..."
git branch -M main
git push -u origin main

echo ""
echo "=========================================="
echo "✅ 部署完成！"
echo "=========================================="
echo ""
echo "📋 后续步骤："
echo "1. 访问 GitHub 仓库查看代码"
echo "2. 进入 Settings → Actions → General 启用 GitHub Actions"
echo "3. 进入 Settings → Actions → General → Workflow permissions"
echo "   选择 'Read and write permissions'"
echo "4. 推送代码后，GitHub Actions 会自动构建 Docker 镜像"
echo "5. 镜像地址：ghcr.io/$(git remote get-url origin | sed 's/.*github.com[:/]\(.*\)\.git/\1/' | tr '[:upper:]' '[:lower:]'):latest"
echo ""
echo "📚 详细文档请查看 DEPLOYMENT.md"
echo ""

