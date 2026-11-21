#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""交叉校验：外部 ZHOUYI 繁体通行本 vs 本仓库 jingwen.py 简体通行本。

【前置条件】此脚本为可选工具，不属于零依赖核心：
  1. 需要第三方包 zhconv：  pip install zhconv
  2. 需要外部参考库 bollwarm/ZHOUYI（Perl，2016 桔子，Perl 同款许可）单独放在
     仓库外的 ../zhouyi-ref/ 目录。出于许可隔离，该库【不在本仓库内】，
     请勿把它复制进 MIT 授权的仓库。
  3. 需要系统安装 Perl 来运行 ZHOUYI.pm。

若只想验证本仓库结构，请直接运行仓库根目录的 `python verify.py`（零依赖）。

对比策略：只提取汉字序列（去掉所有标点/空格），繁转简后逐条比对，
发现错字、漏字、错位。双向互校——两边都可能错，差异点人工判断。
"""
import sys, re
from pathlib import Path

try:
    import zhconv
except ImportError:
    raise SystemExit("缺少 zhconv，请先执行：pip install zhconv（或用 verify.py 做零依赖自检）")

HERE = Path(__file__).parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "core"))
from jingwen import TUAN, YAO  # noqa: E402


def han(s: str) -> str:
    """只保留汉字，去掉标点空格，用于容错比对。"""
    return re.sub(r"[^\u4e00-\u9fff]", "", s)


def parse_zhouyi(pm_path: Path):
    """解析 ZHOUYI.pm 的 __DATA__ 段，返回 {卦号: {name, tuan, yao:[(爻题,爻辞,小象)]}}。"""
    text = pm_path.read_text(encoding="utf-8")
    data = text.split("__DATA__", 1)[1]
    result = {}
    cur_no = None
    cur_yao = None  # 当前爻的临时存储 [爻题, 爻辞, 小象]
    first_xiang_done = False  # 大象是否已过

    yao_pat = re.compile(r"^(初[九六]|[九六][二三四五]|上[九六]|用[九六])[:：](.*)$")

    for raw in data.splitlines():
        line = raw.strip()
        if not line:
            continue
        # 卦标题：《易經》第一卦乾 乾為天 乾上乾下
        m = re.match(r"^《易經》第([一二三四五六七八九十]+)卦(.+)", line)
        if m:
            cur_no = cn_num(m.group(1))
            name = m.group(2).strip()[0]  # 第一个字即卦名
            result[cur_no] = {"name": name, "tuan": "", "yao": []}
            cur_yao = None
            first_xiang_done = False
            continue
        if cur_no is None:
            continue
        g = result[cur_no]
        # 彖传
        if line.startswith("《彖》曰"):
            g["tuan"] = zhconv.convert(line.split("曰", 1)[1].strip(), "zh-cn")
            continue
        # 文言（仅乾坤），跳过后续直到下一卦
        if line.startswith("《文言》曰"):
            cur_yao = None
            continue
        # 象曰：区分大象（第一条，无爻辞）与小象（归属当前爻）
        if line.startswith("《象》曰"):
            xiang = zhconv.convert(line.split("曰", 1)[1].strip(), "zh-cn")
            if cur_yao is not None and not first_xiang_done:
                # 这条其实是大象（卦辞后的第一条象，还没遇到爻辞）
                first_xiang_done = True
            elif cur_yao is not None:
                cur_yao[2] = xiang  # 小象
            continue
        # 爻辞
        m = yao_pat.match(line)
        if m:
            title = m.group(1)
            ci = zhconv.convert(m.group(2).strip(), "zh-cn")
            cur_yao = [title, ci, ""]
            g["yao"].append(cur_yao)
            first_xiang_done = True
            continue
        # 卦辞（卦名开头的行），忽略
        continue
    return result


def cn_num(s: str) -> int:
    """中文数字转 int（一到六十四）。"""
    nums = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6,
            "七": 7, "八": 8, "九": 9, "十": 10}
    s = s.strip()
    if s in nums:
        return nums[s]
    if "十" in s:
        parts = s.split("十")
        tens = nums.get(parts[0], 1) * 10
        ones = nums.get(parts[1], 0) if len(parts) > 1 and parts[1] else 0
        return tens + ones
    return 0


def main():
    import os
    # 外部参考库不在本仓库内；默认在仓库同级的 ../zhouyi-ref/，
    # 也可用 ZHOUYI_PM 环境变量指向任意位置的 ZHOUYI.pm。
    pm = Path(os.getenv("ZHOUYI_PM", str(ROOT.parent / "zhouyi-ref" / "lib" / "ZHOUYI.pm")))
    if not pm.exists():
        print(f"找不到 ZHOUYI.pm：{pm}")
        print("请用 ZHOUYI_PM=/path/to/ZHOUYI.pm 指定，或参见本文件顶部说明。")
        return 1
    ref = parse_zhouyi(pm)
    print(f"ZHOUYI 解析出 {len(ref)} 卦")

    diff_count = 0
    report = []

    # 彖传对比
    for no in range(1, 65):
        r = ref.get(no)
        if not r:
            report.append(f"[缺] ZHOUYI 无第{no}卦")
            diff_count += 1
            continue
        ours = TUAN.get(no, "")
        ref_tuan = r["tuan"]
        if han(ours) != han(ref_tuan):
            diff_count += 1
            report.append(f"[彖传-第{no}卦{ours and ref.get('name')}]")
            report.append(f"   我们: {ours}")
            report.append(f"   ZHOUYI: {ref_tuan}")

    # 爻辞对比
    for no in range(1, 65):
        r = ref.get(no)
        if not r:
            continue
        ours_yao = YAO.get(no, [])
        ref_yao = r["yao"]
        if len(ours_yao) != len(ref_yao):
            diff_count += 1
            report.append(f"[爻数-第{no}卦] 我们{len(ours_yao)} vs ZHOUYI {len(ref_yao)}")
        for i, (ot, oc, ox) in enumerate(ours_yao):
            if i >= len(ref_yao):
                diff_count += 1
                report.append(f"[爻-第{no}卦] 我们多出 {ot}:{oc}")
                continue
            rt, rc, rx = ref_yao[i]
            if ot != rt:
                diff_count += 1
                report.append(f"[爻题-第{no}卦第{i+1}爻] {ot} vs {rt}")
            if han(oc) != han(rc):
                diff_count += 1
                report.append(f"[爻辞-第{no}卦{ot}]")
                report.append(f"   我们: {oc}")
                report.append(f"   ZHOUYI: {rc}")
            if han(ox) != han(rx):
                diff_count += 1
                report.append(f"[小象-第{no}卦{ot}]")
                report.append(f"   我们: {ox}")
                report.append(f"   ZHOUYI: {rx}")

    print("=" * 60)
    if diff_count == 0:
        print("✅ 全部一致（彖传64 + 爻辞386 + 小象384 逐字吻合）")
    else:
        print(f"⚠️ 共 {diff_count} 处差异：")
        for line in report:
            print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
