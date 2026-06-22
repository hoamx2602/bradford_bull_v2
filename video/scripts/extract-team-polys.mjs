// Reads the Roboflow COCO export and emits src/team_polys.json — for each
// labelled person, their segmentation outline as [x%, y%] points (relative to
// the source image size). The Team scene uses these to cut a person-shaped
// spotlight hole out of the dim overlay instead of a plain rectangle.
import { readFileSync, writeFileSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const here = dirname(fileURLToPath(import.meta.url));
const root = join(here, "..");
const coco = JSON.parse(
  readFileSync(join(root, "public/img/team/_annotations.coco.json"), "utf8")
);

const catById = {};
for (const c of coco.categories) catById[c.id] = c.name;
const imgById = {};
for (const im of coco.images) imgById[im.id] = im;

const out = {};
for (const ann of coco.annotations) {
  const cat = catById[ann.category_id];
  if (!cat || cat === "Test") continue;
  const im = imgById[ann.image_id];
  const W = im.width;
  const H = im.height;
  const seg = ann.segmentation[0];
  const pts = [];
  for (let i = 0; i < seg.length; i += 2) {
    pts.push([
      +((seg[i] / W) * 100).toFixed(2),
      +((seg[i + 1] / H) * 100).toFixed(2),
    ]);
  }
  out[cat] = pts;
}

writeFileSync(join(root, "src", "team_polys.json"), JSON.stringify(out) + "\n");
console.log("extract-team-polys:", Object.keys(out).join(", "));
