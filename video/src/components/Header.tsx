import React from "react";
import { useCurrentFrame } from "remotion";
import { C, mono, inter } from "../theme";
import { seg, rise } from "../anim";
import { PAD } from "../theme";

/** Clean section header: a small accent pill, a big Inter title, a brand
 *  underline. `step` shows a quiet "01 / 06" index in mono. */
export const Header: React.FC<{ kicker: string; title: string; step?: string }> = ({
  kicker,
  title,
  step,
}) => {
  const f = useCurrentFrame();
  const chip = seg(f, 2, 12);
  const ul = seg(f, 16, 18);
  return (
    <>
      <div
        style={{
          position: "absolute",
          left: PAD,
          top: 96,
          display: "flex",
          alignItems: "center",
          gap: 16,
          opacity: chip,
          transform: `translateY(${(1 - chip) * -10}px)`,
        }}
      >
        <div
          style={{
            padding: "9px 18px",
            borderRadius: 999,
            background: C.red,
            color: C.white,
            fontFamily: inter,
            fontWeight: 700,
            fontSize: 21,
            letterSpacing: 2,
          }}
        >
          {kicker}
        </div>
        {step ? (
          <span style={{ fontFamily: mono, fontSize: 20, color: C.dim, letterSpacing: 1 }}>{step}</span>
        ) : null}
      </div>
      <div
        style={{
          position: "absolute",
          left: PAD,
          top: 150,
          fontFamily: inter,
          fontWeight: 700,
          fontSize: 64,
          letterSpacing: -1.5,
          color: C.white,
          ...rise(f, 8, 18),
        }}
      >
        {title}
      </div>
      <div
        style={{
          position: "absolute",
          left: PAD + 2,
          top: 248,
          height: 6,
          width: 132 * ul,
          borderRadius: 3,
          background: C.red,
          boxShadow: `0 0 18px ${C.red}`,
        }}
      />
    </>
  );
};

/** A list row with a clean dot and Inter body text. */
export const Bullet: React.FC<{ text: string; active?: boolean; color?: string }> = ({
  text,
  active,
  color,
}) => {
  const dot = color ?? (active ? C.red : C.dim);
  return (
    <div style={{ display: "flex", alignItems: "center", gap: 20 }}>
      <span
        style={{
          width: active ? 16 : 12,
          height: active ? 16 : 12,
          borderRadius: "50%",
          background: dot,
          flexShrink: 0,
          boxShadow: active ? `0 0 14px ${C.red}` : "none",
        }}
      />
      <div
        style={{
          fontFamily: inter,
          fontWeight: active ? 600 : 500,
          fontSize: 36,
          color: active === false ? C.muted : C.white,
        }}
      >
        {text}
      </div>
    </div>
  );
};
