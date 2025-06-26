#!/bin/bash

echo "启动HTTP VPN演示项目的Docker容器..."

# 启动nginx1容器 (用户aaa)
echo "启动nginx1容器 (用户aaa) - 端口6060..."
cd containers/nginx1
docker-compose up -d
cd ../..

# 启动nginx2容器 (用户bbb)  
echo "启动nginx2容器 (用户bbb) - 端口8080..."
cd containers/nginx2
docker-compose up -d
cd ../..

# 启动nginx3容器 (用户ccc)
echo "启动nginx3容器 (用户ccc) - 端口9090..."
cd containers/nginx3
docker-compose up -d
cd ../..

echo ""
echo "所有容器启动完成！"
echo ""
echo "容器状态:"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
echo ""
echo "下一步："
echo "1. 启动认证服务器: cd app && python app.py"
echo "2. 启动转发器: python start_proxy.py"
echo "3. 访问: http://localhost:3001" 