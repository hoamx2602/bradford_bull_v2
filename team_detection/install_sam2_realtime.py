#!/usr/bin/env python3
"""
Install the SAM2 *real-time* (camera predictor) fork — the one thing that makes
`process_video.py --tracker sam2` actually work.

Why this script exists
----------------------
The SAM2 path in process_video.py needs ``build_sam2_camera_predictor``.  The
upstream facebookresearch ``sam2`` package does **not** provide it — only the
real-time fork does:

    https://github.com/Gy920/segment-anything-2-real-time

Without the fork, ``SAM2Tracker`` raises ImportError and the pipeline silently
falls back to ByteTrack.  This installer sets the fork up so it works on a
plain Windows + conda machine that has **no CUDA/MSVC build toolchain**:

  1. clone the fork into  team_detection/sam2_realtime/
  2. patch it so it installs without compiling anything:
       * the optional ``sam2._C`` connected-components CUDA extension is only
         built when SAM2_BUILD_CUDA=1 (default: skipped)
       * ``get_connected_components`` gets a pure-Python OpenCV fallback so the
         model's hole-filling still works without the CUDA extension
  3. move any shadowing ``./sam2`` source clone out of the import path
     (a leftover clone in the cwd hides the installed package and breaks
     Hydra initialisation)
  4. (re)install the fork as an editable package, replacing upstream ``sam2``
  5. download + verify the sam2.1 checkpoint

Usage (run from anywhere; paths are resolved relative to this file):
    python install_sam2_realtime.py                 # 'large' checkpoint
    python install_sam2_realtime.py --size base+
    python install_sam2_realtime.py --no-checkpoint # skip the download
    SAM2_BUILD_CUDA=1 python install_sam2_realtime.py   # also compile _C
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

HERE       = Path(__file__).resolve().parent
FORK_URL   = "https://github.com/Gy920/segment-anything-2-real-time.git"
FORK_DIR   = HERE / "sam2_realtime"
CKPT_DIR   = HERE / "checkpoints"
CKPT_BASE  = "https://dl.fbaipublicfiles.com/segment_anything_2/092824"
CKPTS      = {
    "large": "sam2.1_hiera_large.pt",
    "base+": "sam2.1_hiera_base_plus.pt",
    "small": "sam2.1_hiera_small.pt",
    "tiny":  "sam2.1_hiera_tiny.pt",
}
# A truncated download is far smaller than the real weights; reject those.
MIN_CKPT_MB = {"large": 600, "base+": 250, "small": 100, "tiny": 100}


def run(cmd, **kw):
    print(f"  $ {' '.join(str(c) for c in cmd)}")
    subprocess.run(cmd, check=True, **kw)


# ── 1. clone ────────────────────────────────────────────────────────────────

def clone_fork():
    if (FORK_DIR / "setup.py").exists():
        print(f"[1/5] Fork already present at {FORK_DIR}")
        return
    print(f"[1/5] Cloning fork -> {FORK_DIR}")
    run(["git", "clone", "--depth", "1", FORK_URL, str(FORK_DIR)])


# ── 2. patch so it installs without a build toolchain ─────────────────────────

def patch_setup():
    """Gate the CUDA extension behind SAM2_BUILD_CUDA (default off)."""
    f = FORK_DIR / "setup.py"
    txt = f.read_text(encoding="utf-8")
    if "SAM2_BUILD_CUDA" in txt:
        return
    txt = txt.replace(
        "from setuptools import find_packages, setup\n"
        "from torch.utils.cpp_extension import BuildExtension, CUDAExtension",
        "import os\n\n"
        "from setuptools import find_packages, setup\n"
        "from torch.utils.cpp_extension import BuildExtension, CUDAExtension\n\n"
        "# Only compile the optional CUDA connected-components extension when\n"
        "# explicitly requested.  On Windows a matching MSVC + CUDA toolchain is\n"
        "# usually unavailable, so default OFF and rely on the OpenCV fallback.\n"
        'BUILD_CUDA = os.getenv("SAM2_BUILD_CUDA", "0") == "1"',
    )
    txt = txt.replace(
        "    ext_modules=get_extensions(),\n"
        '    cmdclass={"build_ext": BuildExtension.with_options(no_python_abi_suffix=True)},',
        "    ext_modules=get_extensions() if BUILD_CUDA else [],\n"
        "    cmdclass=({\"build_ext\": BuildExtension.with_options("
        "no_python_abi_suffix=True)}\n"
        "              if BUILD_CUDA else {}),",
    )
    f.write_text(txt, encoding="utf-8")
    print("      patched setup.py (CUDA extension now optional)")


def patch_misc():
    """Add an OpenCV fallback to get_connected_components (no _C required)."""
    f = FORK_DIR / "sam2" / "utils" / "misc.py"
    txt = f.read_text(encoding="utf-8")
    if "OpenCV) fallback" in txt:
        return
    old = (
        "    from sam2 import _C\n\n"
        "    return _C.get_connected_componnets(mask.to(torch.uint8).contiguous())"
    )
    new = (
        "    try:\n"
        "        from sam2 import _C\n\n"
        "        return _C.get_connected_componnets("
        "mask.to(torch.uint8).contiguous())\n"
        "    except (ImportError, ModuleNotFoundError):\n"
        "        # Pure-Python (OpenCV) fallback — used when the optional CUDA\n"
        "        # extension `sam2._C` was not compiled. Same semantics: per-pixel\n"
        "        # component label + the area of the component each pixel is in.\n"
        "        import cv2\n"
        "        import numpy as np\n\n"
        "        m = mask.to(torch.uint8).contiguous().cpu().numpy()\n"
        "        n, _, h, w = m.shape\n"
        "        labels_out = np.zeros((n, 1, h, w), dtype=np.int32)\n"
        "        counts_out = np.zeros((n, 1, h, w), dtype=np.int32)\n"
        "        for i in range(n):\n"
        "            num, lab, stats, _ = cv2.connectedComponentsWithStats(\n"
        "                m[i, 0], connectivity=8)\n"
        "            areas = stats[:, cv2.CC_STAT_AREA].astype(np.int32)\n"
        "            area_map = areas[lab]\n"
        "            area_map[lab == 0] = 0\n"
        "            labels_out[i, 0] = lab\n"
        "            counts_out[i, 0] = area_map\n"
        "        device = mask.device\n"
        "        return (torch.from_numpy(labels_out).to(device),\n"
        "                torch.from_numpy(counts_out).to(device))"
    )
    if old not in txt:
        print("      WARNING: could not find get_connected_components body to "
              "patch — upstream may have changed. Skipping.")
        return
    f.write_text(txt.replace(old, new), encoding="utf-8")
    print("      patched misc.py (OpenCV connected-components fallback)")


def patch_fork():
    print("[2/5] Patching fork for toolchain-free install")
    patch_setup()
    patch_misc()


# ── 3. un-shadow a leftover ./sam2 source clone ───────────────────────────────

def unshadow():
    """
    A bare `sam2/` directory in team_detection/ becomes a namespace package and
    shadows the installed fork on `import sam2` (because the cwd is on sys.path
    first).  That hides build_sam2_camera_predictor AND skips the Hydra config
    init in the fork's __init__.py.  Move it aside.
    """
    shadow = HERE / "sam2"
    if shadow.is_dir():
        dest = HERE / "sam2_facebook_clone_UNUSED"
        i = 1
        while dest.exists():
            dest = HERE / f"sam2_facebook_clone_UNUSED_{i}"
            i += 1
        print(f"[3/5] Moving shadowing clone {shadow.name}/ -> {dest.name}/")
        shadow.rename(dest)
    else:
        print("[3/5] No shadowing ./sam2 clone — good")


# ── 4. install ────────────────────────────────────────────────────────────────

def install():
    print("[4/5] Installing fork (editable, no CUDA build)")
    pip = [sys.executable, "-m", "pip"]
    # Remove the upstream package first so the editable fork wins cleanly.
    subprocess.run(pip + ["uninstall", "-y", "SAM-2"],
                   check=False)
    env = dict(os.environ)
    env.setdefault("SAM2_BUILD_CUDA", "0")
    run(pip + ["install", "-e", ".", "--no-build-isolation"],
        cwd=str(FORK_DIR), env=env)


# ── 5. checkpoint ─────────────────────────────────────────────────────────────

def checkpoint(size):
    name = CKPTS[size]
    dst  = CKPT_DIR / name
    CKPT_DIR.mkdir(exist_ok=True)
    min_mb = MIN_CKPT_MB[size]
    if dst.exists() and dst.stat().st_size > min_mb * 1e6:
        print(f"[5/5] Checkpoint OK: {dst} "
              f"({dst.stat().st_size/1e6:.0f} MB)")
        return
    if dst.exists():
        print(f"[5/5] Checkpoint looks truncated "
              f"({dst.stat().st_size/1e6:.1f} MB) — re-downloading")
        dst.unlink()
    else:
        print(f"[5/5] Downloading checkpoint {name}")
    run(["curl", "-L", "--fail", "-o", str(dst), f"{CKPT_BASE}/{name}"])
    mb = dst.stat().st_size / 1e6
    if mb < min_mb:
        raise RuntimeError(
            f"Download incomplete: {dst} is only {mb:.1f} MB "
            f"(expected > {min_mb} MB). Re-run the script.")
    print(f"      downloaded {mb:.0f} MB")


# ── verify ────────────────────────────────────────────────────────────────────

def verify():
    print("Verifying import (from a neutral cwd) ...")
    code = (
        "from sam2.build_sam import build_sam2_camera_predictor; "
        "import sam2, os; "
        "print('  sam2 ->', sam2.__file__); "
        "print('  build_sam2_camera_predictor: OK')"
    )
    # Run from the repo root, not team_detection, to dodge any ./sam2 shadow.
    subprocess.run([sys.executable, "-c", code],
                   check=True, cwd=str(HERE.parent))


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--size", default="large", choices=list(CKPTS),
                    help="checkpoint size to download (default: large)")
    ap.add_argument("--no-checkpoint", action="store_true",
                    help="skip the checkpoint download")
    args = ap.parse_args()

    clone_fork()
    patch_fork()
    unshadow()
    install()
    if not args.no_checkpoint:
        checkpoint(args.size)
    verify()
    print("\nDone. SAM2 real-time is installed. Run the pipeline with:")
    print("    python process_video.py --video <clip> --refs <refs.pkl> "
          "--tracker sam2")


if __name__ == "__main__":
    main()
