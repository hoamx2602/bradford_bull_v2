"""Build the occlusion audit kit.

    python occlusion_audit.py            # sample and build the rating page
    python occlusion_audit.py --analyse  # once occlusion_audit/labels.csv is filled

Occlusion is not annotated in the dataset, so it is measured the same way team
attribution is (Section 5.4): a stratified sample, rated by eye against a fixed
scale, with the sampling rule and the judgements retained.

Sampling is stratified by sponsor class - nine instances per class, 153 in all -
so that a per-class occlusion rate can be estimated and set against the per-class
accuracy residuals from Section 5.7. Within a class the draw is random under a
fixed seed, so the sample is reproducible.

Each item is rendered with context around the logo, because occlusion cannot be
judged from a tight crop: the rater has to see what is covering the mark.
Objective features are recorded alongside so that, once the labels exist, they
can be checked against measurable proxies.
"""
from __future__ import annotations

import argparse
import base64
import csv
import io
import json
import random
import re
from collections import defaultdict
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent
DATA = ROOT.parent / "training-result" / "data"
OUT = ROOT / "occlusion_audit"
SPLITS = ["train", "valid", "test"]

PER_CLASS = 9
SEED = 11
CONTEXT = 2.6      # surroundings to show, as a multiple of the box's longer side
MIN_VIEW = 150     # ...but never a window narrower than this, in source pixels,
                   # since a small mark needs its surroundings to be judgeable
TILE = 300         # rendered tile size in pixels

LEVELS = [
    (0, "Unobstructed", "the whole mark is visible"),
    (1, "Partially covered", "part of the mark is hidden, but enough remains to read it"),
    (2, "Heavily covered", "most of the mark is hidden, or only a sliver shows"),
]


def brand_of(name: str) -> str:
    return re.sub(r"_(home|away)$", "", name)


def collect():
    items = []
    for split in SPLITS:
        j = json.loads((DATA / split / "_annotations.coco.json").read_text(encoding="utf-8"))
        cats = {c["id"]: brand_of(c["name"]) for c in j["categories"]}
        imgs = {im["id"]: im for im in j["images"]}
        for a in j["annotations"]:
            im = imgs[a["image_id"]]
            x, y, w, h = a["bbox"]
            if w < 8 or h < 8:
                continue
            items.append({
                "split": split,
                "file": im["file_name"],
                "brand": cats[a["category_id"]],
                "x": x, "y": y, "w": w, "h": h,
                "fw": im["width"], "fh": im["height"],
            })
    return items


def sample(items):
    by_brand = defaultdict(list)
    for it in items:
        by_brand[it["brand"]].append(it)
    rng = random.Random(SEED)
    chosen = []
    for brand in sorted(by_brand):
        pool = by_brand[brand]
        chosen += rng.sample(pool, min(PER_CLASS, len(pool)))
    rng.shuffle(chosen)          # rate in mixed order, so the class is not a cue
    return chosen


def render(it) -> tuple[str, dict]:
    """A context crop with the annotated box outlined, as a data URI."""
    path = DATA / it["split"] / it["file"]
    x, y, w, h = it["x"], it["y"], it["w"], it["h"]
    cx, cy = x + w / 2, y + h / 2
    side = max(max(w, h) * CONTEXT, MIN_VIEW)
    left, top = cx - side / 2, cy - side / 2
    right, bottom = cx + side / 2, cy + side / 2

    with Image.open(path) as im:
        frame = im.convert("RGB")
        crop = frame.crop((int(left), int(top), int(right), int(bottom)))
        gray = np.asarray(frame.convert("L").crop(
            (int(x), int(y), int(x + w), int(y + h))), dtype=float)

    scale = TILE / max(1, crop.width)
    crop = crop.resize((TILE, max(1, int(crop.height * scale))), Image.LANCZOS)
    draw = ImageDraw.Draw(crop)
    box = [(x - left) * scale, (y - top) * scale,
           (x + w - left) * scale, (y + h - top) * scale]
    draw.rectangle(box, outline=(235, 104, 52), width=2)

    buf = io.BytesIO()
    crop.save(buf, format="JPEG", quality=82)
    uri = "data:image/jpeg;base64," + base64.b64encode(buf.getvalue()).decode()

    edge = int(x <= 2 or y <= 2 or x + w >= it["fw"] - 2 or y + h >= it["fh"] - 2)
    features = {
        "area_pct": round(w * h / (it["fw"] * it["fh"]) * 100, 4),
        "height_px": int(h),
        "aspect": round(w / h, 3),
        "edge_touch": edge,
        "intensity_sd": round(float(gray.std()), 1) if gray.size else 0.0,
    }
    return uri, features


PAGE = """<!doctype html>
<meta charset="utf-8">
<title>Occlusion audit &mdash; LogoLens</title>
<style>
 :root {{ --ink:#0b0b0b; --ink2:#52514e; --muted:#898781; --line:#e1e0d9;
          --blue:#2a78d6; --surface:#fff; }}
 * {{ box-sizing:border-box; }}
 body {{ font:15px/1.5 system-ui,"Segoe UI",sans-serif; color:var(--ink);
        background:#f7f7f5; margin:0; padding:24px; }}
 header {{ max-width:1180px; margin:0 auto 20px; }}
 h1 {{ font-size:20px; margin:0 0 6px; }}
 p {{ color:var(--ink2); margin:6px 0; }}
 .key {{ display:flex; gap:18px; flex-wrap:wrap; margin:14px 0 0; padding:12px 14px;
        background:var(--surface); border:1px solid var(--line); border-radius:8px; }}
 .key div {{ font-size:13px; color:var(--ink2); }}
 .key b {{ color:var(--ink); }}
 #bar {{ position:sticky; top:0; z-index:5; max-width:1180px; margin:0 auto 16px;
        background:var(--surface); border:1px solid var(--line); border-radius:8px;
        padding:10px 14px; display:flex; align-items:center; gap:16px; }}
 #count {{ font-variant-numeric:tabular-nums; }}
 button {{ font:inherit; padding:7px 14px; border-radius:6px; border:1px solid var(--blue);
          background:var(--blue); color:#fff; cursor:pointer; }}
 button.ghost {{ background:var(--surface); color:var(--blue); }}
 button:disabled {{ opacity:.45; cursor:default; }}
 .grid {{ max-width:1180px; margin:0 auto; display:grid;
         grid-template-columns:repeat(auto-fill,minmax(272px,1fr)); gap:14px; }}
 .card {{ background:var(--surface); border:1px solid var(--line); border-radius:8px;
         padding:10px; }}
 .card.done {{ border-color:var(--blue); }}
 .card img {{ width:100%; border-radius:4px; display:block; background:#eee; }}
 .meta {{ font-size:12px; color:var(--muted); margin:7px 0 8px;
         display:flex; justify-content:space-between; }}
 .opts {{ display:flex; gap:6px; }}
 .opts label {{ flex:1; text-align:center; font-size:12.5px; padding:6px 2px;
               border:1px solid var(--line); border-radius:5px; cursor:pointer;
               color:var(--ink2); }}
 .opts input {{ display:none; }}
 .opts input:checked + span {{ font-weight:600; }}
 .opts label:has(input:checked) {{ background:var(--blue); border-color:var(--blue);
                                  color:#fff; }}
 textarea {{ width:100%; max-width:1180px; margin:16px auto; display:block; height:180px;
            font:12px/1.4 ui-monospace,Consolas,monospace; padding:10px;
            border:1px solid var(--line); border-radius:8px; }}
</style>
<header>
  <h1>Occlusion audit &mdash; {n} sponsor logos</h1>
  <p>The orange box marks the logo. Judge <b>only how much of the mark is covered
     by something in front of it</b> &mdash; another player, the ball, an arm, or the
     edge of the frame. Small, blurred or distant is <b>not</b> occluded.</p>
  <div class="key">
    <div><b>0 &middot; Unobstructed</b> &mdash; the whole mark is visible</div>
    <div><b>1 &middot; Partly covered</b> &mdash; part hidden, still readable</div>
    <div><b>2 &middot; Heavily covered</b> &mdash; most hidden, or a sliver only</div>
  </div>
</header>
<div id="bar">
  <span id="count">0 / {n} rated</span>
  <button id="copy" disabled>Copy CSV</button>
  <button id="dl" class="ghost" disabled>Download labels.csv</button>
  <span style="color:#898781;font-size:13px">Progress is saved in this browser.</span>
</div>
<div class="grid">{cards}</div>
<textarea id="out" placeholder="The CSV appears here once every item is rated."></textarea>
<script>
const N = {n};
const KEY = "logolens-occlusion-v1";
const saved = JSON.parse(localStorage.getItem(KEY) || "{{}}");
document.querySelectorAll("input[type=radio]").forEach(r => {{
  if (saved[r.name] === r.value) {{ r.checked = true; }}
  r.addEventListener("change", () => {{
    saved[r.name] = r.value;
    localStorage.setItem(KEY, JSON.stringify(saved));
    r.closest(".card").classList.add("done");
    refresh();
  }});
  if (r.checked) r.closest(".card").classList.add("done");
}});
function csv() {{
  let rows = ["id,brand,occlusion"];
  for (const el of document.querySelectorAll(".card")) {{
    const id = el.dataset.id, brand = el.dataset.brand;
    const v = saved["i" + id];
    if (v !== undefined) rows.push(`${{id}},${{brand}},${{v}}`);
  }}
  return rows.join("\\n");
}}
function refresh() {{
  const n = Object.keys(saved).length;
  document.getElementById("count").textContent = n + " / " + N + " rated";
  const done = n === N;
  document.getElementById("copy").disabled = !done;
  document.getElementById("dl").disabled = !done;
  if (done) document.getElementById("out").value = csv();
}}
document.getElementById("copy").onclick = () => navigator.clipboard.writeText(csv());
document.getElementById("dl").onclick = () => {{
  const b = new Blob([csv()], {{type:"text/csv"}});
  const a = document.createElement("a");
  a.href = URL.createObjectURL(b); a.download = "labels.csv"; a.click();
}};
refresh();
</script>
"""

CARD = """<div class="card" data-id="{id}" data-brand="{brand}">
  <img src="{uri}" alt="logo {id}" loading="lazy">
  <div class="meta"><span>#{id}</span><span>{height_px} px tall</span></div>
  <div class="opts">
    <label><input type="radio" name="i{id}" value="0"><span>0</span></label>
    <label><input type="radio" name="i{id}" value="1"><span>1</span></label>
    <label><input type="radio" name="i{id}" value="2"><span>2</span></label>
  </div>
</div>"""


def build():
    OUT.mkdir(exist_ok=True)
    chosen = sample(collect())
    cards, rows = [], []
    for i, it in enumerate(chosen, 1):
        uri, feats = render(it)
        cards.append(CARD.format(id=i, brand=it["brand"], uri=uri, **feats))
        rows.append({"id": i, "brand": it["brand"], "split": it["split"],
                     "file": it["file"], **feats})

    (OUT / "audit.html").write_text(
        PAGE.format(n=len(chosen), cards="\n".join(cards)), encoding="utf-8")
    with open(OUT / "sample.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)

    size_mb = (OUT / "audit.html").stat().st_size / 1e6
    print(f"{len(chosen)} items across {len({r['brand'] for r in rows})} classes")
    print(f"  {OUT / 'audit.html'}  ({size_mb:.1f} MB, self-contained)")
    print(f"  {OUT / 'sample.csv'}  (objective features per item)")
    print("\nOpen audit.html, rate every item, then save labels.csv into the same folder")
    print("and run:  python occlusion_audit.py --analyse")


def analyse():
    labels_path = OUT / "labels.csv"
    if not labels_path.exists():
        raise SystemExit(f"not found: {labels_path}\nRate the items in audit.html first.")
    labels = {int(r["id"]): int(r["occlusion"]) for r in
              csv.DictReader(open(labels_path, encoding="utf-8"))}
    rows = list(csv.DictReader(open(OUT / "sample.csv", encoding="utf-8")))
    for r in rows:
        r["occlusion"] = labels.get(int(r["id"]))
    rated = [r for r in rows if r["occlusion"] is not None]
    print(f"rated {len(rated)} of {len(rows)}")

    lv = np.array([r["occlusion"] for r in rated])
    print("\noverall distribution")
    for level, name, _ in LEVELS:
        n = int((lv == level).sum())
        print(f"  {level} {name:<20} {n:>4}  ({n / len(lv) * 100:.1f}%)")
    print(f"  any occlusion (1 or 2): {(lv >= 1).mean() * 100:.1f}%")

    print("\nby class (occlusion rate = share rated 1 or 2)")
    by = defaultdict(list)
    for r in rated:
        by[r["brand"]].append(r["occlusion"])
    for brand in sorted(by, key=lambda b: -np.mean([x >= 1 for x in by[b]])):
        v = np.array(by[brand])
        print(f"  {brand:<22} n={len(v):>2}  occluded {np.mean(v >= 1) * 100:5.1f}%  "
              f"mean level {v.mean():.2f}")

    print("\nagainst objective features")
    for key in ("height_px", "area_pct", "aspect", "intensity_sd"):
        x = np.array([float(r[key]) for r in rated])
        r_ = np.corrcoef(x, lv)[0, 1]
        print(f"  {key:<14} r = {r_:+.3f}")
    edge = np.array([int(r["edge_touch"]) for r in rated])
    print(f"  edge_touch     occluded rate {np.mean(lv[edge == 1] >= 1) * 100:.1f}% "
          f"(n={int(edge.sum())}) vs {np.mean(lv[edge == 0] >= 1) * 100:.1f}% otherwise")

    out = OUT / "occlusion_by_class.csv"
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["brand", "n", "occluded_rate", "mean_level"])
        for brand, v in sorted(by.items()):
            v = np.array(v)
            w.writerow([brand, len(v), round(float(np.mean(v >= 1)), 4),
                        round(float(v.mean()), 3)])
    print(f"\nwrote {out}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--analyse", action="store_true")
    a = ap.parse_args()
    analyse() if a.analyse else build()
