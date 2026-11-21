#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""六十四卦 · 全量归卦。

把向量库里的每一条 chunk 归入一个卦位，让图谱与 16 万 chunks 语料物理连通。

做法：
  1. 从 chroma 取出全部 chunk 的嵌入向量（已 L2 归一化）
  2. 用同一个 bge-m3 嵌入 64 个卦位锚点（卦名+卦象+卦辞+大象+核心义+现代语义）
  3. 余弦相似度取 argmax → 该 chunk 归入哪个卦

为什么这样可行：
  · chunk 向量与锚点向量在同一 bge-m3 空间，可直接点积
  · 卦位锚点是中文古典语料，与库内中文正文同域，匹配质量高
  · 64 个锚点 × 161k chunks = 一次矩阵乘，秒级完成，无需重新嵌入

产出（写入 kb_policy.db）：
  gua(gua_no, name, symbol, up_trigram, down_trigram, up_nature, down_nature,
      ci, xiang, core, modern, opposite, binary, anchor_text)
  chunk_gua(doc_key, kb_id, scope, gua_no, score)
  doc_gua(kb_id, scope, gua_no, n, score)
  relations 追加 gua→school / gua→doc

用法：
  python gua_assign.py            # 全量
  python gua_assign.py --dry      # 只算不写
"""
from __future__ import annotations

import argparse
import os
import sqlite3
import sys
import time
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gua64 import gua_rows, anchor_text, school_gua_map, opposite  # noqa: E402
from xiangshu import all_gua_xiangshu  # noqa: E402
from jingwen import TUAN, YAO  # noqa: E402
import jingyi  # noqa: E402
import fangyuan  # noqa: E402
import jieqi  # noqa: E402

INDEX = Path(os.getenv("UNIFIED_BRAIN_INDEX", "~/.openclaw/.openclaw/unified_brain_index"))
POLICY_DB = Path(os.getenv("KB_POLICY_DB", "~/.openclaw/.openclaw/kb_policy.db"))
COLL = "unified_brain"
MODEL_DIR = os.getenv("BGE_M3_DIR", "~/.openclaw/knowledge-base/models/bge-m3")


def get_chroma():
    import chromadb
    from chromadb.config import Settings
    c = chromadb.PersistentClient(path=str(INDEX), settings=Settings(anonymized_telemetry=False))
    return c.get_collection(COLL)


def fetch_all(col, page=10000):
    """分页取出全部 (ids, embeddings, metadatas)。"""
    total = col.count()
    ids, embs, metas = [], [], []
    off = 0
    while off < total:
        got = col.get(limit=page, offset=off, include=["embeddings", "metadatas"])
        if not got or not got.get("ids"):
            break
        ids.extend(got["ids"])
        embs.extend(got["embeddings"])
        metas.extend(got["metadatas"])
        off += len(got["ids"])
        print(f"  [fetch] {len(ids)}/{total}", flush=True)
    return ids, np.asarray(embs, dtype=np.float32), metas


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry", action="store_true", help="只统计不落库")
    a = ap.parse_args()

    t0 = time.time()
    print("[1/4] 取 chunk 向量 ...", flush=True)
    col = get_chroma()
    ids, E, metas = fetch_all(col)
    print(f"  chunks={len(ids)} dim={E.shape[1]}  {time.time()-t0:.0f}s", flush=True)

    print("[2/4] 嵌入 64 卦位锚点 ...", flush=True)
    from sentence_transformers import SentenceTransformer
    model = SentenceTransformer(MODEL_DIR)
    try:
        import torch
        if torch.cuda.is_available():
            model.cuda()
            print("  device: GPU", torch.cuda.get_device_name(0), flush=True)
    except Exception as e:
        print("  device: CPU", e, flush=True)
    rows = gua_rows()
    anchors = [anchor_text(r) for r in rows]
    A = model.encode(anchors, normalize_embeddings=True, batch_size=16,
                     show_progress_bar=False)
    A = np.asarray(A, dtype=np.float32)
    print(f"  anchors={A.shape}  {time.time()-t0:.0f}s", flush=True)

    print("[3/4] 相似度匹配 ...", flush=True)
    sim = E @ A.T                      # (N, 64)
    best = sim.argmax(axis=1)
    best_score = sim[np.arange(len(best)), best]
    print(f"  done  {time.time()-t0:.0f}s", flush=True)

    # 统计
    dist = np.bincount(best, minlength=64)
    print("\n  卦位分布：")
    order = np.argsort(-dist)
    for i in order:
        r = rows[i]
        print(f"    {r['gua_no']:>2} {r['name']} {r['symbol']}  {dist[i]:>7}  "
              f"({dist[i]*100.0/len(ids):>5.2f}%)  {r['core']}")
    print(f"\n  平均相似度 = {best_score.mean():.4f}  "
          f"≥0.4 的 chunk 占 {(best_score>=0.4).mean()*100:.1f}%")

    if a.dry:
        print("[dry] 未落库")
        return

    print("\n[4/4] 写入 kb_policy.db ...", flush=True)
    con = sqlite3.connect(str(POLICY_DB))
    xs = {x['gua_no']: x for x in all_gua_xiangshu()}
    con.executescript("""
        DROP TABLE IF EXISTS gua;
        CREATE TABLE gua(
          gua_no INTEGER PRIMARY KEY, name TEXT, symbol TEXT,
          up_trigram TEXT, down_trigram TEXT, up_nature TEXT, down_nature TEXT,
          ci TEXT, xiang TEXT, core TEXT, modern TEXT, opposite INTEGER, binary TEXT,
          anchor_text TEXT,
          tuan TEXT, de TEXT, wuxing TEXT, fangwei TEXT,
          cuo INTEGER, zong INTEGER, hu INTEGER, xiaoxi TEXT,
          xian_up INTEGER, xian_down INTEGER,
          fang_row INTEGER, fang_col INTEGER, yuantu_order INTEGER,
          xian_fangwei TEXT,
          pigua TEXT, yue TEXT, dizhi TEXT, lvlu TEXT, huangdao TEXT, jieqi TEXT);
        CREATE TABLE IF NOT EXISTS chunk_gua(
          doc_key TEXT PRIMARY KEY, kb_id INTEGER, scope TEXT,
          gua_no INTEGER, score REAL);
        CREATE INDEX IF NOT EXISTS idx_chunk_gua_kb ON chunk_gua(kb_id);
        CREATE INDEX IF NOT EXISTS idx_chunk_gua_no ON chunk_gua(gua_no);
        CREATE TABLE IF NOT EXISTS doc_gua(
          kb_id INTEGER, scope TEXT, gua_no INTEGER, n INTEGER, score REAL,
          PRIMARY KEY(kb_id, scope, gua_no));
        DROP TABLE IF EXISTS yao;
        CREATE TABLE yao(
          gua_no INTEGER, yao_pos INTEGER, title TEXT, ci TEXT, xiang TEXT,
          PRIMARY KEY(gua_no, yao_pos));
    """)
    con.execute("DELETE FROM gua")
    con.execute("DELETE FROM chunk_gua")
    con.execute("DELETE FROM doc_gua")
    con.execute("DELETE FROM yao")

    fy = {f['gua_no']: f for f in fangyuan.all_gua_fangyuan()}
    jq = {x['gua_no']: x for x in jieqi.all_gua_jieqi()}
    con.executemany(
        "INSERT OR REPLACE INTO gua(gua_no,name,symbol,up_trigram,down_trigram,"
        "up_nature,down_nature,ci,xiang,core,modern,opposite,binary,anchor_text,"
        "tuan,de,wuxing,fangwei,cuo,zong,hu,xiaoxi,"
        "xian_up,xian_down,fang_row,fang_col,yuantu_order,xian_fangwei,"
        "pigua,yue,dizhi,lvlu,huangdao,jieqi) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,"
        "?,?,?,?,?,?)",
        [(r['gua_no'], r['name'], r['symbol'], r['up_trigram'], r['down_trigram'],
          r['up_nature'], r['down_nature'], r['ci'], r['xiang'], r['core'], r['modern'],
          r['opposite'], r['binary'], anchor_text(r),
          TUAN.get(r['gua_no'], ''),
          xs[r['gua_no']]['gua_de'], xs[r['gua_no']]['wuxing'],
          xs[r['gua_no']]['fangwei'],
          xs[r['gua_no']]['cuo'], xs[r['gua_no']]['zong'], xs[r['gua_no']]['hu'],
          xs[r['gua_no']]['xiaoxi'],
          fy[r['gua_no']]['xian_up'], fy[r['gua_no']]['xian_down'],
          fy[r['gua_no']]['fang_row'], fy[r['gua_no']]['fang_col'],
          fy[r['gua_no']]['yuantu_order'], fy[r['gua_no']]['xian_fangwei'],
          jq[r['gua_no']]['辟卦'], jq[r['gua_no']]['月'], jq[r['gua_no']]['地支'],
          jq[r['gua_no']]['律吕'], jq[r['gua_no']]['黄道次'], jq[r['gua_no']]['节气'])
         for r in rows])

    # 爻表：384 + 用九用六 = 386 条
    yao_rows = []
    for gno, lines in YAO.items():
        for pos, (title, ci, xiang) in enumerate(lines, start=1):
            yao_rows.append((gno, pos, title, ci, xiang))
    con.executemany("INSERT OR REPLACE INTO yao(gua_no,yao_pos,title,ci,xiang) "
                    "VALUES (?,?,?,?,?)", yao_rows)

    # 义理图谱：yili / yili_rel（道/德/阴阳/五行/仁义礼智信…）
    n_yili = jingyi.build_tables(con)

    # 归卦置信度阈值：低于阈值的 chunk 不硬归（避免低质量摊派污染骨架）
    GUARD = float(os.getenv("GUA_ASSIGN_MIN_SCORE", "0.35"))
    chunk_rows = []
    n_skip = 0
    for i, m in enumerate(metas):
        if not m:
            continue
        sc = float(best_score[i])
        if sc < GUARD:
            n_skip += 1
            continue
        # best 是 0 基的锚点下标，gua 表用 1 基卦号 —— 这里 +1 对齐
        chunk_rows.append((m.get("doc_key", ""), m.get("kb_id"), m.get("scope", ""),
                           int(best[i]) + 1, sc))
    con.executemany("INSERT OR REPLACE INTO chunk_gua(doc_key,kb_id,scope,gua_no,score) "
                    "VALUES (?,?,?,?,?)", chunk_rows)

    # doc_gua 聚合
    agg = {}
    for dk, kb, scope, gno, sc in chunk_rows:
        k = (kb, scope, gno)
        cur = agg.setdefault(k, [0, 0.0])
        cur[0] += 1
        cur[1] += sc
    con.executemany("INSERT OR REPLACE INTO doc_gua(kb_id,scope,gua_no,n,score) "
                    "VALUES (?,?,?,?,?)",
                    [(k[0], k[1], k[2], v[0], round(v[1] / max(v[0], 1), 4))
                     for k, v in agg.items()])

    # 图谱边：卦 → 学派；卦 → 文献
    name_by_no = {r['gua_no']: r['name'] for r in rows}
    rel = []
    for school, gname in school_gua_map().items():
        for r in rows:
            if r['name'] == gname:
                rel.append(("gua", r['name'], "governs", "school", school))
                break
    doc_gua_count = con.execute("SELECT COUNT(DISTINCT kb_id||'|'||scope) FROM doc_gua").fetchone()[0]
    con.execute("DELETE FROM relations WHERE from_type='gua'")
    con.executemany("INSERT INTO relations(from_type,from_name,rel,to_type,to_name) "
                    "VALUES (?,?,?,?,?)", rel)

    con.commit()
    print(f"  gua={len(rows)}  yao={len(yao_rows)}  yili={n_yili}  "
          f"chunk_gua={len(chunk_rows)}  doc_gua={len(agg)}  覆盖文献={doc_gua_count}")
    if n_skip:
        print(f"  [阈值 {GUARD}] 未归卦(低置信度) chunk = {n_skip} "
              f"({n_skip*100.0/max(len(ids),1):.1f}%)")
    print(f"[done] {time.time()-t0:.0f}s")
    con.close()


if __name__ == "__main__":
    main()
