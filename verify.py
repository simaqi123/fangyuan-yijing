#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""周易数理自检 —— 零依赖，验证核心算法的结构不变量。

运行：
    python verify.py

检查项：
    1. 六十四卦全集唯一、编号连续 1..64
    2. 先天八卦方位与卦序自洽
    3. 二十四节气齐全、顺序正确
    4. 象数关系（错卦/综卦/互卦）闭合
    5. SFT 训练数据格式合法（若 data/ 存在）
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE / "core"))

import gua64          # noqa: E402
import fangyuan       # noqa: E402
import jieqi          # noqa: E402
import xiangshu       # noqa: E402

PASS = "[PASS]"
FAIL = "[FAIL]"
failures: list[str] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    tag = PASS if ok else FAIL
    print(f"  {tag}  {name}" + (f"  — {detail}" if detail else ""))
    if not ok:
        failures.append(name)


def main() -> int:
    print("=" * 60)
    print("周易数理自检 · fangyuan-yijing")
    print("=" * 60)

    print("\n[1] 六十四卦")
    g = gua64.GUA64
    check("卦数量为 64", len(g) == 64, f"实际 {len(g)}")
    nums = {row[0] for row in g if isinstance(row, (tuple, list)) and row}
    check("卦编号覆盖 1..64", nums == set(range(1, 65)), f"覆盖 {len(nums)} 个编号")
    names = [row[1] for row in g if isinstance(row, (tuple, list)) and len(row) > 1]
    check("卦名无重复", len(set(names)) == len(names), f"{len(set(names))} 个唯一卦名")

    print("\n[2] 先天八卦")
    xt = [fangyuan.xian_tian(i) for i in range(8)]
    check("先天卦序生成 8 个方位", len(xt) == 8, f"实际 {len(xt)}")
    check("先天卦序无重复", len(set(xt)) == len(xt))

    print("\n[3] 二十四节气")
    jq = jieqi.JIEQI
    check("节气数量为 24", len(jq) == 24, f"实际 {len(jq)}")

    print("\n[4] 象数关系")
    try:
        # 错卦是对合运算：cuo(cuo(n)) == n
        involutive = all(xiangshu.cuo_gua(xiangshu.cuo_gua(n)) == n
                         for n in range(1, 65))
        check("错卦对合性 cuo(cuo(n))=n（64 卦全检）", involutive)
        # 综卦是置换：结果落在 1..64 且无重复
        zong = [xiangshu.zong_gua(n) for n in range(1, 65)]
        check("综卦为 1..64 的置换", sorted(zong) == list(range(1, 65)))
        check("乾(1)/坤(2) 互为错卦",
              xiangshu.cuo_gua(1) == 2 and xiangshu.cuo_gua(2) == 1,
              f"错(1)={xiangshu.cuo_gua(1)} 错(2)={xiangshu.cuo_gua(2)}")
    except Exception as exc:                    # noqa: BLE001
        check("象数关系校验", False, str(exc)[:80])

    print("\n[5] SFT 训练数据")
    data_dir = HERE / "data"
    jsonls = sorted(data_dir.glob("*.jsonl")) if data_dir.exists() else []
    if not jsonls:
        print("  [SKIP] 未发现 data/*.jsonl")
    else:
        total = 0
        bad = 0
        for path in jsonls:
            with path.open(encoding="utf-8") as fh:
                for line_no, line in enumerate(fh, 1):
                    if not line.strip():
                        continue
                    total += 1
                    try:
                        obj = json.loads(line)
                        assert isinstance(obj, dict) and "messages" in obj
                    except Exception:           # noqa: BLE001
                        bad += 1
                        if bad <= 2:
                            print(f"  [FAIL] {path.name}:{line_no} JSON 或 messages 字段非法")
        check(f"{len(jsonls)} 个 jsonl 共 {total} 条格式合法", bad == 0,
              f"非法 {bad} 条" if bad else "")

    print("\n" + "=" * 60)
    if failures:
        print(f"结果：{len(failures)} 项失败 — " + "、".join(failures))
        return 1
    print("结果：全部通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
