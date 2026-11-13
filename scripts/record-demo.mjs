#!/usr/bin/env node
// Record the real local Relate-backed application. No fixture, mocked API or remote service.
import assert from 'node:assert/strict';
import { mkdir, readFile, writeFile, stat, unlink } from 'node:fs/promises';
import path from 'node:path';
import { spawnSync } from 'node:child_process';
import { chromium } from 'playwright';
import ffmpegBinary from '@ffmpeg-installer/ffmpeg';
import ffprobeBinary from '@ffprobe-installer/ffprobe';

const base = process.env.DEMO_URL || 'http://127.0.0.1:8765';
const output = path.resolve(process.argv[2] || 'demo/output');
await mkdir(output, { recursive: true });
const health = await (await fetch(base + '/api/health')).json();
const graph = await (await fetch(base + '/api/graph')).json();
const impact = await (await fetch(base + '/api/impact?id=lab.assays.moisture_pct')).json();
assert.equal(health.ok, true, 'A real Relate database must be readable');
assert.equal(graph.assets.length, 49);
assert.equal(graph.flows.length, 60);
const actualOutputs = new Set(impact.outputs.map(x => x.id));
for (const id of ['metric.payout', 'metric.carbon', 'dash.esg']) {
  assert(actualOutputs.has(id), 'Expected Relate path to ' + id);
}
const browser = await chromium.launch({ headless: true, args: ['--no-sandbox'] });
const context = await browser.newContext({
  viewport: {width: 1600, height: 900},
  deviceScaleFactor: 1, acceptDownloads: true, bypassCSP: true,
  recordVideo: {dir: output, size: {width: 1600, height: 900}}
});
const page = await context.newPage();
const pageErrors = [];
page.on('pageerror', e => pageErrors.push(e.message));
page.on('response', r => {
  if (r.url().includes('/api/') && r.status() >= 400) pageErrors.push('HTTP ' + r.status() + ': ' + r.url());
});
try {
  await page.goto(base, {waitUntil: 'domcontentloaded'});
  await page.waitForFunction(() => {
    const title = document.querySelector('#focus-title');
    return title && title.textContent !== 'Loading relationships...' && document.querySelectorAll('#world .node').length >= 6;
  }, {timeout: 20000});
  await page.addStyleTag({ content: [
    '#rec-overlay{position:fixed;left:355px;right:35px;bottom:25px;z-index:99999;pointer-events:none;',
    'background:rgba(8,18,34,.94);border:1px solid rgba(126,184,247,.42);border-left:5px solid #f1a55c;',
    'border-radius:16px;padding:21px 28px;box-shadow:0 18px 56px rgba(0,0,0,.48);color:#f4f7ff;',
    'font-family:Inter,Arial,sans-serif;letter-spacing:.1px;transition:opacity .25s ease}',
    '#rec-label{font-size:14px;font-weight:800;color:#f3b475;letter-spacing:2.1px;margin-bottom:8px}',
    '#rec-title{font-size:27px;font-weight:800;line-height:1.18;margin-bottom:6px}',
    '#rec-body{font-size:18px;font-weight:500;line-height:1.35;color:#cdd8eb}',
    '#rec-brand{position:fixed;z-index:99999;right:35px;top:74px;color:#fff;',
    'background:rgba(8,18,34,.86);border:1px solid #3f5679;border-radius:24px;',
    'font:700 12px Inter,Arial,sans-serif;letter-spacing:1.3px;padding:9px 15px;pointer-events:none}'
  ].join('') });
  await page.evaluate(() => {
    const cap = document.createElement('div');
    cap.id = 'rec-overlay';
    cap.innerHTML = '<div id="rec-label"></div><div id="rec-title"></div><div id="rec-body"></div>';
    document.body.append(cap);
    const brand = document.createElement('div'); brand.id='rec-brand';
    brand.textContent = 'REAL RELATE GRAPH  /  LIVE CYPHER';
    document.body.append(brand);
  });
  const caption = async (step, title, detail, seconds) => {
    await page.evaluate(({step,title,detail}) => {
      document.querySelector('#rec-label').textContent = step;
      document.querySelector('#rec-title').textContent = title;
      document.querySelector('#rec-body').textContent = detail;
    }, {step,title,detail});
    await page.waitForTimeout(seconds * 1000);
  };
  const scroll = async selector => {
    await page.locator(selector).evaluate(el => el.scrollIntoView({behavior:'smooth',block:'start'}));
    await page.waitForTimeout(700);
  };

  await page.screenshot({path:path.join(output,'poster.png')});
  await caption('01  /  THE QUESTION', 'What breaks when one column changes?',
    'LabTrack moisture_pct switches from 0–100 percent to a 0–1 ratio. Which business outputs depend on it?', 10);
  await scroll('.work-card');
  assert((await page.locator('#world .node').count()) >= 6);
  await caption('02  /  REAL CYPHER LINEAGE', 'Follow the hidden eight-node dependency',
    'The path crosses assay normalization and dry mass, reaching the Scope 3 assurance dashboard.', 14);
  await scroll('.results');
  await page.locator('#outputs .output[data-id="metric.payout"]').click();
  await caption('03  /  UNEXPECTED COST', 'Supplier payments are in the blast radius',
    'Every hop is backed by a Relate FLOWS_TO relationship and its recorded explanation.', 12);
  await page.locator('#outputs .output[data-id="dash.esg"]').click();
  await scroll('.work-card');
  await caption('04  /  SECOND BUSINESS CONSEQUENCE', 'The same input reaches ESG reporting',
    'Dry tonnes also feed carbon-intensity calculations. One lab change crosses FinanceMart and ClimateMart.', 10);
  await page.locator('#view-network').click();
  await caption('05  /  EXPLORE THE BLAST RADIUS', 'One click reveals all connected impact paths',
    'The wider dependency map is traversed in the embedded Relate graph, not inferred by an AI model.', 12);
  await page.locator('#scenario-safe').click();
  await page.waitForFunction(() => document.querySelector('#focus-subtitle')?.textContent?.includes('field.harvests.field_id'));
  const negative = await (await fetch(base + '/api/impact?id=field.harvests.field_id')).json();
  const negativeIds = new Set(negative.outputs.map(o => o.id));
  assert(!negativeIds.has('metric.payout') && !negativeIds.has('metric.carbon') && !negativeIds.has('dash.esg'));
  await scroll('.work-card');
  await caption('06  /  PRECISION MATTERS', 'A narrower change must not trigger false alarms',
    'Changing field_id affects yield, but not payouts or Scope 3. Column-aware edges prevent sibling leakage.', 12);
  await page.locator('#scenario').click();
  await page.waitForFunction(() => document.querySelector('#focus-subtitle')?.textContent?.includes('lab.assays.moisture_pct'));
  await scroll('.results');
  await page.locator('#change-note').fill('moisture_pct: percentage 0–100 becomes fraction 0–1');
  const downloadPromise = page.waitForEvent('download', {timeout:12000});
  await page.locator('#download-report').click();
  const download = await downloadPromise;
  const receiptPath = path.join(output,'impact-review.md');
  await download.saveAs(receiptPath);
  const receipt = await readFile(receiptPath,'utf8');
  assert(receipt.includes('moisture_pct') && receipt.includes('Scope 3') && receipt.includes('payout'), 'Downloaded receipt lacks native lineage evidence');
  await caption('07  /  REVIEW-READY EVIDENCE', 'Export an impact receipt for the pull request',
    'The real downloaded Markdown lists affected outputs, exact paths and why each dependency exists.', 14);
  await scroll('.work-card');
  await page.locator('#view-route').click();
  await caption('08  /  REPRODUCIBLE BY DESIGN', 'Embedded Relate. One persistent .rl file.',
    '49 assets · 60 dependencies · no hosted database · read-only MCP for connected coding agents.', 10);
  assert.deepEqual(pageErrors, [], 'Browser or API errors');
  const video = page.video();
  await page.close();
  await context.close();
  await browser.close();
  const raw = path.join(output,'recorded.webm');
  await video.saveAs(raw);
  const mp4 = path.join(output,'data-impact-graph-demo.mp4');
  const ff = spawnSync(ffmpegBinary.path, [
    '-hide_banner','-loglevel','error','-y','-i',raw,
    '-an','-c:v','libx264','-preset','fast','-crf','29','-pix_fmt','yuv420p',
    '-r','24','-movflags','+faststart',mp4
  ], {encoding:'utf8',timeout:180000});
  if (ff.status !== 0) throw new Error('FFmpeg conversion failed: ' + ff.stderr);
  const probe = spawnSync(ffprobeBinary.path, ['-v','error','-show_entries','format=duration,size','-of','json',mp4], {encoding:'utf8'});
  if (probe.status !== 0) throw new Error('FFprobe failed: ' + probe.stderr);
  const info = JSON.parse(probe.stdout);
  const duration = Number(info.format.duration);
  assert(duration >= 85 && duration <= 125, 'Unexpected demo duration ' + duration);
  const bytes = (await stat(mp4)).size;
  assert(bytes > 100000 && bytes < 30000000, 'Unreasonable output size ' + bytes);
  const manifest = {date:'2026-11-13',engine:health.engine,assets:graph.assets.length,
    relationships:graph.flows.length,source:'live local Relate + Playwright',
    duration_seconds:duration,video_bytes:bytes,receipt_bytes:receipt.length,
    output_ids:[...actualOutputs],verified_negative_control:true,errors:pageErrors};
  await writeFile(path.join(output,'manifest.json'), JSON.stringify(manifest,null,2)+'\n');
  await unlink(raw);
  console.log('DATA_IMPACT_VIDEO_VERIFIED ' + JSON.stringify(manifest));
} catch(e) {
  await browser.close().catch(() => {});
  console.error('DATA_IMPACT_VIDEO_FAILED ' + (e.stack || e));
  process.exitCode=1;
}
