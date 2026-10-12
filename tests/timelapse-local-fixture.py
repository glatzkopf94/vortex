#!/usr/bin/env python3
"""Disposable end-to-end fixture. Never connects to user cameras/volumes."""
import json, os, signal, subprocess, sys, tempfile, threading, time
from pathlib import Path
from urllib.request import Request,urlopen
from http.server import ThreadingHTTPServer
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'bundle/timelapse'))
from service import Service, DEFAULT
from httpd import make_handler
channel='0e652a1b-3ac8-4211-99a0-1f171d362f57'
root=Path(tempfile.mkdtemp(prefix='nkl-timelapse-e2e-'));data=root/'data';data.mkdir();config=root/'config';config.mkdir()
(config/'db.json').write_text(json.dumps({'version':4,'process':{'restreamer-ui:ingest:'+channel:{'id':'restreamer-ui:ingest:'+channel,'order':'stop','config':{'id':'restreamer-ui:ingest:'+channel,'ffversion':'^6.1.1','autostart':False,'input':[{'id':'input_0','address':'testsrc=size=640x360:rate=15','options':['-f','lavfi']}],'output':[{'id':'output_0','address':'-','options':['-f','null']}]}}},'metadata':{'system':{},'process':{'restreamer-ui:ingest:'+channel:{'restreamer-ui':{'meta':{'name':'Lokale Testkamera'}}}}}}))
ui=Path(sys.argv[2]);core=Path(sys.argv[1])
env={**os.environ,'CORE_CONFIGFILE':str(config/'config.json'),'CORE_DB_DIR':str(config),'CORE_STORAGE_DISK_DIR':str(data),'CORE_STORAGE_MIMETYPES_FILE':str(ROOT/'core/mime.types'),'CORE_ROUTER_UI_PATH':str(ui),'CORE_ADDRESS':'127.0.0.1:8080','CORE_FFMPEG_BINARY':'/usr/bin/ffmpeg','CORE_API_AUTH_ENABLE':'true','CORE_API_AUTH_USERNAME':'test-admin','CORE_API_AUTH_PASSWORD':'local-test-only','CORE_RTMP_ENABLE':'false','CORE_SRT_ENABLE':'false','CORE_TLS_ENABLE':'false'}
log=(root/'core.log').open('w'); proc=subprocess.Popen([str(core)],env=env,stdout=log,stderr=log)
fflog=(root/'ffmpeg.log').open('w')
ff=subprocess.Popen(['ffmpeg','-v','error','-re','-f','lavfi','-i','testsrc2=size=640x360:rate=15','-c:v','libx264','-threads','1','-preset','ultrafast','-g','15','-sc_threshold','0','-f','hls','-hls_time','1','-hls_list_size','30','-hls_flags','program_date_time+delete_segments',str(data/(channel+'.m3u8'))],stdout=fflog,stderr=fflog)
service=Service(root/'timelapse',config/'db.json',data,min_free=0,quota=1024**3)
server=ThreadingHTTPServer(('127.0.0.1',8099),make_handler(service));threading.Thread(target=server.serve_forever,daemon=True).start()
try:
    for _ in range(60):
        try:
            if urlopen('http://127.0.0.1:8080/ping').status==200 and (data/(channel+'0.ts')).exists():break
        except Exception:pass
        time.sleep(.5)
    else: raise RuntimeError((root/'core.log').read_text())
    p=data/'channels'/channel;p.mkdir(parents=True)
    cfg={'channelid':channel,'source':channel+'.m3u8','poster':'poster.svg','autoplay':False,'mute':True,'color':{'buttons':'#fff'},'overlay':{'enabled':False},'dvr':{'enabled':True,'hours':3,'segmentDuration':1},'playback':{'singleActiveStream':True,'sessionLimitEnabled':True}}
    (p/'config.js').write_text('var playerConfig='+json.dumps(cfg)+';')
    (data/'poster.svg').write_text('<svg xmlns="http://www.w3.org/2000/svg" width="640" height="360"><rect width="640" height="360" fill="#415a38"/></svg>')
    import re,shutil
    template=(ROOT/'ui/public/_player/videojs/player.html').read_text()
    template=re.sub(r'{{#if (airplay|chromecast)}}.*?{{/if}}','',template,flags=re.S).replace('{{channelid}}',channel).replace('{{name}}','Lokaler Test').replace('{{description}}','')
    (data/(channel+'.html')).write_text(template)
    shutil.copytree(ROOT/'ui/public/_player/videojs/dist',data/'player/videojs/dist')
    service.configure(channel,{**DEFAULT,'mode':'season','interval':60,'width':640,'public':True})
    pid=service.action({'action':'start','channel':channel})['id']
    project=service.rows('SELECT * FROM projects WHERE id=?',(pid,))[0]
    for i in range(3):
        service.capture(project,int(time.time())+i)
    if service.status()['projects'][0]['frames']!=3:raise RuntimeError(str(service.status()))
    # Reuse captured images for an 8-second real preview (avoids a two-hour wait).
    first=service.rows('SELECT * FROM frames WHERE project=? ORDER BY slot',(pid,))[0]
    for i in range(197):
        file=service.root/pid/f'{1900000000+i}.jpg';shutil.copyfile(first['path'],file)
        service.write('INSERT INTO frames VALUES(?,?,?,?)',(pid,1900000000+i,str(file),file.stat().st_size))
    service.action({'action':'export','project':pid});service.render(service.rows('SELECT * FROM projects WHERE id=?',(pid,))[0])
    if service.status()['projects'][0]['exported']!=200:raise RuntimeError(str(service.status()))
    token=json.load(urlopen(Request('http://127.0.0.1:8080/api/login',data=json.dumps({'username':'test-admin','password':'local-test-only'}).encode(),headers={'Content-Type':'application/json'})))['access_token']
    ready={'root':str(root),'channel':channel,'project':pid,'token':token}
    Path('/tmp/nkl-timelapse-fixture.json').write_text(json.dumps(ready))
    print(json.dumps({k:v for k,v in ready.items() if k!='token'}),flush=True)
    if '--test' in sys.argv:
        subprocess.run(['node',str(ROOT/'tests/test-timelapse-browser.cjs')],check=True)
        sys.exit(0)
    stopping=threading.Event()
    signal.signal(signal.SIGTERM,lambda *_:stopping.set());signal.signal(signal.SIGINT,lambda *_:stopping.set())
    while not stopping.wait(.5):pass
finally:
    server.shutdown();service.close();ff.terminate();proc.send_signal(signal.SIGINT)
    for process in (ff,proc):
        try:process.wait(timeout=10)
        except subprocess.TimeoutExpired:process.kill()
