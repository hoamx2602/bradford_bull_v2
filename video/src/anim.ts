import { interpolate, Easing } from "remotion";

const easeOut = Easing.out(Easing.cubic);

/** Eased 0→1 ramp between [start, start+dur] frames. */
export function seg(frame: number, start: number, dur = 18): number {
  return interpolate(frame, [start, start + dur], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: easeOut,
  });
}

/** Fade + rise-in style props. */
export function rise(frame: number, start: number, dur = 18, dist = 26) {
  const a = seg(frame, start, dur);
  return { opacity: a, transform: `translateY(${(1 - a) * dist}px)` };
}

/** Fade only. */
export function fade(frame: number, start: number, dur = 18): { opacity: number } {
  return { opacity: seg(frame, start, dur) };
}

/** Whole-scene gentle fade in at head and out at tail. */
export function sceneFade(frame: number, total: number): number {
  return Math.min(
    seg(frame, 0, 8),
    interpolate(frame, [total - 8, total], [1, 0], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    })
  );
}
