#!/usr/bin/env python3
"""Real HEVC copy -> fMP4 HLS -> optional reduced AVC chain; no camera required."""
import subprocess, tempfile, re
from pathlib import Path

help_text=subprocess.run(['ffmpeg','-hide_banner','-h','full'],capture_output=True).stdout
progress_options=['-nojsonstats'] if re.search(rb'(?m)^-jsonstats\s', help_text) else []

def run(*args):
    p=subprocess.run(['ffmpeg',*progress_options,'-hide_banner','-loglevel','error',*args],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    if p.returncode: raise AssertionError(p.stderr.decode(errors='replace'))
    return p.stdout

with tempfile.TemporaryDirectory() as d:
    root=Path(d); original=root/'original.mp4'; main=root/'main.m3u8'; sub=root/'fallback.m3u8'
    run('-f','lavfi','-i','testsrc2=size=960x540:rate=25','-t','6','-an','-c:v','libx265','-preset','ultrafast','-x265-params','pools=1:frame-threads=1:keyint=50:log-level=error','-tag:v','hvc1',str(original))
    run('-i',str(original),'-map','0:v:0','-c:v','copy','-tag:v','hvc1','-b:v','8192k','-f','hls','-hls_time','2','-hls_list_size','0','-hls_segment_type','fmp4','-hls_fmp4_init_filename','init.mp4','-master_pl_name','master.m3u8',str(main))
    assert '#EXT-X-MAP:' in main.read_text()
    assert '#EXT-X-STREAM-INF:' in (root/'master.m3u8').read_text(), 'Empty master playlist'
    before=run('-i',str(original),'-map','0:v:0','-f','framemd5','-')
    after=run('-i',str(main),'-map','0:v:0','-f','framemd5','-')
    def hashes(data):return [line.split(b',')[-1].strip() for line in data.splitlines() if not line.startswith(b'#')]
    assert hashes(before)==hashes(after), 'HEVC pass-through changed video frames'
    run('-i',str(main),'-map','0:v:0','-map','0:a:0?','-c:v','libx264','-preset','veryfast','-threads','2','-vf',r'scale=-2:min(ih\,360)','-b:v','768k','-maxrate','768k','-bufsize','1536k','-r','25','-g','50','-pix_fmt','yuv420p','-c:a','aac','-f','hls','-hls_time','2','-hls_list_size','0',str(sub))
    run('-i',str(sub),'-f','null','-')
    probe=subprocess.run(['ffmpeg',*progress_options,'-hide_banner','-i',str(sub)],capture_output=True).stderr.decode()
    assert 'h264' in probe and '640x360' in probe,probe
    print('HEVC fMP4 passthrough: identical decoded frames; H.264 fallback 640x360: OK')
