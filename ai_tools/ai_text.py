import os
import json
from typing import List, Dict, Any

try:
    from PyQt5.QtWidgets import QTextEdit
    from PyQt5.QtGui import QTextCharFormat, QColor, QFont
except Exception:
    QTextEdit = None
    QTextCharFormat = None
    QColor = None
    QFont = None

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "core", "core_data")
NOTE_FILE = os.path.join(DATA_DIR, "notes.html")
STYLE_FILE = os.path.join(DATA_DIR, "notes_style.json")


def _ensure_dirs():
    os.makedirs(DATA_DIR, exist_ok=True)


def save_note(html: str) -> Dict[str, Any]:
    _ensure_dirs()
    try:
        with open(NOTE_FILE, "w", encoding="utf-8") as f:
            f.write(html if html is not None else "")
        return {"success": True, "path": NOTE_FILE}
    except Exception as e:
        return {"success": False, "error": str(e)}


def read_note() -> Dict[str, Any]:
    if not os.path.exists(NOTE_FILE):
        return {"success": True, "content": ""}
    try:
        with open(NOTE_FILE, "r", encoding="utf-8") as f:
            return {"success": True, "content": f.read()}
    except Exception as e:
        return {"success": False, "error": str(e), "content": ""}


def clear_note() -> Dict[str, Any]:
    _ensure_dirs()
    try:
        with open(NOTE_FILE, "w", encoding="utf-8") as f:
            f.write("")
        return {"success": True}
    except Exception as e:
        return {"success": False, "error": str(e)}


def append_note(text: str) -> Dict[str, Any]:
    current = read_note()
    if not current.get("success", False):
        return current
    html = current.get("content", "")
    addition = f"<p>{text}</p>"
    new_html = (html or "") + addition
    return save_note(new_html)


def search_note(keyword: str, context_len: int = 30) -> Dict[str, Any]:
    content = read_note().get("content", "")
    plain = _strip_html(content)
    result: List[Dict[str, Any]] = []
    if not keyword:
        return {"success": True, "matches": result}
    idx = 0
    low_plain = plain.lower()
    low_kw = keyword.lower()
    while True:
        pos = low_plain.find(low_kw, idx)
        if pos == -1:
            break
        start = max(0, pos - context_len)
        end = min(len(plain), pos + len(keyword) + context_len)
        snippet = plain[start:end]
        result.append({"index": pos, "snippet": snippet})
        idx = pos + len(keyword)
    return {"success": True, "matches": result}


def _strip_html(html: str) -> str:
    import re
    return re.sub(r"<[^>]+>", "", html or "")


def set_note_style_preferences(font_family: str = "Microsoft YaHei",
                               font_size: int = 14,
                               color: str = "#FFFFFF",
                               bold: bool = False,
                               italic: bool = False) -> Dict[str, Any]:
    _ensure_dirs()
    prefs = {
        "font_family": font_family,
        "font_size": font_size,
        "color": color,
        "bold": bold,
        "italic": italic
    }
    try:
        with open(STYLE_FILE, "w", encoding="utf-8") as f:
            json.dump(prefs, f, ensure_ascii=False, indent=2)
        return {"success": True, "preferences": prefs}
    except Exception as e:
        return {"success": False, "error": str(e)}


def get_note_style_preferences() -> Dict[str, Any]:
    if not os.path.exists(STYLE_FILE):
        return {
            "success": True,
            "preferences": {
                "font_family": "Microsoft YaHei",
                "font_size": 14,
                "color": "#FFFFFF",
                "bold": False,
                "italic": False
            }
        }
    try:
        with open(STYLE_FILE, "r", encoding="utf-8") as f:
            return {"success": True, "preferences": json.load(f)}
    except Exception as e:
        return {"success": False, "error": str(e)}

def toggle_bold(editor: "QTextEdit") -> None:
    if QTextEdit is None or not isinstance(editor, QTextEdit):
        return
    cursor = editor.textCursor()
    fmt = QTextCharFormat()
    is_bold = cursor.charFormat().fontWeight() == QFont.Bold
    fmt.setFontWeight(QFont.Normal if is_bold else QFont.Bold)
    cursor.mergeCharFormat(fmt)
    editor.mergeCurrentCharFormat(fmt)


def toggle_italic(editor: "QTextEdit") -> None:
    if QTextEdit is None or not isinstance(editor, QTextEdit):
        return
    cursor = editor.textCursor()
    fmt = QTextCharFormat()
    fmt.setFontItalic(not cursor.charFormat().fontItalic())
    cursor.mergeCharFormat(fmt)
    editor.mergeCurrentCharFormat(fmt)


def increase_font_size(editor: "QTextEdit", step: int = 1) -> None:
    if QTextEdit is None or not isinstance(editor, QTextEdit):
        return
    cursor = editor.textCursor()
    current_size = int(cursor.charFormat().fontPointSize() or editor.fontPointSize() or 14)
    fmt = QTextCharFormat()
    fmt.setFontPointSize(max(6, current_size + step))
    cursor.mergeCharFormat(fmt)
    editor.mergeCurrentCharFormat(fmt)


def decrease_font_size(editor: "QTextEdit", step: int = 1) -> None:
    increase_font_size(editor, -step)



def write_note(content: str) -> Dict[str, Any]:
    html = f"<p>{content}</p>" if "<" not in content else content
    return save_note(html)


def update_note(content: str) -> Dict[str, Any]:
    return write_note(content)


def get_note() -> Dict[str, Any]:
    return read_note()


def replace_note_text(old_text: str, new_text: str, replace_all: bool = True) -> Dict[str, Any]:
    current = read_note()
    if not current.get("success", False):
        return current
    html = current.get("content", "")
    if replace_all:
        html = html.replace(old_text, new_text)
    else:
        html = html.replace(old_text, new_text, 1)
    return save_note(html)


def remove_note_text(target_text: str, remove_all: bool = True) -> Dict[str, Any]:
    return replace_note_text(target_text, "", remove_all)


def apply_style_to_editor(editor: "QTextEdit", preferences: Dict[str, Any]) -> None:
    if QTextEdit is None or not isinstance(editor, QTextEdit):
        return
    font_family = preferences.get("font_family", "Microsoft YaHei")
    font_size = preferences.get("font_size", 14)
    color = preferences.get("color", "#FFFFFF")
    bold = preferences.get("bold", False)
    italic = preferences.get("italic", False)
    cursor = editor.textCursor()
    cursor.select(cursor.Document)
    fmt = QTextCharFormat()
    if QFont:
        font = QFont(font_family, font_size)
        font.setBold(bold)
        font.setItalic(italic)
        fmt.setFont(font)
    if QColor:
        fmt.setForeground(QColor(color))
    cursor.mergeCharFormat(fmt)
    editor.mergeCurrentCharFormat(fmt)
    editor.setFont(QFont(font_family, font_size))


def load_note_to_editor(editor: "QTextEdit") -> None:
    if QTextEdit is None or not isinstance(editor, QTextEdit):
        return
    data = read_note()
    if data.get("success", False):
        editor.setHtml(data.get("content", ""))
    prefs = get_note_style_preferences().get("preferences", {})
    apply_style_to_editor(editor, prefs)


def save_editor_content(editor: "QTextEdit") -> Dict[str, Any]:
    if QTextEdit is None or not isinstance(editor, QTextEdit):
        return {"success": False, "error": "editor_unavailable"}
    return save_note(editor.toHtml())


def set_font_size(editor: "QTextEdit", font_size: int) -> None:
    if QTextEdit is None or not isinstance(editor, QTextEdit):
        return
    fmt = QTextCharFormat()
    fmt.setFontPointSize(max(6, font_size))
    cursor = editor.textCursor()
    cursor.mergeCharFormat(fmt)
    editor.mergeCurrentCharFormat(fmt)
