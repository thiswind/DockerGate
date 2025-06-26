#!/usr/bin/env python3
"""
HTTP VPN 转发器 - 基于HTTP的应用层VPN实现
"""

import socket
import threading
import re
import os
import time
from typing import Optional, Tuple
from .auth import AuthManager

class HTTPVPNProxy:
    """HTTP VPN 代理服务器"""
    
    def __init__(self, listen_port: int = 5000):
        self.listen_port = listen_port
        self.secret_key = "http-vpn-secret-key-change-this-in-production"
        self.running = True
        
        # 认证会话文件路径
        auth_session_file = os.path.join(
            os.path.dirname(os.path.dirname(__file__)), 
            'shared', 
            'auth_sessions.json'
        )
        
        # 初始化认证管理器
        self.auth_manager = AuthManager(self.secret_key, auth_session_file)
        
        print(f"认证会话文件: {auth_session_file}")
    
    def start(self):
        """启动代理服务器"""
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            server_socket.bind(('0.0.0.0', self.listen_port))
            server_socket.listen(10)
            
            print("=" * 60)
            print("HTTP VPN 转发器启动成功")
            print("=" * 60)
            print(f"监听端口: {self.listen_port}")
            print("用户路由映射:")
            print("  aaa → 127.0.0.1:6060 (nginx-user-aaa)")
            print("  bbb → 127.0.0.1:8080 (nginx-user-bbb)")
            print("  ccc → 127.0.0.1:9090 (nginx-user-ccc)")
            print("")
            print("访问方式:")
            print("  1. 先在 http://localhost:3001 登录")
            print("  2. 登录成功后会自动跳转到转发器")
            print("  3. 看到对应用户的专属页面")
            print("=" * 60)
            
            while self.running:
                try:
                    client_socket, client_addr = server_socket.accept()
                    
                    # 为每个客户端创建处理线程
                    client_thread = threading.Thread(
                        target=self.handle_client,
                        args=(client_socket, client_addr),
                        daemon=True
                    )
                    client_thread.start()
                    
                except Exception as e:
                    print(f"接受连接时出错: {e}")
                    
        except Exception as e:
            print(f"服务器启动失败: {e}")
        finally:
            server_socket.close()
    
    def handle_client(self, client_socket: socket.socket, client_addr: Tuple[str, int]):
        """处理客户端连接"""
        try:
            # 接收HTTP请求
            request_data = self.receive_http_request(client_socket)
            if not request_data:
                return
            
            # 解析请求基本信息
            method, path, _ = self.parse_request_line(request_data)
            
            print(f"\n[{time.strftime('%H:%M:%S')}] 收到请求: {client_addr[0]} → {method} {path}")
            
            # 特殊路径处理
            if path == '/dashboard':
                self.handle_dashboard_request(client_socket, request_data)
                return
            elif path == '/favicon.ico':
                self.send_404_response(client_socket)
                return
            
            # 认证请求
            auth_payload = self.auth_manager.authenticate_request(request_data)
            if not auth_payload:
                print(f"[认证失败] {client_addr[0]} → {path}")
                self.send_unauthorized_response(client_socket)
                return
            
            # 获取目标端口
            target_port = auth_payload.get('target_port')
            username = auth_payload.get('username')
            
            if not target_port:
                print(f"[路由失败] 用户 {username} 没有分配目标端口")
                self.send_error_response(client_socket, 500, "Internal Server Error")
                return
            
            print(f"[路由成功] {username} → 127.0.0.1:{target_port}")
            
            # 清理请求并转发
            clean_request = self.auth_manager.clean_request(request_data)
            self.forward_to_container(client_socket, target_port, clean_request, username)
            
        except Exception as e:
            print(f"处理客户端请求时出错: {e}")
        finally:
            try:
                client_socket.close()
            except:
                pass
    
    def receive_http_request(self, client_socket: socket.socket) -> Optional[str]:
        """接收完整的HTTP请求"""
        try:
            client_socket.settimeout(30)  # 30秒超时
            request_data = b""
            
            while True:
                chunk = client_socket.recv(4096)
                if not chunk:
                    break
                
                request_data += chunk
                
                # 检查是否接收到完整的HTTP头部
                if b"\r\n\r\n" in request_data:
                    headers_end = request_data.find(b"\r\n\r\n")
                    headers_part = request_data[:headers_end].decode('utf-8', errors='ignore')
                    
                    # 检查是否有请求体
                    content_length_match = re.search(r'Content-Length:\s*(\d+)', headers_part, re.IGNORECASE)
                    if content_length_match:
                        content_length = int(content_length_match.group(1))
                        body_received = len(request_data) - headers_end - 4
                        
                        if body_received >= content_length:
                            break
                    else:
                        # 没有Content-Length，认为请求完整
                        break
            
            return request_data.decode('utf-8', errors='ignore')
            
        except socket.timeout:
            print("接收请求超时")
            return None
        except Exception as e:
            print(f"接收请求时出错: {e}")
            return None
    
    def parse_request_line(self, request_data: str) -> Tuple[str, str, str]:
        """解析HTTP请求行"""
        lines = request_data.split('\r\n')
        if not lines:
            return "", "", ""
        
        request_line = lines[0]
        parts = request_line.split(' ')
        
        if len(parts) >= 3:
            return parts[0], parts[1], parts[2]
        
        return "", "", ""
    
    def handle_dashboard_request(self, client_socket: socket.socket, request_data: str):
        """处理仪表板请求"""
        # 认证请求
        auth_payload = self.auth_manager.authenticate_request(request_data)
        if not auth_payload:
            self.send_redirect_to_login(client_socket)
            return
        
        username = auth_payload.get('username')
        target_port = auth_payload.get('target_port')
        
        # 生成仪表板页面
        dashboard_html = self.generate_dashboard_html(username, target_port)
        self.send_html_response(client_socket, dashboard_html)
    
    def generate_dashboard_html(self, username: str, target_port: int) -> str:
        """生成用户仪表板页面"""
        return f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>HTTP VPN 仪表板 - 用户 {username.upper()}</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            margin: 0;
            padding: 0;
            min-height: 100vh;
            display: flex;
            justify-content: center;
            align-items: center;
        }}
        .dashboard {{
            text-align: center;
            background: rgba(255, 255, 255, 0.1);
            padding: 40px;
            border-radius: 20px;
            backdrop-filter: blur(10px);
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
            max-width: 600px;
            width: 90%;
        }}
        h1 {{
            font-size: 2.5em;
            margin-bottom: 20px;
            text-shadow: 2px 2px 4px rgba(0, 0, 0, 0.5);
        }}
        .user-info {{
            background: rgba(255, 255, 255, 0.2);
            padding: 20px;
            border-radius: 10px;
            margin: 20px 0;
        }}
        .access-button {{
            display: inline-block;
            background: #4CAF50;
            color: white;
            padding: 15px 30px;
            text-decoration: none;
            border-radius: 10px;
            font-size: 1.2em;
            font-weight: bold;
            margin: 10px;
            transition: all 0.3s ease;
            border: none;
            cursor: pointer;
        }}
        .access-button:hover {{
            background: #45a049;
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0, 0, 0, 0.3);
        }}
        .logout-button {{
            background: #f44336;
        }}
        .logout-button:hover {{
            background: #da190b;
        }}
        .info-section {{
            background: rgba(255, 255, 255, 0.1);
            padding: 20px;
            border-radius: 10px;
            margin: 20px 0;
            text-align: left;
        }}
        .status-indicator {{
            display: inline-block;
            width: 12px;
            height: 12px;
            background: #4CAF50;
            border-radius: 50%;
            margin-right: 10px;
            animation: pulse 2s infinite;
        }}
        @keyframes pulse {{
            0% {{ opacity: 1; }}
            50% {{ opacity: 0.5; }}
            100% {{ opacity: 1; }}
        }}
    </style>
</head>
<body>
    <div class="dashboard">
        <h1>🚀 HTTP VPN 仪表板</h1>
        
        <div class="user-info">
            <h2>欢迎，用户 {username.upper()}！</h2>
            <p><span class="status-indicator"></span>连接状态：已认证</p>
            <p>分配端口：{target_port}</p>
            <p>VPN状态：活跃</p>
        </div>
        
        <div>
            <button onclick="accessContainer()" class="access-button">
                访问我的专属容器
            </button>
            <a href="http://localhost:3001/logout" class="access-button logout-button">
                退出登录
            </a>
        </div>
        
        <div class="info-section">
            <h3>📋 系统信息</h3>
            <p><strong>用户身份：</strong> {username}</p>
            <p><strong>目标容器：</strong> nginx-user-{username}</p>
            <p><strong>容器端口：</strong> 127.0.0.1:{target_port}</p>
            <p><strong>转发器：</strong> HTTP VPN Proxy v1.0</p>
        </div>
        
        <div class="info-section">
            <h3>🔒 安全特性</h3>
            <p>✅ JWT Token 认证</p>
            <p>✅ 端口隔离保护</p>
            <p>✅ 用户权限控制</p>
            <p>✅ 透明代理转发</p>
        </div>
    </div>
    
    <script>
        function getCookie(name) {{
            const value = `; ${{document.cookie}}`;
            const parts = value.split(`; ${{name}}=`);
            if (parts.length === 2) return parts.pop().split(';').shift();
            return null;
        }}
        
        function accessContainer() {{
            // 直接访问根路径，转发器会自动路由到正确的容器
            window.location.href = '/';
        }}
        
        // 定期检查认证状态
        setInterval(function() {{
            const token = getCookie('auth_token');
            if (!token) {{
                alert('会话已过期，请重新登录');
                window.location.href = 'http://localhost:3001';
            }}
        }}, 60000); // 每分钟检查一次
    </script>
</body>
</html>
        """
    
    def forward_to_container(self, client_socket: socket.socket, target_port: int, 
                           clean_request: str, username: str):
        """转发请求到目标容器"""
        try:
            # 连接到目标容器
            target_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            target_socket.connect(('127.0.0.1', target_port))
            
            # 发送清理后的请求
            target_socket.send(clean_request.encode('utf-8'))
            
            # 接收容器响应
            response_data = self.receive_response(target_socket)
            target_socket.close()
            
            if response_data:
                # 注入认证机制到响应中
                modified_response = self.inject_auth_mechanism(response_data, username)
                client_socket.send(modified_response)
            else:
                self.send_error_response(client_socket, 502, "Bad Gateway")
                
        except ConnectionRefusedError:
            print(f"无法连接到容器端口 {target_port}")
            self.send_error_response(client_socket, 503, "Service Unavailable")
        except Exception as e:
            print(f"转发请求时出错: {e}")
            self.send_error_response(client_socket, 500, "Internal Server Error")
    
    def receive_response(self, target_socket: socket.socket) -> Optional[bytes]:
        """接收目标容器的响应"""
        try:
            target_socket.settimeout(30)
            response_data = b""
            
            while True:
                chunk = target_socket.recv(4096)
                if not chunk:
                    break
                response_data += chunk
                
                # 简单的响应完整性检查
                if b"\r\n\r\n" in response_data:
                    headers_end = response_data.find(b"\r\n\r\n")
                    headers_part = response_data[:headers_end].decode('utf-8', errors='ignore')
                    
                    # 检查Content-Length
                    content_length_match = re.search(r'Content-Length:\s*(\d+)', headers_part, re.IGNORECASE)
                    if content_length_match:
                        content_length = int(content_length_match.group(1))
                        body_received = len(response_data) - headers_end - 4
                        
                        if body_received >= content_length:
                            break
                    else:
                        # 对于没有Content-Length的响应，等待连接关闭
                        if 'Connection: close' in headers_part or 'connection: close' in headers_part:
                            continue
                        else:
                            break
            
            return response_data
            
        except socket.timeout:
            print("接收容器响应超时")
            return None
        except Exception as e:
            print(f"接收容器响应时出错: {e}")
            return None
    
    def inject_auth_mechanism(self, response_data: bytes, username: str) -> bytes:
        """在响应中注入认证机制"""
        try:
            response_str = response_data.decode('utf-8', errors='ignore')
            
            # 检查是否是HTML响应
            if 'text/html' in response_str and '<head>' in response_str:
                # 注入认证JavaScript代码
                auth_script = f"""
<script>
// HTTP VPN 客户端认证注入 - 用户 {username}
(function() {{
    console.log('HTTP VPN 认证机制已注入 - 用户: {username}');
    
    // 获取当前认证token
    function getAuthToken() {{
        const value = `; ${{document.cookie}}`;
        const parts = value.split(`; auth_token=`);
        if (parts.length === 2) return parts.pop().split(';').shift();
        return null;
    }}
    
    const currentToken = getAuthToken();
    if (!currentToken) {{
        console.warn('未找到认证token，可能需要重新登录');
        return;
    }}
    
    // 拦截fetch请求
    const originalFetch = window.fetch;
    window.fetch = function(url, options = {{}}) {{
        options.headers = options.headers || {{}};
        options.headers['Authorization'] = 'Bearer ' + currentToken;
        
        console.log('拦截fetch请求:', url);
        return originalFetch(url, options);
    }};
    
    // 拦截XMLHttpRequest
    const originalXHROpen = XMLHttpRequest.prototype.open;
    XMLHttpRequest.prototype.open = function(method, url, ...args) {{
        const result = originalXHROpen.apply(this, arguments);
        this.setRequestHeader('Authorization', 'Bearer ' + currentToken);
        
        console.log('拦截XHR请求:', method, url);
        return result;
    }};
    
    // 拦截表单提交
    document.addEventListener('submit', function(e) {{
        const form = e.target;
        console.log('拦截表单提交:', form.action);
        
        // 添加隐藏的认证字段
        const tokenInput = document.createElement('input');
        tokenInput.type = 'hidden';
        tokenInput.name = '__auth_token';
        tokenInput.value = currentToken;
        form.appendChild(tokenInput);
    }});
    
    // 拦截链接点击
    document.addEventListener('click', function(e) {{
        if (e.target.tagName === 'A' && e.target.href) {{
            console.log('拦截链接点击:', e.target.href);
            
            // 如果是相对链接，添加认证参数
            if (!e.target.href.startsWith('http')) {{
                const url = new URL(e.target.href, window.location.origin);
                url.searchParams.set('__auth_token', currentToken);
                e.target.href = url.toString();
            }}
        }}
    }});
    
    console.log('HTTP VPN 认证机制设置完成');
}})();
</script>
"""
                
                # 在</head>前插入认证脚本
                response_str = response_str.replace('</head>', auth_script + '</head>')
                response_data = response_str.encode('utf-8')
                
                # 更新Content-Length
                headers_end = response_data.find(b'\r\n\r\n')
                if headers_end != -1:
                    headers_part = response_data[:headers_end].decode('utf-8')
                    body_part = response_data[headers_end + 4:]
                    
                    # 更新Content-Length
                    new_length = len(body_part)
                    headers_part = re.sub(r'Content-Length:\s*\d+', f'Content-Length: {new_length}', 
                                        headers_part, flags=re.IGNORECASE)
                    
                    response_data = headers_part.encode('utf-8') + b'\r\n\r\n' + body_part
        
        except Exception as e:
            print(f"注入认证机制时出错: {e}")
        
        return response_data
    
    def send_html_response(self, client_socket: socket.socket, html_content: str):
        """发送HTML响应"""
        html_bytes = html_content.encode('utf-8')
        response = (
            f"HTTP/1.1 200 OK\r\n"
            f"Content-Type: text/html; charset=utf-8\r\n"
            f"Content-Length: {len(html_bytes)}\r\n"
            f"Connection: close\r\n"
            f"\r\n"
        ).encode('utf-8') + html_bytes
        
        client_socket.send(response)
    
    def send_unauthorized_response(self, client_socket: socket.socket):
        """发送401未授权响应"""
        html_content = """
<!DOCTYPE html>
<html>
<head>
    <title>401 - 认证失败</title>
    <style>
        body { font-family: Arial, sans-serif; text-align: center; margin-top: 100px; }
        .error { color: #d32f2f; font-size: 1.5em; }
        .message { margin: 20px; color: #666; }
        .link { color: #1976d2; text-decoration: none; }
    </style>
</head>
<body>
    <div class="error">🔒 401 - 认证失败</div>
    <div class="message">
        您需要先登录才能访问此页面<br>
        <a href="http://localhost:3001" class="link">点击这里登录</a>
    </div>
</body>
</html>
        """
        
        html_bytes = html_content.encode('utf-8')
        response = (
            f"HTTP/1.1 401 Unauthorized\r\n"
            f"Content-Type: text/html; charset=utf-8\r\n"
            f"Content-Length: {len(html_bytes)}\r\n"
            f"Connection: close\r\n"
            f"\r\n"
        ).encode('utf-8') + html_bytes
        
        client_socket.send(response)
    
    def send_redirect_to_login(self, client_socket: socket.socket):
        """重定向到登录页面"""
        response = (
            "HTTP/1.1 302 Found\r\n"
            "Location: http://localhost:3001\r\n"
            "Content-Length: 0\r\n"
            "Connection: close\r\n"
            "\r\n"
        )
        client_socket.send(response.encode('utf-8'))
    
    def send_404_response(self, client_socket: socket.socket):
        """发送404响应"""
        response = (
            "HTTP/1.1 404 Not Found\r\n"
            "Content-Type: text/html\r\n"
            "Content-Length: 23\r\n"
            "Connection: close\r\n"
            "\r\n"
            "<h1>404 Not Found</h1>"
        )
        client_socket.send(response.encode('utf-8'))
    
    def send_error_response(self, client_socket: socket.socket, code: int, message: str):
        """发送错误响应"""
        html_content = f"<h1>{code} {message}</h1>"
        html_bytes = html_content.encode('utf-8')
        
        response = (
            f"HTTP/1.1 {code} {message}\r\n"
            f"Content-Type: text/html\r\n"
            f"Content-Length: {len(html_bytes)}\r\n"
            f"Connection: close\r\n"
            f"\r\n"
        ).encode('utf-8') + html_bytes
        
        client_socket.send(response)
    
    def stop(self):
        """停止代理服务器"""
        self.running = False

if __name__ == "__main__":
    proxy = HTTPVPNProxy(listen_port=5000)
    try:
        proxy.start()
    except KeyboardInterrupt:
        print("\n正在停止HTTP VPN转发器...")
        proxy.stop()
        print("转发器已停止") 