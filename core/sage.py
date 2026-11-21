#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""圣人思维框架 SAGE_SYS —— 立心 · 格物 · 致知 · 笃行（第 2 项：灵魂层）。

让 Qwen 回答任何问题时，先走经义四步，再落到具体专业问题，实现「一通百通」：

  【立心】诚其意、正其心 —— 先正本心，明本末、义利、是非，不逐末妄作。
          （《大学》正心诚意、《中庸》中）
  【格物】穷究其理 —— 用卦象、五行、义理关系把此事之理拆解清楚。
          （《大学》格物、《系辞》极深研几）
  【致知】贯通明理 —— 格物所得与经义互证，得出判断与洞察。
          （《系辞》穷神知化、知至）
  【笃行】与时偕行 —— 给出合于时中、知行合一的行止建议。
          （《中庸》笃行、时中）

依赖：kb_policy.db（gua 表已含彖传/卦德/错综互卦、yili 义理概念、yili_rel 义理关系、yao 爻辞）。
与 dedao_brain 的关系：本模块只产出「四步提示词 + 义理上下文」，最终调用 _llm 由 dedao_brain 完成。
"""
from __future__ import annotations

import os
import re
import sqlite3
from pathlib import Path

POLICY_DB = Path(os.getenv("KB_POLICY_DB", "~/.openclaw/.openclaw/kb_policy.db"))

SAGE_SYS = (
    "你是「圣人思维」引导引擎，以《周易》为体、儒道为用。\n"
    "你回答任何问题（油气、中医、工作、人生皆可）时，都按四步贯通经义，做到「一通百通」：\n"
    "【立心】诚其意、正其心：先问此事之本末（先后轻重）、义利（是否合宜）、是非（是否合道），"
    "端正发问之根本，不逐末、不妄作。\n"
    "【格物】穷究其理：用卦象、五行、义理关系、时空坐标（方图方位·圆图时序）框架，"
    "把此事之理拆解清楚"
    "（是什么、为什么、处于何势——何时、何地、何势）。\n"
    "【致知】贯通明理：把格物所得与经义互证，得出判断与洞察"
    "（该进该退、该守该变、何时可成）。\n"
    "【笃行】与时偕行：给出合于时中、知行合一的可落地行止建议。\n\n"
    "硬性规则：\n"
    "1. 四步必须依次输出，每步以【立心】【格物】【致知】【笃行】开头。\n"
    "2. 经义引用必须出自<义理>或<卦象>给出的原文，不得杜撰经文；未给出的经文不得凭空引用。\n"
    "3. 专业素材（油气/中医/工作）是「格物」的实据，经义是「贯通」的理则，二者相济，不牵强附会。\n"
    "4. 若卦象/义理与所问无明显关联，如实说明「义理仅作旁通」，不硬套。\n"
    "5. 结尾以「一言以蔽之：……」一句话收束。"
)

# 义理关键词 → 卦名（供定卦兜底：问题里出现这些词时，优先取对应卦）
KEY_GUA = {
    '仁': '乾', '义': '乾', '礼': '履', '智': '坎', '信': '中孚',
    '诚': '无妄', '中庸': '节', '中和': '节', '变化': '革', '变革': '革',
    '生生': '复', '恢复': '复', '养生': '颐', '修身': '谦', '家': '家人',
    '治国': '师', '治理': '师', '平天下': '泰', '天下': '泰', '时中': '随',
    '等待': '需', '时机': '需', '蓄势': '需', '争讼': '讼', '冲突': '讼',
    '教育': '蒙', '启蒙': '蒙', '积累': '大畜', '储蓄': '小畜', '节制': '节',
    '减损': '损', '增益': '益', '困难': '坎', '险': '坎', '光明': '离',
    '退避': '遁', '隐退': '遁', '前进': '晋', '晋升': '晋', '团结': '同人',
    '丰盛': '丰', '鼎盛': '丰', '鼎': '鼎', '涣散': '涣', '凝聚': '萃',
    '完成': '既济', '成功': '既济', '未完成': '未济', '未成': '未济',
    '决断': '夬', '相遇': '姤', '聚集': '萃', '上升': '升', '渐进': '渐',
    '止': '艮', '静': '艮', '动': '震', '震动': '震', '喜悦': '兑', '和悦': '兑',
    '渗透': '巽', '顺从': '巽', '开创': '乾', '创始': '乾', '承载': '坤',
    '包容': '坤', '艰难': '屯', '初创': '屯', '观': '观', '观察': '观',
}


def _conn():
    return sqlite3.connect(str(POLICY_DB))


# 语义定卦缓存（bge-m3 懒加载，与 unified_brain_mcp 复用同一模型路径）
_gua_vec_cache = None


def _gua_vectors():
    """64 卦锚点向量（懒加载 + 缓存），用于语义定位卦位。"""
    global _gua_vec_cache
    if _gua_vec_cache is None:
        import numpy as np
        from sentence_transformers import SentenceTransformer
        model_dir = os.getenv("BGE_M3_DIR", "~/.openclaw/knowledge-base/models/bge-m3")
        model = SentenceTransformer(model_dir)
        con = _conn()
        try:
            rows = con.execute("SELECT gua_no, name, anchor_text FROM gua "
                               "ORDER BY gua_no").fetchall()
        finally:
            con.close()
        texts = [(r[2] or '') for r in rows]
        vecs = model.encode(texts, normalize_embeddings=True, show_progress_bar=False)
        _gua_vec_cache = (np.asarray(vecs, dtype="float32"),
                          [(r[0], r[1]) for r in rows])
    return _gua_vec_cache


def semantic_gua(question: str, top: int = 3, min_score: float = 0.30) -> list:
    """语义定卦：用 bge-m3 把问题与 64 卦锚点做相似度，返回卦名列表。"""
    try:
        import numpy as np
        from sentence_transformers import SentenceTransformer
        model_dir = os.getenv("BGE_M3_DIR", "~/.openclaw/knowledge-base/models/bge-m3")
        model = SentenceTransformer(model_dir)
        vecs, names = _gua_vectors()
        qv = np.asarray(model.encode(question, normalize_embeddings=True),
                        dtype="float32")
        sims = vecs @ qv
        out = []
        for idx in np.argsort(-sims):
            sc = float(sims[idx])
            if sc < min_score:
                break
            out.append(names[idx][1])
            if len(out) >= top:
                break
        return out
    except Exception:
        return []


def _first(con, sql, args):
    try:
        r = con.execute(sql, args).fetchone()
        return r if r else None
    except sqlite3.OperationalError:
        return None


def gua_by_keywords(question: str, con) -> list:
    """由问题关键词定卦：先 KEY_GUA，再卦名/核心义/现代语义 LIKE。返回卦名列表。"""
    q = question or ""
    hit = []
    seen = set()
    for kw, gname in KEY_GUA.items():
        if kw in q and gname not in seen:
            seen.add(gname)
            hit.append(gname)
    # 卦名/卦辞/核心义 LIKE
    try:
        rows = con.execute(
            "SELECT name FROM gua WHERE name LIKE ? OR ci LIKE ? OR core LIKE ? "
            "OR modern LIKE ? OR tuan LIKE ? LIMIT 8", ("%" + q[:6] + "%",) * 5).fetchall()
        for r in rows:
            if r[0] not in seen:
                seen.add(r[0])
                hit.append(r[0])
    except sqlite3.OperationalError:
        pass
    return hit


def gua_context(con, gua_names: list) -> dict:
    """取命中的卦的完整义理上下文（卦辞/大象/彖传/卦德/错综互卦/爻辞节选）。"""
    out = []
    for gname in gua_names:
        r = _first(con,
                   "SELECT gua_no,name,symbol,up_nature,down_nature,ci,xiang,tuan,"
                   "de,wuxing,fangwei,cuo,zong,hu,xiaoxi,"
                   "xian_up,xian_down,fang_row,fang_col,yuantu_order,xian_fangwei "
                   "FROM gua WHERE name=?",
                   (gname,))
        if not r:
            continue
        (no, name, symbol, up, down, ci, xiang, tuan, de, wx, fw, cuo, zong, hu, xs,
         xian_up, xian_down, fang_row, fang_col, yuantu_order, xian_fw) = r
        n2 = {x[0]: x[1] for x in
              con.execute("SELECT gua_no,name FROM gua").fetchall()}
        yaos = con.execute(
            "SELECT title,ci FROM yao WHERE gua_no=? ORDER BY yao_pos LIMIT 3",
            (no,)).fetchall()
        try:
            import jieqi as _jq
            import tuilian as _tl
            jq = _jq.gua_jieqi(no)
            jq_line = {"节气": jq["节气"], "值月": f"{jq['月']}({jq['地支']})",
                       "律吕": jq["律吕"], "黄道次": jq["黄道次"]}
            tui = _tl.tuilian_text(no)
        except Exception:
            jq_line = {"节气": "", "值月": "", "律吕": "", "黄道次": ""}
            tui = ""
        out.append({
            "name": name, "symbol": symbol, "上卦": up, "下卦": down,
            "卦辞": ci, "大象": xiang, "彖传": tuan,
            "卦德": de, "五行": wx, "方位": fw,
            "错卦": n2.get(cuo, ""), "综卦": n2.get(zong, ""),
            "互卦": n2.get(hu, ""), "消息": xs or "",
            "先天数": f"上{xian_up}下{xian_down}",
            "方图位": f"行{fang_row}列{fang_col}",
            "圆图位": yuantu_order,
            "先天方位": xian_fw,
            "节气": jq_line["节气"], "值月": jq_line["值月"],
            "律吕": jq_line["律吕"], "黄道次": jq_line["黄道次"],
            "推演链": tui,
            "爻辞节选": [f"{t}：{c}" for t, c in yaos],
        })
    return out


def yili_context(con, question: str, gua_names: list) -> dict:
    """取义理概念 + 关系（命中问题关键词或所定卦的概念）。"""
    concepts = []
    rels = []
    try:
        rows = con.execute("SELECT name,meaning,basis,gua FROM yili").fetchall()
    except sqlite3.OperationalError:
        return {"concepts": [], "relations": []}
    for name, meaning, basis, gua in rows:
        hit = (gua in gua_names)  # 通过卦关联命中（单字/多字概念均适用）
        if not hit and len(name) >= 2 and name in question:
            hit = True  # 仅多字概念做子串匹配，避免单字「气/理/中」误命中
        if hit:
            concepts.append({"name": name, "meaning": meaning, "basis": basis, "卦": gua})
    # 相关关系
    try:
        relrows = con.execute("SELECT src,rel,dst,basis FROM yili_rel").fetchall()
        names = {c["name"] for c in concepts}
        for src, rel, dst, basis in relrows:
            if src in names or dst in names:
                rels.append({"src": src, "rel": rel, "dst": dst, "basis": basis})
    except sqlite3.OperationalError:
        pass
    return {"concepts": concepts, "relations": rels}


def build_sage_context(question: str) -> dict:
    """定卦 + 义理 + 经文，返回完整圣人思维上下文。"""
    q = (question or "").strip()
    if not q:
        return {"gua": [], "yili": {"concepts": [], "relations": []}, "ok": False}
    con = _conn()
    try:
        gua_names = gua_by_keywords(q, con)
        if not gua_names:
            gua_names = semantic_gua(q)   # 关键词未命中 → 语义定卦兜底
        gctx = gua_context(con, gua_names)
        yctx = yili_context(con, q, gua_names)
        return {"gua": gctx, "yili": yctx, "gua_names": gua_names, "ok": True}
    finally:
        con.close()


def _fmt_ctx(sage_ctx: dict) -> str:
    """把义理上下文格式化成给 LLM 的文本块。"""
    parts = []
    for g in sage_ctx.get("gua", []):
        parts.append(
            f"【卦·{g['name']}】{g['symbol']} 上{g['上卦']}下{g['下卦']}　"
            f"卦德：{g['卦德']}　五行：{g['五行']}　方位：{g['方位']}\n"
            f"卦辞：{g['卦辞']}\n大象：{g['大象']}\n彖传：{g['彖传']}\n"
            f"错卦：{g['错卦']}　综卦：{g['综卦']}　互卦：{g['互卦']}"
            + (f"　消息：{g['消息']}" if g['消息'] else "") +
            f"\n时空：先天数{g['先天数']}　方图(空间){g['方图位']}　"
            f"圆图(时间)第{g['圆图位']}位　先天方位{g['先天方位']}"
            + (f"\n节气：{g['节气']}（{g['值月']}）　律吕：{g['律吕']}　黄道次：{g['黄道次']}"
               if g['节气'] else "")
            + ("\n爻辞节选：" + "；".join(g['爻辞节选']) if g['爻辞节选'] else "")
            + (f"\n推演链：\n{g['推演链']}" if g.get('推演链') else ""))
    for c in sage_ctx.get("yili", {}).get("concepts", []):
        parts.append(f"【义理·{c['name']}】{c['meaning']}（{c['basis']}）")
    for r in sage_ctx.get("yili", {}).get("relations", []):
        parts.append(f"【义理关系】{r['src']} —{r['rel']}→ {r['dst']}（{r['basis']}）")
    return "\n".join(parts)


def sage_prompt(question: str, sage_ctx: dict, kb_ctx: str = "", local_ctx: str = "") -> str:
    """组装四步提示词。kb_ctx/local_ctx 为知识库/本地记录素材（可为空）。"""
    yili = _fmt_ctx(sage_ctx) or "（未命中具体卦象，请仅以通用义理旁通）"
    return (
        "请用「立心→格物→致知→笃行」四步，贯通经义回答下列问题。\n\n"
        "<卦象与义理>\n%s\n</卦象与义理>\n\n"
        "<专业素材·知识库>\n%s\n</专业素材·知识库>\n\n"
        "<专业素材·本地记录>\n%s\n</专业素材·本地记录>\n\n"
        "问题：%s\n\n"
        "要求：先【立心】正本心，再【格物】用卦象义理+素材穷理，"
        "后【致知】贯通得判断，终【笃行】给出合于时中的行止。"
        % (yili, kb_ctx or "（无）", local_ctx or "（无）", question))


def self_check() -> list:
    errs = []
    if not POLICY_DB.exists():
        # 本地可能还没建库，跳过内容校验，只校验数据结构
        return errs
    con = _conn()
    try:
        for t in ("gua", "yili", "yili_rel", "yao"):
            r = _first(con, "SELECT COUNT(*) FROM %s" % t, ())
            if r is None:
                errs.append(f"缺表 {t}")
    finally:
        con.close()
    return errs


if __name__ == '__main__':
    if not POLICY_DB.exists():
        print("kb_policy.db 不存在（本地环境），仅做语法自检")
        print("SAGE_SYS 框架四步：立心 → 格物 → 致知 → 笃行")
        raise SystemExit(0)
    ctx = build_sage_context("我在做一个油气项目，遇到瓶颈，很焦虑，该怎么办？")
    print("定卦：", ctx["gua_names"])
    print(_fmt_ctx(ctx)[:800])
