const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const {hevcCodecFromSampleEntry: codec} = require('./hevc-codec.cjs');
const {patchSource} = require('./patch-hevc.cjs');
const probe = require('mux.js/lib/mp4/probe');

function box(type, data, extended = false) {
  const header = Buffer.alloc(extended ? 16 : 8);
  header.writeUInt32BE(extended ? 1 : data.length + 8);
  header.write(type, 4);
  if (extended) header.writeUInt32BE(data.length + 16, 12);
  return Buffer.concat([header, data]);
}
function config(profile = 1, compatibility = 0x60000000, level = 153, constraints = [0xb0]) {
  const data = Buffer.alloc(23);
  data[0] = 1; data[1] = profile;
  data.writeUInt32BE(compatibility, 2); data[12] = level;
  constraints.forEach((v, i) => { data[6 + i] = v; });
  return data;
}
function entry(data, prefix = Buffer.alloc(0), extended = false) {
  return Buffer.concat([Buffer.alloc(78), prefix, box('hvcC', data, extended)]);
}
function init(type, data) {
  const hdlr = Buffer.alloc(12); hdlr.write('vide', 8);
  return box('moov', box('trak', box('mdia', Buffer.concat([
    box('hdlr', hdlr), box('minf', box('stbl', box('stsd', Buffer.concat([
      Buffer.from([0,0,0,0,0,0,0,1]), box(type, data)
    ]))))
  ]))));
}

test('Main and Main10 use actual configuration, not a fixed level', () => {
  assert.equal(codec('hvc1', entry(config())), 'hvc1.1.6.L153.B0');
  assert.equal(codec('hev1', entry(config(2, 0x20000000, 120, [0x90]))), 'hev1.2.4.L120.90');
  assert.equal(codec('hvc1', entry(config(0x63, 0x80000001, 186, [0,0,0x10]))), 'hvc1.A3.80000001.H186.00.00.10');
  assert.equal(codec('hvc1', entry(config(0xc4, 0, 93, []))), 'hvc1.C4.0.L93');
});
test('child box order, extended headers and size-to-end are supported', () => {
  assert.equal(codec('hvc1', entry(config(), box('pasp', Buffer.alloc(8)), true)), 'hvc1.1.6.L153.B0');
  const data = entry(config()); data.writeUInt32BE(0, 78);
  assert.equal(codec('hvc1', data), 'hvc1.1.6.L153.B0');
});
test('bad headers and truncated NAL arrays cannot create a guessed codec', () => {
  for (const data of [Buffer.alloc(85), entry(Buffer.alloc(22)), entry(Buffer.alloc(23))])
    assert.equal(codec('hvc1', data), 'hvc1');
  const badSize = entry(config()); badSize.writeUInt32BE(0xffffffff, 78);
  assert.equal(codec('hvc1', badSize), 'hvc1');
  const nal = config(); nal[22] = 1;
  assert.equal(codec('hvc1', entry(nal)), 'hvc1');
  const valid = Buffer.concat([nal, Buffer.from([0xa0,0,1,0,2,0x40,1])]);
  assert.equal(codec('hvc1', entry(valid)), 'hvc1.1.6.L153.B0');
  assert.equal(codec('hvc1', entry(valid.subarray(0, valid.length-1))), 'hvc1');
  assert.equal(codec('Opus', entry(config())), 'Opus');
});
test('actual mux.js init probing returns complete hvc1 and hev1 strings', () => {
  for (const type of ['hvc1', 'hev1']) {
    const track = probe.tracks(init(type, entry(config())))[0];
    assert.equal(track.type, 'video');
    assert.equal(track.codec, type + '.1.6.L153.B0');
  }
  const avc = Buffer.concat([Buffer.alloc(78), box('avcC', Buffer.from([1,0x64,0,0x28]))]);
  assert.equal(probe.tracks(init('avc1', avc))[0].codec, 'avc1.640028');
});
test('patch is idempotent and rejects unrecognized upstream source', () => {
  const source = '// flac, opus, etc\ntrack.codec = track.codec.toLowerCase();';
  const patched = patchSource(source);
  assert.equal(patchSource(patched), patched);
  assert.throws(() => patchSource('other source'), /expected exactly one/);
  assert.throws(() => patchSource(source + '\n' + source), /expected exactly one/);
  const context = {track: {codec:'hvc1'}, codecBox:entry(config())};
  vm.runInNewContext(patched, context);
  assert.equal(context.track.codec, 'hvc1.1.6.L153.B0');
});
test('all Video.js distributions contain the same self-contained worker parser', () => {
  for (const name of ['video.cjs.js', 'video.es.js', 'video.js']) {
    const source = fs.readFileSync(path.join(__dirname, '../node_modules/video.js/dist', name), 'utf8');
    assert.ok(source.includes(codec.toString()), name);
  }
});
