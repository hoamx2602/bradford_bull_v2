"""Visual smoke test for the inventory WHERE student on person crops.

The WHERE student is trained on broadcast person crops, not full frames.  This
tool makes that contract visible: detect people, run the logo student inside
each sufficiently large person crop, and save an overlay plus inspectable
per-person/logo crops.

Example:
    python inventory/visualize_student.py --video data/real/frame.jpg \
        --student runs/detect/runs/student_v2/weights/best.pt --out results/student_smoke
"""
from __future__ import annotations

import argparse
from pathlib import Path

import cv2


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--video", required=True, help="image or video source")
    ap.add_argument("--student", required=True, help="class-agnostic logo student weights")
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--person-model", default="yolo26n.pt")
    ap.add_argument("--frame", type=int, default=0, help="frame index when source is a video")
    ap.add_argument("--person-conf", type=float, default=0.35)
    ap.add_argument("--logo-conf", type=float, default=0.10)
    ap.add_argument("--imgsz", type=int, default=640)
    ap.add_argument("--device", default="cuda")
    a = ap.parse_args()

    from ultralytics import YOLO

    a.out.mkdir(parents=True, exist_ok=True)
    source = Path(a.video)
    if source.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp"}:
        frame = cv2.imread(str(source))
    else:
        cap = cv2.VideoCapture(str(source))
        cap.set(cv2.CAP_PROP_POS_FRAMES, a.frame)
        ok, frame = cap.read()
        cap.release()
        if not ok:
            raise SystemExit(f"Cannot read frame {a.frame} from {source}")
    if frame is None:
        raise SystemExit(f"Cannot read {source}")

    person_model = YOLO(a.person_model)
    student = YOLO(a.student)
    (a.out / "persons").mkdir(exist_ok=True)
    (a.out / "crops").mkdir(exist_ok=True)
    persons = person_model.predict(frame, classes=[0], conf=a.person_conf,
                                   imgsz=a.imgsz, device=a.device, verbose=False)[0]
    overlay = frame.copy()
    n_people = n_logos = 0
    for pi, pbox in enumerate(persons.boxes.xyxy.cpu().numpy() if persons.boxes else []):
        x0, y0, x1, y1 = (int(v) for v in pbox)
        h, w = y1 - y0, x1 - x0
        if h < 90 or w < 20:
            continue
        pad_x, pad_y = int(w * 0.06), int(h * 0.06)
        px0, py0 = max(0, x0 - pad_x), max(0, y0 - pad_y)
        px1, py1 = min(frame.shape[1], x1 + pad_x), min(frame.shape[0], y1 + pad_y)
        person = frame[py0:py1, px0:px1]
        if person.size == 0:
            continue
        n_people += 1
        cv2.rectangle(overlay, (px0, py0), (px1, py1), (135, 135, 135), 1)
        result = student.predict(person, conf=a.logo_conf, imgsz=a.imgsz,
                                 device=a.device, verbose=False)[0]
        person_vis = person.copy()
        for li, b in enumerate(result.boxes.xyxy.cpu().numpy() if result.boxes else []):
            lx0, ly0, lx1, ly1 = (int(v) for v in b)
            conf = float(result.boxes.conf[li])
            gx0, gy0, gx1, gy1 = px0 + lx0, py0 + ly0, px0 + lx1, py0 + ly1
            cv2.rectangle(overlay, (gx0, gy0), (gx1, gy1), (0, 190, 0), 2)
            cv2.putText(overlay, f"logo {conf:.2f}", (gx0, max(18, gy0 - 5)),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 190, 0), 1)
            cv2.rectangle(person_vis, (lx0, ly0), (lx1, ly1), (0, 190, 0), 2)
            logo = person[max(0, ly0):ly1, max(0, lx0):lx1]
            if logo.size:
                cv2.imwrite(str(a.out / "crops" / f"p{pi:02d}_l{li:02d}.jpg"), logo)
            n_logos += 1
        cv2.imwrite(str(a.out / "persons" / f"person_{pi:02d}.jpg"), person_vis)

    cv2.imwrite(str(a.out / "overlay.jpg"), overlay)
    print(f"[student-viz] people={n_people}, logo boxes={n_logos} -> {a.out}")


if __name__ == "__main__":
    main()
