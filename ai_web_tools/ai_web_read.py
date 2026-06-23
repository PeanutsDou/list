import sys
import json
import time

try:
    import uiautomation as auto
except ImportError:
    auto = None

def get_all_browsers_info():
    """
    获取所有正在运行的浏览器窗口信息（包括后台窗口）。
    返回列表，每个元素为字典：
    [
      {"title": str, "url": str, "browser_type": str, "status": "success"},
      ...
    ]
    """
    if auto is None:
        return [{
            "status": "error",
            "error": "Missing dependency: uiautomation. Please install it using 'pip install uiautomation'."
        }]

    results = []
    
    try:
        # 获取根节点下的所有顶层窗口
        root = auto.GetRootControl()
        windows = root.GetChildren()
        
        for window in windows:
            # 必须是窗口控件
            if window.ControlTypeName != "WindowControl":
                continue
                
            title = window.Name
            class_name = window.ClassName
            browser_type = "Unknown"
            
            # 判断是否为目标浏览器
            # 注意：某些应用可能内嵌 Chrome 内核（如 Electron 应用），这里主要针对标准浏览器
            if "Chrome" in class_name or "Google Chrome" in title:
                browser_type = "Chrome"
            elif "Edge" in class_name or "Microsoft Edge" in title:
                browser_type = "Edge"
            elif "Firefox" in class_name or "Mozilla Firefox" in title:
                browser_type = "Firefox"
            else:
                continue
            
            # 排除当前 IDE 窗口（如果它被识别为浏览器，例如基于 Electron 的编辑器）
            # 这里简单过滤掉标题包含 "Trae" 或 "VS Code" 的窗口，防止递归分析自己
            if "Trae" in title or "Visual Studio Code" in title:
                continue

            url = "Unknown"
            
            # 针对 Chrome/Edge/Firefox 的地址栏查找逻辑
            try:
                # 限制搜索深度以提高性能
                # RegexName 匹配常见语言的地址栏名称
                address_bar = window.EditControl(searchDepth=12, RegexName=".*地址.*|.*Address.*|.*搜索.*|.*Search.*|.*Location.*")
                
                if address_bar.Exists(0, 0):
                    # 尝试通过 ValuePattern 获取值
                    if hasattr(address_bar, 'GetValuePattern'):
                        pattern = address_bar.GetValuePattern()
                        if pattern:
                            url = pattern.Value
                    
                    # 兼容性尝试
                    if (not url or url == "Unknown") and hasattr(address_bar, 'GetLegacyIAccessiblePattern'):
                        pattern = address_bar.GetLegacyIAccessiblePattern()
                        if pattern:
                            url = pattern.Value
            except Exception:
                # 单个窗口获取失败不影响整体
                pass
            
            # 格式化 URL
            if url and url != "Unknown":
                url = url.strip()
                if not url.startswith(("http://", "https://", "file://", "chrome://", "edge://", "about:")):
                    if "." in url and " " not in url:
                        url = "https://" + url

            results.append({
                "status": "success",
                "title": title,
                "url": url,
                "browser_type": browser_type
            })

    except Exception as e:
        return [{
            "status": "error",
            "error": str(e)
        }]

    if not results:
        return [{"status": "info", "message": "No active browser windows found."}]
        
    return results

if __name__ == "__main__":
    # 测试代码
    print("正在扫描所有浏览器窗口...")
    data = get_all_browsers_info()
    print(json.dumps(data, indent=2, ensure_ascii=False))
