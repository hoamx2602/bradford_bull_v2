import React from "react";
import { Img, staticFile, useCurrentFrame } from "remotion";
import { Bg } from "../components/Bg";
import { Header } from "../components/Header";
import { C, inter } from "../theme";
import { seg } from "../anim";
import { Ticks } from "../components/Sfx";
import { POSTER } from "../assets";

const TODAY = ["Automated sponsorship reporting", "Brand & marketing intelligence", "Business decision support"];
const FUTURE = ["Real-time match analytics", "Multi-sport deployment", "Advanced sponsor valuation", "Live dashboard integration"];

const ITEM_GAP = 24; // frames between each bullet within a column — slow enough to read

const Col: React.FC<{ tag: string; title: string; color: string; items: string[]; left: number; f: number; base: number }> = ({ tag, title, color, items, left, f, base }) => (
  <div style={{ position: "absolute", left, top: 350, width: 760 }}>
    <div style={{ fontFamily: inter, fontWeight: 700, fontSize: 20, letterSpacing: 2, textTransform: "uppercase", color, opacity: seg(f, base, 16) }}>{tag}</div>
    <div style={{ fontFamily: inter, fontWeight: 700, fontSize: 42, color: C.white, marginTop: 6, opacity: seg(f, base, 16) }}>{title}</div>
    <div style={{ display: "flex", flexDirection: "column", gap: 26, marginTop: 40 }}>
      {items.map((it, i) => (
        <div key={i} style={{ display: "flex", gap: 18, alignItems: "center", opacity: seg(f, base + 16 + i * ITEM_GAP, 16), transform: `translateY(${(1 - seg(f, base + 16 + i * ITEM_GAP, 16)) * 14}px)` }}>
          <span style={{ width: 13, height: 13, borderRadius: "50%", background: color, flexShrink: 0 }} />
          <div style={{ fontFamily: inter, fontWeight: 400, fontSize: 34, color: C.white }}>{it}</div>
        </div>
      ))}
    </div>
  </div>
);

export const Impact: React.FC = () => {
  const f = useCurrentFrame();
  return (
    <Bg>
      {/* poster artwork as a dim, blurred backdrop */}
      <Img
        src={staticFile(POSTER)}
        style={{ position: "absolute", left: "50%", top: "50%", width: "85%", transform: "translate(-50%, -50%)", opacity: 0.16, filter: "blur(6px)" }}
      />
      <Header kicker="IMPACT & FUTURE" title="Where LogoLense goes next" />
      <Ticks at={[30, 46, 54, 70, 78, 94, 102]} volume={0.34} />
      <Col tag="Now" title="Impact today" color={C.red} items={TODAY} left={120} f={f} base={30} />
      <Col tag="Roadmap" title="Future" color={C.term} items={FUTURE} left={1010} f={f} base={46} />
    </Bg>
  );
};
