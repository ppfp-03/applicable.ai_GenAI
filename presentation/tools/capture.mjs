#!/usr/bin/env node
/*
 * Deterministic frame capture for review. Because every frame is a pure function of time,
 * seeking and screenshotting gives exactly what the audience sees at that instant.
 *
 *   node tools/capture.mjs stills out/ 0 4.5 12 20.5            # specific timestamps
 *   node tools/capture.mjs video out/frames --fps 30             # every frame, then:
 *   ffmpeg -framerate 30 -i out/frames/%05d.png -pix_fmt yuv420p -crf 18 out/trailer.mp4
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
  console.error('usage: capture.mjs stills <outDir> <t…> | video <outDir> [--fps N] [--from s] [--to s] [--scale k]');
  process.exit(1);
}
const opt = (name, dflt) => {
  const i = rest.indexOf('--' + name);
  return i >= 0 ? parseFloat(rest[i + 1]) : dflt;
};
mkdirSync(outDir, { recursive: true });

const scale = opt('scale', 0.5);
const browser = await chromium.launch({
  executablePath: process.env.CHROMIUM_PATH || undefined,
  args: ['--force-color-profile=srgb', '--font-render-hinting=none'],
});
const page = await browser.newPage({ viewport: { width: Math.round(1920 * scale), height: Math.round(1080 * scale) }, deviceScaleFactor: 1 });
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
  const duration = await page.evaluate(() => window.Applicable.player.duration);
  const from = opt('from', 0), to = opt('to', duration);
  let i = 0;
  for (let f = Math.round(from * fps); f <= Math.round(to * fps); f++, i++) {
    await shoot(f / fps, join(outDir, String(i).padStart(5, '0') + '.png'));
  }
  console.log(`${i} frames at ${fps} fps`);
}
await browser.close();
