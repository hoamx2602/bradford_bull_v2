#!/usr/bin/env python3
"""
Bac 4 (P0) — 3D cloth-drape logo factory.  RUNS INSIDE BLENDER:

    blender --background --python bac4_cloth.py -- --n 8 --out data_bac4

What it does (see bac4_3d_simulation.md)
----------------------------------------
Drape a high-res cloth plane over a random collider so it forms physical folds,
UV-map a REAL logo onto the cloth, render photoreal with Cycles, and auto-export a
pixel-perfect YOLO box for the logo. Because the logo lives in the cloth's UV, it
wrinkles/curves WITH the fabric — the thing diffusion (Bac 3) could not do — yet it
is still the real asset (label fidelity, golden rule 8.1).

Two render passes share the exact same deformed geometry/camera:
  1. beauty : fabric + logo, lit (the training image)
  2. mask   : emission = logo alpha, world black  -> threshold -> bbox/mask

This P0 has NO body/jersey (those need licensed SMPL/AMASS + a rugby mesh). It
proves the cloth->logo deformation + perfect auto-label loop. Body+jersey is P1.

Output: images/{train,val}/*.jpg  labels/{train,val}/*.txt  data.yaml (nc:1).
"""
import os
import sys
import math
import random
import argparse
from pathlib import Path

import bpy
import numpy as np
from mathutils import Vector


# ---------------------------------------------------------------------- arg parse
def parse_args():
    argv = sys.argv
    argv = argv[argv.index("--") + 1:] if "--" in argv else []
    p = argparse.ArgumentParser()
    p.add_argument("--logos", default=str(Path(__file__).resolve().parents[2] / "Sponsor Logo"))
    p.add_argument("--out", default=str(Path(__file__).resolve().parent / "data_bac4"))
    p.add_argument("--n", type=int, default=8)
    p.add_argument("--val-frac", type=float, default=0.10)
    p.add_argument("--res", type=int, default=1024)
    p.add_argument("--samples", type=int, default=96)
    p.add_argument("--sim-frames", type=int, default=40, help="cloth settle frames")
    p.add_argument("--cloth-sub", type=int, default=80, help="cloth grid subdivisions")
    p.add_argument("--device", default="OPTIX", choices=["OPTIX", "CUDA", "CPU"])
    p.add_argument("--seed", type=int, default=0)
    return p.parse_args(argv)


# ------------------------------------------------------------------- gpu / engine
def setup_cycles(args):
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.samples = args.samples
    scene.cycles.use_denoising = True
    scene.render.resolution_x = args.res
    scene.render.resolution_y = args.res
    scene.render.image_settings.file_format = "PNG"
    if args.device == "CPU":
        scene.cycles.device = "CPU"
        return
    prefs = bpy.context.preferences.addons["cycles"].preferences
    try:
        prefs.compute_device_type = args.device
    except TypeError:
        prefs.compute_device_type = "CUDA"
    prefs.get_devices()
    n_gpu = 0
    for d in prefs.devices:
        d.use = d.type in (args.device, "CUDA", "OPTIX")
        if d.use and d.type != "CPU":
            n_gpu += 1
    scene.cycles.device = "GPU" if n_gpu else "CPU"
    print(f"[cycles] device={scene.cycles.device} ({n_gpu} accel devices)")


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()
    for block in (bpy.data.meshes, bpy.data.materials, bpy.data.images,
                  bpy.data.lights, bpy.data.cameras):
        for b in list(block):
            try:
                block.remove(b)
            except Exception:
                pass


# ----------------------------------------------------------------------- assets
def load_logos(logo_dir):
    paths = []
    for f in sorted(Path(logo_dir).iterdir()):
        if f.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp") and f.stat().st_size > 0:
            paths.append(str(f))
    if not paths:
        raise SystemExit(f"No logos in {logo_dir}")
    print(f"[logos] {len(paths)} assets")
    return paths


def make_collider(rng):
    """A random primitive the cloth drapes over -> varied folds."""
    kind = rng.choice(["sphere", "cube", "two_cubes", "cylinder"])
    if kind == "sphere":
        bpy.ops.mesh.primitive_uv_sphere_add(radius=rng.uniform(0.5, 0.9),
                                             location=(0, 0, 0))
    elif kind == "cube":
        bpy.ops.mesh.primitive_cube_add(size=rng.uniform(0.8, 1.3), location=(0, 0, 0))
    elif kind == "cylinder":
        bpy.ops.mesh.primitive_cylinder_add(radius=rng.uniform(0.4, 0.7),
                                            depth=rng.uniform(0.8, 1.4),
                                            rotation=(math.radians(90), 0, 0))
    else:  # two cubes -> a saddle/valley
        bpy.ops.mesh.primitive_cube_add(size=0.7, location=(-0.6, 0, 0))
        a = bpy.context.active_object
        bpy.ops.mesh.primitive_cube_add(size=0.7, location=(0.6, 0, 0))
        b = bpy.context.active_object
        a.select_set(True); b.select_set(True)
        bpy.context.view_layer.objects.active = b
        bpy.ops.object.join()
    col = bpy.context.active_object
    col.modifiers.new("Collision", "COLLISION")
    col.collision.thickness_outer = 0.02
    return col


def make_cloth(args, rng):
    bpy.ops.mesh.primitive_grid_add(x_subdivisions=args.cloth_sub,
                                    y_subdivisions=args.cloth_sub,
                                    size=rng.uniform(2.6, 3.4),
                                    location=(0, 0, 1.4))
    cloth = bpy.context.active_object
    cloth.rotation_euler = (0, 0, rng.uniform(0, math.pi))
    m = cloth.modifiers.new("Cloth", "CLOTH")
    cs = m.settings
    cs.quality = 8
    cs.mass = rng.uniform(0.2, 0.5)
    cs.tension_stiffness = rng.uniform(10, 25)
    cs.compression_stiffness = rng.uniform(10, 25)
    cs.bending_stiffness = rng.uniform(0.2, 1.5)   # low -> more wrinkles
    m.collision_settings.use_self_collision = True
    # smooth shading
    bpy.ops.object.shade_smooth()
    return cloth


# ----------------------------------------------------------------------- material
def logo_placement(rng):
    """Pick the logo's UV scale/offset/rotation ONCE so the beauty and mask passes
    paint the logo at the IDENTICAL spot (otherwise the bbox won't match)."""
    s = rng.uniform(1.3, 2.2)                       # >1 -> logo occupies 1/s of cloth
    return dict(scale=s,
                jx=rng.uniform(-0.12, 0.12),
                jy=rng.uniform(-0.12, 0.12),
                rot=rng.uniform(-0.3, 0.3))


def _logo_tex_nodes(nt, logo_path, place):
    """Shared UV->Mapping->ImageTexture(logo) chain. Returns (color_out, alpha_out)."""
    s = place["scale"]
    uv = nt.nodes.new("ShaderNodeTexCoord")
    mapping = nt.nodes.new("ShaderNodeMapping")
    mapping.inputs["Scale"].default_value = (s, s, 1)
    # out = s*in + loc ; centring the 1/s window on UV 0.5 needs loc = 0.5*(1-s)
    mapping.inputs["Location"].default_value = (0.5 * (1 - s) + place["jx"],
                                                0.5 * (1 - s) + place["jy"], 0)
    mapping.inputs["Rotation"].default_value = (0, 0, place["rot"])
    tex = nt.nodes.new("ShaderNodeTexImage")
    tex.image = bpy.data.images.load(logo_path, check_existing=False)
    tex.extension = "CLIP"                          # no tiling -> alpha 0 outside logo
    nt.links.new(uv.outputs["UV"], mapping.inputs["Vector"])
    nt.links.new(mapping.outputs["Vector"], tex.inputs["Vector"])
    return tex.outputs["Color"], tex.outputs["Alpha"]


def beauty_material(logo_path, place, rng):
    mat = bpy.data.materials.new("cloth_beauty")
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Roughness"].default_value = rng.uniform(0.6, 0.95)
    color, alpha = _logo_tex_nodes(nt, logo_path, place)
    mix = nt.nodes.new("ShaderNodeMixRGB")
    fabric = (rng.random(), rng.random(), rng.random())
    mix.inputs["Color1"].default_value = (*fabric, 1)   # fabric base
    nt.links.new(alpha, mix.inputs["Fac"])
    nt.links.new(color, mix.inputs["Color2"])           # logo over fabric
    nt.links.new(mix.outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return mat


def mask_material(logo_path, place):
    mat = bpy.data.materials.new("cloth_mask")
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    emit = nt.nodes.new("ShaderNodeEmission")
    emit.inputs["Color"].default_value = (1, 1, 1, 1)
    _, alpha = _logo_tex_nodes(nt, logo_path, place)
    nt.links.new(alpha, emit.inputs["Strength"])        # white only where logo
    nt.links.new(emit.outputs["Emission"], out.inputs["Surface"])
    return mat


# ----------------------------------------------------------------------- lighting/cam
def setup_world(rng):
    world = bpy.data.worlds.new("W")
    bpy.context.scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    g = rng.uniform(0.2, 0.7)
    bg.inputs["Color"].default_value = (g * rng.uniform(0.8, 1.0),
                                        g * rng.uniform(0.8, 1.0),
                                        g * rng.uniform(0.9, 1.1), 1)
    bg.inputs["Strength"].default_value = rng.uniform(0.3, 1.2)
    return world


def add_lights(rng):
    for _ in range(rng.randint(1, 3)):
        d = bpy.data.lights.new("L", "AREA")
        d.energy = rng.uniform(300, 1500)
        d.size = rng.uniform(1, 4)
        d.color = (rng.uniform(0.8, 1), rng.uniform(0.8, 1), rng.uniform(0.85, 1))
        o = bpy.data.objects.new("L", d)
        bpy.context.collection.objects.link(o)
        az, el, r = rng.uniform(0, 2 * math.pi), rng.uniform(0.5, 1.3), rng.uniform(3, 6)
        o.location = (r * math.cos(az) * math.cos(el),
                      r * math.sin(az) * math.cos(el), 1.4 + r * math.sin(el))
        c = o.constraints.new("TRACK_TO")
        c.track_axis = "TRACK_NEGATIVE_Z"
        c.up_axis = "UP_Y"


def add_camera(rng, target):
    cam = bpy.data.cameras.new("C")
    cam.lens = rng.uniform(35, 70)
    o = bpy.data.objects.new("C", cam)
    bpy.context.collection.objects.link(o)
    bpy.context.scene.camera = o
    az = rng.uniform(0, 2 * math.pi)
    el = rng.uniform(0.25, 0.95)                 # above horizon, some oblique angles
    r = rng.uniform(3.0, 4.5)
    o.location = (target.x + r * math.cos(az) * math.cos(el),
                  target.y + r * math.sin(az) * math.cos(el),
                  target.z + r * math.sin(el))
    empty = bpy.data.objects.new("aim", None)
    empty.location = target
    bpy.context.collection.objects.link(empty)
    c = o.constraints.new("TRACK_TO")
    c.target = empty
    c.track_axis = "TRACK_NEGATIVE_Z"
    c.up_axis = "UP_Y"
    return o


# ----------------------------------------------------------------------- bbox
def bbox_from_mask(path, thresh=0.15):
    img = bpy.data.images.load(path, check_existing=False)
    w, h = img.size
    px = np.array(img.pixels[:], dtype=np.float32).reshape(h, w, 4)
    px = px[::-1]                                 # Blender stores bottom-up
    bpy.data.images.remove(img)
    m = px[:, :, 0] > thresh
    ys, xs = np.where(m)
    if len(xs) < 8:                              # logo not visible enough
        return None
    return xs.min(), ys.min(), xs.max(), ys.max(), w, h


def to_yolo(b):
    x1, y1, x2, y2, w, h = b
    cx, cy = (x1 + x2) / 2 / w, (y1 + y2) / 2 / h
    return f"0 {cx:.6f} {cy:.6f} {(x2 - x1) / w:.6f} {(y2 - y1) / h:.6f}"


# ----------------------------------------------------------------------- one sample
def render_sample(args, logo_path, rng, dst_noext, mask_noext):
    """Render mask first (cheap -> early skip), then beauty straight to JPEG.
    Returns the YOLO bbox tuple, or None if the logo is not visible."""
    clear_scene()
    setup_cycles(args)
    setup_world(rng)
    add_lights(rng)
    make_collider(rng)
    cloth = make_cloth(args, rng)

    # settle the cloth: evaluate frames in order so the solver caches folds
    scene = bpy.context.scene
    scene.frame_start = 1
    scene.frame_end = args.sim_frames
    for f in range(1, args.sim_frames + 1):
        scene.frame_set(f)

    # camera aims at the deformed cloth centre
    dg = bpy.context.evaluated_depsgraph_get()
    ev = cloth.evaluated_get(dg)
    cen = sum((cloth.matrix_world @ v.co for v in ev.data.vertices), Vector()) / len(ev.data.vertices)
    add_camera(rng, cen)

    place = logo_placement(rng)                     # same logo spot for both passes
    beauty = beauty_material(logo_path, place, rng)
    mask = mask_material(logo_path, place)
    bg = scene.world.node_tree.nodes["Background"].inputs["Strength"]
    world_strength = bg.default_value

    # pass 1 — MASK (logo emission on black world); Raw view so values are binary
    cloth.data.materials.clear()
    cloth.data.materials.append(mask)
    bg.default_value = 0.0
    scene.view_settings.view_transform = "Raw"
    scene.cycles.samples = 16
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = mask_noext
    bpy.ops.render.render(write_still=True)

    box = bbox_from_mask(mask_noext + ".png")
    if box is None:
        return None

    # pass 2 — BEAUTY straight to JPEG (no reload/re-encode)
    cloth.data.materials[0] = beauty
    bg.default_value = world_strength
    scene.view_settings.view_transform = "AgX"      # filmic tone map for realism
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

    # resolve --out against the script dir (Blender's cwd in --background is unreliable)
    out = Path(args.out)
    if not out.is_absolute():
        out = Path(__file__).resolve().parent / out
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
        stem = f"bac4_{i:06d}"
        dst_noext = str(out / "images" / split / stem)   # Blender appends .jpg
        mask_noext = str(tmp / f"{stem}_m")              # Blender appends .png
        try:
            b = render_sample(args, logo, rng, dst_noext, mask_noext)
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
    print(f"\n[done] {made}/{args.n} images -> {out.resolve()}")


if __name__ == "__main__":
    main()
