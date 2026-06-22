// Scans public/img and writes src/assets.json — a flat list of asset paths
// (relative to public/, forward-slashed) that actually exist on disk.
// Scenes read this so optional user assets (team photos, club logos, Ian's
// photo) gracefully fall back to placeholders when a file isn't present yet.
import { readdirSync, statSync, writeFileSync } from "node:fs";
import { join, relative, sep } from "node:path";
import { fileURLToPath } from "node:url";
import { dirname } from "node:path";

const here = dirname(fileURLToPath(import.meta.url));
const root = join(here, "..");
const publicDir = join(root, "public");

const out = [];
const walk = (dir) => {
  for (const name of readdirSync(dir)) {
    const p = join(dir, name);
    if (statSync(p).isDirectory()) walk(p);
    else if (/\.(png|jpe?g|webp|svg|mp4|webm|mov|m4v)$/i.test(name))
      out.push(relative(publicDir, p).split(sep).join("/"));
  }
};
for (const sub of ["img", "logo", "video", "hard_frames"]) {
  try {
    walk(join(publicDir, sub));
  } catch {
    /* dir may not exist yet */
  }
}
out.sort();
writeFileSync(join(root, "src", "assets.json"), JSON.stringify(out, null, 2) + "\n");
console.log(`scan-assets: ${out.length} image(s) ->`, out.join(", ") || "(none)");
