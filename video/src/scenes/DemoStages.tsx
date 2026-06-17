import React from "react";
import { StageClip } from "../components/StageClip";
import { STAGES } from "../assets";

const Stage: React.FC<{ i: number; muted?: boolean }> = ({ i, muted }) => {
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
      muted={muted}
    />
  );
};

export const StagePlayer: React.FC = () => <Stage i={0} />;
export const StageLogo: React.FC = () => <Stage i={1} />;
// Body segmentation's recorded audio is just camera noise — keep this one muted.
export const StageSeg: React.FC = () => <Stage i={2} muted />;
