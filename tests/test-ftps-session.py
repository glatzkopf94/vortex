#!/usr/bin/env python3
"""Loopback FTPS fixture requiring real TLS control/data session reuse.
No external service or credentials; both TLS 1.2 and TLS 1.3 are exercised.
"""
import ftplib
import hashlib
import io
import socket
import ssl
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bundle/timelapse'))
import transfer

class StrictServer:
    def __init__(self,cert,key,version):
        self.context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        self.context.minimum_version=self.context.maximum_version=version
        self.context.load_cert_chain(cert,key)
        self.listener=socket.socket();self.listener.bind(('127.0.0.1',0));self.listener.listen(5)
        self.listener.settimeout(.2);self.port=self.listener.getsockname()[1]
        self.stop=False;self.files={};self.reused=[];self.errors=[];self.logins=0
        self.thread=threading.Thread(target=self.run,daemon=True);self.thread.start()
    def close(self):
        self.stop=True;self.listener.close();self.thread.join(4)
    def run(self):
        while not self.stop:
            try:connection,_=self.listener.accept()
            except socket.timeout:continue
            except OSError:break
            try:self.serve(connection)
            except (ConnectionError,ssl.SSLError):pass # rejected certificate / client closes
            except Exception as error:self.errors.append(repr(error))
            finally:connection.close()
    def serve(self,connection):
        connection.settimeout(4);passive=None;rename=None
        def reply(line):connection.sendall((line+'\r\n').encode())
        def read_line():
            data=b''
            while not data.endswith(b'\r\n'):
                char=connection.recv(1)
                if not char:return ''
                data+=char
                if len(data)>8192:raise ValueError('FTP line too long')
            return data.decode().rstrip('\r\n')
        try:
            reply('220 Strict session-reuse FTPS fixture')
            while True:
                line=read_line()
                if not line:break
                command,_,arg=line.partition(' ')
                if command=='AUTH':
                    reply('234 Begin TLS');connection=self.context.wrap_socket(connection,server_side=True)
                elif command=='USER':self.logins+=1;reply('331 Password required')
                elif command=='PASS':reply('230 Logged in')
                elif command in ('PBSZ','PROT','TYPE'):reply('200 OK')
                elif command=='CWD':reply('250 Directory changed' if arg=='/mrkarr.de/public_html/nestcam' or arg=='/' else '550 Failed to change directory.')
                elif command=='PWD':reply('257 "/mrkarr.de/public_html/nestcam"')
                elif command=='PASV':
                    if passive:passive.close()
                    passive=socket.socket();passive.bind(('127.0.0.1',0));passive.listen(1);passive.settimeout(4)
                    port=passive.getsockname()[1];reply(f'227 Passive (127,0,0,1,{port//256},{port%256})')
                elif command in ('NLST','STOR','LIST'):
                    raw,_=passive.accept();raw.settimeout(4);passive.close();passive=None
                    reply('150 Open data connection')
                    with self.context.wrap_socket(raw,server_side=True) as data:
                        reused=data.session_reused;self.reused.append(reused)
                        if reused:
                            if command=='STOR':
                                contents=b''
                                while True:
                                    block=data.recv(65536)
                                    if not block:break
                                    contents+=block
                                self.files[arg]=contents
                            else:data.sendall(b'test.txt\r\n')
                        data.unwrap().close()
                    reply('226 Transfer complete' if reused else '522 SSL connection failed: session reuse required')
                elif command=='SIZE':reply('213 '+str(len(self.files[arg])))
                elif command=='RNFR':rename=arg;reply('350 Ready')
                elif command=='RNTO':self.files[arg]=self.files.pop(rename);reply('250 Renamed')
                elif command=='DELE':self.files.pop(arg,None);reply('250 Deleted')
                elif command=='QUIT':reply('221 Goodbye');break
                else:reply('502 Unsupported command')
        finally:
            if passive:passive.close()
            connection.close()

class SessionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();cls.root=Path(cls.temp.name)
        cls.cert=cls.root/'cert.pem';cls.key=cls.root/'key.pem'
        subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-keyout',str(cls.key),'-out',str(cls.cert),'-days','1','-subj','/CN=localhost','-addext','subjectAltName=IP:127.0.0.1,DNS:localhost'],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        cls.fingerprint=hashlib.sha256(ssl.PEM_cert_to_DER_cert(cls.cert.read_text())).hexdigest()
    @classmethod
    def tearDownClass(cls):cls.temp.cleanup()
    def config(self,server,pin=True):
        return {**transfer.DEFAULT,'host':'127.0.0.1','port':server.port,'username':'test','password':'test-secret','directory':'/mrkarr.de/public_html/nestcam','tlsTrust':{'host':'127.0.0.1','port':server.port,'sha256':self.fingerprint} if pin else None}
    def test_real_tls_versions_with_pinned_and_ca_verified_connections(self):
        for version in (ssl.TLSVersion.TLSv1_2,ssl.TLSVersion.TLSv1_3):
            for pin in (True,False):
                with self.subTest(version=version,pin=pin):
                    server=StrictServer(self.cert,self.key,version)
                    config=self.config(server,pin)
                    context=ssl.create_default_context(cafile=str(self.cert))
                    try:
                        with patch('transfer.ssl.create_default_context',return_value=context):
                            result=transfer.test_connection(config)
                            self.assertEqual(result['state'],'success',result)
                            client=transfer.ftp_client(config,4)
                            try:
                                client.connect(config['host'],config['port']);client.login(config['username'],config['password']);client.prot_p()
                                client.cwd(config['directory'])
                                source=self.root/'movie.mp4';source.write_bytes(b'video-content'*100000)
                                transfer.upload_one(client,source,'movie.mp4')
                                self.assertEqual(server.files['movie.mp4'],source.read_bytes())
                                # Repeated data connections on the same control session.
                                transfer.upload_one(client,source,'second.mp4')
                                self.assertEqual(server.files['second.mp4'],source.read_bytes())
                            finally:client.close()
                        self.assertEqual(server.reused,[True]*4)
                        self.assertFalse(any(name.endswith('.tmp') or name.endswith('.part') for name in server.files))
                    finally:server.close()
                    self.assertEqual(server.errors,[])
    def test_original_client_reproduces_522(self):
        server=StrictServer(self.cert,self.key,ssl.TLSVersion.TLSv1_2)
        client=ftplib.FTP_TLS(context=ssl.create_default_context(cafile=str(self.cert)),timeout=4)
        try:
            client.connect('127.0.0.1',server.port);client.login('test','test-secret');client.prot_p()
            with self.assertRaisesRegex(ftplib.error_perm,'522.*session reuse required'):client.nlst()
            self.assertEqual(server.reused,[False])
        finally:client.close();server.close()
    def test_changed_certificate_never_sends_credentials(self):
        server=StrictServer(self.cert,self.key,ssl.TLSVersion.TLSv1_3)
        config=self.config(server);config['tlsTrust']['sha256']='0'*64
        client=transfer.ftp_client(config,4)
        try:
            client.connect('127.0.0.1',server.port)
            with self.assertRaises(transfer.CertificatePinError):client.login('test','test-secret')
            self.assertEqual(server.logins,0)
        finally:client.close();server.close()
    def test_untrusted_ca_requires_confirmation_without_credentials(self):
        server=StrictServer(self.cert,self.key,ssl.TLSVersion.TLSv1_3)
        try:
            result=transfer.test_connection(self.config(server,pin=False))
            self.assertEqual(result['state'],'certificate_required',result)
            self.assertEqual(result['certificate']['sha256'],self.fingerprint)
            self.assertEqual(server.logins,0)
        finally:server.close()
    def test_wrong_path_exposes_real_server_reply(self):
        server=StrictServer(self.cert,self.key,ssl.TLSVersion.TLSv1_3)
        config=self.config(server);config['directory']='/nestcam'
        try:
            result=transfer.test_connection(config)
            self.assertEqual(result['state'],'error')
            self.assertIn('Zielordner abgelehnt',result['message'])
            self.assertIn('550 Failed to change directory.',result['message'])
            self.assertEqual(server.reused,[])
        finally:server.close()
    def test_handshake_failure_closes_data_and_control(self):
        context=Mock();context.wrap_socket.side_effect=ssl.SSLError('handshake failed')
        client=transfer.ReusingFTP_TLS(context=context);client._prot_p=True;client.sock=Mock();connection=Mock()
        with patch.object(ftplib.FTP,'ntransfercmd',return_value=(connection,0)),patch.object(client,'close') as close:
            with self.assertRaises(ssl.SSLError):client.ntransfercmd('NLST')
            connection.close.assert_called_once();close.assert_called_once()
    def test_server_reply_is_bounded_and_password_redacted(self):
        text=transfer.friendly_error(ftplib.error_perm('522 session reuse required\r\nsecret\x00'+'x'*500),'Verzeichnis lesen',('secret',))
        self.assertIn('session reuse required',text);self.assertIn('Serverantwort:',text)
        self.assertNotIn('secret',text);self.assertNotIn('\r',text);self.assertNotIn('\n',text);self.assertNotIn('\x00',text)
        self.assertLess(len(text),510)
        self.assertIn('Failed to change directory',transfer.friendly_error(ftplib.error_perm('550 Failed to change directory.'),'Zielordner'))

if __name__=='__main__':unittest.main()
