import React from "react";
import { noise2D } from "@remotion/noise";
import { H, W } from "../timeline";

export type Cam = { x: number; y: number; s: number; rot?: number };

/**
 * A 2D camera over a 1920x1080 world: world point (x, y) is framed at the screen centre at scale s.
 * Children are laid out in world coordinates.
 */
export const Camera: React.FC<{ cam: Cam; children: React.ReactNode; style?: React.CSSProperties }> = ({
  cam,
  children,
  style,
}) => {
  const tx = W / 2 - cam.x * cam.s;
  const ty = H / 2 - cam.y * cam.s;
  return (
    <div
      style={{
        position: "absolute",
        left: 0,
        top: 0,
        width: W,
        height: H,
        transformOrigin: "0 0",
        transform: `translate(${tx.toFixed(3)}px, ${ty.toFixed(3)}px) scale(${cam.s.toFixed(5)})${
          cam.rot ? ` rotate(${cam.rot.toFixed(4)}deg)` : ""
        }`,
        ...style,
      }}
    >
      {children}
    </div>
  );
};

/**
 * Operator drift: a slow, low-amplitude handheld float so locked-off shots still breathe.
 * Smooth in the frame (noise sampled at fractional frames), so motion blur sees it as motion.
 */
export const drift = (f: number, seed: string, amp = 3, speed = 0.006) => ({
  dx: noise2D(seed + "x", f * speed, 0) * amp,
  dy: noise2D(seed + "y", 0, f * speed) * amp,
});
