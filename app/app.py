#!/usr/bin/env python3
"""
Flask认证应用 - HTTP VPN系统的认证服务器
"""

from flask import Flask, request, render_template, redirect, url_for, make_response
import jwt
import json
import os
import time
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = "http-vpn-secret-key-change-this-in-production"

# 用户数据库
USERS = {
    "aaa": {"password": "111", "target_port": 6060},
    "bbb": {"password": "222", "target_port": 8080}, 
    "ccc": {"password": "333", "target_port": 9090}
}

# 认证会话文件路径
AUTH_SESSION_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'shared', 'auth_sessions.json')

def load_auth_sessions():
    """加载认证会话数据"""
    try:
        with open(AUTH_SESSION_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {"sessions": {}, "user_mappings": {}}

def save_auth_sessions(data):
    """保存认证会话数据"""
    try:
        # 确保目录存在
        os.makedirs(os.path.dirname(AUTH_SESSION_FILE), exist_ok=True)
        
        with open(AUTH_SESSION_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"保存认证会话失败: {e}")
        return False

def generate_token(username):
    """生成JWT token"""
    payload = {
        'username': username,
        'target_port': USERS[username]['target_port'],
        'exp': datetime.utcnow() + timedelta(minutes=30),  # 改为30分钟
        'iat': datetime.utcnow()
    }
    return jwt.encode(payload, app.secret_key, algorithm='HS256')

def verify_token(token):
    """验证JWT token"""
    try:
        payload = jwt.decode(token, app.secret_key, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

@app.route('/')
def index():
    """首页 - 显示登录页面"""
    return render_template('login.html')

@app.route('/login', methods=['POST'])
def login():
    """处理登录请求"""
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '').strip()
    
    # 验证用户凭据
    if username not in USERS or USERS[username]['password'] != password:
        return render_template('login.html', error="用户名或密码错误")
    
    # 生成JWT token
    token = generate_token(username)
    
    # 加载现有的认证会话
    auth_data = load_auth_sessions()
    
    # 踢出该用户的所有现有会话（实现单用户登录）
    sessions_to_remove = []
    for session_id_old, session in auth_data['sessions'].items():
        if session.get('username') == username:
            sessions_to_remove.append(session_id_old)
    
    for session_id_old in sessions_to_remove:
        del auth_data['sessions'][session_id_old]
        print(f"踢出用户 {username} 的旧会话: {session_id_old}")
    
    # 创建会话ID
    session_id = f"session_{username}_{int(time.time())}"
    current_time = datetime.utcnow()
    
    # 添加新的认证会话（使用滑动超时）
    auth_data['sessions'][session_id] = {
        'username': username,
        'token': token,
        'target_port': USERS[username]['target_port'],
        'created_at': current_time.isoformat(),
        'last_activity': current_time.isoformat(),  # 新增：最后活动时间
        'timeout_minutes': 30,  # 新增：超时时间（分钟）
        'active': True
    }
    
    # 清理所有过期的会话（使用滑动超时）
    expired_sessions = []
    for sid, session in auth_data['sessions'].items():
        try:
            last_activity = datetime.fromisoformat(session.get('last_activity', session.get('created_at')))
            timeout_minutes = session.get('timeout_minutes', 30)
            if (current_time - last_activity).total_seconds() > timeout_minutes * 60:
                expired_sessions.append(sid)
        except:
            expired_sessions.append(sid)
    
    for sid in expired_sessions:
        if sid in auth_data['sessions']:
            expired_username = auth_data['sessions'][sid].get('username', 'unknown')
            del auth_data['sessions'][sid]
            print(f"清理过期会话: {sid} (用户: {expired_username})")
    
    # 保存认证会话
    if not save_auth_sessions(auth_data):
        return render_template('login.html', error="认证会话保存失败，请重试")
    
    print(f"用户 {username} 登录成功，会话ID: {session_id}")
    
    # 设置Cookie并直接跳转到转发器根路径（用户容器）
    response = make_response(redirect('http://localhost:5001/'))
    response.set_cookie(
        'auth_token', 
        token, 
        max_age=1800,  # 30分钟
        httponly=False,  # 允许JavaScript访问，用于VPN注入
        secure=False,   # 开发环境设为False
        samesite='Lax'
    )
    response.set_cookie(
        'session_id', 
        session_id, 
        max_age=1800,  # 30分钟
        httponly=False,
        secure=False,
        samesite='Lax'
    )
    
    return response

@app.route('/logout')
def logout():
    """用户退出登录"""
    session_id = request.cookies.get('session_id')
    
    if session_id:
        # 从认证会话中移除
        auth_data = load_auth_sessions()
        if session_id in auth_data['sessions']:
            username = auth_data['sessions'][session_id]['username']
            del auth_data['sessions'][session_id]
            save_auth_sessions(auth_data)
            print(f"用户 {username} 已退出登录，会话ID: {session_id}")
    
    # 清除Cookie并跳转回登录页面
    response = make_response(redirect(url_for('index')))
    response.set_cookie('auth_token', '', expires=0)
    response.set_cookie('session_id', '', expires=0)
    
    return response

@app.route('/api/verify_token', methods=['POST'])
def api_verify_token():
    """API: 验证token（供转发器调用）"""
    try:
        data = request.get_json()
        token = data.get('token')
        
        if not token:
            return {"valid": False, "error": "缺少token"}, 400
        
        payload = verify_token(token)
        if payload:
            return {
                "valid": True,
                "username": payload['username'],
                "target_port": payload['target_port'],
                "expires": payload['exp']
            }
        else:
            return {"valid": False, "error": "token无效或已过期"}, 401
            
    except Exception as e:
        return {"valid": False, "error": str(e)}, 500

@app.route('/api/get_user_sessions')
def api_get_user_sessions():
    """API: 获取当前活跃的用户会话（供调试使用）"""
    auth_data = load_auth_sessions()
    active_sessions = {}
    
    current_time = datetime.utcnow()
    for session_id, session in auth_data['sessions'].items():
        try:
            last_activity = datetime.fromisoformat(session.get('last_activity', session.get('created_at')))
            timeout_minutes = session.get('timeout_minutes', 30)
            if ((current_time - last_activity).total_seconds() <= timeout_minutes * 60 and 
                session.get('active', True)):
                active_sessions[session_id] = {
                    'username': session['username'],
                    'target_port': session['target_port'],
                    'created_at': session['created_at'],
                    'last_activity': session.get('last_activity'),
                    'timeout_minutes': timeout_minutes
                }
        except:
            continue
    
    return {
        "active_sessions": active_sessions,
        "total_count": len(active_sessions)
    }

@app.route('/status')
def status():
    """系统状态页面"""
    auth_data = load_auth_sessions()
    active_sessions = []
    
    current_time = datetime.utcnow()
    for session_id, session in auth_data['sessions'].items():
        try:
            last_activity = datetime.fromisoformat(session.get('last_activity', session.get('created_at')))
            timeout_minutes = session.get('timeout_minutes', 30)
            if ((current_time - last_activity).total_seconds() <= timeout_minutes * 60 and 
                session.get('active', True)):
                active_sessions.append({
                    'session_id': session_id,
                    'username': session['username'],
                    'target_port': session['target_port'],
                    'created_at': session['created_at'],
                    'last_activity': session.get('last_activity'),
                    'timeout_minutes': timeout_minutes
                })
        except:
            continue
    
    status_html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>HTTP VPN 系统状态</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; }}
            .container {{ max-width: 800px; margin: 0 auto; }}
            .session {{ background: #f0f0f0; padding: 15px; margin: 10px 0; border-radius: 5px; }}
            .header {{ background: #333; color: white; padding: 20px; border-radius: 5px; margin-bottom: 20px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>HTTP VPN 系统状态</h1>
                <p>当前活跃会话: {len(active_sessions)}</p>
            </div>
            
            <h2>活跃会话列表</h2>
            {"".join([f'''
            <div class="session">
                <strong>用户:</strong> {s['username']}<br>
                <strong>目标端口:</strong> {s['target_port']}<br>
                <strong>会话ID:</strong> {s['session_id']}<br>
                <strong>创建时间:</strong> {s['created_at']}<br>
                <strong>最后活动:</strong> {s['last_activity']}<br>
                <strong>超时时间:</strong> {s['timeout_minutes']}分钟
            </div>
            ''' for s in active_sessions])}
            
            <div style="margin-top: 30px;">
                <a href="/">返回登录页面</a> | 
                <a href="/api/get_user_sessions">API接口</a>
            </div>
        </div>
    </body>
    </html>
    """
    
    return status_html

if __name__ == '__main__':
    print("=" * 60)
    print("HTTP VPN 认证服务器启动")
    print("=" * 60)
    print("访问地址: http://localhost:3001")
    print("状态页面: http://localhost:3001/status")
    print("")
    print("测试账户:")
    for username, info in USERS.items():
        print(f"  {username} / {info['password']} → 端口 {info['target_port']}")
    print("")
    print("认证会话文件:", AUTH_SESSION_FILE)
    print("=" * 60)
    
    app.run(host='0.0.0.0', port=3001, debug=True) 