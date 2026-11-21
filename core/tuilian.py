#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""卦际时空推演 tuilian.py —— 「此卦此时此地 → 变卦何时何地」。

把「错卦 / 综卦 / 互卦」与「方圆图坐标 + 历法节气」接起来，形成确定性推演链：

  · 错卦（六爻阴阳全变）= 物极必反、对立转化 —— 对应【何时】：阴阳对转，约半年之隔
  · 综卦（卦象上下颠倒）= 换位再观、反求诸己 —— 对应【何地】：从对立方位重看
  · 互卦（二三四五爻互体）= 事态中段、内部演变 —— 对应【何势】：过程中的变数

全部由卦的二进制结构 + 方圆图坐标 + 辟卦节气【程序精确推算】，无手抄、可校验。
"""
from __future__ import annotations

from xiangshu import (cuo_zong_hu, gua_de, gua_wuxing, gua_fangwei, rows_name,
                      is_xiaoxi)
from fangyuan import xian_tian, fangtu_pos, yuantu_order, xian_fangwei
import jieqi


def _one(no: int) -> dict:
    """单卦的完整时空画像。"""
    j = jieqi.gua_jieqi(no)
    up, down = xian_tian(no)
    row, col = fangtu_pos(no)
    return {
        "gua_no": no, "name": rows_name(no),
        "卦德": gua_de(no), "五行": gua_wuxing(no), "方位": gua_fangwei(no),
        "先天数": f"上{up}下{down}",
        "方图位": f"行{row}列{col}",
        "圆图位": yuantu_order(no),
        "先天方位": xian_fangwei(no),
        "辟卦": j["辟卦"], "月": j["月"], "地支": j["地支"],
        "律吕": j["律吕"], "黄道次": j["黄道次"], "节气": j["节气"],
        "is_xiaoxi": j["is_xiaoxi"],
    }


def _rel_name(no: int) -> str:
    return rows_name(no)


def tuilian(no: int) -> dict:
    """第 no 卦的时空推演链。"""
    rel = cuo_zong_hu(no)
    return {
        "此卦": _one(no),
        "错卦": {**_one(rel["错卦"]),
                 "义": "六爻阴阳全变 · 物极必反、对立转化"},
        "综卦": {**_one(rel["综卦"]),
                 "义": "卦象上下颠倒 · 换位再观、反求诸己"},
        "互卦": {**_one(rel["互卦"]),
                 "义": "二三四五爻互体 · 事态中段、内部演变"},
    }


def tuilian_text(no: int) -> str:
    """推演链 → 可读文本（供 LLM 上下文 / 展示）。"""
    t = tuilian(no)
    lines = []
    cur = t["此卦"]
    lines.append(
        f"【此卦】{cur['name']}（{cur['卦德']}）值 {cur['节气']}（{cur['月']}{cur['地支']}，"
        f"律{cur['律吕']}·{cur['黄道次']}）\n"
        f"  五行{cur['五行']}　方位{cur['方位']}　先天数{cur['先天数']}　"
        f"方图(空间){cur['方图位']}　圆图(时间)第{cur['圆图位']}位　先天方位{cur['先天方位']}")
    for key, label in (("错卦", "变之极"), ("综卦", "反之观"), ("互卦", "中之变")):
        g = t[key]
        lines.append(
            f"【{key}·{label}】{g['name']} —— {g['义']}\n"
            f"  值 {g['节气']}（{g['月']}{g['地支']}）　方位{g['方位']}　"
            f"方图{g['方图位']}　圆图第{g['圆图位']}位　先天方位{g['先天方位']}")
    return "\n\n".join(lines)


def self_check() -> list:
    errs = []
    for no in range(1, 65):
        t = tuilian(no)
        for k in ("此卦", "错卦", "综卦", "互卦"):
            if not t[k]["name"]:
                errs.append(f"卦 {no} 推演缺 {k}")
        # 错卦对偶：此卦的错卦的错卦 = 此卦
        if cuo_zong_hu(cuo_zong_hu(no)["错卦"])["错卦"] != no:
            errs.append(f"错卦对偶失败 @{no}")
    return errs


if __name__ == "__main__":
    errs = self_check()
    if errs:
        print("推演层自检失败：")
        for e in errs:
            print("  -", e)
        raise SystemExit(1)
    print("推演层自检通过：64 卦错/综/互推演链完整")
    print()
    print(tuilian_text(47))   # 困卦
    print()
    print(tuilian_text(24))   # 复卦
