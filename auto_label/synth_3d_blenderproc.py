"""Bậc 4 — 3D simulation (BlenderProc): UV-map logo thật lên áo + render + nhãn tự.

Xem `../bac4_3d_simulation.md` và `../docs/3d-synthetic-tools.md` (so sánh tool).
Đây là "data factory" 3D: body (SMPL) + áo rugby (mesh có UV) + logo THẬT UV-map +
cloth sim + pose + domain randomization → ảnh + **nhãn HOÀN HẢO tự động** (bbox/OBB,
mask, % visibility kể cả khi bị che) cho Tầng 1 & 2.

⚠ KHÔNG chạy bằng python thường — chạy qua BlenderProc:
    pip install blenderproc        # tải Blender riêng
    blenderproc run auto_label/synth_3d_blenderproc.py \
        --jersey assets/rugby_jersey.obj --body assets/body_smpl.obj \
        --logo "Sponsor Logo/1 - aon_logo_white_rgb (3).png" --out data/synth_b4 --n 200

Đây là SKELETON (điểm cắm asset/pose). Cần: mesh áo có UV layout, body SMPL/SMPL-X,
pose rugby (AMASS/mocap), HDRI. % visibility = pixel_logo_hiện / pixel_logo_nếu_không_che.
"""
from __future__ import annotations

import argparse
import sys


def build_scene(args):
    import blenderproc as bproc
    import numpy as np
    bproc.init()

    # 1. BODY + 2. POSE ------------------------------------------------------ #
    body = bproc.loader.load_obj(args.body)[0]
    # apply_random_pose(body, amass_clip=random.choice(POSES))  # ◀ cắm AMASS/mocap

    # 3. GARMENT — áo rugby có UV layout chuẩn ------------------------------- #
    jersey = bproc.loader.load_obj(args.jersey)[0]

    # 4. LOGO — UV-map ảnh logo THẬT vào ô áo (label fidelity) --------------- #
    logo_mat = bproc.material.create_material_from_texture(args.logo, "logo")
    logo_mat.set_principled_shader_value("Roughness", 0.7)
    jersey.add_material(logo_mat)            # gán vào slot UV ngực/vai/tay
    logo_mat.set_cp("category_id", 1)        # material id để tách mask logo

    # 5. CLOTH SIM (Blender cloth / PhysX) — nếp gấp vật lý ------------------ #
    # bproc.object.simulate_cloth(jersey, body, ...)   # ◀ điểm cắm cloth sim

    # 6. SCENE — sân/khung thành/đa cầu thủ (occlusion thật) ----------------- #
    light = bproc.types.Light(); light.set_type("SUN")

    # 8. DOMAIN RANDOMIZATION (§5 bac4) ------------------------------------- #
    def randomize():
        light.set_energy(np.random.uniform(2, 8))
        bproc.camera.add_camera_pose(_random_broadcast_view())

    return body, jersey, logo_mat, randomize


def _random_broadcast_view():
    import numpy as np
    import blenderproc as bproc
    loc = np.random.uniform([-3, -6, 1.2], [3, -2, 2.5])      # góc broadcast
    poi = np.array([0, 0, 1.0])
    rot = bproc.camera.rotation_from_forward_vec(poi - loc)
    return bproc.math.build_transformation_mat(loc, rot)


def render(args, body, jersey, logo_mat, randomize):
    import blenderproc as bproc
    bproc.renderer.enable_segmentation_output(map_by=["instance", "category_id"])
    bproc.renderer.set_max_amount_of_samples(64)            # Cycles PBR
    for i in range(args.n):
        randomize()
        data = bproc.renderer.render()
        seg = data["category_id_segmaps"]                  # mask theo material
        # bbox/OBB + % visibility tính từ seg (pixel logo hiện / nếu không che)
        # bproc.writer.write_coco_annotations(...)         # ◀ xuất COCO/YOLO
    print(f"[synth-b4] rendered {args.n} frame (cắm writer COCO/YOLO + visibility).")


def main():
    ap = argparse.ArgumentParser(description="Bậc 4 — BlenderProc 3D (skeleton)")
    ap.add_argument("--jersey", required=True)
    ap.add_argument("--body", required=True)
    ap.add_argument("--logo", required=True)
    ap.add_argument("--out", default="data/synth_b4")
    ap.add_argument("--n", type=int, default=200)
    a = ap.parse_args()
    try:
        import blenderproc  # noqa: F401
    except Exception:
        sys.exit("⚠ Chạy bằng: `blenderproc run auto_label/synth_3d_blenderproc.py ...` "
                 "(cài: pip install blenderproc). Xem ../docs/3d-synthetic-tools.md")
    body, jersey, logo_mat, randomize = build_scene(a)
    render(a, body, jersey, logo_mat, randomize)


if __name__ == "__main__":
    main()
