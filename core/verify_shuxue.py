#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""数理严格验证：六十四卦 = 六维超立方体 MoE 的核心命题。

这不是"跑通就完事"的 POC 自检，而是把「六十四卦即 64 顶点」这个核心论断
拆成一组【可执行数学断言】，每条都能被独立证伪。
全部通过 = 数理上站得住；任何一条失败 = 方案存在数理漏洞，需先修再谈训练。

命题清单（每条都能被独立证伪）：
  P1  双射同构：64 卦六爻 = {0,1}^6 全集（无重复、无遗漏）
  P2  错卦 = 对径点：embed(错卦) = -embed(本卦)
  P3  动爻 = 相邻顶点：变任意一爻 → 汉明距离恰 = 1，6 邻居唯一
  P4  综卦 = 镜像：爻序反转
  P5  点积-距离线性律：dot = 6 - 2·hamming（亲疏完全由距离决定）
  P6  路由自命中：低温下 top1 必命中自身
  P7  错卦权重最小：对径点在 softmax 中权重全局最小
  P8  路由归一化：softmax 全量权重和 = 1
  P9  对径配对：{卦,错卦} 恰构成 32 个不相交对
  P10 超立方体图：每顶点恰 6 邻居，边双向对称（总 192 边）
  P11 度分布 = 二项式：与某卦距离 k 的卦数恰 = C(6,k)
  P12 结构先验可达：存在嵌入使"对径反号/相邻正相关"损失=0（非病态）
"""
from __future__ import annotations
import math

from xiangshu import hex_from_bottom, cuo_gua, zong_gua, hu_gua, rows_name
from gua_moe import embed, hamming, dot, gua_router

# 六爻 → 卦号 映射（P1 通过后即为 64 条满射）
HEX_TO_NO = {hex_from_bottom(no): no for no in range(1, 65)}


# ============================================================ 命题断言
def P1_bijection() -> str | None:
    """64 卦六爻 = {0,1}^6 全集（双射同构的根基）。"""
    if len(HEX_TO_NO) != 64:
        return f"六爻组合数 != 64：{len(HEX_TO_NO)}"
    full = {tuple((k >> i) & 1 for i in range(6)) for k in range(64)}
    missing = full - set(HEX_TO_NO)
    if missing:
        return f"{0, 1}^6 缺失 {len(missing)} 个顶点：{sorted(missing)[:5]}…"
    # 反向：每个六爻都能反查到唯一卦号
    for no in range(1, 65):
        if HEX_TO_NO[hex_from_bottom(no)] != no:
            return f"卦{no} 六爻反查不一致"
    return None


def P2_antipodal() -> str | None:
    """错卦 = 对径点：embed(错卦) = -embed(本卦)。"""
    for no in range(1, 65):
        c = cuo_gua(no)
        if tuple(-x for x in embed(no)) != embed(c):
            return f"{rows_name(no)}↔{rows_name(c)} 非对径点"
    return None


def P3_neighbors() -> str | None:
    """动爻 = 相邻顶点：变一爻 → 汉明距离恰 1，6 邻居唯一。"""
    for no in range(1, 65):
        h = hex_from_bottom(no)
        nbs = []
        for i in range(6):
            h2 = list(h)
            h2[i] ^= 1
            h2 = tuple(h2)
            nb = HEX_TO_NO.get(h2)
            if nb is None:
                return f"卦{no} 变第{i}爻 {h2} 无对应卦"
            if hamming(no, nb) != 1:
                return f"卦{no} 变第{i}爻→{nb} 距离={hamming(no, nb)}≠1"
            nbs.append(nb)
        if len(set(nbs)) != 6:
            return f"卦{no} 六邻居不唯一：{nbs}"
    return None


def P4_mirror() -> str | None:
    """综卦 = 镜像：爻序反转。"""
    for no in range(1, 65):
        expect = HEX_TO_NO[tuple(reversed(hex_from_bottom(no)))]
        if zong_gua(no) != expect:
            return f"卦{no} 综卦 {rows_name(zong_gua(no))} ≠ 反转 {rows_name(expect)}"
    return None


def P5_linear() -> str | None:
    """点积-距离线性律：dot(a,b) = 6 - 2·hamming(a,b)。"""
    for a in range(1, 65):
        for b in range(1, 65):
            lhs = dot(embed(a), embed(b))
            rhs = 6 - 2 * hamming(a, b)
            if lhs != rhs:
                return f"({rows_name(a)},{rows_name(b)}) dot={lhs} ≠ {rhs}"
    return None


def P6_selfhit() -> str | None:
    """路由自命中：低温下 top1 必命中自身。"""
    for no in range(1, 65):
        top = gua_router(embed(no), temperature=0.01, top_k=1)
        if top[0][0] != no:
            return f"{rows_name(no)} top1={rows_name(top[0][0])}"
    return None


def P7_cuo_min() -> str | None:
    """错卦权重最小：对径点在 softmax 全量排序中垫底。"""
    for no in range(1, 65):
        full = gua_router(embed(no), temperature=1.0, top_k=64)
        if full[-1][0] != cuo_gua(no):
            return f"{rows_name(no)} 垫底是 {rows_name(full[-1][0])}，应为错卦 {rows_name(cuo_gua(no))}"
    return None


def P8_normalize() -> str | None:
    """softmax 全量权重和 = 1。"""
    for no in (1, 2, 11, 24, 63, 64):
        full = gua_router(embed(no), temperature=1.0, top_k=64)
        s = sum(w for _, w in full)
        if abs(s - 1.0) > 1e-9:
            return f"{rows_name(no)} 权重和={s}"
    return None


def P9_pairs() -> str | None:
    """{卦,错卦} 恰 32 个不相交对。"""
    seen = set()
    pairs = 0
    for no in range(1, 65):
        c = cuo_gua(no)
        if no in seen:
            continue
        if c in seen:
            return f"卦{no} 的错卦 {c} 已在其他对中"
        seen.add(no)
        seen.add(c)
        pairs += 1
    if pairs != 32 or len(seen) != 64:
        return f"配对 {pairs} 组 / 覆盖 {len(seen)} 卦，应为 32/64"
    return None


def P10_graph() -> str | None:
    """超立方体图：每顶点 6 邻居，边双向对称，总 192 边。"""
    edges = set()
    for no in range(1, 65):
        h = hex_from_bottom(no)
        for i in range(6):
            h2 = list(h)
            h2[i] ^= 1
            nb = HEX_TO_NO[tuple(h2)]
            # 无向边：从两个端点各数一次，用 set 去重后应恰为 192
            edges.add((min(no, nb), max(no, nb)))
    if len(edges) != 64 * 6 // 2:
        return f"边数 {len(edges)} ≠ 192"
    # 双向对称：若 a 变第 i 爻到 b，则 b 变第 i 爻回 a
    for a in range(1, 65):
        for i in range(6):
            h = list(hex_from_bottom(a))
            h[i] ^= 1
            b = HEX_TO_NO[tuple(h)]
            hb = list(hex_from_bottom(b))
            hb[i] ^= 1
            if HEX_TO_NO[tuple(hb)] != a:
                return f"边 {a}↔{b} 不对称"
    return None


def P11_degree() -> str | None:
    """度分布 = 二项式：与某卦距离 k 的卦数恰 = C(6,k)。"""
    import math as _m
    for no in (1, 11, 63):  # 抽查即可（P5 已保证全体线性）
        dist = {}
        for b in range(1, 65):
            d = hamming(no, b)
            dist[d] = dist.get(d, 0) + 1
        for k in range(7):
            expect = _m.comb(6, k)
            if dist.get(k, 0) != expect:
                return (f"{rows_name(no)} 距离{k}的卦数={dist.get(k, 0)} "
                        f"≠ C(6,{k})={expect}")
    return None


def P12_attainable() -> str | None:
    """结构先验可达：用 embed(no) 作专家嵌入，构造性验证对径/相邻约束全满足。"""
    # 构造：专家嵌入 e_no = embed(no)（六维 ±1）
    # 约束① 对径反号：e_{cuo} = -e_no
    # 约束② 相邻正相关：dot(e_no, e_邻居) > 0
    # 约束③ 自命中：dot(e_no, e_no) = 6 全局最大
    for no in range(1, 65):
        e = embed(no)
        if tuple(-x for x in e) != embed(cuo_gua(no)):
            return f"构造不满足对径 @{rows_name(no)}"
        for i in range(6):
            h = list(hex_from_bottom(no))
            h[i] ^= 1
            nb = HEX_TO_NO[tuple(h)]
            if dot(e, embed(nb)) <= 0:
                return f"构造不满足相邻正相关 @{rows_name(no)}↔{rows_name(nb)}"
        if dot(e, e) != 6:
            return f"构造自命中点积≠6 @{rows_name(no)}"
    return None


PROPOSITIONS = [
    ("P1  双射同构（64卦=2⁶全集）", P1_bijection),
    ("P2  错卦=对径点", P2_antipodal),
    ("P3  动爻=相邻顶点(距离1)", P3_neighbors),
    ("P4  综卦=镜像(爻序反转)", P4_mirror),
    ("P5  点积=6-2·汉明距离", P5_linear),
    ("P6  路由自命中", P6_selfhit),
    ("P7  错卦在softmax中权重最小", P7_cuo_min),
    ("P8  softmax归一化", P8_normalize),
    ("P9  对径32对全覆盖", P9_pairs),
    ("P10 超立方体图(192边双向)", P10_graph),
    ("P11 度分布=C(6,k)", P11_degree),
    ("P12 结构先验可达(非病态)", P12_attainable),
]


def main():
    print("=" * 64)
    print("数理严格验证：六十四卦 = 六维超立方体 MoE")
    print("=" * 64)
    fails = []
    for name, fn in PROPOSITIONS:
        try:
            err = fn()
        except Exception as e:  # noqa: BLE001
            err = f"异常：{type(e).__name__}: {e}"
        mark = "✅ 通过" if err is None else f"❌ 失败：{err}"
        print(f"  {mark}  {name}")
        if err is not None:
            fails.append(name)

    print("-" * 64)
    if fails:
        print(f"结果：{len(fails)}/{len(PROPOSITIONS)} 失败 —— 方案存在数理漏洞，需先修")
        raise SystemExit(1)
    print("结果：12/12 全部通过 —— 数理上成立，可进入训练阶段")

    # ---- 附带输出：点积值域与可行性估算 ----
    print("\n【点积值域】embed 为 ±1 向量，点积 ∈ {-6..6}，与汉明距离一一对应：")
    for d in range(7):
        print(f"   汉明距离 {d} → 点积 {6 - 2 * d:>2}  → 卦数 C(6,{d}) = {math.comb(6, d)}")

    print("\n【参数量估算】卦象专家层（不含 Qwen 微调）：")
    for d_out in (16, 64, 512):
        params = 64 * (6 * d_out + d_out)
        print(f"   专家输出维 {d_out:>3} → 64×(6×{d_out}+{d_out}) = {params:,} 参数")

    print("\n【风险提示】（这些是'可行性'边界，不是'数理'漏洞）")
    print("  · MoE 本身参数量极小，GB10 训得动；算力大头在 Qwen3-14B LoRA 与输入投影编码器")
    print("  · 504 条语料对 MoE 偏少，但结构先验 + 程序可生成海量合法样本，数据非硬瓶颈")
    print("  · 64 专家 + 小数据易过拟合，需靠对径/相邻正则 + 权重共享缓解")
    print("  · 本项目是'结构可证明正确'，'义理解读质量'仍取决于 Qwen 微调，需阶段4评估")


if __name__ == "__main__":
    main()
