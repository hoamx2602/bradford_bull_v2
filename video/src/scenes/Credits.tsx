import React from "react";
import { useCurrentFrame, AbsoluteFill } from "remotion";
import { Bg } from "../components/Bg";
import { Header } from "../components/Header";
import { C, inter } from "../theme";
import { seg } from "../anim";
import { LogoTile } from "../components/Atoms";
import { BULLS, BRADFORD } from "../assets";
import { Ticks } from "../components/Sfx";

export const Credits: React.FC = () => {
  const f = useCurrentFrame();
  return (
    <Bg>
      <Header kicker="COLLABORATION" title="Partnership" />
      <Ticks at={[24, 60]} volume={0.34} />

      <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
        <div style={{ display: "flex", alignItems: "center", gap: 56, opacity: seg(f, 36, 20), transform: `translateY(${(1 - seg(f, 36, 20)) * 18}px)` }}>
          <LogoTile file={BULLS} label="Bradford Bulls RLFC" w={300} h={180} light />
          <div style={{ fontFamily: inter, fontWeight: 700, fontSize: 44, color: C.dim }}>×</div>
          <LogoTile file={BRADFORD} label="University of Bradford" w={380} h={180} light />
        </div>
        <div style={{ fontFamily: inter, fontWeight: 600, fontSize: 30, color: C.white, marginTop: 48, opacity: seg(f, 64, 20) }}>
          Bradford Bulls Rugby League Club × University of Bradford
        </div>
      </AbsoluteFill>
    </Bg>
  );
};
