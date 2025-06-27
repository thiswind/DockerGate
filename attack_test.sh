#!/bin/bash

# HTTP VPN 系统 - 综合攻击测试脚本
# 用于验证简化后系统的安全性

echo "🎯========================================🎯"
echo "   HTTP VPN 简化系统 - 综合攻击测试"
echo "🎯========================================🎯"
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 测试结果计数
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# 辅助函数
print_test_header() {
    echo -e "\n${BLUE}=== 🚨 攻击测试$1: $2 ===${NC}"
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
}

print_success() {
    echo -e "${GREEN}✅ 防御成功: $1${NC}"
    PASSED_TESTS=$((PASSED_TESTS + 1))
}

print_failure() {
    echo -e "${RED}❌ 安全漏洞: $1${NC}"
    FAILED_TESTS=$((FAILED_TESTS + 1))
}

print_info() {
    echo -e "${YELLOW}ℹ️  $1${NC}"
}

# 首先获取有效的认证token用于某些测试
echo -e "${BLUE}📋 准备测试环境...${NC}"
print_info "获取有效的认证token..."

# 登录获取认证token
curl -s -X POST http://localhost:3001/login -d "username=aaa&password=111" -c temp_cookies.txt > /dev/null 2>&1
if [ -f temp_cookies.txt ]; then
    VALID_TOKEN=$(grep auth_token temp_cookies.txt | awk '{print $7}' 2>/dev/null)
    if [ -n "$VALID_TOKEN" ]; then
        print_info "已获取用户aaa的有效token"
    else
        print_info "警告: 无法获取有效token，部分测试可能受影响"
    fi
else
    print_info "警告: 登录失败，部分测试可能受影响"
fi

echo ""

# 攻击测试1: 直接端口绕过攻击
print_test_header "1" "直接端口绕过攻击"
print_info "尝试直接访问nginx容器端口，绕过转发器..."

echo -n "测试端口6060: "
if timeout 5 curl -s http://127.0.0.1:6060/ > /dev/null 2>&1; then
    print_failure "端口6060可直接访问，存在绕过风险"
else
    print_success "端口6060访问被拒绝"
fi

echo -n "测试端口8080: "
if timeout 5 curl -s http://127.0.0.1:8080/ > /dev/null 2>&1; then
    print_failure "端口8080可直接访问，存在绕过风险"
else
    print_success "端口8080访问被拒绝"
fi

echo -n "测试端口9090: "
if timeout 5 curl -s http://127.0.0.1:9090/ > /dev/null 2>&1; then
    print_failure "端口9090可直接访问，存在绕过风险"
else
    print_success "端口9090访问被拒绝"
fi

# 攻击测试2: 无认证访问攻击
print_test_header "2" "无认证访问攻击"
print_info "尝试在无认证情况下访问转发器..."

RESPONSE=$(curl -s -w "%{http_code}" http://localhost:5001/ -o temp_response.txt)
if [ "$RESPONSE" = "401" ]; then
    print_success "转发器正确返回401未授权状态"
else
    print_failure "转发器未正确处理无认证请求 (状态码: $RESPONSE)"
fi

# 攻击测试3: JWT Token伪造攻击
print_test_header "3" "JWT Token伪造攻击"
print_info "尝试使用伪造的JWT token访问..."

# 伪造token测试
FAKE_TOKENS=(
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VybmFtZSI6ImFkbWluIiwidGFyZ2V0X3BvcnQiOjgwODB9.fake_signature"
    "fake.jwt.token"
    "eyJhbGciOiJub25lIiwidHlwIjoiSldUIn0.eyJ1c2VybmFtZSI6ImFhYSIsInRhcmdldF9wb3J0Ijo2MDYwfQ."
    ""
)

for i in "${!FAKE_TOKENS[@]}"; do
    TOKEN="${FAKE_TOKENS[$i]}"
    echo -n "测试伪造token $((i+1)): "
    
    RESPONSE=$(curl -s -w "%{http_code}" http://localhost:5001/ -H "Cookie: auth_token=$TOKEN" -o /dev/null)
    if [ "$RESPONSE" = "401" ]; then
        print_success "伪造token被正确拒绝"
    else
        print_failure "伪造token被接受 (状态码: $RESPONSE)"
    fi
done

# 攻击测试4: 权限提升攻击
print_test_header "4" "权限提升攻击"
print_info "尝试使用用户aaa的token访问其他用户资源..."

if [ -n "$VALID_TOKEN" ]; then
    # 尝试通过修改请求参数来访问其他用户资源
    echo -n "尝试访问用户bbb资源: "
    
    # 这里我们测试是否能通过某种方式访问到其他用户的内容
    # 由于当前系统直接基于token中的target_port路由，理论上应该无法跨用户访问
    RESPONSE=$(curl -s http://localhost:5001/ -H "Cookie: auth_token=$VALID_TOKEN")
    
    # 检查响应中是否包含用户aaa的标识
    if echo "$RESPONSE" | grep -q "用户AAA"; then
        print_success "用户aaa只能访问自己的资源"
    elif echo "$RESPONSE" | grep -q "用户BBB\|用户CCC"; then
        print_failure "检测到跨用户访问，存在权限提升风险"
    else
        print_info "无法确定权限提升测试结果"
    fi
else
    print_info "跳过权限提升测试 (无有效token)"
fi

# 攻击测试5: HTTP方法攻击
print_test_header "5" "HTTP方法攻击"
print_info "测试各种HTTP方法的处理..."

METHODS=("GET" "POST" "PUT" "DELETE" "PATCH" "OPTIONS" "HEAD")

for METHOD in "${METHODS[@]}"; do
    echo -n "测试$METHOD方法: "
    
    RESPONSE=$(curl -s -w "%{http_code}" -X "$METHOD" http://localhost:5001/ -o /dev/null)
    if [ "$RESPONSE" = "401" ]; then
        print_success "未认证的$METHOD请求被正确拒绝"
    else
        print_info "未认证的$METHOD请求返回状态码: $RESPONSE"
    fi
done

# 攻击测试6: 请求头注入攻击
print_test_header "6" "请求头注入攻击"
print_info "尝试通过恶意请求头绕过认证..."

MALICIOUS_HEADERS=(
    "Authorization: Bearer fake_token"
    "X-Forwarded-For: 127.0.0.1"
    "X-Real-IP: localhost"
    "X-Original-URL: /admin"
    "X-Rewrite-URL: /admin"
)

for HEADER in "${MALICIOUS_HEADERS[@]}"; do
    echo -n "测试恶意头: $(echo "$HEADER" | cut -d: -f1): "
    
    RESPONSE=$(curl -s -w "%{http_code}" http://localhost:5001/ -H "$HEADER" -o /dev/null)
    if [ "$RESPONSE" = "401" ]; then
        print_success "恶意请求头被正确忽略"
    else
        print_failure "恶意请求头可能影响了认证 (状态码: $RESPONSE)"
    fi
done

# 攻击测试7: Cookie操纵攻击
print_test_header "7" "Cookie操纵攻击"
print_info "尝试通过操纵cookie绕过认证..."

MALICIOUS_COOKIES=(
    "auth_token=admin_token"
    "auth_token=; session_id=admin_session"
    "session_id=../../../etc/passwd"
    "auth_token=null"
)

for COOKIE in "${MALICIOUS_COOKIES[@]}"; do
    echo -n "测试恶意cookie: "
    
    RESPONSE=$(curl -s -w "%{http_code}" http://localhost:5001/ -H "Cookie: $COOKIE" -o /dev/null)
    if [ "$RESPONSE" = "401" ]; then
        print_success "恶意cookie被正确拒绝"
    else
        print_failure "恶意cookie被接受 (状态码: $RESPONSE)"
    fi
done

# 攻击测试8: 路径遍历攻击
print_test_header "8" "路径遍历攻击"
print_info "尝试通过路径遍历访问敏感文件..."

MALICIOUS_PATHS=(
    "/../../../etc/passwd"
    "/..%2f..%2f..%2fetc%2fpasswd"
    "/.env"
    "/docker-compose.yml"
    "/app"
)

for PATH in "${MALICIOUS_PATHS[@]}"; do
    echo -n "测试路径: $PATH: "
    
    RESPONSE=$(curl -s -w "%{http_code}" "http://localhost:5001$PATH" -o /dev/null)
    if [ "$RESPONSE" = "401" ]; then
        print_success "路径遍历被认证拦截"
    elif [ "$RESPONSE" = "404" ]; then
        print_info "路径不存在 (这是预期的)"
    else
        print_failure "路径遍历可能成功 (状态码: $RESPONSE)"
    fi
done

# 清理临时文件
rm -f temp_cookies.txt temp_response.txt

# 输出测试总结
echo ""
echo "🎯========================================🎯"
echo "           攻击测试总结报告"
echo "🎯========================================🎯"
echo -e "${BLUE}总测试数量: $TOTAL_TESTS${NC}"
echo -e "${GREEN}防御成功: $PASSED_TESTS${NC}"
echo -e "${RED}发现漏洞: $FAILED_TESTS${NC}"

if [ $FAILED_TESTS -eq 0 ]; then
    echo -e "\n${GREEN}🛡️  恭喜！系统通过了所有安全测试！${NC}"
    echo -e "${GREEN}💪 HTTP VPN 简化版安全防护表现优秀！${NC}"
    exit 0
else
    echo -e "\n${RED}⚠️  发现 $FAILED_TESTS 个安全问题，需要修复！${NC}"
    echo -e "${YELLOW}🔧 建议检查上述失败的测试项目并进行安全加固。${NC}"
    exit 1
fi 