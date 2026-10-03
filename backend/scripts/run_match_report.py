"""Run the analytics pipeline over full-match videos and export the location report.

The web flow (upload -> /processing -> dashboard -> "Export .xlsx") needs the whole
file pushed through a browser upload and a running Next.js frontend, which is a poor
fit for a 100-minute match. This runner points the *same* pipeline at a folder of
video files, writes the analyses into the same SQLite DB (so they still show up in
the dashboard), and drops one .xlsx per video into --out-dir.

    conda activate bradford_bulls
    python backend/scripts/run_match_report.py --kit home

Only the analytics path runs. The annotated preview, body-part segmentation and
team-detection overlay videos are full-fps renders capped at the first ~30-60 s of
footage; they cost minutes and contribute nothing to the report, so they are off
here (--with-overlays to re-enable).

Team references: the global backend/data/team_refs.pkl was built for ONE kit
(currently away/black). Running a home match against it silently labels the wrong
side as the target team, which drops every Bradford logo. So this runner always
bootstraps references from the video itself, per (video, kit), and caches them in
backend/data/auto_refs/ — pass --team-refs to override, or --no-team-filter to
count logos on every player.
"""
from __future__ import annotations

import argparse
import os
import pickle
import re
import shutil
import sys
import time
import uuid
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = BACKEND_DIR.parent
sys.path.insert(0, str(BACKEND_DIR))

VIDEO_EXT = {".mp4", ".mov", ".avi", ".mkv", ".m4v", ".ts", ".webm"}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="Full-match logo analytics -> per-location Excel report",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--input-dir", type=Path, default=REPO_ROOT / "match_input",
                   help="folder of match videos to process")
    p.add_argument("--video", type=Path, action="append", default=None,
                   help="process this file only (repeatable; overrides --input-dir)")
    p.add_argument("--out-dir", type=Path, default=REPO_ROOT / "match_reports",
                   help="where the .xlsx reports are written")
    p.add_argument("--kit", choices=("home", "away"), default="home",
                   help="Bradford's kit in these videos (home=white/Top Notch, "
                        "away=black/Floor Tonic)")
    p.add_argument("--fps", type=float, default=2.0,
                   help="frames analysed per second of video")
    p.add_argument("--event", default=None,
                   help="event name for the analysis (default: the file's stem)")
    p.add_argument("--criteria", default=None,
                   help="comma-separated AI criteria for the export; default = the "
                        "saved Settings value")
    p.add_argument("--detector", choices=("yolo", "rfdetr"), default=None,
                   help="override the logo detector backend (default: backend/.env)")
    p.add_argument("--audience", type=int, default=0, help="audience size for EMV")
    p.add_argument("--cpm", type=float, default=22.0, help="base CPM for EMV")
    p.add_argument("--placement", default="Live Broadcast TV",
                   help="placement type for EMV")
    p.add_argument("--team-refs", type=Path, default=None,
                   help="use this team-reference pickle instead of bootstrapping")
    p.add_argument("--no-team-filter", action="store_true",
                   help="count logos on every player, not just the target team")
    p.add_argument("--with-overlays", action="store_true",
                   help="also render the preview / bodyseg / team-detect videos")
    p.add_argument("--force", action="store_true",
                   help="re-run videos that already have an analysis")
    p.add_argument("--export-only", default=None, metavar="ANALYSIS_ID",
                   help="skip detection; just re-export this existing analysis")
    return p.parse_args(argv)


def apply_env(args: argparse.Namespace) -> None:
    """Set pipeline knobs BEFORE app.config is imported (env beats backend/.env)."""
    os.environ["SAMPLE_FPS"] = str(args.fps)
    if not args.with_overlays:
        os.environ["PREVIEW_ENABLED"] = "false"
        os.environ["ENABLE_BODYSEG"] = "false"
        os.environ["TEAMDET_VIDEO_ENABLED"] = "false"
    if args.no_team_filter:
        os.environ["TEAM_FILTER_ENABLED"] = "false"
    if args.detector:
        os.environ["LOGO_BACKEND"] = args.detector
        os.environ["DETECTOR_BACKEND"] = args.detector


# -- helpers --------------------------------------------------------------

def hms(seconds: float) -> str:
    seconds = int(max(0, seconds))
    h, rem = divmod(seconds, 3600)
    m, s = divmod(rem, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def register_video(video: Path, storage_root: Path) -> str:
    """Make `video` reachable under the storage root and return its key.

    Already inside the store -> reuse it. Same volume -> hardlink (instant, no
    second copy of a multi-GB match). Otherwise copy.
    """
    storage_root.mkdir(parents=True, exist_ok=True)
    if video.parent.resolve() == storage_root.resolve():
        return video.name
    key = f"{uuid.uuid4().hex}{video.suffix.lower()}"
    dest = storage_root / key
    try:
        os.link(video, dest)
    except OSError:
        shutil.copy2(video, dest)
    return key


def existing_analysis(session, video_name: str, kit: str):
    """The most recent completed analysis for this file+kit that has exposure
    facts (older runs predate facts_json and can't produce an AI %)."""
    from app.db.models import Analysis, Job, JobStatus

    rows = (
        session.query(Job, Analysis)
        .join(Analysis, Job.analysis_id == Analysis.id)
        .filter(Job.video_name == video_name, Job.kit == kit,
                Job.status == JobStatus.done)
        .order_by(Analysis.analyzed_at.desc())
        .all()
    )
    for _job, analysis in rows:
        if analysis.facts_json:
            return analysis
    return None


def team_refs_for(video: Path, kit: str, explicit: Path | None):
    """Refs pickle path for this (video, kit), bootstrapping + caching if needed."""
    if explicit is not None:
        return explicit
    cache_dir = BACKEND_DIR / "data" / "auto_refs"
    cache_dir.mkdir(parents=True, exist_ok=True)
    cached = cache_dir / f"{video.stem}-{kit}.pkl"
    if cached.exists():
        print(f"  team refs: reusing {cached.name}")
        return cached

    from app.pipeline.teamid.bootstrap import build_refs_from_video

    print(f"  team refs: bootstrapping the {kit} kit from the video ...", flush=True)
    t0 = time.time()
    refs = build_refs_from_video(video, kit)
    if refs is None:
        print("  team refs: bootstrap failed - running WITHOUT the team filter")
        return None
    with cached.open("wb") as f:
        pickle.dump(refs, f)
    meta = refs.get("meta", {})
    print(f"  team refs: built in {hms(time.time() - t0)} "
          f"(target crops {meta.get('n_target', '?')}, other {meta.get('n_other', '?')}) "
          f"-> {cached.name}")
    return cached


def make_progress_printer():
    """Console progress: one line per stage, throttled, with a detection ETA."""
    state = {"last": 0.0, "detect_t0": None, "stage": None}

    def cb(pct: int, stage: str, detail: str) -> None:
        now = time.time()
        m = re.match(r"(\d+)/(\d+) frames", detail)
        if stage == "detect" and state["detect_t0"] is None:
            state["detect_t0"] = now
        new_stage = stage != state["stage"]
        if not new_stage and now - state["last"] < 15:
            return
        state["last"] = now
        state["stage"] = stage
        eta = ""
        if m and state["detect_t0"]:
            done, total = int(m.group(1)), int(m.group(2))
            spent = now - state["detect_t0"]
            if done > 0 and spent > 5:
                rate = done / spent
                eta = f"  ~{hms((total - done) / rate)} left  ({rate:.1f} fps)"
        print(f"  [{pct:3d}%] {stage:<9} {detail}{eta}", flush=True)

    return cb


def print_table(rows: list[dict]) -> None:
    def cell(v):
        return "     -" if v is None else f"{v:6.2f}"

    print(f"  {'Location':<20} {'Logo':<20} {'Human':>6} {'AI':>6} {'Adj':>6} {'Vis':>6}")
    h = ai = adj = 0.0
    for r in rows:
        print(f"  {r['locationName']:<20} {(r['logo'] or '-'):<20} "
              f"{cell(r['humanPercentage'])} {cell(r['aiPercentage'])} "
              f"{cell(r['aiAdjusted'])} {cell(r['visibility'])}")
        h += r["humanPercentage"] or 0.0
        ai += r["aiPercentage"] or 0.0
        adj += r["aiAdjusted"] or 0.0
    print(f"  {'TOTAL':<20} {'':<20} {h:6.2f} {ai:6.2f} {adj:6.2f}")


# -- one video ------------------------------------------------------------

def export_report(analysis_id: str, out_dir: Path, criteria: str | None) -> Path:
    from app.api.routes_analyses import _build_breakdown
    from app.api.xlsx_export import build_location_workbook
    from app.db.base import session_scope
    from app.db.repository import AnalysisRepository

    with session_scope() as s:
        analysis = AnalysisRepository(s).get(analysis_id)
        if analysis is None:
            raise SystemExit(f"analysis {analysis_id} not found")
        enabled, kit, rows, zone_detail = _build_breakdown(s, analysis, criteria)
        content = build_location_workbook(
            analysis=analysis, rows=rows, zone_detail=zone_detail,
            enabled=enabled, kit=kit,
        )
        stem = analysis.event_name or analysis.video_name or analysis_id

    out_dir.mkdir(parents=True, exist_ok=True)
    out = out_dir / f"{re.sub(r'[^A-Za-z0-9._-]+', '_', stem)}_locations.xlsx"
    out.write_bytes(content)
    print_table(rows)
    print(f"  criteria: {', '.join(enabled)}")
    return out


def run_one(video: Path, args: argparse.Namespace) -> Path | None:
    from app.config import get_settings
    from app.db.base import session_scope
    from app.db.repository import AnalysisRepository, JobRepository
    from app.pipeline import ingest, orchestrator
    from app.storage import get_storage

    settings = get_settings()
    storage = get_storage()
    event = args.event or video.stem

    print(f"\n=== {video.name}  (kit={args.kit}, {args.fps} fps) ===")

    with session_scope() as s:
        prior = existing_analysis(s, video.name, args.kit)
        prior_id = prior.id if prior else None
    if prior_id and not args.force:
        print(f"  already analysed ({prior_id}) - exporting; use --force to re-run")
        return export_report(prior_id, args.out_dir, args.criteria)

    meta = ingest.probe(video)
    n_frames = int(meta.duration_seconds * args.fps)
    print(f"  {meta.width}x{meta.height} @ {meta.fps}fps, {hms(meta.duration_seconds)} "
          f"-> {n_frames} sampled frames")

    refs_key = None
    if settings.team_filter_enabled:
        refs_path = team_refs_for(video, args.kit, args.team_refs)
        if refs_path is not None:
            with refs_path.open("rb") as f:
                refs_key = storage.save(f, refs_path.name)

    storage_key = register_video(video, settings.storage_dir)
    with session_scope() as s:
        job = JobRepository(s).create(
            event_name=event, video_name=video.name, storage_key=storage_key,
            audience_size=args.audience, placement_type=args.placement,
            cpm_base=args.cpm, kit=args.kit, team_refs_key=refs_key,
        )
        job_id = job.id

    t0 = time.time()
    orchestrator.run_analysis(job_id, progress_cb=make_progress_printer())

    with session_scope() as s:
        job = JobRepository(s).get(job_id)
        status, err, analysis_id = job.status.value, job.error, job.analysis_id
    if status != "done" or not analysis_id:
        print(f"  FAILED after {hms(time.time() - t0)}: {err}")
        return None

    print(f"  analysed in {hms(time.time() - t0)} -> analysis {analysis_id}")

    # The team filter is the stage most likely to be silently wrong (it decides
    # which kit is Bradford from the video itself), so surface what it did. A
    # drop rate near 100 % means it picked the wrong side — re-run with
    # --no-team-filter, or with --team-refs pointing at known-good references.
    with session_scope() as s:
        result = AnalysisRepository(s).get(analysis_id).result_json
    tf = result.get("teamFilter") or {}
    if tf.get("enabled"):
        print(f"  team filter: kept {tf.get('kept')} / dropped {tf.get('dropped')} "
              f"logo detections (drop rate {tf.get('dropRate')})")
    else:
        print("  team filter: OFF - logos counted on every player")
    # AnalysisResult logos carry the display label under "name" (see aggregate).
    brands = [str(logo.get("name") or logo.get("class") or "?")
              for logo in result.get("logos", [])]
    print(f"  {len(brands)} brand(s) detected: {', '.join(brands[:12])}"
          f"{' ...' if len(brands) > 12 else ''}")

    return export_report(analysis_id, args.out_dir, args.criteria)


# -- entry point ----------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass

    args = parse_args(argv)
    apply_env(args)

    try:
        import openpyxl  # noqa: F401
    except ImportError:
        print("openpyxl is required for the Excel export:  pip install openpyxl")
        return 2

    from app.db.base import init_db

    init_db()

    if args.export_only:
        export_report(args.export_only, args.out_dir, args.criteria)
        return 0

    if args.video:
        videos = [Path(v).resolve() for v in args.video]
        missing = [v for v in videos if not v.is_file()]
        if missing:
            print("not found: " + ", ".join(str(m) for m in missing))
            return 2
    else:
        if not args.input_dir.is_dir():
            print(f"input folder does not exist: {args.input_dir}")
            return 2
        videos = sorted(
            p for p in args.input_dir.iterdir()
            if p.is_file() and p.suffix.lower() in VIDEO_EXT
        )
        if not videos:
            print(f"no video files in {args.input_dir} "
                  f"({', '.join(sorted(VIDEO_EXT))})")
            return 2

    print(f"{len(videos)} video(s) -> {args.out_dir}")
    written: list[Path] = []
    for video in videos:
        try:
            out = run_one(video, args)
        except Exception as exc:  # one bad file must not lose the rest of the batch
            import traceback

            traceback.print_exc()
            print(f"  ERROR on {video.name}: {exc}")
            out = None
        if out is not None:
            written.append(out)
            print(f"  report: {out}")

    print(f"\ndone - {len(written)}/{len(videos)} report(s) written to {args.out_dir}")
    return 0 if len(written) == len(videos) else 1


if __name__ == "__main__":
    raise SystemExit(main())
