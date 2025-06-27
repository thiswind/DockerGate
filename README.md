# DockerGate - 安全容器化HTTP VPN

基于HTTP的应用层VPN实现，采用Docker容器化架构，提供完整的用户隔离和安全防护。

## 🏗️ 项目架构

### 核心安全理念

**DockerGate = Docker容器网络隔离 + HTTP VPN转发 + JWT认证 + 配置模板分离**

- 🔒 **完全隔离**：nginx容器运行在Docker内部网络，外部无法直接访问
- 🛡️ **认证防护**：所有请求必须通过JWT认证和HTTP VPN转发器
- 🚫 **绕过阻止**：彻底杜绝127.0.0.1端口绕过的安全隐患
- 📄 **数据分离**：配置模板与敏感运行时数据完全分离，确保版本控制安全
## 📁 项目结构

```
DockerGate/
├── forwarder/                 # 转发器包
│   ├── __init__.py
│   ├── proxy.py              # HTTP VPN转发器主程序
│   └── auth.py               # JWT认证管理模块
├── app/                      # Flask认证应用
│   ├── app.py               # 认证服务器
│   └── templates/
│       └── login.html       # 登录页面
├── containers/               # 单独容器配置(已废弃)
│   └── ...                  # 保留用于参考
├── shared/                         # 共享数据
│   ├── auth_sessions_template.json # 认证会话模板文件(进入版本控制)
│   └── auth_sessions.json         # 运行时会话文件(不进入版本控制)
├── Dockerfile.auth          # 认证服务器镜像
├── Dockerfile.proxy         # HTTP VPN转发器镜像
├── docker-compose.yml       # 统一容器编排
├── init_session.sh          # 环境初始化脚本
├── requirements.txt         # Python依赖
└── README.md               # 项目说明
```

## 🏛️ 系统架构

### 容器化组件

```
┌─────────────────────────────────────────────────────────────┐
│                    Docker Network: vpn-internal             │
│                                                             │
│  ┌──────────────┐  ┌──────────────┐  ┌─────────────────┐   │
│  │ auth-server  │  │ vpn-proxy    │  │ nginx-user-aaa  │   │
│  │   :3001      │  │    :5001     │  │      :80        │   │
│  └──────────────┘  └──────────────┘  └─────────────────┘   │
│                                                             │
│                     ┌─────────────────┐  ┌────────────────┐ │
│                     │ nginx-user-bbb  │  │ nginx-user-ccc │ │
│                     │      :80        │  │      :80       │ │
│                     └─────────────────┘  └────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                              │
                    ┌─────────┴─────────┐
                    │   宿主机端口      │
                    │  3001 ← 认证     │
                    │  5001 ← 转发     │
                    └───────────────────┘
```

### 安全工作流程

```
用户浏览器 
    ↓ (http://localhost:3001)
Flask认证服务器 (容器内)
    ↓ JWT Token + 302跳转
HTTP VPN转发器 (容器内)
    ↓ 认证验证 + 路由决策
nginx用户容器 (Docker内部网络，完全隔离)
    ↓ 响应 + 认证注入
用户浏览器 (看到专属页面)
```

## 🚀 快速部署

### 环境初始化

⭐ **重要**: DockerGate 采用配置模板分离架构，首次部署必须进行环境初始化！
首次部署或重新初始化环境时，需要运行初始化脚本：

```bash
# 初始化会话文件（从模板创建运行时文件）
./init_session.sh
```

### 一键启动所有服务

```bash
# 1. 构建并启动所有容器
docker-compose up -d

# 2. 查看服务状态
docker-compose ps

# 3. 查看日志
docker-compose logs -f
```

### 完整部署流程

```bash
# 克隆项目
git clone <repository-url>
cd DockerGate

# 环境初始化
./init_session.sh

# 启动服务
docker-compose up -d

# 验证部署
curl http://localhost:3001
```

### 访问测试

1. **认证服务器**: http://localhost:3001
2. **转发器状态**: http://localhost:5001 (需先登录)
3. **测试账户**:
   - `aaa / 111` → 蓝紫色专属页面
   - `bbb / 222` → 绿色专属页面  
   - `ccc / 333` → 粉色专属页面

## 🔐 安全特性

### 完整安全验证

我们进行了全面的**安全攻击测试**，所有攻击均被成功防御：

| 攻击类型 | 防御状态 | 验证结果 |
|---------|---------|---------|
| **直接端口绕过** | ✅ 完全防御 | 端口6060/8080/9090无法访问 |
| **无认证访问** | ✅ 完全防御 | 返回401 Unauthorized |
| **JWT Token伪造** | ✅ 完全防御 | 伪造token被拒绝 |
| **权限提升攻击** | ✅ 完全防御 | 用户只能访问分配资源 |
| **HTTP方法攻击** | ✅ 完全防御 | OPTIONS/DELETE/PUT被拒绝 |
| **路径遍历攻击** | ✅ 完全防御 | ../etc/passwd返回404 |
| **Header注入攻击** | ✅ 完全防御 | X-Forwarded-For被忽略 |
| **Session劫持** | ✅ 完全防御 | 伪造session被拒绝 |
| **并发请求攻击** | ✅ 完全防御 | 系统处理稳定 |

### 安全机制层次

1. **🔒 认证层**: JWT Token + Session管理
2. **🛡️ 授权层**: 用户权限严格隔离  
3. **🚫 网络层**: Docker内部网络完全隔离
4. **🔄 代理层**: 所有流量强制通过转发器
5. **🧹 清理层**: 认证信息自动清理
6. **📄 数据分离**: 创新的模板分离架构，配置安全与运行时数据完全隔离

### 🆕 架构创新: 配置模板分离

DockerGate 采用了创新的**配置模板分离架构**，解决了企业级部署中的核心痛点：

- **🎯 问题**: 传统方案中，配置文件要么包含敏感数据不能进版本控制，要么需要复杂的配置管理
- **💡 创新**: 分离配置模板与运行时数据，通过`init_session.sh`脚本实现优雅的环境初始化
- **🏆 优势**: 既保证了敏感数据安全，又确保了项目的可部署性和团队协作效率

**这种架构设计让DockerGate成为了企业级HTTP VPN解决方案的标杆！**
### 数据安全实践

- **模板文件** (`shared/auth_sessions_template.json`)：
  - 包含基础用户配置
  - 纳入版本控制
  - 不含敏感信息

- **运行时文件** (`shared/auth_sessions.json`)：
  - 包含实际会话数据和JWT tokens
  - 不进入版本控制
  - 通过`init_session.sh`从模板创建

## 🧪 安全测试

### 端口隔离验证

```bash
# 旧架构的安全隐患（已解决）
curl http://localhost:6060/  # 以前可以绕过认证
curl http://localhost:8080/  # 以前可以绕过认证
curl http://localhost:9090/  # 以前可以绕过认证

# 新架构的安全保障
curl http://localhost:6060/  # Connection refused ✅
curl http://localhost:8080/  # Connection refused ✅  
curl http://localhost:9090/  # Connection refused ✅
```

### 认证绕过测试

```bash
# 无认证访问转发器
curl http://localhost:5001/
# 结果: 401 Unauthorized ✅

# JWT Token伪造攻击
curl -H "Authorization: Bearer fake_token" http://localhost:5001/
# 结果: 401 Unauthorized ✅
```

### 权限提升测试

```bash
# 即使修改URL参数，用户仍只能访问自己的资源
# AAA用户尝试访问其他端口
curl -H "Cookie: auth_token=$AAA_TOKEN" "http://localhost:5001/?target_port=8080"
# 结果: 仍然返回AAA专属页面 ✅
```

### 配置模板分离验证

```bash
# 验证模板文件安全性
cat shared/auth_sessions_template.json  # 只有基础配置，无敏感信息 ✅

# 验证运行时文件隔离
git check-ignore shared/auth_sessions.json  # 被正确忽略 ✅

# 验证初始化流程
./init_session.sh  # 从模板安全创建运行时文件 ✅```

## 🔧 运维管理

### 服务管理

```bash
# 停止所有服务
docker-compose down

# 重启服务
docker-compose restart

# 查看容器状态
docker-compose ps

# 查看特定服务日志
docker-compose logs auth-server
docker-compose logs vpn-proxy
```

### 监控和调试

- **认证服务器状态**: http://localhost:3001/status
- **会话API**: http://localhost:3001/api/get_user_sessions
- **容器网络**: `docker network inspect dockergate_vpn-internal`

### 用户管理

编辑 `app/app.py` 中的 `USERS` 字典添加新用户：

```python
USERS = {
    'aaa': {'password': '111', 'target_port': 6060},
    'bbb': {'password': '222', 'target_port': 8080}, 
    'ccc': {'password': '333', 'target_port': 9090},
    'newuser': {'password': 'newpass', 'target_port': 7070},  # 新用户
}
```

## 🆚 架构对比

### 旧架构问题
- ❌ nginx容器暴露在127.0.0.1
- ❌ 可以直接访问端口绕过认证
- ❌ 存在安全隐患

### 新架构优势  
- ✅ nginx容器完全在Docker内部网络
- ✅ 外部无法直接访问任何后端服务
- ✅ 强制所有流量通过HTTP VPN转发器
- ✅ 通过全面安全测试验证
- ✅ 配置模板与运行时数据完全分离
- ✅ 敏感会话信息永不进入版本控制
## 🛠️ 故障排除

### 容器启动失败

```bash
# 检查端口占用
netstat -tlnp | grep -E "(3001|5001)"

# 清理并重新构建
docker-compose down -v
docker-compose build --no-cache
docker-compose up -d
```

### 网络连接问题

```bash
# 检查Docker网络
docker network ls
docker network inspect dockergate_vpn-internal

# 检查容器间连通性
docker-compose exec vpn-proxy ping nginx-user-aaa
```

### 认证问题

- 检查 `shared/auth_sessions.json` 是否存在
  ```bash
  # 如果文件不存在，运行初始化脚本
  ./init_session.sh
  ```
- 确认所有容器的时间同步
- 查看认证服务器和转发器日志

### 环境初始化问题

⭐ **重要**: DockerGate 采用配置模板分离架构，首次部署必须进行环境初始化！
```bash
# 重新初始化环境
./init_session.sh

# 检查模板文件是否存在
ls -la shared/auth_sessions_template.json

# 检查脚本权限
ls -la init_session.sh

# 如果权限不足，添加执行权限
chmod +x init_session.sh
```

## 📝 开发说明

### 镜像构建

```bash
# 构建认证服务器镜像
docker build -f Dockerfile.auth -t dockergate-auth .

# 构建转发器镜像  
docker build -f Dockerfile.proxy -t dockergate-proxy .
```

### 本地开发

如需本地开发调试，可以：

```bash
# 只启动nginx容器
docker-compose up -d nginx-user-aaa nginx-user-bbb nginx-user-ccc

# 本地运行认证服务器
cd app && python app.py

# 本地运行转发器  
python start_proxy.py
```

## 🎯 技术亮点

- **🔒 零信任架构**: 默认拒绝，显式授权
- **🛡️ 深度防御**: 多层安全机制
- **🚫 完全隔离**: Docker网络边界保护  
- **🔄 透明代理**: 对后端应用完全透明
- **📄 配置模板分离**: 创新的数据分离设计，配置安全与部署便利并重- **🧪 安全验证**: 通过全面攻击测试

## 📜 许可证

MIT License

---

**DockerGate** - 让容器访问控制变得简单而安全 🚀 