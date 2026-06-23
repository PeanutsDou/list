import os
import sys
import json
import datetime
from typing import List, Dict, Optional

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.append(project_root)

# 记账数据存储路径
DATA_FILE = os.path.join(project_root, "ai_konwledge", "money_knowledge.json")

def _load_data() -> List[Dict]:
    if not os.path.exists(DATA_FILE):
        return []
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                return []
            data = json.loads(content)
            return data if isinstance(data, list) else []
    except Exception:
        return []

def _save_data(data: List[Dict]):
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def add_transaction(amount: float, category: str, description: str = "", type: str = "expense", date: str = "") -> Dict:
    """
    添加一笔收支记录。
    
    Args:
        amount: 金额
        category: 分类 (如: 餐饮, 交通, 工资)
        description: 备注
        type: 类型 (expense: 支出, income: 收入)
        date: 日期 (YYYY-MM-DD), 默认为今天
    """
    try:
        amount = float(amount)
    except ValueError:
        return {"success": False, "message": "金额必须是数字"}

    if not date:
        date = datetime.date.today().isoformat()
    
    record = {
        "id": str(datetime.datetime.now().timestamp()),
        "date": date,
        "type": type,
        "amount": amount,
        "category": category,
        "description": description,
        "created_at": datetime.datetime.now().isoformat()
    }
    
    data = _load_data()
    data.append(record)
    _save_data(data)
    
    return {"success": True, "message": "记账成功", "record": record}

def get_transactions(start_date: str = "", end_date: str = "", category: str = "", type: str = "") -> Dict:
    """
    查询收支记录。
    """
    data = _load_data()
    filtered = []
    
    for item in data:
        if type and item.get("type") != type:
            continue
        if category and category not in item.get("category", ""):
            continue
        if start_date and item.get("date") < start_date:
            continue
        if end_date and item.get("date") > end_date:
            continue
        filtered.append(item)
        
    # 按日期倒序
    filtered.sort(key=lambda x: x["date"], reverse=True)
    
    return {"success": True, "count": len(filtered), "transactions": filtered}

def get_summary(period: str = "month", date: str = "") -> Dict:
    """
    获取收支统计。
    period: month (默认), year, total
    date: 指定日期或月份 (YYYY-MM 或 YYYY), 默认为当前
    """
    data = _load_data()
    if not date:
        now = datetime.date.today()
        if period == "month":
            date = now.strftime("%Y-%m")
        elif period == "year":
            date = now.strftime("%Y")
            
    total_income = 0.0
    total_expense = 0.0
    category_stats = {}
    
    for item in data:
        item_date = item.get("date", "")
        if period == "month" and not item_date.startswith(date):
            continue
        if period == "year" and not item_date.startswith(date):
            continue
            
        amount = item.get("amount", 0.0)
        itype = item.get("type", "expense")
        cat = item.get("category", "其他")
        
        if itype == "income":
            total_income += amount
        else:
            total_expense += amount
            category_stats[cat] = category_stats.get(cat, 0.0) + amount
            
    return {
        "success": True,
        "period": period,
        "date": date,
        "total_income": round(total_income, 2),
        "total_expense": round(total_expense, 2),
        "balance": round(total_income - total_expense, 2),
        "category_stats": category_stats
    }
