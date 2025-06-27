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
            print("HTTP VPN 转发器启动成功 (简化模式)")
            print("=" * 60)
            print(f"监听端口: {self.listen_port}")
            print("用户路由映射:")
            print("  aaa → nginx-user-aaa:80 (容器内部)")
            print("  bbb → nginx-user-bbb:80 (容器内部)")
            print("  ccc → nginx-user-ccc:80 (容器内部)")
            print("")
            print("简化特性:")
            print("  🔒 nginx容器完全不暴露到宿主机")
            print("  🛡️ 只能通过转发器访问")
            print("  🚫 127.0.0.1绕过已被阻止")
            print("  ✨ 无dashboard，登录后直接进入容器")
            print("  🎯 纯透明代理，无JavaScript注入")
            print("")
            print("使用方式:")
            print("  1. 访问 http://localhost:3001 登录")
            print("  2. 登录成功后直接显示用户专属容器内容")
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
            if path == '/favicon.ico':
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
    

    
    def forward_to_container(self, client_socket: socket.socket, target_port: int, 
                           clean_request: str, username: str):
        """转发请求到目标容器"""
        try:
            # 端口到容器名的映射
            container_mapping = {
                6060: 'nginx-user-aaa',
                8080: 'nginx-user-bbb',
                9090: 'nginx-user-ccc'
            }
            
            container_name = container_mapping.get(target_port)
            if not container_name:
                print(f"未找到端口 {target_port} 对应的容器")
                self.send_error_response(client_socket, 500, "Internal Server Error")
                return
            
            # 通过容器名连接到目标容器（Docker内部网络）
            target_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            target_socket.connect((container_name, 80))  # 连接容器内部的80端口
            
            print(f"[容器连接] {username} → {container_name}:80")
            
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
            print(f"无法连接到容器 {container_name}")
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
        """简化的HTTP响应处理 - 基本透明代理"""
        # 简化后只做基本的透明代理，不注入复杂的JavaScript
        # 认证由转发器在请求层面处理，无需在响应中注入代码
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