import React from "react";
import { Composition, Folder } from "remotion";
import { FontGate } from "./lib/FontGate";
import { Launch } from "./Launch";
import { LaunchSub, subMetadata } from "./LaunchSub";
import { Act1TooLate } from "./acts/Act1TooLate";
import { Act2Problem } from "./acts/Act2Problem";
import { Act3Reveal } from "./acts/Act3Reveal";
import { Act4Freshness } from "./acts/Act4Freshness";
import { Act5ActFirst } from "./acts/Act5ActFirst";
import { Act6Lockup } from "./acts/Act6Lockup";
import { BlurLab } from "./lab/BlurLab";
import { ACT, FPS, H, TOTAL, W } from "./timeline";

const gated = (C: React.FC) => {
  const Gated: React.FC = () => (
    <FontGate>
      <C />
    </FontGate>
  );
  return Gated;
};

export const RemotionRoot: React.FC = () => (
  <>
    {/* The film (with the soundtrack in Studio; renders are muted and muxed by scripts/render.sh). */}
    <Composition id="Launch" component={Launch} durationInFrames={TOTAL} fps={FPS} width={W} height={H} defaultProps={{ withAudio: true }} />
    {/* The film as sub-frames for the motion-blurred master. */}
    <Composition
      id="LaunchSub"
      component={LaunchSub}
      durationInFrames={TOTAL}
      fps={FPS}
      width={W}
      height={H}
      defaultProps={{ groups: [] as number[] }}
      calculateMetadata={subMetadata}
    />

    {/* Each act alone, for iterating without scrubbing the film (same components as the film). */}
    <Folder name="Acts">
      <Composition id="Act1" component={gated(Act1TooLate)} durationInFrames={ACT.tooLate.dur} fps={FPS} width={W} height={H} />
      <Composition id="Act2" component={gated(Act2Problem)} durationInFrames={ACT.problem.dur} fps={FPS} width={W} height={H} />
      <Composition id="Act3" component={gated(Act3Reveal)} durationInFrames={ACT.reveal.dur} fps={FPS} width={W} height={H} />
      <Composition id="Act4" component={gated(Act4Freshness)} durationInFrames={ACT.fresh.dur} fps={FPS} width={W} height={H} />
      <Composition id="Act5" component={gated(Act5ActFirst)} durationInFrames={ACT.actFirst.dur} fps={FPS} width={W} height={H} />
      <Composition id="Act6" component={gated(Act6Lockup)} durationInFrames={ACT.edge.dur} fps={FPS} width={W} height={H} />
    </Folder>

    {/* Motion-blur comparison: Remotion's in-browser HtmlInCanvasMotionBlur vs the external path. */}
    <Folder name="Lab">
      <Composition id="BlurLab" component={gated(BlurLab)} durationInFrames={ACT.reveal.dur} fps={FPS} width={W} height={H} />
    </Folder>
  </>
);
