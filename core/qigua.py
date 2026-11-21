#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""时间起卦层 —— 梅花易数数字起卦 + 时令卦（节气→辟卦）。

复用已有模块（零新依赖）：
  · fangyuan.gua_no_by_fangtu / XIAN_TIAN_NAME —— 先天卦数（乾1兑2…坤8）
  · xiangshu.hex_from_bottom / _gua_no_by_hex —— 爻变推算（变卦）
  · jieqi.JIEQI / XIAOXI_BY_NAME / jieqi_of_date —— 节气→十二辟卦

两种起卦：
  1) 梅花易数时间起卦：年月日时 → 上卦/下卦 → 动爻 → 本卦 + 变卦
  2) 时令卦：公历日期 → 节气 → 十二消息辟卦（此刻天地气运）

用法：
  python qigua.py            # 自检 + 用当前时间演示两种起卦
"""
from __future__ import annotations

from fangyuan import gua_no_by_fangtu, XIAN_TIAN_NAME
from xiangshu import hex_from_bottom, _gua_no_by_hex, rows_name
from jieqi import JIEQI, XIAOXI_BY_NAME, jieqi_of_date

# 节气名 → (节气, 黄经, 日期, 地支, 辟卦名, 三候)
_JIEQI_BY_NAME = {x[0]: x for x in JIEQI}


def shi_num(hour: int) -> int:
    """时辰序：子1 丑2 … 亥12（每时辰2小时，子时 23:00-00:59）。"""
    return ((hour + 1) % 24) // 2 + 1


def meihua_qigua(year: int, month: int, day: int, hour: int) -> dict:
    """梅花易数时间起卦（公历数字起卦，梅花易数之变通法）。

    上卦 = (年+月+日) 除 8 取余；下卦 = (年+月+日+时) 除 8 取余；
    动爻 = (年+月+日+时) 除 6 取余（余 0 取 6 / 8）。
    传统梅花用农历年月日 + 地支年序；此处用公历数字，零农历依赖。
    """
    shi = shi_num(hour)
    up_num = (year + month + day) % 8 or 8
    down_num = (year + month + day + shi) % 8 or 8
    dong = (year + month + day + shi) % 6 or 6

    ben = gua_no_by_fangtu(row=down_num, col=up_num)   # row=下卦先天数, col=上卦先天数
    h = list(hex_from_bottom(ben))                     # 六爻从下往上
    h[dong - 1] = 1 - h[dong - 1]                      # 动爻阴阳互变
    bian = _gua_no_by_hex(tuple(h))

    return {
        "起卦": f"{year}年{month}月{day}日 时数{shi}",
        "上卦": XIAN_TIAN_NAME.get(up_num, "?"),
        "下卦": XIAN_TIAN_NAME.get(down_num, "?"),
        "动爻": dong,
        "本卦": ben, "本卦名": rows_name(ben),
        "变卦": bian, "变卦名": rows_name(bian),
    }


def shiling_gua(month: int, day: int) -> dict:
    """时令卦：公历日期 → 节气 → 十二消息辟卦（天地气运）。"""
    jq = jieqi_of_date(month, day)
    info = _JIEQI_BY_NAME.get(jq)
    pigua_name = info[4] if info else ""
    xiao = XIAOXI_BY_NAME.get(pigua_name)
    return {
        "节气": jq,
        "三候": info[5] if info else [],
        "辟卦": pigua_name,
        "辟卦号": xiao[1] if xiao else 0,
        "月": xiao[2] if xiao else "",
        "地支": xiao[3] if xiao else "",
        "律吕": xiao[4] if xiao else "",
        "黄道次": xiao[5] if xiao else "",
    }


# ============================================================ 自检
def self_check() -> list:
    errs = []
    if [shi_num(h) for h in (23, 0, 1, 2, 22)] != [1, 1, 2, 2, 12]:
        errs.append(f"时辰序错误：{[shi_num(h) for h in (23,0,1,2,22)]}")
    r = meihua_qigua(2026, 11, 10, 10)
    if not (1 <= r["本卦"] <= 64 and 1 <= r["变卦"] <= 64 and 1 <= r["动爻"] <= 6):
        errs.append(f"梅花起卦非法：{r}")
    # 变卦 = 本卦动爻互变，重算校验
    h = list(hex_from_bottom(r["本卦"]))
    h[r["动爻"] - 1] = 1 - h[r["动爻"] - 1]
    if _gua_no_by_hex(tuple(h)) != r["变卦"]:
        errs.append("变卦推算不一致")
    s = shiling_gua(11, 10)
    if not s["辟卦"] or not s["节气"]:
        errs.append(f"时令卦空：{s}")
    # 关键锚点：冬至=复、夏至=姤、立春=泰
    anchors = {(12, 22): "复", (6, 21): "姤", (2, 4): "泰"}
    for (m, d), want in anchors.items():
        got = shiling_gua(m, d)["辟卦"]
        if got != want:
            errs.append(f"时令锚点 ({m},{d}) 应 {want} 实得 {got}")
    return errs


if __name__ == "__main__":
    errs = self_check()
    if errs:
        print("自检失败：")
        for e in errs:
            print("  -", e)
        raise SystemExit(1)
    print("时间起卦层自检通过（时辰序 / 梅花起卦 / 变卦推算 / 时令锚点 全对）")

    import datetime
    now = datetime.datetime.now()
    m = meihua_qigua(now.year, now.month, now.day, now.hour)
    s = shiling_gua(now.month, now.day)
    print(f"\n【梅花时间起卦】{m['起卦']}")
    print(f"  上卦{m['上卦']} · 下卦{m['下卦']} · 动爻第{m['动爻']}爻")
    print(f"  本卦【{m['本卦名']}】 → 变卦【{m['变卦名']}】")
    print(f"\n【时令卦】{s['节气']} → 辟卦【{s['辟卦']}】（{s['月']}·{s['地支']}·{s['律吕']}·{s['黄道次']}）")
    print(f"  三候：{'、'.join(s['三候'])}")
