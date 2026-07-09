"""SigLIP2 image->brand-name-text matcher (WHAT tier, né pixel-gap template).

Thay vì so ảnh crop với ảnh template (gap template-sạch↔broadcast-mờ đã giết DINOv2),
ta so ảnh crop với EMBEDDING TÊN BRAND (text). SigLIP2 là dual-encoder image-text,
mạnh với wordmark. Distractor text (out-of-roster) cho reject unknown tự động.

    python auto_label/siglip_textmatch.py --crops data/real/trackS/crops \
        --out data/trackS_siglip.jsonl
"""
from __future__ import annotations
import argparse, json
from pathlib import Path
import numpy as np, cv2

# tên brand mô tả (roster) — key khớp gallery
ROSTER = {
    "aon": "AON", "cch": "Cedar Court Hotels", "chadlaw": "Chadwick Lawrence solicitors",
    "klg": "KLG", "acs": "ACS Group", "bartercard": "Bartercard",
    "fairway_flooring": "Fairway Roofing", "mcp": "MCP", "mna_cladding": "MNA Cladding",
    "mna_support": "MNA Support Services", "romantica": "Romantica Beds",
    "paints_laquers": "Paints and Lacquers", "atm_hospitality": "ATM Hospitality",
    "em_workwear": "EM Workwear", "floor_tonic": "Floor Tonic", "top_notch": "Top Notch",
}
# out-of-roster (giải/đối thủ/đồ hoạ) -> nhãn "unknown"
DISTRACT = {
    "betfred": "Betfred", "brewdog": "BrewDog", "bm": "B&M Bargains", "eft": "EFT Group",
    "stainforth": "Stainforth", "superleague": "Super League", "dominos": "Dominos",
    "crest": "sports club crest badge", "grass": "green grass field", "jersey": "sports jersey fabric",
}
PROMPT = "a photo of the {} logo"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--crops", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--model", default="google/siglip2-base-patch16-256")
    ap.add_argument("--min-longest", type=int, default=0)
    a = ap.parse_args()
    import torch
    from transformers import AutoModel, AutoProcessor
    from PIL import Image
    dev = "cuda" if torch.cuda.is_available() else "cpu"
    proc = AutoProcessor.from_pretrained(a.model)
    model = AutoModel.from_pretrained(a.model).to(dev).eval()

    keys = list(ROSTER) + list(DISTRACT)
    names = list(ROSTER.values()) + list(DISTRACT.values())
    prompts = [PROMPT.format(n) for n in names]
    with torch.no_grad():
        tin = proc(text=prompts, return_tensors="pt", padding="max_length").to(dev)
        temb = torch.nn.functional.normalize(model.get_text_features(**tin), dim=-1)

    crops = sorted(Path(a.crops).glob("*.png")) + sorted(Path(a.crops).glob("*.jpg"))
    out = []
    B = 64
    batch, stems = [], []
    def flush():
        if not batch: return
        with torch.no_grad():
            iin = proc(images=batch, return_tensors="pt").to(dev)
            iemb = torch.nn.functional.normalize(model.get_image_features(**iin), dim=-1)
            sims = (iemb @ temb.T).cpu().numpy()  # (b, nkeys)
        for st, sc in zip(stems, sims):
            order = np.argsort(-sc)
            top = keys[order[0]]; top_s = float(sc[order[0]])
            top2 = float(sc[order[1]])
            pred = "unknown" if top in DISTRACT else top
            out.append({"id": f"crops/{st}", "pred": pred, "top_key": top,
                        "sim": round(top_s, 4), "margin": round(top_s - top2, 4)})
        batch.clear(); stems.clear()
    for p in crops:
        im = cv2.imread(str(p), cv2.IMREAD_UNCHANGED)
        if im is None: continue
        h, w = im.shape[:2]
        if max(h, w) < a.min_longest: continue
        if im.ndim == 3 and im.shape[2] == 4:
            al = im[:, :, 3:4] / 255.0; im = (im[:, :, :3] * al + 255 * (1 - al)).astype(np.uint8)
        rgb = cv2.cvtColor(im, cv2.COLOR_BGR2RGB)
        batch.append(Image.fromarray(rgb)); stems.append(p.stem)
        if len(batch) >= B: flush()
    flush()
    Path(a.out).write_text("\n".join(json.dumps(o) for o in out), encoding="utf-8")
    print(f"[siglip] {len(out)} crop -> {a.out}")


if __name__ == "__main__":
    main()
