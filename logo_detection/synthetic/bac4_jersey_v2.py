"""bac4_jersey_v2.py — Batch render rugby jersey GLB với UV-painted sponsor logos.

Workflow:
  1. Import rugby jersey GLB (UV layout đã phân tích, chest center ≈ (0.305, 0.37))
  2. Mỗi sample: chọn logo ngẫu nhiên → paint lên UV texture → apply vào jersey material
  3. Random camera / lighting / body tilt / background (real game frame)
  4. Render + annotation YOLO từ vertex projection

Usage:
    blender --background --python bac4_jersey_v2.py -- \\
        --n 50 --logo-dir "Sponsor Logo" --out data_bac4_v2
"""

import sys, os, math, random, struct, json, shutil, argparse
from pathlib import Path

# ── Parse args ──────────────────────────────────────────────────────────────
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--n",          type=int,   default=20,   help="số ảnh cần render")
ap.add_argument("--glb",        default="logo_detection/meshes/rugby_jersey_-_visual_animation.glb")
ap.add_argument("--logo-dir",   default="Sponsor Logo")
ap.add_argument("--bg-dir",     default="data/real/auto/images", help="ảnh nền game thật")
ap.add_argument("--hdri",       default="",                help="thư mục HDRI (tùy chọn)")
ap.add_argument("--out",        default="logo_detection/synthetic/data_bac4_v2")
ap.add_argument("--size",       type=int,   default=640)
ap.add_argument("--seed",       type=int,   default=0)
ap.add_argument("--jpeg-min",   type=int,   default=72)
ap.add_argument("--jpeg-max",   type=int,   default=95)
# UV chest logo position (tinh chỉnh nếu cần sau khi test render)
ap.add_argument("--uv-u",  type=float, default=0.305,  help="UV U center of chest logo")
ap.add_argument("--uv-v",  type=float, default=0.375,  help="UV V center of chest logo")
ap.add_argument("--uv-w",  type=float, default=0.145,  help="logo width in UV space")
ap.add_argument("--debug-uv", action="store_true", help="render 1 ảnh với logo UV box highlight")
args = ap.parse_args(argv)

import bpy, bmesh
import numpy as np
from PIL import Image, ImageFilter, ImageEnhance

# ── Paths ────────────────────────────────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent.parent  # bradford_bull_v2/
GLB  = ROOT / args.glb
LOGO_DIR = ROOT / args.logo_dir
BG_DIR   = ROOT / args.bg_dir
OUT_DIR  = ROOT / args.out
IMG_DIR  = OUT_DIR / "images"
LBL_DIR  = OUT_DIR / "labels"
IMG_DIR.mkdir(parents=True, exist_ok=True)
LBL_DIR.mkdir(parents=True, exist_ok=True)

rng = random.Random(args.seed)
np.random.seed(args.seed)

TEX_SIZE = 4096  # jersey texture resolution

# ── UV chest region (từ phân tích mesh) ────────────────────────────────────
# Front panel UV center ≈ (0.305, 0.375), unit = UV [0,1]
UV_CX = args.uv_u
UV_CY = args.uv_v
UV_W  = args.uv_w   # logo width in UV space (height scaled by logo AR)


# ══════════════════════════════════════════════════════════════════════════════
# 1. Parse GLB: build vertex UV map for annotation
# ══════════════════════════════════════════════════════════════════════════════
def _read_glb_arrays(glb_path):
    with open(glb_path, "rb") as f:
        f.read(12)
        cl, _ = struct.unpack("<II", f.read(8))
        js = json.loads(f.read(cl))
        cl2, _ = struct.unpack("<II", f.read(8))
        bd = f.read(cl2)

    def _acc(i):
        a = js["accessors"][i]; bv = js["bufferViews"][a["bufferView"]]
        off = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
        nc = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}[a["type"]]
        fmt = {5126: "f", 5123: "H", 5125: "I", 5121: "B"}[a["componentType"]]
        stride = bv.get("byteStride", struct.calcsize(fmt) * nc)
        rows = [struct.unpack(f"{nc}{fmt}", bd[off + i * stride: off + i * stride + struct.calcsize(fmt) * nc])
                for i in range(a["count"])]
        return np.array(rows, dtype=np.float32)

    prim = js["meshes"][0]["primitives"][0]
    at = prim["attributes"]
    pos = _acc(at["POSITION"])
    uv  = _acc(at["TEXCOORD_0"])
    nrm = _acc(at["NORMAL"]) if "NORMAL" in at else None
    idx = _acc(prim["indices"]).astype(int).flatten()
    return pos, uv, nrm, idx

print("[v2] Parsing GLB vertex data...")
_pos, _uv, _nrm, _idx = _read_glb_arrays(GLB)


def get_logo_verts_local(uv_cx, uv_cy, uv_w, logo_ar=1.0):
    """Trả về array các vertex local-space positions nằm trong logo UV box."""
    uv_h = uv_w / max(logo_ar, 0.05)  # height tỉ lệ AR
    u0, u1 = uv_cx - uv_w / 2, uv_cx + uv_w / 2
    v0, v1 = uv_cy - uv_h / 2, uv_cy + uv_h / 2
    mask = (_uv[:, 0] >= u0) & (_uv[:, 0] <= u1) & \
           (_uv[:, 1] >= v0) & (_uv[:, 1] <= v1)
    verts = _pos[mask]  # (K, 3) local XYZ
    return verts, (u0, u1, v0, v1)


# ══════════════════════════════════════════════════════════════════════════════
# 2. Texture painting (Pillow)
# ══════════════════════════════════════════════════════════════════════════════
def paint_jersey_texture(logo_path: Path, uv_cx: float, uv_cy: float,
                         uv_w: float, jersey_color=(240, 240, 240),
                         debug_uv=False) -> tuple[Path, float, tuple]:
    """
    Tạo jersey texture mới:
      - Base màu jersey (trắng / Bradford Bulls color)
      - Paint logo PNG tại chest UV position
    Trả về (temp_png_path, logo_ar, uv_box)
    """
    # Base texture: màu jersey
    base = Image.new("RGB", (TEX_SIZE, TEX_SIZE), jersey_color)

    # Load logo RGBA
    logo_raw = Image.open(logo_path).convert("RGBA")
    logo_ar  = logo_raw.width / max(logo_raw.height, 1)

    # Compute logo size trên texture (pixel)
    uv_h = uv_w / max(logo_ar, 0.05)
    logo_pw = int(uv_w * TEX_SIZE)
    logo_ph = int(uv_h * TEX_SIZE)
    logo_pw = max(logo_pw, 32); logo_ph = max(logo_ph, 32)

    logo_resized = logo_raw.resize((logo_pw, logo_ph), Image.LANCZOS)

    # UV → PIL pixel: py = (1 - V) * H  (GLTF: V=0=bottom)
    # Logo center pixel:
    cx_px = int(uv_cx * TEX_SIZE)
    cy_px = int((1 - uv_cy) * TEX_SIZE)
    x0 = cx_px - logo_pw // 2
    y0 = cy_px - logo_ph // 2

    # Composite logo lên base texture
    base.paste(logo_resized, (x0, y0), logo_resized.split()[3])

    if debug_uv:
        from PIL import ImageDraw
        draw = ImageDraw.Draw(base)
        u0_px = cx_px - logo_pw // 2
        u1_px = cx_px + logo_pw // 2
        v0_px = cy_px - logo_ph // 2
        v1_px = cy_px + logo_ph // 2
        draw.rectangle([u0_px, v0_px, u1_px, v1_px], outline=(255, 0, 0), width=8)

    # Mild augmentation: slight brightness / saturation jitter
    if not debug_uv:
        enh = rng.uniform(0.85, 1.15)
        base = ImageEnhance.Brightness(base).enhance(enh)

    # Save temp texture
    tmp = Path(f"/tmp/jersey_tex_{os.getpid()}.png")
    base.save(str(tmp))

    uv_h2 = uv_w / max(logo_ar, 0.05)
    uv_box = (uv_cx - uv_w / 2, uv_cx + uv_w / 2,
              uv_cy - uv_h2 / 2, uv_cy + uv_h2 / 2)
    return tmp, logo_ar, uv_box


# ══════════════════════════════════════════════════════════════════════════════
# 3. Blender scene setup
# ══════════════════════════════════════════════════════════════════════════════
def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for block in [bpy.data.meshes, bpy.data.materials,
                  bpy.data.images, bpy.data.lights, bpy.data.cameras]:
        for item in list(block):
            block.remove(item)


def setup_render(size: int, jpeg_q: int):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device   = "GPU"
    sc.cycles.samples  = 64
    try:
        sc.cycles.device = "GPU"
        bpy.context.preferences.addons["cycles"].preferences.compute_device_type = "CUDA"
        bpy.context.preferences.addons["cycles"].preferences.get_devices()
        for d in bpy.context.preferences.addons["cycles"].preferences.devices:
            d.use = True
    except Exception:
        sc.cycles.device = "CPU"

    sc.render.resolution_x = size
    sc.render.resolution_y = size
    sc.render.image_settings.file_format = "JPEG"
    sc.render.image_settings.quality     = jpeg_q
    sc.render.film_transparent = False


def import_jersey(glb_path: Path):
    bpy.ops.import_scene.gltf(filepath=str(glb_path))
    # Tìm mesh object vừa import
    jersey = None
    for obj in bpy.context.selected_objects:
        if obj.type == "MESH":
            jersey = obj
            break
    if jersey is None:
        jersey = next((o for o in bpy.data.objects if o.type == "MESH"), None)
    if jersey is None:
        raise RuntimeError("Không tìm thấy mesh sau khi import GLB")
    return jersey


def apply_texture_to_jersey(jersey, tex_path: Path):
    """Thay texture của jersey material bằng file PNG mới."""
    if not jersey.data.materials:
        mat = bpy.data.materials.new("JerseyMat")
        jersey.data.materials.append(mat)
    else:
        mat = jersey.data.materials[0]

    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()

    # Principled BSDF
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Roughness"].default_value = 0.8
    bsdf.inputs["Specular IOR Level"].default_value = 0.05

    # Texture image
    img_node = nt.nodes.new("ShaderNodeTexImage")
    img = bpy.data.images.load(str(tex_path), check_existing=False)
    img_node.image = img
    img_node.interpolation = "Linear"

    # UV Map
    uv_node = nt.nodes.new("ShaderNodeUVMap")
    uv_node.uv_map = "UVMap"

    out_node = nt.nodes.new("ShaderNodeOutputMaterial")

    nt.links.new(uv_node.outputs["UV"],       img_node.inputs["Vector"])
    nt.links.new(img_node.outputs["Color"],   bsdf.inputs["Base Color"])
    nt.links.new(bsdf.outputs["BSDF"],        out_node.inputs["Surface"])


def setup_camera(jersey, rng_local: random.Random):
    """Camera nhìn từ phía trước jersey với random angle."""
    cam_data = bpy.data.cameras.new("Cam")
    cam_obj  = bpy.data.objects.new("Cam", cam_data)
    bpy.context.scene.collection.objects.link(cam_obj)
    bpy.context.scene.camera = cam_obj

    # Jersey center từ bounding box
    bb = [jersey.matrix_world @ v.co for v in jersey.data.vertices]
    cx = sum(v.x for v in bb) / len(bb)
    cy = sum(v.y for v in bb) / len(bb)
    cz = sum(v.z for v in bb) / len(bb)
    import mathutils
    center = mathutils.Vector((cx, cy, cz))

    # Camera distance
    dist = rng_local.uniform(1.4, 2.2)
    # Azimuth: frontal bias ±25°
    az = math.radians(rng_local.uniform(-25, 25))
    # Elevation: slight up-tilt
    el = math.radians(rng_local.uniform(-10, 15))

    # Camera position (jersey faces +Z)
    cam_x = cx + dist * math.sin(az)
    cam_y = cy - dist * math.cos(el) * math.cos(az)
    cam_z = cz + dist * math.sin(el)
    cam_obj.location = (cam_x, cam_y, cam_z)

    # Point at jersey center
    direction = center - cam_obj.location
    rot_quat = direction.to_track_quat("-Z", "Y")
    cam_obj.rotation_euler = rot_quat.to_euler()

    # Focal length DR
    cam_data.lens = rng_local.uniform(40, 85)
    return cam_obj


def setup_lighting(rng_local: random.Random, hdri_dir: str = ""):
    world = bpy.data.worlds.get("World")
    if world is None:
        world = bpy.data.worlds.new("World")
    bpy.context.scene.world = world
    world.use_nodes = True
    nt = world.node_tree
    nt.nodes.clear()
    bg_node  = nt.nodes.new("ShaderNodeBackground")
    out_node = nt.nodes.new("ShaderNodeOutputWorld")
    nt.links.new(bg_node.outputs["Background"], out_node.inputs["Surface"])

    # HDRI nếu có
    hdri_used = False
    if hdri_dir:
        hdris = list(Path(hdri_dir).glob("*.hdr")) + list(Path(hdri_dir).glob("*.exr"))
        if hdris:
            env_node = nt.nodes.new("ShaderNodeTexEnvironment")
            hdr_path = rng_local.choice(hdris)
            env_img  = bpy.data.images.load(str(hdr_path), check_existing=True)
            env_node.image = env_img
            coord_node  = nt.nodes.new("ShaderNodeTexCoord")
            map_node    = nt.nodes.new("ShaderNodeMapping")
            map_node.inputs["Rotation"].default_value[2] = rng_local.uniform(0, math.tau)
            nt.links.new(coord_node.outputs["Generated"], map_node.inputs["Vector"])
            nt.links.new(map_node.outputs["Vector"],     env_node.inputs["Vector"])
            nt.links.new(env_node.outputs["Color"],      bg_node.inputs["Color"])
            bg_node.inputs["Strength"].default_value = rng_local.uniform(0.8, 2.5)
            hdri_used = True

    if not hdri_used:
        # Procedural sky (Blender 5.x: dùng HOSEK_WILKIE)
        sky_node = nt.nodes.new("ShaderNodeTexSky")
        sky_node.sky_type = "HOSEK_WILKIE"
        elev = math.radians(rng_local.uniform(15, 60))
        az2  = math.radians(rng_local.uniform(0, 360))
        import mathutils
        sky_node.sun_direction = mathutils.Vector(
            (math.cos(elev) * math.sin(az2), math.cos(elev) * math.cos(az2), math.sin(elev))
        )
        sky_node.turbidity = rng_local.uniform(2.0, 6.0)
        coord2 = nt.nodes.new("ShaderNodeTexCoord")
        nt.links.new(coord2.outputs["Generated"], sky_node.inputs["Vector"])
        nt.links.new(sky_node.outputs["Color"],   bg_node.inputs["Color"])
        bg_node.inputs["Strength"].default_value = rng_local.uniform(0.6, 1.8)

    # Key light thêm vào
    light_data = bpy.data.lights.new("KeyLight", "AREA")
    light_data.energy = rng_local.uniform(200, 600)
    light_data.size   = rng_local.uniform(1.0, 3.0)
    light_obj = bpy.data.objects.new("KeyLight", light_data)
    bpy.context.scene.collection.objects.link(light_obj)
    light_obj.location = (rng_local.uniform(-2, 2), rng_local.uniform(-3, -1),
                          rng_local.uniform(2, 4))


def set_background_image(bg_dir: Path, rng_local: random.Random):
    """Dùng ảnh game thật làm nền (world background image plane)."""
    if not bg_dir.exists():
        return
    frames = list(bg_dir.glob("*.jpg")) + list(bg_dir.glob("*.png"))
    if not frames:
        return
    chosen = rng_local.choice(frames)

    world = bpy.context.scene.world
    nt = world.node_tree

    # Thêm env texture cho background riêng (mix với lighting)
    # Dùng background image via compositor
    bpy.context.scene.render.film_transparent = True
    bpy.context.scene.use_nodes = True
    comp = bpy.context.scene.node_tree
    if not comp.nodes:
        return
    # Compositor: Image → Scale → AlphaOver (under render)
    comp.nodes.clear()
    rl   = comp.nodes.new("CompositorNodeRLayers")
    bg   = comp.nodes.new("CompositorNodeImage")
    scale = comp.nodes.new("CompositorNodeScale")
    ao   = comp.nodes.new("CompositorNodeAlphaOver")
    comp_out = comp.nodes.new("CompositorNodeComposite")

    bg_img = bpy.data.images.load(str(chosen), check_existing=False)
    bg.image = bg_img
    scale.space = "RENDER_SIZE"
    scale.frame_method = "CROP"

    comp.links.new(bg.outputs["Image"],   scale.inputs["Image"])
    comp.links.new(scale.outputs["Image"], ao.inputs[1])
    comp.links.new(rl.outputs["Image"],   ao.inputs[2])
    comp.links.new(ao.outputs["Image"],   comp_out.inputs["Image"])
    bpy.context.scene.render.film_transparent = True


# ══════════════════════════════════════════════════════════════════════════════
# 4. Annotation: project logo verts → 2D bbox
# ══════════════════════════════════════════════════════════════════════════════
def compute_yolo_bbox(jersey, cam_obj, logo_verts_local, img_w, img_h):
    """
    logo_verts_local: (K,3) local-space positions của các vert trong logo UV box
    Trả về (cx, cy, w, h) normalized, hoặc None nếu không visible.
    """
    if len(logo_verts_local) == 0:
        return None

    from bpy_extras.object_utils import world_to_camera_view
    import mathutils
    sc = bpy.context.scene
    mw = jersey.matrix_world

    xs2d, ys2d = [], []
    for v in logo_verts_local:
        world_pt = mw @ mathutils.Vector(v.tolist())
        co_cam = world_to_camera_view(sc, cam_obj, world_pt)
        # co_cam.x ∈ [0,1] left→right, co_cam.y ∈ [0,1] bottom→top
        if 0 <= co_cam.x <= 1 and 0 <= co_cam.y <= 1 and co_cam.z > 0:
            xs2d.append(co_cam.x)
            ys2d.append(1 - co_cam.y)  # flip Y: 0=top

    if len(xs2d) < 4:
        return None

    x_min, x_max = min(xs2d), max(xs2d)
    y_min, y_max = min(ys2d), max(ys2d)
    cx = (x_min + x_max) / 2
    cy = (y_min + y_max) / 2
    w  = x_max - x_min
    h  = y_max - y_min
    if w < 0.005 or h < 0.005:
        return None
    return cx, cy, w, h


# ══════════════════════════════════════════════════════════════════════════════
# 5. Logo files
# ══════════════════════════════════════════════════════════════════════════════
LOGO_FILES = [p for p in LOGO_DIR.iterdir()
              if p.suffix.lower() in {".png", ".jpg", ".jpeg"}]
if not LOGO_FILES:
    raise RuntimeError(f"Không tìm thấy logo nào trong {LOGO_DIR}")
print(f"[v2] Tìm thấy {len(LOGO_FILES)} logos, render {args.n} ảnh")


# ══════════════════════════════════════════════════════════════════════════════
# 6. Main render loop
# ══════════════════════════════════════════════════════════════════════════════
clear_scene()

for i in range(args.n):
    sample_rng = random.Random(args.seed + i * 1000)
    jpeg_q = sample_rng.randint(args.jpeg_min, args.jpeg_max)
    setup_render(args.size, jpeg_q)

    # --- Import jersey GLB ---
    jersey = import_jersey(GLB)

    # --- Chọn logo ngẫu nhiên ---
    logo_path = sample_rng.choice(LOGO_FILES)
    logo_img_check = Image.open(logo_path)
    logo_ar = logo_img_check.width / max(logo_img_check.height, 1)
    logo_img_check.close()

    # --- UV width variation ---
    uv_w_sample = UV_W * sample_rng.uniform(0.8, 1.2)
    # Nhỏ jitter trong chest area
    uv_cx = UV_CX + sample_rng.uniform(-0.015, 0.015)
    uv_cy = UV_CY + sample_rng.uniform(-0.015, 0.015)

    # --- Jersey color (Bradford Bulls: trắng chủ đạo, thêm variation nhỏ) ---
    base_c = sample_rng.randint(228, 250)
    jersey_color = (base_c, base_c, base_c)

    # --- Paint texture ---
    tex_path, _, uv_box = paint_jersey_texture(
        logo_path, uv_cx, uv_cy, uv_w_sample,
        jersey_color=jersey_color,
        debug_uv=args.debug_uv
    )

    # --- Apply texture ---
    apply_texture_to_jersey(jersey, tex_path)

    # --- Body tilt ---
    tilt_deg = sample_rng.uniform(-12, 12)
    jersey.rotation_euler[0] = math.radians(sample_rng.uniform(-5, 5))
    jersey.rotation_euler[1] = math.radians(tilt_deg)
    jersey.rotation_euler[2] = math.radians(sample_rng.uniform(-8, 8))
    bpy.context.view_layer.update()

    # --- Camera ---
    cam_obj = setup_camera(jersey, sample_rng)

    # --- Lighting ---
    setup_lighting(sample_rng, args.hdri)

    # --- Background ---
    set_background_image(BG_DIR, sample_rng)

    # --- Logo verts cho annotation ---
    logo_verts, _ = get_logo_verts_local(uv_cx, uv_cy, uv_w_sample, logo_ar)

    # --- Render ---
    img_name = f"{i:05d}.jpg"
    out_path = str(IMG_DIR / img_name)
    bpy.context.scene.render.filepath = out_path
    bpy.ops.render.render(write_still=True)

    # --- Annotation ---
    bbox = compute_yolo_bbox(jersey, cam_obj, logo_verts, args.size, args.size)
    lbl_path = LBL_DIR / f"{i:05d}.txt"
    if bbox:
        cx2, cy2, w2, h2 = bbox
        lbl_path.write_text(f"0 {cx2:.6f} {cy2:.6f} {w2:.6f} {h2:.6f}\n")
        print(f"[{i+1}/{args.n}] {logo_path.name}  bbox=({cx2:.3f},{cy2:.3f},{w2:.3f},{h2:.3f})")
    else:
        lbl_path.write_text("")
        print(f"[{i+1}/{args.n}] {logo_path.name}  (logo not visible)")

    # --- Cleanup ---
    try:
        tex_path.unlink(missing_ok=True)
    except Exception:
        pass

    # Clear scene trừ Blender internals
    clear_scene()

# --- YAML dataset file ---
yaml_path = OUT_DIR / "dataset.yaml"
yaml_path.write_text(
    f"path: {OUT_DIR}\n"
    f"train: images\n"
    f"val: images\n"
    f"nc: 1\n"
    f"names: ['logo']\n"
)

print(f"\n[v2] Done. {args.n} ảnh tại {OUT_DIR}")
print(f"     YOLO labels: {LBL_DIR}")
print(f"     Dataset yaml: {yaml_path}")
