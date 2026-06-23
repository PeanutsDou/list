#!/usr/bin/env python3
"""
远程控制客户端 - 本地客户端
用于连接远程服务器并处理 Web 端消息
"""

import asyncio
import json
import logging
import os
import sys
import websockets
from typing import Dict, Any, Callable, Optional
import time

# 获取项目根目录并加入 sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
if project_root not in sys.path:
    sys.path.append(project_root)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class RemoteClient:
    def __init__(self, config_path: str = "config.json", on_message_callback: Optional[Callable] = None):
        """初始化客户端"""
        base_dir = os.path.dirname(os.path.abspath(__file__))
        if not os.path.isabs(config_path):
            config_path = os.path.join(base_dir, config_path)
            
        self.config = self.load_config(config_path)
        self.ws_connection = None
        self.is_connected = False
        self.on_message_callback = on_message_callback
        self.loop = None
        
    def set_callback(self, callback: Callable):
        """设置消息回调函数"""
        self.on_message_callback = callback
        
    def load_config(self, config_path: str) -> Dict[str, Any]:
        """加载配置文件"""
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            raise
    
    async def connect_to_server(self):
        """连接到服务器"""
        server_config = self.config['server']
        auth_token = server_config['auth_token']
        
        # 构建 WebSocket URL
        ws_url = f"ws://{server_config['host']}:{server_config['port']}/ws/client?token={auth_token}"
        
        logger.info(f"正在连接到服务器: {ws_url}")
        
        try:
            self.ws_connection = await websockets.connect(ws_url)
            self.is_connected = True
            logger.info("连接服务器成功")
            
            # 发送连接确认消息
            await self.ws_connection.send(json.dumps({
                "type": "client_connect",
                "client_name": self.config['client']['name'],
                "timestamp": int(time.time())
            }))
            
        except Exception as e:
            logger.error(f"连接服务器失败: {e}")
            self.is_connected = False
            raise
    
    async def send_message(self, message: Dict[str, Any]):
        """发送消息到服务器"""
        if not self.is_connected or not self.ws_connection:
            logger.error("未连接到服务器，无法发送消息")
            return
        
        try:
            await self.ws_connection.send(json.dumps(message))
            logger.debug(f"发送消息: {message}")
        except Exception as e:
            logger.error(f"发送消息失败: {e}")
            self.is_connected = False
    
    async def receive_messages(self):
        """接收服务器消息"""
        while self.is_connected:
            try:
                message = await self.ws_connection.recv()
                message_data = json.loads(message)
                
                # 处理不同类型的消息
                await self.handle_message(message_data)
                
            except websockets.exceptions.ConnectionClosed:
                logger.warning("连接已关闭")
                self.is_connected = False
                break
            except Exception as e:
                logger.error(f"接收消息失败: {e}")
                self.is_connected = False
                break
    
    async def handle_message(self, message: Dict[str, Any]):
        """处理接收到的消息"""
        msg_type = message.get('type', '')
        
        if msg_type == 'chat':
            # 处理 Web 端发送的消息
            text_content = message.get('text', '')
            context = message.get('context', {})
            context['source'] = 'web'
            
            logger.info(f"收到 Web 消息: {text_content}")
            
            if self.on_message_callback:
                if asyncio.iscoroutinefunction(self.on_message_callback):
                    await self.on_message_callback(text_content, context)
                else:
                    self.on_message_callback(text_content, context)
        elif msg_type == 'clear_chat':
            context = message.get('context', {})
            context['action'] = 'clear_chat'
            if self.on_message_callback:
                if asyncio.iscoroutinefunction(self.on_message_callback):
                    await self.on_message_callback("", context)
                else:
                    self.on_message_callback("", context)
            
        elif msg_type == 'ping':
            await self.send_message({"type": "pong"})
        else:
            logger.warning(f"未知消息类型: {msg_type}")
    
    async def send_reply(self, reply_content: str, context: Dict[str, Any]):
        """发送回复到 Web 端"""
        await self.send_message({
            "type": "response",
            "text": reply_content,
            "context": context
        })
    
    async def run(self):
        """运行客户端"""
        self.loop = asyncio.get_running_loop()
        reconnect_interval = self.config['client'].get('reconnect_interval', 5)
        
        while True:
            try:
                await self.connect_to_server()
                await self.receive_messages()
                
            except Exception as e:
                logger.error(f"连接异常: {e}")
            
            if self.is_connected:
                self.is_connected = False
            
            logger.info(f"等待 {reconnect_interval} 秒后重连...")
            await asyncio.sleep(reconnect_interval)

async def main():
    """主函数"""
    client = RemoteClient()
    await client.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("客户端已停止")
