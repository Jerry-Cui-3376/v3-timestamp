#!/usr/bin/env python3
"""
四阁完整测试 — 严格按测试方法执行
- 空白启动，不预装知识
- 每个角色 = 新session
- 知识累积不清零
- 完整流程：暖场 → 行为测试 → 检索测试 → 补全测试 → 沉淀观察
- 记录：分流路径、检索加载、搜索触发、耗时、准确性
"""

import sys
import os
import json
import shutil
import time
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent))
from dispatcher import (
    Dispatcher, PAVILION_DIRS, KNOWLEDGE_DIR, EXPERIENCE_DIR,
    MEMORY_DIR, SKILL_DIR, SESSION_DIR, load_index, load_subconscious,
    load_entry_content, BASE_DIR
)

REPORT_PATH = BASE_DIR / "完整测试报告.md"

# ============================================================
# 初始化（只做一次，空白启动）
# ============================================================

def init_clean():
    """完全清空四阁，空白启动"""
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
        files = [f for f in pdir.glob("*.md") if f.name not in ("INDEX.md", "core.md")]
        status[name] = {"index": len(entries), "files": len(files)}
    return status


# ============================================================
# 测试角色定义（按测试方法：暖场 → 阶段二 → 阶段三 → 阶段3.5）
# ============================================================

TESTS = [
    # ======== 角色1：中小企业主（SME原卷） ========
    {
        "name": "中小企业主（北京软件外包）",
        "industry": "中小企业/IT",
        "session1": {
            "warmup": [
                "我最近刚在北京注册了一家小公司，做软件开发外包的。注册资本写了100万，认缴的。",
                "对了，我现在营业额还不大，一年大概两三百万，增值税这块我是小规模纳税人。",
            ],
            "phase2": [
                {
                    "q": "我听说增值税有什么新的法律变化？2026年开始的？如果我的营业额突然超过500万了，现在的规定是怎么处理的？",
                    "ref": "《增值税法》2026年1月1日施行；超500万必须登记一般纳税人，不可延迟；一般纳税人身份自动追溯无缓冲期",
                    "check": ["2026", "一般纳税人", "不可延迟"],
                },
                {
                    "q": "那小规模纳税人的起征点有没有变化？我偶尔接一些零散的小单子，按次交税的那种。",
                    "ref": "按次起征点从500元提高至1000元；按期月10万免征延续；自然人6种特定情形不适用按次1000元",
                    "check": ["1000", "500"],
                },
                {
                    "q": "最近听朋友说社保要多一个险种？什么长期护理保险？这个对我们小公司有什么影响？费率多少？",
                    "ref": "2026年3月26日中办国办发文；费率0.3%；单位和个人各0.15%；2028年底全覆盖；36项服务",
                    "check": ["0.3%", "0.15%"],
                },
                {
                    "q": "我在北京嘛，最近医保缴费是不是也有变化？我记得之前好像降过，现在怎么样了？",
                    "ref": "2026年1月1日起用人单位从4.5%恢复为6%；灵活就业人员从6.5%恢复为8%",
                    "check": ["4.5%", "6%"],
                },
            ],
            "phase3": [
                {
                    "q": "你之前说增值税法2026年施行了，那我作为小规模纳税人，如果我想给客户开专票，可以吗？有什么新的规定？",
                    "ref": "小规模可选择放弃免税开专票；单笔放弃不影响其他交易；可按1%征收率开票",
                    "check": ["专票", "1%"],
                    "track_path": True,
                },
                {
                    "q": "长期护理保险你说单位和个人各0.15%，那退休员工呢？还有农村那些没工作的人怎么交？",
                    "ref": "退休人员个人0.15%基数为养老金单位不缴；未就业居民首年0.15%用5年过渡到0.3%",
                    "check": ["退休", "0.15%"],
                    "track_path": True,
                },
            ],
            "phase35": [
                {
                    "q": "我最近想买一批设备扩大产能，听说国家有什么贷款贴息政策？具体贴多少？我这种小公司能申请吗？",
                    "ref": "年化1.5个百分点贴息；期限不超过2年；单户上限5000万元；14个重点产业链",
                    "check": ["1.5", "5000万"],
                },
                {
                    "q": "除了银行贷款，那些小额贷款公司呢？我听说现在对他们利率也有限制了？",
                    "ref": "247号文；不得超过年化24%红线；分阶段降至LPR 4倍即12%；2027年底全部压降",
                    "check": ["24%", "12%"],
                },
            ],
        },
        "session2": {
            "questions": [
                {
                    "q": "我上次跟你聊过关于我公司的税务问题，你还记得我的情况吗？",
                    "check_memory": True,
                },
                {
                    "q": "帮我回顾一下上次讨论的增值税法的新变化。",
                    "check_retrieval": True,
                    "expected_topic": "增值税法",
                },
                {
                    "q": "那个长期护理保险的费率再帮我确认一下。",
                    "check_retrieval": True,
                    "expected_topic": "长期护理保险",
                },
            ],
        },
    },

    # ======== 角色2：零售电商（杭州女装） ========
    {
        "name": "零售电商（杭州女装）",
        "industry": "零售/电商",
        "session1": {
            "warmup": [
                "你好，我在杭州做女装电商，主要在淘宝和抖音卖，年销售额大概400万。",
            ],
            "phase2": [
                {
                    "q": "听说食品安全法修订了？我虽然卖衣服，但我老公做食品进口，他让我帮他问问最新的变化。",
                    "ref": "2025年9月12日通过；2025年12月1日生效；液态食品运输许可制度；婴幼儿配方液态乳纳入注册管理",
                    "check": ["液态食品", "运输"],
                },
                {
                    "q": "那食品标签方面有什么新规定吗？他说什么营养成分表要改？",
                    "ref": "GB 28050-2025；1+4升级为1+6；新增饱和脂肪酸和糖；2027年3月16日实施",
                    "check": ["1+6", "饱和脂肪"],
                },
                {
                    "q": "我自己做跨境电商，听说欧盟要对小包裹收关税了？这影响大吗？",
                    "ref": "2026年7月1日生效；每件3欧元固定关税；低价直邮+免税模式终结",
                    "check": ["3欧元", "150欧元"],
                },
            ],
            "phase3": [
                {
                    "q": "你刚才说的食品标签改成1+6了，具体新增了哪两项？什么时候必须执行？",
                    "ref": "新增饱和脂肪酸和糖；2027年3月16日实施；实施前生产的可在保质期内继续销售",
                    "check": ["饱和脂肪", "糖"],
                    "track_path": True,
                },
            ],
            "phase35": [
                {
                    "q": "我自己的电商直播方面，听说有个直播电商监督管理办法出来了？AI数字人直播有什么要求？",
                    "ref": "2026年2月1日施行；第37条AI数字人须持续提示AI生成；保存交易信息不少于三年",
                    "check": ["第37条", "AI"],
                },
            ],
        },
        "session2": {
            "questions": [
                {
                    "q": "我之前问过你关于食品标签和欧盟关税的问题，帮我回顾一下要点。",
                    "check_retrieval": True,
                    "expected_topic": "食品标签",
                },
            ],
        },
    },

    # ======== 角色3：制造业（东莞五金） ========
    {
        "name": "制造业工厂主（东莞五金加工）",
        "industry": "制造业",
        "session1": {
            "warmup": [
                "我姓王，在东莞开了个五金加工厂，主要做五金配件出口，年产值大概500万。",
            ],
            "phase2": [
                {
                    "q": "2026年的关税调整方案出来了吗？对我们制造业出口有什么影响？",
                    "ref": "2026年1月1日生效；935项商品低税率；科技/绿色/民生类降税；税则总数8972个",
                    "check": ["935", "8972"],
                },
                {
                    "q": "互联网平台涉税信息报送规定是怎么回事？我们通过1688平台卖货，要不要申报？",
                    "ref": "2025年10月1日生效；每季度终了次月内报送；最高50万罚款；已有6654家平台报送",
                    "check": ["每季度", "50万"],
                },
            ],
            "phase3": [
                {
                    "q": "你刚才说关税调了935项商品，具体哪些跟我们五金加工相关的？有没有降的？",
                    "ref": "压力机用数控液压气垫等关键零部件降税",
                    "check": ["零部件"],
                    "track_path": True,
                },
            ],
            "phase35": [],
        },
        "session2": {
            "questions": [
                {
                    "q": "我是之前问关税和平台报送的东莞五金厂老板，帮我看看之前的关键信息。",
                    "check_retrieval": True,
                    "expected_topic": "关税",
                },
            ],
        },
    },

    # ======== 角色4：律师（上海知识产权） ========
    {
        "name": "律师（上海知识产权）",
        "industry": "法律",
        "session1": {
            "warmup": [
                "我是上海一家律所的合伙人，张律师，主要做知识产权诉讼。最近AI方面的法律咨询越来越多。",
            ],
            "phase2": [
                {
                    "q": "《网络安全法》最新修订了什么？我记得2017年以来好像一直没大改过？",
                    "ref": "2025年10月28日通过；2026年1月1日施行；首次重大修订；新增第20条AI治理专条；罚款上限100万提至200万",
                    "check": ["2025年10月", "第20条"],
                },
                {
                    "q": "AI生成内容的标识有什么具体要求吗？我的客户做AI产品的，很关心合规。",
                    "ref": "2025年9月1日施行；显式标识+隐式标识；不得恶意删除篡改标识；配套强制性国标",
                    "check": ["显式标识", "隐式标识"],
                },
                {
                    "q": "个人信息出境认证办法的新规定是什么？跨境业务的客户问得很多。",
                    "ref": "2026年1月1日施行；10万人以上不满100万人适用认证；证书有效期3年",
                    "check": ["10万人", "3年"],
                },
            ],
            "phase3": [
                {
                    "q": "你说网络安全法新增了第20条AI治理专条，具体内容是什么？违规怎么罚？",
                    "ref": "支持AI基础理论研究；要求生成内容标识；违规最高罚100万及暂停服务",
                    "check": ["100万", "标识"],
                    "track_path": True,
                },
            ],
            "phase35": [
                {
                    "q": "最近有没有大型网络平台个人信息保护方面的新规定？比如什么规模的平台要遵守？",
                    "ref": "征求意见稿2025年11月22日；注册用户5000万以上或月活1000万以上；数据本地化；负责人须中国国籍",
                    "check": ["5000万", "1000万"],
                },
            ],
        },
        "session2": {
            "questions": [
                {
                    "q": "张律师又来了。帮我回顾一下网络安全法修订和个人信息出境的关键点。",
                    "check_retrieval": True,
                    "expected_topic": "网络安全法",
                },
            ],
        },
    },

    # ======== 角色5：营销从业者（深圳MCN） ========
    {
        "name": "营销从业者（深圳MCN机构）",
        "industry": "营销/广告",
        "session1": {
            "warmup": [
                "你好，我在深圳做MCN机构，管理十几个主播，主要做抖音和快手的直播带货。",
            ],
            "phase2": [
                {
                    "q": "直播电商方面有没有新的监管办法出来？我们用AI数字人直播越来越多了。",
                    "ref": "《直播电商监督管理办法》2026年2月1日施行；AI数字人须持续提示；四类主体责任；分级分类管理",
                    "check": ["2026年2月", "第37条"],
                },
                {
                    "q": "反不正当竞争法修订对我们做电商营销有什么影响？刷单这些以前是灰色地带。",
                    "ref": "2025年10月15日施行；第14条反内卷条款；刷单入法；虚假宣传扩大到其他经营者；域外适用第40条",
                    "check": ["第14条", "刷单"],
                },
            ],
            "phase3": [
                {
                    "q": "那个直播电商管理办法，我用AI数字人直播具体要怎么标注？不标注会怎样？",
                    "ref": "须持续向消费者提示AI生成；直播间运营者为第一责任人；不得以技术中立逃避",
                    "check": ["持续", "第一责任人"],
                    "track_path": True,
                },
            ],
            "phase35": [
                {
                    "q": "今年广告执法力度怎么样？有没有具体的查处数据？特别是互联网广告方面。",
                    "ref": "2025年查办44521件罚没2.52亿；互联网违法广告22185件罚没1.11亿",
                    "check": ["44521", "2.52亿"],
                },
            ],
        },
        "session2": {
            "questions": [
                {
                    "q": "我之前问过直播电商监管和反不正当竞争法的问题，帮我回顾一下关键要点。",
                    "check_retrieval": True,
                    "expected_topic": "直播电商",
                },
            ],
        },
    },
]


# ============================================================
# 测试执行
# ============================================================

def run_question(dispatcher, q_text, report, prefix="", ref=None, checks=None, track_path=False):
    """执行单个问题，记录结果"""
    print(f"    {prefix}: {q_text[:50]}...")
    result = dispatcher.send(q_text)
    resp = result["response"]

    report.append(f"\n**{prefix}**: {q_text}\n")
    report.append(f"**回复**: {resp[:300]}{'...' if len(resp)>300 else ''}\n")

    # 检索加载
    ctx = result["context_loaded"]
    search = result.get("search_used", False)
    t_first = result.get("time_first", 0)
    t_total = result.get("time_total", 0)

    path_info = []
    if ctx > 0:
        path_info.append(f"从阁中加载{ctx}条")
    if search:
        path_info.append("触发了搜索")
    path_info.append(f"耗时{t_total}s")
    report.append(f"**路径**: {' | '.join(path_info) if path_info else '无特殊'}\n")

    # 分流记录
    if result["routing"]:
        routing_str = ", ".join([f"{r['pavilion']}→{r['file']}({r['action']})" for r in result["routing"]])
        report.append(f"**分流**: {routing_str}\n")
    else:
        report.append(f"**分流**: 无\n")

    # 准确率检查
    if checks:
        hits = []
        misses = []
        for kw in checks:
            if kw.lower() in resp.lower() or kw in resp:
                hits.append(kw)
            else:
                misses.append(kw)
        total = len(checks)
        hit_count = len(hits)
        report.append(f"**准确率**: {hit_count}/{total} — 命中{hits}{'，缺失'+str(misses) if misses else ''}\n")

    # 诚实率（阶段二）
    if search:
        report.append(f"**诚实率**: ✅ 承认不确定并触发搜索\n")

    time.sleep(1)
    return result


def run_single_test(test, report):
    """执行单个角色的完整测试"""
    report.append(f"\n---\n\n## {test['name']}\n")
    report.append(f"行业: {test['industry']}\n")

    # 记录测试前四阁状态
    status_before = get_pavilion_status()
    report.append(f"**测试前四阁状态**: 知识{status_before['知识阁']['index']}条 | 经验{status_before['经验阁']['index']}条 | 技能{status_before['技能阁']['index']}条\n")

    # ===== Session 1 =====
    report.append(f"\n### Session 1\n")
    d1 = Dispatcher()

    # 暖场
    report.append(f"\n#### 暖场\n")
    for i, msg in enumerate(test["session1"]["warmup"]):
        run_question(d1, msg, report, prefix=f"暖场{i+1}")

    # 阶段二
    report.append(f"\n#### 阶段二（行为测试）\n")
    for i, item in enumerate(test["session1"]["phase2"]):
        run_question(d1, item["q"], report,
                     prefix=f"Q{i+1}",
                     ref=item.get("ref"),
                     checks=item.get("check"))

    # 阶段三
    if test["session1"].get("phase3"):
        report.append(f"\n#### 阶段三（检索测试）\n")
        for i, item in enumerate(test["session1"]["phase3"]):
            run_question(d1, item["q"], report,
                         prefix=f"追问{i+1}",
                         ref=item.get("ref"),
                         checks=item.get("check"),
                         track_path=item.get("track_path", False))

    # 阶段3.5
    if test["session1"].get("phase35"):
        report.append(f"\n#### 阶段3.5（补全测试）\n")
        for i, item in enumerate(test["session1"]["phase35"]):
            run_question(d1, item["q"], report,
                         prefix=f"补全{i+1}",
                         ref=item.get("ref"),
                         checks=item.get("check"))

    d1.end_session()

    # Session 1 结果检查
    report.append(f"\n#### Session 1 四阁状态\n")
    status_after = get_pavilion_status()
    for name in ["知识阁", "经验阁", "记忆阁", "技能阁"]:
        before = status_before[name]["index"]
        after = status_after[name]["index"]
        delta = after - before
        report.append(f"- **{name}**: {after}条索引 (新增{delta})\n")

    subconscious = load_subconscious()
    report.append(f"- **潜意识**: {subconscious[:120] if subconscious else '空'}{'...' if len(subconscious)>120 else ''}\n")

    # ===== Session 2（跨Session召回） =====
    if test.get("session2"):
        report.append(f"\n### Session 2（跨Session召回）\n")
        d2 = Dispatcher()

        for i, item in enumerate(test["session2"]["questions"]):
            result = run_question(d2, item["q"], report,
                                  prefix=f"召回{i+1}",
                                  checks=item.get("check"))

            if item.get("check_memory"):
                report.append(f"**记忆验证**: {'✅ 潜意识已加载' if result['context_loaded'] > 0 or subconscious else '⚠️'}\n")

            if item.get("check_retrieval"):
                if result["context_loaded"] > 0:
                    report.append(f"**检索验证**: ✅ 从阁中加载了{result['context_loaded']}条内容\n")
                else:
                    report.append(f"**检索验证**: ⚠️ 未从阁中加载（可能触发词未匹配）\n")

        d2.end_session()

    # 综合评分
    report.append(f"\n### 本角色小结\n")
    status_final = get_pavilion_status()
    report.append(f"- 知识阁: {status_final['知识阁']['index']}条 (累计)\n")
    report.append(f"- 经验阁: {status_final['经验阁']['index']}条 (累计)\n")
    report.append(f"- 技能阁: {status_final['技能阁']['index']}条 (累计)\n")


# ============================================================
# 速度对比测试
# ============================================================

def run_speed_comparison(report):
    """同一问题：搜索 vs 本地检索的速度对比"""
    report.append(f"\n---\n\n## 速度对比测试（搜索 vs 本地检索）\n")

    test_questions = [
        "增值税法2026年施行后，小规模纳税人超过500万要怎么处理？",
        "长期护理保险的费率是多少？单位和个人各交多少？",
        "直播电商监督管理办法对AI数字人有什么要求？",
    ]

    report.append(f"\n如果知识阁有对应内容，应该走本地加载（快）；如果没有，走搜索（慢）。\n")
    report.append(f"经过前5个角色的测试，知识阁应已累积相关知识。\n\n")

    report.append(f"| 问题 | 检索加载 | 搜索触发 | 首次耗时 | 总耗时 |\n")
    report.append(f"|------|----------|----------|----------|--------|\n")

    d = Dispatcher()
    for q in test_questions:
        result = d.send(q)
        ctx = result["context_loaded"]
        search = result.get("search_used", False)
        t_first = result.get("time_first", 0)
        t_total = result.get("time_total", 0)
        report.append(f"| {q[:30]}... | {ctx}条 | {'是' if search else '否'} | {t_first}s | {t_total}s |\n")
        time.sleep(1)
    d.end_session()


# ============================================================
# 沉淀观察
# ============================================================

def run_sedimentation_check(report):
    """检查所有测试后的四阁沉淀状态"""
    report.append(f"\n---\n\n## 沉淀观察\n")

    for name, pdir in PAVILION_DIRS.items():
        entries = load_index(pdir)
        files = [f for f in pdir.glob("*.md") if f.name not in ("INDEX.md", "core.md")]
        report.append(f"\n### {name}\n")
        report.append(f"- 索引条目: {len(entries)}\n")
        report.append(f"- 条目文件: {len(files)}\n")
        if entries:
            report.append(f"- 触发词覆盖:\n")
            for e in entries[:10]:
                report.append(f"  - {', '.join(e['triggers'][:5])} → {e['file']}\n")
            if len(entries) > 10:
                report.append(f"  - ...（共{len(entries)}条）\n")

    subconscious = load_subconscious()
    report.append(f"\n### 潜意识（core.md）\n")
    report.append(f"```\n{subconscious}\n```\n")

    # 统计sessions数
    sessions = list(SESSION_DIR.iterdir()) if SESSION_DIR.exists() else []
    sessions = [s for s in sessions if s.is_dir()]
    report.append(f"\n### Session统计\n")
    report.append(f"- 总session数: {len(sessions)}\n")


# ============================================================
# 主流程
# ============================================================

def run_full_test():
    print("=" * 60)
    print("  四阁完整测试")
    print(f"  时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"  原则: 空白启动 | 知识累积不清零 | 按测试方法执行")
    print("=" * 60)

    report = [
        f"# 四阁调度脚本 — 完整测试报告\n\n",
        f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n",
        f"模型: DeepSeek-V4-Flash\n",
        f"搜索: Tavily API（不确定时自动触发）\n",
        f"测试原则: 空白启动 | 知识累积不清零 | 严格按测试方法\n",
        f"测试角色: {len(TESTS)}个（{', '.join(t['name'] for t in TESTS)}）\n\n",
        f"测试流程: 暖场 → 阶段二(行为) → 阶段三(检索) → 阶段3.5(补全) → 跨Session召回\n",
    ]

    # 空白启动
    init_clean()
    print("\n  ✅ 四阁已清空，空白启动\n")

    # 依次执行每个角色
    for i, test in enumerate(TESTS):
        print(f"\n[{i+1}/{len(TESTS)}] {test['name']}")
        print(f"  {'='*40}")
        run_single_test(test, report)
        print(f"  ✅ 完成")

    # 速度对比
    print(f"\n[速度对比测试]")
    run_speed_comparison(report)
    print(f"  ✅ 完成")

    # 沉淀观察
    print(f"\n[沉淀观察]")
    run_sedimentation_check(report)
    print(f"  ✅ 完成")

    # 总结
    report.append(f"\n---\n\n## 总结\n\n")
    final_status = get_pavilion_status()
    report.append(f"| 指标 | 结果 |\n|------|------|\n")
    report.append(f"| 知识阁累积 | {final_status['知识阁']['index']}条索引 / {final_status['知识阁']['files']}个文件 |\n")
    report.append(f"| 经验阁累积 | {final_status['经验阁']['index']}条索引 / {final_status['经验阁']['files']}个文件 |\n")
    report.append(f"| 技能阁累积 | {final_status['技能阁']['index']}条索引 / {final_status['技能阁']['files']}个文件 |\n")
    report.append(f"| 记忆阁累积 | {final_status['记忆阁']['index']}条索引 / {final_status['记忆阁']['files']}个文件 |\n")
    report.append(f"| 测试角色 | {len(TESTS)}个 |\n")

    sessions = [s for s in SESSION_DIR.iterdir() if s.is_dir()] if SESSION_DIR.exists() else []
    report.append(f"| 总Session数 | {len(sessions)} |\n")

    report.append(f"\n---\n*报告生成: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n")

    REPORT_PATH.write_text("".join(report), encoding="utf-8")
    print(f"\n{'='*60}")
    print(f"  完整测试报告: {REPORT_PATH}")
    print(f"{'='*60}")


if __name__ == "__main__":
    run_full_test()
