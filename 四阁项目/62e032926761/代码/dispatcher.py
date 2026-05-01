#!/usr/bin/env python3
"""
四阁调度脚本 — 核心运行时
替代Hermes的全貌核心：接收输入 → 检索加载 → 拼装Prompt → 调API → 沙漏分流 → Session管理
"""

import os
import re
import sys
import json
import uuid
import hashlib
import time
import jieba
from datetime import datetime
from pathlib import Path
from openai import OpenAI
from tavily import TavilyClient

BASE_DIR = Path(__file__).parent
KNOWLEDGE_DIR = BASE_DIR / "知识阁"
EXPERIENCE_DIR = BASE_DIR / "经验阁"
MEMORY_DIR = BASE_DIR / "记忆阁"
SKILL_DIR = BASE_DIR / "技能阁"
SESSION_DIR = BASE_DIR / "sessions"

PAVILION_DIRS = {
    "知识阁": KNOWLEDGE_DIR,
    "经验阁": EXPERIENCE_DIR,
    "记忆阁": MEMORY_DIR,
    "技能阁": SKILL_DIR,
}

API_BASE_URL = os.environ.get("SIGE_API_BASE", "https://api.deepseek.com")
API_KEY = os.environ.get("SIGE_API_KEY", "sk-10810f86c3e148c6b3f0182806456942")
MODEL = os.environ.get("SIGE_MODEL", "deepseek-v4-flash")
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY", "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")

SYSTEM_RULES = """你是一个严谨的AI助手。铁律如下：
1. 不许编造。不确定的事情必须明确说"我不确定"，然后去查。
2. 回答要基于事实。如果你知道，直接回答；如果不确定，说明并建议搜索。
3. 回答简洁有力，不要废话。
4. 当用户告诉你关于他/她自己的信息时，记住这些信息。
5. 当你从搜索或对话中学到新的事实性知识，明确标注出来。"""

# ============================================================
# 1. 关键词提取
# ============================================================

STOP_WORDS = set("的了吗呢吧啊哦呀是在有我你他她它们这那个和与或但如果所以因为虽然可以能够应该需要什么怎么为什么哪个哪些".split() +
                 list("，。？！、；：""''（）【】"))

def extract_keywords(text):
    words = jieba.cut(text)
    keywords = []
    for w in words:
        w = w.strip()
        if len(w) >= 2 and w not in STOP_WORDS:
            keywords.append(w)
    return keywords


# ============================================================
# 2. INDEX检索 — 触发词匹配
# ============================================================

def load_index(pavilion_dir):
    index_path = pavilion_dir / "INDEX.md"
    if not index_path.exists():
        return []
    entries = []
    for line in index_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or line.startswith("<!--"):
            continue
        parts = [p.strip() for p in line.split("|")]
        parts = [p for p in parts if p]
        if len(parts) >= 3:
            triggers = [t.strip() for t in parts[0].split(",")]
            filename = parts[1]
            summary = parts[2]
            entries.append({"triggers": triggers, "file": filename, "summary": summary})
    return entries


def match_triggers(keywords, pavilion_name, pavilion_dir):
    entries = load_index(pavilion_dir)
    matched = []
    for entry in entries:
        for trigger in entry["triggers"]:
            for kw in keywords:
                if trigger in kw or kw in trigger:
                    matched.append(entry)
                    break
            else:
                continue
            break
    return matched


def load_entry_content(pavilion_dir, filename):
    filepath = pavilion_dir / filename
    if filepath.exists():
        return filepath.read_text(encoding="utf-8")
    return ""


def retrieve_context(keywords):
    context_blocks = []
    for name, pdir in PAVILION_DIRS.items():
        if name == "记忆阁":
            continue
        matches = match_triggers(keywords, name, pdir)
        for m in matches:
            content = load_entry_content(pdir, m["file"])
            if content:
                context_blocks.append(f"[{name}] {m['summary']}\n{content}")
    return context_blocks


# ============================================================
# 3. 潜意识加载（记忆阁 core.md 始终注入）
# ============================================================

def subconscious_keywords(text):
    kws = extract_keywords(text)
    return set(kws)


def entries_overlap(kw_a, kw_b):
    if not kw_a or not kw_b:
        return 0.0
    overlap = kw_a & kw_b
    smaller = min(len(kw_a), len(kw_b))
    return len(overlap) / smaller if smaller > 0 else 0.0


OVERLAP_THRESHOLD = 0.3


def load_subconscious():
    core_path = MEMORY_DIR / "core.md"
    if not core_path.exists():
        return ""
    content = core_path.read_text(encoding="utf-8").strip()
    lines = [l for l in content.splitlines() if not l.startswith("#") and not l.startswith("<!--") and l.strip()]
    if not lines:
        return ""

    parsed = []
    for line in lines:
        parts = line.split("|", 1)
        if len(parts) == 2:
            timestamp = parts[0].strip()
            entry = parts[1].strip()
        else:
            entry = line.strip()
            timestamp = "0000-00-00 00:00"
        kws = subconscious_keywords(entry)
        parsed.append({"ts": timestamp, "entry": entry, "kws": kws})

    parsed.sort(key=lambda x: x["ts"], reverse=True)

    selected = []
    for item in parsed:
        superseded = False
        for kept in selected:
            if entries_overlap(item["kws"], kept["kws"]) >= OVERLAP_THRESHOLD:
                superseded = True
                break
        if not superseded:
            selected.append(item)

    selected.reverse()
    return "\n".join(s["entry"] for s in selected) if selected else ""


# ============================================================
# 4. Prompt拼装
# ============================================================

def assemble_prompt(user_input, keywords, history, search_result=None):
    subconscious = load_subconscious()
    context_blocks = retrieve_context(keywords)

    system_parts = [SYSTEM_RULES]
    if subconscious:
        system_parts.append(f"\n[用户信息]\n{subconscious}")

    system_prompt = "\n".join(system_parts)

    messages = [{"role": "system", "content": system_prompt}]

    if context_blocks:
        context_text = "\n\n---\n\n".join(context_blocks)
        messages.append({"role": "system", "content": f"[相关知识/经验]\n{context_text}"})

    if search_result:
        messages.append({"role": "system", "content": f"[搜索结果]\n{search_result}"})

    for msg in history:
        messages.append(msg)

    messages.append({"role": "user", "content": user_input})

    return messages


# ============================================================
# 5. API调用 + 搜索
# ============================================================

UNCERTAINTY_PATTERNS = [
    r'我不确定',
    r'我(?:目前|暂时)?(?:无法|没有|不能)(?:确认|确定|查到|找到)',
    r'(?:建议|请).*(?:搜索|查询|查一下|查阅|咨询)',
    r'(?:超出|不在).*(?:知识|数据|训练)',
    r'截至.*(?:没有|不确定|无法)',
    r'我.*不(?:太)?清楚',
    r'需要.*(?:进一步|最新).*(?:查询|搜索|确认)',
    r'(?:抱歉|遗憾).*(?:没有|无法).*(?:信息|数据)',
]


def detect_uncertainty(text):
    for p in UNCERTAINTY_PATTERNS:
        if re.search(p, text):
            return True
    return False


def search_web(query, max_results=5):
    try:
        client = TavilyClient(api_key=TAVILY_API_KEY)
        result = client.search(query=query, max_results=max_results, search_depth="advanced")
        snippets = []
        for r in result.get("results", []):
            title = r.get("title", "")
            content = r.get("content", "")
            snippets.append(f"【{title}】{content}")
        return "\n\n".join(snippets[:max_results])
    except Exception as e:
        return f"[搜索失败: {e}]"


def call_api(messages):
    client = OpenAI(api_key=API_KEY, base_url=API_BASE_URL)
    try:
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            temperature=0.7,
            max_tokens=2048,
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"[API调用失败: {e}]"


def call_with_search_fallback(user_input, keywords, history):
    """两阶段调用：先问模型 → 如果不确定 → 搜索 → 带搜索结果再问"""
    t_start = time.time()

    messages = assemble_prompt(user_input, keywords, history)
    first_response = call_api(messages)
    t_first = time.time() - t_start

    search_used = False
    search_result = None
    final_response = first_response

    if detect_uncertainty(first_response):
        search_used = True
        search_query = user_input
        search_result = search_web(search_query)

        if search_result and not search_result.startswith("[搜索失败"):
            messages_with_search = assemble_prompt(
                user_input, keywords, history, search_result=search_result
            )
            final_response = call_api(messages_with_search)

    t_total = time.time() - t_start

    return {
        "response": final_response,
        "first_response": first_response,
        "search_used": search_used,
        "search_result": search_result,
        "time_first": round(t_first, 2),
        "time_total": round(t_total, 2),
    }


# ============================================================
# 6. 沙漏分流 — 规则匹配，不让模型判断
# ============================================================

KNOWLEDGE_PATTERNS = [
    r'\d{4}年',
    r'\d+\.?\d*[%％]',
    r'\d+\.?\d*(?:万|亿|元|美元|人民币|吨|千克|公斤|度|千瓦)',
    r'(?:根据|依据|按照).{0,10}(?:规定|法|条例|办法|通知|意见|政策)',
    r'(?:《[^》]+》)',
    r'(?:增值税|所得税|消费税|关税|印花税|房产税|契税|个税)',
    r'(?:起征点|税率|税额|免征|减免|征收)',
    r'(?:是指|定义为|即|指的是)',
    r'(?:国务院|财政部|税务总局|央行|银保监|证监会|发改委|工信部|住建部|商务部|市场监管|生态环境部|应急管理部)',
    r'(?:自\d{4}年\d{1,2}月)',
    r'(?:第[一二三四五六七八九十]+条)',
    r'(?:施行|生效|实施|执行)',
    r'(?:同比|环比|增长率|增速|GDP|CPI|PPI)',
    r'(?:合同法|公司法|劳动法|民法典|刑法|行政法|知识产权法|反垄断法|数据安全法|个人信息保护法|网络安全法)',
    r'(?:碳排放|碳交易|碳市场|碳配额|碳中和|碳达峰|排污许可|环评|环保)',
    r'(?:覆盖|纳入|扩容|门槛|标准|要求|条件)',
    r'(?:目前|现状|当前|截至|最新)',
]

EXPERIENCE_PATTERNS = [
    r'(?:发现|原来|实际上|事实上)',
    r'(?:试过|尝试过|验证过|测试过|实践过)',
    r'(?:有效|无效|可行|不可行|成功|失败)',
    r'(?:经验|教训|踩坑|踩过坑|注意|要注意)',
    r'(?:建议|推荐|不建议|不推荐|避免|应该避免)',
    r'(?:最佳实践|常见问题|解决方案|workaround)',
    r'(?:之前.*(?:遇到|碰到|发现))',
    r'(?:关键是|核心是|重点是|本质是)',
]

MEMORY_PATTERNS = [
    r'(?:我是|我叫|我的名字|我姓)',
    r'(?:我的公司|我们公司|公司名|公司叫)',
    r'(?:我(?:在|住|来自|位于))',
    r'(?:我(?:喜欢|偏好|习惯|讨厌|不喜欢))',
    r'(?:我的(?:工作|职业|行业|专业|背景))',
    r'(?:我(?:做|从事|负责|管理))',
    r'(?:我.{0,5}(?:年营业额|营收|收入|利润|产值))',
    r'(?:我.{0,5}(?:小规模|一般纳税人|个体户|有限公司|合伙企业))',
    r'(?:我(?:想|要|需要|希望|打算|计划))',
    r'(?:我.{0,5}(?:开了|注册了|成立了|创办了))',
]

SKILL_PATTERNS = [
    r'(?:第[一二三四五六七八九十]+步)',
    r'(?:步骤[一二三四五六七八九十\d])',
    r'(?:流程|操作流程|工作流|pipeline)',
    r'(?:1\.|2\.|3\.)',
    r'(?:首先|然后|接着|最后|最终)',
    r'(?:如何做|怎么做|怎么操作|操作方法)',
    r'(?:模板|脚本|命令|指令)',
]


def classify_text(text):
    results = []

    knowledge_score = sum(1 for p in KNOWLEDGE_PATTERNS if re.search(p, text))
    experience_score = sum(1 for p in EXPERIENCE_PATTERNS if re.search(p, text))
    memory_score = sum(1 for p in MEMORY_PATTERNS if re.search(p, text))
    skill_score = sum(1 for p in SKILL_PATTERNS if re.search(p, text))

    if knowledge_score >= 2:
        results.append(("知识阁", knowledge_score))
    if experience_score >= 2:
        results.append(("经验阁", experience_score))
    if memory_score >= 1:
        results.append(("记忆阁", memory_score))
    if skill_score >= 2:
        results.append(("技能阁", skill_score))

    return results


def extract_storable_segments(user_input, model_response):
    segments = []

    user_classifications = classify_text(user_input)
    for pavilion, score in user_classifications:
        if pavilion == "记忆阁":
            # 含问号的是提问，不是身份信息，不存入潜意识
            if '？' not in user_input and '?' not in user_input:
                segments.append({"pavilion": pavilion, "content": user_input, "source": "user", "score": score})

    paragraphs = re.split(r'\n\n+', model_response)
    for para in paragraphs:
        para = para.strip()
        if len(para) < 10:
            continue
        classifications = classify_text(para)
        for pavilion, score in classifications:
            segments.append({"pavilion": pavilion, "content": para, "source": "model", "score": score})

    if not any(c[0] == "知识阁" for c in classify_text(model_response)):
        full_classifications = classify_text(model_response)
        for pavilion, score in full_classifications:
            if pavilion == "知识阁" and not any(s["pavilion"] == "知识阁" for s in segments):
                segments.append({"pavilion": pavilion, "content": model_response, "source": "model", "score": score})

    return segments


# ============================================================
# 7. 写入阁 + 更新INDEX
# ============================================================

def generate_entry_id(content):
    return hashlib.md5(content.encode()).hexdigest()[:8]


def extract_trigger_words(content):
    keywords = extract_keywords(content)
    scored = {}
    for kw in keywords:
        scored[kw] = scored.get(kw, 0) + 1
    sorted_kw = sorted(scored.items(), key=lambda x: -x[1])
    return [kw for kw, _ in sorted_kw[:8]]


def check_duplicate(pavilion_dir, content):
    trigger_words = extract_trigger_words(content)
    entries = load_index(pavilion_dir)
    for entry in entries:
        overlap = sum(1 for t in entry["triggers"] if any(t in tw or tw in t for tw in trigger_words))
        if overlap >= 3:
            return entry
    return None


def write_to_pavilion(pavilion_name, content, source="model"):
    pavilion_dir = PAVILION_DIRS[pavilion_name]

    if pavilion_name == "记忆阁" and source == "user":
        core_path = pavilion_dir / "core.md"
        existing = core_path.read_text(encoding="utf-8") if core_path.exists() else ""
        content_clean = content.strip()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        timestamped_entry = f"{timestamp}|{content_clean}"
        if content_clean not in existing:
            with open(core_path, "a", encoding="utf-8") as f:
                f.write(f"\n{timestamped_entry}\n")
        return "core.md", "updated"

    dup = check_duplicate(pavilion_dir, content)
    if dup:
        existing_path = pavilion_dir / dup["file"]
        if existing_path.exists():
            existing_content = existing_path.read_text(encoding="utf-8")
            if content.strip() not in existing_content:
                with open(existing_path, "a", encoding="utf-8") as f:
                    f.write(f"\n\n---\n{datetime.now().strftime('%Y-%m-%d %H:%M')}\n{content.strip()}\n")
        return dup["file"], "merged"

    entry_id = generate_entry_id(content)
    filename = f"{entry_id}.md"
    filepath = pavilion_dir / filename

    summary_line = content.strip().split("\n")[0][:60]

    with open(filepath, "w", encoding="utf-8") as f:
        f.write(f"# {summary_line}\n\n")
        f.write(f"创建时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
        f.write(content.strip())
        f.write("\n")

    trigger_words = extract_trigger_words(content)
    triggers_str = ", ".join(trigger_words)

    index_path = pavilion_dir / "INDEX.md"
    with open(index_path, "a", encoding="utf-8") as f:
        f.write(f"{triggers_str} | {filename} | {summary_line}\n")

    return filename, "created"


# ============================================================
# 8. Session管理
# ============================================================

def create_session():
    session_id = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:6]
    session_path = SESSION_DIR / session_id
    session_path.mkdir(parents=True, exist_ok=True)
    dialog_path = session_path / "dialog.md"
    dialog_path.write_text(f"# Session {session_id}\n开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n", encoding="utf-8")
    return session_id, session_path


def append_to_dialog(session_path, role, content):
    dialog_path = session_path / "dialog.md"
    with open(dialog_path, "a", encoding="utf-8") as f:
        timestamp = datetime.now().strftime("%H:%M:%S")
        f.write(f"\n## [{timestamp}] {role}\n{content}\n")


def session_end_sedimentation(session_path):
    """Session结束后的沉淀整理：去重去噪、瘦身、毕业机制、归潜意识"""
    dialog_path = session_path / "dialog.md"
    if not dialog_path.exists():
        return []

    content = dialog_path.read_text(encoding="utf-8")
    results = []

    # TODO: 毕业机制（重复操作→Skill）和潜意识归入
    # 需要跨session统计，后续版本实现

    return results


# ============================================================
# 9. 主循环
# ============================================================

def run_interactive():
    print("=" * 50)
    print("  四阁调度系统 v1.0")
    print("  输入 /exit 退出 | /status 查看四阁状态")
    print("=" * 50)

    session_id, session_path = create_session()
    print(f"  Session: {session_id}")
    print("=" * 50)

    history = []

    while True:
        try:
            user_input = input("\n你: ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not user_input:
            continue

        if user_input == "/exit":
            print("\n正在进行session沉淀整理...")
            session_end_sedimentation(session_path)
            print("Session结束。再见！")
            break

        if user_input == "/status":
            print_status()
            continue

        # Step 1: 提取关键词
        keywords = extract_keywords(user_input)

        # Step 2: 检索加载
        context_blocks = retrieve_context(keywords)
        subconscious = load_subconscious()

        retrieval_info = []
        if subconscious:
            retrieval_info.append("潜意识已加载")
        if context_blocks:
            retrieval_info.append(f"命中{len(context_blocks)}条阁内容")
        if retrieval_info:
            print(f"  [{', '.join(retrieval_info)}]")

        # Step 3: 拼装Prompt
        messages = assemble_prompt(user_input, keywords, history)

        # Step 4: 调用API
        response = call_api(messages)
        print(f"\nSonny: {response}")

        # 记录对话
        append_to_dialog(session_path, "用户", user_input)
        append_to_dialog(session_path, "Sonny", response)
        history.append({"role": "user", "content": user_input})
        history.append({"role": "assistant", "content": response})

        # Step 5: 沙漏分流
        segments = extract_storable_segments(user_input, response)
        if segments:
            routing_log = []
            for seg in segments:
                filename, action = write_to_pavilion(seg["pavilion"], seg["content"], seg["source"])
                routing_log.append(f"{seg['pavilion']}→{filename}({action})")
            print(f"  [沙漏分流: {'; '.join(routing_log)}]")


def print_status():
    print("\n--- 四阁状态 ---")
    for name, pdir in PAVILION_DIRS.items():
        entries = load_index(pdir)
        files = list(pdir.glob("*.md"))
        non_index = [f for f in files if f.name != "INDEX.md" and f.name != "core.md"]
        print(f"  {name}: {len(entries)}条索引, {len(non_index)}个条目文件")

    sessions = list(SESSION_DIR.iterdir()) if SESSION_DIR.exists() else []
    sessions = [s for s in sessions if s.is_dir()]
    print(f"  Sessions: {len(sessions)}个")
    print("--- ---")


# ============================================================
# 10. 程序化调用接口（供测试脚本使用）
# ============================================================

class Dispatcher:
    def __init__(self):
        self.session_id, self.session_path = create_session()
        self.history = []

    def send(self, user_input):
        keywords = extract_keywords(user_input)
        context_blocks = retrieve_context(keywords)

        result = call_with_search_fallback(user_input, keywords, self.history)
        response = result["response"]

        append_to_dialog(self.session_path, "用户", user_input)
        append_to_dialog(self.session_path, "Sonny", response)
        self.history.append({"role": "user", "content": user_input})
        self.history.append({"role": "assistant", "content": response})

        segments = extract_storable_segments(user_input, response)
        routing_results = []
        for seg in segments:
            filename, action = write_to_pavilion(seg["pavilion"], seg["content"], seg["source"])
            routing_results.append({
                "pavilion": seg["pavilion"],
                "file": filename,
                "action": action,
                "source": seg["source"],
                "score": seg["score"],
            })

        return {
            "response": response,
            "keywords": keywords,
            "context_loaded": len(context_blocks),
            "routing": routing_results,
            "search_used": result["search_used"],
            "time_first": result["time_first"],
            "time_total": result["time_total"],
        }

    def end_session(self):
        return session_end_sedimentation(self.session_path)

    def get_status(self):
        status = {}
        for name, pdir in PAVILION_DIRS.items():
            entries = load_index(pdir)
            files = [f for f in pdir.glob("*.md") if f.name not in ("INDEX.md", "core.md")]
            status[name] = {"index_entries": len(entries), "files": len(files)}
        return status


if __name__ == "__main__":
    run_interactive()
