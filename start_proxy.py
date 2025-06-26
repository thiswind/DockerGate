#!/usr/bin/env python3
"""
HTTP VPN 转发器启动脚本
"""

from forwarder.proxy import HTTPVPNProxy

if __name__ == "__main__":
    proxy = HTTPVPNProxy(listen_port=5000)
    try:
        proxy.start()
    except KeyboardInterrupt:
        print("\n正在停止HTTP VPN转发器...")
        proxy.stop()
        print("转发器已停止") 