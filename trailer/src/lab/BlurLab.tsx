import React from "react";
import { HtmlInCanvasMotionBlur } from "@remotion/motion-blur";
import { useVideoConfig } from "remotion";
import { Act3Reveal } from "../acts/Act3Reveal";

// Evidence for the motion-blur decision (README, "Motion blur"). The reveal act - a fast wave, the
// edge collapsing into the tile, the product's soft peach glows - through Remotion's in-browser
// accumulator, to compare frame by frame with scripts/accumulate.py's float path. Same shutter.
export const BlurLab: React.FC = () => {
  const { width, height } = useVideoConfig();
  return (
    <HtmlInCanvasMotionBlur width={width} height={height} samples={16} shutterAngle={216}>
      <Act3Reveal />
    </HtmlInCanvasMotionBlur>
  );
};
