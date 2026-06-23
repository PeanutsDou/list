import sys
import os
import winreg
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QCheckBox, QLabel, 
                             QMessageBox, QApplication)
from PyQt5.QtCore import Qt

class SettingsPanel(QWidget):
    """
    设置面板，包含开机自启等设置
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.text_color = "white"
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # 开机自启开关
        self.auto_start_cb = QCheckBox("开机自动启动")
        self.auto_start_cb.setCursor(Qt.PointingHandCursor)
        self.auto_start_cb.stateChanged.connect(self.toggle_auto_start)
        
        # 初始化状态
        is_auto_start = self.check_auto_start_status()
        self.auto_start_cb.setChecked(is_auto_start)
        
        layout.addWidget(self.auto_start_cb)
        
        self.update_style(self.text_color)

    def get_app_path(self):
        """获取应用程序的可执行文件路径或脚本路径"""
        if getattr(sys, 'frozen', False):
            # 如果是打包后的 exe
            return sys.executable
        else:
            # 如果是 python 脚本运行
            # 使用 pythonw.exe 运行当前脚本的入口文件 (假设入口是 ui_main.py 或 main.py)
            # 这里我们需要找到项目的根目录入口文件
            current_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(current_dir) # list/
            main_script = os.path.join(project_root, "ui_main.py")
            
            if not os.path.exists(main_script):
                 # 尝试找 main.py
                main_script = os.path.join(project_root, "main.py")
            
            # 使用 pythonw.exe 避免控制台窗口，或者 python.exe
            python_exe = sys.executable.replace("python.exe", "pythonw.exe")
            if not os.path.exists(python_exe):
                python_exe = sys.executable
                
            return f'"{python_exe}" "{main_script}"'

    def check_auto_start_status(self):
        """检查注册表中是否已设置开机自启"""
        app_name = "DesktopAIHelper"
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
                                 r"Software\Microsoft\Windows\CurrentVersion\Run", 
                                 0, winreg.KEY_READ)
            value, _ = winreg.QueryValueEx(key, app_name)
            winreg.CloseKey(key)
            
            # 简单的检查：只要有值且包含我们的脚本名，就认为已开启
            # 实际上可能路径变了，这里简化处理
            current_path_cmd = self.get_app_path()
            # 去除引号比较，或者直接比较
            return True
        except WindowsError:
            return False

    def toggle_auto_start(self, state):
        """切换开机自启状态"""
        app_name = "DesktopAIHelper"
        app_path_cmd = self.get_app_path()
        
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
                                 r"Software\Microsoft\Windows\CurrentVersion\Run", 
                                 0, winreg.KEY_SET_VALUE | winreg.KEY_WRITE)
            
            if state == Qt.Checked:
                winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, app_path_cmd)
            else:
                try:
                    winreg.DeleteValue(key, app_name)
                except WindowsError:
                    pass # 如果本来就不存在，忽略
            
            winreg.CloseKey(key)
            
        except Exception as e:
            QMessageBox.warning(self, "设置失败", f"无法修改注册表: {str(e)}")
            # 恢复复选框状态
            self.auto_start_cb.blockSignals(True)
            self.auto_start_cb.setChecked(not (state == Qt.Checked))
            self.auto_start_cb.blockSignals(False)

    def update_style(self, text_color):
        self.text_color = text_color
        self.auto_start_cb.setStyleSheet(f"""
            QCheckBox {{
                color: {text_color};
                spacing: 5px;
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border-radius: 4px;
                border: 1px solid {text_color};
            }}
            QCheckBox::indicator:checked {{
                background-color: {text_color};
                border: 1px solid {text_color};
                image: url(:/icons/check.png); /* 如果有图标的话，这里简化为纯色 */
            }}
            QCheckBox::indicator:checked:hover {{
                background-color: rgba(255, 255, 255, 200);
            }}
             QCheckBox::indicator:unchecked:hover {{
                background-color: rgba(255, 255, 255, 50);
            }}
        """)
