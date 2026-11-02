const puppeteer = require('puppeteer');
const fs = require('fs');
const path = require('path');
const { execSync } = require('child_process');

async function record() {
  const framesDir = path.join(__dirname, '..', 'temp_frames');
  if (fs.existsSync(framesDir)) {
    fs.rmSync(framesDir, { recursive: true, force: true });
  }
  fs.mkdirSync(framesDir, { recursive: true });

  console.log("Launching headless browser at 1920x1080...");
  const browser = await puppeteer.launch({
    headless: "new",
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--window-size=1920,1080']
  });

  const page = await browser.newPage();
  await page.setViewport({ width: 1920, height: 1080, deviceScaleFactor: 1 });

  console.log("Navigating to http://127.0.0.1:8000/...");
  await page.goto('http://127.0.0.1:8000/', { waitUntil: 'networkidle0' });

  let frameCount = 0;
  const fps = 15; // 15 fps capture for high stability and smooth motion
  const frameIntervalMs = 1000 / fps;

  // Helper to capture a frame
  async function snap() {
    frameCount++;
    const filename = path.join(framesDir, `frame_${String(frameCount).padStart(5, '0')}.png`);
    await page.screenshot({ path: filename });
  }

  // Hold state for N seconds
  async function hold(seconds) {
    const totalFrames = Math.round(seconds * fps);
    for (let i = 0; i < totalFrames; i++) {
      await snap();
      await new Promise(r => setTimeout(r, frameIntervalMs));
    }
  }

  console.log("Stage 1: Overview of Live Dashboard...");
  await hold(4);

  console.log("Stage 2: Scenario 1 - API Key Rotation (Auto-Response)...");
  await page.evaluate(() => {
    document.querySelectorAll('.btn-scenario')[0].click();
  });
  // Wait for submission & animation
  await hold(12);

  console.log("Stage 3: Scenario 2 - Outage Safety Veto...");
  await page.evaluate(() => {
    document.querySelectorAll('.btn-scenario')[1].click();
  });
  await hold(12);

  console.log("Stage 4: Scenario 3 - PII & Luhn Checksum Redaction...");
  await page.evaluate(() => {
    document.querySelectorAll('.btn-scenario')[2].click();
  });
  await hold(12);

  console.log("Stage 5: Scenario 4 - Low Similarity Gate Failure...");
  await page.evaluate(() => {
    document.querySelectorAll('.btn-scenario')[3].click();
  });
  await hold(10);

  console.log("Stage 6: Testing Database Trigger Immutability...");
  await page.evaluate(() => {
    document.querySelectorAll('.btn-scenario')[4].click();
  });
  await hold(6);

  console.log("Stage 7: Inspecting SQLite Decision Log Table...");
  await page.evaluate(() => {
    window.scrollTo({ top: 400, behavior: 'smooth' });
  });
  await hold(8);

  console.log(`Captured ${frameCount} frames. Closing browser...`);
  await browser.close();

  const outVideo = path.join(__dirname, '..', '01_Video', 'in_app_demo_live.mp4');
  console.log(`Encoding frames to ${outVideo} via FFmpeg...`);
  const ffmpegCmd = `ffmpeg -y -framerate ${fps} -i "${path.join(framesDir, 'frame_%05d.png')}" -c:v libx264 -pix_fmt yuv420p -crf 18 "${outVideo}"`;
  execSync(ffmpegCmd, { stdio: 'inherit' });

  console.log("Cleaning up temp frames...");
  fs.rmSync(framesDir, { recursive: true, force: true });
  console.log("In-app live demo recorded successfully!");
}

record().catch(err => {
  console.error("Recording failed:", err);
  process.exit(1);
});

