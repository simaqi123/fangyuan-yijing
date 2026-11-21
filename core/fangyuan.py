#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""先天六十四卦方圆图 · 时空坐标层（地基深挖 · 第三层）。

思想来源：《周易·系辞传》「天地定位，山泽通气，雷风相薄，水火不相射」
           + 邵雍《皇极经世》先天方圆图。
已学习微信文章《核心干货：一文彻底搞懂六十四卦方圆图》（北冥宏元堂）并程序化落地。

核心义理（文章 + 象数传统）：
  · 方图 = 管【空间 / 方位】；圆图 = 管【时间 / 时序】
  · 天地定位：乾在上、坤在下（圆图乾居最上、坤居最下）
  · 先天八卦数：乾1 兑2 离3 震4 巽5 坎6 艮7 坤8
  · 方图 8×8：行 = 下卦先天数（从下往上 1→8），列 = 上卦先天数（从右往左 1→8），
              「乾」居右下角（乾上乾下）
  · 圆图序：按方图「下卦行序 1→8、每行内上卦列序 1→8」读出，即天道左旋，
             乾=1 → 坤=64，一卦一个圆周位置
  · 阴阳二气转化：圆图左右半圆方向相反（左顺右逆），即一阴一阳之谓道

本模块与前两层的关系：
  · gua64.py  = 经文本体（卦辞/彖/大象/核心义/现代语义）
  · xiangshu.py = 象数结构（错综互卦/卦德/五行/后天方位/消息卦）
  · 本模块   = 时空坐标（先天数/方图空间位/圆图时间位/先天方位）

全部由卦的上下卦结构【程序精确推算】，并内置邵雍标准圆图卦序作防错锚点，
因此绝对准确、可校验。
"""
from __future__ import annotations

from gua64 import GUA64, _norm_trigram

# ============================================================ 先天八卦数
# 邵雍先天序：乾一、兑二、离三、震四、巽五、坎六、艮七、坤八
XIAN_TIAN_NUM = {
    '乾': 1, '兑': 2, '离': 3, '震': 4,
    '巽': 5, '坎': 6, '艮': 7, '坤': 8,
}
XIAN_TIAN_NAME = {v: k for k, v in XIAN_TIAN_NUM.items()}

# 先天八卦方位（邵雍先天图：乾坤定上下、离坎列左右）
# 乾南 坤北 离东 坎西 兑东南 震东北 巽西南 艮西北
XIAN_TIAN_FANGWEI = {
    '乾': '南', '坤': '北', '离': '东', '坎': '西',
    '兑': '东南', '震': '东北', '巽': '西南', '艮': '西北',
}

# ============================================================ 防错锚点
# 邵雍标准「先天六十四卦圆图」卦序（从乾起，逆时针一周，坤收尾）。
# 这张表是权威锚点 —— 程序推算出的圆图序必须与之逐位一致。
YUAN_TU_NAMES = [
    '乾', '夬', '大有', '大壮', '小畜', '需', '大畜', '泰',
    '履', '兑', '睽', '归妹', '中孚', '节', '损', '临',
    '同人', '革', '离', '丰', '家人', '既济', '贲', '明夷',
    '无妄', '随', '噬嗑', '震', '益', '屯', '颐', '复',
    '姤', '大过', '鼎', '恒', '巽', '井', '蛊', '升',
    '讼', '困', '未济', '解', '涣', '坎', '蒙', '师',
    '遁', '咸', '旅', '小过', '渐', '蹇', '艮', '谦',
    '否', '萃', '晋', '豫', '观', '比', '剥', '坤',
]


# ============================================================ 结构推算
def _row(no: int) -> dict:
    """取第 no 卦的上下卦（no 为通行本卦序，1 基）。"""
    _, name, up, down, *_ = GUA64[no - 1]
    return {'gua_no': no, 'name': name,
            'up_trigram': _norm_trigram(up), 'down_trigram': _norm_trigram(down)}


def xian_tian(no: int) -> tuple:
    """返回 (上卦先天数, 下卦先天数)。"""
    r = _row(no)
    return XIAN_TIAN_NUM[r['up_trigram']], XIAN_TIAN_NUM[r['down_trigram']]


def fangtu_pos(no: int) -> tuple:
    """方图坐标 (row, col)：
    row = 下卦先天数（从下往上 1→8，乾在底）
    col = 上卦先天数（从右往左 1→8，乾在右）
    「乾」= (1,1) 居右下角；「坤」= (8,8) 居左上角。
    """
    up_num, down_num = xian_tian(no)
    return down_num, up_num


def yuantu_order(no: int) -> int:
    """圆图时序（1..64）：按方图行序 1→8、每行内列序 1→8 读出。
    乾=1 → 坤=64，一卦一个圆周位置（天道左旋）。
    """
    row, col = fangtu_pos(no)
    return (row - 1) * 8 + col


def xian_fangwei(no: int) -> str:
    """先天方位：上卦先天方位·下卦先天方位。"""
    r = _row(no)
    return f"{XIAN_TIAN_FANGWEI[r['up_trigram']]}·{XIAN_TIAN_FANGWEI[r['down_trigram']]}"


def gua_no_by_fangtu(row: int, col: int) -> int:
    """由方图坐标反查卦号（row/col 均为 1..8）。"""
    for no in range(1, 65):
        r, c = fangtu_pos(no)
        if r == row and c == col:
            return no
    return 0


def all_gua_fangyuan() -> list:
    """产出全部 64 卦的方圆图行（供建表）。"""
    out = []
    for no in range(1, 65):
        r = _row(no)
        up_num, down_num = xian_tian(no)
        row, col = fangtu_pos(no)
        out.append({
            'gua_no': no,
            'name': r['name'],
            'up_trigram': r['up_trigram'],
            'down_trigram': r['down_trigram'],
            'xian_up': up_num,          # 上卦先天数
            'xian_down': down_num,      # 下卦先天数
            'fang_row': row,            # 方图行（空间位·下卦）
            'fang_col': col,            # 方图列（空间位·上卦）
            'yuantu_order': yuantu_order(no),   # 圆图时序（时间位）
            'xian_fangwei': xian_fangwei(no),   # 先天方位
        })
    return out


# ============================================================ 自检
def self_check() -> list:
    """方圆图自检：
    1. 方图坐标 8×8 恰覆盖 64 卦，无重复无遗漏
    2. 圆图序 1..64 恰覆盖，无重复无遗漏
    3. 推算的圆图卦序与邵雍标准序逐位一致（防错锚点）
    4. 乾=圆图1、坤=圆图64、天地定位（泰/否对角）
    """
    errs = []
    rows = all_gua_fangyuan()

    # 1) 方图坐标覆盖
    cells = {(r['fang_row'], r['fang_col']) for r in rows}
    full = {(i, j) for i in range(1, 9) for j in range(1, 9)}
    if cells != full:
        errs.append(f"方图坐标未满覆盖：缺 {full - cells} 多 {cells - full}")

    # 2) 圆图序覆盖
    orders = [r['yuantu_order'] for r in rows]
    if sorted(orders) != list(range(1, 65)):
        errs.append("圆图序未覆盖 1..64")

    # 3) 与邵雍标准序逐位一致
    by_order = {r['yuantu_order']: r['name'] for r in rows}
    for i, std_name in enumerate(YUAN_TU_NAMES, start=1):
        if by_order.get(i) != std_name:
            errs.append(f"圆图序 @{i} 应为 {std_name}，实得 {by_order.get(i)}")
            break

    # 4) 天地定位
    by_name = {r['name']: r for r in rows}
    if by_name['乾']['yuantu_order'] != 1:
        errs.append("乾不应在圆图第1位")
    if by_name['坤']['yuantu_order'] != 64:
        errs.append("坤不应在圆图第64位")
    if by_name['泰']['fang_row'] != 1 or by_name['泰']['fang_col'] != 8:
        errs.append("泰应居方图右下角一行末（地天交）")
    if by_name['否']['fang_row'] != 8 or by_name['否']['fang_col'] != 1:
        errs.append("否应居方图左上角一列首（天地不交）")

    # 5) 先天数合法性
    for r in rows:
        if not (1 <= r['xian_up'] <= 8 and 1 <= r['xian_down'] <= 8):
            errs.append(f"先天数越界 @{r['name']}")
    return errs


def rows_name(no: int) -> str:
    return _row(no)['name']


if __name__ == '__main__':
    errs = self_check()
    if errs:
        print("方圆图自检失败：")
        for e in errs:
            print("  -", e)
        raise SystemExit(1)
    print("方圆图自检通过：方图 8×8 满覆盖、圆图序 1..64 满覆盖、与邵雍标准序逐位一致")
    print()
    for no in (1, 2, 11, 12, 24, 63, 64):
        r = _row(no)
        up_num, down_num = xian_tian(no)
        row, col = fangtu_pos(no)
        print(f"{no:>2} {r['name']:<3} 上{r['up_trigram']}{up_num} 下{r['down_trigram']}{down_num}  "
              f"方图(行{row},列{col})  圆图第{yuantu_order(no):>2}位  先天方位{xian_fangwei(no)}")
