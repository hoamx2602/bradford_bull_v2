import { loadFont as loadMono } from "@remotion/google-fonts/JetBrainsMono";
import { loadFont as loadInter } from "@remotion/google-fonts/Inter";

// Nerd / monospace face for headlines, prompts, labels and numbers.
export const mono = loadMono().fontFamily;
// Inter for running body copy.
export const inter = loadInter().fontFamily;

// Kept as an alias so older references don't break; points at mono now.
export const space = mono;

// LogoLense brand (logo Group_34.svg): red #BA0201 + near-black #090A0E,
// dressed up in a VVTerm / terminal keynote palette.
export const C = {
  red: "#FF3B30", // brighter, screen-friendly brand red (accent, prompt)
  redDeep: "#BA0201", // true logo red (fills, bars)
  crimson: "#7C0A0A", // deep shade
  term: "#43D17A", // terminal green — success / "ok" ticks
  amber: "#F5A623", // warnings / secondary highlight
  steel: "#7C89A0", // cool neutral secondary
  white: "#F4F6FB",
  muted: "#7E8696", // dim comment-grey
  dim: "#4A5160", // dimmer chrome / borders
  card: "rgba(255,255,255,0.035)", // glassy surface on near-black
  cardLine: "rgba(255,255,255,0.08)", // hairline border
  ink: "#05060A", // deepest black — chip text on bright fills
  bg0: "#0A0B10",
  bg1: "#050609",
};

// Spacing rhythm reused across scenes (1920×1080 stage).
export const PAD = 120;
