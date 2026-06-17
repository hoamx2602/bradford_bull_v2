import React from "react";
import { useCurrentFrame, interpolate, Img, staticFile } from "remotion";
import { Bg } from "../components/Bg";
import { Header } from "../components/Header";
import { C, mono, inter } from "../theme";
import { seg } from "../anim";
import { SPONSORS } from "../assets";
import { PAD } from "../theme";
import { Sfx, Ticks } from "../components/Sfx";

const POINTS = [
  "Per-logo visibility scored live (size × position × clarity).",
  "Same sponsor swings from fully visible to occluded in seconds.",
  "Camera angle & player position drive most of the variance.",
];

export const Results: React.FC = () => {
  const f = useCurrentFrame();
  const target = Math.max(SPONSORS.length, 9);
  const val = Math.round(interpolate(f, [12, 46], [0, target], { extrapolateLeft: "clamp", extrapolateRight: "clamp" }));
  return (
    <Bg>
      <Header kicker="RESULTS" title="Visibility is never constant" />
      <Sfx name="pop" from={12} volume={0.4} />
      <Ticks at={[40, 52, 64]} volume={0.38} />

      <div style={{ position: "absolute", left: PAD, top: 350, opacity: seg(f, 12, 16) }}>
        <div style={{ fontFamily: mono, fontWeight: 700, fontSize: 210, lineHeight: 1, color: C.red, textShadow: `0 0 50px rgba(255,59,48,0.4)` }}>
          {String(val).padStart(2, "0")}
        </div>
        <div style={{ fontFamily: inter, fontWeight: 600, fontSize: 40, color: C.white, marginTop: 6 }}>sponsor brands detected</div>
        <div style={{ fontFamily: inter, fontWeight: 400, fontSize: 26, color: C.muted, marginTop: 8 }}>in a single 14-second clip</div>

        {/* live-lighting sponsor logo strip (real marks) */}
        <div style={{ display: "flex", flexWrap: "wrap", gap: 14, marginTop: 40, width: 760 }}>
          {SPONSORS.map((s, i) => {
            const on = i < val;
            return (
              <div
                key={s}
                style={{
                  width: 168,
                  height: 78,
                  borderRadius: 10,
                  background: C.card,
                  border: `1px solid ${on ? C.red : C.dim}`,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  padding: 12,
                  opacity: on ? 1 : 0.28,
                  transition: "none",
                }}
              >
                <Img src={staticFile(s)} style={{ maxWidth: "100%", maxHeight: "100%", objectFit: "contain" }} />
              </div>
            );
          })}
        </div>
      </div>

      <div style={{ position: "absolute", left: 1020, top: 420, display: "flex", flexDirection: "column", gap: 42 }}>
        {POINTS.map((p, i) => (
          <div key={i} style={{ display: "flex", gap: 20, alignItems: "flex-start", opacity: seg(f, 40 + i * 12, 16), transform: `translateY(${(1 - seg(f, 40 + i * 12, 16)) * 16}px)`, maxWidth: 760 }}>
            <span style={{ width: 15, height: 15, borderRadius: "50%", background: C.red, marginTop: 12, flexShrink: 0 }} />
            <div style={{ fontFamily: inter, fontWeight: 400, fontSize: 33, color: C.white, lineHeight: 1.35 }}>{p}</div>
          </div>
        ))}
      </div>
    </Bg>
  );
};
