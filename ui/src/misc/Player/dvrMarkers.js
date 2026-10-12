export default function attachDVRMarkers(player, source) {
const publicSourceURL=new URL(source,window.location.href);
const controller=new AbortController();
player.on('dispose',()=>controller.abort());
var progressControl = player.controlBar.progressControl;
var progressHolder = progressControl.el().querySelector(
'.vjs-progress-holder',
);
if (progressHolder) {
var markers = document.createElement('div');
markers.className = 'lc-dvr-markers';
markers.setAttribute('aria-hidden', 'true');
var clockTooltip = document.createElement('div');
clockTooltip.className = 'lc-dvr-clock-tooltip';
clockTooltip.setAttribute('aria-hidden', 'true');
progressHolder.appendChild(markers);
progressHolder.appendChild(clockTooltip);

var dvrClock = new Intl.DateTimeFormat(undefined, {
hour: '2-digit',
minute: '2-digit',
hourCycle: 'h23',
});
var clockAtEnd = null;
var lastClockRefresh = 0;
var draggingDVR = false;
var formatClock = function (milliseconds) {
return dvrClock.format(new Date(milliseconds));
};
var seekWindow = function () {
var ranges = player.seekable();
if (!ranges || !ranges.length) return null;
var start = ranges.start(0);
var end = ranges.end(ranges.length - 1);
return Number.isFinite(start) && Number.isFinite(end) &&
end > start ? { start: start, end: end } : null;
};
var renderDVRClock = function () {
var range = seekWindow();
if (!range || !Number.isFinite(clockAtEnd)) return;
var first = clockAtEnd - (range.end - range.start) * 1000;
var span = (range.end - range.start) * 1000;
var halfHour = 30 * 60 * 1000;
var ticks = document.createDocumentFragment();
var holderWidth = progressHolder.clientWidth;
var labelEvery = Math.max(1, Math.ceil(65 * span / (halfHour * Math.max(1, holderWidth))));
var index = 0;
for (var time = Math.ceil(first / halfHour) * halfHour;
time <= clockAtEnd && index < 400; time += halfHour, index++) {
var tick = document.createElement('span');
tick.className = 'lc-dvr-tick';
tick.style.left = ((time - first) / span * 100) + '%';
if (index % labelEvery === 0 && time - first > 22000 && clockAtEnd - time > 22000) {
var label = document.createElement('span');
label.className = 'lc-dvr-tick-label';
label.textContent = formatClock(time);
tick.appendChild(label);
}
ticks.appendChild(tick);
}
markers.replaceChildren(ticks);
};
var setClockFromSegments = function (segments, range) {
if (!segments || !segments.length) return false;
for (var i = segments.length - 1; i >= 0; i--) {
var segment = segments[i];
var date = segment.dateTimeObject || segment.dateTimeString;
var wallTime = date instanceof Date ? date.getTime() : Date.parse(date);
if (!Number.isFinite(wallTime)) continue;
if (Number.isFinite(segment.start)) {
clockAtEnd = wallTime + (range.end - segment.start) * 1000;
} else if (i === segments.length - 1) {
clockAtEnd = wallTime + Number(segment.duration || 0) * 1000;
} else {
var remaining = 0;
for (var j = i; j < segments.length; j++) remaining += Number(segments[j].duration || 0);
clockAtEnd = wallTime + remaining * 1000;
}
return true;
}
return false;
};
var fetchPlaylistClock = function (url, depth) {
if (depth > 1) return Promise.resolve(false);
return fetch(url, { cache: 'no-store', signal: controller.signal }).then(function (response) {
if (!response.ok) throw new Error('HLS playlist unavailable');
return response.text();
}).then(function (body) {
var lines = body.split(/\r?\n/);
var lastDate = null;
var elapsed = 0;
for (var i = 0; i < lines.length; i++) {
if (lines[i].indexOf('#EXT-X-PROGRAM-DATE-TIME:') === 0) {
lastDate = Date.parse(lines[i].slice(25));
elapsed = 0;
} else if (lines[i].indexOf('#EXTINF:') === 0 && Number.isFinite(lastDate)) {
elapsed += parseFloat(lines[i].slice(8)) * 1000;
}
}
if (Number.isFinite(lastDate)) {
clockAtEnd = lastDate + elapsed;
return true;
}
var variant = lines.find(function (line) {
return line && line.charAt(0) !== '#';
});
return variant ? fetchPlaylistClock(new URL(variant, url).toString(), depth + 1) : false;
}).catch(function () { return false; });
};
var updateDVRClock = function () {
var range = seekWindow();
if (!range) return;
var tech = player.tech && player.tech(true);
var playlist = tech && tech.vhs && tech.vhs.playlists && tech.vhs.playlists.media();
if (playlist && setClockFromSegments(playlist.segments, range)) {
renderDVRClock();
return;
}
fetchPlaylistClock(publicSourceURL.toString(), 0).then(function (found) {
if (found && !player.isDisposed()) renderDVRClock();
});
};
var refreshDVRClock = function () {
if (Date.now() - lastClockRefresh < 15000) return;
lastClockRefresh = Date.now();
updateDVRClock();
};
var showClockAtPointer = function (event) {
var range = seekWindow();
if (!range || !Number.isFinite(clockAtEnd)) return;
var bounds = progressHolder.getBoundingClientRect();
if (!bounds.width) return;
var fraction = Math.min(1, Math.max(0, (event.clientX - bounds.left) / bounds.width));
clockTooltip.style.left = (fraction * 100) + '%';
clockTooltip.textContent = formatClock(clockAtEnd - (1 - fraction) * (range.end - range.start) * 1000);
clockTooltip.classList.add('is-visible');
};
progressHolder.addEventListener('pointermove', showClockAtPointer);
progressHolder.addEventListener('pointerdown', function (event) {
draggingDVR = true;
showClockAtPointer(event);
});
progressHolder.addEventListener('pointerleave', function () {
if (!draggingDVR) clockTooltip.classList.remove('is-visible');
});
var onDragMove = function (event) {
if (draggingDVR) showClockAtPointer(event);
};
var onDragEnd = function () {
draggingDVR = false;
clockTooltip.classList.remove('is-visible');
};
window.addEventListener('pointermove', onDragMove);
window.addEventListener('pointerup', onDragEnd);
window.addEventListener('pointercancel', onDragEnd);
player.on('dispose', function () {
window.removeEventListener('pointermove', onDragMove);
window.removeEventListener('pointerup', onDragEnd);
window.removeEventListener('pointercancel', onDragEnd);
});
player.on('progress', refreshDVRClock);
player.on('timeupdate', refreshDVRClock);
player.on('loadedmetadata', updateDVRClock);
player.on('durationchange', updateDVRClock);
player.on('playerresize', renderDVRClock);
updateDVRClock();
}
}
