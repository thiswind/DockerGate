#!/bin/bash

# DockerGate 环境初始化脚本
# 用途: 从模板文件创建运行时会话文件

set -e  # 遇到错误立即退出

echo "============================================"
echo "DockerGate 环境初始化"
echo "============================================"

# 定义文件路径
TEMPLATE_FILE="shared/auth_sessions_template.json"
RUNTIME_FILE="shared/auth_sessions.json"

# 检查模板文件是否存在
if [ ! -f "$TEMPLATE_FILE" ]; then
    echo "❌ 错误: 模板文件 $TEMPLATE_FILE 不存在"
    echo "请确保项目完整克隆"
    exit 1
fi

# 检查shared目录是否存在
if [ ! -d "shared" ]; then
    echo "📁 创建 shared 目录..."
    mkdir -p shared
fi

# 如果运行时文件已存在，询问是否覆盖
if [ -f "$RUNTIME_FILE" ]; then
    echo "⚠️  运行时文件 $RUNTIME_FILE 已存在"
    read -p "是否要重新初始化？这将清除所有现有会话 [y/N]: " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "📋 跳过初始化，使用现有文件"
        exit 0
    fi
fi

# 复制模板文件到运行时文件
echo "📄 从模板创建运行时会话文件..."
cp "$TEMPLATE_FILE" "$RUNTIME_FILE"

# 验证文件创建成功
if [ -f "$RUNTIME_FILE" ]; then
    echo "✅ 运行时会话文件创建成功: $RUNTIME_FILE"
else
    echo "❌ 错误: 无法创建运行时文件"
    exit 1
fi

echo ""
echo "🎯 初始化完成！"
echo ""
echo "📋 下一步操作:"
echo "   1. 启动服务: docker-compose up -d"
echo "   2. 访问认证: http://localhost:3001"
echo "   3. 测试账户:"
echo "      - aaa / 111 → 蓝紫色页面"
echo "      - bbb / 222 → 绿色页面"
echo "      - ccc / 333 → 粉色页面"
echo ""
echo "🔒 安全提示:"
echo "   - $RUNTIME_FILE 包含运行时会话数据，不会进入版本控制"
echo "   - $TEMPLATE_FILE 是配置模板，已纳入版本控制"
echo ""
echo "============================================" 