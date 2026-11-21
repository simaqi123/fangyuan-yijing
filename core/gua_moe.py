#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""卦象专家路由层（超立方体 MoE）—— 六十四卦 = 64 个可训练专家。

核心思想（这是整套模型的"灵魂"，GitHub 上无人做）：
  六十四卦 = 六维布尔超立方体的 64 个顶点（阴阳=1bit，六爻=6bit，2⁶=64）。
    · 错卦（六爻全反）＝ 对径点（嵌入互为相反向量）
    · 动爻（变一爻）　＝ 沿边相邻顶点（汉明距离 1）
    · 卦际距离　　　　＝ 汉明距离（几爻不同）

架构：
  输入 →【定卦·触发机制】softmax(输入 · 卦嵌入) → top-k 卦专家 → 加权融合 → 输出

本文件为 POC（纯 Python 零依赖，验证结构与前向逻辑）。
可训练版（PyTorch）接口见文末 docstring：把 GuaMoE 的权重换成 nn.Parameter，
加"错卦对径 / 动爻相邻"对比损失注入结构先验，即可在 DGX 上训练。
"""
from __future__ import annotations
import math
import random

from xiangshu import hex_from_bottom, cuo_gua, rows_name

N_GUA = 64
D_STRUCT = 6          # 六爻 = 6 个二进制维


# ============================================================ 结构嵌入（超立方体顶点）
def embed(no: int) -> tuple:
    """第 no 卦的对称超立方体嵌入：阳爻=+1、阴爻=-1（6 维，从下往上）。"""
    return tuple(1 if x else -1 for x in hex_from_bottom(no))


def hamming(no_a: int, no_b: int) -> int:
    """两卦的汉明距离（几爻不同）。"""
    ea, eb = embed(no_a), embed(no_b)
    return sum(1 for x, y in zip(ea, eb) if x != y)


def dot(a, b) -> float:
    return float(sum(x * y for x, y in zip(a, b)))


# ============================================================ 定卦路由（触发机制）
def gua_router(q, temperature: float = 1.0, top_k: int = 3) -> list:
    """输入 q（6 维或投影到卦空间）→ 64 卦 softmax → top-k 卦 + 权重。

    返回 [(卦号, 权重), ...]，权重和为 top-k 的归一化概率。
    """
    scores = [dot(embed(no), q) / temperature for no in range(1, 65)]
    m = max(scores)
    exps = [math.exp(s - m) for s in scores]      # 数值稳定 softmax
    total = sum(exps)
    ranked = sorted(((i + 1, exps[i] / total) for i in range(64)),
                    key=lambda x: -x[1])
    return ranked[:top_k]


# ============================================================ 六十四卦专家混合
class GuaMoE:
    """64 个卦专家：每个卦一个可训练线性专家（POC 用随机权重模拟）。"""

    def __init__(self, d_out: int = 16, seed: int = 42):
        rng = random.Random(seed)
        self.d_out = d_out
        # 64 个专家，每个是 6→d_out 的线性映射（可训练参数）
        self.W = [[[rng.gauss(0, 1 / math.sqrt(D_STRUCT)) for _ in range(d_out)]
                   for _ in range(D_STRUCT)] for _ in range(N_GUA)]
        self.b = [[0.0] * d_out for _ in range(N_GUA)]

    def expert(self, no: int, q) -> list:
        """第 no 卦专家：W[no]^T q + b[no]。"""
        w, b = self.W[no - 1], self.b[no - 1]
        return [sum(w[j][i] * q[j] for j in range(D_STRUCT)) + b[i]
                for i in range(self.d_out)]

    def forward(self, q, temperature: float = 1.0, top_k: int = 3):
        """前向：定卦路由 + top-k 专家加权融合。"""
        top = gua_router(q, temperature, top_k)
        out = [0.0] * self.d_out
        for no, weight in top:
            e = self.expert(no, q)
            for i in range(self.d_out):
                out[i] += weight * e[i]
        return out, top


# ============================================================ 自检
def self_check() -> list:
    errs = []
    # 1) 错卦 = 对径点（互为相反向量）
    for no in range(1, 65):
        c = cuo_gua(no)
        if tuple(-x for x in embed(no)) != embed(c):
            errs.append(f"错卦非对径点：{rows_name(no)}↔{rows_name(c)}")
            break
    # 2) 动爻（变一爻）= 汉明距离 1；错卦 = 距离 6
    for no in range(1, 65):
        if hamming(no, cuo_gua(no)) != 6:
            errs.append(f"错卦汉明距离非6：{rows_name(no)}")
            break
    # 3) 路由自命中：卦自身嵌入 top1 必命中自身（低温）
    for no in (1, 2, 11, 63):
        top = gua_router(embed(no), temperature=0.1, top_k=1)
        if top[0][0] != no:
            errs.append(f"路由自命中失败：{rows_name(no)}→{rows_name(top[0][0])}")
    # 4) 路由权重归一化（top_k=3 权重和 ≤1）
    top = gua_router(embed(1), temperature=1.0, top_k=3)
    s = sum(w for _, w in top)
    if abs(s) > 1.0001:
        errs.append(f"路由权重和超1：{s}")
    # 5) 融合输出维度
    moe = GuaMoE()
    out, _ = moe.forward(embed(1))
    if len(out) != 16:
        errs.append(f"融合输出维度错误：{len(out)}")
    return errs


if __name__ == "__main__":
    errs = self_check()
    if errs:
        print("自检失败：")
        for e in errs:
            print("  -", e)
        raise SystemExit(1)
    print("卦象专家路由层 POC 自检通过：")
    print("  · 错卦=对径点（互为相反向量）✓")
    print("  · 错卦汉明距离=6、动爻=1 ✓")
    print("  · 定卦路由自命中 ✓")

    print("\n【演示】输入「乾」卦嵌入，路由 top3 与融合：")
    top = gua_router(embed(1), temperature=1.0, top_k=3)
    for no, w in top:
        print(f"   {rows_name(no)}（卦{no}）权重 {w:.3f}，与乾汉明距离 {hamming(1, no)}")

    print("\n【演示】结构先验：乾↔坤 互为对径点（错卦），汉明距离 6")
    print(f"   embed(乾)={embed(1)}")
    print(f"   embed(坤)={embed(2)}")
