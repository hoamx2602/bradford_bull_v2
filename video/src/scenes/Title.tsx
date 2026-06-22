import React from "react";
import { useCurrentFrame, useVideoConfig, spring, AbsoluteFill, Img, staticFile } from "remotion";
import { Bg } from "../components/Bg";
import { C, inter } from "../theme";
import { seg } from "../anim";
import { Sfx } from "../components/Sfx";

export const Title: React.FC = () => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();
  const pop = spring({ frame: f - 6, fps, config: { damping: 200 } });
  const ul = seg(f, 22, 22);
  return (
    <Bg bars>
      <Sfx name="chime" from={6} volume={0.6} />
      <Sfx name="tick" from={48} volume={0.35} />
      <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
        <Img
          src={staticFile("logo/logolense-dark.svg")}
          style={{
            width: 900,
            opacity: pop,
            transform: `scale(${0.93 + 0.07 * pop})`,
            filter: "drop-shadow(0 0 60px rgba(255,59,48,0.22))",
          }}
        />
        <div style={{ height: 7, width: 900 * ul, background: C.red, borderRadius: 4, marginTop: 30, boxShadow: `0 0 22px ${C.red}` }} />
        <div style={{ fontFamily: inter, fontWeight: 500, fontSize: 40, color: "#c5f000", marginTop: 42, opacity: seg(f, 34, 18) }}>
          Your Brand, Our Focus
        </div>
        <div style={{ fontFamily: inter, fontWeight: 600, fontSize: 28, color: C.red, marginTop: 48, opacity: seg(f, 48, 18), letterSpacing: 0.5 }}>
          Intelligent Sponsorship Visibility &amp; Brand Analytics Using AI
        </div>
      </AbsoluteFill>
    </Bg>
  );
};
