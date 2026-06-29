"""bac4_v2_render.py — Bước 2: Blender render từ manifest (chạy với Blender --python).

Đọc manifest.json từ bước paint → import jersey GLB → apply texture → render + annotation.

Usage (gọi từ bac4_jersey_v2.sh, không chạy trực tiếp):
    blender --background --python bac4_v2_render.py -- --manifest path/to/manifest.json
"""

import sys, os, math, random, struct, json, argparse, subprocess
from pathlib import Path

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--manifest", required=True)
ap.add_argument("--glb",      default="logo_detection/meshes/rugby_jersey_-_visual_animation.glb")
ap.add_argument("--bg-dir",   default="data/real/auto/images")
ap.add_argument("--hdri",     default="")
ap.add_argument("--size",     type=int, default=640)
args = ap.parse_args(argv)

import bpy
import numpy as np

# Blender chạy trên Windows → cần convert Linux path → Windows UNC path
def to_win(p: str) -> str:
    # Convert any path to Windows UNC path.
    p = str(p).replace("\\", "/")   # normalize to forward slashes
    if p.startswith("//"):
        # Already a UNC path (e.g. //wsl.localhost/Ubuntu/...) → normalize backslash
        return p.replace("/", "\\")
    if p.startswith("/"):
        # Linux absolute path → prepend WSL UNC
        return "\\\\wsl.localhost\\Ubuntu" + p.replace("/", "\\")
    # Windows drive path or relative → return as-is
    return p

ROOT     = Path(__file__).resolve().parent.parent.parent
GLB      = ROOT / args.glb
BG_DIR   = ROOT / args.bg_dir
manifest = json.loads(Path(args.manifest).read_text())
OUT_DIR  = Path(args.manifest).parent
IMG_DIR  = OUT_DIR / "images"
LBL_DIR  = OUT_DIR / "labels"
IMG_DIR.mkdir(exist_ok=True)
LBL_DIR.mkdir(exist_ok=True)

# ── Parse GLB vertex UV (cho annotation) ────────────────────────────────────
def _read_glb(glb_path):
    import struct as _s
    with open(glb_path, "rb") as f:
        f.read(12)
        cl, _ = _s.unpack("<II", f.read(8)); js = json.loads(f.read(cl))
        cl2, _ = _s.unpack("<II", f.read(8)); bd = f.read(cl2)

    def _a(i):
        a = js["accessors"][i]; bv = js["bufferViews"][a["bufferView"]]
        off = bv.get("byteOffset", 0) + a.get("byteOffset", 0); cnt = a["count"]
        nc = {"SCALAR": 1, "VEC2": 2, "VEC3": 3}[a["type"]]
        fmt = {5126: "f", 5123: "H", 5125: "I"}[a["componentType"]]
        stride = bv.get("byteStride", _s.calcsize(fmt) * nc)
        return np.array([_s.unpack(f"{nc}{fmt}", bd[off+i*stride:off+i*stride+_s.calcsize(fmt)*nc])
                         for i in range(cnt)], dtype=np.float32)

    p = js["meshes"][0]["primitives"][0]["attributes"]
    return _a(p["POSITION"]), _a(p["TEXCOORD_0"])

print("[render] Loading GLB vertex data...")
_POS_GLTF, _UV = _read_glb(GLB)
# Convert GLTF Y-up → Blender Z-up: Bx=Gx, By=-Gz, Bz=Gy
# This gives positions in Blender LOCAL space, matching jersey.matrix_world expectations.
_POS = np.column_stack([_POS_GLTF[:, 0], -_POS_GLTF[:, 2], _POS_GLTF[:, 1]])


def logo_verts(uv_cx, uv_cy, uv_w, uv_h):
    u0, u1 = uv_cx - uv_w / 2, uv_cx + uv_w / 2
    v0, v1 = uv_cy - uv_h / 2, uv_cy + uv_h / 2
    mask = (_UV[:, 0] >= u0) & (_UV[:, 0] <= u1) & (_UV[:, 1] >= v0) & (_UV[:, 1] <= v1)
    return _POS[mask]


# ── Scene helpers ─────────────────────────────────────────────────────────────
def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for col in [bpy.data.meshes, bpy.data.materials,
                bpy.data.images, bpy.data.lights, bpy.data.cameras]:
        for it in list(col):
            col.remove(it)
    # Reset compositor (Blender 5.x: node_tree via compositor access)
    try:
        bpy.context.scene.render.film_transparent = False
        comp = bpy.context.scene.compositing_node_tree
        if comp:
            comp.nodes.clear()
    except Exception:
        pass


def setup_render(size, jpeg_q):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    try:
        sc.cycles.device = "GPU"
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.compute_device_type = "CUDA"
        prefs.get_devices()
        for d in prefs.devices:
            d.use = True
    except Exception:
        sc.cycles.device = "CPU"
    sc.cycles.samples = 64
    sc.render.resolution_x = size
    sc.render.resolution_y = size
    sc.render.image_settings.file_format = "JPEG"
    sc.render.image_settings.quality     = jpeg_q
    sc.render.film_transparent = False


def import_jersey():
    bpy.ops.import_scene.gltf(filepath=to_win(str(GLB)))
    for obj in bpy.context.selected_objects:
        if obj.type == "MESH":
            return obj
    return next((o for o in bpy.data.objects if o.type == "MESH"), None)


def apply_texture(jersey, tex_path):
    if not jersey.data.materials:
        mat = bpy.data.materials.new("JerseyMat")
        jersey.data.materials.append(mat)
    else:
        mat = jersey.data.materials[0]
    # Blender 5.x: access node_tree directly (use_nodes deprecated but still works)
    nt = mat.node_tree; nt.nodes.clear()
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Roughness"].default_value = 0.75
    try:
        bsdf.inputs["Specular IOR Level"].default_value = 0.04
    except KeyError:
        pass
    img_node = nt.nodes.new("ShaderNodeTexImage")
    win_tex = to_win(str(tex_path))
    img_node.image = bpy.data.images.load(win_tex, check_existing=False)
    img_node.interpolation = "Linear"
    uv = nt.nodes.new("ShaderNodeUVMap"); uv.uv_map = "UVMap"
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(uv.outputs["UV"],          img_node.inputs["Vector"])
    nt.links.new(img_node.outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(bsdf.outputs["BSDF"],      out.inputs["Surface"])


def setup_camera(jersey, rng_l):
    import mathutils
    cd = bpy.data.cameras.new("Cam")
    co = bpy.data.objects.new("Cam", cd)
    bpy.context.scene.collection.objects.link(co)
    bpy.context.scene.camera = co
    bb = [jersey.matrix_world @ v.co for v in jersey.data.vertices]
    cx = sum(v.x for v in bb) / len(bb)
    cy = sum(v.y for v in bb) / len(bb)
    cz = sum(v.z for v in bb) / len(bb)
    center = mathutils.Vector((cx, cy, cz))
    dist = rng_l.uniform(1.8, 3.5)
    az   = math.radians(rng_l.uniform(-25, 25))
    el   = math.radians(rng_l.uniform(-8, 18))
    co.location = (cx + dist * math.sin(az),
                   cy - dist * math.cos(el) * math.cos(az),
                   cz + dist * math.sin(el))
    d = center - co.location
    co.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    cd.lens = rng_l.uniform(42, 85)
    return co


def setup_lighting(rng_l, hdri_dir=""):
    world = bpy.data.worlds.get("World") or bpy.data.worlds.new("World")
    bpy.context.scene.world = world
    world.use_nodes = True
    nt = world.node_tree; nt.nodes.clear()
    bg = nt.nodes.new("ShaderNodeBackground")
    nt.links.new(bg.outputs["Background"], nt.nodes.new("ShaderNodeOutputWorld").inputs["Surface"])
    hdri_used = False
    if hdri_dir:
        hdris = list(Path(hdri_dir).glob("*.hdr")) + list(Path(hdri_dir).glob("*.exr"))
        if hdris:
            env = nt.nodes.new("ShaderNodeTexEnvironment")
            env.image = bpy.data.images.load(to_win(str(rng_l.choice(hdris))), check_existing=True)
            coord = nt.nodes.new("ShaderNodeTexCoord")
            mp    = nt.nodes.new("ShaderNodeMapping")
            mp.inputs["Rotation"].default_value[2] = rng_l.uniform(0, math.tau)
            import mathutils
            nt.links.new(coord.outputs["Generated"], mp.inputs["Vector"])
            nt.links.new(mp.outputs["Vector"], env.inputs["Vector"])
            nt.links.new(env.outputs["Color"], bg.inputs["Color"])
            bg.inputs["Strength"].default_value = rng_l.uniform(0.8, 2.5)
            hdri_used = True
    if not hdri_used:
        import mathutils
        sky = nt.nodes.new("ShaderNodeTexSky")
        sky.sky_type = "HOSEK_WILKIE"
        el = math.radians(rng_l.uniform(15, 60))
        az = math.radians(rng_l.uniform(0, 360))
        sky.sun_direction = mathutils.Vector(
            (math.cos(el)*math.sin(az), math.cos(el)*math.cos(az), math.sin(el)))
        sky.turbidity = rng_l.uniform(2, 6)
        coord2 = nt.nodes.new("ShaderNodeTexCoord")
        nt.links.new(coord2.outputs["Generated"], sky.inputs["Vector"])
        nt.links.new(sky.outputs["Color"], bg.inputs["Color"])
        bg.inputs["Strength"].default_value = rng_l.uniform(0.6, 1.8)
    ld = bpy.data.lights.new("Key", "AREA"); ld.energy = rng_l.uniform(250, 700)
    lo = bpy.data.objects.new("Key", ld)
    bpy.context.scene.collection.objects.link(lo)
    lo.location = (rng_l.uniform(-2, 2), rng_l.uniform(-3, -1), rng_l.uniform(2, 4))


def set_background(bg_dir, rng_l):
    if not bg_dir.exists(): return
    frames = list(bg_dir.glob("*.jpg")) + list(bg_dir.glob("*.png"))
    if not frames: return
    try:
        bpy.context.scene.render.film_transparent = True
        # Blender 5.x: compositing node tree via bpy.context.scene.compositing_node_tree
        comp = bpy.context.scene.compositing_node_tree
        if comp is None:
            return
        comp.nodes.clear()
        rl   = comp.nodes.new("CompositorNodeRLayers")
        bg_n = comp.nodes.new("CompositorNodeImage")
        scl  = comp.nodes.new("CompositorNodeScale")
        ao   = comp.nodes.new("CompositorNodeAlphaOver")
        cout = comp.nodes.new("CompositorNodeComposite")
        bg_n.image = bpy.data.images.load(to_win(str(rng_l.choice(frames))), check_existing=False)
        scl.space = "RENDER_SIZE"; scl.frame_method = "CROP"
        comp.links.new(bg_n.outputs["Image"], scl.inputs["Image"])
        comp.links.new(scl.outputs["Image"],  ao.inputs[1])
        comp.links.new(rl.outputs["Image"],   ao.inputs[2])
        comp.links.new(ao.outputs["Image"],   cout.inputs["Image"])
    except Exception as e:
        print(f"[bg] compositor skip: {e}")


def compute_bbox(jersey, cam, verts_local):
    if len(verts_local) == 0: return None
    from bpy_extras.object_utils import world_to_camera_view
    import mathutils
    sc = bpy.context.scene; mw = jersey.matrix_world
    xs, ys = [], []
    for v in verts_local:
        wp = mw @ mathutils.Vector(v.tolist())
        c  = world_to_camera_view(sc, cam, wp)
        if 0 <= c.x <= 1 and 0 <= c.y <= 1 and c.z > 0:
            xs.append(c.x); ys.append(1 - c.y)
    if len(xs) < 4: return None
    x0, x1 = min(xs), max(xs); y0, y1 = min(ys), max(ys)
    w = x1 - x0; h = y1 - y0
    if w < 0.005 or h < 0.005: return None
    return (x0+x1)/2, (y0+y1)/2, w, h


# ── Main render loop ──────────────────────────────────────────────────────────
print(f"[render] {len(manifest)} samples → {IMG_DIR}")
for entry in manifest:
    i   = entry["idx"]
    rng = random.Random(entry["cam_seed"])

    clear_scene()
    setup_render(args.size, entry["jpeg_q"])

    jersey = import_jersey()
    apply_texture(jersey, entry["tex"])  # raw string, not Path (avoids Windows path normalization)

    # Body tilt
    jersey.rotation_euler[0] = math.radians(entry["tilt_x"])
    jersey.rotation_euler[1] = math.radians(entry["tilt_y"])
    jersey.rotation_euler[2] = math.radians(entry["tilt_z"])
    bpy.context.view_layer.update()

    cam = setup_camera(jersey, rng)
    setup_lighting(rng, args.hdri)
    set_background(BG_DIR, rng)

    out_path = str(IMG_DIR / f"{i:05d}.jpg")
    bpy.context.scene.render.filepath = out_path
    bpy.ops.render.render(write_still=True)

    verts = logo_verts(entry["uv_cx"], entry["uv_cy"], entry["uv_w"], entry["uv_h"])
    bbox  = compute_bbox(jersey, cam, verts)
    lbl   = LBL_DIR / f"{i:05d}.txt"
    if bbox:
        cx, cy, w, h = bbox
        lbl.write_text(f"0 {cx:.6f} {cy:.6f} {w:.6f} {h:.6f}\n")
        status = f"bbox=({cx:.3f},{cy:.3f},{w:.3f},{h:.3f})"
    else:
        lbl.write_text("")
        status = "logo not visible"
    print(f"[{i+1}/{len(manifest)}] {entry['brand']}  {status}")

# YAML
(OUT_DIR / "dataset.yaml").write_text(
    f"path: {OUT_DIR}\ntrain: images\nval: images\nnc: 1\nnames: ['logo']\n")
print(f"\n[render] Done. Images: {IMG_DIR}")
