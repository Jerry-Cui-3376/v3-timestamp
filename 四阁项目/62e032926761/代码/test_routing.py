#!/usr/bin/env python3
"""
四阁路由机械测试 — 验证分流规则是否正确
不调用API，只测试 classify_text 和写入逻辑
"""

import sys
import os
import shutil
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from dispatcher import (
    classify_text, extract_storable_segments, write_to_pavilion,
    load_index, extract_keywords, match_triggers, load_subconscious,
    KNOWLEDGE_DIR, EXPERIENCE_DIR, MEMORY_DIR, SKILL_DIR, PAVILION_DIRS, BASE_DIR
)

# ============================================================
# 测试用例
# ============================================================

ROUTING_TESTS = [
    # === 知识阁测试 ===
    {
        "name": "政策法规 → 知识阁",
        "text": "根据《增值税法》规定，小规模纳税人增值税起征点自2025年1月1日起调整为每月15万元，季度45万元。",
        "expected": "知识阁",
    },
    {
        "name": "经济数据 → 知识阁",
        "text": "2025年第三季度GDP同比增长4.8%，CPI环比上涨0.3%，PPI同比下降1.2%。",
        "expected": "知识阁",
    },
    {
        "name": "法律条文 → 知识阁",
        "text": "《民法典》第五百七十七条规定，当事人一方不履行合同义务或者履行合同义务不符合约定的，应当承担继续履行、采取补救措施或者赔偿损失等违约责任。",
        "expected": "知识阁",
    },
    {
        "name": "财税政策 → 知识阁",
        "text": "财政部、税务总局发布通知，自2025年起对小微企业减免所得税，年应纳税所得额不超过300万元的部分，减按25%计入应纳税所得额，按20%税率缴纳。",
        "expected": "知识阁",
    },
    {
        "name": "行业数据 → 知识阁",
        "text": "工信部数据显示，2025年我国软件业务收入达12.5万亿元，同比增长11.2%，其中信息技术服务收入8.3万亿元。",
        "expected": "知识阁",
    },

    # === 经验阁测试 ===
    {
        "name": "实践经验 → 经验阁",
        "text": "我们发现在做税务筹划时，原来把研发费用单独归集比混在管理费用里更有效，加计扣除比例能从75%提到100%。之前踩过坑，注意一定要有研发立项文件。",
        "expected": "经验阁",
    },
    {
        "name": "验证结论 → 经验阁",
        "text": "实际上小规模转一般纳税人不一定划算，我们试过两种方案，发现年营业额在300万以下时保持小规模纳税人更有效。关键是要算综合税负率。",
        "expected": "经验阁",
    },
    {
        "name": "最佳实践 → 经验阁",
        "text": "最佳实践是在合同签订前就确认开票类型，避免后期扯皮。常见问题是对方要求开专票但我们是小规模，解决方案是提前沟通或代开。",
        "expected": "经验阁",
    },

    # === 记忆阁测试 ===
    {
        "name": "用户身份 → 记忆阁",
        "text": "我是一个在北京注册的软件公司老板，我们公司年营业额大概200万，小规模纳税人。",
        "expected": "记忆阁",
    },
    {
        "name": "用户偏好 → 记忆阁",
        "text": "我喜欢简洁的回答，不要太多废话，我习惯用微信沟通。",
        "expected": "记忆阁",
    },
    {
        "name": "用户职业 → 记忆阁",
        "text": "我的工作是做软件外包，负责项目管理和技术架构。",
        "expected": "记忆阁",
    },

    # === 技能阁测试 ===
    {
        "name": "操作步骤 → 技能阁",
        "text": "注册公司的流程如下：第一步，核名，去工商局提交公司名称预审；第二步，提交材料，包括章程、股东身份证、租赁合同；第三步，领取营业执照；第四步，刻章备案；第五步，银行开户；第六步，税务登记。",
        "expected": "技能阁",
    },
    {
        "name": "操作指南 → 技能阁",
        "text": "如何做增值税申报：1. 登录电子税务局；2. 选择增值税申报表；3. 填写销售额和进项税额；4. 核对应纳税额；5. 提交申报；6. 完成缴款。",
        "expected": "技能阁",
    },

    # === 边界/混合测试 ===
    {
        "name": "纯闲聊 → 不分流",
        "text": "今天天气真不错啊，你觉得呢？",
        "expected": None,
    },
    {
        "name": "简短问题 → 不分流",
        "text": "帮我查一下这个",
        "expected": None,
    },
]


def reset_pavilions():
    """清空四阁内容，恢复初始状态"""
    for name, pdir in PAVILION_DIRS.items():
        for f in pdir.glob("*.md"):
            if f.name == "INDEX.md":
                f.write_text(f"# {name}索引\n\n<!-- 格式：触发词 | 条目文件名 | 摘要 -->\n", encoding="utf-8")
            elif f.name == "core.md":
                f.write_text("# 潜意识（始终加载）\n\n<!-- 用户身份和核心偏好，每轮对话自动注入 -->\n", encoding="utf-8")
            else:
                f.unlink()


def run_classification_tests():
    print("=" * 60)
    print("  四阁路由机械测试")
    print("=" * 60)

    passed = 0
    failed = 0
    results = []

    for test in ROUTING_TESTS:
        classifications = classify_text(test["text"])
        if test["expected"] is None:
            if not classifications:
                status = "✅ PASS"
                passed += 1
            else:
                got = [c[0] for c in classifications]
                status = f"❌ FAIL — 期望不分流，实际分到 {got}"
                failed += 1
        else:
            pavilion_names = [c[0] for c in classifications]
            if test["expected"] in pavilion_names:
                status = "✅ PASS"
                passed += 1
            else:
                status = f"❌ FAIL — 期望 {test['expected']}，实际 {pavilion_names or '不分流'}"
                failed += 1

        results.append({"name": test["name"], "status": status})
        print(f"  {status}  {test['name']}")

    print(f"\n  结果: {passed}/{passed+failed} 通过")
    return passed, failed, results


def run_write_tests():
    print("\n" + "=" * 60)
    print("  写入 + INDEX更新 测试")
    print("=" * 60)

    reset_pavilions()

    test_cases = [
        ("知识阁", "2025年小规模纳税人增值税起征点调至15万元/月，根据《增值税法》第十二条规定。"),
        ("经验阁", "我们发现做外包项目时，原来按阶段验收比一次性交付更有效，能避免尾款拖延的坑。"),
        ("技能阁", "发票作废流程：第一步，在开票系统找到原发票；第二步，点击作废按钮；第三步，打印作废标记；第四步，留存备查。"),
    ]

    passed = 0
    failed = 0

    for pavilion, content in test_cases:
        filename, action = write_to_pavilion(pavilion, content, "model")

        # 检查文件是否创建
        filepath = PAVILION_DIRS[pavilion] / filename
        file_exists = filepath.exists()

        # 检查INDEX是否更新
        entries = load_index(PAVILION_DIRS[pavilion])
        in_index = any(e["file"] == filename for e in entries)

        if file_exists and in_index:
            print(f"  ✅ PASS  {pavilion}: 文件已创建({filename}), INDEX已更新")
            passed += 1
        else:
            print(f"  ❌ FAIL  {pavilion}: 文件{'存在' if file_exists else '不存在'}, INDEX{'已更新' if in_index else '未更新'}")
            failed += 1

    # 测试记忆阁潜意识写入
    write_to_pavilion("记忆阁", "我是北京的软件公司老板，年营业额200万", "user")
    subconscious = load_subconscious()
    if "北京" in subconscious and "软件" in subconscious:
        print(f"  ✅ PASS  记忆阁→潜意识: core.md已更新")
        passed += 1
    else:
        print(f"  ❌ FAIL  记忆阁→潜意识: core.md未正确写入")
        failed += 1

    # 测试去重
    filename2, action2 = write_to_pavilion("知识阁", "2025年小规模纳税人增值税起征点调至15万元/月，根据最新政策规定。", "model")
    if action2 == "merged":
        print(f"  ✅ PASS  去重机制: 重复内容合并({action2})")
        passed += 1
    else:
        print(f"  ❌ FAIL  去重机制: 期望merged，实际{action2}")
        failed += 1

    print(f"\n  结果: {passed}/{passed+failed} 通过")
    return passed, failed


def run_keyword_tests():
    print("\n" + "=" * 60)
    print("  关键词提取 + 触发词匹配 测试")
    print("=" * 60)

    passed = 0
    failed = 0

    # 先写入一条知识让INDEX有内容
    reset_pavilions()
    write_to_pavilion("知识阁", "2025年增值税起征点调整为15万元/月，小规模纳税人适用。根据《增值税法》规定。", "model")

    # 测试关键词提取
    kws = extract_keywords("小规模纳税人增值税起征点是多少？")
    if any("增值税" in kw or "纳税人" in kw or "起征点" in kw for kw in kws):
        print(f"  ✅ PASS  关键词提取: {kws}")
        passed += 1
    else:
        print(f"  ❌ FAIL  关键词提取: {kws}")
        failed += 1

    # 测试触发词匹配
    matches = match_triggers(kws, "知识阁", KNOWLEDGE_DIR)
    if matches:
        print(f"  ✅ PASS  触发词匹配: 命中{len(matches)}条")
        passed += 1
    else:
        print(f"  ❌ FAIL  触发词匹配: 未命中")
        failed += 1

    # 测试不相关查询不命中
    kws2 = extract_keywords("今天天气怎么样？")
    matches2 = match_triggers(kws2, "知识阁", KNOWLEDGE_DIR)
    if not matches2:
        print(f"  ✅ PASS  不相关查询不命中: 正确")
        passed += 1
    else:
        print(f"  ❌ FAIL  不相关查询误命中: {matches2}")
        failed += 1

    print(f"\n  结果: {passed}/{passed+failed} 通过")
    return passed, failed


def run_all_tests():
    total_passed = 0
    total_failed = 0

    p, f, _ = run_classification_tests()
    total_passed += p
    total_failed += f

    p, f = run_write_tests()
    total_passed += p
    total_failed += f

    p, f = run_keyword_tests()
    total_passed += p
    total_failed += f

    print("\n" + "=" * 60)
    print(f"  总计: {total_passed}/{total_passed+total_failed} 通过")
    if total_failed == 0:
        print("  🎉 全部通过！路由规则就绪。")
    else:
        print(f"  ⚠️ {total_failed}项失败，需要调整规则。")
    print("=" * 60)

    return total_passed, total_failed


if __name__ == "__main__":
    run_all_tests()
