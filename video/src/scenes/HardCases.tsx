import React from "react";
import { Img, staticFile, useCurrentFrame } from "remotion";
import { Bg } from "../components/Bg";
import { Header } from "../components/Header";
import { C, inter } from "../theme";
import { seg } from "../anim";
import { HARDCASES } from "../assets";
import { PAD } from "../theme";

const SRC_W = 1920;
const SRC_H = 1080;
const ZOOM = 2.3; // how far in we punch on the focal point

// Sized + positioned so the image is zoomed into (cx%, cy%) of the source,
// clamped so we never reveal space beyond the source's edges.
const zoomStyle = (cx: number, cy: number, colW: number, rowH: number) => {
  const fullW = colW * ZOOM;
  const fullH = fullW * (SRC_H / SRC_W);
  const rawLeft = colW / 2 - (cx / 100) * fullW;
  const rawTop = rowH / 2 - (cy / 100) * fullH;
  const left = Math.min(0, Math.max(colW - fullW, rawLeft));
  const top = Math.min(0, Math.max(rowH - fullH, rawTop));
  return { width: fullW, height: fullH, left, top };
};

export const HardCases: React.FC = () => {
  const f = useCurrentFrame();
  const COL_W = 800;
  const ROW_H = 300;
  return (
    <Bg>
      <Header kicker="FINDINGS" title="Logo detection examples" />
      <div style={{ position: "absolute", left: PAD, top: 360, display: "grid", gridTemplateColumns: `${COL_W}px ${COL_W}px`, gap: "30px 40px" }}>
        {HARDCASES.map((h, i) => {
          const start = 40 + i * 70; // ~1.3s rest, then one card every ~2.3s
          const ap = seg(f, start, 18);
          const z = zoomStyle(h.cx, h.cy, COL_W, ROW_H);
          return (
            <div key={i} style={{ opacity: ap, transform: `translateY(${(1 - ap) * 22}px)` }}>
              <div style={{ position: "relative", width: COL_W, height: ROW_H, borderRadius: 14, overflow: "hidden", border: `1px solid ${C.cardLine}`, boxShadow: "0 18px 44px rgba(0,0,0,0.45)" }}>
                <Img src={staticFile(h.src)} style={{ position: "absolute", ...z, maxWidth: "none" }} />
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
