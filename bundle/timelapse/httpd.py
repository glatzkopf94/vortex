#!/usr/bin/env python3
"""Loopback-only HTTP adapter. Do not expose this port directly."""
import json
import os
from pathlib import Path
import re
import signal
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit
from service import Service, UUID


def make_handler(service):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args): pass
        def reply(self,status,data,mime='application/json'):
            if not isinstance(data,bytes): data=json.dumps(data,ensure_ascii=False).encode()
            self.send_response(status); self.send_header('Content-Type',mime); self.send_header('Cache-Control','no-store')
            self.send_header('X-Content-Type-Options','nosniff'); self.send_header('Content-Length',str(len(data))); self.end_headers()
            if self.command!='HEAD': self.wfile.write(data)
        def do_POST(self):
            if self.path!='/admin/action': return self.reply(404,{'message':'Not found'})
            try:
                size=int(self.headers.get('Content-Length','0'))
                if not 0<size<=16384: return self.reply(413,{'message':'Request too large'})
                request=json.loads(self.rfile.read(size))
                with service.lock: result=service.action(request)
                self.reply(200,result)
            except (ValueError,KeyError,TypeError) as e: self.reply(400,{'message':str(e)})
        def do_HEAD(self): self.do_GET()
        def do_GET(self):
            path=urlsplit(self.path).path
            try:
                if path=='/admin/status': return self.reply(200,service.status())
                if path=='/public/player.js': return self.reply(200,(Path(__file__).parent/'player.js').read_bytes(),'application/javascript')
                if path=='/public/player.css': return self.reply(200,(Path(__file__).parent/'player.css').read_bytes(),'text/css')
                match=re.fullmatch(r'/public/channel/([^/]+)/availability',path)
                if match:
                    if not UUID.fullmatch(match[1]): return self.reply(404,{'message':'Not found'})
                    return self.reply(200,{'active':service.channel_active(match[1])})
                match=re.fullmatch(r'/public/channel/([^/]+)',path)
                if match:
                    if not UUID.fullmatch(match[1]): return self.reply(404,{'message':'Not found'})
                    return self.reply(200,service.status(match[1],public=True))
                match=re.fullmatch(r'/(admin|public)/project/([^/]+)/(index\.m3u8|segment-\d{6}\.ts|export\.mp4|poster\.jpg|timeline\.json)',path)
                if not match or not UUID.fullmatch(match[2]): return self.reply(404,{'message':'Not found'})
                access,pid,filename=match.groups()
                projects=service.rows('SELECT * FROM projects WHERE id=?',(pid,))
                if not projects or (access=='public' and (not service.channel_active(projects[0]['channel']) or not json.loads(projects[0]['settings'])['public'])): return self.reply(404,{'message':'Not found'})
                p=projects[0]; s=json.loads(p['settings'])
                if filename=='timeline.json': return self.reply(200,service.timeline(p))
                if filename=='index.m3u8':
                    segments=service.rows('SELECT * FROM segments WHERE project=? ORDER BY number',(pid,))
                    if not segments: return self.reply(404,{'message':'Vorschau wird vorbereitet'})
                    durations=[max(0.04,x['frames']/s['fps']) for x in segments]
                    import math
                    text='#EXTM3U\n#EXT-X-VERSION:3\n#EXT-X-PLAYLIST-TYPE:VOD\n#EXT-X-TARGETDURATION:'+str(max(1,math.ceil(max(durations))))+'\n#EXT-X-MEDIA-SEQUENCE:0\n'
                    for index,(segment,duration) in enumerate(zip(segments,durations)):
                        if index: text+='#EXT-X-DISCONTINUITY\n'
                        text+=f'#EXTINF:{duration:.6f},\nsegment-{segment["number"]:06d}.ts\n'
                    return self.reply(200,(text+'#EXT-X-ENDLIST\n').encode(),'application/vnd.apple.mpegurl')
                if filename=='export.mp4' and access!='admin': return self.reply(404,{'message':'Not found'})
                file=service.root/pid/filename
                if filename=='export.mp4' and not file.is_file() and p['nas']=='gesichert':
                    nas=Path(os.environ.get('NKL_TIMELAPSE_NAS','/mnt/nkl-timelapse'))
                    if not (nas/'.nkl-timelapse-target').is_file(): return self.reply(503,{'message':'NAS nicht verfuegbar'})
                    file=nas/(p['channel']+'-'+pid+'.mp4')
                if not file.is_file(): return self.reply(404,{'message':'Datei noch nicht verfuegbar'})
                with file.open('rb') as f:
                    size=os.fstat(f.fileno()).st_size; start=0; end=size-1; status=200
                    value=self.headers.get('Range')
                    if value:
                        m=re.fullmatch(r'bytes=(\d+)-(\d*)',value)
                        if not m: return self.reply(416,{'message':'Unsupported range'})
                        start=int(m[1]); end=min(end,int(m[2])) if m[2] else end; status=206
                        if start>end: return self.reply(416,{'message':'Invalid range'})
                    self.send_response(status)
                    self.send_header('Content-Type','image/jpeg' if filename.endswith('.jpg') else ('video/mp4' if filename.endswith('.mp4') else 'video/mp2t'))
                    self.send_header('Cache-Control','no-store'); self.send_header('Accept-Ranges','bytes')
                    if status==206: self.send_header('Content-Range',f'bytes {start}-{end}/{size}')
                    if filename=='export.mp4': self.send_header('Content-Disposition',f'attachment; filename="Zeitraffer-{p["label"] if p["day"] else pid}.mp4"')
                    self.send_header('Content-Length',str(end-start+1)); self.end_headers()
                    if self.command=='HEAD': return
                    f.seek(start); remaining=end-start+1
                    while remaining:
                        block=f.read(min(262144,remaining))
                        if not block: break
                        self.wfile.write(block); remaining-=len(block)
            except (BrokenPipeError,ConnectionResetError): pass
            except Exception as e: self.reply(503,{'message':type(e).__name__+': '+str(e)[:200]})
    return Handler


def main():
    root=Path(os.environ.get('NKL_TIMELAPSE_ROOT','/core/timelapse')); root.mkdir(parents=True,exist_ok=True)
    # A single service owns the scheduler; never run two against the same store.
    import fcntl
    lock=(root/'service.lock').open('w')
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    service=Service(root)
    stopping=threading.Event()
    def stop(*_): stopping.set()
    signal.signal(signal.SIGTERM,stop); signal.signal(signal.SIGINT,stop)
    server=ThreadingHTTPServer(('127.0.0.1',int(os.environ.get('NKL_TIMELAPSE_PORT','8099'))),make_handler(service))
    thread=threading.Thread(target=server.serve_forever,daemon=True); thread.start()
    try:
        while not stopping.is_set():
            try: service.tick()
            except Exception as e: print('Timelapse scheduler:',type(e).__name__,str(e),flush=True)
            stopping.wait(2)
    finally: server.shutdown(); service.close()

if __name__=='__main__': main()
