# Fangyuan Yijing

> **The I Ching as a computable structure — not a metaphor.**
> A zero-dependency Python core that treats the 64 hexagrams as the 64 vertices
> of a 6-dimensional Boolean hypercube, plus the research reports, training
> data and an offline interactive visualization behind an LLM fine-tuning plan.

**Build in public.** MIT licensed. Core algorithms need only Python 3.8+ standard library.

[![CI](https://github.com/simaqi123/fangyuan-yijing/actions/workflows/validate.yml/badge.svg)](https://github.com/simaqi123/fangyuan-yijing/actions/workflows/validate.yml)

---

## Why this exists

Most writing about the I Ching stops at interpretation. This project asks a
narrower, testable question: **can the relationships between hexagrams be made
exact and computational?** The answer underpinning this repository is yes —
and it is provable, not decorative.

| Common framing | This project's framing |
|---|---|
| Hexagrams as symbols to interpret | Hexagrams as 6-bit vectors, i.e. vertices of {0,1}⁶ |
| "Opposite" / "inverted" as soft concepts | Cuo = antipodal point; Zong = bit-order reversal; changed line = Hamming distance 1 |
| Meaning handed down by tradition | Geometry derived from structure, then checked against the classic text |
| Divination as the output | A training corpus for a model that reasons over structure, text and time/space |

The repository is the working set behind that question: a verification harness,
the algorithm modules, four SFT datasets, ten research/decision reports, and a
single-file interactive Fang-Yuan (square-and-circle) map you can open offline.

---

## What's in the box

| | |
|---|---|
| **64** | hexagrams as a complete, unique 6-bit vertex set |
| **12** | independently falsifiable mathematical propositions (all verified) |
| **24** | solar terms wired into the time-coordinate layer |
| **9,738** | SFT training records across 4 JSONL files |
| **10** | research and decision reports (feasibility, training plan, audits) |
| **0** | third-party dependencies for the core algorithms |

The central claim — **64 hexagrams ≅ 6-dimensional hypercube** — is checked in
[`docs/en/mathematical-verification.md`](docs/en/mathematical-verification.md)
(12 propositions, English) as 12 separate
assertions, including: bijection to {0,1}⁶; cuo as antipode; changed line as a
Hamming-1 neighbor; the identity `dot = 6 − 2·hamming`; cuo as an involution;
and the hypercube graph having 192 symmetric edges.
The Chinese original — the source of truth — is
[`docs/数理可行性验证报告.md`](docs/数理可行性验证报告.md).

---

## Quick start

No `pip install`, no build step. Just Python 3.8+.

```bash
git clone https://github.com/simaqi123/fangyuan-yijing.git
cd fangyuan-yijing

# Run the self-check (structure, relations, data format)
python verify.py

# Open the interactive Fang-Yuan map offline: double-click
#   web/先天方圆图交互可视化.html
```

Expected self-check output:

```
[1] 六十四卦     64 hexagrams · numbering 1..64 · unique names
[2] 先天八卦     8 directions, no duplicates
[3] 二十四节气   24 terms
[4] 象数关系     cuo involution over all 64 · zong permutation · qian/kun antipodal
[5] SFT 数据     4 jsonl / 9738 records, all well-formed
结果：全部通过
```

The core modules import directly from `core/`:

```python
import sys
sys.path.insert(0, "core")

import gua64, fangyuan, jieqi, xiangshu

len(gua64.GUA64)          # 64
fangyuan.xian_tian(0)     # first hexagram of the先天 sequence
xiangshu.cuo_gua(1)       # 2 — qian's antipode is kun
jieqi.JIEQI[0]            # first solar term
```

---

## The structure claim, precisely

Each line is one bit: **yang = 1, yin = 0**. Six lines give 2⁶ = 64 vertices.
Every classical relation then becomes geometry:

| Relation | Computation | File |
|---|---|---|
| Hexagram set | bijection to {0,1}⁶ | `core/gua64.py` |
| Cuo (错卦) | bitwise complement — antipodal vertex | `core/xiangshu.py` |
| Zong (综卦) | reverse the six-bit sequence — mirror | `core/xiangshu.py` |
| Hu (互卦) | lines 2-3-4 / 3-4-5 recombined | `core/xiangshu.py` |
| Changed line | Hamming distance 1, six unique neighbors | `core/gua_moe.py` |
| Affinity | `dot = 6 − 2·hamming` | `core/gua_moe.py` |
| Fang-Yuan map | square = space (8×8), circle = time (1→64) | `core/fangyuan.py` |
| Solar terms | 24-term time coordinate | `core/jieqi.py` |

`verify.py` re-checks the load-bearing invariants on every run, so an edit that
breaks the geometry fails loudly.

---

## Repository layout

```
fangyuan-yijing/
├── core/                       Zero-dependency algorithm modules
│   ├── gua64.py                64 hexagrams, lines, names, judgments
│   ├── fangyuan.py             Fang-Yuan square/circle,先天 numbering
│   ├── jieqi.py                24 solar terms
│   ├── xiangshu.py             Image-number relations: cuo/zong/hu, wuxing, directions
│   ├── gua_moe.py              Hypercube geometry: Hamming, dot, router
│   ├── gua_assign.py           Assignment/enrichment (needs numpy + local KB paths)
│   ├── sage.py                 "Sage thinking" retrieval layer (needs sentence-transformers)
│   ├── jingwen.py              Tuan zhuan, yao ci, small images (classical text)
│   └── ...                     fangyuan_dashboard, tuilian, qigua, verify_shuxue
├── data/                       SFT training corpus (JSONL, 9,738 records)
│   ├── sft_jingyi.jsonl        Four-step sage reasoning, classical text grounded
│   ├── axis1_train.jsonl       Math/structure axis — 1.5万 target
│   ├── axis1_eval.jsonl        Held-out evaluation set
│   ├── l3_traps.jsonl          Hallucination / logic-consistency traps
│   └── *_manifest.json         Dataset manifests
├── docs/                       Research and decision reports (Chinese)
│   ├── en/                     English editions
│   │   └── mathematical-verification.md  The 12 propositions, in English
│   ├── 数理可行性验证报告.md     The 12 falsifiable propositions (source of truth)
│   ├── 易经大模型-训练方案-v1.md Four-axis training plan, capability limits, gates
│   ├── 先天方圆图学习与应用报告.md Square=space / circle=time, how it plugs in
│   └── ...                     feasibility, audits, fixes, roadmap
├── web/                        Offline artifacts
│   └── 先天方圆图交互可视化.html  Single-file interactive map (117 KB)
├── tools/zhouyi_verify.py      Cross-check harness vs an external ZHOUYI source
├── verify.py                   Zero-dependency self-check (run this first)
├── .github/workflows/
│   └── validate.yml            CI: self-check + artifact integrity on push/PR
└── LICENSE                     MIT
```

**Optional heavier layers**: `core/gua_assign.py` and `core/sage.py` import
`numpy`/`sentence-transformers` and read from configurable paths
(`UNIFIED_BRAIN_INDEX`, `KB_POLICY_DB`, `BGE_M3_DIR`). They are not needed for
`verify.py` or the core geometry modules. Set those environment variables to
your own local paths if you want to use them.

---

## Training design (in brief)

The fine-tuning plan in [`docs/易经大模型-训练方案-v1.md`](docs/易经大模型-训练方案-v1.md)
is built on one distinction: a model only learns what can be written as a token
sequence. So:

- **What can be trained**: the 6-bit encoding, hexagram relations, classical text,
  and structured reasoning traces.
- **What cannot be trained as-is**: the image of the Fang-Yuan map, hypercube
  geometry — these are converted to "coordinate ↔ hexagram ↔ relation" triples.
- **Four axes**: structure (1.5万), semantics (5千), image/meaning (3千), logic (2千).
- **Capability gates**: L1 math is auto-graded 0/1; L3 logic consistency and
  hallucination rate are red lines. No claim is made that the model predicts
  the future or gives medical advice.

The datasets here are the usable output of that design, in the same message
format used for SFT (`{"messages": [{"role": ..., "content": ...}]}`).

---

## What this is not

- Not a divination service, and not a prediction engine.
- Not medical advice — nothing here diagnoses or treats anything.
- Not a claim that the hexagrams "encode modern science"; the claim is narrower:
  the *relations between hexagrams* form a well-defined structure that can be
  computed and used to organize classical text.
- Not a complete training pipeline: the heavier retrieval/embedding layers are
  included as reference code and require your own models and local data.

---

## License

MIT — see [`LICENSE`](LICENSE).

The classical texts (周易/彖传/爻辞 etc.) are public-domain heritage; the
commentary, datasets and code here are original to this project. The external
`ZHOUYI` Perl reference library is **not** included — do not copy it into a
MIT-licensed repo; see the note in `tools/zhouyi_verify.py`.

---

<div align="center">

**Fangyuan Yijing** · 圆图管时间，方图管空间 · structure first, meaning after

</div>
