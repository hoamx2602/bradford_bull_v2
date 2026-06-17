import React from "react";
import { useCurrentFrame, AbsoluteFill, Img, staticFile, interpolate } from "remotion";
import { Bg } from "../components/Bg";
import { C, inter } from "../theme";
import { seg } from "../anim";
import { TEAM_GROUPS, Pt } from "../assets";
import { Ticks } from "../components/Sfx";

const FADE_IN = 24; // group photo + title fade-in
const HOLD = 90; // ~3s plain view of the full photo before highlighting starts
const PER = 56; // frames spent spotlighting each member — slow enough to read
const TAIL = 60; // ~2s plain view after the last highlight (overlay removed)
const GAP = 26; // crossfade between the two group photos

// Centered horizontally: photo(760) + gap(64) + list(560) = 1384 wide on a
// 1920 stage → left margin (1920-1384)/2 = 268. The list tracks PHOTO.left.
const PHOTO = { left: 268, top: 268, width: 760, height: Math.round((760 * 1122) / 1402) };
const MASK_COLOR = "rgba(5,6,10,0.82)";

// "x,y x,y ..." for an SVG <polygon> (points are already in 0–100 viewBox units).
const polyPoints = (pts: Pt[]) => pts.map(([x, y]) => `${x},${y}`).join(" ");
// A dim-everything path with the person's outline punched out (even-odd rule).
const holePath = (pts: Pt[]) =>
  "M0 0H100V100H0Z" + (pts.length ? "M" + pts.map(([x, y]) => `${x} ${y}`).join("L") + "Z" : "");

// Flatten both groups into one timeline: each group gets an intro, then one
// beat per member; groups crossfade into each other.
const buildSchedule = () => {
  let cursor = 0;
  return TEAM_GROUPS.map((group) => {
    const start = cursor;
    const introEnd = start + HOLD;
    const end = introEnd + group.members.length * PER + TAIL;
    cursor = end + GAP;
    return { group, start, introEnd, end };
  });
};
const SCHEDULE = buildSchedule();
const TOTAL = SCHEDULE[SCHEDULE.length - 1].end;
const SFX_AT = SCHEDULE.flatMap((s) => s.group.members.map((_, i) => s.introEnd + i * PER));

export const Team: React.FC = () => {
  const f = useCurrentFrame();

  return (
    <Bg>
      <Ticks at={SFX_AT} name="pop" volume={0.4} />
      <AbsoluteFill>
        <div style={{ position: "absolute", left: 0, top: 0, width: "100%", textAlign: "center" }}>
          <div style={{ fontFamily: inter, fontWeight: 700, fontSize: 22, letterSpacing: 3, color: C.red, marginTop: 70, opacity: seg(f, 2, 12) }}>
            THE TEAM
          </div>
        </div>

        {SCHEDULE.map((s, gi) => {
          const photoOpacity =
            gi === 0
              ? interpolate(f, [s.end, s.end + GAP], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" })
              : interpolate(f, [s.start - GAP, s.start], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
          if (photoOpacity <= 0) return null;

          const localFrame = Math.max(0, f - s.introEnd);
          const memberIdx = Math.min(s.group.members.length - 1, Math.floor(localFrame / PER));
          // overlay fades in before the first highlight and fades back out after
          // the last one, leaving ~2s (TAIL) of plain photo before the cut.
          const highlightsEnd = HOLD + s.group.members.length * PER;
          const maskOpacity =
            seg(f - s.start, HOLD - 14, 16) *
            (1 - seg(f - s.start, highlightsEnd, 14)) *
            photoOpacity;
          const pts = s.group.members[memberIdx].points;

          // accumulating reveal list, to the right of the photo
          const rowH = 86;
          const rowGap = 12;
          const listTotal = s.group.members.length * rowH + (s.group.members.length - 1) * rowGap;
          const listTop = PHOTO.top + Math.max(0, (PHOTO.height - listTotal) / 2);
          const listLeft = PHOTO.left + PHOTO.width + 64;

          const titleIn = seg(f, s.start, FADE_IN);
          return (
            <div key={s.group.title} style={{ opacity: photoOpacity }}>
              <div
                style={{
                  position: "absolute",
                  left: 0,
                  top: 116,
                  width: "100%",
                  textAlign: "center",
                  fontFamily: inter,
                  fontWeight: 700,
                  fontSize: 60,
                  letterSpacing: -1.5,
                  color: C.white,
                  opacity: titleIn,
                  transform: `translateY(${(1 - titleIn) * 18}px)`,
                }}
              >
                <span style={{ position: "relative", display: "inline-block" }}>
                  {s.group.title}
                  <span
                    style={{
                      position: "absolute",
                      left: 0,
                      bottom: -22,
                      height: 5,
                      width: "100%",
                      borderRadius: 3,
                      background: C.red,
                      transform: `scaleX(${seg(f, s.start + 10, 16)})`,
                      transformOrigin: "left",
                    }}
                  />
                </span>
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
                  opacity: seg(f, s.start, FADE_IN),
                }}
              >
                <Img src={staticFile(s.group.photo)} style={{ width: "100%", height: "100%", objectFit: "cover" }} />
              </div>

              {/* dim overlay with the active member's exact silhouette punched out,
                  plus a red outline traced around them */}
              {maskOpacity > 0 && pts.length > 0 ? (
                <svg
                  width={PHOTO.width}
                  height={PHOTO.height}
                  viewBox="0 0 100 100"
                  preserveAspectRatio="none"
                  style={{ position: "absolute", left: PHOTO.left, top: PHOTO.top, overflow: "visible" }}
                >
                  <path d={holePath(pts)} fillRule="evenodd" fill={MASK_COLOR} style={{ opacity: maskOpacity }} />
                  <polygon
                    points={polyPoints(pts)}
                    fill="none"
                    stroke={C.red}
                    strokeWidth={3}
                    strokeLinejoin="round"
                    vectorEffect="non-scaling-stroke"
                    style={{ opacity: maskOpacity, filter: `drop-shadow(0 0 6px ${C.red})` }}
                  />
                </svg>
              ) : null}

              {/* accumulating list — each member appends below the previous, active one highlighted */}
              <div style={{ position: "absolute", left: listLeft, top: listTop, display: "flex", flexDirection: "column", gap: rowGap }}>
                {s.group.members.map((m, idx) => {
                  const revealAt = s.start + HOLD + idx * PER;
                  const itemOpacity = seg(f, revealAt + 4, 18) * photoOpacity;
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
