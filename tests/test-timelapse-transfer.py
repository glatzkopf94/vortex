#!/usr/bin/env python3
import json
import socket
import threading
import time
import io
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bundle/timelapse'))
import transfer

class FTP:
    def __init__(self):self.files={};self.protected=False;self.fail=False;self.sock=self
    def settimeout(self,value):self.socket_timeout=value
    def connect(self,*args):pass
    def login(self,*args):pass
    def prot_p(self):self.protected=True
    def set_pasv(self,value):assert value
    def cwd(self,directory):pass
    def retrlines(self,command,callback):callback("USB-Stick")
    def voidcmd(self,value):return '200 OK'
    def storbinary(self,command,stream,blocksize,callback=None):
        if self.fail:raise OSError('connection lost')
        self.files[command[5:]]=stream.read()
        if callback:callback(self.files[command[5:]])
    def transfercmd(self,command):
        if self.fail:raise OSError('connection lost')
        owner=self
        class Connection:
            def __init__(self):
                self.sender,self.receiver=socket.socketpair();self.chunks=[]
                self.thread=threading.Thread(target=self.read);self.thread.start()
            def read(self):
                while True:
                    chunk=self.receiver.recv(65536)
                    if not chunk:break
                    self.chunks.append(chunk)
                self.receiver.close()
            def __enter__(self):return self.sender
            def __exit__(self,*args):
                self.sender.close();self.thread.join()
                owner.files[command[5:]]=b''.join(self.chunks)
        return Connection()
    def voidresp(self):return '226 Complete'
    def size(self,path):return len(self.files[path])
    def rename(self,source,target):self.files[target]=self.files.pop(source)
    def delete(self,path):self.files.pop(path,None)
    def close(self):pass

class TransferTests(unittest.TestCase):
    def test_ftps_incremental_upload_failure_and_local_retention(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);pid='00000000-0000-0000-0000-000000000001';channel='00000000-0000-0000-0000-000000000002'
            with sqlite3.connect(root/'state.sqlite') as db:
                db.execute('CREATE TABLE projects(id,channel,day)');db.execute('INSERT INTO projects VALUES(?,?,?)',(pid,channel,'2026-10-07'))
            folder=root/pid;folder.mkdir();source=folder/'export.mp4';source.write_bytes(b'original export')
            transfer.configure(root,{'enabled':True,'host':'test.invalid','username':'user','password':'test-only'})
            transfer.configure(root,{'enabled':True,'host':'test.invalid','username':'user','password':''})
            self.assertEqual(transfer.read_config(root)['password'],'test-only')
            ftp=FTP()
            with patch('transfer.ftplib.FTP_TLS',return_value=ftp) as factory:
                transfer.execute(root)
                self.assertTrue(ftp.protected)
                self.assertTrue(factory.call_args.kwargs['context'].check_hostname)
                self.assertEqual(factory.call_args.kwargs['context'].verify_mode,2)
                self.assertEqual(json.loads((root/'transfer-result.json').read_text())['uploaded'],1)
                transfer.execute(root)
                self.assertEqual(json.loads((root/'transfer-result.json').read_text())['uploaded'],0)
                self.assertTrue(source.exists())
                old=dict(ftp.files);source.write_bytes(b'new updated export');ftp.fail=True
                transfer.execute(root)
                self.assertEqual(json.loads((root/'transfer-result.json').read_text())['state'],'error')
                self.assertEqual(ftp.files,old);self.assertTrue(source.exists())
                ftp.fail=False;transfer.execute(root)
                self.assertEqual(list(ftp.files.values()),[b'new updated export'])
            self.assertEqual((root/'transfer-config.json').stat().st_mode&0o777,0o600)
    def test_readable_filenames_and_collisions(self):
        projects=[{'id':'a','channel':'one','day':'2026-10-11'}, {'id':'b','channel':'two','day':'2026-10-10'}]
        names=transfer.filenames(projects,{'one':'Webcam','two':'Nest/Innen'})
        self.assertEqual(names['a'],'Webcam_11.10.2026.mp4')
        self.assertEqual(names['b'],'Nest_Innen_10.10.2026.mp4')
        projects.append({'id':'c','channel':'one','day':'2026-10-11'})
        names=transfer.filenames(projects,{'one':'Webcam'})
        self.assertEqual(len(set(names.values())),3)
        self.assertTrue(all('/' not in v for v in names.values()))

    def test_manual_plan_uses_readable_name_and_selected_file_only(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            with sqlite3.connect(root/'state.sqlite') as db:
                db.execute('CREATE TABLE projects(id,channel,day)')
                for pid in ['a','b']:
                    db.execute('INSERT INTO projects VALUES(?,?,?)',(pid,'camera','2026-10-11'))
                    (root/pid).mkdir();(root/pid/'export.mp4').write_bytes(b'video')
            transfer.configure(root,{'host':'test.invalid','username':'user','enabled':False})
            ftp=FTP()
            with patch('transfer.ftplib.FTP_TLS',return_value=ftp):transfer.execute(root,plan={'origin':'manual','files':{'b':'Webcam_11.10.2026.mp4'}})
            self.assertEqual(set(ftp.files),{'Webcam_11.10.2026.mp4'})
            self.assertEqual(json.loads((root/'transfer-result.json').read_text())['origin'],'manual')

    def test_slow_progress_can_exceed_idle_deadline(self):
        class Connection:
            def setblocking(self,value):pass
            def send(self,block):return 1
        clock=[0.0];events=[]
        def ready(read,write,errors,timeout):
            clock[0]+=0.4
            return read,write,[]
        with patch('transfer.time.monotonic',side_effect=lambda:clock[0]),patch('transfer.select.select',side_effect=ready):
            sent=transfer.send_stream(Connection(),io.BytesIO(b'1234567890'),lambda n,idle:events.append((n,idle)),idle_timeout=1)
        self.assertEqual(sent,10);self.assertGreater(clock[0],1)

    def test_stalled_upload_expires_and_reports_idle(self):
        class Connection:
            def setblocking(self,value):pass
        clock=[0.0];events=[]
        def waiting(*args):
            clock[0]+=1;return [],[],[]
        with patch('transfer.time.monotonic',side_effect=lambda:clock[0]),patch('transfer.select.select',side_effect=waiting):
            with self.assertRaises(TimeoutError):
                transfer.send_stream(Connection(),io.BytesIO(b'data'),lambda n,idle:events.append((n,idle)),idle_timeout=3)
        self.assertEqual(events[-1],(0,3))

    def test_channel_selection_preserves_other_upload_records(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            with sqlite3.connect(root/'state.sqlite') as db:
                db.execute('CREATE TABLE projects(id,channel,day)')
                for pid,channel in [('a','one'),('b','two')]:
                    db.execute('INSERT INTO projects VALUES(?,?,?)',(pid,channel,'2026-10-11'))
                    (root/pid).mkdir();(root/pid/'export.mp4').write_bytes(b'video')
            transfer.configure(root,{'enabled':True,'host':'test.invalid','username':'user'})
            ftp=FTP()
            with patch('transfer.ftplib.FTP_TLS',return_value=ftp):
                transfer.execute(root,'one')
                self.assertEqual(set(ftp.files),{'one-a.mp4'})
                transfer.execute(root,'two')
                self.assertEqual(set(json.loads((root/'transfer-records.json').read_text())),{'a','b'})
                transfer.execute(root)
                self.assertEqual(json.loads((root/'transfer-result.json').read_text())['uploaded'],0)
                self.assertEqual(ftp.socket_timeout,120)

    def test_timeout_retains_progress_and_previous_finished_video(self):
        with tempfile.TemporaryDirectory() as temporary:
            source=Path(temporary)/'export.mp4';source.write_bytes(b'new-video')
            ftp=FTP();ftp.files['movie.mp4']=b'old-video';events=[]
            def stalled(connection,stream,report):
                block=stream.read(3);connection.sendall(block);report(3,120)
                raise TimeoutError('secret')
            with patch('transfer.send_stream',side_effect=stalled):
                with self.assertRaises(TimeoutError):transfer.upload_one(ftp,source,'movie.mp4',lambda **v:events.append(v))
            self.assertEqual(events[-1]['sentBytes'],3)
            self.assertEqual(ftp.files['movie.mp4'],b'old-video')
            self.assertEqual(source.read_bytes(),b'new-video')
            transfer.upload_one(ftp,source,'movie.mp4')
            self.assertEqual(ftp.files,{'movie.mp4':b'new-video'})

    def test_real_local_ftp_roundtrip(self):
        try:
            from pyftpdlib.authorizers import DummyAuthorizer
            from pyftpdlib.handlers import FTPHandler
            from pyftpdlib.servers import FTPServer
        except ImportError:self.skipTest('Optional pyftpdlib required for loopback FTP integration')
        import threading
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);remote=root/'remote';remote.mkdir();pid='00000000-0000-0000-0000-000000000003'
            with sqlite3.connect(root/'state.sqlite') as db:
                db.execute('CREATE TABLE projects(id,channel,day)');db.execute('INSERT INTO projects VALUES(?,?,?)',(pid,'camera','2026-10-07'))
            (root/pid).mkdir();(root/pid/'export.mp4').write_bytes(b'loopback-file'*10000)
            auth=DummyAuthorizer();auth.add_user('test','test-password',str(remote),perm='elradfmwMT')
            class Handler(FTPHandler):pass
            Handler.authorizer=auth
            server=FTPServer(('127.0.0.1',0),Handler)
            thread=threading.Thread(target=server.serve_forever,kwargs={'timeout':0.05},daemon=True);thread.start()
            try:
                transfer.configure(root,{'enabled':True,'protocol':'ftp','host':'127.0.0.1','port':server.socket.getsockname()[1],'username':'test','password':'test-password'})
                probe=transfer.test_connection(transfer.read_config(root))
                self.assertEqual(probe['state'],'success')
                self.assertFalse(list(remote.glob('vortex-connection-test-*')))
                transfer.execute(root)
                self.assertEqual(json.loads((root/'transfer-result.json').read_text())['state'],'success')
                self.assertEqual((remote/('camera-'+pid+'.mp4')).read_bytes(),(root/pid/'export.mp4').read_bytes())
                self.assertFalse(list(remote.glob('*.part')))
                (root/pid/'export.mp4').write_bytes(b'new version')
                transfer.execute(root)
                self.assertEqual((remote/('camera-'+pid+'.mp4')).read_bytes(),b'new version')
            finally:server.close_all();thread.join(timeout=2)

    def test_connection_uses_unsaved_port_and_cleans_probe(self):
        with tempfile.TemporaryDirectory() as root:
            config=transfer.validate(root,{'host':'test.invalid','port':40357,'username':'user','password':'secret'})
            ftp=FTP()
            with patch('transfer.ftplib.FTP_TLS',return_value=ftp),patch.object(ftp,'connect') as connect:
                result=transfer.test_connection(config)
                connect.assert_called_once_with('test.invalid',40357)
            self.assertEqual(result['state'],'success')
            self.assertEqual(result['entries'],['USB-Stick'])
            self.assertEqual(ftp.files,{})
            self.assertFalse((Path(root)/'transfer-config.json').exists())
            self.assertNotIn('secret',json.dumps(result))

    def test_connection_errors_are_specific_and_hide_credentials(self):
        import ssl
        config={**transfer.DEFAULT,'host':'test.invalid','username':'user','password':'secret'}
        for error,text in [(transfer.ftplib.error_perm('530 secret'),'Anmeldung'),(ssl.SSLCertVerificationError('secret'),'TLS-Zertifikat'),(ConnectionRefusedError('secret'),'abgelehnt')]:
            with patch('transfer.ftplib.FTP_TLS',side_effect=error):result=transfer.test_connection(config)
            self.assertEqual(result['state'],'error');self.assertIn(text,result['message']);self.assertNotIn('secret',result['message'])

    def test_rejects_ftp_command_injection(self):
        with tempfile.TemporaryDirectory() as root:
            for field in ['host','username','password','directory']:
                with self.assertRaises(ValueError):transfer.configure(root,{field:'bad\r\nDELE test'})
            with self.assertRaises(ValueError):transfer.configure(root,{'directory':'/../other'})

if __name__=='__main__':unittest.main()
