// Firefox regression with three consecutive, high-bitrate production segments.
// TIMELAPSE_FIXTURE_DIR contains index.m3u8 and its first three TS files.
// No production requests or modifications: everything is served on loopback.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const http = require('node:http');
const {firefox} = require('playwright');
const root = path.resolve(__dirname, '..');
const fixture = process.env.TIMELAPSE_FIXTURE_DIR;
assert.ok(fixture, 'Set TIMELAPSE_FIXTURE_DIR to the downloaded regression fixture');
const manifest = fs.readFileSync(path.join(fixture, 'index.m3u8'), 'utf8');
const segments = [...manifest.matchAll(/#EXTINF:([\d.]+),\s*\n(segment-\d+\.ts)/g)]
  .slice(0, 3).map(m => ({duration:Number(m[1]), name:m[2]}));
assert.equal(segments.length, 3);
const duration = segments.reduce((sum, s) => sum + s.duration, 0);
const playlist = '#EXTM3U\n#EXT-X-VERSION:3\n#EXT-X-PLAYLIST-TYPE:VOD\n#EXT-X-TARGETDURATION:' +
  Math.ceil(Math.max(...segments.map(s => s.duration))) + '\n' + segments.map((s, i) =>
    (i ? '#EXT-X-DISCONTINUITY\n' : '') + `#EXTINF:${s.duration},\n${s.name}\n`).join('') + '#EXT-X-ENDLIST\n';
const files = {
  '/video.js':fs.readFileSync(path.join(root, 'ui/public/_player/videojs/dist/video.min.js')),
  '/helper.js':fs.readFileSync(path.join(root, 'ui/public/_player/videojs/dist/timeline-markers.js')),
};
const html = '<script src="/video.js"></script><script src="/helper.js"></script>' +
  '<video id="preview" muted controls></video><video id="live" muted></video>';

(async () => {
  const server = http.createServer((req, res) => {
    const url = req.url.split('?')[0];
    if (url === '/') return res.end(html);
    if (files[url]) { res.setHeader('Content-Type', 'application/javascript'); return res.end(files[url]); }
    if (url === '/index.m3u8') { res.setHeader('Content-Type', 'application/vnd.apple.mpegurl'); return res.end(playlist); }
    const segment = segments.find(s => '/' + s.name === url);
    if (!segment) { res.statusCode = 404; return res.end(); }
    const file = path.join(fixture, segment.name);
    res.setHeader('Content-Type', 'video/mp2t');
    res.setHeader('Content-Length', fs.statSync(file).size);
    // Simulate a slow download; prefetch must absorb this delay.
    setTimeout(() => { if (!res.destroyed) fs.createReadStream(file).pipe(res); },
      segment === segments[2] ? 8000 : 0);
  });
  await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
  let browser;
  try {
    browser = await firefox.launch({headless:true});
    const page = await browser.newPage();
    const errors = [], quota = [];
    page.on('pageerror', e => errors.push(e.message));
    page.on('console', m => { if (m.text().includes('QUOTA_EXCEEDED_ERR')) quota.push(m.text()); });
    await page.goto(`http://127.0.0.1:${server.address().port}/`);
    await page.evaluate(() => {
      videojs.log.level('debug');
      window.preview = videojs('preview', {muted:true, preload:'none'});
      window.seeks = []; window.waits = 0;
      preview.on('seeking', () => seeks.push(preview.currentTime()));
      preview.on('waiting', () => waits++);
      nklConfigureTimelapseBuffer(preview);
      preview.src({src:'/index.m3u8', type:'application/x-mpegURL'});
      preview.play();
    });
    await page.waitForFunction(() => preview.ended(), undefined, {timeout:180000});
    assert.deepEqual(await page.evaluate(() => seeks), [], 'Playback must not jump automatically');
    assert.deepEqual(quota, [], 'No destructive quota recovery');
    assert.equal(await page.evaluate(() => preview.error()), null);
    assert.ok(await page.evaluate(() => waits <= 1), 'Prefetch must avoid waiting after initial startup');
    assert.ok(Math.abs(await page.evaluate(() => preview.currentTime()) - duration) < 0.2);
    // Seeking backwards reloads evicted pictures instead of losing access.
    await page.evaluate(() => { preview.currentTime(2); preview.play(); });
    await page.waitForFunction(() => preview.currentTime() > 3 && preview.currentTime() < 6 && !preview.seeking());
    await page.evaluate(() => {
      preview.dispose();
      window.live = videojs('live', {preload:'none'});
      live.src({src:'/index.m3u8', type:'application/x-mpegURL'});
    });
    await page.waitForFunction(() => live.tech().vhs && live.tech().vhs.playlistController_);
    assert.ok(await page.evaluate(() => live.tech().vhs.playlistController_.goalBufferLength()) >= 30,
      'Live/DVR keeps the original buffering policy');
    assert.deepEqual(errors, []);
    console.log('PASS: Firefox original large segments, eight-second delayed prefetch without rebuffering, automatic seeks or quota recovery; backward seek and unchanged Live/DVR buffer.');
  } finally {
    if (browser) await browser.close();
    server.closeAllConnections();
    await new Promise(resolve => server.close(resolve));
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
