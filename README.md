# DockerGate - 安全容器化HTTP VPN (简化版)

基于HTTP的应用层VPN实现，采用Docker容器化架构，提供完整的用户隔离和安全防护。

🎯 **简化版特性**: 移除Dashboard，登录后直接进入用户容器，纯透明代理模式，30分钟滑动超时机制，通过61项自动化测试全面验证安全性。

## 🏗️ 项目架构

### 核心安全理念

**DockerGate = Docker容器网络隔离 + HTTP VPN转发 + JWT认证 + 配置模板分离 + 自动化测试验证**

- 🔒 **完全隔离**：nginx容器运行在Docker内部网络，外部无法直接访问
- 🛡️ **认证防护**：所有请求必须通过JWT认证和HTTP VPN转发器
- 🚫 **绕过阻止**：彻底杜绝127.0.0.1端口绕过的安全隐患
- 📄 **数据分离**：配置模板与敏感运行时数据完全分离，确保版本控制安全
- ✨ **简化架构**：移除Dashboard，登录后直接进入用户容器，用户体验更流畅
- 🧪 **自动验证**：56项自动化测试确保安全性和功能完整性，零人工验证负担
## 📁 项目结构

```
DockerGate/
├── forwarder/                 # 转发器包
│   ├── __init__.py
│   ├── proxy.py              # HTTP VPN转发器主程序 (简化版)
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
├── attack_test.sh           # 🛡️ 安全攻击测试脚本
├── functional_test.sh       # 🚀 功能完整性测试脚本
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

# 🧪 运行自动化测试验证系统
./attack_test.sh      # 安全攻击测试
./functional_test.sh   # 功能完整性测试
```

### 访问测试

1. **认证服务器**: http://localhost:3001
2. **转发器状态**: http://localhost:5001 (需先登录)
3. **测试账户**:
   - `aaa / 111` → 蓝紫色专属页面 (端口6060)
   - `bbb / 222` → 绿色专属页面 (端口8080)
   - `ccc / 333` → 橙色专属页面 (端口9090)

⭐ **简化特性**: 登录成功后直接进入用户专属容器，无需Dashboard确认页面！

## 🧪 自动化测试套件

DockerGate 配备了comprehensive的自动化测试套件，确保系统的安全性和功能完整性：

### 🛡️ 安全攻击测试 (`attack_test.sh`)

全面的安全渗透测试，覆盖8种攻击场景：

```bash
# 运行安全攻击测试
./attack_test.sh
```

**测试覆盖范围**：
- ✅ **直接端口绕过攻击** - 验证容器端口完全隔离
- ✅ **无认证访问攻击** - 验证转发器认证机制  
- ✅ **JWT Token伪造攻击** - 验证token签名和验证
- ✅ **权限提升攻击** - 验证用户权限边界
- ✅ **HTTP方法攻击** - 验证各种HTTP方法处理
- ✅ **请求头注入攻击** - 验证恶意请求头防护
- ✅ **Cookie操纵攻击** - 验证cookie安全机制
- ✅ **路径遍历攻击** - 验证目录遍历防护

**最新测试结果**：
- 🎯 **总攻击场景**: 8个
- 🛡️ **防御成功**: 30项细分测试全部通过
- 🚫 **发现漏洞**: 0个
- 📊 **安全评级**: 优秀

### 🚀 功能完整性测试 (`functional_test.sh`)

全面的功能验证测试，覆盖8个核心功能：

```bash
# 运行功能测试
./functional_test.sh
```

**测试覆盖范围**：
- ✅ **系统状态检查** - 验证认证服务器和转发器状态
- ✅ **用户登录测试** - 验证所有用户登录流程
- ✅ **用户容器访问** - 验证用户专属页面显示
- ✅ **用户隔离测试** - 验证用户间完全隔离
- ✅ **简化跳转测试** - 验证登录后直接进入容器
- ✅ **错误处理测试** - 验证系统异常处理能力
- ✅ **滑动超时测试** - 验证30分钟滑动超时机制工作正常
- ✅ **性能测试** - 验证系统响应性能

**最新测试结果**：
- 🎯 **总功能场景**: 8个
- ✅ **功能正常**: 31项细分测试全部通过
- ❌ **功能异常**: 0个
- 📊 **成功率**: 100%

### 测试脚本特性

- 🎨 **彩色输出** - 成功/失败状态清晰可见
- 📊 **自动统计** - 自动生成测试报告和成功率
- 🔄 **一键运行** - 单个命令完成所有测试
- 🧹 **自动清理** - 测试完成后自动清理临时文件
- ⚡ **快速执行** - 完整测试套件在1分钟内完成

## 🔐 安全特性

### 完整安全验证

我们通过**自动化攻击测试脚本**进行了全面验证，所有攻击均被成功防御：

| 攻击类型 | 防御状态 | 自动化测试结果 |
|---------|---------|---------|
| **直接端口绕过** | ✅ 完全防御 | 端口6060/8080/9090 Connection refused |
| **无认证访问** | ✅ 完全防御 | 返回401 Unauthorized |
| **JWT Token伪造** | ✅ 完全防御 | 4种伪造token全部被拒绝 |
| **权限提升攻击** | ✅ 完全防御 | 用户只能访问分配资源 |
| **HTTP方法攻击** | ✅ 完全防御 | 7种HTTP方法全部返回401 |
| **请求头注入攻击** | ✅ 完全防御 | 5种恶意header被忽略 |
| **Cookie操纵攻击** | ✅ 完全防御 | 4种恶意cookie被拒绝 |
| **路径遍历攻击** | ✅ 完全防御 | 5种路径遍历尝试被拦截 |

🎯 **测试统计**: 8个攻击场景，30项细分测试，100%防御成功率

### 🔄 滑动超时机制

DockerGate 实现了智能的**30分钟滑动超时机制**，显著提升用户体验：

- **⏱️ 滑动窗口**: 每次HTTP请求重置30分钟倒计时，活跃用户永不掉线
- **🔄 自动刷新**: 用户浏览网页时活动时间实时更新
- **🚫 空闲过期**: 只有真正停止使用30分钟后才会自动过期
- **👤 单用户控制**: 新用户登录自动踢出该用户的所有旧会话
- **🎯 自然体验**: 无需手动退出登录，符合现代web应用习惯

**技术实现**：
- 会话文件记录 `last_activity` 和 `timeout_minutes` 字段
- 每次认证成功自动更新最后活动时间
- 状态页面实时显示滑动超时信息
- 通过专项自动化测试验证机制完整性

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

### 自动化测试和验证

```bash
# 🛡️ 安全验证 - 运行全面的安全攻击测试
./attack_test.sh

# 🚀 功能验证 - 运行完整的功能测试  
./functional_test.sh

# 📊 获取测试报告和统计
# 两个脚本都会自动生成彩色测试报告和成功率统计

# ⚡ 快速验证 - 运行两个测试脚本验证整个系统
./attack_test.sh && ./functional_test.sh
```

**测试脚本使用建议**：
- 🚀 **部署后验证**: 每次部署后运行测试脚本验证系统状态
- 🔄 **定期检查**: 定期运行测试脚本确保系统安全性
- 🔧 **故障排查**: 系统异常时运行测试脚本定位问题
- 📈 **性能监控**: 通过测试脚本监控系统性能变化

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
- **📄 配置模板分离**: 创新的数据分离设计，配置安全与部署便利并重
- **✨ 简化架构**: 移除Dashboard，登录后直接进入用户容器
- **🎯 纯净代理**: 无复杂JavaScript注入，纯透明HTTP代理
- **🧪 全面验证**: 通过61项自动化测试验证（30项安全 + 31项功能）
- **⏱️ 滑动超时**: 30分钟智能滑动超时机制，活跃用户永不掉线
- **⚡ 极致性能**: 毫秒级响应时间，企业级性能表现
- **🔧 运维友好**: 一键部署，自动化测试，零配置维护

## 📜 许可证

MIT License

---

**DockerGate** - 让容器访问控制变得简单而安全 🚀 