import React from "react";
import { useCurrentFrame, AbsoluteFill, Img, staticFile } from "remotion";
import { Bg } from "../components/Bg";
import { C, inter } from "../theme";
import { seg } from "../anim";
import { LogoTile } from "../components/Atoms";
import { BULLS, BRADFORD } from "../assets";
import { Sfx } from "../components/Sfx";

export const Closing: React.FC = () => {
  const f = useCurrentFrame();
  const ul = seg(f, 14, 18);
  return (
    <Bg bars>
      <Sfx name="chime" from={2} volume={0.6} />
      <Sfx name="pop" from={46} volume={0.4} />
      <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
        <Img
          src={staticFile("logo/logolense-dark.svg")}
          style={{ width: 660, opacity: seg(f, 2, 16), filter: "drop-shadow(0 0 50px rgba(255,59,48,0.2))" }}
        />
        <div style={{ height: 6, width: 640 * ul, background: C.red, borderRadius: 4, marginTop: 24, boxShadow: `0 0 20px ${C.red}` }} />
        <div style={{ fontFamily: inter, fontWeight: 600, fontSize: 34, color: "#c5f000", marginTop: 40, opacity: seg(f, 22, 18), letterSpacing: 0.5 }}>
          Your Brand, Our Focus
        </div>
        <div style={{ fontFamily: inter, fontWeight: 500, fontSize: 30, color: C.muted, marginTop: 26, opacity: seg(f, 34, 18) }}>
          LogoLens Analytics Team · University of Bradford
        </div>
        <div style={{ display: "flex", gap: 28, marginTop: 52, opacity: seg(f, 46, 18) }}>
          <LogoTile file={BRADFORD} label="University of Bradford" w={230} h={120} light />
          <LogoTile file={BULLS} label="Bradford Bulls RLFC" w={230} h={120} light />
        </div>
      </AbsoluteFill>
    </Bg>
  );
};
