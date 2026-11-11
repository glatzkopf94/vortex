"""Add canonical player overlays to managed single-frame JPEG captures only."""
import os
from pathlib import Path
import re
import signal
import shutil
import subprocess
import sys
import tempfile
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

def main():
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
