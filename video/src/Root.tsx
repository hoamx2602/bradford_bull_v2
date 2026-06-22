import React from "react";
import { Composition, Audio, staticFile } from "remotion";
import { TransitionSeries, linearTiming } from "@remotion/transitions";
import { fade } from "@remotion/transitions/fade";

import { Title } from "./scenes/Title";
import { Team, TEAM_SCENE_FRAMES } from "./scenes/Team";
import { Credits } from "./scenes/Credits";
import { Motivation } from "./scenes/Motivation";
import { What } from "./scenes/What";
import { Pipeline } from "./scenes/Pipeline";
import { StagePlayer, StageLogo, StageSeg } from "./scenes/DemoStages";
import { HardCases } from "./scenes/HardCases";
import { Dashboard } from "./scenes/Dashboard";
import { Results } from "./scenes/Results";
import { Challenges } from "./scenes/Challenges";
import { Impact } from "./scenes/Impact";
import { ProductDemo, PRODUCT_DEMO_SECS } from "./scenes/ProductDemo";
import { Closing } from "./scenes/Closing";

const FPS = 30;

type Scene = { id: string; Comp: React.FC; secs: number };

// No narration any more — each scene is held just long enough to read its
// content comfortably, then cuts to the next. Tuned by hand for pace.
const SCENES: Scene[] = [
  { id: "title", Comp: Title, secs: 6.5 },
  { id: "team", Comp: Team, secs: TEAM_SCENE_FRAMES / FPS },
  { id: "credits", Comp: Credits, secs: 6 },
  { id: "motivation", Comp: Motivation, secs: 13 },
  { id: "what", Comp: What, secs: 5 },
  { id: "pipeline", Comp: Pipeline, secs: 8 },
  { id: "stage_player", Comp: StagePlayer, secs: 5 },
  { id: "stage_logo", Comp: StageLogo, secs: 5 },
  { id: "stage_seg", Comp: StageSeg, secs: 5 },
  { id: "hardcases", Comp: HardCases, secs: 12 },
  { id: "dashboard", Comp: Dashboard, secs: 7.5 },
  { id: "results", Comp: Results, secs: 6 },
  { id: "challenges", Comp: Challenges, secs: 19 },
  { id: "impact", Comp: Impact, secs: 14.5 },
  { id: "product_demo", Comp: ProductDemo, secs: PRODUCT_DEMO_SECS },
  { id: "closing", Comp: Closing, secs: 5 },
];

const frames = (s: Scene): number => Math.round(s.secs * FPS);

// Smooth crossfade between every scene. Transitions overlap their neighbours,
// so the total is the sum of scenes minus one fade per gap.
const FADE = 26; // ~0.87s — slower crossfade so cuts feel less abrupt
const TOTAL =
  SCENES.reduce((n, s) => n + frames(s), 0) - (SCENES.length - 1) * FADE;

const Main: React.FC = () => (
  <>
    {/* background music bed across the whole video — "Inspired" by Kevin MacLeod
        (incompetech.com), CC BY. Swap public/audio/bg.mp3 for your own track.
        The track is ~80s but the video now runs much longer, so it loops to
        fill the full duration instead of cutting out partway through. */}
    <Audio src={staticFile("audio/bg.mp3")} volume={0.5} loop />

    <TransitionSeries>
      {SCENES.flatMap((s, i) => {
        const seq = (
          <TransitionSeries.Sequence key={s.id} durationInFrames={frames(s)}>
            <s.Comp />
          </TransitionSeries.Sequence>
        );
        return i === 0
          ? [seq]
          : [
              <TransitionSeries.Transition
                key={`t-${s.id}`}
                timing={linearTiming({ durationInFrames: FADE })}
                presentation={fade()}
              />,
              seq,
            ];
      })}
    </TransitionSeries>
  </>
);

export const RemotionRoot: React.FC = () => (
  <Composition
    id="LogoLense"
    component={Main}
    durationInFrames={TOTAL}
    fps={FPS}
    width={1920}
    height={1080}
  />
);
