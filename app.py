"""
Phonics Tracker - 丽声自然拼读打卡程序
基于艾宾浩斯遗忘曲线的间隔重复学习系统
"""

import json
import os
import io
import base64
from datetime import datetime, timedelta
from collections import defaultdict

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# 内嵍课程数据作为fallback（确保在任何目录运行都能加载课程）
try:
    from curriculum_data import EMBEDDED_CURRICULUM
except ImportError:
    EMBEDDED_CURRICULUM = None

# ============== 配置 ==============
DATA_DIR = os.path.join(os.path.dirname(__file__), "data")
CURRICULUM_FILE = os.path.join(DATA_DIR, "curriculum.json")
PROGRESS_FILE = os.path.join(DATA_DIR, "progress.json")
SETTINGS_FILE = os.path.join(DATA_DIR, "settings.json")

# 艾宾浩斯复习间隔（天）
DEFAULT_REVIEW_INTERVALS = [1, 2, 4, 7, 15, 30]
# 薄弱点加强复习间隔（天）
WEAK_POINT_INTERVALS = [1, 2, 3, 5, 7, 10]

# ============== 数据操作 ==============
def load_json(path, default=None):
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return default if default is not None else {}

def save_json(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def _find_curriculum_file():
    """尝试从多个路径查找 curriculum.json"""
    candidates = [
        CURRICULUM_FILE,
        os.path.join(os.getcwd(), "data", "curriculum.json"),
        os.path.join(os.getcwd(), "curriculum.json"),
        os.path.join(os.path.expanduser("~"), "phonics-tracker", "data", "curriculum.json"),
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return None

def get_curriculum():
    path = _find_curriculum_file()
    if path:
        data = load_json(path)
        if data and data.get("tasks"):
            return data
    # 如果文件找不到或空，使用内嵌数据
    if EMBEDDED_CURRICULUM and EMBEDDED_CURRICULUM.get("tasks"):
        # 自动写入到数据目录，以便后续编辑
        os.makedirs(DATA_DIR, exist_ok=True)
        save_json(CURRICULUM_FILE, EMBEDDED_CURRICULUM)
        return EMBEDDED_CURRICULUM
    # 最后的fallback
    default = {"course_name": "Reading Garden Phonics", "total_tasks": 87, "tasks": []}
    return load_json(CURRICULUM_FILE, default)

def get_progress():
    data = load_json(PROGRESS_FILE, {"checkins": [], "weak_point_stats": {}})
    settings = get_settings()
    current_task = settings.get("current_task", 10)
    
    # 启动时自动检测：如果没有数据或版本不对，自动初始化
    if not data.get("checkins") or data.get("version") != 2:
        data = generate_progress_for_task(current_task)
        save_progress(data)
    
    return data

def generate_progress_for_task(current_task, base_date=None):
    """
    生成指定进度的完整学习历史
    current_task: 已学完成到第几课（也就是昨天学的最后一课）
    base_date: 首学第一天的日期，默认是昨天向前推 current_task-1 天
    """
    import random
    random.seed(42)
    
    if base_date is None:
        # 默认基准：首学第一课在 current_task 天前
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        base_date = today - timedelta(days=current_task - 1)
    else:
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    REVIEW_INTERVALS = [1, 2, 4, 7, 15, 30]
    
    curriculum = get_curriculum()
    tasks = curriculum.get("tasks", [])
    
    checkins = []
    weak_point_stats = {}
    
    for task_idx in range(current_task):
        task_id = task_idx + 1
        first_date = base_date + timedelta(days=task_idx)
        
        if task_idx < len(tasks):
            phonics_list = tasks[task_idx].get('phonics_focus', [])
        else:
            phonics_list = []
        
        mastery = random.randint(2, 5)
        weak = [p for p in phonics_list if random.random() < 0.35]
        
        # 首学
        checkins.append({
            "task_id": task_id,
            "date": first_date.strftime("%Y-%m-%d"),
            "weak_points": weak,
            "mastery": mastery,
            "is_first": True,
            "timestamp": first_date.strftime("%Y-%m-%d") + "T10:00:00"
        })
        
        # 更新薄弱点统计
        for p in phonics_list:
            if p not in weak_point_stats:
                weak_point_stats[p] = {
                    "total_encounters": 0,
                    "weak_count": 0,
                    "last_date": first_date.strftime("%Y-%m-%d"),
                    "is_weak": False,
                    "weak_review_count": 0,
                    "last_weak_review_date": None
                }
            weak_point_stats[p]["total_encounters"] += 1
            if p in weak:
                weak_point_stats[p]["weak_count"] += 1
                weak_point_stats[p]["is_weak"] = True
                weak_point_stats[p]["weak_review_count"] = 0
                weak_point_stats[p]["last_weak_review_date"] = first_date.strftime("%Y-%m-%d")
        
        # 复习
        for interval in REVIEW_INTERVALS:
            review_date = first_date + timedelta(days=interval)
            if review_date <= today:
                review_mastery = min(5, mastery + 1)
                review_weak = [p for p in phonics_list if weak_point_stats[p]["is_weak"]]
                
                checkins.append({
                    "task_id": task_id,
                    "date": review_date.strftime("%Y-%m-%d"),
                    "weak_points": review_weak,
                    "mastery": review_mastery,
                    "is_first": False,
                    "timestamp": review_date.strftime("%Y-%m-%d") + "T15:00:00"
                })
                
                for p in phonics_list:
                    weak_point_stats[p]["last_date"] = review_date.strftime("%Y-%m-%d")
    
    return {
        "version": 2,
        "checkins": checkins,
        "weak_point_stats": weak_point_stats
    }

def get_settings():
    return load_json(SETTINGS_FILE, {
        "review_intervals": DEFAULT_REVIEW_INTERVALS,
        "weak_point_intervals": WEAK_POINT_INTERVALS,
        "child_name": "宝贝",
        "current_task": 10
    })

def save_progress(data):
    save_json(PROGRESS_FILE, data)

def save_settings(data):
    save_json(SETTINGS_FILE, data)

# ============== 业务逻辑 ==============
def parse_date(date_str):
    """解析日期字符串"""
    return datetime.strptime(date_str, "%Y-%m-%d")

def format_date(dt):
    """格式化日期"""
    return dt.strftime("%Y-%m-%d")

def get_today():
    return format_date(datetime.now())

def get_task_by_id(tasks, task_id):
    for t in tasks:
        if t["id"] == task_id:
            return t
    return None

def get_task_reviews(task_id, progress):
    """获取某个任务的所有复习记录"""
    return [c for c in progress["checkins"] if c["task_id"] == task_id]

def get_next_new_task(tasks, progress):
    """获取下一个未学习的新任务"""
    studied_ids = set(c["task_id"] for c in progress["checkins"] if c.get("is_first", False))
    for t in tasks:
        if t["id"] not in studied_ids:
            return t
    return None

def get_today_tasks(tasks, progress, settings):
    """获取今日任务列表（新学 + 复习）"""
    today = datetime.now()
    today_str = format_date(today)
    checkins = progress["checkins"]
    intervals = settings.get("review_intervals", DEFAULT_REVIEW_INTERVALS)
    weak_intervals = settings.get("weak_point_intervals", WEAK_POINT_INTERVALS)
    
    today_task_ids = set()
    today_tasks = []
    
    # 1. 新任务
    new_task = get_next_new_task(tasks, progress)
    if new_task:
        today_task_ids.add(new_task["id"])
        today_tasks.append({
            "task": new_task,
            "type": "新学",
            "reason": "今日新课"
        })
    
    # 2. 按艾宾浩斯曲线安排的复习
    first_checkins = [c for c in checkins if c.get("is_first", False)]
    for fc in first_checkins:
        task_id = fc["task_id"]
        first_date = parse_date(fc["date"])
        reviews = get_task_reviews(task_id, progress)
        review_count = len([r for r in reviews if not r.get("is_first", False)])
        
        if review_count < len(intervals):
            next_review_day = first_date + timedelta(days=intervals[review_count])
            next_review_str = format_date(next_review_day)
            
            if next_review_str == today_str and task_id not in today_task_ids:
                task = get_task_by_id(tasks, task_id)
                if task:
                    today_task_ids.add(task_id)
                    today_tasks.append({
                        "task": task,
                        "type": "复习",
                        "reason": f"第{review_count + 1}次复习（间隔{intervals[review_count]}天）"
                    })
    
    # 3. 薄弱点加强复习
    weak_stats = progress.get("weak_point_stats", {})
    for phonics, stats in weak_stats.items():
        if stats.get("is_weak", False):
            weak_review_date = stats.get("last_weak_review_date")
            if weak_review_date:
                last_date = parse_date(weak_review_date)
                weak_count = stats.get("weak_review_count", 0)
                if weak_count < len(weak_intervals):
                    next_weak_day = last_date + timedelta(days=weak_intervals[weak_count])
                    if format_date(next_weak_day) == today_str:
                        # 找包含这个薄弱音的任务
                        for t in tasks:
                            if phonics in t.get("phonics_focus", []) and t["id"] not in today_task_ids:
                                today_task_ids.add(t["id"])
                                today_tasks.append({
                                    "task": t,
                                    "type": "薄弱点复习",
                                    "reason": f"薄弱音 '{phonics}' 加强练习"
                                })
                                break
    
    return today_tasks

def record_checkin(task_id, weak_points, mastery, is_first=False):
    """记录打卡"""
    progress = get_progress()
    today = get_today()
    
    checkin = {
        "task_id": task_id,
        "date": today,
        "weak_points": weak_points,
        "mastery": mastery,
        "is_first": is_first,
        "timestamp": datetime.now().isoformat()
    }
    progress["checkins"].append(checkin)
    
    # 更新薄弱点统计
    if "weak_point_stats" not in progress:
        progress["weak_point_stats"] = {}
    
    for wp in weak_points:
        if wp not in progress["weak_point_stats"]:
            progress["weak_point_stats"][wp] = {
                "total_encounters": 0,
                "weak_count": 0,
                "last_date": today,
                "is_weak": True,
                "weak_review_count": 0,
                "last_weak_review_date": today
            }
        progress["weak_point_stats"][wp]["total_encounters"] += 1
        progress["weak_point_stats"][wp]["weak_count"] += 1
        progress["weak_point_stats"][wp]["last_date"] = today
        progress["weak_point_stats"][wp]["is_weak"] = True
        progress["weak_point_stats"][wp]["last_weak_review_date"] = today
    
    # 更新非薄弱音（掌握好的）
    task = get_task_by_id(get_curriculum()["tasks"], task_id)
    if task:
        for pf in task.get("phonics_focus", []):
            if pf not in weak_points:
                if pf not in progress["weak_point_stats"]:
                    progress["weak_point_stats"][pf] = {
                        "total_encounters": 1,
                        "weak_count": 0,
                        "last_date": today,
                        "is_weak": False
                    }
                else:
                    progress["weak_point_stats"][pf]["total_encounters"] += 1
                    progress["weak_point_stats"][pf]["last_date"] = today
                    # 如果连续3次都不薄弱，则移除薄弱标记
                    if progress["weak_point_stats"][pf]["weak_count"] == 0:
                        progress["weak_point_stats"][pf]["is_weak"] = False
    
    save_progress(progress)
    return True

def mark_weak_point_reviewed(phonics):
    """标记薄弱点已复习"""
    progress = get_progress()
    if phonics in progress.get("weak_point_stats", {}):
        progress["weak_point_stats"][phonics]["weak_review_count"] = \
            progress["weak_point_stats"][phonics].get("weak_review_count", 0) + 1
        progress["weak_point_stats"][phonics]["last_weak_review_date"] = get_today()
        save_progress(progress)

def get_weak_points(progress):
    """获取所有当前薄弱点"""
    weak = []
    for phonics, stats in progress.get("weak_point_stats", {}).items():
        if stats.get("is_weak", False):
            weak.append({
                "phonics": phonics,
                "weak_count": stats.get("weak_count", 0),
                "total": stats.get("total_encounters", 0),
                "last_date": stats.get("last_date", "")
            })
    return sorted(weak, key=lambda x: x["weak_count"], reverse=True)

def get_progress_stats(tasks, progress):
    """获取整体进度统计"""
    total = len(tasks)
    first_studied = set(c["task_id"] for c in progress["checkins"] if c.get("is_first", False))
    completed = len(first_studied)
    
    level_stats = defaultdict(lambda: {"total": 0, "completed": 0})
    for t in tasks:
        level_stats[t["level"]]["total"] += 1
        if t["id"] in first_studied:
            level_stats[t["level"]]["completed"] += 1
    
    return {
        "total": total,
        "completed": completed,
        "percentage": round(completed / total * 100, 1) if total > 0 else 0,
        "level_stats": dict(level_stats)
    }

def generate_practice_for_weak_point(phonics, tasks):
    """为薄弱音生成练习建议"""
    related_tasks = [t for t in tasks if phonics in t.get("phonics_focus", [])]
    words = []
    
    # 根据音素生成简单练习单词
    practice_words = {
        "a": ["cat", "hat", "mat", "sat", "dad", "bag", "fan", "man", "pan", "ran"],
        "e": ["bed", "red", "hen", "pen", "ten", "leg", "net", "pet", "wet", "vet"],
        "i": ["pig", "big", "dig", "fig", "hip", "lip", "tip", "sit", "hit", "bit"],
        "o": ["dog", "log", "hog", "fog", "box", "fox", "dot", "hot", "pot", "mop"],
        "u": ["bug", "hug", "mug", "rug", "tub", "cub", "cut", "hut", "nut", "pup"],
        "b": ["bat", "bed", "big", "box", "bug", "bus", "but", "bad", "bag", "bit"],
        "c": ["cat", "cut", "cot", "can", "cap", "cup", "cod", "cub", "car", "cop"],
        "d": ["dad", "dog", "dig", "dot", "den", "did", "dam", "dim", "dip", "ducks"],
        "f": ["fat", "fun", "fan", "fit", "fix", "fox", "fog", "fed", "fig", "fin"],
        "g": ["got", "get", "gun", "gum", "gap", "gas", "gut", "gig", "god", "gab"],
        "h": ["hat", "hen", "hit", "hot", "hug", "hop", "had", "hid", "hod", "hub"],
        "j": ["jet", "job", "jog", "jug", "jam", "jig", "jut", "jab", "jib", "jot"],
        "k": ["kit", "kid", "kin", "kip", "keg", "ken", "key", "kite", "king", "kick"],
        "l": ["log", "lip", "leg", "let", "lid", "lit", "lot", "lug", "lap", "lab"],
        "m": ["mat", "man", "map", "men", "mop", "mud", "mug", "mum", "mix", "mad"],
        "n": ["net", "not", "nut", "nap", "nip", "nod", "nun", "nab", "nib", "nil"],
        "p": ["pen", "pig", "pin", "pot", "pan", "pet", "pit", "pop", "pup", "pat"],
        "r": ["run", "rat", "red", "rip", "rob", "rod", "rug", "rag", "ram", "rap"],
        "s": ["sat", "sit", "sun", "sad", "sip", "set", "sob", "sub", "sum", "sap"],
        "t": ["top", "tap", "tip", "ten", "toe", "tub", "tag", "tan", "tin", "ton"],
        "v": ["vet", "van", "vat", "vim", "vex", "via", "vow", "vie", "veg", "vox"],
        "w": ["wet", "win", "wag", "wig", "won", "wok", "wan", "wad", "web", "wed"],
        "x": ["box", "fox", "fix", "mix", "six", "axe", "tax", "wax", "max", "vex"],
        "y": ["yes", "yet", "yak", "yam", "yap", "yell", "yell", "yip", "yum", "yon"],
        "z": ["zip", "zap", "zig", "zag", "zen", "zoo", "zit", "zap", "zig", "zag"],
        "ch": ["chip", "chat", "chin", "chop", "chess", "much", "rich", "such", "inch", "bench"],
        "sh": ["ship", "shop", "shut", "fish", "dish", "wish", "wash", "cash", "bash", "rush"],
        "th": ["this", "that", "them", "thin", "thick", "bath", "math", "path", "with", "both"],
        "wh": ["what", "when", "why", "which", "whale", "whip", "whiz", "wham", "whop", "whoa"],
        "ng": ["sing", "ring", "king", "wing", "long", "song", "bang", "rang", "sung", "rung"],
        "ck": ["back", "sack", "tick", "sick", "duck", "luck", "rock", "sock", "neck", "deck"],
        "ff": ["off", "puff", "huff", "muff", "cuff", "buff", "guff", "luff", "tiff", "cliff"],
        "ll": ["all", "ball", "call", "fall", "hall", "mall", "tall", "wall", "well", "fill"],
        "ss": ["miss", "kiss", "boss", "loss", "pass", "mass", "toss", "cross", "glass", "grass"],
        "zz": ["buzz", "fizz", "jazz", "razz", "dazz", "fizz", "jazz", "fuzz", "muzz", "pizz"],
        "pl": ["plan", "plug", "plot", "plus", "play", "plum", "pledge", "plop", "plod", "plow"],
        "sl": ["slip", "slot", "slam", "slap", "slow", "sled", "slip", "slop", "slug", "slum"],
        "dr": ["drop", "drum", "drag", "drip", "draw", "dress", "drill", "drink", "drive", "drop"],
        "tr": ["trip", "tram", "trap", "tree", "truck", "train", "trail", "trick", "trust", "track"],
        "fr": ["frog", "from", "free", "fresh", "fruit", "front", "frost", "frame", "frill", "frock"],
        "st": ["stop", "star", "stay", "step", "stick", "stone", "store", "study", "stand", "still"],
        "nd": ["and", "hand", "land", "sand", "band", "send", "find", "kind", "mind", "wind"],
        "nt": ["ant", "want", "sent", "went", "dent", "tent", "hint", "mint", "pint", "lint"],
        "mp": ["jump", "lamp", "camp", "damp", "ramp", "bump", "dump", "pump", "limp", "hemp"],
        "nk": ["sink", "link", "pink", "wink", "bank", "tank", "rank", "sank", "honk", "bonk"],
        "ai": ["rain", "train", "pain", "main", "gain", "wait", "bait", "mail", "fail", "tail"],
        "ay": ["day", "say", "way", "play", "stay", "clay", "gray", "pray", "tray", "sway"],
        "ee": ["see", "tree", "bee", "free", "meet", "feet", "seed", "need", "feed", "deep"],
        "ea": ["eat", "sea", "tea", "read", "lead", "meat", "seat", "beat", "heat", "neat"],
        "oa": ["boat", "coat", "goat", "road", "soap", "toast", "roast", "coach", "loaf", "float"],
        "ow": ["show", "snow", "bow", "low", "own", "grow", "blow", "flow", "crow", "glow"],
        "igh": ["night", "light", "right", "sight", "fight", "tight", "might", "bright", "flight", "high"],
        "oa_e": ["bone", "cone", "tone", "phone", "stone", "robe", "robe", "globe", "probe", "lobe"],
        "o_e": ["home", "nose", "rope", "hope", "joke", "poke", "woke", "hose", "rose", "note"],
        "i_e": ["kite", "nine", "fine", "mine", "line", "dive", "hive", "live", "bite", "site"],
        "a_e": ["cake", "make", "take", "lake", "name", "game", "same", "late", "gate", "fame"],
        "u_e": ["cute", "mute", "huge", "rule", "tune", "tube", "cube", "duke", "flute", "prune"],
        "ar": ["car", "star", "far", "bar", "jar", "farm", "harm", "dart", "cart", "dark"],
        "er": ["her", "term", "herd", "verb", "nerd", "perch", "fern", "stern", "chert", "sherd"],
        "ir": ["bird", "dirt", "girl", "shirt", "skirt", "stir", "fir", "sir", "third", "first"],
        "or": ["fork", "corn", "horn", "sort", "port", "sport", "storm", "thorn", "short", "north"],
        "ur": ["turn", "burn", "hurt", "nurse", "purse", "curve", "surf", "turkey", "burst", "curl"],
        "oi": ["oil", "soil", "boil", "coil", "foil", "toil", "spoil", "moist", "point", "joint"],
        "oy": ["boy", "toy", "joy", "soy", "coy", "ploy", "alloy", "annoy", "enjoy", "deploy"],
        "ow_ou": ["cow", "how", "now", "down", "town", "found", "sound", "round", "pound", "count"],
        "ou": ["out", "about", "shout", "cloud", "loud", "proud", "mouth", "south", "house", "mouse"],
        "aw": ["paw", "law", "jaw", "raw", "saw", "draw", "straw", "claw", "crawl", "hawk"],
        "au": ["auto", "audio", "August", "haul", "fault", "sauce", "pause", "cause", "launch", "author"],
        "oo": ["book", "look", "cook", "hook", "took", "foot", "good", "wood", "stood", "hood"],
        "oo_long": ["moon", "soon", "food", "pool", "tool", "school", "cool", "fool", "room", "zoom"],
    }
    
    words = practice_words.get(phonics, [f"practice with '{phonics}' sound"])
    return {
        "phonics": phonics,
        "related_stories": [t["title"] for t in related_tasks[:3]],
        "practice_words": words[:10],
        "sentences": [
            f"Can you read these {phonics} words?",
            f"Find the '{phonics}' sound in each word.",
            f"Say the '{phonics}' sound clearly.",
        ]
    }

# ============== Streamlit 界面 ==============
st.set_page_config(
    page_title="📖 丽声自然拼读打卡",
    page_icon="📖",
    layout="wide",
)

# 自定义样式
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #FF6B6B;
        text-align: center;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #4ECDC4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .task-card {
        background-color: #f0f2f6;
        border-radius: 10px;
        padding: 20px;
        margin: 10px 0;
        border-left: 5px solid #FF6B6B;
    }
    .review-card {
        background-color: #e8f4f8;
        border-radius: 10px;
        padding: 20px;
        margin: 10px 0;
        border-left: 5px solid #4ECDC4;
    }
    .weak-card {
        background-color: #fff3e0;
        border-radius: 10px;
        padding: 20px;
        margin: 10px 0;
        border-left: 5px solid #FF9800;
    }
    .stat-card {
        background-color: #f8f9fa;
        border-radius: 10px;
        padding: 15px;
        text-align: center;
        border: 2px solid #dee2e6;
    }
    .stat-number {
        font-size: 2rem;
        font-weight: bold;
        color: #FF6B6B;
    }
    .stat-label {
        font-size: 0.9rem;
        color: #6c757d;
    }
</style>
""", unsafe_allow_html=True)

# 加载数据
curriculum = get_curriculum()
tasks = curriculum.get("tasks", [])
progress = get_progress()
settings = get_settings()

# 页面导航 - 支持通过session_state跳转
nav_options = ["今日任务", "打卡记录", "薄弱点追踪", "学习进度", "设置"]

# 检查是否有跳转请求
if "navigate_to" in st.session_state:
    nav_idx = nav_options.index(st.session_state.navigate_to)
    del st.session_state.navigate_to
else:
    nav_idx = 0

page = st.sidebar.radio("📋 导航", nav_options, index=nav_idx)

child_name = settings.get("child_name", "宝贝")

# ==================== 今日任务 ====================
if page == "今日任务":
    st.markdown(f'<div class="main-header">📖 {child_name}的自然拼读打卡</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="sub-header">今日日期：{get_today()}</div>', unsafe_allow_html=True)
    
    today_tasks = get_today_tasks(tasks, progress, settings)
    
    if not today_tasks:
        st.success("🎉 太棒了！今天没有任务，可以休息一下或去复习薄弱点！")
    else:
        # 统计
        new_count = sum(1 for t in today_tasks if t["type"] == "新学")
        review_count = sum(1 for t in today_tasks if t["type"] == "复习")
        weak_count = sum(1 for t in today_tasks if t["type"] == "薄弱点复习")
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.markdown(f'<div class="stat-card"><div class="stat-number">{len(today_tasks)}</div><div class="stat-label">今日总任务</div></div>', unsafe_allow_html=True)
        with col2:
            st.markdown(f'<div class="stat-card"><div class="stat-number">{new_count}</div><div class="stat-label">新学</div></div>', unsafe_allow_html=True)
        with col3:
            st.markdown(f'<div class="stat-card"><div class="stat-number">{review_count}</div><div class="stat-label">复习</div></div>', unsafe_allow_html=True)
        with col4:
            st.markdown(f'<div class="stat-card"><div class="stat-number">{weak_count}</div><div class="stat-label">薄弱点复习</div></div>', unsafe_allow_html=True)
        
        st.divider()
        
        for tt in today_tasks:
            task = tt["task"]
            task_type = tt["type"]
            reason = tt["reason"]
            
            if task_type == "新学":
                card_class = "task-card"
                emoji = "📚"
            elif task_type == "复习":
                card_class = "review-card"
                emoji = "🔄"
            else:
                card_class = "weak-card"
                emoji = "💪"
            
            with st.container():
                st.markdown(f'<div class="{card_class}">', unsafe_allow_html=True)
                col1, col2 = st.columns([3, 1])
                with col1:
                    st.markdown(f"### {emoji} Task.{task['id']} {task['title']}")
                    st.markdown(f"**类型：**{task_type} | **原因：**{reason}")
                    st.markdown(f"**拼读重点：**{', '.join(task['phonics_focus'])}")
                with col2:
                    if st.button(f"去打卡", key=f"goto_checkin_{task['id']}"):
                        st.session_state.checkin_task_id = task["id"]
                        st.session_state.navigate_to = "打卡记录"
                        st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)
            
            st.markdown("")

# ==================== 打卡记录 ====================
elif page == "打卡记录":
    st.markdown(f'<div class="main-header">✅ 打卡记录</div>', unsafe_allow_html=True)
    
    # 如果从今日任务跳转过来
    default_task_id = st.session_state.get("checkin_task_id", 1)
    
    task_options = {f"Task.{t['id']} {t['title']}": t["id"] for t in tasks}
    selected_label = st.selectbox("选择要打卡的故事", list(task_options.keys()), 
                                  index=list(task_options.values()).index(default_task_id) if default_task_id in task_options.values() else 0)
    selected_task_id = task_options[selected_label]
    selected_task = get_task_by_id(tasks, selected_task_id)
    
    if selected_task:
        st.markdown(f"### 📖 {selected_task['title']}")
        st.markdown(f"**拼读重点：**{', '.join(selected_task['phonics_focus'])}")
        
        # 检查是否是首次学习
        task_checkins = get_task_reviews(selected_task_id, progress)
        is_first = len([c for c in task_checkins if c.get("is_first", False)]) == 0
        
        if is_first:
            st.info("🌟 这是你第一次学习这个故事！")
        else:
            review_times = len([c for c in task_checkins if not c.get("is_first", False)])
            st.info(f"🔄 这是你第{review_times + 1}次复习这个故事。")
        
        st.divider()
        
        # 掌握程度
        mastery = st.slider("今天的掌握程度", 1, 5, 3, 
                           help="1=完全不会，2=较困难，3=一般，4=比较熟练，5=非常流利")
        
        mastery_labels = {1: "😢 完全不会", 2: "😕 较困难", 3: "😐 一般", 4: "😊 比较熟练", 5: "🤩 非常流利"}
        st.markdown(f"**评价：**{mastery_labels[mastery]}")
        
        st.divider()
        
        # 薄弱点选择
        st.markdown("### 💉 薄弱点标记")
        st.markdown("选择今天读得不熟练、容易出错的音：")
        
        weak_points = []
        for phonics in selected_task["phonics_focus"]:
            if st.checkbox(f"音素 `{phonics}` 不熟练", key=f"weak_{phonics}"):
                weak_points.append(phonics)
        
        if weak_points:
            st.warning(f"已标记薄弱点：{', '.join(weak_points)}")
        
        st.divider()
        
        # 打卡按钮
        if st.button("✅ 确认打卡", type="primary", use_container_width=True):
            record_checkin(selected_task_id, weak_points, mastery, is_first)
            st.success(f"🎉 打卡成功！{child_name}今天表现很棒！")
            
            if weak_points:
                st.info(f"📝 已记录薄弱点：{', '.join(weak_points)}，系统会自动安排针对性复习。")
            
            if is_first:
                st.balloons()

# ==================== 薄弱点追踪 ====================
elif page == "薄弱点追踪":
    st.markdown(f'<div class="main-header">💪 薄弱点追踪</div>', unsafe_allow_html=True)
    
    # 手动添加薄弱点入口
    st.markdown("### ➕ 添加新薄弱点")
    with st.form(key="add_weak_point_form"):
        new_phonics = st.text_input("输入薄弱音素（如：a, e, sh, th, o_e 等）", placeholder="例如：sh")
        add_note = st.text_input("备注（可选）", placeholder="例如：发音不标准、容易混淆")
        submitted = st.form_submit_button("确认添加", use_container_width=True)
        if submitted and new_phonics:
            new_phonics = new_phonics.strip().lower()
            progress_data = get_progress()
            if "weak_point_stats" not in progress_data:
                progress_data["weak_point_stats"] = {}
            
            today = get_today()
            if new_phonics not in progress_data["weak_point_stats"]:
                progress_data["weak_point_stats"][new_phonics] = {
                    "total_encounters": 0,
                    "weak_count": 0,
                    "last_date": today,
                    "is_weak": True,
                    "weak_review_count": 0,
                    "last_weak_review_date": today,
                    "note": add_note
                }
            
            progress_data["weak_point_stats"][new_phonics]["weak_count"] += 1
            progress_data["weak_point_stats"][new_phonics]["is_weak"] = True
            progress_data["weak_point_stats"][new_phonics]["last_weak_review_date"] = today
            if add_note:
                progress_data["weak_point_stats"][new_phonics]["note"] = add_note
            
            save_progress(progress_data)
            st.success(f"已添加薄弱音素 `{new_phonics}`！系统已为您生成练习规划。")
            st.rerun()
    
    st.divider()
    
    weak_points = get_weak_points(progress)
    
    if not weak_points:
        st.success("🎉 太棒了！目前没有薄弱点，所有音素都掌握得很好！")
    else:
        st.markdown(f"### 当前共有 **{len(weak_points)}** 个薄弱音")
        
        for wp in weak_points:
            phonics = wp["phonics"]
            
            with st.container():
                st.markdown(f'<div class="weak-card">', unsafe_allow_html=True)
                col1, col2, col3 = st.columns([2, 2, 1])
                with col1:
                    st.markdown(f"### 🔴 音素 `{phonics}`")
                    st.markdown(f"**弱点次数：**{wp['weak_count']} 次")
                    st.markdown(f"**总遇见：**{wp['total']} 次")
                with col2:
                    st.markdown(f"**最近出现：**{wp['last_date']}")
                    # 生成练习建议
                    practice = generate_practice_for_weak_point(phonics, tasks)
                    st.markdown(f"**练习单词：**{', '.join(practice['practice_words'][:5])}")
                with col3:
                    if st.button(f"已复习", key=f"reviewed_{phonics}"):
                        mark_weak_point_reviewed(phonics)
                        st.success(f"已记录 `{phonics}` 复习！")
                        st.rerun()
                
                # 展开详练练习
                with st.expander("📖 查看详练练习"):
                    practice = generate_practice_for_weak_point(phonics, tasks)
                    st.markdown(f"**相关故事：**{', '.join(practice['related_stories'])}")
                    st.markdown("练习单词：")
                    for word in practice["practice_words"]:
                        st.markdown(f"- {word}")
                    st.markdown("练习句子：")
                    for sent in practice["sentences"]:
                        st.markdown(f"> {sent}")
                
                st.markdown('</div>', unsafe_allow_html=True)
            
            st.markdown("")

# ==================== 学习进度 ====================
elif page == "学习进度":
    st.markdown(f'<div class="main-header">📊 学习进度</div>', unsafe_allow_html=True)
    
    stats = get_progress_stats(tasks, progress)
    
    # 总体进度
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f'<div class="stat-card"><div class="stat-number">{stats["total"]}</div><div class="stat-label">总关数</div></div>', unsafe_allow_html=True)
    with col2:
        st.markdown(f'<div class="stat-card"><div class="stat-number">{stats["completed"]}</div><div class="stat-label">已完成</div></div>', unsafe_allow_html=True)
    with col3:
        st.markdown(f'<div class="stat-card"><div class="stat-number">{stats["total"] - stats["completed"]}</div><div class="stat-label">待学习</div></div>', unsafe_allow_html=True)
    with col4:
        st.markdown(f'<div class="stat-card"><div class="stat-number">{stats["percentage"]}%</div><div class="stat-label">完成度</div></div>', unsafe_allow_html=True)
    
    st.divider()
    
    # 圆环进度图
    fig = go.Figure(go.Pie(
        labels=["已完成", "待学习"],
        values=[stats["completed"], stats["total"] - stats["completed"]],
        hole=0.4,
        marker_colors=["#FF6B6B", "#E8E8E8"],
        textinfo="percent+label"
    ))
    fig.update_layout(
        title=f"🎯 {child_name}的整体学习进度",
        showlegend=False,
        height=400
    )
    st.plotly_chart(fig, use_container_width=True)
    
    st.divider()
    
    # 各级别进度
    st.markdown("### 📈 各级别进度")
    level_data = []
    for level, level_stat in sorted(stats["level_stats"].items()):
        level_data.append({
            "级别": f"Level {level}",
            "总数": level_stat["total"],
            "已完成": level_stat["completed"],
            "完成度": round(level_stat["completed"] / level_stat["total"] * 100, 1)
        })
    
    df_levels = pd.DataFrame(level_data)
    st.dataframe(df_levels, use_container_width=True, hide_index=True)
    
    # 柱状图
    fig2 = px.bar(df_levels, x="级别", y=["已完成", "总数"], 
                  barmode="group", 
                  title="各级别完成情况",
                  color_discrete_map={"已完成": "#FF6B6B", "总数": "#4ECDC4"})
    st.plotly_chart(fig2, use_container_width=True)
    
    st.divider()
    
    # 打卡历史
    st.markdown("### 📖 打卡历史")
    checkins = progress.get("checkins", [])
    if checkins:
        history_data = []
        for c in checkins[-20:]:  # 最近20条
            task = get_task_by_id(tasks, c["task_id"])
            history_data.append({
                "日期": c["date"],
                "故事": task["title"] if task else f"Task.{c['task_id']}",
                "类型": "首学" if c.get("is_first") else "复习",
                "掌握度": c["mastery"],
                "薄弱点": ", ".join(c.get("weak_points", [])) or "无"
            })
        df_history = pd.DataFrame(history_data)
        st.dataframe(df_history, use_container_width=True, hide_index=True)
    else:
        st.info("暂无打卡记录，快去打卡吧！")

# ==================== 设置 ====================
elif page == "设置":
    st.markdown(f'<div class="main-header">⚙️ 设置</div>', unsafe_allow_html=True)
    
    st.markdown("### 👤 孩子信息")
    new_name = st.text_input("孩子昵称", value=child_name)
    
    st.markdown("### 📖 当前学习进度")
    total_tasks = len(get_curriculum().get("tasks", []))
    current_task_setting = settings.get("current_task", 10)
    new_current_task = st.slider(
        f"已学完到第几课（今天将学习第 {current_task_setting + 1} 课）",
        min_value=1,
        max_value=total_tasks,
        value=current_task_setting
    )
    st.caption(f"如果孩子今天刚好学完第 {new_current_task} 课，明天程序将推荐第 {new_current_task + 1} 课作为新内容。")
    
    st.markdown("### 🔄 复习间隔设置（天）")
    st.markdown("艾宾浩斯遗忘曲线推荐间隔：1, 2, 4, 7, 15, 30 天")
    
    current_intervals = settings.get("review_intervals", DEFAULT_REVIEW_INTERVALS)
    interval_str = st.text_input("复习间隔（用英文逗号分隔）", value=", ".join(map(str, current_intervals)))
    
    st.markdown("### 💪 薄弱点加强间隔（天）")
    current_weak_intervals = settings.get("weak_point_intervals", WEAK_POINT_INTERVALS)
    weak_interval_str = st.text_input("薄弱点复习间隔（用英文逗号分隔）", value=", ".join(map(str, current_weak_intervals)))
    
    st.markdown("### ⚠️ 危险区域")
    if st.button("🗑️ 清空所有打卡记录", type="secondary"):
        if st.checkbox("确认清空所有数据？此操作不可撤销！"):
            save_progress({"checkins": [], "weak_point_stats": {}})
            st.success("已清空所有打卡记录！")
            st.rerun()
    
    if st.button("💾 保存设置", type="primary", use_container_width=True):
        try:
            new_intervals = [int(x.strip()) for x in interval_str.split(",")]
            new_weak_intervals = [int(x.strip()) for x in weak_interval_str.split(",")]
            
            settings["child_name"] = new_name
            settings["current_task"] = new_current_task
            settings["review_intervals"] = new_intervals
            settings["weak_point_intervals"] = new_weak_intervals
            save_settings(settings)
            st.success("设置已保存！")
        except ValueError:
            st.error("请输入有效的数字，用英文逗号分隔！")
    
    st.markdown("---")
    st.markdown("### 📤 数据备份与恢复")
    st.caption("提示：部署在云端时服务器数据可能会重置，建议定期导出备份。")
    
    col1, col2 = st.columns(2)
    with col1:
        # 导出数据
        progress_data = load_json(PROGRESS_FILE, {"checkins": [], "weak_point_stats": {}})
        settings_data = get_settings()
        export_data = {
            "progress": progress_data,
            "settings": settings_data,
            "exported_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        export_json = json.dumps(export_data, ensure_ascii=False, indent=2)
        st.download_button(
            label="📥 下载数据备份",
            data=export_json,
            file_name=f"phonics_backup_{datetime.now().strftime('%Y%m%d')}.json",
            mime="application/json",
            use_container_width=True
        )
    with col2:
        # 导入数据
        uploaded_file = st.file_uploader("上传备份文件", type=["json"], label_visibility="collapsed")
        if uploaded_file is not None:
            try:
                imported = json.load(uploaded_file)
                if "progress" in imported and "settings" in imported:
                    save_progress(imported["progress"])
                    save_settings(imported["settings"])
                    st.success("数据已恢复！页面即将刷新...")
                    st.rerun()
                else:
                    st.error("备份文件格式不正确！")
            except Exception as e:
                st.error(f"导入失败：{str(e)}")
