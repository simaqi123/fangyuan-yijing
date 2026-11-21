#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""六十四卦 · 象数推算层（地基深挖 · 第一层）。

与 gua64.py（文本骨架）互补：gua64.py 管「经文本体」，本模块管「象数结构」。
象数结构全部由卦的六爻二进制结构【程序精确推算】，不依赖任何手抄文本，
因此绝对准确、可校验——这是"地基牢"的根本保证。

推算依据（《周易》通行象数体系）：
  · 六爻位次：从下往上 = 初、二、三、四、五、上
  · 下卦 = 初/二/三爻；上卦 = 四/五/上爻
  · 爻性：阳爻称"九"，阴爻称"六"
  · 错卦（变卦）：六爻阴阳全变        —— 二进制逐位取反
  · 综卦（覆卦）：卦象上下颠倒        —— 二进制逆序
  · 互卦（中爻）：二三四爻为下卦、三四五爻为上卦
  · 卦德：八经卦之德（乾健坤顺震动巽入坎陷离丽艮止兑说）
  · 五行：八卦配五行（乾兑金、离火、震巽木、坎水、艮坤土）
  · 方位：后天八卦（离南坎北震东兑西巽东南艮东北乾西北坤西南）
  · 消息：十二辟卦（阴阳消长，配十二月）
"""
from __future__ import annotations

from gua64 import TRIGRAM, GUA64, _norm_trigram

# ============================================================ 八经卦象数
# 卦德（说卦传：乾健、坤顺、震动、巽入、坎陷、离丽、艮止、兑说）
BAGUA_DE = {
    '乾': '健', '坤': '顺', '震': '动', '巽': '入',
    '坎': '陷', '离': '丽', '艮': '止', '兑': '说',
}
BAGUA_DE_FULL = {
    '乾': '刚健', '坤': '柔顺', '震': '震动奋起', '巽': '谦顺渗透',
    '坎': '险陷', '离': '附丽光明', '艮': '静止节制', '兑': '和悦',
}
# 八卦配五行
BAGUA_WUXING = {
    '乾': '金', '兑': '金', '离': '火', '震': '木',
    '巽': '木', '坎': '水', '艮': '土', '坤': '土',
}
# 后天八卦方位（文王八卦）
BAGUA_FANGWEI = {
    '离': '南', '坎': '北', '震': '东', '兑': '西',
    '巽': '东南', '艮': '东北', '坤': '西南', '乾': '西北',
}
# 八卦配人伦（说卦传：乾坤六子）
BAGUA_REN = {
    '乾': '父', '坤': '母', '震': '长男', '巽': '长女',
    '坎': '中男', '离': '中女', '艮': '少男', '兑': '少女',
}
# 八卦配动物（说卦传）
BAGUA_ANIMAL = {
    '乾': '马', '坤': '牛', '震': '龙', '巽': '鸡',
    '坎': '豕', '离': '雉', '艮': '狗', '兑': '羊',
}
# 八卦配身体（说卦传：近取诸身）
BAGUA_BODY = {
    '乾': '首', '坤': '腹', '震': '足', '巽': '股',
    '坎': '耳', '离': '目', '艮': '手', '兑': '口',
}

# 十二消息卦（十二辟卦）：(卦号, 卦名, 月建, 地支, 节气)
SHIERY_XIAOXI = [
    (24, '复', '十一月', '子', '冬至'),
    (19, '临', '十二月', '丑', '大寒'),
    (11, '泰', '正月', '寅', '雨水'),
    (34, '大壮', '二月', '卯', '春分'),
    (43, '夬', '三月', '辰', '谷雨'),
    (1, '乾', '四月', '巳', '小满'),
    (44, '姤', '五月', '午', '夏至'),
    (33, '遁', '六月', '未', '大暑'),
    (12, '否', '七月', '申', '处暑'),
    (20, '观', '八月', '酉', '秋分'),
    (23, '剥', '九月', '戌', '霜降'),
    (2, '坤', '十月', '亥', '小雪'),
]


# ============================================================ 结构推算
def _row(no: int) -> dict:
    """取第 no 卦的行数据（no 为通行本卦序，1 基）。"""
    return gua_rows_index()[no - 1]


def gua_rows_index() -> list:
    """规范化后的 64 卦行（gua64.gua_rows() 的缓存版）。"""
    from gua64 import gua_rows
    return gua_rows()


def hex_from_bottom(no: int) -> tuple:
    """返回第 no 卦六爻（从下往上：初、二、三、四、五、上），1=阳 0=阴。

    这是象数推算的唯一权威坐标 —— 一切错/综/互卦都从这里推出。
    """
    r = _row(no)
    up, down = r['up_trigram'], r['down_trigram']
    u = TRIGRAM[up][2]   # (初,二,三) 从下往上
    d = TRIGRAM[down][2]
    # 从下往上：下卦初二三 + 上卦四五上
    return (d[0], d[1], d[2], u[0], u[1], u[2])


def _gua_no_by_hex(h: tuple) -> int:
    """由六爻（从下往上）反查卦号。用于错/综/互卦落位。"""
    # 先找上下卦名
    d = _trigram_name(h[0:3])   # 下卦
    u = _trigram_name(h[3:6])   # 上卦
    for r in gua_rows_index():
        if r['up_trigram'] == u and r['down_trigram'] == d:
            return r['gua_no']
    # 找不到时（互卦可能不是通行本上下卦名直接对应？不会，互卦必是八卦之一）
    return 0


def _trigram_name(bits: tuple) -> str:
    """三爻（从下往上）→ 卦名。"""
    for name, (_, _, b) in TRIGRAM.items():
        if b == bits:
            return name
    return ''


def cuo_gua(no: int) -> int:
    """错卦（变卦）：六爻阴阳全变。"""
    h = hex_from_bottom(no)
    return _gua_no_by_hex(tuple(1 - x for x in h))


def zong_gua(no: int) -> int:
    """综卦（覆卦）：卦象上下颠倒。"""
    h = hex_from_bottom(no)
    return _gua_no_by_hex(tuple(reversed(h)))


def hu_gua(no: int) -> int:
    """互卦（中爻卦）：二三四爻为下互、三四五爻为上互，下互在下、上互在上。

    权威定义：取原卦的二、三、四爻为「下互卦」，三、四、五爻为「上互卦」，
    合成新卦时下互在下、上互在上。
    例：屯(下震上坎)=100010，二三四=000(坤)、三四五=001(艮)，
        互卦=坤下艮上=剥卦。
    """
    h = hex_from_bottom(no)  # (初,二,三,四,五,上)
    down = h[1:4]            # 二、三、四 → 下互
    up = h[2:5]              # 三、四、五 → 上互
    return _gua_no_by_hex(down + up)  # 下互+上互 → 下互在下、上互在上


def cuo_zong_hu(no: int) -> dict:
    """一卦的完整象数关系：错卦 / 综卦 / 互卦。"""
    return {
        '错卦': cuo_gua(no),
        '综卦': zong_gua(no),
        '互卦': hu_gua(no),
    }


def yao_lines(no: int) -> list:
    """第 no 卦六爻的爻题（从下往上）：初九/九二/…/上九 或 初六/六二/…/上六。"""
    h = hex_from_bottom(no)
    pos = ['初', '二', '三', '四', '五', '上']
    out = []
    for i, bit in enumerate(h):
        if i == 0 or i == 5:
            # 初爻、上爻：位置字在前
            out.append(f"{pos[i]}{'九' if bit else '六'}")
        else:
            out.append(f"{'九' if bit else '六'}{pos[i]}")
    return out


def gua_de(no: int) -> str:
    """六十四卦卦德：上卦德 + 下卦德（内卦在下、外卦在上）。"""
    r = _row(no)
    up, down = r['up_trigram'], r['down_trigram']
    return f"{BAGUA_DE[up]}·{BAGUA_DE[down]}"


def gua_wuxing(no: int) -> str:
    """卦配五行：上卦五行 + 下卦五行。"""
    r = _row(no)
    up, down = r['up_trigram'], r['down_trigram']
    return f"{BAGUA_WUXING[up]}{BAGUA_WUXING[down]}"


def gua_fangwei(no: int) -> str:
    """卦方位（取上下卦后天方位）。"""
    r = _row(no)
    up, down = r['up_trigram'], r['down_trigram']
    return f"{BAGUA_FANGWEI[up]}·{BAGUA_FANGWEI[down]}"


def is_xiaoxi(no: int) -> str:
    """是否十二消息卦，是则返回月建，否则空串。"""
    for gno, name, month, zhi, jieqi in SHIERY_XIAOXI:
        if gno == no:
            return f"{month}({zhi})·{jieqi}"
    return ''


def all_gua_xiangshu() -> list:
    """产出全部 64 卦的象数行（供建表）。"""
    from gua64 import anchor_text
    out = []
    for no in range(1, 65):
        r = _row(no)
        h = hex_from_bottom(no)
        rel = cuo_zong_hu(no)
        out.append({
            'gua_no': no,
            'name': r['name'],
            'symbol': r['symbol'],
            'binary_from_bottom': ''.join(map(str, h)),
            'gua_de': gua_de(no),
            'wuxing': gua_wuxing(no),
            'fangwei': gua_fangwei(no),
            'renlun': f"{BAGUA_REN[r['up_trigram']]}·{BAGUA_REN[r['down_trigram']]}",
            'cuo': rel['错卦'], 'zong': rel['综卦'], 'hu': rel['互卦'],
            'xiaoxi': is_xiaoxi(no),
            'yao_titles': ' '.join(yao_lines(no)),
        })
    return out


# ============================================================ 自检
def self_check() -> list:
    """象数层自检：错卦对偶、综卦对偶、互卦合法、64 卦齐全。"""
    errs = []
    rows = {r['gua_no']: r['name'] for r in gua_rows_index()}
    if len(rows) != 64:
        errs.append(f"卦数 != 64: {len(rows)}")
    for no in range(1, 65):
        # 错卦：两次取反回自身
        if cuo_gua(cuo_gua(no)) != no:
            errs.append(f"错卦对偶失败 @{no}")
        # 综卦：两次颠倒回自身
        if zong_gua(zong_gua(no)) != no:
            errs.append(f"综卦对偶失败 @{no}")
        # 互卦必须落在 1..64
        if not (1 <= hu_gua(no) <= 64):
            errs.append(f"互卦越界 @{no}")
        # 爻题 6 个
        if len(yao_lines(no)) != 6:
            errs.append(f"爻题数量 != 6 @{no}")
    # 十二消息卦应恰 12 个
    xs = [g for g, *_ in SHIERY_XIAOXI]
    if len(set(xs)) != 12:
        errs.append("消息卦 != 12")
    return errs


def rows_name(no: int) -> str:
    rows = {r['gua_no']: r['name'] for r in gua_rows_index()}
    return rows.get(no, f"?{no}")


if __name__ == '__main__':
    errs = self_check()
    if errs:
        print("自检失败：")
        for e in errs:
            print("  -", e)
        raise SystemExit(1)
    print("象数层自检通过：错/综卦对偶成立、互卦合法、384 爻题齐全")
    for no in (1, 2, 11, 12, 24, 63, 64):
        r = _row(no)
        rel = cuo_zong_hu(no)
        print(f"\n{no:>2} {r['name']} {r['symbol']}  hex={''.join(map(str,hex_from_bottom(no)))}")
        print(f"    卦德={gua_de(no)}  五行={gua_wuxing(no)}  方位={gua_fangwei(no)}  "
              f"消息={is_xiaoxi(no) or '-'}")
        print(f"    错卦={rows_name(rel['错卦'])}  综卦={rows_name(rel['综卦'])}  "
              f"互卦={rows_name(rel['互卦'])}")
        print(f"    爻题={' '.join(yao_lines(no))}")
