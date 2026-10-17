#!/bin/sh

set -eu

project_dir="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$project_dir"
. ./release.env

container="$(docker compose -f compose.yaml ps -q restreamer-nkl)"
if [ -z "$container" ]; then
    echo "Smoke-Test: Container laeuft nicht." >&2
    exit 1
fi

docker exec "$container" ffmpeg -hide_banner -filters 2>/dev/null | grep -Eq '[[:space:]]fps[[:space:]]'
docker exec "$container" ffmpeg -hide_banner -filters 2>/dev/null | grep -Eq '[[:space:]]drawtext[[:space:]]'
docker exec "$container" ffmpeg -hide_banner -filters 2>/dev/null | grep -Eq '[[:space:]]overlay[[:space:]]'
docker exec "$container" ffmpeg -hide_banner -filters 2>/dev/null | grep -Eq '[[:space:]]movie[[:space:]]'
docker exec "$container" python3 --version >/dev/null
docker exec "$container" python3 -c 'import json, urllib.request' >/dev/null
docker exec "$container" test -x /core/bin/livechasing-manager.py
docker exec "$container" test -x /core/bin/migrate-timestamp-repair.py
docker exec "$container" test -x /core/bin/migrate-player-1.4.py
docker exec "$container" test -x /core/bin/migrate-dvr-retention.py
docker exec "$container" ffmpeg -hide_banner -h muxer=hls 2>&1 | grep -q hls_max_window_duration
docker exec "$container" sh -c 'grep -Fq "lc-dvr-markers" /core/ui/_player/videojs/player.html'
docker exec "$container" sh -c "ps auxww | grep '[l]ivechasing-manager.py'" >/dev/null
docker exec "$container" sh -c 'grep -Fq "def purge_dvr_content" /core/bin/livechasing-manager.py'
docker exec "$container" python3 -c 'from urllib.request import urlopen; import json; s=json.load(urlopen("http://127.0.0.1:8099/admin/status", timeout=10)); assert "projects" in s'
# Exercise the production time-lapse renderer and patched FFmpeg in private temp data.
docker exec -i "$container" python3 - <<'PYTL'
import sys,tempfile,json,subprocess
from pathlib import Path
sys.path.insert(0,'/core/bin/timelapse')
from service import Service,DEFAULT
with tempfile.TemporaryDirectory() as tmp:
    root=Path(tmp);channel='00000000-0000-0000-0000-000000000001'
    db=root/'db.json';db.write_text(json.dumps({'metadata':{'process':{'restreamer-ui:ingest:'+channel:{'restreamer-ui':{'meta':{'name':'Smoke'}}}}}}))
    service=Service(root/'state',db,root/'data',min_free=0,quota=1024**3)
    try:
        service.configure(channel,{**DEFAULT,'mode':'season'})
        pid=service.action({'action':'start','channel':channel})['id']
        folder=service.root/pid;folder.mkdir(exist_ok=True)
        subprocess.run(['ffmpeg','-hide_banner','-v','error','-f','lavfi','-i','testsrc2=size=320x240:rate=25','-frames:v','30','-threads','1',str(folder/'%06d.jpg')],check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        for i in range(1,31):
            f=folder/f'{i:06d}.jpg';service.write('INSERT INTO frames VALUES(?,?,?,?)',(pid,i,str(f),f.stat().st_size))
        service.action({'action':'export','project':pid})
        service.render(service.rows('SELECT * FROM projects WHERE id=?',(pid,))[0])
        p=service.rows('SELECT * FROM projects WHERE id=?',(pid,))[0]
        assert not p['error'],p['error']
        assert service.rows('SELECT SUM(frames) AS n FROM segments WHERE project=?',(pid,))[0]['n']==30
        assert (folder/'export.mp4').is_file()
        subprocess.run(['ffmpeg','-v','error','-i',str(folder/'segment-000000.ts'),'-f','null','-'],check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        service.render_quality(p)
        service.render_quality(p)
        error=service.rows('SELECT error FROM projects WHERE id=?',(pid,))[0]['error']
        assert not error,error
        assert all(q['ready'] for q in service.qualities(pid)),service.qualities(pid)
        for height in (1080,720):
            subprocess.run(['ffmpeg','-v','error','-i',str(folder/f'quality-{height}-segment-000000.ts'),'-f','null','-'],check=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        print('Production time-lapse preview, MP4 and quality renditions: OK')
    finally:service.close()
PYTL
docker inspect "$container" --format '{{range .Mounts}}{{println .Destination}}{{end}}' | grep -Fxq /core/timelapse
docker exec "$container" test -d /core/data/livechasing-control/requests
docker exec "$container" test -d /core/data/livechasing-control/responses
docker exec "$container" sh -c 'test "$CORE_STORAGE_DISK_CACHE_TYPES_BLOCK" = ".m3u8 .mpd .txt .html .js"'
docker exec "$container" sh -c 'grep -Fq "local-draft-v2" /core/ui/static/js/main.*.js'
docker exec "$container" sh -c 'grep -Fq "overlay-assistant-v2-player" /core/ui/static/js/main.*.js'
docker exec "$container" sh -c 'grep -Fq "overlay-assistant-v2-burnin" /core/ui/static/js/main.*.js'
docker exec "$container" sh -c 'grep -Fq "RTSP stability profile" /core/ui/static/js/main.*.js'
docker exec "$container" sh -c 'grep -Fq "lc-position-top-center" /core/ui/_player/videojs/player.html'
docker exec "$container" sh -c 'grep -Fq "lc-position-bottom-center" /core/ui/_player/videojs/player.html'
docker exec "$container" sh -c 'grep -Fq "window.setTimeout(refreshOverlayText, 5000)" /core/ui/_player/videojs/player.html'
docker exec "$container" sh -c 'grep -Fq "var safeStart = first + dvrSegmentDuration * 2" /core/ui/_player/videojs/player.html'
docker exec "$container" sh -c 'grep -Fq "livechasing-active-player-v1" /core/ui/_player/videojs/player.html'
docker exec "$container" sh -c 'grep -Fq "player.hasStarted(false)" /core/ui/_player/videojs/player.html'
docker exec "$container" sh -c 'grep -Fq "playbackLimitMilliseconds" /core/ui/_player/videojs/player.html'
docker exec "$container" sh -c 'grep -Fq "playbackActivationPending" /core/ui/_player/videojs/player.html'
docker exec "$container" sh -c 'grep -Fq "updatePlayerOverlayLayout" /core/ui/_player/videojs/player.html'
docker exec "$container" sh -c 'grep -Fq "vjs-live-no-dvr" /core/ui/_player/videojs/player.html'
docker exec "$container" sh -c 'grep -Fq -- "--lc-player-ratio" /core/ui/_player/videojs/player.html'
docker exec "$container" sh -c 'grep -Fq "Automatically detect 16:9 or 4:3" /core/ui/static/js/main.*.js'
docker exec "$container" sh -c 'grep -Fq "Delete all DVR content" /core/ui/static/js/main.*.js'
docker exec "$container" sh -c 'grep -Fq "install-latest-nkl-release" /core/ui/static/js/main.*.js'
docker exec "$container" sh -c 'test "$NKL_RELEASE_VERSION" = "'"$RELEASE_VERSION"'"'
docker exec "$container" sh -c 'grep -Fq "livechasing-viewer-id-v1" /core/ui/_player/videojs/player.html'
docker exec "$container" sh -c 'ls /core/ui/static/media/vortex-background.*.jpg >/dev/null'

docker exec -i "$container" python3 - <<'PY'
from pathlib import Path
from urllib.request import Request, urlopen

page = Path('/core/data/nkl-cache-smoke.html')
page.write_text('<html>current player</html>')
try:
    for method in ('GET', 'HEAD'):
        request = Request('http://127.0.0.1:8080/nkl-cache-smoke.html', method=method,
                          headers={'If-None-Match': 'old', 'If-Modified-Since': 'Wed, 23 Sep 2026 12:00:00 GMT'})
        with urlopen(request, timeout=10) as response:
            assert response.status == 200
            assert 'no-store' in response.headers.get('Cache-Control', '')
            assert response.headers.get('Pragma') == 'no-cache'
finally:
    page.unlink(missing_ok=True)
PY

# Segments are intentionally three times longer than the requested hls_time.
# The playlist must retain 12 seconds of actual video, not twelve seconds
# worth of nominal two-second segment counts.
docker exec -i "$container" sh -ec '
    mkdir -p /tmp/nkl-dvr-window-smoke
    trap "rm -rf /tmp/nkl-dvr-window-smoke" EXIT
    ffmpeg -hide_banner -loglevel error -f lavfi -i testsrc2=size=160x90:rate=5 \
      -t 40 -c:v libx264 -preset ultrafast -g 30 -keyint_min 30 -sc_threshold 0 \
      -f hls -hls_time 2 -hls_list_size 100 \
      -hls_flags delete_segments \
      -hls_segment_filename /tmp/nkl-dvr-window-smoke/seg%03d.ts \
      /tmp/nkl-dvr-window-smoke/stream.m3u8
    ffmpeg -hide_banner -loglevel error -f lavfi -i testsrc2=size=160x90:rate=5 \
      -t 12 -c:v libx264 -preset ultrafast -g 30 -keyint_min 30 -sc_threshold 0 \
      -f hls -hls_time 2 -hls_list_size 100 -hls_max_window_duration 12 \
      -hls_flags append_list+delete_segments+discont_start \
      -hls_segment_filename /tmp/nkl-dvr-window-smoke/seg%03d.ts \
      /tmp/nkl-dvr-window-smoke/stream.m3u8
    ffmpeg -hide_banner -loglevel error -i /tmp/nkl-dvr-window-smoke/stream.m3u8 -map 0:v:0 -f null -
    python3 - <<"PY"
from pathlib import Path
import re

root = Path("/tmp/nkl-dvr-window-smoke")
playlist = (root / "stream.m3u8").read_text()
durations = [float(value) for value in re.findall(r"#EXTINF:([0-9.]+)", playlist)]
assert durations and sum(durations) <= 12.01, durations
assert len(durations) <= 2, durations
assert len(list(root.glob("seg*.ts"))) < 7
PY
'

dvr_control_id='00000000-0000-4000-8000-000000000009'
dvr_control_request="/core/data/livechasing-control/requests/$dvr_control_id.json"
dvr_control_response="/core/data/livechasing-control/responses/$dvr_control_id.json"
docker exec "$container" rm -f "$dvr_control_request" "$dvr_control_response"
printf '{"version":1,"action":"purge-dvr","requestId":"%s","channelIds":[]}\n' "$dvr_control_id" | \
    docker exec -i "$container" sh -c "cat > '$dvr_control_request'"
dvr_control_ready=false
for _ in 1 2 3 4 5 6 7 8 9 10; do
    if docker exec "$container" test -f "$dvr_control_response"; then
        dvr_control_ready=true
        break
    fi
    sleep 1
done
test "$dvr_control_ready" = true
docker exec "$container" python3 -c "import json; data=json.load(open('$dvr_control_response')); assert data['ok'] is True and data['deletedFiles'] == 0"
docker exec "$container" rm -f "$dvr_control_request" "$dvr_control_response"
for font in \
    /usr/share/fonts/truetype/dejavu/DejaVuSans.ttf \
    /usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf \
    /usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf \
    /usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf; do
    docker exec "$container" test -r "$font"
done

docker exec "$container" ffmpeg -hide_banner -formats 2>/dev/null | \
    grep -Eq '^[[:space:]]*D[E[:space:]][[:space:]]+rtsp[[:space:]]'
docker exec "$container" ffmpeg -hide_banner -h demuxer=rtsp 2>&1 | grep -q -- '-buffer_size'
docker exec "$container" ffmpeg -hide_banner -h full 2>&1 | grep -q -- '-max_delay'
docker exec "$container" ffmpeg -hide_banner -h full 2>&1 | grep -q -- '-err_detect'
docker exec "$container" ffmpeg -hide_banner -h full 2>&1 | grep -q -- '-xerror'

jsonstats="$(docker exec "$container" ffmpeg \
    -hide_banner -loglevel level+info -stats_period 0.5 -jsonstats \
    -f lavfi -i 'testsrc2=size=320x180:rate=15' \
    -t 2 -codec:v libx264 -preset ultrafast -f null - 2>&1)"

printf '%s\n' "$jsonstats" | grep -q '^ffmpeg.inputs:'
printf '%s\n' "$jsonstats" | grep -q '^ffmpeg.outputs:'
printf '%s\n' "$jsonstats" | grep -q '^ffmpeg.progress:'

smoke_textfile='/core/data/overlays/.restreamer-smoke-test.txt'
smoke_logo='/core/data/overlays/.restreamer-smoke-test.bmp'
cleanup() {
    docker exec "$container" rm -f "$smoke_textfile" "$smoke_logo" >/dev/null 2>&1 || true
}
trap cleanup EXIT HUP INT TERM

printf 'Temp: 21.5 °C   F: 48 %%\n' | \
    docker exec -i "$container" sh -c "mkdir -p /core/data/overlays && cat > '$smoke_textfile'"

docker exec "$container" ffmpeg \
    -hide_banner -loglevel error \
    -f lavfi -i 'color=c=0x32AAFF:size=160x80' \
    -frames:v 1 "$smoke_logo"

docker exec "$container" ffmpeg \
    -hide_banner -loglevel error \
    -f lavfi -i 'testsrc2=size=1280x720:rate=15' \
    -t 2 \
    -filter_complex "[0:v]fps=fps=15:start_time=0:round=near[base];movie=filename='$smoke_logo',format=rgba,colorchannelmixer=aa=0.80[logo];[base][logo]overlay=x=W-w-24:y=24[tmp];[tmp]drawtext=textfile='$smoke_textfile':reload=15:expansion=none:fontfile='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf':fontcolor=0x32AAFF:fontsize=36:x=24:y=h-th-24[out]" \
    -map '[out]' \
    -codec:v libx264 -preset ultrafast \
    -f null -

cleanup
trap - EXIT HUP INT TERM

av_smoke='/tmp/nkl-cfr-av-smoke.ts'
docker exec "$container" rm -f "$av_smoke"
docker exec "$container" ffmpeg \
    -hide_banner -loglevel error \
    -f lavfi -i 'testsrc2=size=160x90:rate=149654/10000' \
    -f lavfi -i 'sine=frequency=1000:sample_rate=48000' \
    -t 12 \
    -filter:v 'fps=fps=15:start_time=0:round=near' \
    -codec:v libx264 -preset ultrafast -g 30 -keyint_min 30 -sc_threshold 0 \
    -codec:a aac -b:a 64k \
    -f mpegts "$av_smoke"

docker exec -i "$container" python3 - "$av_smoke" <<'PY'
import re
import subprocess
import sys

path = sys.argv[1]

result = subprocess.run([
    'ffmpeg', '-hide_banner', '-loglevel', 'info', '-debug_ts', '-i', path,
    '-map', '0:v:0', '-map', '0:a:0', '-codec', 'copy', '-f', 'null', '-',
], text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
packet = re.compile(
    r'demuxer\+ffmpeg -> .*?type:(video|audio) .*?pkt_pts_time:([-0-9.]+) '
    r'.*?duration_time:([-0-9.]+)'
)
streams = {'video': [], 'audio': []}
for kind, pts, duration in packet.findall(result.stderr):
    streams[kind].append((float(pts), float(duration)))

def packet_times(kind):
    packets = streams[kind]
    times = [pts for pts, _ in packets]
    assert times and all(right > left for left, right in zip(times, times[1:])), kind
    return times[0], max(pts + duration for pts, duration in packets), len(times)

video_start, video_end, video_packets = packet_times('video')
audio_start, audio_end, _ = packet_times('audio')
assert abs(video_packets / 12.0 - 15.0) < 0.2
assert min(video_end, audio_end) - max(video_start, audio_start) > 11.8
assert abs(video_end - audio_end) < 0.15
PY
docker exec "$container" rm -f "$av_smoke"

echo "Smoke-Test erfolgreich: adaptive Player-Geometrie, Bandbreitenschutz, RTSP-Profile, schnelle Player-Overlays, DVR-Schutz, zeitbasierte CFR-Reparatur, A/V-Ueberlappung, Drawtext, Logo-Overlay, Manager und libx264 funktionieren."
