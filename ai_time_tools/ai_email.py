import os
import sys
import smtplib
import ssl
import threading
import uuid
import datetime
import time
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formataddr, formatdate, make_msgid

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.append(project_root)

try:
    from tools.config_loader import get_email_config
except ImportError:
    def get_email_config():
        return {}

# 尝试导入 core.llm_client 用于实时邮件生成
try:
    from core import llm_client
except ImportError:
    llm_client = None

_SCHEDULE_LOCK = threading.Lock()
_SCHEDULE_TASKS = {} # 内存中的定时任务记录 (task_id -> dict)
_ACTIVE_TIMERS = {} # 内存中的定时器对象 (task_id -> threading.Timer)

EMAIL_TASKS_FILE = os.path.join(project_root, "ai_konwledge", "email_tasks.json")

def _load_email_tasks_data():
    if not os.path.exists(EMAIL_TASKS_FILE):
        return {"scheduled_tasks": [], "realtime_tasks": []}
    try:
        with open(EMAIL_TASKS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"scheduled_tasks": [], "realtime_tasks": []}

def _save_email_tasks_data(data):
    try:
        with open(EMAIL_TASKS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving email tasks: {e}")

def write_email(subject, body, to, cc=None, bcc=None, sender_email="", sender_name="", reply_to="", is_html=False, charset="utf-8"):
    config = get_email_config()
    sender_email = sender_email or config.get("default_sender", "")
    
    # 如果 to 为空，尝试使用默认收件人
    if not to and config.get("default_recipient"):
        to = config.get("default_recipient")

    recipients = _normalize_recipients(to)
    if not recipients:
        return {"success": False, "reason": "to_empty", "message": "收件人不能为空"}
    content = {
        "subject": "" if subject is None else str(subject),
        "body": "" if body is None else str(body),
        "to": recipients,
        "cc": _normalize_recipients(cc),
        "bcc": _normalize_recipients(bcc),
        "sender_email": "" if sender_email is None else str(sender_email),
        "sender_name": "" if sender_name is None else str(sender_name),
        "reply_to": "" if reply_to is None else str(reply_to),
        "is_html": bool(is_html),
        "charset": "" if charset is None else str(charset)
    }
    return {"success": True, "message": "邮件内容已生成", "email": content}


def send_email(subject, body, to=None, cc=None, bcc=None, sender_email="", sender_name="", reply_to="", is_html=False, charset="utf-8",
               smtp_server="", smtp_port=None, smtp_ssl=None, smtp_user="", smtp_auth_code="", smtp_auth_file="", timeout=20):
    
    config = get_email_config()
    
    # 填充默认配置
    smtp_server = smtp_server or config.get("smtp_server", "smtp.qq.com")
    if smtp_port is None:
        smtp_port = config.get("smtp_port", 465)
    if smtp_ssl is None:
        smtp_ssl = config.get("smtp_ssl", True)
    smtp_user = smtp_user or config.get("smtp_user", "")
    sender_email = sender_email or config.get("default_sender", "") or smtp_user
    smtp_auth_code = smtp_auth_code or config.get("smtp_auth_code", "")

    # 如果 to 为空，尝试使用默认收件人
    if not to and config.get("default_recipient"):
        to = config.get("default_recipient")

    recipients = _normalize_recipients(to)
    if not recipients:
        return {"success": False, "reason": "to_empty", "message": "收件人不能为空"}
    cc_list = _normalize_recipients(cc)
    bcc_list = _normalize_recipients(bcc)
    sender_email = (sender_email or smtp_user or "").strip()
    if not sender_email:
        return {"success": False, "reason": "sender_empty", "message": "发件人邮箱不能为空"}
    smtp_user = (smtp_user or sender_email).strip()
    
    auth_code = _load_auth_code(smtp_auth_code, smtp_auth_file)
    if not auth_code:
        return {"success": False, "reason": "auth_code_missing", "message": "SMTP 授权码为空或不可用"}
    message = _build_message(
        subject=subject,
        body=body,
        to_list=recipients,
        cc_list=cc_list,
        sender_email=sender_email,
        sender_name=sender_name,
        reply_to=reply_to,
        is_html=is_html,
        charset=charset
    )
    all_recipients = recipients + cc_list + bcc_list
    try:
        _send_smtp(
            smtp_server=smtp_server,
            smtp_port=int(smtp_port) if smtp_port is not None else 465,
            smtp_ssl=bool(smtp_ssl),
            smtp_user=smtp_user,
            smtp_auth_code=auth_code,
            sender_email=sender_email,
            recipients=all_recipients,
            message=message,
            timeout=int(timeout) if timeout is not None else 20
        )
        return {
            "success": True,
            "message": "邮件发送成功",
            "message_id": message.get("Message-ID", ""),
            "to": recipients,
            "cc": cc_list,
            "bcc": bcc_list,
            "sender": sender_email
        }
    except Exception as exc:
        return {"success": False, "reason": "send_failed", "message": f"发送失败: {str(exc)}"}


def schedule_send_email(subject, body, to=None, send_at="", delay_seconds=0, recurrence=None, cc=None, bcc=None, sender_email="", sender_name="", reply_to="", is_html=False, charset="utf-8",
                        smtp_server="", smtp_port=None, smtp_ssl=None, smtp_user="", smtp_auth_code="", smtp_auth_file="", timeout=20):
    """
    定时发送邮件，支持单次或周期性发送。
    """
    config = get_email_config()
    # 如果 to 为空，尝试使用默认收件人
    if not to and config.get("default_recipient"):
        to = config.get("default_recipient")

    recipients = _normalize_recipients(to)
    if not recipients:
        return {"success": False, "reason": "to_empty", "message": "收件人不能为空"}
    
    # 计算首次延迟
    initial_delay = _resolve_delay_seconds(send_at, delay_seconds)
    
    # 如果没有指定时间且有周期性配置，尝试从周期配置计算下一次执行时间
    if initial_delay is None and recurrence:
        initial_delay = _calculate_next_recurrence_delay(recurrence)
    
    if initial_delay is None:
        # 如果既没指定时间也没周期，立即发送
        if not recurrence:
             return send_email(subject, body, to, cc, bcc, sender_email, sender_name, reply_to, is_html, charset, smtp_server, smtp_port, smtp_ssl, smtp_user, smtp_auth_code, smtp_auth_file, timeout)
        else:
             initial_delay = 0 

    if initial_delay < 0:
        initial_delay = 0

    task_id = str(uuid.uuid4())
    scheduled_at = datetime.datetime.now() + datetime.timedelta(seconds=initial_delay)
    
    args = {
        "subject": subject,
        "body": body,
        "to": recipients,
        "cc": cc,
        "bcc": bcc,
        "sender_email": sender_email,
        "sender_name": sender_name,
        "reply_to": reply_to,
        "is_html": is_html,
        "charset": charset,
        "smtp_server": smtp_server,
        "smtp_port": smtp_port,
        "smtp_ssl": smtp_ssl,
        "smtp_user": smtp_user,
        "smtp_auth_code": smtp_auth_code,
        "smtp_auth_file": smtp_auth_file,
        "timeout": timeout
    }
    
    task_info = {
        "task_id": task_id,
        "type": "scheduled",
        "status": "scheduled",
        "created_at": datetime.datetime.now().isoformat(),
        "scheduled_at": scheduled_at.isoformat(),
        "recurrence": recurrence,
        "args": args
    }

    # 保存到文件
    data = _load_email_tasks_data()
    data["scheduled_tasks"].append(task_info)
    _save_email_tasks_data(data)

    # 启动定时器
    _start_timer_for_task(task_id, initial_delay, args, recurrence)
    
    return {
        "success": True,
        "message": "已创建定时发送任务",
        "task_id": task_id,
        "scheduled_at": scheduled_at.isoformat(),
        "recurrence": str(recurrence) if recurrence else "none"
    }

def _start_timer_for_task(task_id, delay, args, recurrence):
    def _task_wrapper():
        _execute_scheduled_send(task_id, args)
        
        # 处理周期性调度
        if recurrence:
            next_delay = _calculate_next_recurrence_delay(recurrence, from_time=datetime.datetime.now())
            if next_delay is not None and next_delay >= 0:
                _start_timer_for_task(task_id, next_delay, args, recurrence)
                # 更新文件中的下一次执行时间
                with _SCHEDULE_LOCK:
                    data = _load_email_tasks_data()
                    for t in data["scheduled_tasks"]:
                        if t["task_id"] == task_id:
                            t["status"] = "scheduled_recurring"
                            t["scheduled_at"] = (datetime.datetime.now() + datetime.timedelta(seconds=next_delay)).isoformat()
                            break
                    _save_email_tasks_data(data)

    timer = threading.Timer(delay, _task_wrapper)
    timer.daemon = True
    with _SCHEDULE_LOCK:
        _ACTIVE_TIMERS[task_id] = timer
        _SCHEDULE_TASKS[task_id] = { # 简单的内存缓存
             "task_id": task_id,
             "status": "scheduled"
        }
    timer.start()

def delete_email_task(task_id):
    """
    删除指定的邮件任务（定时或实时）。
    """
    with _SCHEDULE_LOCK:
        # 1. 尝试停止正在运行的定时器
        if task_id in _ACTIVE_TIMERS:
            timer = _ACTIVE_TIMERS.pop(task_id)
            timer.cancel()
        if task_id in _SCHEDULE_TASKS:
            _SCHEDULE_TASKS.pop(task_id)
        
        # 2. 从文件中删除
        data = _load_email_tasks_data()
        original_len = len(data["scheduled_tasks"]) + len(data["realtime_tasks"])
        
        data["scheduled_tasks"] = [t for t in data["scheduled_tasks"] if t["task_id"] != task_id]
        data["realtime_tasks"] = [t for t in data["realtime_tasks"] if t["task_id"] != task_id]
        
        new_len = len(data["scheduled_tasks"]) + len(data["realtime_tasks"])
        
        if original_len != new_len:
            _save_email_tasks_data(data)
            return {"success": True, "message": f"任务 {task_id} 已删除"}
        else:
            return {"success": False, "message": f"未找到 ID 为 {task_id} 的任务"}

def add_realtime_email_task(prompt, to=None, subject_hint="实时邮件"):
    """
    添加一个实时邮件任务（每日首次启动时发送）。
    """
    config = get_email_config()
    if not to and config.get("default_recipient"):
        to = config.get("default_recipient")
    
    recipients = _normalize_recipients(to)
    if not recipients:
        return {"success": False, "message": "收件人不能为空"}

    task_id = str(uuid.uuid4())
    task_info = {
        "task_id": task_id,
        "type": "realtime",
        "trigger": "daily_first_start",
        "prompt": prompt,
        "subject_hint": subject_hint,
        "to": recipients,
        "created_at": datetime.datetime.now().isoformat(),
        "last_run_date": ""
    }
    
    data = _load_email_tasks_data()
    data["realtime_tasks"].append(task_info)
    _save_email_tasks_data(data)
    
    return {"success": True, "message": "实时邮件任务已添加", "task_id": task_id}

def get_email_tasks(query_type="all"):
    """
    获取邮件任务列表。
    query_type: "all", "scheduled", "realtime"
    """
    data = _load_email_tasks_data()
    if query_type == "scheduled":
        return data["scheduled_tasks"]
    elif query_type == "realtime":
        return data["realtime_tasks"]
    else:
        return data

def init_email_service():
    """
    初始化邮件服务：
    1. 恢复定时任务
    2. 检查并运行实时任务
    """
    threading.Thread(target=_restore_scheduled_tasks, daemon=True).start()
    threading.Thread(target=_check_and_run_realtime_tasks, daemon=True).start()

def _restore_scheduled_tasks():
    """恢复未过期的定时任务"""
    data = _load_email_tasks_data()
    now = datetime.datetime.now()
    
    for task in data["scheduled_tasks"]:
        task_id = task.get("task_id")
        recurrence = task.get("recurrence")
        args = task.get("args")
        scheduled_at_str = task.get("scheduled_at")
        
        if not task_id or not args:
            continue
            
        scheduled_at = _parse_datetime(scheduled_at_str)
        delay = 0
        
        if scheduled_at:
            if scheduled_at > now:
                delay = (scheduled_at - now).total_seconds()
            elif recurrence:
                # 已经过期，但有周期性，计算下一次
                delay = _calculate_next_recurrence_delay(recurrence)
                if delay is None:
                    continue
            else:
                # 过期且无周期，忽略
                continue
        elif recurrence:
             delay = _calculate_next_recurrence_delay(recurrence)
             if delay is None:
                continue

        if delay is not None:
            _start_timer_for_task(task_id, delay, args, recurrence)

def _check_and_run_realtime_tasks():
    """检查并运行实时任务"""
    if not llm_client:
        print("Warning: llm_client not available, realtime email tasks skipped.")
        return

    data = _load_email_tasks_data()
    today_str = datetime.date.today().isoformat()
    tasks_to_run = []
    
    for task in data["realtime_tasks"]:
        if task.get("last_run_date") != today_str:
            tasks_to_run.append(task)
    
    if not tasks_to_run:
        return

    # 等待几秒确保网络就绪
    time.sleep(5)
    
    for task in tasks_to_run:
        prompt = task.get("prompt")
        recipients = task.get("to")
        task_id = task.get("task_id")
        subject_hint = task.get("subject_hint", "实时邮件")
        
        # 调用 LLM 生成内容
        try:
            full_prompt = f"请根据以下要求撰写一封邮件。\n要求：{prompt}\n\n请以JSON格式返回，包含 'subject' 和 'body' 两个字段。subject是邮件标题，body是邮件正文（可以是HTML格式）。不要返回Markdown代码块，直接返回JSON字符串。"
            llm_response = llm_client.one_chat(full_prompt)
            
            # 解析 LLM 返回的 JSON
            # 这里做一个简单的清洗，防止 LLM 返回 markdown code block
            cleaned_response = llm_response.strip()
            if cleaned_response.startswith("```json"):
                cleaned_response = cleaned_response[7:]
            if cleaned_response.startswith("```"):
                cleaned_response = cleaned_response[3:]
            if cleaned_response.endswith("```"):
                cleaned_response = cleaned_response[:-3]
            
            try:
                email_content = json.loads(cleaned_response)
                subject = email_content.get("subject", subject_hint)
                body = email_content.get("body", "无正文")
            except json.JSONDecodeError:
                # Fallback if JSON parsing fails
                subject = f"{subject_hint} - {today_str}"
                body = llm_response
            
            # 发送邮件
            send_email(subject, body, to=recipients, is_html=True)
            
            # 更新 last_run_date
            task["last_run_date"] = today_str
            
        except Exception as e:
            print(f"Error executing realtime task {task_id}: {e}")
            
    # 保存状态更新
    _save_email_tasks_data(data)

def _calculate_next_recurrence_delay(recurrence, from_time=None):
    """
    根据周期配置计算下一次执行的等待秒数。
    """
    now = from_time or datetime.datetime.now()
    
    if isinstance(recurrence, str):
        rtype = recurrence.lower()
        if rtype == "daily":
            # 明天同一时间
            target = now + datetime.timedelta(days=1)
            return (target - now).total_seconds()
        elif rtype == "weekly":
            target = now + datetime.timedelta(weeks=1)
            return (target - now).total_seconds()
        elif rtype == "monthly":
            # 简单处理：30天后
            target = now + datetime.timedelta(days=30)
            return (target - now).total_seconds()
        elif rtype == "yearly":
            target = now + datetime.timedelta(days=365)
            return (target - now).total_seconds()
        return None

    if isinstance(recurrence, dict):
        rtype = recurrence.get("type", "").lower()
        if rtype == "interval":
            return float(recurrence.get("seconds", 0))
        
        # 针对定点发送 (daily, weekly)
        target_time_str = recurrence.get("time") # HH:MM:SS
        if target_time_str:
            try:
                # 解析目标时间
                parts = target_time_str.split(":")
                h, m = int(parts[0]), int(parts[1])
                s = int(parts[2]) if len(parts) > 2 else 0
                
                target = now.replace(hour=h, minute=m, second=s, microsecond=0)
                
                if rtype == "daily":
                    if target <= now:
                        target += datetime.timedelta(days=1)
                elif rtype == "weekly":
                    weekday = int(recurrence.get("weekday", 0)) # 0=Monday
                    days_ahead = weekday - now.weekday()
                    if days_ahead <= 0: # Target day already happened this week
                        if days_ahead == 0 and target > now: # Today is the day, but later
                            pass 
                        else:
                            days_ahead += 7
                    target += datetime.timedelta(days=days_ahead)
                    # 如果计算出的 target 还是比 now 小（例如 weekday 就是今天，但时间已过），需要 +7 天
                    if target <= now:
                         target += datetime.timedelta(days=7)
                
                return (target - now).total_seconds()
            except Exception:
                return None
                
    return None


def _execute_scheduled_send(task_id, kwargs):
    result = send_email(**kwargs)
    # 不再需要维护内存中的 _SCHEDULE_TASKS 状态，因为我们主要依赖文件
    # 但为了调试或短时状态查询，可以保留一点
    pass 


def _sanitize_result(result):
    if not isinstance(result, dict):
        return result
    sanitized = dict(result)
    if "auth_code" in sanitized:
        sanitized.pop("auth_code", None)
    return sanitized


def _resolve_delay_seconds(send_at, delay_seconds):
    if delay_seconds is not None:
        try:
            delay_value = float(delay_seconds)
            if delay_value >= 0:
                return delay_value
        except Exception:
            pass
    if send_at:
        target = _parse_datetime(send_at)
        if target is None:
            return None
        now = datetime.datetime.now()
        return max(0.0, (target - now).total_seconds())
    return None


def _parse_datetime(value):
    if not value:
        return None
    if isinstance(value, datetime.datetime):
        return value
    text = str(value).strip()
    if not text:
        return None
    try:
        return datetime.datetime.fromisoformat(text)
    except Exception:
        pass
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y/%m/%d %H:%M:%S", "%Y/%m/%d %H:%M"):
        try:
            return datetime.datetime.strptime(text, fmt)
        except Exception:
            continue
    return None


def _normalize_recipients(value):
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        items = []
        for item in value:
            if item is None:
                continue
            part = str(item).strip()
            if part:
                items.append(part)
        return items
    text = str(value).replace("；", ";").replace("，", ",")
    parts = []
    for chunk in text.split(","):
        for piece in chunk.split(";"):
            item = piece.strip()
            if item:
                parts.append(item)
    return parts


def _build_message(subject, body, to_list, cc_list, sender_email, sender_name="", reply_to="", is_html=False, charset="utf-8"):
    subtype = "html" if is_html else "plain"
    message = MIMEMultipart()
    message["Subject"] = "" if subject is None else str(subject)
    message["From"] = formataddr((sender_name, sender_email)) if sender_name else sender_email
    message["To"] = ", ".join(to_list)
    if cc_list:
        message["Cc"] = ", ".join(cc_list)
    if reply_to:
        message["Reply-To"] = reply_to
    message["Date"] = formatdate(localtime=True)
    message["Message-ID"] = make_msgid()
    content = "" if body is None else str(body)
    message.attach(MIMEText(content, subtype, charset))
    return message


def _load_auth_code(smtp_auth_code, smtp_auth_file):
    if smtp_auth_code:
        return str(smtp_auth_code).strip()
    path = smtp_auth_file or os.path.join(project_root, "邮箱smtp")
    if not path:
        return ""
    if not os.path.exists(path):
        return ""
    try:
        with open(path, "r", encoding="utf-8") as file:
            content = file.read().strip()
        if not content:
            return ""
        for line in content.splitlines():
            text = line.strip()
            if not text:
                continue
            if ":" in text:
                key, value = text.split(":", 1)
                if key.strip().lower() in {"qq", "smtp", "auth", "authorization"}:
                    return value.strip()
            if text:
                return text
        return ""
    except Exception:
        return ""


def _send_smtp(smtp_server, smtp_port, smtp_ssl, smtp_user, smtp_auth_code, sender_email, recipients, message, timeout):
    context = ssl.create_default_context()
    if smtp_ssl:
        with smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=timeout, context=context) as server:
            server.login(smtp_user, smtp_auth_code)
            server.sendmail(sender_email, recipients, message.as_string())
    else:
        with smtplib.SMTP(smtp_server, smtp_port, timeout=timeout) as server:
            server.starttls(context=context)
            server.login(smtp_user, smtp_auth_code)
            server.sendmail(sender_email, recipients, message.as_string())
