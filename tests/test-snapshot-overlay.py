#!/usr/bin/env python3
import importlib.util,json,os,sys,tempfile,unittest,subprocess,shutil
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bundle/timelapse'))
from player_overlay import capture_filter
import snapshot_overlay as snap
A='00000000-0000-0000-0000-000000000001'
B='00000000-0000-0000-0000-000000000002'
class SnapshotTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
  self.db=self.root/'db.json';self.channel=self.root/'channels'/A;self.channel.mkdir(parents=True)
  self.cfg={'enabled':True,'template':'24 °C','fontSize':48,'box':True,'position':'bottom-left'}
  self.save()
 def tearDown(self):self.tmp.cleanup()
 def save(self):self.db.write_text(json.dumps({'metadata':{'process':{'restreamer-ui:ingest:'+A:{'restreamer-ui':{'player':{'overlay':self.cfg}}}}}}))
 def args(self):return ['-i',f'http://localhost:8080/memfs/{A}.m3u8','-vframes','1','-f','image2','-update','1',f'http://user:secret@localhost:8080/memfs/{A}.jpg']
 def test_only_managed_snapshots(self):
  args=self.args();self.assertEqual(snap.snapshot_channel(args),A)
  for altered in [args[:-1]+['/tmp/test.jpg'],args[:-1]+[args[-1].replace(A,B)],args[:-1]+[args[-1].replace('localhost','example.com')],args+['extra'],args[:-1]+['-vf','null',args[-1]],['-version'],['-i','source','-codec:v','copy','out.m3u8']]:
   self.assertIsNone(snap.snapshot_channel(altered))
 def test_real_dynamic_render_matches_timelapse_at_multiple_sizes(self):
  for n,color in [(1,'red'),(2,'green')]:
   logo=self.channel/f'playeroverlaylogo{n}.png'
   subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i',f'color={color}:s=32x32','-frames:v','1','-threads','1',str(logo)],check=True)
   self.cfg[f'logo{n}']={'enabled':True,'path':f'/channels/{A}/{logo.name}','width':100,'position':'top-right' if n==1 else 'top-left','opacity':.7}
  self.save();(self.channel/'player-overlay.txt').write_text('23.4 °C / 80% : %{n}')
  for w,h in [(640,360),(1280,720),(640,480)]:
   def render(dynamic):
    graph=capture_filter(self.db,self.root,A,None if dynamic else w,None if dynamic else h,'null',self.root/'text.txt')
    r=subprocess.run(['ffmpeg','-v','error','-filter_complex_threads','1','-f','lavfi','-i',f'color=blue:s={w}x{h}','-filter_complex',graph,'-map','[tlout]','-frames:v','1','-threads','1','-pix_fmt','rgb24','-f','rawvideo','-'],capture_output=True)
    self.assertEqual(r.returncode,0,r.stderr.decode());return r.stdout
   self.assertEqual(render(True),render(False))
 def test_disabled_and_channel_isolation(self):
  self.assertIsNone(capture_filter(self.db,self.root,B,None,None,'null',self.root/'t'))
  self.cfg['enabled']=False;self.save()
  self.assertIsNone(capture_filter(self.db,self.root,A,None,None,'null',self.root/'t'))
 def test_wrapper_preserves_command_and_cleans_temporary_files(self):
  args=self.args()
  with patch.dict(os.environ,{'CORE_DB_DIR':str(self.root),'CORE_STORAGE_DISK_DIR':str(self.root)}),patch.object(sys,'argv',['snapshot',*args]),patch.object(snap.subprocess,'Popen') as spawn,patch.object(snap.signal,'signal'):
   spawn.return_value.wait.return_value=0
   self.assertEqual(snap.main(),0)
   command=spawn.call_args.args[0]
   self.assertEqual(command[1:1+len(args)-1],args[:-1]);self.assertEqual(command[-1],args[-1])
   self.assertNotIn('-filter_complex_script',command)
   graph=command[command.index('-filter_complex')+1]
   self.assertIn('drawtext=',graph)
   import re
   text_path=re.search(r"textfile='([^']+)'",graph)[1]
   self.assertFalse(Path(text_path).exists())
 def test_real_wrapper_upload(self):
  from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
  import threading
  images=[]
  class Handler(BaseHTTPRequestHandler):
   def do_PUT(self):
    body=b''
    if self.headers.get('Transfer-Encoding')=='chunked':
     while True:
      n=int(self.rfile.readline().strip(),16)
      if n==0:self.rfile.readline();break
      body+=self.rfile.read(n);self.rfile.read(2)
    else:body=self.rfile.read(int(self.headers.get('Content-Length','0')))
    images.append(body);self.send_response(200);self.end_headers()
   do_POST=do_PUT
   def log_message(self,*args):pass
  server=ThreadingHTTPServer(('127.0.0.1',0),Handler);threading.Thread(target=server.serve_forever,daemon=True).start()
  try:
   source=self.root/(A+'.m3u8')
   subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=black:s=640x360','-t','1','-c:v','libx264','-threads','1','-f','hls',str(source)],check=True)
   args=['-v','error','-filter_complex_threads','1','-i',str(source),'-vframes','1','-f','image2','-update','1','-threads','1','-method','PUT',f'http://127.0.0.1:{server.server_port}/memfs/{A}.jpg']
   with patch.dict(os.environ,{'CORE_DB_DIR':str(self.root),'CORE_STORAGE_DISK_DIR':str(self.root)}),patch.object(sys,'argv',['snapshot',*args]),patch.object(snap,'REAL',shutil.which('ffmpeg')):
    self.assertEqual(snap.main(),0)
   self.assertEqual(len(images),1);self.assertTrue(images[0].startswith(b'\xff\xd8'))
   jpg=self.root/'result.jpg';jpg.write_bytes(images[0])
   pixels=subprocess.run(['ffmpeg','-v','error','-i',str(jpg),'-threads','1','-f','rawvideo','-pix_fmt','rgb24','-'],check=True,capture_output=True).stdout
   self.assertGreater(sum(v>180 for v in pixels),100)
  finally:server.shutdown();server.server_close()
if __name__=='__main__':unittest.main()
