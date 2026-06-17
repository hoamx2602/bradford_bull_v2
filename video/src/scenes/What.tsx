import React from "react";
import { useCurrentFrame } from "remotion";
import { Bg } from "../components/Bg";
import { Header } from "../components/Header";
import { C, inter } from "../theme";
import { seg } from "../anim";
import { PAD } from "../theme";
import { Ticks } from "../components/Sfx";

const COLS: [string, string, string, string[]][] = [
  ["For Sponsors", "Sponsors", C.steel, ["Measure logo exposure", "Evaluate sponsorship ROI", "Compare across matches"]],
  ["For Clubs", "Clubs", C.red, ["Evidence-based pricing", "Objective visibility reports", "New commercial value"]],
  ["For Designers", "Designers", C.amber, ["See what drives visibility", "Optimise size & contrast", "Design for the pitch"]],
];

export const What: React.FC = () => {
  const f = useCurrentFrame();
  return (
    <Bg>
      <Header kicker="WHAT IS LOGOLENS" title="One platform, three audiences" />
      <Ticks at={[20, 30, 40]} name="pop" volume={0.42} />
      <div style={{ position: "absolute", left: PAD + 20, top: 340, display: "flex", gap: 40 }}>
        {COLS.map(([key, name, col, bs], i) => {
          const ap = seg(f, 20 + i * 10, 18);
          return (
            <div
              key={i}
              style={{
                width: 520,
                height: 560,
                borderRadius: 18,
                background: C.card,
                border: `1px solid ${C.cardLine}`,
                overflow: "hidden",
                opacity: ap,
                transform: `translateY(${(1 - ap) * 30}px)`,
                boxShadow: "0 24px 60px rgba(0,0,0,0.45)",
              }}
            >
              <div style={{ padding: "26px 32px 20px", borderBottom: `1px solid ${C.cardLine}` }}>
                <div style={{ fontFamily: inter, fontWeight: 700, fontSize: 20, letterSpacing: 2, textTransform: "uppercase", color: col }}>{key}</div>
                <div style={{ fontFamily: inter, fontWeight: 700, fontSize: 42, color: C.white, marginTop: 6 }}>{name}</div>
              </div>
              <div style={{ padding: "38px 36px", display: "flex", flexDirection: "column", gap: 34 }}>
                {bs.map((b, j) => (
                  <div key={j} style={{ display: "flex", alignItems: "center", gap: 18, opacity: seg(f, 34 + i * 8 + j * 5, 16) }}>
                    <span style={{ width: 13, height: 13, borderRadius: "50%", background: col, flexShrink: 0 }} />
                    <div style={{ fontFamily: inter, fontWeight: 500, fontSize: 31, color: C.white }}>{b}</div>
                  </div>
                ))}
              </div>
            </div>
          );
        })}
      </div>
    </Bg>
  );
};
