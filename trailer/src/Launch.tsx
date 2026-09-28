import React from "react";
import { AbsoluteFill, Sequence, staticFile } from "remotion";
import { Audio } from "@remotion/media";
import { ACT } from "./timeline";
import { Act1TooLate } from "./acts/Act1TooLate";
import { Act2Problem } from "./acts/Act2Problem";
import { Act3Reveal } from "./acts/Act3Reveal";
import { Act4Freshness } from "./acts/Act4Freshness";
import { Act5ActFirst } from "./acts/Act5ActFirst";
import { Act6Lockup } from "./acts/Act6Lockup";
import { FontGate } from "./lib/FontGate";

// The film. Acts hand over on exact frames; every seam is a designed match, not a cut.
// The soundtrack plays in Studio only: renders are muted and the master audio is muxed by ffmpeg
// (scripts/render.sh), so encoder priming can never offset it.
export const Launch: React.FC<{ withAudio?: boolean }> = ({ withAudio = true }) => (
  <FontGate>
    <AbsoluteFill style={{ background: "#000" }}>
      <Sequence from={ACT.tooLate.from} durationInFrames={ACT.tooLate.dur} name="1 · Too late">
        <Act1TooLate />
      </Sequence>
      <Sequence from={ACT.problem.from} durationInFrames={ACT.problem.dur} name="2 · The real problem">
        <Act2Problem />
      </Sequence>
      <Sequence from={ACT.reveal.from} durationInFrames={ACT.reveal.dur} name="3 · Applicable.ai">
        <Act3Reveal />
      </Sequence>
      <Sequence from={ACT.fresh.from} durationInFrames={ACT.fresh.dur} name="4 · Find what's fresh">
        <Act4Freshness />
      </Sequence>
      <Sequence from={ACT.actFirst.from} durationInFrames={ACT.actFirst.dur} name="5 · Act first">
        <Act5ActFirst />
      </Sequence>
      <Sequence from={ACT.edge.from} durationInFrames={ACT.edge.dur} name="6 · Competitive edge">
        <Act6Lockup />
      </Sequence>
      {withAudio && <Audio src={staticFile("audio/soundtrack.wav")} />}
    </AbsoluteFill>
  </FontGate>
);
