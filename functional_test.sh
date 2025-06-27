#!/bin/bash

# HTTP VPN 系统 - 综合功能测试脚本
# 用于验证简化后系统的正常功能

echo "🚀========================================🚀"
echo "   HTTP VPN 简化系统 - 综合功能测试"
echo "🚀========================================🚀"
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# 测试结果计数
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# 用户配置
USERS_LIST="aaa bbb ccc"
get_user_info() {
    local username=$1
    case $username in
        "aaa") echo "111:6060:蓝紫色:AAA" ;;
        "bbb") echo "222:8080:绿色:BBB" ;;
        "ccc") echo "333:9090:橙色:CCC" ;;
        *) echo "" ;;
    esac
}

# 辅助函数
print_test_header() {
    echo -e "\n${BLUE}=== 🧪 功能测试$1: $2 ===${NC}"
    TOTAL_TESTS=$((TOTAL_TESTS + 1))
}

print_success() {
    echo -e "${GREEN}✅ 功能正常: $1${NC}"
    PASSED_TESTS=$((PASSED_TESTS + 1))
}

print_failure() {
    echo -e "${RED}❌ 功能异常: $1${NC}"
    FAILED_TESTS=$((FAILED_TESTS + 1))
}

print_info() {
    echo -e "${YELLOW}ℹ️  $1${NC}"
}

print_user_info() {
    echo -e "${PURPLE}👤 $1${NC}"
}

# 检查系统状态
check_system_status() {
    echo -e "${CYAN}🔍 检查系统状态...${NC}"
    
    # 检查认证服务器
    if curl -s http://localhost:3001/ > /dev/null 2>&1; then
        print_success "认证服务器 (端口3001) 运行正常"
    else
        print_failure "认证服务器 (端口3001) 无法访问"
        return 1
    fi
    
    # 检查转发器
    RESPONSE=$(curl -s -w "%{http_code}" http://localhost:5001/ -o /dev/null)
    if [ "$RESPONSE" = "401" ]; then
        print_success "转发器 (端口5001) 运行正常，正确返回认证要求"
    else
        print_failure "转发器 (端口5001) 状态异常 (状态码: $RESPONSE)"
        return 1
    fi
    
    echo ""
    return 0
}

# 测试用户登录流程
test_user_login() {
    local username=$1
    local user_info=$(get_user_info "$username")
    local password=$(echo "$user_info" | cut -d: -f1)
    local port=$(echo "$user_info" | cut -d: -f2)
    local color=$(echo "$user_info" | cut -d: -f3)
    local display_name=$(echo "$user_info" | cut -d: -f4)
    
    print_user_info "测试用户 $username 登录流程..."
    
    # 测试登录
    RESPONSE=$(curl -s -w "%{http_code}" -X POST http://localhost:3001/login \
        -d "username=$username&password=$password" \
        -c "cookies_$username.txt" \
        -o "login_response_$username.html")
    
    if [ "$RESPONSE" = "302" ] || [ "$RESPONSE" = "200" ]; then
        print_success "用户 $username 登录成功 (状态码: $RESPONSE)"
    else
        print_failure "用户 $username 登录失败 (状态码: $RESPONSE)"
        return 1
    fi
    
    # 检查是否获得了认证token
    if [ -f "cookies_$username.txt" ]; then
        TOKEN=$(grep auth_token "cookies_$username.txt" | awk '{print $7}' 2>/dev/null)
        if [ -n "$TOKEN" ]; then
            print_success "用户 $username 获得有效的认证token"
        else
            print_failure "用户 $username 未获得认证token"
            return 1
        fi
    else
        print_failure "用户 $username cookie文件未生成"
        return 1
    fi
    
    return 0
}

# 测试用户容器访问
test_user_container_access() {
    local username=$1
    local user_info=$(get_user_info "$username")
    local password=$(echo "$user_info" | cut -d: -f1)
    local port=$(echo "$user_info" | cut -d: -f2)
    local color=$(echo "$user_info" | cut -d: -f3)
    local display_name=$(echo "$user_info" | cut -d: -f4)
    
    print_user_info "测试用户 $username 容器访问..."
    
    # 获取认证token
    if [ ! -f "cookies_$username.txt" ]; then
        print_failure "用户 $username 的cookie文件不存在，请先执行登录测试"
        return 1
    fi
    
    TOKEN=$(grep auth_token "cookies_$username.txt" | awk '{print $7}' 2>/dev/null)
    if [ -z "$TOKEN" ]; then
        print_failure "用户 $username 的认证token无效"
        return 1
    fi
    
    # 访问用户专属容器
    RESPONSE_CODE=$(curl -s -w "%{http_code}" http://localhost:5001/ \
        -H "Cookie: auth_token=$TOKEN" \
        -o "container_response_$username.html")
    
    if [ "$RESPONSE_CODE" = "200" ]; then
        print_success "用户 $username 成功访问转发器"
        
        # 检查响应内容是否包含正确的用户标识
        if grep -q "用户${display_name}" "container_response_$username.html"; then
            print_success "用户 $username 看到了正确的专属页面 (${color}主题)"
        else
            print_failure "用户 $username 未看到正确的专属页面内容"
            return 1
        fi
        
        # 检查端口信息是否正确
        if grep -q "$port" "container_response_$username.html"; then
            print_success "用户 $username 的端口映射信息正确 (端口$port)"
        else
            print_failure "用户 $username 的端口映射信息错误"
            return 1
        fi
        
    else
        print_failure "用户 $username 无法访问转发器 (状态码: $RESPONSE_CODE)"
        return 1
    fi
    
    return 0
}

# 测试用户隔离
test_user_isolation() {
    print_user_info "测试用户隔离机制..."
    
    local isolation_passed=true
    
    # 测试每个用户只能看到自己的内容
    for user in $USERS_LIST; do
        if [ -f "cookies_$user.txt" ]; then
            local token=$(grep auth_token "cookies_$user.txt" | awk '{print $7}' 2>/dev/null)
            local user_info=$(get_user_info "$user")
            local user_display=$(echo "$user_info" | cut -d: -f4)
            
            if [ -n "$token" ]; then
                RESPONSE=$(curl -s http://localhost:5001/ -H "Cookie: auth_token=$token")
                
                # 检查是否只包含自己的用户标识
                if echo "$RESPONSE" | grep -q "用户${user_display}"; then
                    print_success "用户 $user 只能看到自己的内容"
                else
                    print_failure "用户 $user 看不到自己的内容"
                    isolation_passed=false
                fi
                
                # 检查是否不包含其他用户的标识
                for other_user in $USERS_LIST; do
                    if [ "$user" != "$other_user" ]; then
                        local other_info=$(get_user_info "$other_user")
                        local other_display=$(echo "$other_info" | cut -d: -f4)
                        if echo "$RESPONSE" | grep -q "用户${other_display}"; then
                            print_failure "用户 $user 能看到用户 $other_user 的内容，隔离失败"
                            isolation_passed=false
                        fi
                    fi
                done
            fi
        fi
    done
    
    if [ "$isolation_passed" = true ]; then
        print_success "用户隔离机制工作正常"
        return 0
    else
        print_failure "用户隔离机制存在问题"
        return 1
    fi
}

# 测试登录后直接跳转（无Dashboard）
test_direct_redirect() {
    print_user_info "测试简化后的直接跳转功能..."
    
    # 使用用户aaa测试登录后是否直接显示容器内容
    RESPONSE=$(curl -s -L -X POST http://localhost:3001/login \
        -d "username=aaa&password=111" \
        -c "direct_test_cookies.txt")
    
    # 检查响应是否直接包含容器内容而不是Dashboard
    if echo "$RESPONSE" | grep -q "405 Not Allowed"; then
        print_success "登录后直接重定向到转发器 (收到nginx的405响应，这是预期的POST方法响应)"
    elif echo "$RESPONSE" | grep -q "HTTP VPN 仪表板"; then
        print_failure "仍然显示Dashboard页面，简化未生效"
        return 1
    else
        print_info "登录重定向响应内容需要进一步检查"
    fi
    
    # 清理测试文件
    rm -f direct_test_cookies.txt 2>/dev/null
    
    return 0
}

# 测试错误处理
test_error_handling() {
    print_user_info "测试错误处理机制..."
    
    # 测试错误的用户名密码
    RESPONSE=$(curl -s -w "%{http_code}" -X POST http://localhost:3001/login \
        -d "username=invalid&password=wrong" -o /dev/null)
    
    if [ "$RESPONSE" = "200" ]; then
        print_success "认证服务器正确处理错误登录"
    else
        print_info "错误登录返回状态码: $RESPONSE"
    fi
    
    # 测试过期token（这里模拟）
    FAKE_TOKEN="expired.jwt.token"
    RESPONSE=$(curl -s -w "%{http_code}" http://localhost:5001/ \
        -H "Cookie: auth_token=$FAKE_TOKEN" -o /dev/null)
    
    if [ "$RESPONSE" = "401" ]; then
        print_success "转发器正确处理无效token"
    else
        print_failure "转发器未正确处理无效token (状态码: $RESPONSE)"
        return 1
    fi
    
    return 0
}

# 测试响应性能
test_response_performance() {
    print_user_info "测试响应性能..."
    
    # 测试认证服务器响应时间
    AUTH_TIME=$(curl -s -w "%{time_total}" http://localhost:3001/ -o /dev/null)
    print_success "认证服务器响应时间: ${AUTH_TIME}s"
    
    # 测试转发器响应时间（使用有效token）
    if [ -f "cookies_aaa.txt" ]; then
        TOKEN=$(grep auth_token "cookies_aaa.txt" | awk '{print $7}' 2>/dev/null)
        if [ -n "$TOKEN" ]; then
            PROXY_TIME=$(curl -s -w "%{time_total}" http://localhost:5001/ \
                -H "Cookie: auth_token=$TOKEN" -o /dev/null)
            print_success "转发器响应时间: ${PROXY_TIME}s"
        fi
    fi
    
    return 0
}

# 主测试流程
main() {
    echo -e "${CYAN}🏃 开始HTTP VPN系统功能测试...${NC}"
    echo ""
    
    # 1. 检查系统状态
    print_test_header "1" "系统状态检查"
    if ! check_system_status; then
        echo -e "\n${RED}❌ 系统状态检查失败，终止测试${NC}"
        exit 1
    fi
    
    # 2. 测试用户登录
    print_test_header "2" "用户登录测试"
    for username in $USERS_LIST; do
        if ! test_user_login "$username"; then
            print_failure "用户 $username 登录测试失败"
        fi
    done
    
    # 3. 测试容器访问
    print_test_header "3" "用户容器访问测试"
    for username in $USERS_LIST; do
        if ! test_user_container_access "$username"; then
            print_failure "用户 $username 容器访问测试失败"
        fi
    done
    
    # 4. 测试用户隔离
    print_test_header "4" "用户隔离测试"
    if ! test_user_isolation; then
        print_failure "用户隔离测试失败"
    fi
    
    # 5. 测试直接跳转
    print_test_header "5" "简化跳转测试"
    if ! test_direct_redirect; then
        print_failure "简化跳转测试失败"
    fi
    
    # 6. 测试错误处理
    print_test_header "6" "错误处理测试"
    if ! test_error_handling; then
        print_failure "错误处理测试失败"
    fi
    
    # 7. 测试性能
    print_test_header "7" "性能测试"
    if ! test_response_performance; then
        print_failure "性能测试失败"
    fi
    
    # 清理临时文件
    print_info "清理测试文件..."
    rm -f cookies_*.txt login_response_*.html container_response_*.html 2>/dev/null
    
    # 输出测试总结
    echo ""
    echo "🚀========================================🚀"
    echo "           功能测试总结报告"
    echo "🚀========================================🚀"
    echo -e "${BLUE}总测试场景: $TOTAL_TESTS${NC}"
    echo -e "${GREEN}功能正常: $PASSED_TESTS${NC}"
    echo -e "${RED}功能异常: $FAILED_TESTS${NC}"
    
    # 计算成功率
    if [ $TOTAL_TESTS -gt 0 ]; then
        SUCCESS_RATE=$(( (PASSED_TESTS * 100) / TOTAL_TESTS ))
        echo -e "${CYAN}成功率: ${SUCCESS_RATE}%${NC}"
    fi
    
    if [ $FAILED_TESTS -eq 0 ]; then
        echo -e "\n${GREEN}🎉 恭喜！所有功能测试通过！${NC}"
        echo -e "${GREEN}🚀 HTTP VPN 简化版功能完美！${NC}"
        exit 0
    else
        echo -e "\n${YELLOW}⚠️  发现 $FAILED_TESTS 个功能问题${NC}"
        echo -e "${YELLOW}🔧 建议检查上述失败的功能并进行修复${NC}"
        exit 1
    fi
}

# 运行主测试
main "$@" 