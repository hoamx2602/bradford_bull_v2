import React from "react";
import { AbsoluteFill, Video, staticFile, useCurrentFrame } from "remotion";
import { seg } from "../anim";

/** Section 5 — the real annotated demo footage (crowd audio kept quiet; the
 *  scene's narration is layered on by the Series wrapper in Root). */
export const Demo: React.FC = () => {
  const f = useCurrentFrame();
  return (
    <AbsoluteFill style={{ background: "#000" }}>
      <Video
        src={staticFile("demo.mp4")}
        muted
        style={{ width: "100%", height: "100%", objectFit: "cover", opacity: seg(f, 0, 10) }}
      />
    </AbsoluteFill>
  );
};
