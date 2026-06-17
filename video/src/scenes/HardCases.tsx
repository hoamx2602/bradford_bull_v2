import React from "react";
import { Img, staticFile, useCurrentFrame, interpolate } from "remotion";
import { Bg } from "../components/Bg";
import { Header } from "../components/Header";
import { C, inter } from "../theme";
import { seg } from "../anim";
import { HARDCASES } from "../assets";
import { PAD } from "../theme";

// where the "hard" logo sits in each frame (% of the tile) — just a marker
const MARK = [
  { x: 62, y: 40 },
  { x: 44, y: 30 },
  { x: 70, y: 58 },
  { x: 30, y: 44 },
];

export const HardCases: React.FC = () => {
  const f = useCurrentFrame();
  const pulse = 1 + 0.12 * Math.sin(f / 6);
  const COL_W = 800;
  const ROW_H = 300;
  return (
    <Bg>
      <Header kicker="FINDINGS" title="Logos the eye would miss" />
      <div style={{ position: "absolute", left: PAD, top: 360, display: "grid", gridTemplateColumns: `${COL_W}px ${COL_W}px`, gap: "30px 40px" }}>
        {HARDCASES.map((h, i) => {
          const ap = seg(f, 16 + i * 8, 16);
          const m = MARK[i];
          return (
            <div key={i} style={{ opacity: ap, transform: `translateY(${(1 - ap) * 22}px)` }}>
              <div style={{ position: "relative", width: COL_W, height: ROW_H, borderRadius: 14, overflow: "hidden", border: `1px solid ${C.cardLine}`, boxShadow: "0 18px 44px rgba(0,0,0,0.45)" }}>
                <Img src={staticFile(h.src)} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
                {/* marker ring on the hard-to-see logo */}
                <div
                  style={{
                    position: "absolute",
                    left: `${m.x}%`,
                    top: `${m.y}%`,
                    width: 92,
                    height: 92,
                    marginLeft: -46,
                    marginTop: -46,
                    borderRadius: "50%",
                    border: `3px solid ${C.red}`,
                    boxShadow: `0 0 22px ${C.red}`,
                    transform: `scale(${pulse})`,
                    opacity: interpolate(ap, [0.4, 1], [0, 1], { extrapolateLeft: "clamp" }),
                  }}
                />
                {/* tag chip */}
                <div style={{ position: "absolute", left: 16, bottom: 16, padding: "7px 14px", borderRadius: 8, background: "rgba(5,6,10,0.78)", fontFamily: inter, fontWeight: 600, fontSize: 22, color: C.white }}>
                  {h.tag}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </Bg>
  );
};
