#!/usr/bin/env python3
import json,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
from datetime import datetime,timezone
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bundle/timelapse'))
from service import Service,DEFAULT,channel_settings,project_settings
CHANNEL='00000000-0000-0000-0000-000000000001'
NOW=datetime(2026,11,10,12,tzinfo=timezone.utc).timestamp()
class CombinedTests(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name)
  self.db=self.root/'db.json';self.db.write_text(json.dumps({'metadata':{'process':{'restreamer-ui:ingest:'+CHANNEL:{'restreamer-ui':{'meta':{'name':'Test'}}}}}}))
  self.s=Service(self.root/'state',self.db,self.root/'data',min_free=0,quota=1024**3)
  self.s.set_channel_active(CHANNEL,True)
 def tearDown(self):self.s.close();self.tmp.cleanup()
 def config(self,**kw):
  with patch('service.time.time',return_value=NOW):return self.s.configure(CHANNEL,{**DEFAULT,**kw})
 def rows(self):return self.s.rows('SELECT * FROM projects ORDER BY started')
 def start(self):return self.s.action({'action':'start','channel':CHANNEL},now=NOW)
 def test_parallel_rollover_and_restart(self):
  self.config(mode='both',interval=45,seasonSettings={'interval':600,'fps':12})
  self.assertEqual(self.rows(),[])
  result=self.start();self.start();rows=self.rows();self.assertEqual(len(rows),2)
  day=next(p for p in rows if p['day']);season=next(p for p in rows if not p['day'])
  self.assertEqual(json.loads(day['settings'])['interval'],45)
  self.assertEqual(json.loads(season['settings'])['interval'],600)
  self.assertEqual(json.loads(season['settings'])['mode'],'season')
  self.s.close();self.s=Service(self.root/'state',self.db,self.root/'data',min_free=0)
  self.s.schedule(NOW+86400);rows=self.rows();self.assertEqual(len(rows),3)
  self.assertEqual(next(p for p in rows if p['id']==day['id'])['status'],'finished')
  self.assertEqual(next(p for p in rows if p['id']==result['id'])['status'],'recording')
  self.assertEqual(sum(not bool(p['day']) for p in rows),1)
 def test_season_mode_finishes_daily_and_preserves_settings(self):
  c=self.config(mode='both',interval=45,seasonSettings={'interval':600});self.start()
  day=next(p for p in self.rows() if p['day']);self.s.action({'action':'pause','project':day['id']})
  with patch('service.time.time',return_value=NOW+10):
   c=self.s.configure(CHANNEL,{**c,**c['seasonSettings'],'mode':'season'})
  rows=self.rows();stopped=next(p for p in rows if p['day'])
  self.assertEqual(stopped['status'],'finished');self.assertEqual(stopped['export'],1)
  self.s.schedule(NOW+86400);self.assertEqual(len(self.rows()),2)
  c=self.s.configure(CHANNEL,{**c,**c['dailySettings'],'mode':'both','interval':90})
  self.assertEqual(c['dailySettings']['interval'],90);self.assertEqual(c['seasonSettings']['interval'],600)
  c=self.s.configure(CHANNEL,{**c,'mode':'daily'})
  self.assertEqual(c['interval'],90)
  self.assertEqual(next(p for p in self.rows() if not p['day'])['status'],'finished')
 def test_adding_season_to_armed_daily_continues_daily(self):
  c=self.config(interval=60);self.start();day=self.rows()[0]['id']
  with patch('service.time.time',return_value=NOW):c=self.s.configure(CHANNEL,{**c,'mode':'both'})
  self.assertEqual(len(self.rows()),2)
  self.assertEqual(next(p for p in self.rows() if p['id']==day)['status'],'recording')
  self.s.configure(CHANNEL,c);self.assertEqual(len(self.rows()),2)
 def test_profile_updates_are_independent_and_season_does_not_restart(self):
  c=self.config(mode='both',interval=60,seasonSettings={'interval':600});self.start()
  c=self.s.configure(CHANNEL,{**c,'interval':120,'seasonSettings':{**c['seasonSettings'],'interval':900}})
  for p in self.rows():self.assertEqual(json.loads(p['settings'])['interval'],120 if p['day'] else 900)
  season=next(p for p in self.rows() if not p['day'])
  self.s.action({'action':'stop','project':season['id']},now=NOW+5)
  self.s.schedule(NOW+86400)
  self.assertEqual(sum(not bool(p['day']) for p in self.rows()),1)
  self.assertEqual(sum(p['status']=='recording' for p in self.rows()),1)
 def test_legacy_profile_is_preserved_and_validated(self):
  old={**DEFAULT,'mode':'season','interval':3600,'fps':12,'width':1280}
  normalized=channel_settings(old)
  self.assertEqual(project_settings(normalized,'season'),old)
  combined=channel_settings({**normalized,**normalized['dailySettings'],'mode':'both'},normalized)
  self.assertEqual(combined['dailySettings'],normalized['dailySettings'])
  with self.assertRaises(ValueError):channel_settings({**combined,'seasonSettings':{'interval':1}})
  with self.assertRaises(ValueError):channel_settings({**combined,'mode':'invalid'})
 def test_solar_daily_window_does_not_delay_season(self):
  self.config(mode='both',window='solar',latitude=52.52,longitude=13.405)
  night=datetime(2026,11,10,0,tzinfo=timezone.utc).timestamp()
  self.s.action({'action':'start','channel':CHANNEL},now=night)
  self.assertEqual(len(self.rows()),1);self.assertIsNone(self.rows()[0]['day'])
  self.s.schedule(NOW);self.assertEqual(len(self.rows()),2)
if __name__=='__main__':unittest.main()
