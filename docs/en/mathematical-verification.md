# The 64 Hexagrams as a 6-Dimensional Hypercube — Mathematical Verification

> **Purpose.** Before spending compute (downloading Qwen3-14B, running LoRA fine-tuning), establish that the
> "hexagram-centred model" is mathematically sound — not a mystical analogy, but an exact isomorphism that
> can be falsified and trained on.
>
> **Method.** The core claim is decomposed into 12 independently falsifiable propositions, written as
> executable assertions and run one by one. All green = the mathematics holds.
>
> This is the English rendering of [`../数理可行性验证报告.md`](../数理可行性验证报告.md). The numbers are
> identical; only the prose language differs. If the two ever disagree, the Chinese file is the source.

---

## 1. The core claim

**The 64 hexagrams are the 64 vertices of a 6-dimensional Boolean hypercube.**

- Each line is one bit: yang = 1, yin = 0.
- Six lines = six bits, and 2⁶ = 64 vertices.
- Every classical relation between hexagrams therefore becomes **computable geometry** rather than a
  textual concept.

The 12 propositions below pin that claim down line by line.

---

## 2. Twelve propositions, all passing

| # | Proposition | Meaning | Result |
|---|---|---|---|
| P1 | Bijection | 64 hexagrams ↔ the whole of {0,1}⁶, no duplicates, no gaps | ✅ |
| P2 | Cuo = antipode | Flipping all six lines = the opposite vector in the embedding | ✅ |
| P3 | Changed line = adjacent vertex | Changing one line = Hamming distance exactly 1; the 6 neighbours are unique | ✅ |
| P4 | Zong = mirror | Turning the figure upside down = reversing the bit order | ✅ |
| P5 | Dot–distance linear law | `dot = 6 − 2·hamming` — affinity is fully determined by distance | ✅ |
| P6 | Router self-hit | At low temperature, top-1 always hits the hexagram itself | ✅ |
| P7 | Cuo has minimum weight | The antipodal vertex ranks last globally under softmax | ✅ |
| P8 | Normalisation | Softmax weights over all 64 sum to 1 | ✅ |
| P9 | Antipodal pairing | {hexagram, cuo} forms exactly 32 disjoint pairs | ✅ |
| P10 | Hypercube graph | 64 vertices × 6 neighbours = 192 undirected edges, symmetric | ✅ |
| P11 | Degree distribution = binomial | The number of hexagrams at distance k is C(6,k) | ✅ |
| P12 | Structural prior is reachable | An embedding exists where antipodal/adjacency constraints have loss = 0 (not ill-posed) | ✅ |

**Result: 12/12 passing. The mathematics holds; the project can proceed to training.**

---

## 3. The three conclusions that matter

### 3.1 Affinity is entirely determined by Hamming distance (P5 + P11)

With ±1 embeddings, the dot product equals `6 − 2·hamming`, so it can only take the values
{-6, -4, -2, 0, 2, 4, 6}. For any hexagram, the number of hexagrams at distance k is exactly the binomial
coefficient C(6,k):

| distance k | 0 | 1 | 2 | 3 | 4 | 5 | 6 |
|---|---|---|---|---|---|---|---|
| count | 1 | 6 | 15 | 20 | 15 | 6 | 1 |

This `1-6-15-20-15-6-1` distribution is the **fingerprint of a 6-dimensional hypercube** — only a genuine
6-cube has this degree distribution. P11 passing is therefore equivalent to proving that the 64 hexagrams
*are* a 6-cube: not approximately, not metaphorically.

### 3.2 Every classical relation is a geometric operation (P2/P3/P4)

| Yijing concept | Geometric equivalent |
|---|---|
| Cuo 错卦 (all six lines inverted) | Antipodal point (the vertex in the opposite direction through the centre) |
| Changed line 动爻 (one line flipped) | Walking one edge to an adjacent vertex |
| Zong 综卦 (figure turned upside down) | Hyperplane mirror |
| Affinity between hexagrams | Hamming distance (how many bits differ) |

So "fix a hexagram, then reason" becomes pure geometric computation that can be handed to a model as
trainable parameters.

### 3.3 The structural prior is not wishful — it is a reachable optimum (P12)

Using `embed(no)` itself as the expert embedding simultaneously satisfies all three structural constraints
(cuo flips sign, changed line is positively correlated with adjacency, self-hit is maximal) with **loss = 0**.
The optimisation problem is therefore **well-posed**: a feasible solution exists at training time, and it
will not collapse into an ill-posed or unsolvable state.

---

## 4. Feasibility estimate — boundaries, not defects

| Dimension | Estimate | Judgement |
|---|---|---|
| MoE parameter count | only 229k parameters at output dimension 512 | Trains comfortably on a GB10 |
| Compute bottleneck | Qwen3-14B LoRA + the input projection encoder | This is where the real spend is |
| Data volume | 504 corpus pairs is thin for a MoE | The structural prior lets a program generate unlimited legal samples — not a hard bottleneck |
| Overfitting risk | 64 experts with little data | Mitigated by antipodal/adjacency regularisation and weight sharing |

**In one sentence:** the *structure* is provably correct (the 12 propositions above); the *quality of
meaning-level interpretation* still depends on the Qwen fine-tune and must be evaluated at stage 4. The
former carries no remaining risk; the latter is the actual work training has to do.

---

## 5. Reproducing this

The self-check is zero-dependency:

```bash
git clone https://github.com/simaqi123/fangyuan-yijing.git
cd fangyuan-yijing
python verify.py
```

Expected output ends with `结果：全部通过` ("all checks passed"). The invariant harness lives in
`verify.py`; the modules it exercises are in `core/` (`gua64.py`, `xiangshu.py`, `gua_moe.py`,
`fangyuan.py`).

---

## 6. What this document does *not* claim

- It does not claim the hexagrams encode modern science. The claim is narrower: **the relations between
  hexagrams form a well-defined structure that can be computed**, and that structure is a 6-cube.
- It does not claim the model predicts anything. P12 establishes that a structural prior is *reachable*,
  not that a trained model produces meaningful readings.
- It is not an argument from tradition. Long use is not evidence; the 12 assertions are.

---

*English rendering of [`../数理可行性验证报告.md`](../数理可行性验证报告.md). Issues and corrections welcome
— especially if you can find a counterexample to P2, P3 or P4.*
