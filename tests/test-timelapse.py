#!/usr/bin/env python3
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch
from datetime import date, datetime, timezone
from urllib.request import urlopen, Request
from urllib.error import HTTPError
from http.server import ThreadingHTTPServer

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'bundle/timelapse'))
from service import Service, DEFAULT, settings, atomic
from solar import window, sun_times
from httpd import make_handler
CHANNEL='0e652a1b-3ac8-4211-99a0-1f171d362f57'

class TimelapseTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.root=Path(self.tmp.name)
        self.db=self.root/'db.json'; self.db.write_text(json.dumps({'metadata':{'process':{'restreamer-ui:ingest:'+CHANNEL:{'restreamer-ui':{'meta':{'name':'Test'}}}}}}))
        self.service=Service(self.root/'state',self.db,self.root/'data',min_free=0,quota=1024**3)
    def tearDown(self): self.service.close(); self.tmp.cleanup()
    def project(self,**options):
        s={**DEFAULT,'mode':'season',**options}; self.service.configure(CHANNEL,s)
        return self.service.action({'action':'start','channel':CHANNEL},now=1800000000)['id']
    def frame(self,pid,slot):
        path=self.service.root/pid/f'{slot}.jpg'; path.parent.mkdir(exist_ok=True)
        subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=c=red:size=640x360','-frames:v','1','-threads','1','-y',str(path)],check=True)
        self.service.write('INSERT INTO frames VALUES(?,?,?,?)',(pid,slot,str(path),path.stat().st_size))
        return path
    def overlay_config(self, address='rtsp://camera/live', graph="scale=640:360,drawtext=text='Weather'"):
        db=json.loads(self.db.read_text())
        db['process']={'restreamer-ui:ingest:'+CHANNEL:{'config':{
            'input':[{'address':address,'options':['-rtsp_transport','tcp']}],
            'output':[{'options':['-map','0:0','-filter:v',graph]}]}}}
        self.db.write_text(json.dumps(db))

    def test_global_overlay_default_persistence_and_source_selection(self):
        self.assertFalse(self.service.global_settings()['includeBurnedOverlays'])
        self.overlay_config()
        with patch.object(self.service,'fresh_source',return_value='http://127.0.0.1:8080/live.m3u8'):
            args,filters=self.service.capture_input(CHANNEL)
            self.assertIn('rtsp://camera/live',args)
            self.assertEqual(filters,'scale=640:360')
            self.service.action({'action':'configure_global','includeBurnedOverlays':True})
            args,filters=self.service.capture_input(CHANNEL)
            self.assertIn('http://127.0.0.1:8080/live.m3u8',args)
            self.assertEqual(filters,'')
        self.service.close()
        self.service=Service(self.root/'state',self.db,self.root/'data',min_free=0)
        self.assertTrue(self.service.global_settings()['includeBurnedOverlays'])
        with self.assertRaises(ValueError):self.service.action({'action':'configure_global','includeBurnedOverlays':'false'})

    def test_overlay_logo_bypass_and_unsupported_source(self):
        self.overlay_config(graph="[in]scale=640:360[lc_base0];movie=logo.png[lc_logo0];[lc_base0][lc_logo0]overlay=x=0:y=0[lc_base1];[lc_base1]null[out]")
        with patch.object(self.service,'fresh_source',return_value='http://127.0.0.1:8080/live.m3u8'):
            self.assertEqual(self.service.capture_input(CHANNEL)[1],'scale=640:360')
            self.overlay_config(address='rtmp://localhost/push')
            with self.assertRaisesRegex(ValueError,'direkt abrufbare'):self.service.capture_input(CHANNEL)
            self.overlay_config(graph='scale=640:360')
            self.assertIn('http://127.0.0.1:8080/live.m3u8',self.service.capture_input(CHANNEL)[0])

    def test_actual_overlay_free_http_snapshot(self):
        from http.server import SimpleHTTPRequestHandler
        from functools import partial
        source=self.root/'camera.mp4'
        subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','color=c=blue:s=640x360:r=5','-t','1','-c:v','libx264','-threads','1','-pix_fmt','yuv420p','-y',str(source)],check=True)
        class Quiet(SimpleHTTPRequestHandler):
            def log_message(self,*args):pass
        server=ThreadingHTTPServer(('127.0.0.1',0),partial(Quiet,directory=str(self.root)))
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        try:
            self.overlay_config(address=f'http://127.0.0.1:{server.server_port}/camera.mp4')
            # HTTP input must not inherit RTSP-only options.
            db=json.loads(self.db.read_text());db['process']['restreamer-ui:ingest:'+CHANNEL]['config']['input'][0]['options']=[];self.db.write_text(json.dumps(db))
            pid=self.project();project=self.service.rows('SELECT * FROM projects WHERE id=?',(pid,))[0]
            with patch.object(self.service,'fresh_source',return_value='http://127.0.0.1:8080/live.m3u8'),patch.object(self.service,'source_format',return_value=(640,360,1000000)):
                self.service.capture(project,1800000000)
            self.assertEqual(self.service.status()['projects'][0]['frames'],1)
            image=self.service.root/pid/'1800000000.jpg'
            pixel=subprocess.check_output(['ffmpeg','-v','error','-i',str(image),'-vf','scale=1:1','-f','rawvideo','-pix_fmt','rgb24','-threads','1','-'])
            self.assertGreater(pixel[2],200)
            self.assertLess(pixel[0],30)
        finally:server.shutdown();server.server_close();thread.join()

    def test_saving_transfer_waits_for_interval(self):
        self.service.action({'action':'configure_transfer','settings':{'enabled':True,'host':'test.invalid','username':'user','intervalMinutes':60}},now=1800000000)
        self.assertEqual(self.service.next_transfer,1800003600)
        self.service.schedule_transfer(1800000001)
        self.assertIsNone(self.service.transfer_job)

    def test_manual_selection_without_automatic_enabled(self):
        pid=self.project()
        self.service.action({'action':'configure_transfer','settings':{'host':'test.invalid','username':'user','enabled':False}})
        self.service.action({'action':'transfer_now','channel':CHANNEL,'projects':[pid]})
        self.assertEqual(set(self.service.transfer_plan['files']),{pid})
        self.assertEqual(self.service.transfer_plan['origin'],'manual')
        self.service.action({'action':'cancel_transfer','origin':'manual'})
        self.assertFalse(self.service.transfer_pending)
        self.assertEqual(self.service.status()['transferStatus']['state'],'idle')
        with self.assertRaises(ValueError):self.service.action({'action':'transfer_now','projects':['missing']})
        with self.assertRaises(ValueError):self.service.action({'action':'transfer_now','projects':[pid],'onlyFinished':True})

    def test_automatic_channel_and_finished_filters(self):
        one=self.project();self.service.write("UPDATE projects SET status='finished' WHERE id=?",(one,));two=self.project();other='11111111-1111-1111-1111-111111111111'
        self.service.write("UPDATE projects SET status='finished' WHERE id=?",(one,))
        self.service.write("UPDATE projects SET channel=?,status='finished' WHERE id=?",(other,two))
        self.project()
        self.service.action({'action':'configure_transfer','settings':{'host':'test.invalid','username':'user','enabled':True,'autoChannels':[CHANNEL],'onlyFinished':True}},now=1800000000)
        with patch.object(self.service,'transfer_isolated') as worker:
            self.service.schedule_transfer(1800003601);self.service.transfer_job.result()
            plan=worker.call_args.args[0]
            self.assertEqual(set(plan['files']),{one});self.assertEqual(plan['origin'],'automatic')

    def test_cancel_running_worker_clears_progress(self):
        from unittest.mock import MagicMock
        process=MagicMock();process.poll.return_value=None
        plan={'origin':'manual','files':{}}
        with patch('service.subprocess.Popen',return_value=process),patch('service.time.sleep',side_effect=lambda _:self.service.transfer_cancel.set()):
            self.service.transfer_isolated(plan)
        process.kill.assert_called_once();process.wait.assert_called_once()
        self.assertEqual(self.service.status()['transferStatus'],{'state':'idle','origin':'manual'})

    def test_ftp_probe_does_not_block_status_or_save_config(self):
        entered=threading.Event();release=threading.Event()
        def probe(config):
            entered.set();release.wait(3);return {'state':'success','message':'OK'}
        with patch('service.transfer.test_connection',side_effect=probe):
            try:
                self.service.action({'action':'test_transfer','settings':{'host':'test.invalid','port':40357,'username':'user','password':'secret'}})
                self.assertTrue(entered.wait(1))
                self.assertEqual(self.service.status()['transferTest']['state'],'running')
                self.assertFalse((self.service.root/'transfer-config.json').exists())
                with self.assertRaises(ValueError):self.service.action({'action':'test_transfer','settings':{}})
            finally:release.set()
            self.service.transfer_test_job.result(timeout=2)
            self.assertEqual(self.service.status()['transferTest']['state'],'success')

    def test_original_resolution_and_source_bitrate(self):
        self.assertEqual(settings({'width':0})['width'],0)
        pid=self.project(width=0)
        p=self.service.rows('SELECT * FROM projects WHERE id=?',(pid,))[0]
        commands=[]
        def capture_run(cmd, timeout):
            commands.append(cmd)
            Path(cmd[-1]).write_bytes(b'x'*200)
        with patch.object(self.service,'source_format',return_value=(2560,1920,8192000)), patch.object(self.service,'fresh_source',return_value='http://127.0.0.1:8080/test.m3u8'), patch('service.run',side_effect=capture_run):
            self.service.capture(p,1800000000)
        self.assertIn('scale=2560:1920',commands[0][commands[0].index('-vf')+1])
        saved=json.loads(self.service.rows('SELECT settings FROM projects WHERE id=?',(pid,))[0]['settings'])
        self.assertEqual(saved['sourceBitrate'],8192000)
        self.assertEqual(saved['sourceHeight'],1920)

    def test_quality_independent_of_initial_bandwidth_and_even_timestamps(self):
        pid=self.project(width=640,sourceBitrate=1000)
        folder=self.service.root/pid;folder.mkdir(exist_ok=True)
        subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','testsrc2=size=640x360:rate=25','-frames:v','60','-threads','1','-q:v','2',str(folder/'%06d.jpg')],check=True)
        for i in range(1,61):
            f=folder/f'{i:06d}.jpg'
            self.service.write('INSERT INTO frames VALUES(?,?,?,?)',(pid,1800000000+i*120,str(f),f.stat().st_size))
        self.service.write('UPDATE projects SET export=1 WHERE id=?',(pid,))
        p=self.service.rows('SELECT * FROM projects WHERE id=?',(pid,))[0]
        import service as module
        actual_run=module.run
        with patch('service.run',wraps=actual_run) as run:
            self.service.render(p)
        command=run.call_args_list[0].args[0]
        self.assertNotIn('-b:v',command)
        self.assertEqual(command[command.index('-crf')+1],'18')
        self.assertEqual(command[command.index('-g')+1],'250')
        output=folder/'export.mp4'
        self.assertTrue(output.exists())
        result=json.loads(subprocess.check_output(['ffprobe','-v','error','-select_streams','v:0','-show_frames','-show_entries','frame=best_effort_timestamp_time','-of','json',str(output)]))
        times=[float(f['best_effort_timestamp_time']) for f in result['frames']]
        self.assertEqual(len(times),60)
        for a,b in zip(times,times[1:]):self.assertAlmostEqual(b-a,1/25,places=5)

    def test_patched_ffmpeg_progress_mode_and_live_percent(self):
        from service import ffmpeg_progress_options
        ffmpeg_progress_options.cache_clear()
        try:
            with patch('service.subprocess.run',return_value=subprocess.CompletedProcess([],0,stdout=b'-jsonstats          print JSON progress report\n')):
                self.assertEqual(ffmpeg_progress_options(),['-jsonstats','0'])
                pid=self.project()
                folder=self.service.root/pid;folder.mkdir(exist_ok=True)
                args=self.service.progress_args(pid,'Bilder verarbeiten',10)
                self.assertIn('-jsonstats',args)
                (folder/'ffmpeg-progress.txt').write_text('out_time_us=2500000\nprogress=continue\n')
                self.assertEqual(self.service.progress(pid)['percent'],25)
                (folder/'ffmpeg-progress.txt').write_text('out_time_us=7500000\nprogress=continue\n')
                self.assertEqual(self.service.progress(pid)['percent'],75)
            ffmpeg_progress_options.cache_clear()
            with patch('service.subprocess.run',return_value=subprocess.CompletedProcess([],0,stdout=b'-stats_period time\n')):
                self.assertEqual(ffmpeg_progress_options(),[])
        finally:ffmpeg_progress_options.cache_clear()

    def test_first_preview_waits_for_two_images(self):
        pid=self.project()
        self.service.write("UPDATE projects SET status='paused' WHERE id=?",(pid,))
        self.frame(pid,1800000000)
        with patch.object(self.service,'render') as render:
            self.service.tick(1800000120)
            self.assertIsNone(self.service.render_job)
            self.frame(pid,1800000120)
            self.service.tick(1800000240)
            self.service.render_job.result()
            self.assertEqual(render.call_count,1)

    def test_daily_timeline_retains_actual_frame_times_and_excludes_season(self):
        pid=self.project(width=640)
        slots=[int(datetime(2026,10,6,h,m,tzinfo=timezone.utc).timestamp()) for h,m in [(6,0),(7,0),(10,15)]]
        for slot in slots:self.frame(pid,slot)
        p=self.service.rows('SELECT * FROM projects WHERE id=?',(pid,))[0]
        self.service.render(p)
        self.assertEqual(self.service.timeline(p),{'markers':[]})
        self.service.write('UPDATE projects SET day=? WHERE id=?',('2026-10-06',pid))
        p=self.service.rows('SELECT * FROM projects WHERE id=?',(pid,))[0]
        data=self.service.timeline(p)
        self.assertEqual([m['label'] for m in data['markers']],['08:00','09:00','12:15'])
        self.assertEqual([m['position'] for m in data['markers']],[i/json.loads(p['settings'])['fps'] for i in range(3)])
        self.service.write('DELETE FROM timeline WHERE project=?',(pid,))
        self.assertEqual(self.service.timeline(p)['markers'],[])
        for slot in slots:self.service.write("INSERT INTO attempts VALUES(?,?,'done')",(pid,slot))
        self.assertEqual(self.service.timeline(p),data)

    def test_free_interval_and_bulk_delete_separation(self):
        for value in [30,31,45,90,86400]:self.assertEqual(settings({'interval':value})['interval'],value)
        season=self.project()
        self.service.action({'action':'stop','project':season})
        daily=self.service.create_project(CHANNEL,{**DEFAULT,'interval':30},1800000000,day='2027-01-15')
        self.service.action({'action':'stop','project':daily})
        running=self.service.create_project(CHANNEL,DEFAULT,1800086400,day='2027-01-16')
        self.frame(daily,1800000000)
        with self.assertRaises(ValueError):self.service.action({'action':'delete_finished'})
        from concurrent.futures import Future
        self.service.render_job=Future()
        with self.assertRaisesRegex(ValueError,'Verarbeitung'):self.service.action({'action':'delete_finished','mode':'daily'})
        self.service.render_job.set_result(None)
        result=self.service.action({'action':'delete_finished','mode':'daily'})
        self.assertEqual(result['deleted'],1)
        self.assertFalse((self.service.root/daily).exists())
        self.assertIsNone(self.service.create_project(CHANNEL,DEFAULT,1800000000,day='2027-01-15'))
        ids={p['id'] for p in self.service.status()['projects']}
        self.assertEqual(ids,{season,running})
        self.service.action({'action':'delete_finished','mode':'season'})
        self.assertEqual([p['id'] for p in self.service.status()['projects']],[running])

    def test_mode_interval_limits_and_transfer_status_secrets(self):
        self.assertEqual(settings({'mode':'daily','interval':15})['interval'],15)
        self.assertEqual(settings({'mode':'season','interval':30})['interval'],30)
        self.assertEqual(settings({'mode':'season','interval':86400})['interval'],86400)
        with self.assertRaises(ValueError):settings({'mode':'season','interval':15})
        result=self.service.action({'action':'configure_transfer','settings':{'password':'not-a-real-password'}})
        self.assertNotIn('password',result)
        self.assertTrue(result['passwordConfigured'])
        config=self.service.root/'transfer-config.json'
        self.assertEqual(config.stat().st_mode & 0o777,0o600)
        status=self.service.status()
        self.assertGreater(status['diskFreeBytes'],0)
        self.assertNotIn('not-a-real-password',json.dumps(status))
        with self.assertRaises(ValueError):self.service.action({'action':'transfer_now'})

    def test_transfer_scheduler_prepares_export_before_upload(self):
        pid=self.project(width=640)
        self.frame(pid,1800000000)
        self.service.action({'action':'configure_transfer','settings':{'enabled':True,'host':'example.invalid','username':'test','mode':'season'}})
        with patch.object(self.service,'transfer_isolated') as upload:
            self.service.schedule_transfer(1800000000)
            self.assertTrue(self.service.transfer_pending)
            self.assertIsNone(self.service.transfer_job)
            p=self.service.rows('SELECT * FROM projects WHERE id=?',(pid,))[0]
            self.assertEqual(p['export'],1)
            self.service.render(p)
            self.service.schedule_transfer(1800000001)
            self.service.transfer_job.result()
            self.assertEqual(upload.call_count,1)
            self.service.schedule_transfer(1800000002)
            self.assertEqual(upload.call_count,1)

    def test_progress_reports_ffmpeg_time(self):
        pid=self.project()
        (self.service.root/pid).mkdir(exist_ok=True)
        self.service.progress_args(pid,'MP4 zusammenfügen',10)
        path=self.service.root/pid/'ffmpeg-progress.txt'
        path.write_text('out_time_us=5000000\nprogress=continue\n')
        self.assertEqual(self.service.progress(pid),{'phase':'MP4 zusammenfügen','percent':50})
        path.write_text('out_time_us=12000000\nprogress=end\n')
        self.assertEqual(self.service.progress(pid)['percent'],99)
        self.service.processing.pop(pid)
        self.assertIsNone(self.service.progress(pid))

    def test_solar_offsets_and_dst(self):
        s={**DEFAULT,'window':'solar','latitude':52.52,'longitude':13.405}
        rise,setting=sun_times(date(2026,6,21),s['latitude'],s['longitude'])
        # Berlin summer: sunrise about 04:43, sunset about 21:33 local.
        self.assertAlmostEqual(datetime.fromtimestamp(rise,timezone.utc).hour+datetime.fromtimestamp(rise,timezone.utc).minute/60,2.72,delta=.12)
        self.assertAlmostEqual(datetime.fromtimestamp(setting,timezone.utc).hour+datetime.fromtimestamp(setting,timezone.utc).minute/60,19.55,delta=.12)
        a,b=window(date(2026,6,21),s); self.assertEqual(a,rise-3600);self.assertEqual(b,setting+3600)
        full={**DEFAULT,'window':'full'}
        a,b=window(date(2026,3,29),full);self.assertEqual(b-a,23*3600)
        a,b=window(date(2026,10,25),full);self.assertEqual(b-a,25*3600)
        with self.assertRaises(ValueError): sun_times(date(2026,6,21),89,0)
    def test_validation_and_daily_resume_no_duplicates(self):
        for bad in [0,14,86401,float('nan')]:
            with self.assertRaises(ValueError): settings({'interval':bad})
        self.service.configure(CHANNEL,{**DEFAULT})
        now=datetime(2026,10,5,12,tzinfo=timezone.utc).timestamp()
        self.service.schedule(now); self.service.schedule(now+120)
        self.assertEqual(len(self.service.status()['projects']),1)
        self.service.close();self.service=Service(self.root/'state',self.db,self.root/'data',min_free=0)
        self.service.schedule(now+3600);self.assertEqual(len(self.service.status()['projects']),1)
        self.service.schedule(now+86400)
        self.assertEqual(len(self.service.status()['projects']),2)
        self.assertEqual(self.service.status()['projects'][-1]['status'],'finished')
    def test_capture_failure_recovery_and_quota(self):
        pid=self.project(); p=self.service.rows('SELECT * FROM projects WHERE id=?',(pid,))[0]
        self.service.capture(p,1800000000)
        self.assertEqual(self.service.status()['projects'][0]['missed'],1)
        self.assertEqual(self.service.status()['projects'][0]['frames'],0)
        self.service.quota=1
        self.assertFalse(self.service.enough_space(100))
    def test_crash_recovery_reuses_complete_frame_and_counts_missing_slot(self):
        pid=self.project(); path=self.frame(pid,1800000000)
        self.service.write('DELETE FROM frames WHERE project=?',(pid,))
        self.service.write("INSERT INTO attempts VALUES(?,?,'pending')",(pid,1800000000))
        self.service.write("INSERT INTO attempts VALUES(?,?,'pending')",(pid,1800000120))
        self.service.close(); self.service=Service(self.root/'state',self.db,self.root/'data',min_free=0)
        status=self.service.status()['projects'][0]
        self.assertEqual(status['frames'],1); self.assertEqual(status['missed'],1)
        self.service.recover_attempts(); self.assertEqual(self.service.status()['projects'][0]['missed'],1)
    def test_actual_incremental_encode_export_and_raw_cleanup(self):
        pid=self.project(width=640)
        for i in range(4): self.frame(pid,1800000000+i*120)
        self.service.action({'action':'export','project':pid})
        p=self.service.rows('SELECT * FROM projects WHERE id=?',(pid,))[0]; self.service.render(p)
        self.assertEqual(self.service.status()['projects'][0]['exported'],4,self.service.status())
        self.assertEqual([x.name for x in (self.service.root/pid).glob('*.jpg')],['poster.jpg'])
        segment=self.service.root/pid/'segment-000000.ts'; previous=segment.read_bytes()
        for i in range(3): self.frame(pid,1800000600+i*120)
        self.service.action({'action':'export','project':pid})
        self.service.render(self.service.rows('SELECT * FROM projects WHERE id=?',(pid,))[0])
        self.assertEqual(segment.read_bytes(),previous)
        video=self.service.root/pid/'export.mp4'
        probe=subprocess.check_output(['ffprobe','-v','error','-count_frames','-show_entries','stream=nb_read_frames','-of','json',str(video)],text=True)
        self.assertEqual(int(json.loads(probe)['streams'][0]['nb_read_frames']),7,self.service.status())
        self.assertEqual(self.service.status()['projects'][0]['exported'],7)
    def test_poster_backfill_for_existing_rendered_project(self):
        pid=self.project(width=640)
        self.frame(pid,1800000000)
        p=self.service.rows('SELECT * FROM projects WHERE id=?',(pid,))[0]
        self.service.render(p)
        poster=self.service.root/pid/'poster.jpg'
        poster.unlink()
        self.service.render(p)
        self.assertTrue(poster.read_bytes().startswith(b'\xff\xd8'))

    def finished_recording(self, ended, payload=65536):
        pid=self.project()
        self.service.write("UPDATE projects SET status='finished',ends=?,export=0 WHERE id=?",(ended,pid))
        folder=self.service.root/pid;folder.mkdir(exist_ok=True)
        (folder/'export.mp4').write_bytes(b'x'*payload)
        return pid

    def test_retention_days_delete_only_expired_finished_projects(self):
        now=1800000000
        old=self.finished_recording(now-8*86400)
        middle=self.finished_recording(now-4*86400)
        young=self.finished_recording(now-2*86400)
        fresh=self.finished_recording(now-3600)
        paused=self.project();self.service.action({'action':'pause','project':paused})
        for days,expected in [(7,old),(3,middle),(1,young)]:
            self.service.action({'action':'configure_retention','days':days})
            self.assertEqual(self.service.cleanup_retention(now),1)
            self.assertFalse((self.service.root/expected).exists())
        self.assertTrue((self.service.root/fresh).exists())
        self.assertEqual(self.service.rows('SELECT status FROM projects WHERE id=?',(paused,))[0]['status'],'paused')
        self.service.close()
        self.service=Service(self.root/'state',self.db,self.root/'data',min_free=0,quota=1024**3)
        self.assertEqual(self.service.global_settings()['retentionDays'],1)
        for bad in [True,2,-1,'7',None]:
            with self.assertRaises(ValueError):self.service.action({'action':'configure_retention','days':bad})

    def test_never_retention_reclaims_oldest_only_when_quota_needs_space(self):
        now=1800000000
        old=self.finished_recording(now-8*86400)
        newer=self.finished_recording(now-4*86400)
        self.assertEqual(self.service.cleanup_retention(now),0)
        usage=sum(p.stat().st_size for p in self.service.root.rglob('*') if p.is_file())
        self.service.quota=usage+32*1024**2-1
        self.service.next_retention=0
        self.assertEqual(self.service.cleanup_retention(now),1)
        self.assertFalse((self.service.root/old).exists())
        self.assertTrue((self.service.root/newer).exists())

    def test_retention_reserve_and_busy_workers_protect_files(self):
        from concurrent.futures import Future
        from collections import namedtuple
        Disk=namedtuple('Disk','total used free')
        now=1800000000;old=self.finished_recording(now-8*86400)
        self.service.capture_job=Future()
        self.assertEqual(self.service.cleanup_retention(now),0)
        self.service.capture_job.set_result(None)
        self.service.transfer_pending=True
        self.assertEqual(self.service.cleanup_retention(now),0)
        self.service.transfer_pending=False
        pending=self.finished_recording(now-10*86400)
        self.service.write('UPDATE projects SET export=1 WHERE id=?',(pending,))
        with patch('service.shutil.disk_usage',return_value=Disk(100,99,1)):
            self.assertEqual(self.service.cleanup_retention(now),1)
        self.assertFalse((self.service.root/old).exists())
        self.assertTrue((self.service.root/pending).exists())

    def test_channel_activation_is_explicit_persistent_and_preserves_settings(self):
        self.assertFalse(self.service.status()['channels'][0]['active'])
        self.service.action({'action':'set_channel_active','channel':CHANNEL,'active':True})
        self.assertTrue(self.service.status()['channels'][0]['active'])
        pid=self.project(interval=45,public=True)
        self.frame(pid,1800000000)
        before=self.service.rows('SELECT settings FROM channels WHERE id=?',(CHANNEL,))[0]['settings']
        self.service.action({'action':'set_channel_active','channel':CHANNEL,'active':False})
        self.assertEqual(self.service.status(CHANNEL,public=True),{'active':False,'projects':[]})
        with patch.object(self.service,'capture') as capture:
            self.service.tick(1800003600)
            capture.assert_not_called()
        self.assertEqual(self.service.rows('SELECT settings FROM channels WHERE id=?',(CHANNEL,))[0]['settings'],before)
        self.assertTrue(self.service.rows('SELECT * FROM frames WHERE project=?',(pid,)))
        self.service.close()
        self.service=Service(self.root/'state',self.db,self.root/'data',min_free=0,quota=1024**3)
        self.assertFalse(self.service.channel_active(CHANNEL))
        self.service.action({'action':'set_channel_active','channel':CHANNEL,'active':True})
        self.assertEqual(len(self.service.status(CHANNEL,public=True)['projects']),1)
        self.assertEqual(self.service.rows('SELECT settings FROM channels WHERE id=?',(CHANNEL,))[0]['settings'],before)

    def test_legacy_channel_migration_and_disabled_daily_schedule(self):
        self.service.configure(CHANNEL,{**DEFAULT,'mode':'daily','interval':45})
        self.service.close()
        import sqlite3
        with sqlite3.connect(self.root/'state/state.sqlite') as db:
            db.execute('ALTER TABLE channels DROP COLUMN active')
        self.service=Service(self.root/'state',self.db,self.root/'data',min_free=0,quota=1024**3)
        self.assertTrue(self.service.channel_active(CHANNEL))
        self.service.action({'action':'set_channel_active','channel':CHANNEL,'active':False})
        self.service.schedule(1800000000)
        self.assertEqual(self.service.rows('SELECT * FROM projects'),[])
        for bad in ['yes',1,None]:
            with self.assertRaises(ValueError):self.service.action({'action':'set_channel_active','channel':CHANNEL,'active':bad})
        with self.assertRaises(ValueError):self.service.action({'action':'set_channel_active','channel':'unknown','active':True})

    def test_private_public_authorization_ranges_and_nas_unavailable(self):
        pid=self.project(width=640,nas=True)
        self.frame(pid,1800000000); self.service.action({'action':'export','project':pid})
        self.service.render(self.service.rows('SELECT * FROM projects WHERE id=?',(pid,))[0])
        server=ThreadingHTTPServer(('127.0.0.1',0),make_handler(self.service))
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        base=f'http://127.0.0.1:{server.server_port}'
        try:
            self.assertEqual(json.load(urlopen(base+'/public/channel/'+CHANNEL))['projects'],[])
            with self.assertRaises(HTTPError) as ctx:urlopen(base+'/public/project/'+pid+'/index.m3u8')
            self.assertEqual(ctx.exception.code,404)
            with self.assertRaises(HTTPError) as ctx:urlopen(base+'/public/project/'+pid+'/poster.jpg')
            self.assertEqual(ctx.exception.code,404)
            self.service.action({'action':'publish','project':pid,'public':True})
            response=urlopen(base+'/public/project/'+pid+'/poster.jpg')
            self.assertEqual(response.headers['Content-Type'],'image/jpeg')
            self.assertTrue(response.read().startswith(b'\xff\xd8'))
            self.assertIn(b'#EXT-X-ENDLIST',urlopen(base+'/public/project/'+pid+'/index.m3u8').read())
            availability=base+'/public/channel/'+CHANNEL+'/availability'
            self.assertEqual(json.load(urlopen(availability)),{'active':True})
            self.service.action({'action':'set_channel_active','channel':CHANNEL,'active':False})
            self.assertEqual(json.load(urlopen(availability)),{'active':False})
            for filename in ['poster.jpg','index.m3u8','timeline.json','segment-000000.ts']:
                with self.assertRaises(HTTPError) as ctx:urlopen(base+'/public/project/'+pid+'/'+filename)
                self.assertEqual(ctx.exception.code,404)
            response=urlopen(Request(base+'/admin/project/'+pid+'/export.mp4',headers={'Range':'bytes=0-9'}))
            self.assertEqual(response.status,206);self.assertEqual(len(response.read()),10)
            from urllib.parse import unquote
            filename=self.service.status()['projects'][0]['filename']
            self.assertEqual(unquote(response.headers['Content-Disposition'].split("filename*=UTF-8''")[1]),filename)
            self.assertTrue(filename.startswith('Test_'))
            self.service.archive(self.service.rows('SELECT * FROM projects WHERE id=?',(pid,))[0])
            self.assertTrue((self.service.root/pid/'export.mp4').exists())
            self.assertIn('NAS nicht',self.service.status()['projects'][0]['nas'])
        finally:server.shutdown();server.server_close()
    def test_full_outage_skips_catchup_without_burst(self):
        pid=self.project(interval=600)
        captures=[]
        with patch.object(self.service,'capture',side_effect=lambda p,s:captures.append(s)):
            self.service.tick(1800003600);self.service.capture_job.result()
            self.service.tick(1800003601)
        self.assertEqual(len(captures),1)
        self.assertEqual(self.service.status()['projects'][0]['missed'],6)
    def test_nas_verified_copy_then_local_removal_only_when_finished(self):
        pid=self.project(nas=True)
        folder=self.service.root/pid;folder.mkdir()
        content=b'mp4-test-content'*1024
        (folder/'export.mp4').write_bytes(content)
        nas=self.root/'nas';nas.mkdir();(nas/'.nkl-timelapse-target').write_text('NKL_TIMELAPSE')
        with patch.dict(os.environ,{'NKL_TIMELAPSE_NAS':str(nas)}),patch('service.os.path.ismount',return_value=True):
            self.service.archive(self.service.rows('SELECT * FROM projects WHERE id=?',(pid,))[0])
            self.assertEqual((nas/(CHANNEL+'-'+pid+'.mp4')).read_bytes(),content)
            self.assertTrue((folder/'export.mp4').exists())
            self.service.action({'action':'stop','project':pid})
            self.service.write("UPDATE projects SET nas='' WHERE id=?",(pid,))
            self.service.archive(self.service.rows('SELECT * FROM projects WHERE id=?',(pid,))[0])
            self.assertFalse((folder/'export.mp4').exists())
        self.assertEqual(self.service.status()['projects'][0]['nas'],'gesichert')

    def test_stale_camera_playlist_is_rejected(self):
        import io
        from email.message import Message
        cfg=self.root/'data/channels'/CHANNEL/'config.js';cfg.parent.mkdir(parents=True)
        cfg.write_text('var playerConfig='+json.dumps({'source':CHANNEL+'.m3u8'})+';')
        class Response(io.BytesIO):
            headers=Message()
        with patch('service.urllib.request.urlopen',return_value=Response(b'#EXTM3U\n#EXT-X-PROGRAM-DATE-TIME:2026-01-01T00:00:00Z\n#EXTINF:2,\nold.ts\n')):
            with self.assertRaisesRegex(ValueError,'nicht aktuell'):self.service.fresh_source(CHANNEL,now=1800000000)

    def test_interval_changes_active_project_without_changing_video_format(self):
        pid=self.project(interval=120,width=640)
        self.service.configure(CHANNEL,{**DEFAULT,'mode':'season','interval':900,'width':1920})
        project=self.service.status()['projects'][0]
        self.assertEqual(project['settings']['interval'],900)
        self.assertEqual(project['settings']['width'],640)

    def test_pause_stop_resume_and_explicit_delete(self):
        pid=self.project()
        self.service.action({'action':'pause','project':pid}); self.assertEqual(self.service.status()['projects'][0]['status'],'paused')
        self.service.action({'action':'resume','project':pid},now=1800000300)
        self.assertEqual(self.service.rows('SELECT next FROM projects WHERE id=?',(pid,))[0]['next'],1800000300)
        self.service.action({'action':'stop','project':pid})
        self.service.action({'action':'delete','project':pid})
        self.assertEqual(self.service.status()['projects'],[])

if __name__=='__main__':unittest.main()
