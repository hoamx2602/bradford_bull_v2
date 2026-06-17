import React from "react";
import { AbsoluteFill, Img, staticFile, useCurrentFrame, interpolate } from "remotion";
import { C, inter } from "../theme";
import { seg } from "../anim";
import { POSTER } from "../assets";

/** Product-poster showcase: the full marketing artwork, gently zooming, on a
 *  clean dark stage. Lets the design speak before the outro. */
export const Poster: React.FC = () => {
  const f = useCurrentFrame();
  const ap = seg(f, 0, 16);
  const zoom = interpolate(f, [0, 165], [1.0, 1.045], { extrapolateRight: "clamp" });
  return (
    <AbsoluteFill style={{ background: `radial-gradient(120% 120% at 50% 30%, ${C.bg0}, ${C.bg1})` }}>
      <AbsoluteFill
        style={{ background: `radial-gradient(circle at 20% 10%, rgba(255,59,48,0.14), transparent 46%)` }}
      />
      <div
        style={{
          position: "absolute",
          top: 70,
          left: 0,
          width: "100%",
          textAlign: "center",
          fontFamily: inter,
          fontWeight: 700,
          fontSize: 22,
          letterSpacing: 4,
          color: C.red,
          opacity: seg(f, 6, 14),
        }}
      >
        THE PRODUCT
      </div>
      <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
        <Img
          src={staticFile(POSTER)}
          style={{
            height: 940,
            borderRadius: 18,
            border: `1px solid ${C.cardLine}`,
            boxShadow: "0 40px 90px rgba(0,0,0,0.6)",
            opacity: ap,
            transform: `scale(${zoom}) translateY(${(1 - ap) * 16}px)`,
          }}
        />
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
