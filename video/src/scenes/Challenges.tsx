import React from "react";
import { useCurrentFrame } from "remotion";
import { Bg } from "../components/Bg";
import { Header } from "../components/Header";
import { C, inter } from "../theme";
import { seg } from "../anim";
import { PAD } from "../theme";
import { Ticks } from "../components/Sfx";

const ITEMS = [
  "Overlapping players & occlusion",
  "Motion blur in fast action",
  "Varying camera angles",
  "Scale changes near / far",
  "Lighting & weather",
  "Small / partial logos",
];

export const Challenges: React.FC = () => {
  const f = useCurrentFrame();
  return (
    <Bg>
      <Header kicker="REAL-WORLD CHALLENGES" title="Built for messy match footage" />
      <Ticks at={ITEMS.map((_, i) => 40 + i * 90)} volume={0.36} />
      <div style={{ position: "absolute", left: PAD, top: 380, display: "grid", gridTemplateColumns: "780px 780px", gap: "26px 56px" }}>
        {ITEMS.map((it, i) => {
          const ap = seg(f, 40 + i * 90, 16);
          return (
            <div
              key={i}
              style={{
                width: 780,
                height: 104,
                borderRadius: 14,
                background: C.card,
                border: `1px solid ${C.cardLine}`,
                display: "flex",
                alignItems: "center",
                gap: 22,
                paddingLeft: 26,
                opacity: ap,
                transform: `translateX(${(1 - ap) * 24}px)`,
              }}
            >
              <span
                style={{
                  width: 44,
                  height: 44,
                  borderRadius: "50%",
                  background: "rgba(255,59,48,0.12)",
                  border: `1px solid rgba(255,59,48,0.5)`,
                  color: C.red,
                  fontFamily: inter,
                  fontWeight: 700,
                  fontSize: 22,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  flexShrink: 0,
                }}
              >
                {i + 1}
              </span>
              <div style={{ fontFamily: inter, fontWeight: 600, fontSize: 34, color: C.white }}>{it}</div>
            </div>
          );
        })}
      </div>
    </Bg>
  );
};
