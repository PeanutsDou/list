import webbrowser
import os
import sys

def open_url(url):
    """
    使用默认浏览器打开指定的 URL，优先尝试 Google Chrome。
    
    Args:
        url (str): 要打开的网页地址。
        
    Returns:
        dict: 操作结果状态。
    """
    try:
        # 补全协议头
        if not url.startswith(("http://", "https://", "file://")):
            url = "https://" + url

        # 尝试查找 Chrome 浏览器路径 (Windows)
        chrome_paths = [
            r"C:\Program Files\Google\Chrome\Application\chrome.exe",
            r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
            os.path.expanduser(r"~\AppData\Local\Google\Chrome\Application\chrome.exe")
        ]
        
        chrome_path = None
        for path in chrome_paths:
            if os.path.exists(path):
                chrome_path = path
                break
        
        if chrome_path:
            # 注册 Chrome 浏览器
            # %s 是 webbrowser 模块要求的占位符
            webbrowser.register('chrome', None, webbrowser.BackgroundBrowser(chrome_path))
            try:
                webbrowser.get('chrome').open(url)
                return {
                    "status": "success",
                    "message": f"Opened URL with Chrome: {url}",
                    "browser": "Chrome"
                }
            except Exception:
                # 如果 Chrome 打开失败，回退到系统默认
                pass
        
        # 使用系统默认浏览器
        webbrowser.open(url)
        return {
            "status": "success",
            "message": f"Opened URL with default browser: {url}",
            "browser": "Default"
        }

    except Exception as e:
        return {
            "status": "error",
            "error": str(e)
        }

if __name__ == "__main__":
    # 测试代码
    test_url = "www.baidu.com"
    print(f"Opening {test_url}...")
    result = open_url(test_url)
    print(result)
