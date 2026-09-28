#!/usr/bin/env node
/*
 * Deterministic frame capture for review. Because every frame is a pure function of time,
 * seeking and screenshotting gives exactly what the audience sees at that instant.
 *
 *   node tools/capture.mjs stills out/ 0 4.5 12 20.5            # specific timestamps
 *   node tools/capture.mjs video out/frames --fps 30             # every frame
 *   node tools/capture.mjs video out/sub --fps 30 --sub 4        # 4 sub-frames per frame across
 *                                                                  a 180° shutter, for motion blur
 *   node tools/capture.mjs video out/sub --scale 1 --dsf 2        # supersample: 3840×2160 pixels,
 *                                                                  reduced to 1080p by accumulate.py
 *   (tools/render-preview.sh does the whole chain: cues → music → frames → blur → MP4 with sound)
 *
 * Needs `playwright-core` (npm i -D playwright-core) and a Chromium; set CHROMIUM_PATH to
 * use a specific binary.
 */
import { chromium } from 'playwright-core';
import { mkdirSync } from 'node:fs';
import { resolve, dirname, join } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const here = dirname(fileURLToPath(import.meta.url));
const page_url = pathToFileURL(resolve(here, '..', 'index.html')).href;
const [mode, outDir, ...rest] = process.argv.slice(2);
if (!mode || !outDir) {
  console.error('usage: capture.mjs stills <outDir> <t…> | video <outDir> [--fps N] [--from s] [--to s] [--scale k] [--dsf n]');
  process.exit(1);
}
const opt = (name, dflt) => {
  const i = rest.indexOf('--' + name);
  return i >= 0 ? parseFloat(rest[i + 1]) : dflt;
};
mkdirSync(outDir, { recursive: true });

const scale = opt('scale', 0.5);
// Device pixels per CSS pixel. Layers the camera zooms into are rasterised at their CSS size,
// so 2 keeps them sharp once accumulate.py brings the frame back down to 1920×1080.
const dsf = opt('dsf', 1);
const browser = await chromium.launch({
  executablePath: process.env.CHROMIUM_PATH || undefined,
  args: ['--force-color-profile=srgb', '--font-render-hinting=none'],
});
const page = await browser.newPage({ viewport: { width: Math.round(1920 * scale), height: Math.round(1080 * scale) }, deviceScaleFactor: dsf });
page.on('pageerror', (e) => console.error('page error:', e.message));
await page.goto(page_url + '?t=0');
await page.waitForFunction(() => document.documentElement.dataset.ready === '1');
await page.waitForTimeout(600); // let the stage's fade-in finish

const shoot = async (t, file) => {
  await page.evaluate((t) => window.Applicable.player.seek(t), t);
  await page.evaluate(() => new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r))));
  await page.screenshot({ path: file });
};

if (mode === 'stills') {
  const times = rest.filter((x, i) => !x.startsWith('--') && !(rest[i - 1] || '').startsWith('--'));
  for (const s of times) {
    const t = parseFloat(s);
    await shoot(t, join(outDir, `t${t.toFixed(2).padStart(6, '0')}.png`));
  }
} else {
  const fps = opt('fps', 30);
  const sub = opt('sub', 1);
  const duration = await page.evaluate(() => window.Applicable.player.duration);
  const from = opt('from', 0), to = opt('to', duration);
  let i = 0;
  // Files are named by absolute frame number, so several captures can split one film.
  for (let f = Math.round(from * fps); f < Math.round(to * fps); f++, i++) {
    const name = String(f).padStart(5, '0');
    if (sub === 1 && dsf === 1) await shoot(f / fps, join(outDir, name + '.png'));
    else if (sub === 1) await shoot(f / fps, join(outDir, name + '_0.png')); // still to be reduced
    // Sub-frames centred on the frame time across a 180° shutter (half the frame interval).
    else for (let k = 0; k < sub; k++) await shoot(f / fps + ((k + 0.5) / sub - 0.5) * (0.5 / fps), join(outDir, `${name}_${k}.png`));
  }
  console.log(`${i} frames at ${fps} fps` + (sub > 1 ? `, ${sub} sub-frames each` : ''));
}
await browser.close();
