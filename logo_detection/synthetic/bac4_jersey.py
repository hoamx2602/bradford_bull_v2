#!/usr/bin/env python3
"""
Bac 4 (P1) — logo on a JERSEY worn by a real human body.  RUNS INSIDE BLENDER:

    blender --background --python bac4_jersey.py -- --n 8 --out data_bac4_jersey

Upgrade over P0 (cloth-drape): the cloth is now a chest panel derived from a real
CC0 human mesh (MakeHuman base, CC0), solidified into a body-fitting jersey, so the
logo sits on a chest that has true human shoulder/chest curvature. The logo is
projected onto the chest from the front (generated X/Z coords) so it conforms to the
surface, and the auto bbox comes from the same emission-mask trick as P0.

Body asset (CC0, downloaded once to assets/makehuman_base.obj):
    https://raw.githubusercontent.com/makehumancommunity/makehuman/master/makehuman/data/3dobjs/base.obj

Still studio-lit / no stadium scene — that is P1.5 (HDRI + DR + real-in-the-loop).
This step proves "logo on a worn jersey + pixel-perfect auto-label".
"""
import sys
import math
import random
import argparse
from pathlib import Path

import bpy
import bmesh
import numpy as np
from mathutils import Vector

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))   # so Blender's python can import sibling modules

from bac4_cloth import (clear_scene, setup_cycles, setup_world, add_lights,
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
    # chest panel region as fractions of body height (z) and half-width fraction of body
    p.add_argument("--chest-zlo", type=float, default=0.60)
    p.add_argument("--chest-zhi", type=float, default=0.82)
    p.add_argument("--chest-xhalf", type=float, default=0.28, help="half torso width frac")
    p.add_argument("--front-sign", type=float, default=-1.0, help="front = sign*Y; flip if logo lands on the back")
    p.add_argument("--cloth", action="store_true", help="add light cloth sim for wrinkles")
    p.add_argument("--sim-frames", type=int, default=20)
    return p.parse_args(argv)


# ------------------------------------------------------------------------- assets
def load_logos(logo_dir):
    paths = [str(f) for f in sorted(Path(logo_dir).iterdir())
             if f.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp") and f.stat().st_size > 0]
    if not paths:
        raise SystemExit(f"No logos in {logo_dir}")
    print(f"[logos] {len(paths)} assets")
    return paths


def import_body(path):
    bpy.ops.wm.obj_import(filepath=path)
    body = bpy.context.selected_objects[0]
    # apply transforms so local == world
    bpy.context.view_layer.objects.active = body
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    co = [v.co for v in body.data.vertices]
    zmin = min(c.z for c in co); zmax = max(c.z for c in co)
    xspan = max(abs(c.x) for c in co)
    body["_zmin"] = zmin
    body["_zmax"] = zmax
    body["_xspan"] = xspan
    body.data.materials.clear()
    skin = bpy.data.materials.new("skin")
    skin.use_nodes = True
    skin.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.35, 0.25, 0.2, 1)
    body.data.materials.append(skin)
    return body


def make_jersey(body, args, rng):
    """Duplicate the body, keep only the front chest band, solidify -> a worn jersey."""
    zmin, zmax, xspan = body["_zmin"], body["_zmax"], body["_xspan"]
    h = zmax - zmin
    zlo = zmin + args.chest_zlo * h
    zhi = zmin + args.chest_zhi * h
    xhalf = args.chest_xhalf * xspan * 2  # xspan is half-ish (max|x|); widen a touch
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
        front = (n.y * fs) > 0.15          # face points toward the front
        in_band = zlo <= c.z <= zhi and abs(c.x) <= xhalf and (c.y * fs) >= 0
        if not (in_band and front):
            kill.append(f)
    bmesh.ops.delete(bm, geom=kill, context="FACES")
    bm.to_mesh(jersey.data)
    bm.free()
    jersey.data.update()

    if len(jersey.data.polygons) < 10:
        raise RuntimeError(f"chest panel too small ({len(jersey.data.polygons)} faces) "
                           "- adjust --chest-* / --front-sign")

    # offset outward into a fabric shell
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
        scene.frame_start = 1
        scene.frame_end = args.sim_frames
        for fr in range(1, args.sim_frames + 1):
            scene.frame_set(fr)
    return jersey, (zlo, zhi)


# ----------------------------------------------------------------------- material
def logo_placement(rng):
    s = rng.uniform(1.4, 2.4)                       # logo occupies 1/s of chest width
    return dict(scale=s, jx=rng.uniform(-0.06, 0.06), jy=rng.uniform(-0.04, 0.10),
                rot=rng.uniform(-0.12, 0.12))


def _front_proj_logo(nt, logo_path, place):
    """Project the logo onto the chest from the front using Generated X/Z coords, so
    it conforms to the surface. Returns (color_out, alpha_out)."""
    s = place["scale"]
    gen = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(gen.outputs["Generated"], sep.inputs["Vector"])
    comb = nt.nodes.new("ShaderNodeCombineXYZ")
    nt.links.new(sep.outputs["X"], comb.inputs["X"])
    nt.links.new(sep.outputs["Z"], comb.inputs["Y"])
    mapping = nt.nodes.new("ShaderNodeMapping")
    mapping.inputs["Scale"].default_value = (s, s, 1)
    mapping.inputs["Location"].default_value = (0.5 * (1 - s) + place["jx"],
                                                0.5 * (1 - s) + place["jy"], 0)
    mapping.inputs["Rotation"].default_value = (0, 0, place["rot"])
    nt.links.new(comb.outputs["Vector"], mapping.inputs["Vector"])
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(logo_path, check_existing=False)
    tex.extension = "CLIP"
    nt.links.new(mapping.outputs["Vector"], tex.inputs["Vector"])
    return tex.outputs["Color"], tex.outputs["Alpha"]


def jersey_beauty(logo_path, place, rng):
    mat = bpy.data.materials.new("jersey_beauty")
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Roughness"].default_value = rng.uniform(0.6, 0.9)
    color, alpha = _front_proj_logo(nt, logo_path, place)
    mix = nt.nodes.new("ShaderNodeMixRGB")
    mix.inputs["Color1"].default_value = (rng.random(), rng.random(), rng.random(), 1)
    nt.links.new(alpha, mix.inputs["Fac"])
    nt.links.new(color, mix.inputs["Color2"])
    nt.links.new(mix.outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat


def jersey_mask(logo_path, place):
    mat = bpy.data.materials.new("jersey_mask")
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    emit = nt.nodes.new("ShaderNodeEmission")
    _, alpha = _front_proj_logo(nt, logo_path, place)
    nt.links.new(alpha, emit.inputs["Strength"])
    nt.links.new(emit.outputs["Emission"], out.inputs["Surface"])
    return mat


# ----------------------------------------------------------------------- camera
def add_camera(rng, target, front_sign, body_h):
    cam = bpy.data.cameras.new("C")
    cam.lens = rng.uniform(50, 85)
    o = bpy.data.objects.new("C", cam)
    bpy.context.collection.objects.link(o)
    bpy.context.scene.camera = o
    az = math.radians(rng.uniform(-38, 38))            # front-ish only
    el = rng.uniform(-0.12, 0.28)
    r = rng.uniform(0.55, 0.8) * body_h
    o.location = (target.x + r * math.sin(az) * math.cos(el),
                  target.y + front_sign * r * math.cos(az) * math.cos(el),
                  target.z + r * math.sin(el))
    empty = bpy.data.objects.new("aim", None)
    empty.location = target
    bpy.context.collection.objects.link(empty)
    c = o.constraints.new("TRACK_TO")
    c.target = empty
    c.track_axis = "TRACK_NEGATIVE_Z"
    c.up_axis = "UP_Y"


# ----------------------------------------------------------------------- one sample
def render_sample(args, body_path, logo_path, rng, dst_noext, mask_noext):
    clear_scene()
    setup_cycles(args)
    setup_world(rng)
    add_lights(rng)
    body = import_body(body_path)
    jersey, (zlo, zhi) = make_jersey(body, args, rng)
    h = body["_zmax"] - body["_zmin"]

    place = logo_placement(rng)
    beauty = jersey_beauty(logo_path, place, rng)
    mask = jersey_mask(logo_path, place)

    target = Vector((0, 0, (zlo + zhi) / 2))
    add_camera(rng, target, args.front_sign, h)

    scene = bpy.context.scene
    bg = scene.world.node_tree.nodes["Background"].inputs["Strength"]
    world_strength = bg.default_value

    # pass 1 — MASK. Disable all lights so the (non-emissive) body renders BLACK;
    # the logo's Emission shader is self-lit and stays visible -> clean logo mask.
    jersey.data.materials.clear()
    jersey.data.materials.append(mask)
    bg.default_value = 0.0
    lights = [o for o in scene.objects if o.type == "LIGHT"]
    for L in lights:
        L.hide_render = True
    scene.view_settings.view_transform = "Raw"
    scene.cycles.samples = 16
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = mask_noext
    bpy.ops.render.render(write_still=True)
    for L in lights:
        L.hide_render = False

    box = bbox_from_mask(mask_noext + ".png")
    if box is None:
        return None

    # pass 2 — BEAUTY
    jersey.data.materials[0] = beauty
    bg.default_value = world_strength
    scene.view_settings.view_transform = "AgX"
    scene.cycles.samples = args.samples
    scene.render.image_settings.file_format = "JPEG"
    scene.render.image_settings.quality = 92
    scene.render.filepath = dst_noext
    bpy.ops.render.render(write_still=True)
    return box


def main():
    args = parse_args()
    rng = random.Random(args.seed)
    logos = load_logos(args.logos)
    if not Path(args.body).exists():
        raise SystemExit(f"Body mesh not found: {args.body}")

    out = Path(args.out)
    if not out.is_absolute():
        out = HERE / out
    for s in ("images/train", "images/val", "labels/train", "labels/val"):
        (out / s).mkdir(parents=True, exist_ok=True)
    tmp = out / "_tmp"
    tmp.mkdir(exist_ok=True)
    print(f"[out] {out}")

    n_val = int(args.n * args.val_frac)
    made = 0
    for i in range(args.n):
        split = "val" if i < n_val else "train"
        logo = logos[rng.randrange(len(logos))]
        stem = f"jrs_{i:06d}"
        dst = str(out / "images" / split / stem)
        msk = str(tmp / f"{stem}_m")
        try:
            b = render_sample(args, args.body, logo, rng, dst, msk)
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
