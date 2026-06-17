import React from "react";
import { Img, staticFile, useCurrentFrame } from "remotion";
import { Bg } from "../components/Bg";
import { Header, Bullet } from "../components/Header";
import { C, inter } from "../theme";
import { seg } from "../anim";
import { WindowChrome } from "../components/Terminal";
import { PAD } from "../theme";
import { Ticks } from "../components/Sfx";

const ITEMS = [
  "Brands invest millions in sponsorship.",
  "Visibility is still measured by hand.",
  "Exposure shifts with player & camera movement.",
  "Sponsors need objective, data-driven proof.",
];
const CAPS = ["Jersey & board sponsorship", "Reviewed manually", "Movement & camera angles", "Automated, data-driven"];
// ~1.3s rest after the title settles before the first bullet, then ~3s
// between each so there's plenty of time to read before the next lands.
const STARTS = [40, 130, 220, 310];

export const Motivation: React.FC = () => {
  const f = useCurrentFrame();
  let active = 0;
  STARTS.forEach((s, i) => {
    if (f >= s) active = i;
  });
  return (
    <Bg>
      <Header kicker="MOTIVATION" title="A multi-billion-pound question" />
      <Ticks at={STARTS} volume={0.4} />

      <div style={{ position: "absolute", left: PAD, top: 400, display: "flex", flexDirection: "column", gap: 42, width: 820 }}>
        {ITEMS.map((it, i) => (
          <div key={i} style={{ opacity: seg(f, STARTS[i] - 8, 16), transform: `translateY(${(1 - seg(f, STARTS[i] - 8, 16)) * 20}px)` }}>
            <Bullet text={it} active={i === active} />
          </div>
        ))}
      </div>

      {/* windowed image panel */}
      <div
        style={{
          position: "absolute",
          left: 1050,
          top: 340,
          width: 760,
          height: 500,
          borderRadius: 16,
          overflow: "hidden",
          border: `1px solid ${C.cardLine}`,
          boxShadow: "0 30px 70px rgba(0,0,0,0.55)",
          opacity: seg(f, 40, 16),
        }}
      >
        <WindowChrome title="Match footage · sponsorship review" />
        <div style={{ position: "relative", width: "100%", height: "calc(100% - 44px)" }}>
          {[0, 1, 2, 3].map((i) => (
            <Img
              key={i}
              src={staticFile(`img/motiv_${i + 1}.png`)}
              style={{ position: "absolute", inset: 0, width: "100%", height: "100%", objectFit: "cover", opacity: i === 0 ? 1 : seg(f, STARTS[i], 12) }}
            />
          ))}
          <div style={{ position: "absolute", left: 0, bottom: 0, width: "100%", padding: "12px 22px", background: "rgba(5,6,10,0.7)", fontFamily: inter, fontWeight: 600, fontSize: 24, color: C.white }}>
            {CAPS[active]}
          </div>
        </div>
      </div>

      {/* thumbnail strip */}
      <div style={{ position: "absolute", left: 1050, top: 870, display: "flex", gap: 18 }}>
        {CAPS.map((c, i) => (
          <div key={i} style={{ display: "flex", flexDirection: "column", alignItems: "center", gap: 8, opacity: seg(f, 40, 16) }}>
            <div style={{ width: 174, height: 96, borderRadius: 8, overflow: "hidden", border: `${i === active ? 2 : 1}px solid ${i === active ? C.red : C.dim}` }}>
              <Img src={staticFile(`img/motiv_${i + 1}.png`)} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
            </div>
            <div style={{ fontFamily: inter, fontWeight: 500, fontSize: 16, color: i === active ? C.red : C.muted }}>{`${i + 1} · ${c}`}</div>
          </div>
        ))}
      </div>
    </Bg>
  );
};
