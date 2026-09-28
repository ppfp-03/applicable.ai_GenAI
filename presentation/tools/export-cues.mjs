#!/usr/bin/env node
/*
 * Exports every sync point of the film to audio/cues.json for the soundtrack generator.
 * As in the reference film's export-cues.ts, the numbers come from the same timeline the
 * picture uses: the page builds the film and hands over `Applicable.cues` (the musical marks
 * from timing.js plus every sound cue a scene scheduled with ctx.sfx).
 *
 *   node tools/export-cues.mjs            # writes audio/cues.json
 *
 * Needs `playwright-core` and a Chromium (CHROMIUM_PATH to pick one).
 */
import { chromium } from 'playwright-core';
import { mkdirSync, writeFileSync } from 'node:fs';
import { dirname, resolve } from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const browser = await chromium.launch({ executablePath: process.env.CHROMIUM_PATH || undefined });
const page = await browser.newPage();
page.on('pageerror', (e) => console.error('page error:', e.message));
await page.goto(pathToFileURL(resolve(root, 'index.html')).href + '?t=0');
await page.waitForFunction(() => document.documentElement.dataset.ready === '1');
const cues = await page.evaluate(() => window.Applicable.cues);
await browser.close();

mkdirSync(resolve(root, 'audio'), { recursive: true });
writeFileSync(resolve(root, 'audio', 'cues.json'), JSON.stringify(cues, null, 1) + '\n');
const names = {};
for (const s of cues.sfx) names[s.name] = (names[s.name] || 0) + 1;
console.log(`audio/cues.json: ${cues.sfx.length} sound cues over ${cues.duration}s at ${cues.bpm} BPM`, names);
