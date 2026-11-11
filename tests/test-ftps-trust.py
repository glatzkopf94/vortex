#!/usr/bin/env python3
"""Real explicit TLS handshakes plus fail-closed data-channel regression tests."""
import hashlib
import ssl
import sqlite3
import json
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path
from unittest.mock import Mock, patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'bundle/timelapse'))
import transfer

class TrustTests(unittest.TestCase):
    def test_validation_scopes_and_revokes_trust(self):
        with tempfile.TemporaryDirectory() as root:
            trust={'host':'example.test','port':21,'sha256':'A'*64}
            config=transfer.configure(root,{'host':'example.test','tlsTrust':trust,'password':'secret'})
            self.assertEqual(config['tlsTrust']['sha256'],'a'*64)
            self.assertNotIn('password',config)
            self.assertEqual(transfer.read_config(root)['tlsTrust']['host'],'example.test')
            for changes in ({'host':'other.test'},{'port':2121},{'protocol':'ftp'}):
                self.assertIsNone(transfer.validate(root,{**config,**changes})['tlsTrust'])
            for invalid in ({**trust,'sha256':'*'},{**trust,'sha256':'a'*63},'anything'):
                with self.assertRaises(ValueError):transfer.validate(root,{'host':'example.test','tlsTrust':invalid})
            transfer.configure(root,{'host':'example.test','tlsTrust':None})
            self.assertIsNone(transfer.read_config(root)['tlsTrust'])

    def test_data_certificate_mismatch_closes_both_sockets(self):
        client=transfer.PinnedFTP_TLS('a'*64,8);client._prot_p=True
        connection=Mock();connection.getpeercert.return_value=b'different certificate'
        with patch.object(transfer.ReusingFTP_TLS,'ntransfercmd',return_value=(connection,10)),patch.object(client,'close') as close:
            with self.assertRaises(transfer.CertificatePinError):client.ntransfercmd('STOR movie.part')
            connection.close.assert_called_once();close.assert_called_once()

    def test_data_certificate_matches_and_plaintext_is_rejected(self):
        der=b'certificate';digest=hashlib.sha256(der).hexdigest()
        client=transfer.PinnedFTP_TLS(digest,8);connection=Mock();connection.getpeercert.return_value=der
        with patch.object(transfer.ReusingFTP_TLS,'ntransfercmd',return_value=(connection,10)):
            client._prot_p=True
            self.assertEqual(client.ntransfercmd('STOR movie.part'),(connection,10))
            client._prot_p=False
            with self.assertRaises(transfer.CertificatePinError):client.ntransfercmd('STOR movie.part')

    def test_real_explicit_tls_confirmation_and_rotation(self):
        try:
            from pyftpdlib.authorizers import DummyAuthorizer
            from pyftpdlib.handlers import TLS_FTPHandler
            from pyftpdlib.servers import FTPServer
        except ImportError:self.skipTest('Integration requires pyftpdlib and pyOpenSSL')
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);cert=root/'cert.pem';key=root/'key.pem';remote=root/'remote';remote.mkdir()
            subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-keyout',str(key),'-out',str(cert),'-days','1','-subj','/CN=private-test.invalid'],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            der=ssl.PEM_cert_to_DER_cert(cert.read_text());fingerprint=hashlib.sha256(der).hexdigest()
            auth=DummyAuthorizer();auth.add_user('test','secret',str(remote),perm='elradfmwMT')
            class Handler(TLS_FTPHandler):
                logins=0
                def ftp_USER(self,line):
                    type(self).logins+=1
                    return super().ftp_USER(line)
            Handler.certfile=str(cert);Handler.keyfile=str(key);Handler.authorizer=auth
            Handler.tls_control_required=True;Handler.tls_data_required=True
            server=FTPServer(('127.0.0.1',0),Handler)
            thread=threading.Thread(target=server.serve_forever,kwargs={'timeout':0.05},daemon=True);thread.start()
            config={**transfer.DEFAULT,'host':'127.0.0.1','port':server.socket.getsockname()[1],'username':'test','password':'secret'}
            try:
                result=transfer.test_connection(config)
                self.assertEqual(result['state'],'certificate_required')
                self.assertEqual(result['certificate']['sha256'],fingerprint)
                self.assertFalse(result['certificate']['changed'])
                self.assertEqual(Handler.logins,0)
                self.assertEqual(list(remote.iterdir()),[])
                self.assertNotIn('secret',str(result))
                self.assertFalse((root/'transfer-config.json').exists())
                config['tlsTrust']={k:result['certificate'][k] for k in ('host','port','sha256')}
                transfer.configure(root,config)
                result=transfer.test_connection(transfer.read_config(root))
                self.assertEqual(result['state'],'success',result)
                self.assertEqual(Handler.logins,1)
                self.assertEqual(list(remote.iterdir()),[])
                with sqlite3.connect(root/'state.sqlite') as db:
                    db.execute('CREATE TABLE projects(id,channel,day)')
                    db.execute("INSERT INTO projects VALUES('movie','camera','2026-11-09')")
                (root/'movie').mkdir();(root/'movie'/'export.mp4').write_bytes(b'video-content'*10000)
                transfer.execute(root,plan={'origin':'manual','files':{'movie':'camera.mp4'}})
                self.assertEqual(json.loads((root/'transfer-result.json').read_text())['state'],'success')
                self.assertEqual((remote/'camera.mp4').read_bytes(),(root/'movie'/'export.mp4').read_bytes())
                self.assertEqual(Handler.logins,2)
                # Simulate a previously accepted certificate being replaced.
                config['tlsTrust']={**config['tlsTrust'],'sha256':'0'*64}
                result=transfer.test_connection(config)
                self.assertEqual(result['state'],'certificate_required')
                self.assertTrue(result['certificate']['changed'])
                self.assertEqual(Handler.logins,2,'No USER/PASS before matching pin')
                # Automated path raises; it never silently accepts a replacement.
                client=transfer.ftp_client(config,8)
                try:
                    client.connect(config['host'],config['port'])
                    with self.assertRaises(transfer.CertificatePinError):client.login('test','secret')
                finally:client.close()
                self.assertEqual(Handler.logins,2)
            finally:server.close_all();thread.join(timeout=2)

if __name__=='__main__':unittest.main()
