import os
import json
import logging
import asyncio
from typing import Dict, Any

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.responses import HTMLResponse
import uvicorn

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 加载配置
CONFIG_FILE = "config.json"
if os.path.exists(CONFIG_FILE):
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        CONFIG = json.load(f)
else:
    logger.error("Config file not found!")
    CONFIG = {}

SERVER_CONFIG = CONFIG.get("server", {})
AUTH_TOKEN = SERVER_CONFIG.get("auth_token", "default_token")

app = FastAPI()

# HTML 聊天界面
HTML_CONTENT = """
<!DOCTYPE html>
<html>
    <head>
        <title>Remote Chat</title>
        <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
        <style>
            html, body {
                height: 100%;
                margin: 0;
                padding: 0;
                background: #0f1216;
                color: #e8e8e8;
                font-family: "Microsoft YaHei", Arial, sans-serif;
            }
            .app {
                display: flex;
                flex-direction: column;
                height: 100%;
            }
            .app-header {
                padding: 12px;
                background: #151a20;
                border-bottom: 1px solid #2a2f36;
            }
            .title {
                font-size: 16px;
                font-weight: 600;
                margin-bottom: 8px;
            }
            .stats {
                display: flex;
                flex-direction: column;
                gap: 4px;
                font-size: 12px;
                color: #c7c7c7;
            }
            .stat-row {
                display: flex;
                justify-content: space-between;
                gap: 12px;
            }
            .clear-btn {
                margin-top: 8px;
                width: 100%;
                background: #3a3f47;
                color: #ffffff;
                border: none;
                border-radius: 10px;
                padding: 10px 12px;
                font-weight: 600;
            }
            .messages {
                flex: 1;
                overflow-y: auto;
                padding: 12px;
                display: flex;
                flex-direction: column;
                gap: 10px;
            }
            .message {
                display: flex;
                align-items: flex-start;
                gap: 8px;
            }
            .message.user {
                justify-content: flex-end;
            }
            .bubble {
                max-width: 82%;
                padding: 10px 12px;
                border-radius: 12px;
                background: #1f242b;
                color: #e8e8e8;
                white-space: pre-wrap;
                word-break: break-word;
                font-size: 14px;
            }
            .bubble img {
                max-width: 100%;
                border-radius: 8px;
                display: block;
                height: auto;
                object-fit: contain;
                max-height: 50vh;
                cursor: zoom-in;
            }
            .message.user .bubble {
                background: #2d6cdf;
                color: #ffffff;
                border-bottom-right-radius: 4px;
            }
            .message.assistant .bubble {
                border-bottom-left-radius: 4px;
            }
            .message.system .bubble {
                background: #2b3038;
                color: #c7c7c7;
            }
            .segment {
                white-space: pre-wrap;
            }
            .segment.thought {
                color: #9aa0a6;
                font-size: 12px;
                font-style: italic;
            }
            .segment.progress {
                color: #9aa0a6;
                font-size: 11px;
            }
            .segment.final {
                color: #e8e8e8;
                font-size: 14px;
            }
            .input-bar {
                display: flex;
                gap: 8px;
                padding: 10px;
                background: #151a20;
                border-top: 1px solid #2a2f36;
            }
            #messageInput {
                flex: 1;
                resize: none;
                border-radius: 10px;
                background: #0f1216;
                color: #e8e8e8;
                border: 1px solid #2a2f36;
                padding: 10px;
                font-size: 14px;
            }
            #sendBtn {
                background: #2d6cdf;
                color: #ffffff;
                border: none;
                border-radius: 10px;
                padding: 10px 14px;
                font-weight: 600;
                min-width: 64px;
            }
            .image-preview {
                position: fixed;
                inset: 0;
                background: rgba(0, 0, 0, 0.7);
                display: none;
                align-items: center;
                justify-content: center;
                z-index: 9999;
            }
            .image-preview.active {
                display: flex;
            }
            .image-preview img {
                max-width: 92vw;
                max-height: 92vh;
                border-radius: 10px;
                cursor: zoom-out;
                transform-origin: center center;
            }
            .preview-toolbar {
                position: fixed;
                top: 12px;
                right: 12px;
                display: flex;
                gap: 8px;
                z-index: 10000;
            }
            .preview-toolbar button {
                background: #2d6cdf;
                color: #ffffff;
                border: none;
                border-radius: 8px;
                padding: 6px 10px;
                font-weight: 600;
            }
            .image-menu {
                position: fixed;
                display: none;
                flex-direction: column;
                gap: 6px;
                padding: 8px;
                background: #1f242b;
                border: 1px solid #2a2f36;
                border-radius: 10px;
                z-index: 10001;
            }
            .image-menu button {
                background: #2d6cdf;
                color: #ffffff;
                border: none;
                border-radius: 8px;
                padding: 6px 12px;
                font-weight: 600;
                white-space: nowrap;
            }
        </style>
    </head>
    <body>
        <div class="app">
            <div class="app-header">
                <div class="title">Remote Chat</div>
                <div class="stats">
                    <div class="stat-row">
                        <span id="totalTokens">累计消耗Token数：0</span>
                        <span id="totalCost">累计消费：0元</span>
                    </div>
                    <div class="stat-row">
                        <span id="sessionTokens">本次消耗Token数：0</span>
                        <span id="sessionCost">本次消费：0元</span>
                    </div>
                    <div class="stat-row">
                        <span id="connStatus">连接中...</span>
                    </div>
                </div>
                <button id="clearBtn" class="clear-btn">清空历史聊天记录</button>
            </div>
            <div id="messageList" class="messages"></div>
            <div class="input-bar">
                <textarea id="messageInput" rows="2" placeholder="输入你想问的问题..."></textarea>
                <button id="sendBtn">发送</button>
            </div>
        </div>
        <div id="imagePreview" class="image-preview">
            <div class="preview-toolbar">
                <button id="zoomInBtn">放大</button>
                <button id="zoomOutBtn">缩小</button>
                <button id="zoomResetBtn">重置</button>
            </div>
            <img id="previewImage" src="" />
        </div>
        <div id="imageMenu" class="image-menu">
            <button id="saveImageBtn">保存图片</button>
        </div>

        <script>
            var wsProtocol = window.location.protocol === "https:" ? "wss://" : "ws://";
            var wsUrl = wsProtocol + window.location.host + "/ws/web";
            var fallbackUrl = "ws://" + window.location.host + "/ws/web";
            var ws = null;
            var messageList = document.getElementById("messageList");
            var messageInput = document.getElementById("messageInput");
            var sendBtn = document.getElementById("sendBtn");
            var clearBtn = document.getElementById("clearBtn");
            var totalTokens = document.getElementById("totalTokens");
            var totalCost = document.getElementById("totalCost");
            var sessionTokens = document.getElementById("sessionTokens");
            var sessionCost = document.getElementById("sessionCost");
            var connStatus = document.getElementById("connStatus");
            var imagePreview = document.getElementById("imagePreview");
            var previewImage = document.getElementById("previewImage");
            var zoomInBtn = document.getElementById("zoomInBtn");
            var zoomOutBtn = document.getElementById("zoomOutBtn");
            var zoomResetBtn = document.getElementById("zoomResetBtn");
            var imageMenu = document.getElementById("imageMenu");
            var saveImageBtn = document.getElementById("saveImageBtn");

            var currentAssistantBubble = null;
            var currentMode = "normal";
            var pendingText = "";
            var reconnectTimer = null;
            var activeWsUrl = wsUrl;
            var currentPreviewSrc = "";
            var currentScale = 1;
            var longPressTimer = null;

            var tokenPairs = [
                { start: "[[THOUGHT_START]]", end: "[[THOUGHT_END]]", mode: "thought" },
                { start: "[[PROGRESS_START]]", end: "[[PROGRESS_END]]", mode: "progress" },
                { start: "[[FINAL_START]]", end: "[[FINAL_END]]", mode: "final" }
            ];
            var allTokens = tokenPairs.reduce(function(acc, pair) {
                acc.push(pair.start);
                acc.push(pair.end);
                return acc;
            }, []);

            function connectWs(targetUrl) {
                activeWsUrl = targetUrl || wsUrl;
                ws = new WebSocket(activeWsUrl);
                ws.onopen = function() {
                    updateConnectionStatus(true);
                };
                ws.onclose = function() {
                    updateConnectionStatus(false);
                    if (activeWsUrl !== fallbackUrl && fallbackUrl !== wsUrl) {
                        connectWs(fallbackUrl);
                        return;
                    }
                    scheduleReconnect();
                };
                ws.onerror = function() {
                    updateConnectionStatus(false);
                    if (activeWsUrl !== fallbackUrl && fallbackUrl !== wsUrl) {
                        connectWs(fallbackUrl);
                        return;
                    }
                };
                ws.onmessage = function(event) {
                    var data = {};
                    try {
                        data = JSON.parse(event.data);
                    } catch (e) {
                        return;
                    }
                    handleIncoming(data);
                };
            }

            function handleIncoming(data) {
                var type = data.type || "response_full";
                if (type === "response_chunk") {
                    appendAssistantChunk(data.text || "");
                } else if (type === "response_end") {
                    finalizeAssistant();
                } else if (type === "response_full") {
                    addAssistantMessage(data.text || "");
                    finalizeAssistant();
                } else if (type === "response_image") {
                    finalizeAssistant();
                    addAssistantImage(data.base64 || "", data.width, data.height);
                } else if (type === "stats_update") {
                    updateStats(data);
                } else if (type === "clear_chat") {
                    clearMessages();
                } else if (type === "user_message") {
                    addUserMessage(data.text || "");
                } else if (type === "system") {
                    addAssistantMessage(data.text || "");
                    finalizeAssistant();
                } else if (data.text) {
                    addAssistantMessage(data.text);
                    finalizeAssistant();
                }
            }

            function updateStats(data) {
                if (typeof data.total_tokens !== "undefined") {
                    totalTokens.textContent = "累计消耗Token数：" + data.total_tokens;
                }
                if (typeof data.total_cost !== "undefined") {
                    totalCost.textContent = "累计消费：" + Number(data.total_cost).toFixed(6) + "元";
                }
                if (typeof data.session_tokens !== "undefined") {
                    sessionTokens.textContent = "本次消耗Token数：" + data.session_tokens;
                }
                if (typeof data.session_cost !== "undefined") {
                    sessionCost.textContent = "本次消费：" + Number(data.session_cost).toFixed(6) + "元";
                }
            }

            function addUserMessage(text) {
                if (!text) {
                    return;
                }
                var message = document.createElement("div");
                message.className = "message user";
                var bubble = document.createElement("div");
                bubble.className = "bubble";
                bubble.textContent = text;
                message.appendChild(bubble);
                messageList.appendChild(message);
                scrollToBottom();
            }

            function addSystemMessage(text) {
                if (!text) {
                    return;
                }
                var message = document.createElement("div");
                message.className = "message system";
                var bubble = document.createElement("div");
                bubble.className = "bubble";
                bubble.textContent = text;
                message.appendChild(bubble);
                messageList.appendChild(message);
                scrollToBottom();
            }

            function addAssistantMessage(text) {
                if (!text) {
                    return;
                }
                var message = document.createElement("div");
                message.className = "message assistant";
                var bubble = document.createElement("div");
                bubble.className = "bubble";
                bubble.textContent = text;
                message.appendChild(bubble);
                messageList.appendChild(message);
                scrollToBottom();
            }

            function addAssistantImage(base64Data, width, height) {
                if (!base64Data) {
                    return;
                }
                var message = document.createElement("div");
                message.className = "message assistant";
                var bubble = document.createElement("div");
                bubble.className = "bubble";
                var img = document.createElement("img");
                img.src = "data:image/png;base64," + base64Data;
                attachImageInteractions(img, img.src);
                bubble.appendChild(img);
                message.appendChild(bubble);
                messageList.appendChild(message);
                scrollToBottom();
            }

            function ensureAssistantBubble() {
                if (currentAssistantBubble) {
                    return;
                }
                var message = document.createElement("div");
                message.className = "message assistant";
                var bubble = document.createElement("div");
                bubble.className = "bubble";
                message.appendChild(bubble);
                messageList.appendChild(message);
                currentAssistantBubble = bubble;
            }

            function appendTextWithMode(text, mode) {
                if (!text) {
                    return;
                }
                var span = document.createElement("span");
                span.className = "segment " + mode;
                span.textContent = text;
                currentAssistantBubble.appendChild(span);
            }

            function findNextToken(text) {
                var nextIndex = -1;
                var nextToken = null;
                var isStart = false;
                var nextMode = "normal";
                tokenPairs.forEach(function(pair) {
                    var startIndex = text.indexOf(pair.start);
                    if (startIndex >= 0 && (nextIndex === -1 || startIndex < nextIndex)) {
                        nextIndex = startIndex;
                        nextToken = pair.start;
                        isStart = true;
                        nextMode = pair.mode;
                    }
                    var endIndex = text.indexOf(pair.end);
                    if (endIndex >= 0 && (nextIndex === -1 || endIndex < nextIndex)) {
                        nextIndex = endIndex;
                        nextToken = pair.end;
                        isStart = false;
                        nextMode = pair.mode;
                    }
                });
                if (nextIndex === -1) {
                    return null;
                }
                return { index: nextIndex, token: nextToken, isStart: isStart, mode: nextMode };
            }

            function getTailKeepLength(text) {
                var maxLen = 0;
                allTokens.forEach(function(token) {
                    var maxCheck = Math.min(token.length - 1, text.length);
                    for (var len = maxCheck; len > 0; len--) {
                        if (text.endsWith(token.slice(0, len))) {
                            if (len > maxLen) {
                                maxLen = len;
                            }
                            break;
                        }
                    }
                });
                return maxLen;
            }

            function appendAssistantChunk(chunk) {
                if (!chunk) {
                    return;
                }
                ensureAssistantBubble();
                pendingText += chunk;
                while (true) {
                    var found = findNextToken(pendingText);
                    if (!found) {
                        var keepLen = getTailKeepLength(pendingText);
                        var outputText = pendingText.slice(0, pendingText.length - keepLen);
                        appendTextWithMode(outputText, currentMode);
                        pendingText = pendingText.slice(pendingText.length - keepLen);
                        break;
                    }
                    if (found.index > 0) {
                        appendTextWithMode(pendingText.slice(0, found.index), currentMode);
                        pendingText = pendingText.slice(found.index);
                    }
                    if (pendingText.indexOf(found.token) === 0) {
                        pendingText = pendingText.slice(found.token.length);
                        if (found.isStart) {
                            currentMode = found.mode;
                        } else {
                            currentMode = "normal";
                        }
                    }
                }
                scrollToBottom();
            }

            function finalizeAssistant() {
                if (currentAssistantBubble) {
                    if (pendingText) {
                        appendTextWithMode(pendingText, currentMode);
                    }
                    pendingText = "";
                    currentMode = "normal";
                    currentAssistantBubble = null;
                }
            }

            function clearMessages() {
                messageList.innerHTML = "";
                pendingText = "";
                currentMode = "normal";
                currentAssistantBubble = null;
            }

            function sendMessage() {
                if (!ws || ws.readyState !== 1) {
                    addSystemMessage("连接未就绪，正在尝试重连...");
                    scheduleReconnect();
                    return;
                }
                var text = messageInput.value.trim();
                if (!text) {
                    return;
                }
                addUserMessage(text);
                ws.send(JSON.stringify({ type: "chat", text: text }));
                messageInput.value = "";
            }

            function sendClear() {
                if (ws && ws.readyState === 1) {
                    ws.send(JSON.stringify({ type: "clear_chat" }));
                }
                clearMessages();
            }

            function scrollToBottom() {
                messageList.scrollTop = messageList.scrollHeight;
            }

            function updateConnectionStatus(isConnected) {
                if (isConnected) {
                    connStatus.textContent = "已连接: " + activeWsUrl;
                    sendBtn.disabled = false;
                } else {
                    connStatus.textContent = "连接断开: " + activeWsUrl;
                    sendBtn.disabled = true;
                }
            }

            function scheduleReconnect() {
                if (reconnectTimer) {
                    return;
                }
                reconnectTimer = setTimeout(function() {
                    reconnectTimer = null;
                    connectWs(activeWsUrl || wsUrl);
                }, 2000);
            }

            function applyPreviewScale() {
                previewImage.style.transform = "scale(" + currentScale.toFixed(2) + ")";
            }

            function openPreview(src) {
                currentPreviewSrc = src;
                previewImage.src = src;
                currentScale = 1;
                applyPreviewScale();
                imagePreview.classList.add("active");
                hideImageMenu();
            }

            function closePreview() {
                imagePreview.classList.remove("active");
            }

            function showImageMenu(src, x, y) {
                currentPreviewSrc = src;
                imageMenu.style.left = x + "px";
                imageMenu.style.top = y + "px";
                imageMenu.style.display = "flex";
            }

            function hideImageMenu() {
                imageMenu.style.display = "none";
            }

            function triggerSaveImage(src) {
                if (!src) {
                    return;
                }
                var link = document.createElement("a");
                link.href = src;
                link.download = "screen_" + Date.now() + ".png";
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);
            }

            function attachImageInteractions(img, src) {
                img.addEventListener("click", function() {
                    openPreview(src);
                });
                img.addEventListener("contextmenu", function(event) {
                    event.preventDefault();
                    showImageMenu(src, event.clientX, event.clientY);
                });
                img.addEventListener("touchstart", function(event) {
                    if (longPressTimer) {
                        clearTimeout(longPressTimer);
                    }
                    var touch = event.touches && event.touches[0];
                    if (!touch) {
                        return;
                    }
                    longPressTimer = setTimeout(function() {
                        showImageMenu(src, touch.clientX, touch.clientY);
                        longPressTimer = null;
                    }, 600);
                });
                img.addEventListener("touchend", function() {
                    if (longPressTimer) {
                        clearTimeout(longPressTimer);
                        longPressTimer = null;
                    }
                });
            }

            imagePreview.addEventListener("click", function(event) {
                if (event.target === imagePreview) {
                    closePreview();
                }
            });
            previewImage.addEventListener("contextmenu", function(event) {
                event.preventDefault();
                showImageMenu(previewImage.src, event.clientX, event.clientY);
            });
            previewImage.addEventListener("wheel", function(event) {
                event.preventDefault();
                var delta = event.deltaY > 0 ? -0.1 : 0.1;
                currentScale = Math.max(0.2, Math.min(5, currentScale + delta));
                applyPreviewScale();
            });
            zoomInBtn.addEventListener("click", function() {
                currentScale = Math.min(5, currentScale + 0.2);
                applyPreviewScale();
            });
            zoomOutBtn.addEventListener("click", function() {
                currentScale = Math.max(0.2, currentScale - 0.2);
                applyPreviewScale();
            });
            zoomResetBtn.addEventListener("click", function() {
                currentScale = 1;
                applyPreviewScale();
            });
            saveImageBtn.addEventListener("click", function(event) {
                event.preventDefault();
                triggerSaveImage(currentPreviewSrc);
                hideImageMenu();
            });
            document.addEventListener("click", function(event) {
                if (!imageMenu.contains(event.target)) {
                    hideImageMenu();
                }
            });

            sendBtn.addEventListener("click", sendMessage);
            clearBtn.addEventListener("click", sendClear);
            messageInput.addEventListener("keydown", function(event) {
                if (event.key === "Enter" && !event.shiftKey) {
                    event.preventDefault();
                    sendMessage();
                }
            });

            connectWs(wsUrl);
        </script>
    </body>
</html>
"""

class ConnectionManager:
    def __init__(self):
        self.desktop_clients: Dict[str, WebSocket] = {} # 桌面端连接
        self.web_clients: list[WebSocket] = []     # 网页端连接

    async def connect_desktop(self, websocket: WebSocket, client_id: str):
        await websocket.accept()
        self.desktop_clients[client_id] = websocket
        logger.info(f"Desktop Client {client_id} connected")

    def disconnect_desktop(self, client_id: str):
        if client_id in self.desktop_clients:
            del self.desktop_clients[client_id]
            logger.info(f"Desktop Client {client_id} disconnected")

    async def connect_web(self, websocket: WebSocket):
        await websocket.accept()
        self.web_clients.append(websocket)
        logger.info("Web Client connected")
    
    def disconnect_web(self, websocket: WebSocket):
        if websocket in self.web_clients:
            self.web_clients.remove(websocket)
            logger.info("Web Client disconnected")

    async def send_to_desktop(self, message: str):
        # 广播给所有连接的桌面客户端 (或者指定 target)
        # 这里简化为广播给所有 local_client
        target_id = "local_client"
        if target_id in self.desktop_clients:
             try:
                 await self.desktop_clients[target_id].send_text(message)
                 return True
             except:
                 return False
        # 如果 local_client 不在，尝试发给第一个
        elif self.desktop_clients:
             key = list(self.desktop_clients.keys())[0]
             try:
                 await self.desktop_clients[key].send_text(message)
                 return True
             except:
                 return False
        return False

    async def send_to_web(self, message: str):
        # 广播给所有网页客户端
        for client in self.web_clients:
            try:
                await client.send_text(message)
            except:
                pass

manager = ConnectionManager()

@app.get("/")
async def get():
    return HTMLResponse(HTML_CONTENT)

@app.websocket("/ws/web")
async def websocket_web_endpoint(websocket: WebSocket):
    await manager.connect_web(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                msg_type = message.get("type")
                if msg_type == "chat":
                    text = message.get("text", "")
                    if text:
                        logger.info(f"Received from Web: {text}")
                        payload = {
                            "type": "chat",
                            "text": text,
                            "context": {"source": "web"}
                        }
                        success = await manager.send_to_desktop(json.dumps(payload))
                        if not success:
                            await websocket.send_text(json.dumps({"type": "system", "text": "桌面端未连接"}))
                elif msg_type == "clear_chat":
                    payload = {"type": "clear_chat", "context": {"source": "web"}}
                    success = await manager.send_to_desktop(json.dumps(payload))
                    if not success:
                        await websocket.send_text(json.dumps({"type": "system", "text": "桌面端未连接"}))

            except json.JSONDecodeError:
                pass
    except WebSocketDisconnect:
        manager.disconnect_web(websocket)

@app.websocket("/ws/client")
async def websocket_desktop_endpoint(websocket: WebSocket):
    # 简单的鉴权
    token = websocket.query_params.get("token")
    if token != AUTH_TOKEN:
        await websocket.close(code=1008)
        return

    await websocket.accept()
    
    # 临时 ID
    temp_id = f"temp_{id(websocket)}"
    manager.desktop_clients[temp_id] = websocket
    client_id = temp_id
    
    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
                msg_type = message.get("type")
                
                if msg_type == "client_connect":
                    # 客户端注册身份
                    new_client_id = message.get("client_name", "local_client")
                    logger.info(f"Desktop Client registered as: {new_client_id}")
                    
                    if temp_id in manager.desktop_clients:
                        del manager.desktop_clients[temp_id]
                    manager.desktop_clients[new_client_id] = websocket
                    client_id = new_client_id
                    
                elif msg_type == "response":
                    # AI 处理完成，或者桌面端主动发消息
                    result_text = message.get("text", "")
                    if result_text:
                        await manager.send_to_web(json.dumps({"type": "response_full", "text": result_text}))

                elif msg_type == "response_chunk":
                    result_text = message.get("text", "")
                    if result_text:
                        await manager.send_to_web(json.dumps({"type": "response_chunk", "text": result_text}))

                elif msg_type == "response_end":
                    await manager.send_to_web(json.dumps({"type": "response_end"}))

                elif msg_type == "response_image":
                    await manager.send_to_web(json.dumps({
                        "type": "response_image",
                        "base64": message.get("base64", ""),
                        "width": message.get("width"),
                        "height": message.get("height")
                    }))

                elif msg_type == "stats_update":
                    await manager.send_to_web(json.dumps({
                        "type": "stats_update",
                        "total_tokens": message.get("total_tokens"),
                        "total_cost": message.get("total_cost"),
                        "session_tokens": message.get("session_tokens"),
                        "session_cost": message.get("session_cost")
                    }))

                elif msg_type == "clear_chat":
                    await manager.send_to_web(json.dumps({"type": "clear_chat"}))

                elif msg_type == "user_message":
                    text = message.get("text", "")
                    if text:
                        await manager.send_to_web(json.dumps({"type": "user_message", "text": text}))
                
                elif msg_type == "pong":
                    pass
                    
            except json.JSONDecodeError:
                logger.error("Invalid JSON from client")
                
    except WebSocketDisconnect:
        if client_id in manager.desktop_clients:
            manager.disconnect_desktop(client_id)

if __name__ == "__main__":
    uvicorn.run(app, host=SERVER_CONFIG.get("host", "0.0.0.0"), port=SERVER_CONFIG.get("port", 8000))
