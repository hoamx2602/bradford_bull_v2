import React from "react";
import { useCurrentFrame } from "remotion";
import { Bg } from "../components/Bg";
import { Header } from "../components/Header";
import { C, inter, mono } from "../theme";
import { seg } from "../anim";
import { Ticks } from "../components/Sfx";

const STEPS: { t: string; d: string; tech?: string; c: string }[] = [
  { t: "Match video", d: "Rugby match footage is collected", c: C.steel },
  { t: "Frame extraction", d: "Video is split into image frames", c: C.steel },
  { t: "Player detection", d: "Players are found in every frame", tech: "YOLO11-pose", c: C.amber },
  { t: "Multi-object tracking", d: "Each player is tracked across the clip", tech: "ByteTrack", c: C.amber },
  { t: "Logo detection", d: "Sponsor logos located on shirts & boards", tech: "YOLO26m · RF-DETR", c: C.red },
  { t: "Visibility scoring", d: "Size × position × clarity, scored per logo", c: C.red },
  { t: "Analytics dashboard", d: "Exposure, EMV & reports generated", tech: "SigLIP team filter", c: C.term },
];

const TOP = 322; // y of first node centre
const ROW = 96; // vertical gap between steps
const X = 470; // x of the vertical rail
const NODE = 20;

export const Pipeline: React.FC = () => {
  const f = useCurrentFrame();
  const span = (STEPS.length - 1) * ROW;
  // rail draws downward
  const prog = seg(f, 12, STEPS.length * 9);
  const drawn = prog * span;

  return (
    <Bg>
      <Header kicker="OUR AI SOLUTION" title="The processing pipeline" />
      <Ticks at={STEPS.map((_, i) => 14 + i * 9)} volume={0.38} />

      {/* dim base rail */}
      <div style={{ position: "absolute", left: X - 1.5, top: TOP, width: 3, height: span, background: C.dim, borderRadius: 2, opacity: 0.45 }} />
      {/* bright drawn rail */}
      <div style={{ position: "absolute", left: X - 2, top: TOP, width: 4, height: drawn, background: C.red, borderRadius: 2, boxShadow: `0 0 16px ${C.red}` }} />

      {STEPS.map((s, i) => {
        const y = TOP + i * ROW; // node centre
        const ap = seg(f, 14 + i * 9, 14);
        const reached = drawn >= i * ROW - 6;
        return (
          <React.Fragment key={i}>
            {/* index */}
            <div
              style={{
                position: "absolute",
                left: X - 170,
                top: y - 22,
                width: 96,
                textAlign: "right",
                fontFamily: mono,
                fontWeight: 700,
                fontSize: 34,
                color: reached ? s.c : C.dim,
                opacity: ap,
              }}
            >
              {String(i + 1).padStart(2, "0")}
            </div>
            {/* node */}
            <div
              style={{
                position: "absolute",
                left: X - NODE / 2,
                top: y - NODE / 2,
                width: NODE,
                height: NODE,
                borderRadius: "50%",
                background: reached ? s.c : C.bg0,
                border: `3px solid ${reached ? s.c : C.dim}`,
                boxShadow: reached ? `0 0 18px ${s.c}` : "none",
                opacity: ap,
              }}
            />
            {/* content */}
            <div
              style={{
                position: "absolute",
                left: X + 56,
                top: y - 38,
                opacity: ap,
                transform: `translateX(${(1 - ap) * 22}px)`,
              }}
            >
              <div style={{ display: "flex", alignItems: "baseline", gap: 18 }}>
                <span style={{ fontFamily: inter, fontWeight: 700, fontSize: 40, color: C.white }}>{s.t}</span>
                {s.tech ? (
                  <span
                    style={{
                      fontFamily: inter,
                      fontWeight: 600,
                      fontSize: 19,
                      letterSpacing: 0.5,
                      color: s.c,
                      border: `1px solid ${s.c}`,
                      borderRadius: 999,
                      padding: "3px 12px",
                      opacity: 0.9,
                    }}
                  >
                    {s.tech}
                  </span>
                ) : null}
              </div>
              <div style={{ fontFamily: inter, fontWeight: 400, fontSize: 27, color: C.muted, marginTop: 6 }}>{s.d}</div>
            </div>
          </React.Fragment>
        );
      })}
    </Bg>
  );
};
