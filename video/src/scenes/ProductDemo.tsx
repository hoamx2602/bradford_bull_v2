import React from "react";
import { AbsoluteFill, Video, staticFile, useCurrentFrame } from "remotion";
import { C, inter } from "../theme";
import { seg } from "../anim";
import { PRODUCT_DEMO } from "../assets";

// The recording is 113.768s — played in full (no slicing), so the scene
// length below must match it exactly (rounded up a hair for safety).
export const PRODUCT_DEMO_SECS = 113.8;

// A late "see it for real" beat: the full recorded session with the live
// product, shown full-bleed. Rest ~1s before the clip fades in; the label
// and caption land after it's clearly on screen, then fade out so the rest
// of the recording plays clean.
export const ProductDemo: React.FC = () => {
  const f = useCurrentFrame();
  const clipIn = seg(f, 30, 18);
  const labelOpacity = seg(f, 58, 14) * (1 - seg(f, 220, 30));
  return (
    <AbsoluteFill style={{ background: "#000" }}>
      {PRODUCT_DEMO ? (
        <Video
          src={staticFile(PRODUCT_DEMO)}
          muted
          style={{ width: "100%", height: "100%", objectFit: "cover", opacity: clipIn }}
        />
      ) : null}
      <AbsoluteFill style={{ background: "linear-gradient(180deg, rgba(0,0,0,0.55) 0%, transparent 22%, transparent 70%, rgba(0,0,0,0.7) 100%)", opacity: labelOpacity }} />

      <div style={{ position: "absolute", top: 56, left: 64, display: "flex", alignItems: "center", gap: 16, opacity: labelOpacity }}>
        <div style={{ padding: "9px 18px", borderRadius: 999, background: C.red, color: C.white, fontFamily: inter, fontWeight: 700, fontSize: 22, letterSpacing: 1 }}>
          LIVE PRODUCT
        </div>
        <span style={{ fontFamily: inter, fontWeight: 600, fontSize: 22, color: "rgba(255,255,255,0.8)" }}>
          LogoLens — analytics dashboard
        </span>
      </div>
    </AbsoluteFill>
  );
};
