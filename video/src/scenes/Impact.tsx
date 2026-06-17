import React from "react";
import { useCurrentFrame } from "remotion";
import { Bg } from "../components/Bg";
import { Header } from "../components/Header";
import { C, inter } from "../theme";
import { seg } from "../anim";
import { Ticks } from "../components/Sfx";

const TODAY = ["Automated sponsorship reporting", "Brand & marketing intelligence", "Business decision support"];
const FUTURE = ["Real-time match analytics", "Multi-sport deployment", "Advanced sponsor valuation", "Live dashboard integration"];

const Col: React.FC<{ tag: string; title: string; color: string; items: string[]; left: number; f: number; base: number }> = ({ tag, title, color, items, left, f, base }) => (
  <div style={{ position: "absolute", left, top: 350, width: 760 }}>
    <div style={{ fontFamily: inter, fontWeight: 700, fontSize: 20, letterSpacing: 2, textTransform: "uppercase", color, opacity: seg(f, base, 16) }}>{tag}</div>
    <div style={{ fontFamily: inter, fontWeight: 700, fontSize: 42, color: C.white, marginTop: 6, opacity: seg(f, base, 16) }}>{title}</div>
    <div style={{ display: "flex", flexDirection: "column", gap: 26, marginTop: 40 }}>
      {items.map((it, i) => (
        <div key={i} style={{ display: "flex", gap: 18, alignItems: "center", opacity: seg(f, base + 8 + i * 7, 16), transform: `translateY(${(1 - seg(f, base + 8 + i * 7, 16)) * 14}px)` }}>
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
      <Header kicker="IMPACT & FUTURE" title="Where LogoLense goes next" />
      <Ticks at={[26, 33, 40, 42, 49, 56, 63]} volume={0.34} />
      <Col tag="Now" title="Impact today" color={C.red} items={TODAY} left={120} f={f} base={18} />
      <Col tag="Roadmap" title="Future" color={C.term} items={FUTURE} left={1010} f={f} base={34} />
    </Bg>
  );
};
