import json
import stat
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

import service


def frames(codec='h264', duplicate=False):
    stamp = (lambda i: 0 if duplicate else i/20)
    return '\n'.join([f'frame|best_effort_timestamp_time={stamp(i)}' for i in range(120)]
                     + [f'stream|codec_name={codec}|width=2560|height=1440'])


class ReceiverTests(unittest.TestCase):
    def test_probe_requires_decoded_timestamps_and_camera_codec(self):
        self.assertIn('2560 × 1440', service.evaluate(frames(), 6))
        for data, seconds in [(frames('mjpeg'), 6), (frames(), 30), (frames(duplicate=True), 6), ('', 0)]:
            with self.assertRaises(ValueError):
                service.evaluate(data, seconds)

    def test_store_and_rename(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(service,'ROOT',Path(tmp)), \
             patch.dict(service.cameras,clear=True), patch.dict(service.workers,clear=True), \
             patch.object(service,'start') as start:
            body=dict(name='Test',uid='SIMULATED',username='viewer',password='abc"123',profile='rlc810wa')
            camera=service.save(body)
            self.assertEqual(set(camera),{'id','name','port','uid','username'})
            worker=service.workers[camera['id']]=Mock()
            renamed=service.save({**camera,'name':'Werkstatt'})
            self.assertEqual(renamed['id'],camera['id'])
            start.assert_called_once()
            worker.terminate.assert_not_called()
            path=Path(tmp)/'cameras.json'
            self.assertEqual(stat.S_IMODE(path.stat().st_mode),0o600)
            self.assertEqual(json.loads(path.read_text())[camera['id']]['password'],body['password'])
            self.assertNotIn(body['password'],json.dumps(service.dispatch('/cameras',{})))
            with self.assertRaises(ValueError):
                service.save(body)
            service.save({**renamed,'profile':'auto'})
            worker.terminate.assert_not_called()

    def test_failure_checks_only_once(self):
        cam = dict(id='test', profile='auto', detected='rlc810wa')
        job = {'status':'running'}
        with patch.dict(service.workers, {'test':Mock()}), patch.dict(service.tests, {'test':job}), patch.object(service,'restart') as restart, \
             patch.object(service,'check_stream',side_effect=ValueError('Keine Videopakete')) as check:
            service.probe(cam,'sub',job)
            check.assert_called_once_with(cam,'sub',job)
            restart.assert_called_once_with('test')
            self.assertIn('Keine Videopakete', job['message'])
            self.assertEqual(job['status'], 'error')

    def test_core_failure_restarts_once_and_rejects_stale_result(self):
        job = dict(status='ok', stream='main', token='abc')
        body = dict(id='cam', stream='main', token='abc', core_failed=True)
        with patch.dict(service.cameras, {'cam':{}}), patch.dict(service.tests, {'cam':job}), patch.object(service,'restart') as restart:
            with self.assertRaises(ValueError):
                service.dispatch('/status', {**body, 'token':'old'})
            restart.assert_not_called()
            for _ in range(2):
                self.assertEqual(service.dispatch('/status', body)['status'], 'error')
            restart.assert_called_once_with('cam')

    def test_login_rejection_stops_before_profile_retry(self):
        cam=dict(id='test',profile='auto')
        job={'status':'running'}
        with patch.dict(service.tests,{'test':job},clear=True), patch.dict(service.states,{'test':'Kamera gefunden, Anmeldung abgelehnt'}), \
             patch.object(service,'restart') as restart, patch.object(service,'sample') as sample:
            service.probe(cam,'main',job)
            sample.assert_not_called()
            restart.assert_not_called()
            self.assertEqual(job['status'],'error')
            self.assertIn('Anmeldung abgelehnt',job['message'])

    def test_toml_roundtrip_and_profile(self):
        import tomllib
        with tempfile.TemporaryDirectory() as tmp, patch.object(service,'ROOT',Path(tmp)), \
             patch('service.subprocess.Popen') as popen, patch('service.threading.Thread'), \
             patch.dict(service.workers,clear=True), patch.dict(service.states,clear=True):
            cam=dict(id='a'*32,port=18554,uid='TESTONLY',username='viewer',password='ä\\b"c',profile='rlc810wa')
            service.start(cam)
            config=tomllib.loads((Path(tmp)/(cam['id']+'.toml')).read_text())
            conf=config['cameras'][0]
            self.assertEqual(conf['password'],cam['password'])
            self.assertFalse(conf['use_splash'])
            self.assertFalse(conf['push_notifications'])
            self.assertEqual(conf['discovery'],'relay')
            self.assertNotIn(cam['password'],str(popen.call_args.args))
            self.assertEqual(popen.call_args.kwargs['env']['VORTEX_ACK_PROFILE'],'dynamic')


if __name__=='__main__':
    unittest.main()
