#!/usr/bin/env python3
import json,os,sys,tempfile,unittest,subprocess
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bundle/timelapse'))
from service import Service,DEFAULT
from player_overlay import capture_filter
A='00000000-0000-0000-0000-000000000001'
B='00000000-0000-0000-0000-000000000002'
class OverlayTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.data=self.root/'data';self.db=self.root/'db.json';self.text=self.root/'snapshot.txt'
  self.config={'enabled':True,'template':'Temperatur {{w.temp | number:1}} °C','fontSize':48,'fontColor':'#ffffff','position':'bottom-left','box':True,'interval':60}
  self.database={'metadata':{'process':{'restreamer-ui:ingest:'+c:{'restreamer-ui':{'player':{'overlay':dict(self.config)},'meta':{'name':c}}} for c in (A,B)}}}
  self.save()
  for c in (A,B):(self.data/'channels'/c).mkdir(parents=True)
 def save(self):self.db.write_text(json.dumps(self.database))
 def tearDown(self):self.tmp.cleanup()
 def graph(self,c=A):return capture_filter(self.db,self.data,c,640,360,'scale=640:360',self.text)
 def test_channel_values_are_frozen_and_settings_reloaded(self):
  a=self.data/'channels'/A/'player-overlay.txt';a.write_text('10.0 °C')
  (self.data/'channels'/B/'player-overlay.txt').write_text('20.0 °C')
  graph=self.graph();self.assertEqual(self.text.read_text(),'10.0 °C')
  a.write_text('11.0 °C');self.assertEqual(self.text.read_text(),'10.0 °C')
  self.graph();self.assertEqual(self.text.read_text(),'11.0 °C')
  self.graph(B);self.assertEqual(self.text.read_text(),'20.0 °C')
  self.database['metadata']['process']['restreamer-ui:ingest:'+A]['restreamer-ui']['player']['overlay']['fontSize']=80;self.save()
  self.assertIn('fontsize=40',self.graph());self.assertIn('fontsize=24',graph)
 def test_missing_stale_or_disabled_data(self):
  self.graph();self.assertEqual(self.text.read_text(),'Temperatur -- °C')
  cache=self.data/'channels'/A/'player-overlay.txt';cache.write_text('old value');os.utime(cache,(1,1))
  self.graph();self.assertNotIn('old value',self.text.read_text())
  self.database['metadata']['process']['restreamer-ui:ingest:'+A]['restreamer-ui']['player']['overlay']['enabled']=False;self.save();self.assertIsNone(self.graph())
 def test_global_flags_are_independent_and_persist(self):
  s=Service(self.root/'state',self.db,self.data,min_free=0)
  try:
   self.assertFalse(s.global_settings()['includePlayerOverlays'])
   s.action({'action':'configure_global','includeBurnedOverlays':True})
   s.action({'action':'configure_global','includePlayerOverlays':True})
   self.assertTrue(s.global_settings()['includeBurnedOverlays'])
   with self.assertRaises(ValueError):s.action({'action':'configure_global','includeBurnedOverlays':False,'includePlayerOverlays':'true'})
   self.assertTrue(s.global_settings()['includeBurnedOverlays'])
  finally:s.close()
  s=Service(self.root/'state',self.db,self.data,min_free=0)
  try:self.assertTrue(s.global_settings()['includePlayerOverlays'])
  finally:s.close()
 def test_logo_cannot_read_other_channel_or_external_files(self):
  cfg=self.database['metadata']['process']['restreamer-ui:ingest:'+A]['restreamer-ui']['player']['overlay']
  for path in ['/etc/passwd','/channels/'+B+'/playeroverlaylogo1.png','http://example.test/logo.png']:
   cfg['logo1']={'enabled':True,'path':path};self.save()
   with self.assertRaises(ValueError):self.graph()
 def test_real_single_frame_contains_text_and_logo_without_live_transcode(self):
  logo=self.data/'channels'/A/'playeroverlaylogo1.png'
  subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=red:s=32x32','-frames:v','1','-threads','1','-y',str(logo)],check=True)
  cfg=self.database['metadata']['process']['restreamer-ui:ingest:'+A]['restreamer-ui']['player']['overlay']
  cfg['logo1']={'enabled':True,'path':'/channels/'+A+'/playeroverlaylogo1.png','width':100,'position':'top-right','opacity':1};self.save()
  (self.data/'channels'/A/'player-overlay.txt').write_text('23.4 °C / 80% : %{n}')
  graph=self.graph();self.assertIn('expansion=none',graph)
  pixels=subprocess.run(['ffmpeg','-v','error','-filter_complex_threads','1','-f','lavfi','-i','color=black:s=640x360','-filter_complex',graph,'-map','[tlout]','-frames:v','1','-threads','1','-pix_fmt','rgb24','-f','rawvideo','-'],check=True,capture_output=True).stdout
  def pixel(x,y):return pixels[(y*640+x)*3:(y*640+x)*3+3]
  self.assertGreater(pixel(600,25)[0],180)
  self.assertLess(pixel(300,100)[0],10)
  self.assertTrue(any(pixels[(y*640+10)*3:(y*640+350)*3].count(255)>5 for y in range(300,350)))
 def test_spacing_matches_legacy_burnin_pixels_at_all_positions(self):
  # Reference: pre-existing TextOverlay.js POSITIONS and boxborderw=16.
  positions={'top-left':('24','24'),'top-center':('(w-tw)/2','24'),
             'top-right':('w-tw-24','24'),'bottom-left':('24','h-th-24'),
             'bottom-center':('(w-tw)/2','h-th-24'),'bottom-right':('w-tw-24','h-th-24')}
  cfg=self.database['metadata']['process']['restreamer-ui:ingest:'+A]['restreamer-ui']['player']['overlay']
  (self.data/'channels'/A/'player-overlay.txt').write_text('23.4 °C\nLuftfeuchte: 80%')
  for width,height,size in [(640,360,24),(1280,720,48)]:
   for name,(x,y) in positions.items():
    with self.subTest(size=(width,height),position=name):
     cfg['position']=name;self.save()
     graph=capture_filter(self.db,self.data,A,width,height,f'scale={width}:{height}',self.text)
     reference=f"drawtext=textfile='{self.text}':expansion=none:fontfile='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf':fontcolor=0xFFFFFF:fontsize={size}:x={x}:y={y}:box=1:boxcolor=0x000000@0.55:boxborderw=16"
     def pixels(args):
      return subprocess.run(['ffmpeg','-v','error','-filter_complex_threads','1','-f','lavfi','-i',f'color=blue:s={width}x{height}',*args,'-frames:v','1','-threads','1','-pix_fmt','rgb24','-f','rawvideo','-'],check=True,capture_output=True).stdout
     self.assertEqual(pixels(['-filter_complex',graph,'-map','[tlout]']),pixels(['-vf',f'scale={width}:{height},'+reference]))
 def test_capture_integration_keeps_values_in_jpeg(self):
  s=Service(self.root/'state',self.db,self.data,min_free=0,quota=1024**3)
  try:
   s.configure(A,{**DEFAULT,'mode':'season','width':640})
   pid=s.action({'action':'start','channel':A})['id'];p=s.rows('SELECT * FROM projects WHERE id=?',(pid,))[0]
   s.action({'action':'configure_global','includePlayerOverlays':True})
   source=self.root/'source.mp4'
   subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=black:s=640x360','-t','1','-c:v','libx264','-threads','1','-y',str(source)],check=True)
   with patch.object(s,'source_format',return_value=(640,360,1000000)),patch.object(s,'capture_input',return_value=(['-i',str(source)],'')):
    s.capture(p,123)
   saved=s.rows('SELECT * FROM projects WHERE id=?',(pid,))[0];self.assertEqual(saved['error'],'')
   self.assertTrue((s.root/pid/'123.jpg').is_file());self.assertFalse((s.root/pid/'.123.overlay.txt').exists())
   self.assertEqual(len(s.rows('SELECT * FROM frames WHERE project=?',(pid,))),1)
  finally:s.close()
if __name__=='__main__':unittest.main()
