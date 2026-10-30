// Usage: node render.js stills <t1,t2,...> | node render.js video <out.mp4>
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const path = require('path');

const FPS = 30, DURATION = 22.0;
const [mode, arg] = process.argv.slice(2);

(async () => {
  const browser = await chromium.launch();
  const page = await browser.newPage({ viewport: { width: 1920, height: 1080 } });
  await page.goto('file://' + path.join(__dirname, 'index.html'));
  await page.evaluate(() => document.fonts.ready);

  if (mode === 'stills') {
    for (const t of arg.split(',').map(Number)) {
      await page.evaluate((x) => window.render(x), t);
      await page.screenshot({ path: path.join(__dirname, 'stills', `t${t.toFixed(2)}.png`) });
    }
  } else {
    const ff = spawn('ffmpeg', ['-y', '-loglevel', 'error', '-f', 'image2pipe', '-framerate', String(FPS),
      '-i', '-', '-c:v', 'libx264', '-crf', '16', '-preset', 'medium', '-pix_fmt', 'yuv420p', arg],
      { stdio: ['pipe', 'inherit', 'inherit'] });
    const total = Math.round(DURATION * FPS);
    for (let f = 0; f < total; f++) {
      await page.evaluate((x) => window.render(x), f / FPS);
      const buf = await page.screenshot({ type: 'png' });
      if (!ff.stdin.write(buf)) await new Promise((r) => ff.stdin.once('drain', r));
      if (f % 60 === 0) process.stderr.write(`frame ${f}/${total}\n`);
    }
    ff.stdin.end();
    await new Promise((r) => ff.on('close', r));
  }
  await browser.close();
})();
