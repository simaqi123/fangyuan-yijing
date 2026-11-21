#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""先天方圆图 · 交互式可视化（8787 巡检页新增模块）。

产出【自包含】HTML：内嵌 64 卦全息数据 + 方图(8×8 空间) + 圆图(64 位时间) SVG，
点击任一卦显示：卦辞/彖传/大象/爻辞 + 卦德五行方位 + 先天数/方圆坐标 +
辟卦节气/律吕/黄道次 + 错/综/互卦推演链。

数据全部由模块实时推算（gua64/jingwen/xiangshu/fangyuan/jieqi/tuilian），
不依赖 db 建表，因此本地即可测试、页面永远与代码一致。
"""
from __future__ import annotations

import json

from gua64 import gua_rows
from jingwen import TUAN, YAO
from xiangshu import cuo_zong_hu, gua_de, gua_wuxing, gua_fangwei, rows_name
from fangyuan import xian_tian, fangtu_pos, yuantu_order, xian_fangwei
import jieqi


def fangyuan_data() -> list:
    """64 卦全息数据（供 HTML 内嵌 / JSON 接口）。"""
    rows = gua_rows()
    out = []
    for r in rows:
        no = r['gua_no']
        rel = cuo_zong_hu(no)
        up_num, down_num = xian_tian(no)
        row, col = fangtu_pos(no)
        j = jieqi.gua_jieqi(no)
        yaos = YAO.get(no, [])
        out.append({
            "no": no, "name": r['name'], "symbol": r['symbol'],
            "up": r['up_nature'], "down": r['down_nature'],
            "ci": r['ci'], "xiang": r['xiang'], "tuan": TUAN.get(no, ""),
            "core": r['core'], "modern": r['modern'],
            "de": gua_de(no), "wuxing": gua_wuxing(no), "fw": gua_fangwei(no),
            "xian": "上%s下%s" % (up_num, down_num),
            "fang": "行%s列%s" % (row, col),
            "yuantu": yuantu_order(no), "xianfw": xian_fangwei(no),
            "phys": jieqi._phys_pos(yuantu_order(no)),
            "pigua": j["辟卦"], "yue": j["月"], "dizhi": j["地支"],
            "lvlu": j["律吕"], "huangdao": j["黄道次"], "jieqi": j["节气"],
            "is_xiaoxi": j["is_xiaoxi"],
            "cuo": rows_name(rel["错卦"]), "zong": rows_name(rel["综卦"]),
            "hu": rows_name(rel["互卦"]),
            "yaos": [{"t": t, "c": c, "x": x} for t, c, x in yaos],
        })
    return out


# ============================================================ SVG 生成
def _fangtu_svg() -> str:
    """方图 8×8（空间）：行=下卦先天数(下→上)，列=上卦先天数(右→左)，乾右下、坤左上。"""
    size = 54
    gap = 1
    W = 8 * size + 40
    cells = []
    for d in fangyuan_data():
        row, col = d['fang'].replace('行', '').replace('列', ' ').split()
        row, col = int(row), int(col)
        x = (8 - col) * size
        y = (8 - row) * size
        cls = "xiaoxi" if d["is_xiaoxi"] else ""
        cells.append(
            f'<g class="cell {cls}" data-no="{d["no"]}" transform="translate({x},{y})">'
            f'<rect width="{size-gap}" height="{size-gap}" rx="4"/>'
            f'<text x="{(size-gap)/2}" y="22" class="sym">{d["symbol"]}</text>'
            f'<text x="{(size-gap)/2}" y="44" class="nm">{d["name"]}</text>'
            f'</g>')
    return (
        f'<svg viewBox="0 0 {W} {W}" class="fangtu">'
        f'<rect x="0" y="0" width="{W}" height="{W}" class="bg" rx="6"/>'
        f'{"".join(cells)}</svg>')


def _yuantu_svg() -> str:
    """圆图 64 位（时间）：按物理位置 phys 排圆周，乾顶、复坤底、姤乾相邻。"""
    cx, cy, r = 220, 220, 185
    dots = []
    for d in fangyuan_data():
        p = d["phys"]
        ang = (p - 1) * 360.0 / 64.0
        import math
        rad = math.radians(ang)
        x = cx + r * math.sin(rad)
        y = cy - r * math.cos(rad)
        cls = "xiaoxi" if d["is_xiaoxi"] else ""
        dots.append(
            f'<g class="dot {cls}" data-no="{d["no"]}" transform="translate({x:.1f},{y:.1f})">'
            f'<circle r="15"/>'
            f'<text y="4" class="dnm">{d["name"]}</text>'
            f'</g>')
    # 内圈标注四时锚点
    ann = (
        f'<text x="{cx}" y="{cy-r-14}" class="anchor" text-anchor="middle">乾·夏至</text>'
        f'<text x="{cx}" y="{cy+r+24}" class="anchor" text-anchor="middle">坤·冬至</text>'
        f'<text x="{cx+r+30}" y="{cy+4}" class="anchor" text-anchor="middle">春分</text>'
        f'<text x="{cx-r-30}" y="{cy+4}" class="anchor" text-anchor="middle">秋分</text>')
    return (
        f'<svg viewBox="0 0 440 440" class="yuantu">'
        f'<circle cx="{cx}" cy="{cy}" r="{r}" class="ring"/>'
        f'{ann}{"".join(dots)}</svg>')


def fangyuan_page() -> str:
    """返回完整自包含 HTML 页面。"""
    data = fangyuan_data()
    data_json = json.dumps(data, ensure_ascii=False)
    fang = _fangtu_svg()
    yuan = _yuantu_svg()
    return _HTML.replace("__FANGTU__", fang).replace("__YUANTU__", yuan) \
        .replace("__DATA__", data_json)


_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>先天六十四卦方圆图 · 时空推演</title>
<style>
  :root { --bg:#f6f4ef; --card:#fffdf7; --ink:#2b2a26; --sub:#8a857a;
          --line:#e3ddcf; --yang:#c26a2e; --yin:#2e6f8e; --gold:#b8860b; }
  * { box-sizing:border-box; }
  body { margin:0; font-family:"Songti SC","Noto Serif CJK SC",serif;
         background:var(--bg); color:var(--ink); }
  header { padding:22px 28px 8px; border-bottom:1px solid var(--line); }
  header h1 { margin:0 0 4px; font-size:24px; letter-spacing:2px; }
  header p { margin:0; color:var(--sub); font-size:13px; }
  .wrap { display:flex; gap:22px; padding:20px 28px; flex-wrap:wrap; align-items:flex-start; }
  .board { background:var(--card); border:1px solid var(--line); border-radius:10px;
           padding:14px; }
  .board h2 { margin:0 0 10px; font-size:15px; color:var(--sub); font-weight:600; }
  svg .bg { fill:#faf7ef; }
  .cell rect { fill:#f2ede0; stroke:#d8d0bc; cursor:pointer; }
  .cell text.sym { font-size:16px; fill:#777; text-anchor:middle; }
  .cell text.nm { font-size:13px; fill:var(--ink); text-anchor:middle; }
  .cell.xiaoxi rect { fill:#f4e7c8; stroke:var(--gold); stroke-width:1.6; }
  .cell:hover rect { fill:#f7e3bb; stroke:var(--gold); }
  .dot circle { fill:#e8e2d2; stroke:#cfc6ae; cursor:pointer; }
  .dot text.dnm { font-size:11px; fill:var(--ink); text-anchor:middle; }
  .dot.xiaoxi circle { fill:#f4e7c8; stroke:var(--gold); stroke-width:1.8; }
  .dot:hover circle { fill:#f7d98f; stroke:var(--gold); }
  .ring { fill:none; stroke:var(--line); stroke-width:2; }
  .anchor { font-size:12px; fill:var(--sub); }
  #detail { flex:1 1 380px; min-width:320px; background:var(--card);
            border:1px solid var(--line); border-radius:10px; padding:18px 20px; }
  #detail h3 { margin:0 0 2px; font-size:22px; }
  #detail .sub { color:var(--sub); font-size:13px; margin-bottom:10px; }
  #detail .kv { font-size:13px; line-height:1.9; }
  #detail .kv b { color:var(--gold); }
  #detail .block { margin-top:10px; padding-top:8px; border-top:1px dashed var(--line); }
  #detail .lbl { font-size:12px; color:var(--sub); letter-spacing:1px; }
  #detail .txt { font-size:14px; line-height:1.8; }
  #detail .yao { font-size:13px; line-height:1.7; color:#4a463e; }
  #detail .tui { white-space:pre-wrap; font-size:12.5px; line-height:1.7;
                 background:#fbf6ea; border:1px solid var(--line); border-radius:6px;
                 padding:10px; color:#4a463e; }
  .hint { color:var(--sub); font-size:12px; }
</style>
</head>
<body>
<header>
  <h1>先天六十四卦方圆图 · 时空推演</h1>
  <p>方图管空间 · 圆图管时间 · 金框为十二消息卦（值月辟卦）。点击任意卦查看全息与推演链。</p>
</header>
<div class="wrap">
  <div class="board"><h2>方图 · 空间（乾右下 · 坤左上）</h2>__FANGTU__</div>
  <div class="board"><h2>圆图 · 时间（乾夏至 · 坤冬至）</h2>__YUANTU__</div>
  <div id="detail"><div class="hint">点击方图或圆图中的卦位查看详情</div></div>
</div>
<script>
const DATA = __DATA__;
const BYNO = {}; DATA.forEach(d => BYNO[d.no] = d);
function esc(s){ return (s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;'); }
function show(no){
  const d = BYNO[no]; if(!d) return;
  const ys = d.yaos.map(y => y.t + '：' + y.c + (y.x ? '（' + y.x + '）' : '')).join('<br>');
  const tui =
    '【此卦】' + d.name + '（' + d.de + '）值 ' + d.jieqi + '（' + d.yue + d.dizhi +
    '，律' + d.lvlu + '·' + d.huangdao + '）' + '\\n' +
    '  五行' + d.wuxing + '　方位' + d.fw + '　先天数' + d.xian + '　方图' + d.fang +
    '　圆图第' + d.yuantu + '位　先天方位' + d.xianfw + '\\n\\n' +
    '【错卦·变之极】' + d.cuo + ' —— 六爻阴阳全变，物极必反、对立转化' + '\\n' +
    '【综卦·反之观】' + d.zong + ' —— 卦象上下颠倒，换位再观、反求诸己' + '\\n' +
    '【互卦·中之变】' + d.hu + ' —— 二三四五爻互体，事态中段、内部演变';
  document.getElementById('detail').innerHTML =
    '<h3>' + esc(d.name) + ' <span style="font-size:18px">' + esc(d.symbol) + '</span></h3>' +
    '<div class="sub">第' + d.no + '卦 · 上' + d.up + '下' + d.down +
    (d.is_xiaoxi ? ' · <b>消息卦</b>' : '') + '</div>' +
    '<div class="kv">' +
    '<b>卦辞</b> ' + esc(d.ci) + '<br>' +
    '<b>彖传</b> ' + esc(d.tuan) + '<br>' +
    '<b>大象</b> ' + esc(d.xiang) + '<br>' +
    '<b>核心义</b> ' + esc(d.core) + '<br>' +
    '<b>现代语义</b> ' + esc(d.modern) + '</div>' +
    '<div class="kv block">' +
    '<b>卦德</b> ' + esc(d.de) + '　<b>五行</b> ' + esc(d.wuxing) +
    '　<b>方位</b> ' + esc(d.fw) + '<br>' +
    '<b>先天数</b> ' + esc(d.xian) + '　<b>方图(空间)</b> ' + esc(d.fang) +
    '　<b>圆图(时间)</b> 第' + d.yuantu + '位<br>' +
    '<b>先天方位</b> ' + esc(d.xianfw) + '<br>' +
    '<b>值月</b> ' + esc(d.yue) + '（' + d.dizhi + '）　<b>节气</b> ' + esc(d.jieqi) + '<br>' +
    '<b>律吕</b> ' + esc(d.lvlu) + '　<b>黄道次</b> ' + esc(d.huangdao) + '<br>' +
    '<b>错卦</b> ' + esc(d.cuo) + '　<b>综卦</b> ' + esc(d.zong) + '　<b>互卦</b> ' + esc(d.hu) +
    '</div>' +
    '<div class="block"><div class="lbl">爻辞</div><div class="yao">' + ys + '</div></div>' +
    '<div class="block"><div class="lbl">时空推演链</div><div class="tui">' + esc(tui) + '</div></div>';
}
document.querySelectorAll('[data-no]').forEach(el => {
  el.addEventListener('click', () => show(parseInt(el.dataset.no)));
});
show(1);
</script>
</body>
</html>
"""


if __name__ == "__main__":
    data = fangyuan_data()
    print(f"方圆图数据 {len(data)} 卦")
    print("示例（乾）：", json.dumps(data[0], ensure_ascii=False)[:200])
    html = fangyuan_page()
    out = "/tmp/fangyuan_test.html"
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"HTML 已生成: {out} ({len(html)} 字节)")
