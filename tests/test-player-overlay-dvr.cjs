// Execute the actual public-player visibility gate, not a copied implementation.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const html = fs.readFileSync('ui/public/_player/videojs/player.html', 'utf8');
const code = html.split('// BEGIN DVR OVERLAY WINDOW')[1].split('// END DVR OVERLAY WINDOW')[0];
function setup(minutes, dvr = true) {
  const events = {}, documentEvents = {}, timers = new Map();
  const state = {now: 1000, position: 7194, start: 0, edge: 7200, available: true};
  const root = {style: {}};
  const player = {
    on(name, fn) { (events[name] ||= []).push(fn); },
    seekable: () => ({length: state.available ? 1 : 0, start: () => state.start, end: () => state.edge}),
    currentTime: () => state.position,
  };
  vm.runInNewContext(code, {
    player, playerConfig: {dvr: {enabled: dvr}}, playerOverlay: {dvrWindowMinutes: minutes}, overlayRoot: root,
    Date: {now: () => state.now},
    document: {addEventListener: (name, fn) => documentEvents[name] = fn, removeEventListener: name => delete documentEvents[name]},
    window: {setInterval: fn => {timers.set(1,fn);return 1;}, clearInterval: id => timers.delete(id)},
  });
  return {state,root,timers,documentEvents,emit: name => (events[name] || []).forEach(fn=>fn()), tick:()=>timers.forEach(fn=>fn())};
}
const a = setup();
assert.equal(a.root.style.display, 'block');
a.state.position = 6900; a.emit('seeking'); assert.equal(a.root.style.display, 'block');
a.state.position = 6899.9; a.emit('seeking'); assert.equal(a.root.style.display, 'none');
a.state.position = 3600; a.emit('seeked'); assert.equal(a.root.style.display, 'none');
a.state.position = 7194; a.emit('seeking'); assert.equal(a.root.style.display, 'block');
// Paused media and frozen playlist age out even without timeupdate/progress events.
a.emit('pause');a.state.now += 301000;a.tick();assert.equal(a.root.style.display,'none');
// Moving live window; current measurements must not overlay old paused frames.
a.state.edge += 302;a.emit('progress');assert.equal(a.root.style.display,'none');
a.state.position = a.state.edge - 6;a.emit('timeupdate');assert.equal(a.root.style.display,'block');
a.state.now += 301000;a.documentEvents.visibilitychange();assert.equal(a.root.style.display,'none');
// No seekable window or invalid data fail closed, then recover after metadata.
a.state.available=false;a.emit('loadedmetadata');assert.equal(a.root.style.display,'none');
a.state.available=true;a.state.edge=100;a.state.position=94;a.emit('emptied');assert.equal(a.root.style.display,'none');
a.emit('loadedmetadata');assert.equal(a.root.style.display,'block');
a.state.position=NaN;a.tick();assert.equal(a.root.style.display,'none');
a.state.position=-2;a.tick();assert.equal(a.root.style.display,'none');
a.state.position=200;a.tick();assert.equal(a.root.style.display,'none');
a.emit('dispose');assert.equal(a.timers.size,0);assert.equal(Object.keys(a.documentEvents).length,0);
const b=setup('10');b.state.position=6600;b.emit('seeking');assert.equal(b.root.style.display,'block');
b.state.position=6599;b.emit('seeking');assert.equal(b.root.style.display,'none');
for (const invalid of [null,0,-1,'bogus',Infinity,1000]) {
 const p=setup(invalid);p.state.position=6899;p.emit('seeking');assert.equal(p.root.style.display,'none');
}
const live=setup(5,false);live.state.available=false;live.tick();assert.equal(live.root.style.display,'block');
console.log('DVR player overlay: boundaries, channel windows, seeking, pause, background, rollover, invalid state and cleanup passed');
