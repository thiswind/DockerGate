# HTTP VPN 演示项目

基于HTTP的应用层VPN实现，用于演示透明代理和用户权限控制。

## 项目结构

```
http-vpn-demo/
├── forwarder/                 # 转发器包
│   ├── __init__.py
│   ├── proxy.py              # HTTP VPN转发器主程序
│   └── auth.py               # 认证管理模块
├── containers/               # Docker容器配置
│   ├── nginx1/              # 用户AAA的容器
│   ├── nginx2/              # 用户BBB的容器
│   └── nginx3/              # 用户CCC的容器
├── app/                      # Flask认证应用
│   ├── app.py               # 认证服务器
│   └── templates/
│       └── login.html       # 登录页面
├── shared/                   # 共享数据
│   └── auth_sessions.json   # 认证会话文件
├── requirements.txt         # Python依赖
└── README.md               # 项目说明
```

## 系统架构

### 核心组件

1. **Flask认证应用** (端口3001)
   - 用户登录验证
   - JWT Token生成
   - 会话管理

2. **HTTP VPN转发器** (端口5000)
   - 单端口多用户路由
   - 认证验证和请求清理
   - 响应注入认证机制

3. **Nginx容器集群**
   - nginx1: 127.0.0.1:6060 (用户aaa)
   - nginx2: 127.0.0.1:8080 (用户bbb) 
   - nginx3: 127.0.0.1:9090 (用户ccc)

### 工作流程

```
用户浏览器 → Flask认证(3001) → 登录成功 → 跳转到转发器(5000) → 根据认证路由到对应容器
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

### 2. 启动Docker容器

```bash
# 启动nginx容器
cd containers/nginx1 && docker-compose up -d
cd ../nginx2 && docker-compose up -d  
cd ../nginx3 && docker-compose up -d
```

### 3. 启动认证服务器

```bash
cd app
python app.py
```

### 4. 启动转发器

```bash
# 新建终端窗口
cd forwarder
python proxy.py
```

### 5. 访问测试

1. 浏览器访问: http://localhost:3001
2. 使用测试账户登录:
   - `aaa / 111` → 路由到nginx1容器
   - `bbb / 222` → 路由到nginx2容器
   - `ccc / 333` → 路由到nginx3容器
3. 登录成功后自动跳转到转发器
4. 看到对应用户的专属页面

## 测试账户

| 用户名 | 密码 | 目标容器 | 端口 |
|--------|------|----------|------|
| aaa    | 111  | nginx-user-aaa | 6060 |
| bbb    | 222  | nginx-user-bbb | 8080 |
| ccc    | 333  | nginx-user-ccc | 9090 |

## 安全特性验证

### 1. 端口隔离测试

```bash
# 直接访问容器端口（应该失败）
curl http://localhost:6060/  # Connection refused
curl http://localhost:8080/  # Connection refused
curl http://localhost:9090/  # Connection refused
```

### 2. 认证绕过测试

```bash
# 无认证访问转发器（应该返回401）
curl http://localhost:5000/
```

### 3. 用户隔离测试

登录用户aaa后，只能看到nginx1的内容，无法访问其他用户的容器。

## 技术特点

### HTTP应用层VPN

- **透明代理**: 对Docker容器完全透明，无需修改容器内应用
- **认证注入**: 在响应中自动注入JavaScript认证机制
- **请求清理**: 从转发请求中移除认证信息
- **智能路由**: 根据用户身份自动路由到对应容器

### 安全机制

- **JWT Token认证**: 基于时间的token验证
- **端口隔离**: 容器只绑定127.0.0.1，外部无法直接访问
- **用户权限控制**: 每个用户只能访问分配的容器
- **会话管理**: 实时的认证状态同步

## 调试和监控

### 查看系统状态

- 认证服务器状态: http://localhost:3001/status
- 活跃会话API: http://localhost:3001/api/get_user_sessions

### 日志输出

- Flask应用会显示登录/退出日志
- 转发器会显示请求路由日志
- 浏览器控制台会显示认证注入日志

## 故障排除

### 1. 容器无法启动

```bash
# 检查端口占用
netstat -tlnp | grep -E "(6060|8080|9090)"

# 重启容器
docker-compose down && docker-compose up -d
```

### 2. 认证失败

- 检查`shared/auth_sessions.json`文件是否存在
- 确认Flask应用和转发器使用相同的secret key
- 查看浏览器Cookie是否正确设置

### 3. 转发失败

- 确认目标容器正在运行
- 检查容器端口绑定是否正确
- 查看转发器日志输出

## 扩展功能

### 添加新用户

1. 在`app/app.py`的`USERS`字典中添加用户
2. 在`shared/auth_sessions.json`的`user_mappings`中添加映射
3. 创建对应的nginx容器配置

### 自定义容器

- 替换nginx镜像为其他web应用
- 修改容器端口映射
- 更新HTML页面内容

## 许可证

MIT License 