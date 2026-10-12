// Integration test of the shipped Video.js build, actual HLS and DOM controls.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const http = require('node:http');
const path = require('node:path');
const os = require('node:os');
const {execFileSync} = require('node:child_process');
const {chromium} = require(process.env.NKL_PLAYWRIGHT || 'playwright');

const root = path.resolve(__dirname, '..');
const media = fs.mkdtempSync(path.join(os.tmpdir(), 'nkl-player-'));
execFileSync('ffmpeg', ['-hide_banner', '-loglevel', 'error', '-f', 'lavfi', '-i',
  'testsrc2=size=320x180:rate=15', '-t', '60', '-c:v', 'libx264', '-preset', 'ultrafast',
  '-g', '30', '-sc_threshold', '0', '-f', 'hls', '-hls_time', '2', '-hls_list_size', '0',
  path.join(media, 'stream.m3u8')]);
const template = fs.readFileSync(path.join(root, 'ui/public/_player/videojs/player.html'), 'utf8');
let restarting = false;
const server = http.createServer((req, res) => {
  const p = new URL(req.url, 'http://localhost').pathname;
  res.setHeader('Cache-Control', 'no-store');
  if (p === '/') {
    res.setHeader('Content-Type', 'text/html');
    return res.end(['a', 'b', 'c'].map(id => `<iframe src="/${id}.html" width="480" height="270"></iframe>`).join(''));
  }
  if (/^\/[abc]\.html$/.test(p)) {
    res.setHeader('Content-Type', 'text/html');
    return res.end(template.replace(/{{#if (airplay|chromecast)}}[\s\S]*?{{\/if}}/g, '')
      .replaceAll('{{channelid}}', p[1]).replace(/{{[^}]+}}/g, 'Test'));
  }
  if (p.endsWith('/config.js')) {
    res.setHeader('Content-Type', 'application/javascript');
    return res.end('var playerConfig=' + JSON.stringify({channelid:p.split('/')[2], source:'stream.m3u8',
      poster:'/poster.svg', autoplay:false, mute:true, color:{buttons:'#fff'}, overlay:{enabled:false},
      dvr:{enabled:true, hours:3, segmentDuration:2}, playback:{singleActiveStream:true, sessionLimitEnabled:true}}));
  }
  if (p === '/poster.svg') {
    res.setHeader('Content-Type', 'image/svg+xml');
    return res.end('<svg xmlns="http://www.w3.org/2000/svg" width="320" height="180"><rect width="320" height="180" fill="#497d49"/></svg>');
  }
  if (restarting && p.endsWith('.m3u8')) {res.statusCode=503; return res.end('Restarting');}
  const file = p.startsWith('/player/videojs/')
    ? path.join(root, 'ui/public/_player/videojs', p.slice('/player/videojs/'.length))
    : path.join(media, path.basename(p));
  if (!fs.existsSync(file) || !fs.statSync(file).isFile()) {res.statusCode=404; return res.end();}
  res.setHeader('Content-Type', ({'.js':'application/javascript','.css':'text/css','.m3u8':'application/vnd.apple.mpegurl','.ts':'video/mp2t'})[path.extname(file)] || 'application/octet-stream');
  res.end(fs.readFileSync(file));
});

(async () => {
  let browser;
  try {
    await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
    browser = await chromium.launch({headless:true, executablePath:process.env.NKL_CHROMIUM || undefined, args:['--no-sandbox','--disable-dev-shm-usage']});
    const page = await browser.newPage({viewport:{width:1500,height:500}, locale:'de-DE'});
    const errors=[];
    page.on('pageerror', error => errors.push(error.message));
    await page.goto(`http://127.0.0.1:${server.address().port}/`);
    const frame = id => page.frames().find(f => f.url().endsWith(`/${id}.html`));
    for (const id of ['a','b','c']) await frame(id).waitForFunction(() => window.player && player.readyState() >= 0);
    const a=frame('a'), b=frame('b'), c=frame('c');
    for (let cycle=0; cycle<3; cycle++) {
      for (const [active, stopped] of [[a,b],[b,a]]) {
        await active.locator('.vjs-big-play-button').click();
        await active.waitForFunction(() => !player.paused() && player.currentTime()>0 && !player.error());
        await stopped.waitForFunction(() => player.paused() && !player.hasStarted());
        assert.ok(await stopped.locator('.vjs-big-play-button').isVisible());
        assert.equal(await stopped.locator('#lc-playback-gate').isVisible(), false);
        assert.equal(await c.evaluate(() => player.hasStarted()), false);
      }
    }
    // A manifest unavailable while Core/FFmpeg restarts must recover without
    // saving/reloading the generated page. Exercise real VHS HTTP failures.
    restarting = true;
    await a.locator('.vjs-big-play-button').click();
    await a.waitForFunction(() => sourceRetryCount > 0, {timeout:30000});
    restarting = false;
    await a.waitForFunction(() => !player.paused() && player.currentTime()>0 && !player.error(), {timeout:30000});
    // Deactivation while a retry is pending must never resume the old stream.
    await a.evaluate(() => player.error({code:2, message:'Temporary network interruption'}));
    await b.locator('.vjs-big-play-button').click();
    await b.waitForFunction(() => !player.paused() && player.currentTime()>0);
    await a.waitForFunction(() => sourceRetryTimer === null && !publicStreamActivated);
    // Poster clicks use a separate native Video.js component from BigPlayButton.
    await a.locator('.vjs-poster').first().click({position:{x:20,y:20}});
    await a.waitForFunction(() => !player.paused() && player.currentTime()>0);
    await a.evaluate(() => deactivatePublicStream('session'));
    assert.ok(await a.locator('#lc-playback-gate').isVisible());
    assert.equal(await a.locator('#lc-playback-gate-button').textContent(), '▶ Weiter ansehen');
    await a.locator('#lc-playback-gate-button').click();
    await a.waitForFunction(() => !player.paused() && player.currentTime()>0 && !player.error());
    assert.deepEqual(errors, []);
    console.log('Chromium: repeated real HLS reactivation, native Play/poster, restart recovery, untouched third player and session gate passed');
  } finally {
    if (browser) await browser.close();
    server.close();
    fs.rmSync(media, {recursive:true, force:true});
  }
})().catch(error => {console.error(error); process.exitCode=1;});
