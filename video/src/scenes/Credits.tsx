import React from "react";
import { useCurrentFrame } from "remotion";
import { Bg } from "../components/Bg";
import { Header } from "../components/Header";
import { C, inter } from "../theme";
import { seg } from "../anim";
import { Avatar, LogoTile } from "../components/Atoms";
import { BULLS, BRADFORD, IAN } from "../assets";
import { PAD } from "../theme";
import { Sfx, Ticks } from "../components/Sfx";

const label = (txt: string) => (
  <span style={{ letterSpacing: 2, textTransform: "uppercase" as const }}>{txt}</span>
);

export const Credits: React.FC = () => {
  const f = useCurrentFrame();
  const row = (txt: React.ReactNode, size: number, color: string, weight: number, start: number) => (
    <div style={{ fontFamily: inter, fontWeight: weight, fontSize: size, color, opacity: seg(f, start, 16), transform: `translateY(${(1 - seg(f, start, 16)) * 14}px)` }}>{txt}</div>
  );
  return (
    <Bg>
      <Header kicker="SUPERVISION" title="Guidance & Partnership" />
      <Ticks at={[18, 24, 28, 34, 40, 32, 38]} volume={0.34} />
      <Sfx name="pop" from={50} volume={0.4} />
      <Sfx name="pop" from={58} volume={0.4} />

      {/* left column — academic supervision */}
      <div style={{ position: "absolute", left: PAD, top: 360, display: "flex", flexDirection: "column", gap: 14 }}>
        {row(label("Supervisors"), 24, C.red, 700, 18)}
        {row("Irfan Mehmood", 38, C.white, 500, 24)}
        {row("Tillal Eldabi", 38, C.white, 500, 28)}
        <div style={{ height: 34 }} />
        {row(label("Advisor"), 24, C.red, 700, 34)}
        {row("Takao Maruyama", 38, C.white, 500, 40)}
      </div>

      {/* right column — industry collaborator */}
      <div style={{ position: "absolute", left: 980, top: 360, width: 820 }}>
        {row(label("Industry Collaborator"), 24, C.red, 700, 32)}
        <div style={{ marginTop: 16 }}>{row("Bradford Bulls Rugby League Club", 38, C.white, 600, 38)}</div>
        <div style={{ display: "flex", alignItems: "center", gap: 28, marginTop: 36, opacity: seg(f, 46, 18) }}>
          <Avatar name="Ian Stafford" file={IAN} size={150} radius={16} />
          <div>
            <div style={{ fontFamily: inter, fontWeight: 600, fontSize: 32, color: C.white }}>Ian Stafford</div>
            <div style={{ fontFamily: inter, fontSize: 22, color: C.muted, marginTop: 6 }}>Club contact &amp; partner</div>
          </div>
        </div>
        <div style={{ display: "flex", gap: 24, marginTop: 40, opacity: seg(f, 58, 18) }}>
          <LogoTile file={BULLS} label="Bradford Bulls RLFC" w={250} h={150} light />
          <LogoTile file={BRADFORD} label="University of Bradford" w={330} h={150} light />
        </div>
      </div>
    </Bg>
  );
};
