import present from "./assets.json";

const SET = new Set(present as string[]);

/** True when an asset path (relative to public/, e.g. "img/bulls.png") exists. */
export const has = (p: string): boolean => SET.has(p);

/** Returns the path if present, otherwise undefined — for optional <Img>. */
export const opt = (p: string): string | undefined => (SET.has(p) ? p : undefined);

// ── Canonical filenames the user can drop into public/img/ ──────────────────
// Team group photos. Each member carries their bounding box (as a % of the
// photo's width/height, x/y = top-left corner) so the scene can mask a precise
// spotlight over them. Boxes were taken from the Roboflow export at
// public/img/team/_annotations.coco.json (pixel bbox / 1402x1122 image size).
export type TeamMember = { name: string; role: string; x: number; y: number; w: number; h: number };
export type TeamGroup = { title: string; photo: string; members: TeamMember[] };

export const SUPERVISOR_TEAM: TeamGroup = {
  title: "Stakeholders",
  photo: "img/team/supervisor_team.jpeg",
  members: [
    { name: "Tillal Eldabi", role: "Supervisor", x: 0, y: 21.8, w: 27.0, h: 78.1 },
    { name: "Irfan Mehmood", role: "Supervisor", x: 24.5, y: 20.3, w: 29.2, h: 79.6 },
    { name: "Ian Stafford", role: "Supervisor", x: 52.5, y: 21.9, w: 25.5, h: 78.0 },
    { name: "Takao Maruyama", role: "Supervisor", x: 74.8, y: 15.4, w: 25.1, h: 84.5 },
  ],
};

export const STUDENT_TEAM: TeamGroup = {
  title: "Students",
  photo: "img/team/student_team.jpeg",
  members: [
    { name: "Ezichi Abel", role: "MSc AI & Data Analytics", x: 0, y: 20.6, w: 21.4, h: 79.3 },
    { name: "Jason Akhuemokhan", role: "MSc AI & Data Analytics", x: 16.8, y: 22.6, w: 25.8, h: 77.4 },
    { name: "Mai Xuan Hoa", role: "MSc AI & Data Analytics", x: 34.1, y: 17.5, w: 20.3, h: 82.4 },
    { name: "Simranjit Kaur", role: "MSc AI & Data Analytics", x: 45.2, y: 28.1, w: 22.2, h: 71.8 },
    { name: "Tabby Mungai", role: "MSc AI & Data Analytics", x: 63.8, y: 18.5, w: 17.4, h: 81.4 },
    { name: "Rashmi Yatawara", role: "MSc AI & Data Analytics", x: 75.7, y: 26.5, w: 24.3, h: 73.4 },
  ],
};

export const TEAM_GROUPS: TeamGroup[] = [SUPERVISOR_TEAM, STUDENT_TEAM];

// Partner / collaborator marks. Missing → labelled placeholder tile.
export const BULLS = "logo/bradford_bulls_logo.svg"; // Bradford Bulls RLFC
export const BRADFORD = "logo/university_of_bradford_logo.svg"; // University of Bradford
export const IAN = "img/person/ian_bradford_bulls.png"; // Ian Stafford portrait

// Product poster (full marketing artwork) shown as a showcase beat.
export const POSTER = "img/poster/poster.svg";

// ── Demonstration media (drop real clips/screens in; temp fallbacks until then) ─
// Detection demo stages. Drop real clips into public/video/. Until present each
// stage falls back to demo.mp4 (shown from a different point so they look
// distinct). `temp` flags the fallback so the UI can hint "sample footage".
export const STAGES = [
  { label: "Player & Team Detection", file: "video/team_detection.mp4", from: 0,
    caption: "Every player found & assigned to a team" },
  { label: "Logo Detection", file: "video/logo_detection.mp4", from: 150,
    caption: "Sponsor logos located on shirts & boards" },
  { label: "Body Segmentation", file: "video/body_segmentation.mp4", from: 300,
    caption: "Player silhouettes isolated for context" },
].map((s) => ({ ...s, src: opt(s.file), temp: !has(s.file) }));

export const DEMO_FALLBACK = "demo.mp4"; // bundled annotated footage

// "Hard cases" — real annotated frames where the sponsor logo is occluded /
// tiny / blurred / cropped. `cx`/`cy` (% of the 1920x1080 source) is the focal
// point the scene zooms into so the called-out logo box reads clearly.
export const HARDCASES = [
  { file: "hard_frames/occluded.jpg", tag: "Occluded by players", cx: 60, cy: 52 },
  { file: "hard_frames/far_and_small.jpg", tag: "Small & far away", cx: 56, cy: 55 },
  { file: "hard_frames/motion_blur.jpg", tag: "Motion blur", cx: 69, cy: 41 },
  { file: "hard_frames/partial_cropped.jpg", tag: "Partially cropped", cx: 15, cy: 50 },
].map((h) => ({ ...h, src: opt(h.file) ?? h.file }));

// Dashboard screenshot. Drop a real screen into public/img/dashboard/main.png;
// otherwise the scene draws a mock dashboard.
export const DASHBOARD = opt("img/dashboard/main.png");

// Full screen-recording of the live product. Shown as a late "see it for
// real" beat, near the end of the video, right before the closing scene.
export const PRODUCT_DEMO = opt("video/dashboard-product.mp4");

// Real sponsor logos (already copied in) used in the demo / pipeline strips.
export const SPONSORS = [
  "img/sponsors/aon.png",
  "img/sponsors/cch.png",
  "img/sponsors/klg.png",
  "img/sponsors/em.png",
  "img/sponsors/romantica.jpg",
  "img/sponsors/atm.png",
  "img/sponsors/topnotch.png",
  "img/sponsors/mna.png",
].filter(has);
