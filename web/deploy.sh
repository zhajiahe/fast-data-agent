#!/bin/bash

# 前端部署脚本

set -e

echo "🚀 开始构建前端..."

# 安装依赖
echo "📦 安装依赖..."
pnpm install

# 构建生产版本
echo "🔨 构建生产版本..."
pnpm build

echo "✅ 构建完成！"
echo "📁 构建产物位于: dist/"
echo ""
echo "部署选项："
echo "1. 部署到 Nginx: 将 dist/ 目录内容复制到 Nginx web 目录"
echo "2. 部署到 FastAPI: 将 dist/ 内容复制到后端静态文件目录"
echo ""
echo "示例："
echo "  sudo cp -r dist/* /var/www/html/web/"
echo "  或"
echo "  cp -r dist/* ../static/web/"
