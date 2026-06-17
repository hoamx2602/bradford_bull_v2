import React from "react";
import { AbsoluteFill, Video, staticFile, useCurrentFrame } from "remotion";
import { C, inter } from "../theme";
import { seg } from "../anim";
import { PRODUCT_DEMO } from "../assets";

// A late "see it for real" beat: a slice of an actual recorded session with
// the live product, shown full-bleed. Rest ~1s before the clip fades in,
// then label/caption land after it's clearly on screen.
export const ProductDemo: React.FC = () => {
  const f = useCurrentFrame();
  const clipIn = seg(f, 30, 18);
  return (
    <AbsoluteFill style={{ background: "#000" }}>
      {PRODUCT_DEMO ? (
        <Video
          src={staticFile(PRODUCT_DEMO)}
          muted
          startFrom={600}
          style={{ width: "100%", height: "100%", objectFit: "cover", opacity: clipIn }}
        />
      ) : null}
      <AbsoluteFill style={{ background: "linear-gradient(180deg, rgba(0,0,0,0.55) 0%, transparent 22%, transparent 70%, rgba(0,0,0,0.7) 100%)", opacity: clipIn }} />

      <div style={{ position: "absolute", top: 56, left: 64, display: "flex", alignItems: "center", gap: 16, opacity: seg(f, 58, 14) }}>
        <div style={{ padding: "9px 18px", borderRadius: 999, background: C.red, color: C.white, fontFamily: inter, fontWeight: 700, fontSize: 22, letterSpacing: 1 }}>
          LIVE PRODUCT
        </div>
        <span style={{ fontFamily: inter, fontWeight: 600, fontSize: 22, color: "rgba(255,255,255,0.8)" }}>
          LogoLens — analytics dashboard
        </span>
      </div>

      <div style={{ position: "absolute", bottom: 56, left: 64, fontFamily: inter, fontWeight: 500, fontSize: 34, color: C.white, opacity: seg(f, 66, 14), textShadow: "0 2px 12px rgba(0,0,0,0.8)" }}>
        A real session, not a mockup.
      </div>
    </AbsoluteFill>
  );
};
