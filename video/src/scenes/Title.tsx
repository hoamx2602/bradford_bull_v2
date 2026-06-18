import React from "react";
import { useCurrentFrame, AbsoluteFill, Img, staticFile, interpolate } from "remotion";
import { Bg } from "../components/Bg";
import { C } from "../theme";
import { seg } from "../anim";
import { MAIN_POSTER } from "../assets";
import { Sfx } from "../components/Sfx";

// Opening title card: the landscape key-art poster, held for a few seconds
// with a gentle fade + slow zoom.
export const Title: React.FC = () => {
  const f = useCurrentFrame();
  const ap = seg(f, 2, 18);
  const zoom = interpolate(f, [0, 150], [1.0, 1.04], { extrapolateRight: "clamp" });
  return (
    <Bg plain>
      <Sfx name="chime" from={6} volume={0.6} />
      <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
        <Img
          src={staticFile(MAIN_POSTER)}
          style={{
            width: 1500,
            maxWidth: "82%",
            borderRadius: 20,
            border: `1px solid ${C.cardLine}`,
            boxShadow: "0 40px 90px rgba(0,0,0,0.6)",
            opacity: ap,
            transform: `scale(${zoom}) translateY(${(1 - ap) * 16}px)`,
          }}
        />
      </AbsoluteFill>
    </Bg>
  );
};
