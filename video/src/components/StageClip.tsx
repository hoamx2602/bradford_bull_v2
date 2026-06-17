import React from "react";
import { AbsoluteFill, Video, staticFile, useCurrentFrame } from "remotion";
import { C, inter } from "../theme";
import { seg } from "../anim";
import { DEMO_FALLBACK } from "../assets";

/** Full-frame detection demo clip with a stage label. Plays the real clip if
 *  dropped in, else the bundled demo footage (from a given offset). */
export const StageClip: React.FC<{
  label: string;
  caption: string;
  idx: number;
  total: number;
  src?: string;
  from?: number;
  temp?: boolean;
}> = ({ label, caption, idx, total, src, from = 0, temp }) => {
  const f = useCurrentFrame();
  const fade = seg(f, 0, 10);
  const real = src ?? DEMO_FALLBACK;
  return (
    <AbsoluteFill style={{ background: "#000" }}>
      <Video
        src={staticFile(real)}
        muted
        startFrom={temp ? from : 0}
        style={{ width: "100%", height: "100%", objectFit: "cover", opacity: fade }}
      />
      {/* gradient scrims for legibility */}
      <AbsoluteFill style={{ background: "linear-gradient(180deg, rgba(0,0,0,0.55) 0%, transparent 22%, transparent 70%, rgba(0,0,0,0.7) 100%)", opacity: fade }} />

      {/* top-left stage label */}
      <div style={{ position: "absolute", top: 56, left: 64, display: "flex", alignItems: "center", gap: 16, opacity: seg(f, 6, 12) }}>
        <div style={{ padding: "9px 18px", borderRadius: 999, background: C.red, color: C.white, fontFamily: inter, fontWeight: 700, fontSize: 22, letterSpacing: 1 }}>
          {label}
        </div>
        <span style={{ fontFamily: inter, fontWeight: 600, fontSize: 22, color: "rgba(255,255,255,0.8)" }}>
          {idx} / {total}
        </span>
      </div>

      {/* bottom caption */}
      <div style={{ position: "absolute", bottom: 56, left: 64, fontFamily: inter, fontWeight: 500, fontSize: 34, color: C.white, opacity: seg(f, 12, 14), textShadow: "0 2px 12px rgba(0,0,0,0.8)" }}>
        {caption}
      </div>

      {temp ? (
        <div style={{ position: "absolute", bottom: 24, right: 28, fontFamily: inter, fontWeight: 500, fontSize: 16, color: "rgba(255,255,255,0.45)", opacity: fade }}>
          sample footage — replace in public/video/
        </div>
      ) : null}
    </AbsoluteFill>
  );
};
