import sys
import os
import uuid
import json
import asyncio
import time
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
                             QTextEdit, QFrame, QApplication, QSizePolicy, QLabel)
from PyQt5.QtCore import Qt, pyqtSignal, QThread, QTimer, QObject
from PyQt5.QtGui import QFont, QTextCursor, QTextCharFormat, QColor

# 导入 history_data
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.append(project_root)
UI_STATE_FILE = os.path.join(current_dir, "ui_state.json")

# 尝试导入 RemoteClient
RemoteClient = None
try:
    # 动态添加 client 路径
    # 路径结构: list/.remote_chat/client
    client_path = os.path.join(project_root, ".remote_chat", "client")
    if os.path.exists(client_path):
        if client_path not in sys.path:
            sys.path.append(client_path)
        
        # 尝试导入
        from client_app import RemoteClient
        print(f"RemoteClient imported successfully from {client_path}")
    else:
        print(f"Remote client path not found: {client_path}")
        
except ImportError as e:
    print(f"无法导入 RemoteClient: {e}")
    RemoteClient = None

try:
    from core.core_agent.Agent import AgentSession
except ImportError:
    class AgentSession:
        def chat(self, text, stream=True):
            return "错误：无法加载 AI 代理。"
        def clear_context(self):
            return None

try:
    from tools import token_cal
except ImportError:
    class MockTokenCal:
        def start_session(self, session_id):
            return None
        def set_active_session(self, session_id):
            return None
        def get_total_summary(self):
            return {"tokens": 0, "cost": 0.0}
        def get_session_summary(self, session_id):
            return {"tokens": 0, "cost": 0.0}
    token_cal = MockTokenCal()

try:
    from . import ui_image
except Exception:
    try:
        import ui_image
    except Exception:
        ui_image = None

class RemoteService(QThread):
    """
    后台线程运行远程控制客户端 (asyncio event loop)
    """
    message_received = pyqtSignal(str, dict) # text, context
    
    def __init__(self):
        super().__init__()
        self.client = None
        self.loop = None
        self._is_running = False
        
    def run(self):
        if not RemoteClient:
            print("RemoteClient is None, stopping RemoteService.")
            return
            
        print("RemoteService thread started.")
        # 创建新的事件循环
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        
        try:
            print("Initializing RemoteClient...")
            self.client = RemoteClient(on_message_callback=self._on_remote_message)
            self._is_running = True
            print("RemoteClient initialized. Starting run loop...")
            self.loop.run_until_complete(self.client.run())
        except Exception as e:
            print(f"Remote Service Error in run: {e}")
            import traceback
            traceback.print_exc()
        finally:
            print("RemoteService stopped.")
            self._is_running = False
            self.loop.close()
            
    def _on_remote_message(self, text, context):
        """
        客户端收到消息的回调 (运行在 asyncio 线程)
        通过信号发送到主线程
        """
        print(f"RemoteService callback triggered. Text: '{text}', Context: {context}")
        # 注意：这里的 text 可能是空字符串或者其他，如果为空，需要过滤
        if not text:
            print("Received empty text in callback, ignoring.")
            return
            
        # 使用 QMetaObject.invokeMethod 确保信号在主线程发出，或者直接 emit (PyQt 信号通常是线程安全的)
        try:
            self.message_received.emit(text, context)
            print("Signal message_received emitted.")
        except Exception as e:
            print(f"Error emitting signal: {e}")
        
    def send_reply(self, text, context):
        """
        发送回复 (供主线程调用)
        """
        if self.client and self.loop and self._is_running:
            asyncio.run_coroutine_threadsafe(
                self.client.send_reply(text, context), 
                self.loop
            )
        else:
            print("Remote client not running, cannot send reply.")

    def send_stream_chunk(self, text):
        if self.client and self.loop and self._is_running:
            asyncio.run_coroutine_threadsafe(
                self.client.send_message({"type": "response_chunk", "text": text}),
                self.loop
            )

    def send_stream_end(self):
        if self.client and self.loop and self._is_running:
            asyncio.run_coroutine_threadsafe(
                self.client.send_message({"type": "response_end"}),
                self.loop
            )

    def send_image(self, payload):
        if self.client and self.loop and self._is_running and isinstance(payload, dict):
            asyncio.run_coroutine_threadsafe(
                self.client.send_message({
                    "type": "response_image",
                    "base64": payload.get("base64", ""),
                    "width": payload.get("width"),
                    "height": payload.get("height")
                }),
                self.loop
            )

    def send_stats_update(self, total_tokens, total_cost, session_tokens, session_cost):
        if self.client and self.loop and self._is_running:
            asyncio.run_coroutine_threadsafe(
                self.client.send_message({
                    "type": "stats_update",
                    "total_tokens": total_tokens,
                    "total_cost": total_cost,
                    "session_tokens": session_tokens,
                    "session_cost": session_cost
                }),
                self.loop
            )

    def send_clear_action(self):
        if self.client and self.loop and self._is_running:
            asyncio.run_coroutine_threadsafe(
                self.client.send_message({"type": "clear_chat"}),
                self.loop
            )

    def send_user_message(self, text):
        if self.client and self.loop and self._is_running:
            asyncio.run_coroutine_threadsafe(
                self.client.send_message({"type": "user_message", "text": text}),
                self.loop
            )

class ChatWorker(QThread):
    """后台线程处理 AI 请求"""
    chunk_received = pyqtSignal(str)
    finished = pyqtSignal()
    
    def __init__(self, agent, text):
        super().__init__()
        self.agent = agent
        self.text = text
        self._stop_requested = False

    def request_stop(self):
        self._stop_requested = True
        
    def run(self):
        try:
            # 使用流式输出
            stream = self.agent.chat(self.text, stream=True)
            for chunk in stream:
                if self._stop_requested:
                    if hasattr(stream, "close"):
                        stream.close()
                    break
                self.chunk_received.emit(chunk)
        except Exception as e:
            self.chunk_received.emit(f"Error: {str(e)}")
        self.finished.emit()

class ChatInputEdit(QTextEdit):
    """
    支持 Enter 发送，Ctrl+Enter 换行的输入框
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_panel = parent

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            if event.modifiers() & Qt.ControlModifier:
                # Ctrl+Enter: 换行
                self.insertPlainText("\n")
            else:
                # Enter: 发送
                if self.parent_panel:
                    self.parent_panel.send_message()
        else:
            super().keyPressEvent(event)

class ChatPanel(QWidget):
    """
    AI 聊天面板
    """
    tasks_updated = pyqtSignal()
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.agent = AgentSession()
        
        # 初始化远程服务
        self.remote_service = None
        if RemoteClient:
            self.remote_service = RemoteService()
            self.remote_service.message_received.connect(self.process_remote_message)
            self.remote_service.start()
        
        self.text_color = "white"
        self.border_color = "rgba(255, 255, 255, 50)"
        self.is_light = False
        self.thought_mode = False
        self.progress_mode = False
        self.final_mode = False
        self.stream_buffer = ""
        self.thought_start_token = "[[THOUGHT_START]]"
        self.thought_end_token = "[[THOUGHT_END]]"
        self.progress_start_token = "[[PROGRESS_START]]"
        self.progress_end_token = "[[PROGRESS_END]]"
        self.final_start_token = "[[FINAL_START]]"
        self.final_end_token = "[[FINAL_END]]"
        self.base_font_size = 14
        self.thought_font_size = 12
        self.progress_font_size = max(int(self.base_font_size * 0.8), 7)
        self.session_id = None
        self.session_timer = QTimer(self)
        self.session_timer.setInterval(200)
        self.session_timer.timeout.connect(self.refresh_token_stats)
        self.worker = None
        self.is_processing = False
        self.capture_check_timestamp = None
        
        # 当前正在处理的飞书上下文
        self.current_feishu_context = None
        self.accumulated_response = "" 
        
        # 定义聊天记录持久化文件路径
        self.history_file = os.path.join(project_root, "core", "core_data", "ui_chat_history.html")
        
        self.init_ui()

    def process_remote_message(self, text, context):
        """处理来自 Web 端的远程消息"""
        if context and context.get("action") == "clear_chat":
            self.clear_chat()
            return
        if not text:
            print("Received empty remote message.")
            return
            
        print(f"UI received remote message: {text}")
        
        # 如果当前正忙，可能需要排队或者直接拒绝/并发处理
        # 这里简单起见，如果正忙，则打印日志并忽略（或者排队，但现有逻辑是单 worker）
        if self.is_processing:
            print("ChatPanel is busy, ignoring remote message for now.")
            # 可以在这里给 Web 发一个“正忙”的回复
            if self.remote_service:
                self.remote_service.send_reply("抱歉，AI 正在思考其他问题，请稍后再试。", context)
            return
            
        # 设置当前上下文
        self.current_feishu_context = context
        self.accumulated_response = ""
        
        # 在 UI 上显示用户消息
        self.append_user_message(text, source="远程")
        
        # 触发 AI 处理 (复用 send_message 的逻辑部分)
        self.start_ai_worker(text)
        
    def start_ai_worker(self, text):
        """启动 AI 工作线程"""
        if self.is_processing:
            return

        self.is_processing = True
        # 更新按钮状态 (变成停止按钮)
        self._update_send_button_state()
        
        # 准备 AI 回复容器 (先添加一个空的 AI 消息块)
        self.append_message("AI", "")
        
        # 准备新一轮对话的 UI 状态
        self.stream_buffer = ""
        self.thought_mode = False
        self.progress_mode = False
        self.final_mode = False
        
        # 开始新会话统计
        self.session_id = str(uuid.uuid4())
        token_cal.start_session(self.session_id)
        token_cal.set_active_session(self.session_id)
        self.session_timer.start()
        self.capture_check_timestamp = time.time()
        
        self.worker = ChatWorker(self.agent, text)
        self.worker.chunk_received.connect(self.handle_chunk)
        self.worker.finished.connect(self.handle_finished)
        self.worker.start()

    def handle_chunk(self, chunk):
        """处理流式输出片段"""
        # 累积完整回复，用于发送给 Web 端
        self.accumulated_response += chunk
        # 原有的 UI 更新逻辑
        self.process_stream_chunk(chunk)
        if self.remote_service:
            self.remote_service.send_stream_chunk(chunk)

    def handle_finished(self):
        """处理对话结束"""
        self.is_processing = False
        self._update_send_button_state()
        self.session_timer.stop()
        if self.remote_service:
            self.remote_service.send_stream_end()
        
        if self.current_feishu_context:
            self.current_feishu_context = None
        self.session_timer.stop()
        self.refresh_token_stats()
        
        # 如果是飞书触发的对话，提取最终答案并发送回复
        if self.current_feishu_context and self.feishu_service:
            final_reply = self.extract_final_answer(self.accumulated_response)
            if final_reply:
                self.feishu_service.send_reply(final_reply, self.current_feishu_context)
            self.current_feishu_context = None # 重置上下文
            
        if ui_image:
            payload = ui_image.build_latest_capture_payload(self.capture_check_timestamp)
            if payload.get("success"):
                ui_image.append_capture_payload_to_chat(self.chat_display, payload)
                if self.remote_service:
                    self.remote_service.send_image(payload)
                ui_image.clear_screen_captures()

        # 保存聊天记录
        self.save_chat_history()
        
        # 通知任务更新
        if self.agent.tool_executed_in_last_chat:
             self.tasks_updated.emit()

    def extract_final_answer(self, full_response):
        """从完整响应中提取最终回答 (去除思考过程)"""
        if self.final_start_token in full_response and self.final_end_token in full_response:
            try:
                start = full_response.index(self.final_start_token) + len(self.final_start_token)
                end = full_response.index(self.final_end_token)
                return full_response[start:end].strip()
            except:
                return full_response
        return full_response

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # 顶部工具栏 (添加清空按钮)
        top_bar = QHBoxLayout()
        top_bar.addStretch()

        self.total_stats_frame = QFrame()
        total_layout = QHBoxLayout(self.total_stats_frame)
        total_layout.setContentsMargins(8, 4, 8, 4)
        total_layout.setSpacing(12)
        self.total_tokens_label = QLabel("累计消耗Token数：0")
        self.total_cost_label = QLabel("累计消费：0元")
        total_layout.addWidget(self.total_tokens_label)
        total_layout.addWidget(self.total_cost_label)
        top_bar.addWidget(self.total_stats_frame)
        top_bar.addSpacing(10)

        self.clear_btn = QPushButton("清空历史聊天记录")
        self.clear_btn.setFixedSize(140, 30)
        self.clear_btn.setCursor(Qt.PointingHandCursor)
        self.clear_btn.clicked.connect(self.clear_chat)
        top_bar.addWidget(self.clear_btn)
        
        layout.addLayout(top_bar)
        
        # 聊天记录显示区
        self.chat_display = QTextEdit()
        self.chat_display.setReadOnly(True)
        layout.addWidget(self.chat_display)

        self.session_stats_frame = QFrame()
        session_layout = QHBoxLayout(self.session_stats_frame)
        session_layout.setContentsMargins(8, 4, 8, 4)
        session_layout.setSpacing(12)
        self.session_tokens_label = QLabel("本次消耗Token数：0")
        self.session_cost_label = QLabel("本次消费：0元")
        session_layout.addWidget(self.session_tokens_label)
        session_layout.addWidget(self.session_cost_label)
        layout.addWidget(self.session_stats_frame)
        self.last_total_tokens = None
        self.last_total_cost = None
        self.last_session_tokens = None
        self.last_session_cost = None
        
        # 加载历史聊天记录
        self.load_chat_history()
        self.refresh_token_stats()
        self._apply_saved_ui_state()
        
        # 输入区
        input_layout = QHBoxLayout()
        input_layout.setSpacing(5)
        
        self.input_edit = ChatInputEdit(self)
        self.input_edit.setFixedHeight(60) # 固定高度
        self.input_edit.setPlaceholderText("输入你想问的问题... (Enter发送，Ctrl+Enter换行)")
        
        self.send_btn = QPushButton("发送")
        self.send_btn.setFixedSize(60, 60)
        self.send_btn.setCursor(Qt.PointingHandCursor)
        self.send_btn.clicked.connect(self.on_send_clicked)
        
        input_layout.addWidget(self.input_edit)
        input_layout.addWidget(self.send_btn)
        
        layout.addLayout(input_layout)

    def clear_chat(self):
        """清空聊天记录显示"""
        self.chat_display.clear()
        if hasattr(self.agent, 'clear_context'):
            # 同步清空对话记忆文件
            self.agent.clear_context()
        
        # 删除持久化文件
        if os.path.exists(self.history_file):
            try:
                os.remove(self.history_file)
            except Exception as e:
                print(f"Error removing history file: {e}")
        self.refresh_token_stats()
        if self.remote_service:
            self.remote_service.send_clear_action()

    def save_chat_history(self):
        """保存聊天记录到文件"""
        try:
            html = self.chat_display.toHtml()
            # 确保目录存在
            os.makedirs(os.path.dirname(self.history_file), exist_ok=True)
            with open(self.history_file, 'w', encoding='utf-8') as f:
                f.write(html)
        except Exception as e:
            print(f"Error saving chat history: {e}")

    def load_chat_history(self):
        """从文件加载聊天记录"""
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r', encoding='utf-8') as f:
                    html = f.read()
                    self.chat_display.setHtml(html)
                    self.chat_display.moveCursor(QTextCursor.End)
            except Exception as e:
                print(f"Error loading chat history: {e}")

    def send_message(self):
        """发送消息（用户点击发送按钮或回车）"""
        text = self.input_edit.toPlainText().strip()
        if not text:
            return
        
        # 如果正在处理，则不允许再次发送
        if self.is_processing:
            return

        # 重置标志位
        if hasattr(self.agent, "tool_executed_in_last_chat"):
            self.agent.tool_executed_in_last_chat = False
            
        self.accumulated_response = ""
        self.current_feishu_context = None

        # 在 UI 上显示用户消息
        self.append_user_message(text, source="本地")
        if self.remote_service:
            self.remote_service.send_user_message(text)
        
        # 清空输入框
        self.input_edit.clear()
        
        # 启动 AI 线程
        self.start_ai_worker(text)
        
    def append_user_message(self, text, source="本地"):
        """添加用户消息"""
        self.chat_display.moveCursor(QTextCursor.End)
        self.chat_display.insertPlainText("\n") # 确保换行
        
        # 插入时间戳或分隔符（可选）
        
        # 插入 "User: " 前缀 (蓝色)
        cursor = self.chat_display.textCursor()
        format_user = QTextCharFormat()
        format_user.setForeground(QColor("#007ACC")) # VS Code Blue
        format_user.setFontWeight(QFont.Bold)
        cursor.insertText(f"User({source}): ", format_user)
        
        # 插入消息内容 (黑色/白色)
        format_text = QTextCharFormat()
        if self.is_light:
            format_text.setForeground(QColor("black"))
        else:
            format_text.setForeground(QColor(self.text_color))
        cursor.insertText(f"{text}\n", format_text)
        
        self.chat_display.moveCursor(QTextCursor.End)
        
    def append_message(self, sender, text):
        """添加 AI 消息 (如果是 AI，则只添加前缀，内容通过流式追加)"""
        self.chat_display.moveCursor(QTextCursor.End)
        # 只有当文本不为空时才添加换行符，避免开头的空行
        if self.chat_display.toPlainText().strip():
            self.chat_display.insertPlainText("\n")
        
        cursor = self.chat_display.textCursor()
        format_sender = QTextCharFormat()
        
        if sender == "AI":
            format_sender.setForeground(QColor("#28A745")) # Green
        else:
            format_sender.setForeground(QColor("#007ACC"))
            
        format_sender.setFontWeight(QFont.Bold)
        cursor.insertText(f"{sender}: ", format_sender)
        
        if text:
            format_text = QTextCharFormat()
            if self.is_light:
                format_text.setForeground(QColor("black"))
            else:
                format_text.setForeground(QColor(self.text_color))
            cursor.insertText(f"{text}\n", format_text)
            
        self.chat_display.moveCursor(QTextCursor.End)
    
    def process_stream_chunk(self, chunk):
        """
        处理流式输出的文本块，直接追加到 TextEdit
        TODO: 支持 Markdown 渲染或者特殊 token 解析 (如 [THOUGHT])
        """
        cursor = self.chat_display.textCursor()
        cursor.movePosition(QTextCursor.End)
        
        def build_format():
            format_text = QTextCharFormat()
            if self.thought_mode or self.progress_mode:
                format_text.setForeground(QColor("gray"))
                format_text.setFontItalic(True)
                format_text.setFontPointSize(self.thought_font_size if self.thought_mode else self.progress_font_size)
                return format_text
            if self.is_light:
                format_text.setForeground(QColor("black"))
            else:
                format_text.setForeground(QColor(self.text_color))
            format_text.setFontPointSize(self.base_font_size)
            return format_text

        tokens = [
            (self.thought_start_token, "thought_start"),
            (self.thought_end_token, "thought_end"),
            (self.progress_start_token, "progress_start"),
            (self.progress_end_token, "progress_end"),
            (self.final_start_token, "final_start"),
            (self.final_end_token, "final_end"),
        ]

        remaining = chunk
        while remaining:
            next_index = -1
            next_token = None
            next_type = None
            for token, token_type in tokens:
                index = remaining.find(token)
                if index != -1 and (next_index == -1 or index < next_index):
                    next_index = index
                    next_token = token
                    next_type = token_type

            if next_index == -1:
                cursor.insertText(remaining, build_format())
                break

            if next_index > 0:
                cursor.insertText(remaining[:next_index], build_format())

            if next_type == "thought_start":
                self.thought_mode = True
            elif next_type == "thought_end":
                self.thought_mode = False
            elif next_type == "progress_start":
                self.progress_mode = True
            elif next_type == "progress_end":
                self.progress_mode = False
            elif next_type == "final_start":
                self.final_mode = True
                self.thought_mode = False
                self.progress_mode = False
            elif next_type == "final_end":
                self.final_mode = False

            remaining = remaining[next_index + len(next_token):]
        self.chat_display.moveCursor(QTextCursor.End)
        
    def update_style(self, text_color, border_color, is_light):
        self.text_color = text_color
        self.border_color = border_color
        self.is_light = is_light
        # 刷新现有文本颜色需要重绘，这里暂时只影响新消息

    def refresh_token_stats(self):
        total = token_cal.get_total_summary()
        total_tokens = total.get("tokens", 0)
        total_cost = total.get("cost", 0.0)
        self.total_tokens_label.setText(f"累计消耗Token数：{total_tokens}")
        self.total_cost_label.setText(f"累计消费：{total_cost:.6f}元")
        session_summary = token_cal.get_session_summary(self.session_id) if self.session_id else {"tokens": 0, "cost": 0.0}
        session_tokens = session_summary.get("tokens", 0)
        session_cost = session_summary.get("cost", 0.0)
        self.session_tokens_label.setText(f"本次消耗Token数：{session_tokens}")
        self.session_cost_label.setText(f"本次消费：{session_cost:.6f}元")
        if self.remote_service:
            if (self.last_total_tokens != total_tokens or self.last_total_cost != total_cost or
                self.last_session_tokens != session_tokens or self.last_session_cost != session_cost):
                self.remote_service.send_stats_update(
                    total_tokens, total_cost, session_tokens, session_cost
                )
                self.last_total_tokens = total_tokens
                self.last_total_cost = total_cost
                self.last_session_tokens = session_tokens
                self.last_session_cost = session_cost

    def on_send_clicked(self):
        if self.is_processing:
            self.stop_current_task()
            return
        self.send_message()

    def stop_current_task(self):
        if self.worker and self.worker.isRunning():
            self.worker.request_stop()
        self.is_processing = False
        self.input_edit.setReadOnly(False)
        self._update_send_button_state()
        if self.session_timer.isActive():
            self.session_timer.stop()
        self.refresh_token_stats()
        self.append_message("System", "[用户已停止生成]")

    def _update_send_button_state(self):
        if self.is_processing:
            self.send_btn.setText("停止")
            self.send_btn.setEnabled(True)
            self.send_btn.setStyleSheet("background-color: #d9534f; color: white;") # Red for stop
            # 断开之前的连接，连接到停止
            try: self.send_btn.clicked.disconnect() 
            except: pass
            self.send_btn.clicked.connect(self.stop_current_task)
            return
            
        self.send_btn.setText("发送")
        self.send_btn.setEnabled(True)
        # 恢复样式需要调用 update_style 或者直接设置为空
        # 这里简单设置为空，update_style 会被其他地方调用
        self.send_btn.setStyleSheet("") 
        try: self.send_btn.clicked.disconnect() 
        except: pass
        self.send_btn.clicked.connect(self.on_send_clicked)
        self.update_style(self.text_color, self.border_color, self.is_light)

    def _load_ui_state(self):
        if not os.path.exists(UI_STATE_FILE):
            return {}
        try:
            with open(UI_STATE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _save_ui_state(self, data):
        try:
            os.makedirs(os.path.dirname(UI_STATE_FILE), exist_ok=True)
            with open(UI_STATE_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, separators=(",", ":"))
        except Exception:
            pass

    def _apply_saved_ui_state(self):
        data = self._load_ui_state()
        state = data.get("chat_panel", {})
        width = state.get("width")
        height = state.get("height")
        if isinstance(width, int) and isinstance(height, int) and width > 0 and height > 0:
            self.resize(width, height)

    def resizeEvent(self, event):
        data = self._load_ui_state()
        data["chat_panel"] = {"width": self.width(), "height": self.height()}
        self._save_ui_state(data)
        super().resizeEvent(event)

    def update_style(self, text_color, border_color, is_light_theme):
        self.text_color = text_color
        self.border_color = border_color
        self.is_light = is_light_theme
        self.base_font_size = 10
        self.thought_font_size = max(self.base_font_size * 0.8, 7)
        self.progress_font_size = max(self.base_font_size * 0.8, 7)
        
        bg_color = "rgba(0, 0, 0, 30)" if is_light_theme else "rgba(255, 255, 255, 10)"
        input_bg = "rgba(0, 0, 0, 10)" if is_light_theme else "rgba(255, 255, 255, 20)"
        
        # 聊天记录区样式
        self.chat_display.setStyleSheet(f"""
            QTextEdit {{
                background-color: {bg_color};
                border: 1px solid {border_color};
                border-radius: 5px;
                color: {text_color};
                font-family: "Microsoft YaHei";
                font-size: 14px;
                padding: 10px;
            }}
            QScrollBar:vertical {{
                border: none;
                background: transparent;
                width: 6px;
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background: rgba(255, 255, 255, 50);
                min-height: 20px;
                border-radius: 3px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: rgba(255, 255, 255, 100);
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)
        
        # 输入框样式
        self.input_edit.setStyleSheet(f"""
            QTextEdit {{
                background-color: {input_bg};
                border: 1px solid {border_color};
                border-radius: 5px;
                color: {text_color};
                font-family: "Microsoft YaHei";
                font-size: 14px;
            }}
        """)
        
        # 按钮样式
        btn_hover = "rgba(0, 0, 0, 20)" if is_light_theme else "rgba(255, 255, 255, 30)"
        btn_style = f"""
            QPushButton {{
                background-color: transparent;
                border: 1px solid {border_color};
                border-radius: 5px;
                color: {text_color};
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {btn_hover};
            }}
        """
        self.send_btn.setStyleSheet(btn_style)
        self.clear_btn.setStyleSheet(btn_style)
        self.total_stats_frame.setStyleSheet(f"""
            QFrame {{
                background-color: transparent;
                border: 1px solid {border_color};
                border-radius: 5px;
                color: {text_color};
            }}
        """)
        self.session_stats_frame.setStyleSheet(f"""
            QFrame {{
                background-color: transparent;
                border: 1px solid {border_color};
                border-radius: 5px;
                color: {text_color};
            }}
        """)
        self.total_tokens_label.setStyleSheet(f"color: {text_color};")
        self.total_cost_label.setStyleSheet(f"color: {text_color};")
        self.session_tokens_label.setStyleSheet(f"color: {text_color};")
        self.session_cost_label.setStyleSheet(f"color: {text_color};")
