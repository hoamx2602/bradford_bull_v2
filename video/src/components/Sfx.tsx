import React from "react";
import { Audio, Sequence, staticFile } from "remotion";

type Name = "tick" | "pop" | "whoosh" | "riser" | "chime";

/** Fires a one-shot sound effect starting at scene-local frame `from`. */
export const Sfx: React.FC<{ name: Name; from: number; volume?: number }> = ({
  name,
  from,
  volume = 0.5,
}) => (
  <Sequence from={from} durationInFrames={45} layout="none">
    <Audio src={staticFile(`audio/sfx/${name}.mp3`)} volume={volume} />
  </Sequence>
);

/** Convenience: a series of `tick`s at the given scene-local frames. */
export const Ticks: React.FC<{ at: number[]; name?: Name; volume?: number }> = ({
  at,
  name = "tick",
  volume = 0.4,
}) => (
  <>
    {at.map((f, i) => (
      <Sfx key={i} name={name} from={f} volume={volume} />
    ))}
  </>
);
