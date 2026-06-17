import React from "react";
import { Img, staticFile, useCurrentFrame, interpolate } from "remotion";
import { Bg } from "../components/Bg";
import { Header } from "../components/Header";
import { WindowChrome } from "../components/Terminal";
import { C, inter } from "../theme";
import { seg } from "../anim";
import { DASHBOARD } from "../assets";
import { PAD } from "../theme";

const KPIS = [
  { v: "17", l: "Brands tracked" },
  { v: "146s", l: "Total logo exposure" },
  { v: "37%", l: "Avg. visibility score" },
];
const BARS = [
  { n: "Aon", val: 0.82 },
  { n: "CCH", val: 0.64 },
  { n: "KLG", val: 0.57 },
  { n: "EM", val: 0.44 },
  { n: "Romantica", val: 0.33 },
  { n: "ATM", val: 0.21 },
];

const Panel: React.FC<{ x: number; y: number; w: number; h: number; title: string; f: number; start: number; children?: React.ReactNode }> = ({ x, y, w, h, title, f, start, children }) => {
  const ap = seg(f, start, 14);
  return (
    <div style={{ position: "absolute", left: x, top: y, width: w, height: h, borderRadius: 14, background: C.card, border: `1px solid ${C.cardLine}`, padding: 24, opacity: ap, transform: `translateY(${(1 - ap) * 18}px)` }}>
      <div style={{ fontFamily: inter, fontWeight: 600, fontSize: 22, color: C.muted, marginBottom: 16 }}>{title}</div>
      {children}
    </div>
  );
};

const MockDashboard: React.FC<{ f: number }> = ({ f }) => {
  const LEFT = PAD;
  const TOP = 330;
  // line chart points
  const pts = [0.2, 0.45, 0.3, 0.62, 0.5, 0.78, 0.55, 0.7, 0.85];
  const lineProg = seg(f, 60, 26);
  const shown = Math.max(2, Math.round(pts.length * lineProg));
  const cw = 760, ch = 230;
  const path = pts
    .slice(0, shown)
    .map((p, i) => `${(i / (pts.length - 1)) * cw},${ch - p * ch}`)
    .join(" ");
  return (
    <>
      {/* KPI cards */}
      <div style={{ position: "absolute", left: LEFT, top: TOP, display: "flex", gap: 24 }}>
        {KPIS.map((k, i) => {
          const ap = seg(f, 16 + i * 8, 14);
          return (
            <div key={i} style={{ width: 320, height: 150, borderRadius: 14, background: C.card, border: `1px solid ${C.cardLine}`, padding: 24, opacity: ap, transform: `translateY(${(1 - ap) * 16}px)` }}>
              <div style={{ fontFamily: inter, fontWeight: 800, fontSize: 64, color: C.red, lineHeight: 1 }}>{k.v}</div>
              <div style={{ fontFamily: inter, fontWeight: 500, fontSize: 24, color: C.muted, marginTop: 12 }}>{k.l}</div>
            </div>
          );
        })}
      </div>

      {/* bar chart */}
      <Panel x={LEFT} y={TOP + 178} w={820} h={300} title="Visibility by sponsor" f={f} start={40}>
        <div style={{ display: "flex", alignItems: "flex-end", gap: 22, height: 200, paddingTop: 8 }}>
          {BARS.map((b, i) => {
            const g = seg(f, 48 + i * 4, 16);
            return (
              <div key={i} style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 10, flex: 1 }}>
                <div style={{ width: "100%", height: 150 * b.val * g, background: `linear-gradient(180deg, ${C.red}, ${C.crimson})`, borderRadius: "6px 6px 0 0" }} />
                <div style={{ fontFamily: inter, fontSize: 18, color: C.muted }}>{b.n}</div>
              </div>
            );
          })}
        </div>
      </Panel>

      {/* line chart */}
      <Panel x={LEFT + 860} y={TOP + 178} w={820} h={300} title="Visibility over match time" f={f} start={52}>
        <svg width={cw} height={ch} style={{ overflow: "visible" }}>
          {[0.25, 0.5, 0.75].map((g) => (
            <line key={g} x1={0} y1={ch - g * ch} x2={cw} y2={ch - g * ch} stroke={C.cardLine} strokeWidth={1} />
          ))}
          <polyline points={path} fill="none" stroke={C.red} strokeWidth={4} strokeLinejoin="round" strokeLinecap="round" style={{ filter: `drop-shadow(0 0 8px ${C.red})` }} />
        </svg>
      </Panel>
    </>
  );
};

export const Dashboard: React.FC = () => {
  const f = useCurrentFrame();
  return (
    <Bg>
      <Header kicker="ANALYTICS" title="From footage to decisions" />
      {DASHBOARD ? (
        <div style={{ position: "absolute", left: PAD, top: 330, width: 1680, height: 600, borderRadius: 16, overflow: "hidden", border: `1px solid ${C.cardLine}`, boxShadow: "0 30px 70px rgba(0,0,0,0.55)", opacity: seg(f, 12, 16) }}>
          <WindowChrome title="LogoLens — analytics dashboard" />
          <Img src={staticFile(DASHBOARD)} style={{ width: "100%", height: "calc(100% - 44px)", objectFit: "cover" }} />
        </div>
      ) : (
        <MockDashboard f={f} />
      )}
    </Bg>
  );
};
