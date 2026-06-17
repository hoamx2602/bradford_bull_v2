import React from "react";
import { useCurrentFrame, useVideoConfig, spring, AbsoluteFill, Img, staticFile, interpolate } from "remotion";
import { Bg } from "../components/Bg";
import { C, mono, inter } from "../theme";
import { seg } from "../anim";
import { TEAM_GROUPS, TeamMember } from "../assets";
import { Ticks } from "../components/Sfx";

const INTRO = 24; // group photo + label fade-in
const PER = 38; // frames spent spotlighting each member
const GAP = 22; // crossfade between the two group photos

const PHOTO = { left: 150, top: 268, width: 760, height: Math.round((760 * 1122) / 1402) };
const MASK_COLOR = "rgba(5,6,10,0.82)";

const lerp = (a: number, b: number, t: number) => a + (b - a) * t;
const lerpBox = (a: TeamMember, b: TeamMember, t: number) => ({
  x: lerp(a.x, b.x, t),
  y: lerp(a.y, b.y, t),
  w: lerp(a.w, b.w, t),
  h: lerp(a.h, b.h, t),
});

// Flatten both groups into one timeline: each group gets an intro, then one
// beat per member; groups crossfade into each other.
const buildSchedule = () => {
  let cursor = 0;
  return TEAM_GROUPS.map((group) => {
    const start = cursor;
    const introEnd = start + INTRO;
    const end = introEnd + group.members.length * PER;
    cursor = end + GAP;
    return { group, start, introEnd, end };
  });
};
const SCHEDULE = buildSchedule();
const TOTAL = SCHEDULE[SCHEDULE.length - 1].end;
const SFX_AT = SCHEDULE.flatMap((s) => s.group.members.map((_, i) => s.introEnd + i * PER));

export const Team: React.FC = () => {
  const f = useCurrentFrame();
  const { fps } = useVideoConfig();

  return (
    <Bg>
      <Ticks at={SFX_AT} name="pop" volume={0.4} />
      <AbsoluteFill>
        <div style={{ position: "absolute", left: 0, top: 0, width: "100%", textAlign: "center" }}>
          <div style={{ fontFamily: inter, fontWeight: 700, fontSize: 22, letterSpacing: 3, color: C.red, marginTop: 70, opacity: seg(f, 2, 12) }}>
            THE TEAM
          </div>
          <div
            style={{
              fontFamily: inter,
              fontWeight: 700,
              fontSize: 60,
              letterSpacing: -1.5,
              color: C.white,
              marginTop: 10,
              opacity: seg(f, 12, 14),
              transform: `translateY(${(1 - seg(f, 12, 14)) * 18}px)`,
            }}
          >
            LogoLens Analytics Team
          </div>
          <div style={{ height: 5, width: 360 * seg(f, 22, 16), background: C.red, borderRadius: 3, margin: "12px auto 0" }} />
        </div>

        {SCHEDULE.map((s, gi) => {
          const photoOpacity =
            gi === 0
              ? interpolate(f, [s.end, s.end + GAP], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })
              : interpolate(f, [s.start - GAP, s.start], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
          if (photoOpacity <= 0) return null;

          const localFrame = Math.max(0, f - s.introEnd);
          const memberIdx = Math.min(s.group.members.length - 1, Math.floor(localFrame / PER));
          const prevIdx = Math.max(0, memberIdx - 1);
          const t = localFrame - memberIdx * PER;
          const moveT = spring({ frame: t, fps, config: { damping: 200 } });

          const box = lerpBox(s.group.members[prevIdx], s.group.members[memberIdx], moveT);
          const maskOpacity = seg(f - s.start, INTRO - 10, 12) * photoOpacity;

          // hole rect (the active member) in screen px, masked out of the dim overlay
          const hx = PHOTO.left + (box.x / 100) * PHOTO.width;
          const hy = PHOTO.top + (box.y / 100) * PHOTO.height;
          const hw = (box.w / 100) * PHOTO.width;
          const hh = (box.h / 100) * PHOTO.height;

          // accumulating reveal list, to the right of the photo
          const rowH = 86;
          const rowGap = 12;
          const listTotal = s.group.members.length * rowH + (s.group.members.length - 1) * rowGap;
          const listTop = PHOTO.top + Math.max(0, (PHOTO.height - listTotal) / 2);
          const listLeft = PHOTO.left + PHOTO.width + 64;

          return (
            <div key={s.group.label} style={{ opacity: photoOpacity }}>
              <div style={{ position: "absolute", left: PHOTO.left, top: PHOTO.top - 56, fontFamily: mono, fontWeight: 700, fontSize: 22, letterSpacing: 2, color: C.steel, opacity: seg(f, s.start, INTRO) }}>
                {s.group.label}
              </div>

              {/* base photo, full brightness */}
              <div
                style={{
                  position: "absolute",
                  left: PHOTO.left,
                  top: PHOTO.top,
                  width: PHOTO.width,
                  height: PHOTO.height,
                  borderRadius: 18,
                  overflow: "hidden",
                  border: `1px solid ${C.cardLine}`,
                  boxShadow: "0 30px 70px rgba(0,0,0,0.55)",
                  opacity: seg(f, s.start, INTRO),
                }}
              >
                <Img src={staticFile(s.group.photo)} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
              </div>

              {/* dim overlay with a rectangular hole cut around the active member */}
              <div style={{ position: "absolute", left: PHOTO.left, top: PHOTO.top, width: PHOTO.width, height: hy - PHOTO.top, background: MASK_COLOR, opacity: maskOpacity }} />
              <div style={{ position: "absolute", left: PHOTO.left, top: hy + hh, width: PHOTO.width, height: PHOTO.top + PHOTO.height - (hy + hh), background: MASK_COLOR, opacity: maskOpacity }} />
              <div style={{ position: "absolute", left: PHOTO.left, top: hy, width: hx - PHOTO.left, height: hh, background: MASK_COLOR, opacity: maskOpacity }} />
              <div style={{ position: "absolute", left: hx + hw, top: hy, width: PHOTO.left + PHOTO.width - (hx + hw), height: hh, background: MASK_COLOR, opacity: maskOpacity }} />
              <div
                style={{
                  position: "absolute",
                  left: hx,
                  top: hy,
                  width: hw,
                  height: hh,
                  border: `3px solid ${C.red}`,
                  borderRadius: 10,
                  boxShadow: `0 0 30px rgba(255,59,48,0.5)`,
                  opacity: maskOpacity,
                }}
              />

              {/* accumulating list — each member appends below the previous, active one highlighted */}
              <div style={{ position: "absolute", left: listLeft, top: listTop, display: "flex", flexDirection: "column", gap: rowGap }}>
                {s.group.members.map((m, idx) => {
                  const revealAt = s.start + INTRO + idx * PER;
                  const itemOpacity = seg(f, revealAt + 4, 12) * photoOpacity;
                  const active = idx === memberIdx;
                  return (
                    <div
                      key={m.name}
                      style={{
                        height: rowH,
                        width: 560,
                        display: "flex",
                        alignItems: "center",
                        gap: 18,
                        padding: "0 22px",
                        borderRadius: 12,
                        background: active ? C.card : "transparent",
                        border: `1px solid ${active ? C.cardLine : "transparent"}`,
                        opacity: itemOpacity,
                        transform: `translateX(${(1 - itemOpacity) * 24}px)`,
                      }}
                    >
                      <span style={{ width: 10, height: 10, borderRadius: "50%", background: active ? C.red : C.dim, boxShadow: active ? `0 0 14px ${C.red}` : "none", flexShrink: 0 }} />
                      <div>
                        <div style={{ fontFamily: inter, fontWeight: 700, fontSize: 26, color: active ? C.white : C.steel }}>{m.name}</div>
                        <div style={{ fontFamily: inter, fontWeight: 500, fontSize: 17, color: active ? C.red : C.dim, marginTop: 2 }}>{m.role}</div>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          );
        })}

        <div style={{ position: "absolute", left: 0, bottom: 40, width: "100%", textAlign: "center", fontFamily: inter, fontWeight: 500, fontSize: 26, color: C.muted, opacity: seg(f, 30, 18) }}>
          MSc Applied Artificial Intelligence &amp; Data Analytics — University of Bradford
        </div>
      </AbsoluteFill>
    </Bg>
  );
};

export const TEAM_SCENE_FRAMES = TOTAL;
