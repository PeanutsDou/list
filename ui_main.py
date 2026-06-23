import sys
import os
import subprocess
import atexit

# 将当前目录添加到 sys.path，以便能找到 ui 模块
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from PyQt5.QtWidgets import QApplication
from ui.ui_window_transform import DesktopSideBar
from ui.ui_animation import AnimationLayerWindow
from ai_time_tools import ai_email

def start_web_monitor():
    """启动网页监控后台进程"""
    monitor_script = os.path.join(current_dir, "ai_konwledge", "web_konwledge", "web_monitor_sys.py")
    if os.path.exists(monitor_script):
        try:
            # 准备启动参数
            creation_flags = 0
            startupinfo = None
            
            if os.name == 'nt':
                # Windows 下隐藏控制台窗口
                creation_flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0x08000000)
                # 某些情况下还需要 startupinfo
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                
            process = subprocess.Popen(
                [sys.executable, monitor_script],
                cwd=os.path.dirname(monitor_script),
                startupinfo=startupinfo,
                creationflags=creation_flags,
                # 重定向输出以避免潜在的缓冲区阻塞或控制台干扰
                stdout=subprocess.DEVNULL, 
                stderr=subprocess.DEVNULL
            )
            print(f"Web monitor started with PID: {process.pid}")
            
            # 注册退出清理函数
            def cleanup():
                if process.poll() is None:
                    print("Stopping web monitor...")
                    process.terminate()
                    try:
                        process.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        process.kill()
            
            atexit.register(cleanup)
            return process
        except Exception as e:
            print(f"Failed to start web monitor: {e}")
    else:
        print(f"Web monitor script not found at: {monitor_script}")
    return None

def start_soft_monitor():
    monitor_script = os.path.join(current_dir, "ai_konwledge", "soft_konwledge", "soft_monitor_sys.py")
    if os.path.exists(monitor_script):
        try:
            creation_flags = 0
            startupinfo = None
            if os.name == 'nt':
                creation_flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0x08000000)
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            process = subprocess.Popen(
                [sys.executable, monitor_script],
                cwd=os.path.dirname(monitor_script),
                startupinfo=startupinfo,
                creationflags=creation_flags,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
            print(f"Soft monitor started with PID: {process.pid}")
            def cleanup():
                if process.poll() is None:
                    print("Stopping soft monitor...")
                    process.terminate()
                    try:
                        process.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        process.kill()
            atexit.register(cleanup)
            return process
        except Exception as e:
            print(f"Failed to start soft monitor: {e}")
    else:
        print(f"Soft monitor script not found at: {monitor_script}")
    return None

def main():
    app = QApplication(sys.argv)
    
    # 启动后台监控
    start_web_monitor()
    start_soft_monitor()

    # 初始化邮件服务(定时任务恢复与实时邮件检查)
    ai_email.init_email_service()
    
    # 实例化并显示主窗口
    window = DesktopSideBar()
    window.show()

    # 实例化并显示动画层窗口
    animation_layer = AnimationLayerWindow()
    animation_layer.show()
    animation_layer.raise_()
    window.lower()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
