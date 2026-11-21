"""Add canonical player overlays to managed single-frame JPEG captures only."""
import os
from pathlib import Path
import re
import signal
import shutil
import subprocess
import sys
import tempfile
import time
from urllib.parse import urlsplit
from player_overlay import capture_filter

REAL = '/usr/bin/ffmpeg-vortex-real'
UUID = r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}'

def snapshot_channel(args):
    # Never touch live encoders, publication outputs, or timelapse captures.
    if len(args) < 2 or any(x in args for x in ('-vf','-filter:v','-filter_complex','-filter_complex_script')):
        return None
    def value(flag):
        return args[args.index(flag)+1] if flag in args and args.index(flag)+1<len(args) else None
    if value('-vframes') != '1' or value('-f') != 'image2' or value('-update') != '1' or args.count('-i') != 1:
        return None
    target=urlsplit(args[-1])
    if target.scheme not in ('http','https') or target.hostname not in ('localhost','127.0.0.1','::1'):
        return None
    match=re.fullmatch(r'/memfs/('+UUID+r')\.jpg',target.path)
    if not match: return None
    channel=match[1]
    if Path(urlsplit(value('-i') or '').path).name != channel+'.m3u8': return None
    return channel

def repair_dvr(args, root, now):
    """Keep a playable suffix with stable HLS sequence numbers at writer startup."""
    target = args[-1]
    if target.startswith('['):
        options, sep, target = target.partition(']')
        match = re.search(r'[:\[]hls_max_window_duration=(\d+)(?=:|$)', options)
        if not sep or not match or 'append_list' not in options:
            return
        target = target.split('|', 1)[0]
        window = int(match[1])
    else:
        if '-hls_max_window_duration' not in args or '-hls_flags' not in args:
            return
        if 'append_list' not in args[args.index('-hls_flags') + 1].split('+'):
            return
        window = int(args[args.index('-hls_max_window_duration') + 1])
    path = Path(target)
    if window <= 0 or path.parent != root or path.suffix != '.m3u8' or not path.is_file():
        return
    lines = path.read_text().splitlines()
    if not lines or lines[0] != '#EXTM3U':
        return
    entries = []
    for i, line in enumerate(lines):
        if line and not line.startswith('#'):
            segment = path.parent / line
            if not segment.stem.isdecimal() or root not in segment.parents:
                return
            entries.append((i, segment))
    cut = 0
    for count, (_, segment) in enumerate(entries, 1):
        if int(segment.stem) < now - window or not segment.is_file():
            cut = count
    if not cut:
        return
    end = entries[cut - 1][0] + 1
    header = []
    active = {}
    discontinuities = 0
    sequence = None
    for line in lines[:end]:
        if line.startswith('#EXT-X-MEDIA-SEQUENCE:'):
            sequence = int(line.split(':')[1])
        elif line == '#EXT-X-DISCONTINUITY':
            discontinuities += 1
        elif line.startswith('#EXT-X-DISCONTINUITY-SEQUENCE:'):
            discontinuities += int(line.split(':')[1])
        elif line.startswith(('#EXT-X-MAP:', '#EXT-X-KEY:')):
            active[line.split(':')[0]] = line
        elif line.startswith(('#EXT-X-VERSION:', '#EXT-X-TARGETDURATION:', '#EXT-X-INDEPENDENT-SEGMENTS')) or line == '#EXTM3U':
            header.append(line)
    header.append(f'#EXT-X-MEDIA-SEQUENCE:{(sequence or 0) + cut}')
    if discontinuities:
        header.append(f'#EXT-X-DISCONTINUITY-SEQUENCE:{discontinuities}')
    if cut < len(entries):
        header.extend(active.values())
    with tempfile.NamedTemporaryFile(mode='w', dir=root, delete=False) as tmp:
        replacement = Path(tmp.name)
        try:
            tmp.write('\n'.join(header + lines[end:]) + '\n')
            tmp.flush()
            os.fchmod(tmp.fileno(), path.stat().st_mode & 0o777)
            os.replace(replacement, path)
        finally:
            replacement.unlink(missing_ok=True)


def main():
    if sys.argv[1:2] == ['--dvr-start']:
        args = sys.argv[2:]
        repair_dvr(args, Path(os.environ.get('CORE_STORAGE_DISK_DIR', '/core/data')), time.time())
        os.execv(REAL, [REAL, *args])
    args=sys.argv[1:];channel=snapshot_channel(args)
    if channel is None: os.execv(REAL,[REAL,*args])
    with tempfile.TemporaryDirectory(prefix='vortex-preview-',dir='/tmp') as tmp:
        try:
            graph=capture_filter(Path(os.environ.get('CORE_DB_DIR','/core/config'))/'db.json',
                os.environ.get('CORE_STORAGE_DISK_DIR','/core/data'),channel,None,None,'null',Path(tmp)/'text.txt')
        except (OSError,ValueError,TypeError,KeyError) as error:
            # Keep thumbnail generation available; never print credentials/metadata.
            print('Vortex preview: overlay unavailable ('+type(error).__name__+'); capturing plain image',file=sys.stderr)
            graph=None
        if graph is None:
            shutil.rmtree(tmp)
            os.execv(REAL,[REAL,*args])
        # Pass as one argv element, never through a shell. Compatible with FFmpeg 9.
        args[-1:-1]=['-filter_complex',graph,'-map','[tlout]']
        child=subprocess.Popen([REAL,*args])
        def forward(signum,frame):
            if child.poll() is None: child.send_signal(signum)
        for sig in (signal.SIGTERM,signal.SIGINT,signal.SIGHUP): signal.signal(sig,forward)
        return child.wait()

if __name__=='__main__': sys.exit(main())
