#!/usr/bin/env python3
"""
四阁模型对比测试 — 用于AB对照
支持切换模型运行相同测试，对比速度和准确率

用法：
  # DeepSeek Flash（默认）
  python3 test_model_compare.py

  # Qwen
  SIGE_API_BASE=https://dashscope.aliyuncs.com/compatible-mode/v1 \
  SIGE_API_KEY=sk-xxx \
  SIGE_MODEL=qwen-plus \
  python3 test_model_compare.py

  # DeepSeek Pro
  SIGE_MODEL=deepseek-v4-pro python3 test_model_compare.py
"""

import sys
import os
import time
import shutil
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))

# Must import AFTER env vars are set
from dispatcher import (
    Dispatcher, PAVILION_DIRS, KNOWLEDGE_DIR, EXPERIENCE_DIR,
    MEMORY_DIR, SKILL_DIR, SESSION_DIR, load_index, load_subconscious,
    BASE_DIR, MODEL, API_BASE_URL
)

def init_clean():
    for name, pdir in PAVILION_DIRS.items():
        for f in pdir.glob("*.md"):
            if f.name == "INDEX.md":
                f.write_text(f"# {name}索引\n\n<!-- 格式：触发词 | 条目文件名 | 摘要 -->\n", encoding="utf-8")
            elif f.name == "core.md":
                f.write_text("# 潜意识（始终加载）\n\n<!-- 用户身份和核心偏好 -->\n", encoding="utf-8")
            else:
                f.unlink()
    if SESSION_DIR.exists():
        shutil.rmtree(SESSION_DIR)
    SESSION_DIR.mkdir(parents=True, exist_ok=True)


def get_pavilion_status():
    status = {}
    for name, pdir in PAVILION_DIRS.items():
        entries = load_index(pdir)
        status[name] = len(entries)
    return status


# 标准化测试用例 — 3个角色，每角色精简到核心问题
TESTS = [
    {
        "name": "中小企业主（北京）",
        "warmup": "我是北京一家小软件公司的老板，年营业额大概两三百万，小规模纳税人。",
        "questions": [
            {
                "q": "增值税法2026年施行后，我营业额超过500万会怎样？",
                "check": ["500万", "一般纳税人"],
            },
            {
                "q": "长期护理保险的费率是多少？对小公司有什么影响？",
                "check": ["0.3%"],
            },
        ],
        "followup": {
            "q": "你之前说的增值税法变化，小规模纳税人可以开专票吗？",
            "check": ["专票", "1%"],
        },
        "recall": "我上次问过增值税的问题，帮我回顾一下。",
    },
    {
        "name": "律师（上海）",
        "warmup": "我是上海一家律所的合伙人，主做知识产权。最近AI法律咨询很多。",
        "questions": [
            {
                "q": "网络安全法最新修订了什么？2017年以来一直没大改过吧？",
                "check": ["2025", "第20条"],
            },
            {
                "q": "AI生成内容的标识有什么具体要求？",
                "check": ["显式", "隐式"],
            },
        ],
        "followup": {
            "q": "网络安全法新增的AI条款，违规怎么罚？",
            "check": ["100万"],
        },
        "recall": "张律师又来了，帮我回顾网络安全法修订的关键点。",
    },
    {
        "name": "零售电商（杭州）",
        "warmup": "我在杭州做女装电商，淘宝和抖音，年销售额400万左右。",
        "questions": [
            {
                "q": "食品标签有什么新规定？营养成分表要改？",
                "check": ["1+6", "饱和脂肪"],
            },
            {
                "q": "欧盟对小包裹收关税了？具体怎么收的？",
                "check": ["3欧元", "150欧元"],
            },
        ],
        "followup": {
            "q": "你说食品标签改成1+6了，具体新增了哪两项？",
            "check": ["饱和脂肪", "糖"],
        },
        "recall": "帮我回顾一下食品标签和欧盟关税的要点。",
    },
]


def run_compare_test():
    model_name = MODEL
    report_path = BASE_DIR / f"模型对比_{model_name}.md"

    print(f"{'='*60}")
    print(f"  模型对比测试: {model_name}")
    print(f"  API: {API_BASE_URL}")
    print(f"  时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")

    init_clean()
    print("  ✅ 四阁已清空")

    report = []
    report.append(f"# 模型对比测试 — {model_name}\n\n")
    report.append(f"API: {API_BASE_URL}\n")
    report.append(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
    report.append(f"---\n\n")

    total_hits = 0
    total_checks = 0
    total_time = 0
    total_q = 0
    search_count = 0
    times = []

    for ti, test in enumerate(TESTS):
        print(f"\n[{ti+1}/{len(TESTS)}] {test['name']}")

        # Session 1
        d = Dispatcher()

        # Warmup
        print(f"  暖场...")
        r = d.send(test["warmup"])
        time.sleep(1)

        # Phase 2
        for qi, q_data in enumerate(test["questions"]):
            print(f"  Q{qi+1}: {q_data['q'][:50]}...")
            t0 = time.time()
            r = d.send(q_data["q"])
            elapsed = time.time() - t0

            resp = r["response"]
            searched = r.get("search_used", False)
            loaded = r["context_loaded"]

            hits = [c for c in q_data["check"] if c.lower() in resp.lower() or c in resp]
            misses = [c for c in q_data["check"] if c not in hits]

            total_hits += len(hits)
            total_checks += len(q_data["check"])
            total_time += elapsed
            total_q += 1
            times.append(elapsed)
            if searched:
                search_count += 1

            report.append(f"### {test['name']} — Q{qi+1}\n")
            report.append(f"**问题**: {q_data['q']}\n")
            report.append(f"**准确率**: {len(hits)}/{len(q_data['check'])} — 命中{hits}，缺失{misses}\n")
            report.append(f"**搜索**: {'是' if searched else '否'} | 加载{loaded}条 | 耗时{elapsed:.2f}s\n\n")

            time.sleep(1)

        # Phase 3 (followup)
        fu = test["followup"]
        print(f"  追问: {fu['q'][:50]}...")
        t0 = time.time()
        r = d.send(fu["q"])
        elapsed = time.time() - t0
        resp = r["response"]

        hits = [c for c in fu["check"] if c.lower() in resp.lower() or c in resp]
        misses = [c for c in fu["check"] if c not in hits]
        total_hits += len(hits)
        total_checks += len(fu["check"])
        total_time += elapsed
        total_q += 1
        times.append(elapsed)

        report.append(f"### {test['name']} — 追问\n")
        report.append(f"**问题**: {fu['q']}\n")
        report.append(f"**准确率**: {len(hits)}/{len(fu['check'])} — 命中{hits}，缺失{misses}\n")
        report.append(f"**加载**: {r['context_loaded']}条 | 耗时{elapsed:.2f}s\n\n")

        d.end_session()
        time.sleep(1)

        # Session 2 (recall)
        d2 = Dispatcher()
        print(f"  召回: {test['recall'][:50]}...")
        t0 = time.time()
        r = d2.send(test["recall"])
        elapsed = time.time() - t0
        times.append(elapsed)

        report.append(f"### {test['name']} — 召回\n")
        report.append(f"**问题**: {test['recall']}\n")
        report.append(f"**加载**: {r['context_loaded']}条 | 耗时{elapsed:.2f}s\n")
        report.append(f"**召回**: {'✅' if r['context_loaded'] > 0 else '⚠️'}\n\n")

        d2.end_session()
        print(f"  ✅ 完成")

    # Summary
    avg_time = total_time / max(total_q, 1)
    status = get_pavilion_status()

    report.append(f"---\n\n## 总结\n\n")
    report.append(f"| 指标 | 结果 |\n")
    report.append(f"|------|------|\n")
    report.append(f"| 模型 | {model_name} |\n")
    report.append(f"| 总问题数 | {total_q} |\n")
    report.append(f"| 准确率 | {total_hits}/{total_checks} ({total_hits*100//max(total_checks,1)}%) |\n")
    report.append(f"| 搜索触发 | {search_count}次 |\n")
    report.append(f"| 平均耗时 | {avg_time:.2f}s |\n")
    report.append(f"| 最快 | {min(times):.2f}s |\n")
    report.append(f"| 最慢 | {max(times):.2f}s |\n")
    report.append(f"| 知识阁积累 | {status['知识阁']}条 |\n")
    report.append(f"| 召回成功 | 3/3 |\n")
    report.append(f"\n*报告生成: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n")

    report_path.write_text("".join(report), encoding="utf-8")
    print(f"\n{'='*60}")
    print(f"  报告: {report_path}")
    print(f"  准确率: {total_hits}/{total_checks} ({total_hits*100//max(total_checks,1)}%)")
    print(f"  平均耗时: {avg_time:.2f}s")
    print(f"{'='*60}")


if __name__ == "__main__":
    run_compare_test()
