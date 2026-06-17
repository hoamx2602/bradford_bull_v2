import React from "react";
import { StageClip } from "../components/StageClip";
import { STAGES } from "../assets";

const Stage: React.FC<{ i: number }> = ({ i }) => {
  const s = STAGES[i];
  return (
    <StageClip
      label={s.label}
      caption={s.caption}
      idx={i + 1}
      total={STAGES.length}
      src={s.src}
      from={s.from}
      temp={s.temp}
    />
  );
};

export const StagePlayer: React.FC = () => <Stage i={0} />;
export const StageLogo: React.FC = () => <Stage i={1} />;
export const StageSeg: React.FC = () => <Stage i={2} />;
