import React from "react";
import { AbsoluteFill, Img, staticFile, useCurrentFrame, interpolate } from "remotion";
import { C } from "../theme";
import { seg } from "../anim";

/** The shared canvas: near-black, a faint grid, a slow drifting red glow and a
 *  soft vignette. `bars` adds the thin brand rails top & bottom (Title/Closing).
 *  Unless `bars` (hero scenes) a small project logo sits top-right as a mark. */
export const Bg: React.FC<{ bars?: boolean; plain?: boolean; children?: React.ReactNode }> = ({
  bars,
  plain,
  children,
}) => {
  const f = useCurrentFrame();
  const drift = interpolate(f, [0, 300], [0, 40]);
  return (
    <AbsoluteFill
      style={{ background: `radial-gradient(120% 120% at 50% 0%, ${C.bg0}, ${C.bg1})` }}
    >
      {/* drifting brand glow */}
      <AbsoluteFill
        style={{
          background: `radial-gradient(circle at ${18 + drift * 0.1}% 14%, rgba(255,59,48,0.18), transparent 46%)`,
        }}
      />
      <AbsoluteFill
        style={{
          background: `radial-gradient(circle at 88% 96%, rgba(124,137,160,0.12), transparent 48%)`,
        }}
      />
      {/* code grid */}
      <AbsoluteFill
        style={{
          backgroundImage: `linear-gradient(rgba(255,255,255,0.022) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.022) 1px, transparent 1px)`,
          backgroundSize: "72px 72px",
          maskImage: "radial-gradient(120% 90% at 50% 40%, #000 55%, transparent 100%)",
          WebkitMaskImage:
            "radial-gradient(120% 90% at 50% 40%, #000 55%, transparent 100%)",
        }}
      />
      {/* vignette */}
      <AbsoluteFill
        style={{
          boxShadow: "inset 0 0 360px 80px rgba(0,0,0,0.65)",
        }}
      />
      {bars ? (
        <>
          <div style={{ position: "absolute", top: 0, left: 0, width: "100%", height: 5, background: C.red, boxShadow: `0 0 24px ${C.red}` }} />
          <div style={{ position: "absolute", bottom: 0, left: 0, width: "100%", height: 5, background: C.red, boxShadow: `0 0 24px ${C.red}` }} />
        </>
      ) : plain ? null : (
        <Img
          src={staticFile("logo/logolense-dark.svg")}
          style={{ position: "absolute", top: 104, right: 120, height: 40, opacity: 0.85 * seg(f, 4, 14) }}
        />
      )}
      {children}
    </AbsoluteFill>
  );
};
