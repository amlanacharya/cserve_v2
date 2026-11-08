// Records the LIVE dashboard (src/templates/dashboard.html) at 1920x1080.
// Usage: start the API (uvicorn src.api:app --port 8000), then `node scripts/record_in_app_demo.js`.
// Each scenario waits for the REAL API response; only the waiting time is compressed (max WAIT_CAP s)
// so footage never shows a stale result. Outputs:
//   01_Video/in_app_demo_live.mp4, hyperframes_film/assets/in_app_demo.mp4, hyperframes_film/assets/in_app_demo.marks.json
const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

const ROOT = path.join(__dirname, '..');
const URL = process.env.DEMO_URL || 'http://127.0.0.1:8000/dashboard';
const WAIT_CAP = 4;   // seconds of footage allowed for the "processing" phase of each scenario
const HOLD = 25;      // seconds the finished result stays on screen

const SCENARIOS = [
  ['auto', 'AUTO_RESOLVED'],
  ['veto', 'SAFETY_VETO'],
  ['gate1', 'GATE 1'],
  ['gate2', 'GATE 2'],
  ['guard', 'GUARDRAIL'],
  ['pii', 'PII'],
];

async function record() {
  const framesDir = path.join(ROOT, 'temp_frames');
  fs.rmSync(framesDir, { recursive: true, force: true });
  fs.mkdirSync(framesDir, { recursive: true });

  const browser = await puppeteer.launch({
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--window-size=1920,1080'],
  });
  const page = await browser.newPage();
  await page.setViewport({ width: 1920, height: 1080, deviceScaleFactor: 1 });
  await page.goto(URL, { waitUntil: 'networkidle0' });

  const frames = []; // {file, dt, wait}
  let n = 0;
  let last = Date.now();
  async function snap(wait) {
    n++;
    const file = path.join(framesDir, `f_${String(n).padStart(5, '0')}.jpg`);
    await page.screenshot({ path: file, type: 'jpeg', quality: 92 });
    const now = Date.now();
    frames.push({ file, dt: (now - last) / 1000, wait });
    last = now;
  }
  async function hold(seconds) {
    const end = Date.now() + seconds * 1000;
    while (Date.now() < end) await snap(false);
  }
  const trafficText = () => page.evaluate(() => document.getElementById('api-log-text').innerText);
  async function waitForResult(before, timeoutMs = 150000) {
    const end = Date.now() + timeoutMs;
    while (Date.now() < end) {
      const t = await trafficText();
      if (t !== before && /Roundtrip/.test(t)) return true;
      await snap(true);
    }
    return false;
  }

  await hold(5);
  const marks = [];
  for (const [id, label] of SCENARIOS) {
    console.log('Scenario', label);
    const before = await trafficText();
    const startFrame = frames.length;
    await page.evaluate((sid) => loadScenario(sid), id);
    const ok = await waitForResult(before);
    if (!ok) console.warn('  (no response within timeout)');
    await hold(HOLD);
    marks.push({ id, label, startFrame, endFrame: frames.length, answered: ok });
  }

  console.log('Tamper test');
  const tStart = frames.length;
  await page.evaluate(() => testTamper());
  await hold(15);
  marks.push({ id: 'tamper', label: 'TAMPER', startFrame: tStart, endFrame: frames.length, answered: true });

  console.log('Audit log');
  const aStart = frames.length;
  await page.evaluate(() => window.scrollTo({ top: document.body.scrollHeight, behavior: 'smooth' }));
  await hold(33);
  marks.push({ id: 'audit', label: 'AUDIT', startFrame: aStart, endFrame: frames.length, answered: true });
  await browser.close();

  // Compress waiting frames so the processing phase of each scenario totals at most WAIT_CAP seconds.
  for (const m of marks) {
    const w = frames.slice(m.startFrame, m.endFrame).filter((f) => f.wait);
    const total = w.reduce((a, f) => a + f.dt, 0);
    m.rawWait = +total.toFixed(1);
    if (total > WAIT_CAP) w.forEach((f) => { f.dt *= WAIT_CAP / total; });
  }
  let t = 0;
  const lines = [];
  frames.forEach((f, i) => {
    f.t = t; t += f.dt;
    lines.push(`file '${f.file.replace(/\\/g, '/')}'`, `duration ${Math.max(f.dt, 0.01).toFixed(4)}`);
  });
  lines.push(`file '${frames[frames.length - 1].file.replace(/\\/g, '/')}'`);
  const listPath = path.join(framesDir, 'list.txt');
  fs.writeFileSync(listPath, lines.join('\n'));
  const outMarks = marks.map((m) => ({
    id: m.id, label: m.label, rawWaitSeconds: m.rawWait, answered: m.answered,
    start: +frames[m.startFrame].t.toFixed(1),
    end: +(m.endFrame < frames.length ? frames[m.endFrame].t : t).toFixed(1),
  }));
  console.log(JSON.stringify(outMarks), 'total', t.toFixed(1));

  const outA = path.join(ROOT, '01_Video', 'in_app_demo_live.mp4');
  const outB = path.join(ROOT, 'hyperframes_film', 'assets', 'in_app_demo.mp4');
  fs.mkdirSync(path.dirname(outB), { recursive: true });
  execSync(`ffmpeg -y -f concat -safe 0 -i "${listPath}" -vf "fps=30,format=yuv420p" -c:v libx264 -crf 22 -an -movflags +faststart "${outA}"`, { stdio: 'inherit' });
  fs.copyFileSync(outA, outB);
  fs.writeFileSync(path.join(ROOT, 'hyperframes_film', 'assets', 'in_app_demo.marks.json'), JSON.stringify({ total: +t.toFixed(1), marks: outMarks }, null, 2));
  fs.rmSync(framesDir, { recursive: true, force: true });
  console.log('Done:', outA);
}

record().catch((e) => { console.error(e); process.exit(1); });
