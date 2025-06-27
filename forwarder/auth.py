#!/usr/bin/env python3
"""
认证模块 - 处理JWT token验证和会话管理
"""

import jwt
import json
import os
import re
from datetime import datetime
from typing import Optional, Dict, Any

class AuthManager:
    """认证管理器"""
    
    def __init__(self, secret_key: str, auth_session_file: str):
        self.secret_key = secret_key
        self.auth_session_file = auth_session_file
    
    def load_auth_sessions(self) -> Dict[str, Any]:
        """加载认证会话数据"""
        try:
            with open(self.auth_session_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {"sessions": {}, "user_mappings": {}}
    
    def save_auth_sessions(self, data: Dict[str, Any]) -> bool:
        """保存认证会话数据"""
        try:
            os.makedirs(os.path.dirname(self.auth_session_file), exist_ok=True)
            with open(self.auth_session_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"保存认证会话失败: {e}")
            return False
    
    def update_session_activity(self, username: str, token: str) -> bool:
        """更新会话活动时间"""
        auth_sessions = self.load_auth_sessions()
        current_time = datetime.utcnow()
        
        for session_id, session in auth_sessions['sessions'].items():
            if (session.get('username') == username and 
                session.get('token') == token and 
                session.get('active', True)):
                
                # 更新最后活动时间
                session['last_activity'] = current_time.isoformat()
                self.save_auth_sessions(auth_sessions)
                print(f"更新用户 {username} 的活动时间: {current_time.isoformat()}")
                return True
        
        return False
    
    def verify_jwt_token(self, token: str) -> Optional[Dict[str, Any]]:
        """验证JWT token"""
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])
            return payload
        except jwt.ExpiredSignatureError:
            print(f"Token已过期: {token[:20]}...")
            return None
        except jwt.InvalidTokenError:
            print(f"无效的Token: {token[:20]}...")
            return None
    
    def extract_token_from_request(self, request_data: str) -> Optional[str]:
        """从HTTP请求中提取认证token"""
        
        # 方法1: 从Authorization头提取
        auth_match = re.search(r'Authorization:\s*Bearer\s+([^\s\r\n]+)', request_data, re.IGNORECASE)
        if auth_match:
            return auth_match.group(1)
        
        # 方法2: 从Cookie中提取
        cookie_match = re.search(r'Cookie:.*?auth_token=([^;\s\r\n]+)', request_data, re.IGNORECASE)
        if cookie_match:
            return cookie_match.group(1)
        
        # 方法3: 从自定义头提取
        custom_header_match = re.search(r'X-Auth-Token:\s*([^\s\r\n]+)', request_data, re.IGNORECASE)
        if custom_header_match:
            return custom_header_match.group(1)
        
        # 方法4: 从URL参数提取
        url_match = re.search(r'[?&]auth_token=([^&\s\r\n]+)', request_data)
        if url_match:
            return url_match.group(1)
        
        return None
    
    def authenticate_request(self, request_data: str) -> Optional[Dict[str, Any]]:
        """认证HTTP请求"""
        
        # 提取token
        token = self.extract_token_from_request(request_data)
        if not token:
            print("请求中未找到认证token")
            return None
        
        # 验证token
        payload = self.verify_jwt_token(token)
        if not payload:
            print("Token验证失败")
            return None
        
        # 检查会话是否仍然活跃
        auth_sessions = self.load_auth_sessions()
        username = payload.get('username')
        
        # 查找对应的活跃会话（使用滑动超时）
        active_session = None
        current_time = datetime.utcnow()
        
        for session_id, session in auth_sessions['sessions'].items():
            if (session.get('username') == username and 
                session.get('token') == token and 
                session.get('active', True)):
                
                try:
                    # 使用滑动超时检查
                    last_activity = datetime.fromisoformat(session.get('last_activity', session.get('created_at')))
                    timeout_minutes = session.get('timeout_minutes', 30)
                    
                    if (current_time - last_activity).total_seconds() <= timeout_minutes * 60:
                        active_session = session
                        break
                    else:
                        print(f"用户 {username} 的会话已超时 ({timeout_minutes}分钟)")
                        # 标记会话为非活跃
                        session['active'] = False
                        self.save_auth_sessions(auth_sessions)
                except:
                    continue
        
        if not active_session:
            print(f"未找到用户 {username} 的活跃会话")
            return None
        
        # 更新最后活动时间
        self.update_session_activity(username, token)
        
        print(f"用户 {username} 认证成功，目标端口: {payload.get('target_port')}")
        return payload
    
    def clean_request(self, request_data: str) -> str:
        """清理HTTP请求，移除认证信息"""
        
        lines = request_data.split('\r\n')
        clean_lines = []
        
        for line in lines:
            # 跳过认证相关的头部
            if (line.lower().startswith('authorization:') or
                line.lower().startswith('x-auth-token:') or
                line.lower().startswith('x-vpn-auth:')):
                continue
            
            # 处理Cookie头，移除auth_token
            if line.lower().startswith('cookie:'):
                # 移除auth_token cookie
                clean_cookie = re.sub(r'auth_token=[^;]*;?\s*', '', line)
                # 如果Cookie头变空了，就跳过
                if clean_cookie.strip() == 'Cookie:':
                    continue
                clean_lines.append(clean_cookie)
            else:
                clean_lines.append(line)
        
        clean_request = '\r\n'.join(clean_lines)
        
        # 移除URL中的认证参数
        clean_request = re.sub(r'[?&]auth_token=[^&\s]*', '', clean_request)
        
        return clean_request
    
    def get_user_target_port(self, username: str) -> Optional[int]:
        """获取用户对应的目标端口"""
        auth_sessions = self.load_auth_sessions()
        
        # 从user_mappings中获取
        if username in auth_sessions.get('user_mappings', {}):
            return auth_sessions['user_mappings'][username]['target_port']
        
        # 从活跃会话中获取（使用滑动超时检查）
        current_time = datetime.utcnow()
        for session in auth_sessions['sessions'].values():
            if (session.get('username') == username and 
                session.get('active', True)):
                try:
                    last_activity = datetime.fromisoformat(session.get('last_activity', session.get('created_at')))
                    timeout_minutes = session.get('timeout_minutes', 30)
                    
                    if (current_time - last_activity).total_seconds() <= timeout_minutes * 60:
                        return session.get('target_port')
                except:
                    continue
        
        return None 