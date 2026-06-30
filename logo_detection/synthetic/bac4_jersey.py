#!/usr/bin/env python3
"""
Bac 4 (P1.5) — logo on jersey + domain randomization (DR).  RUNS INSIDE BLENDER:

    blender --background --python bac4_jersey.py -- --n 8 --out data_bac4_jersey

P1.5 additions over P1:
  • HDRI lighting  (--hdri dir-or-file; fallback: procedural sky)
  • Body tilt       (--body-tilt 15 deg max  → lean/twist)
  • Camera roll     (subtle handheld feel)
  • JPEG quality    (--jpeg-min 65 --jpeg-max 92  → broadcast compression)
  • Film grain      (Cycles film exposure randomization)
  • Skin-tone DR    (randomized body base color)
  • Motion blur     (--motion-blur flag; camera keyframe shake)

Body asset (CC0, download once to assets/makehuman_base.obj):
    https://raw.githubusercontent.com/makehumancommunity/makehuman/master/makehuman/data/3dobjs/base.obj

Stadium HDRIs (free download):
    https://hdri-haven.com  (filter: outdoor stadium/sports)
    Place .hdr or .exr files in any directory, pass as --hdri <dir>.
"""
import sys
import math
import random
import argparse
from pathlib import Path

import bpy
import bmesh
import numpy as np
from mathutils import Vector, Euler

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

from bac4_cloth import (clear_scene, setup_cycles, add_lights,
                        bbox_from_mask, to_yolo)
BODY = HERE / "assets" / "makehuman_base.obj"


def parse_args():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    p = argparse.ArgumentParser()
    p.add_argument("--logos", default=str(HERE.parents[1] / "Sponsor Logo"))
    p.add_argument("--body", default=str(BODY))
    p.add_argument("--out", default=str(HERE / "data_bac4_jersey"))
    p.add_argument("--n", type=int, default=8)
    p.add_argument("--val-frac", type=float, default=0.10)
    p.add_argument("--res", type=int, default=1024)
    p.add_argument("--samples", type=int, default=96)
    p.add_argument("--device", default="OPTIX", choices=["OPTIX", "CUDA", "CPU"])
    p.add_argument("--seed", type=int, default=0)
    # chest panel geometry
    p.add_argument("--chest-zlo", type=float, default=0.60)
    p.add_argument("--chest-zhi", type=float, default=0.82)
    p.add_argument("--chest-xhalf", type=float, default=0.22)
    p.add_argument("--front-sign", type=float, default=-1.0,
                   help="front = sign*Y; flip if logo lands on back")
    p.add_argument("--cloth", action="store_true", help="cloth sim for wrinkles")
    p.add_argument("--sim-frames", type=int, default=20)
    # P1.5 domain randomization
    p.add_argument("--hdri", default="",
                   help="path to .hdr/.exr file OR directory of HDRIs; "
                        "omit for procedural sky fallback")
    p.add_argument("--body-tilt", type=float, default=15.0,
                   help="max body lean/twist in degrees")
    p.add_argument("--jpeg-min", type=int, default=70,
                   help="min JPEG quality for beauty pass (broadcast compression)")
    p.add_argument("--jpeg-max", type=int, default=92,
                   help="max JPEG quality for beauty pass")
    p.add_argument("--motion-blur", action="store_true",
                   help="enable motion blur via camera keyframe shake")
    p.add_argument("--shutter", type=float, default=0.5,
                   help="motion blur shutter angle (0-1)")
    return p.parse_args(argv)


# -------------------------------------------------------------------------- assets
def load_logos(logo_dir):
    paths = [str(f) for f in sorted(Path(logo_dir).iterdir())
             if f.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp")
             and f.stat().st_size > 0]
    if not paths:
        raise SystemExit(f"No logos in {logo_dir}")
    print(f"[logos] {len(paths)} assets")
    return paths


def _pick_hdri(hdri_arg, rng):
    """Return a single HDRI path or None (fallback to procedural sky)."""
    if not hdri_arg:
        return None
    p = Path(hdri_arg)
    if p.is_file():
        return str(p)
    if p.is_dir():
        candidates = [f for f in p.iterdir()
                      if f.suffix.lower() in (".hdr", ".exr")]
        if candidates:
            return str(rng.choice(candidates))
    print(f"[hdri] not found: {hdri_arg} — using procedural sky")
    return None


# -------------------------------------------------------------------------- world / lighting
def setup_world_dr(rng, hdri_path=None):
    """Domain-randomized world: HDRI if available, else procedural sky."""
    world = bpy.data.worlds.new("W")
    bpy.context.scene.world = world
    world.use_nodes = True
    nt = world.node_tree
    nt.nodes.clear()

    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])

    if hdri_path:
        env = nt.nodes.new("ShaderNodeTexEnvironment")
        try:
            env.image = bpy.data.images.load(hdri_path, check_existing=False)
        except Exception as e:
            print(f"[hdri] load failed ({e}) — falling back to procedural sky")
            hdri_path = None

    if hdri_path:
        # rotate HDRI randomly so lighting direction changes each sample
        coord = nt.nodes.new("ShaderNodeTexCoord")
        mapping = nt.nodes.new("ShaderNodeMapping")
        mapping.inputs["Rotation"].default_value = (
            0, 0, rng.uniform(0, 2 * math.pi))
        nt.links.new(coord.outputs["Generated"], mapping.inputs["Vector"])
        nt.links.new(mapping.outputs["Vector"], env.inputs["Vector"])
        nt.links.new(env.outputs["Color"], bg.inputs["Color"])
        bg.inputs["Strength"].default_value = rng.uniform(0.6, 1.8)
        print(f"[hdri] {Path(hdri_path).name}  strength={bg.inputs['Strength'].default_value:.2f}")
    else:
        # procedural gradient sky (no HDRI needed)
        sky = nt.nodes.new("ShaderNodeTexSky")
        # Blender 5.x: NISHITA removed; use HOSEK_WILKIE
        sky.sky_type = "HOSEK_WILKIE"
        el = math.radians(rng.uniform(15, 75))
        az = rng.uniform(0, 2 * math.pi)
        sky.sun_direction = (math.cos(el) * math.sin(az),
                             math.cos(el) * math.cos(az),
                             math.sin(el))
        sky.turbidity = rng.uniform(1.5, 6.0)
        sky.ground_albedo = rng.uniform(0.1, 0.4)
        coord = nt.nodes.new("ShaderNodeTexCoord")
        nt.links.new(coord.outputs["Generated"], sky.inputs["Vector"])
        nt.links.new(sky.outputs["Color"], bg.inputs["Color"])
        bg.inputs["Strength"].default_value = rng.uniform(0.5, 1.5)

    return world


# -------------------------------------------------------------------------- body
def import_body(path, rng):
    bpy.ops.wm.obj_import(filepath=path)
    body = bpy.context.selected_objects[0]
    bpy.context.view_layer.objects.active = body
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    co = [v.co for v in body.data.vertices]
    zmin = min(c.z for c in co); zmax = max(c.z for c in co)
    xspan = max(abs(c.x) for c in co)
    body["_zmin"] = zmin; body["_zmax"] = zmax; body["_xspan"] = xspan

    # skin-tone domain randomization
    body.data.materials.clear()
    skin = bpy.data.materials.new("skin")
    skin.use_nodes = True
    r = rng.uniform(0.25, 0.55)
    g = rng.uniform(0.18, 0.40)
    b_ = rng.uniform(0.12, 0.30)
    skin.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (r, g, b_, 1)
    body.data.materials.append(skin)
    return body


def apply_body_tilt(body, jersey, rng, max_deg):
    """Lean/twist body + jersey together to simulate player pose variation."""
    if max_deg <= 0:
        return
    rx = math.radians(rng.uniform(-max_deg * 0.4, max_deg * 0.4))   # forward lean
    rz = math.radians(rng.uniform(-max_deg, max_deg))                 # twist
    for obj in (body, jersey):
        obj.rotation_euler.x += rx
        obj.rotation_euler.z += rz


# -------------------------------------------------------------------------- jersey
def make_jersey(body, args, rng):
    zmin, zmax, xspan = body["_zmin"], body["_zmax"], body["_xspan"]
    h = zmax - zmin
    zlo = zmin + args.chest_zlo * h
    zhi = zmin + args.chest_zhi * h
    xhalf = args.chest_xhalf * xspan * 2
    fs = args.front_sign

    bpy.ops.object.select_all(action="DESELECT")
    body.select_set(True)
    bpy.context.view_layer.objects.active = body
    bpy.ops.object.duplicate()
    jersey = bpy.context.active_object
    jersey.name = "jersey"

    bm = bmesh.new()
    bm.from_mesh(jersey.data)
    bm.faces.ensure_lookup_table()
    kill = []
    for f in bm.faces:
        c = f.calc_center_median()
        n = f.normal
        # require clearly front-facing (> 0.30) to exclude side/interior faces
        front = (n.y * fs) > 0.30
        # also require face center to be on the front half of the body
        in_band = (zlo <= c.z <= zhi
                   and abs(c.x) <= xhalf
                   and (c.y * fs) >= 0)
        if not (in_band and front):
            kill.append(f)
    bmesh.ops.delete(bm, geom=kill, context="FACES")
    bm.to_mesh(jersey.data)
    bm.free()
    jersey.data.update()

    if len(jersey.data.polygons) < 10:
        raise RuntimeError(f"chest panel too small ({len(jersey.data.polygons)} faces) "
                           "- adjust --chest-* / --front-sign")

    sol = jersey.modifiers.new("Solidify", "SOLIDIFY")
    sol.thickness = 0.12 * (h / 17.0)
    sol.offset = 1.0
    bpy.ops.object.shade_smooth()

    if args.cloth:
        bpy.context.view_layer.objects.active = jersey
        bpy.ops.object.modifier_apply(modifier="Solidify")
        body.modifiers.new("Collision", "COLLISION")
        m = jersey.modifiers.new("Cloth", "CLOTH")
        m.settings.bending_stiffness = 0.5
        m.collision_settings.distance_min = 0.005
        scene = bpy.context.scene
        scene.frame_start = 1; scene.frame_end = args.sim_frames
        for fr in range(1, args.sim_frames + 1):
            scene.frame_set(fr)
    return jersey, (zlo, zhi)


# -------------------------------------------------------------------------- materials
def logo_placement(rng):
    # Rugby jersey: sponsor logo = ~30-45% of chest width, centered, upright
    s = rng.uniform(2.2, 3.5)
    return dict(scale=s,
                jx=rng.uniform(-0.02, 0.02),   # nearly centered horizontally
                jy=rng.uniform(-0.04, 0.04),   # small vertical variation
                rot=rng.uniform(-0.04, 0.04))  # nearly upright


def _front_proj_logo(nt, logo_path, place, chest_ar=1.0):
    """Project logo onto chest using Generated X/Z coords.

    chest_ar = chest_width / chest_height in world units.
    We correct scale so logo appears at its true pixel aspect ratio.
    """
    # Load image to get pixel AR
    img = bpy.data.images.load(logo_path, check_existing=True)
    logo_ar = img.size[0] / max(img.size[1], 1)  # logo_w / logo_h

    s = place["scale"]
    sx = s
    # sz corrected so logo world-space width/height = logo_ar
    # derivation: (W/sx) / (H/sz) = logo_ar  where chest_ar = W/H
    #   → sz = sx * logo_ar / chest_ar
    sz = s * logo_ar / max(chest_ar, 0.1)

    gen = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(gen.outputs["Generated"], sep.inputs["Vector"])
    comb = nt.nodes.new("ShaderNodeCombineXYZ")
    nt.links.new(sep.outputs["X"], comb.inputs["X"])
    nt.links.new(sep.outputs["Z"], comb.inputs["Y"])
    mapping = nt.nodes.new("ShaderNodeMapping")
    mapping.inputs["Scale"].default_value = (sx, sz, 1)
    # X: center at gen_X=0.5 (horizontal center of chest)
    # Y: center at gen_Z=0.68 (upper chest, where sponsors sit on real kits)
    #    formula: loc_y = 0.5 - center_z * sz
    mapping.inputs["Location"].default_value = (0.5 * (1 - sx) + place["jx"],
                                                0.5 - 0.68 * sz + place["jy"], 0)
    mapping.inputs["Rotation"].default_value = (0, 0, place["rot"])
    nt.links.new(comb.outputs["Vector"], mapping.inputs["Vector"])
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = img
    tex.extension = "CLIP"
    nt.links.new(mapping.outputs["Vector"], tex.inputs["Vector"])
    return tex.outputs["Color"], tex.outputs["Alpha"]


def jersey_beauty(logo_path, place, rng, chest_ar=1.0):
    mat = bpy.data.materials.new("jersey_beauty")
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Roughness"].default_value = rng.uniform(0.55, 0.90)
    import colorsys
    r_, g_, b__ = colorsys.hsv_to_rgb(rng.random(), rng.uniform(0.4, 1.0), rng.uniform(0.25, 0.85))
    color, alpha = _front_proj_logo(nt, logo_path, place, chest_ar)
    mix = nt.nodes.new("ShaderNodeMixRGB")
    mix.inputs["Color1"].default_value = (r_, g_, b__, 1)
    nt.links.new(alpha, mix.inputs["Fac"])
    nt.links.new(color, mix.inputs["Color2"])
    nt.links.new(mix.outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat


def jersey_mask(logo_path, place, chest_ar=1.0):
    mat = bpy.data.materials.new("jersey_mask")
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    emit = nt.nodes.new("ShaderNodeEmission")
    _, alpha = _front_proj_logo(nt, logo_path, place, chest_ar)
    nt.links.new(alpha, emit.inputs["Strength"])
    nt.links.new(emit.outputs["Emission"], out.inputs["Surface"])
    return mat


# -------------------------------------------------------------------------- camera
def add_camera(rng, target, front_sign, body_h, motion_blur=False, shutter=0.5):
    cam_data = bpy.data.cameras.new("C")
    cam_data.lens = rng.uniform(50, 85)
    cam_obj = bpy.data.objects.new("C", cam_data)
    bpy.context.collection.objects.link(cam_obj)
    bpy.context.scene.camera = cam_obj

    # frontal bias: ±25° so logo stays visible and centered in frame
    az = math.radians(rng.uniform(-25, 25))
    el = rng.uniform(-0.10, 0.30)       # slight up-look typical of pitch-side camera
    r = rng.uniform(0.55, 0.85) * body_h
    cam_obj.location = (
        target.x + r * math.sin(az) * math.cos(el),
        target.y + front_sign * r * math.cos(az) * math.cos(el),
        target.z + r * math.sin(el))

    empty = bpy.data.objects.new("aim", None)
    empty.location = target
    bpy.context.collection.objects.link(empty)
    c = cam_obj.constraints.new("TRACK_TO")
    c.target = empty
    c.track_axis = "TRACK_NEGATIVE_Z"
    c.up_axis = "UP_Y"

    # subtle camera roll → handheld feel
    roll_deg = rng.uniform(-6, 6)
    cam_obj.rotation_euler.z += math.radians(roll_deg)

    if motion_blur:
        scene = bpy.context.scene
        scene.render.use_motion_blur = True
        scene.render.motion_blur_shutter = shutter
        # micro-shake between frame 1 and 2 creates camera-motion blur
        scene.frame_set(1)
        cam_obj.keyframe_insert(data_path="location", frame=1)
        shake = body_h * 0.003
        cam_obj.location.x += shake * rng.gauss(0, 1)
        cam_obj.location.z += shake * rng.gauss(0, 1)
        cam_obj.keyframe_insert(data_path="location", frame=2)
        scene.frame_set(1)

    return cam_obj


# -------------------------------------------------------------------------- film grain
def add_film_grain(rng):
    scene = bpy.context.scene
    # Cycles film transparency + slight exposure variation
    scene.cycles.film_exposure = rng.uniform(0.85, 1.25)
    scene.render.film_transparent = False


# -------------------------------------------------------------------------- one sample
def render_sample(args, body_path, logo_path, rng, hdri_path, dst_noext, mask_noext):
    clear_scene()
    setup_cycles(args)
    world = setup_world_dr(rng, hdri_path)
    add_lights(rng)
    body = import_body(body_path, rng)
    jersey, (zlo, zhi) = make_jersey(body, args, rng)
    h = body["_zmax"] - body["_zmin"]

    apply_body_tilt(body, jersey, rng, args.body_tilt)

    # compute chest aspect ratio (world width / world height) for logo AR correction
    verts = [jersey.matrix_world @ v.co for v in jersey.data.vertices]
    xs = [v.x for v in verts]; zs = [v.z for v in verts]
    chest_ar = (max(xs) - min(xs)) / max(max(zs) - min(zs), 1e-4)

    place = logo_placement(rng)
    beauty = jersey_beauty(logo_path, place, rng, chest_ar)
    mask = jersey_mask(logo_path, place, chest_ar)

    target = Vector((0, 0, (zlo + zhi) / 2))
    add_camera(rng, target, args.front_sign, h,
               motion_blur=args.motion_blur, shutter=args.shutter)
    add_film_grain(rng)

    scene = bpy.context.scene
    bg_strength_node = world.node_tree.nodes["Background"].inputs["Strength"]
    world_strength = bg_strength_node.default_value

    # --- pass 1: MASK (motion blur OFF to keep clean edges) ---
    jersey.data.materials.clear()
    jersey.data.materials.append(mask)
    bg_strength_node.default_value = 0.0
    lights = [o for o in scene.objects if o.type == "LIGHT"]
    for L in lights:
        L.hide_render = True
    was_mb = scene.render.use_motion_blur
    scene.render.use_motion_blur = False
    scene.view_settings.view_transform = "Raw"
    scene.cycles.samples = 16
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = mask_noext
    bpy.ops.render.render(write_still=True)
    # restore
    for L in lights:
        L.hide_render = False
    scene.render.use_motion_blur = was_mb

    box = bbox_from_mask(mask_noext + ".png")
    if box is None:
        return None

    # --- pass 2: BEAUTY ---
    jersey.data.materials[0] = beauty
    bg_strength_node.default_value = world_strength
    scene.view_settings.view_transform = "AgX"
    scene.cycles.samples = args.samples
    scene.render.image_settings.file_format = "JPEG"
    # JPEG quality DR: simulate broadcast compression artifacts
    scene.render.image_settings.quality = rng.randint(args.jpeg_min, args.jpeg_max)
    scene.render.filepath = dst_noext
    bpy.ops.render.render(write_still=True)
    return box


def main():
    args = parse_args()
    rng = random.Random(args.seed)
    logos = load_logos(args.logos)
    if not Path(args.body).exists():
        raise SystemExit(f"Body mesh not found: {args.body}\n"
                         "Download from https://raw.githubusercontent.com/makehumancommunity/"
                         "makehuman/master/makehuman/data/3dobjs/base.obj")

    out = Path(args.out)
    if not out.is_absolute():
        out = HERE / out
    for s in ("images/train", "images/val", "labels/train", "labels/val"):
        (out / s).mkdir(parents=True, exist_ok=True)
    tmp = out / "_tmp"
    tmp.mkdir(exist_ok=True)
    print(f"[out] {out}")
    print(f"[DR]  hdri={'yes' if args.hdri else 'procedural sky'}  "
          f"body-tilt={args.body_tilt}°  "
          f"jpeg={args.jpeg_min}–{args.jpeg_max}  "
          f"motion-blur={args.motion_blur}")

    hdri_path = _pick_hdri(args.hdri, rng)

    n_val = int(args.n * args.val_frac)
    made = 0
    for i in range(args.n):
        split = "val" if i < n_val else "train"
        logo = logos[rng.randrange(len(logos))]
        stem = f"jrs_{i:06d}"
        dst = str(out / "images" / split / stem)
        msk = str(tmp / f"{stem}_m")
        # pick a new HDRI each sample if a directory was given
        hdri_path = _pick_hdri(args.hdri, rng)
        try:
            b = render_sample(args, args.body, logo, rng, hdri_path, dst, msk)
        except Exception as e:
            print(f"[skip] {stem}: {e}")
            continue
        if b is None:
            print(f"[skip] {stem}: logo not visible")
            continue
        (out / "labels" / split / f"{stem}.txt").write_text(to_yolo(b))
        made += 1
        print(f"  [{made}/{args.n}] {stem}  bbox={b[:4]}")

    (out / "data.yaml").write_text(
        f"path: {out.resolve().as_posix()}\n"
        "train: images/train\nval: images/val\nnc: 1\nnames: ['logo']\n")
    print(f"\n[done] {made}/{args.n} -> {out.resolve()}")


if __name__ == "__main__":
    main()
