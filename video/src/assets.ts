import present from "./assets.json";
import teamPolys from "./team_polys.json";

const SET = new Set(present as string[]);

const POLYS = teamPolys as unknown as Record<string, [number, number][]>;

/** True when an asset path (relative to public/, e.g. "img/bulls.png") exists. */
export const has = (p: string): boolean => SET.has(p);

/** Returns the path if present, otherwise undefined — for optional <Img>. */
export const opt = (p: string): string | undefined => (SET.has(p) ? p : undefined);

// ── Canonical filenames the user can drop into public/img/ ──────────────────
// Team group photos. Each member carries `points` — their segmentation outline
// as [x%, y%] of the photo — so the scene can cut a person-shaped spotlight
// hole out of the dim overlay. Outlines come from the Roboflow COCO export at
// public/img/team/_annotations.coco.json, extracted by scripts/extract-team-polys.mjs
// into src/team_polys.json (regenerate that whenever the annotations change).
export type Pt = [number, number];
export type TeamMember = { name: string; role: string; points: Pt[] };
export type TeamGroup = { title: string; photo: string; members: TeamMember[] };

// Just names + roles here; the polygon is joined in from team_polys.json by name.
// `poly` overrides which polygon key to use when the displayed name differs from
// the segmentation label (e.g. when two members' name labels need swapping while
// the highlight boxes keep their on-screen appearance order).
type MemberDef = { name: string; role: string; poly?: string };
const group = (title: string, photo: string, defs: MemberDef[]): TeamGroup => ({
  title,
  photo,
  members: defs.map(({ poly, ...d }) => ({ ...d, points: (POLYS[poly ?? d.name] ?? []) as Pt[] })),
});

export const SUPERVISOR_TEAM = group("Stakeholders", "img/team/supervisor_team.jpeg", [
  { name: "Prof. Tillal Eldabi", role: "Project Supervisor" },
  { name: "Dr. Irfan Mehmood", role: "Project Supervisor & AI Lead" },
  { name: "Ian Stafford", role: "Owner & Partner" },
  { name: "Dr. Takao Maruyama", role: "Advisor" },
]);

export const STUDENT_TEAM = group("Students", "img/team/student_team.jpeg", [
  { name: "Ezichi Abel", role: "Data Collection" },
  { name: "Jason Akhuemokhan", role: "Frame Annotation" },
  { name: "Mai Xuan Hoa", role: "Technical Leader — Model Training & Evaluation" },
  { name: "Rashmi Yatawara", role: "Reports & Documentation", poly: "Simranjit Kaur" },
  { name: "Tabby Mungai", role: "UI/UX" },
  { name: "Simranjit Kaur", role: "Data Processing & Visualization", poly: "Rashmi Yatawara" },
]);

export const TEAM_GROUPS: TeamGroup[] = [SUPERVISOR_TEAM, STUDENT_TEAM];

// Partner / collaborator marks. Missing → labelled placeholder tile.
export const BULLS = "logo/bradford_bulls_logo.svg"; // Bradford Bulls RLFC
export const BRADFORD = "logo/university_of_bradford_logo.svg"; // University of Bradford
export const IAN = "img/person/ian_bradford_bulls.png"; // Ian Stafford portrait

// Product poster (full marketing artwork) shown as a showcase beat.
export const POSTER = "img/poster/poster.svg";

// Landscape key-art poster used as the opening title card.
export const MAIN_POSTER = "poster/main-poster.jpeg";

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
