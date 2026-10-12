#!/usr/bin/env python3
# Modified 2026-10-11: validated FTP connection tests and actionable errors.
"""Bounded FTP/explicit-FTPS worker for local MP4 exports. No local deletion."""
import ftplib
import io
import socket
import select
import json
import os
from pathlib import Path
import re
import sqlite3
import ssl
import sys
import time
import uuid
from datetime import datetime
from zoneinfo import ZoneInfo
import unicodedata

DEFAULT={'enabled':False,'protocol':'ftps','host':'','port':21,'username':'','password':'','directory':'/','intervalMinutes':60,'mode':'both','autoChannels':[],'onlyFinished':False}

def read_config(root):
    path=Path(root)/'transfer-config.json'
    return {**DEFAULT,**json.loads(path.read_text())} if path.is_file() else dict(DEFAULT)

def safe_config(config):
    return {**{k:v for k,v in config.items() if k!='password'},'passwordConfigured':bool(config.get('password'))}

def save_json(path,data,private=False):
    path=Path(path);temp=path.with_name('.'+path.name+'.'+uuid.uuid4().hex)
    try:
        with os.fdopen(os.open(temp,os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600 if private else 0o644),'w') as f:
            json.dump(data,f);f.flush();os.fsync(f.fileno())
        os.replace(temp,path)
    finally:temp.unlink(missing_ok=True)

def validate(root,raw):
    if not isinstance(raw,dict):raise ValueError('Ungueltige Uebertragungseinstellungen')
    previous=read_config(root);config={**DEFAULT,**{k:v for k,v in raw.items() if k in DEFAULT}}
    if not raw.get('password'):config['password']=previous['password']
    if config['protocol'] not in ('ftp','ftps') or config['mode'] not in ('daily','season','both'):raise ValueError('Ungueltige Uebertragungsart')
    if not isinstance(config['onlyFinished'],bool):raise ValueError('Ungültiger Aufnahmefilter')
    if not isinstance(config['autoChannels'],list) or len(config['autoChannels'])>1000 or any(not isinstance(c,str) or not re.fullmatch(r'[0-9a-f-]{36}',c) for c in config['autoChannels']):raise ValueError('Ungültige Kanalauswahl')
    if not isinstance(config['enabled'],bool):raise ValueError('Ungueltiger Aktivierungswert')
    for key,low,high in [('port',1,65535),('intervalMinutes',1,1440)]:
        if type(config[key]) is not int or not low<=config[key]<=high:raise ValueError(('Port muss eine ganze Zahl zwischen 1 und 65535 sein.' if key=='port' else 'Übertragungsintervall muss zwischen 1 und 1440 Minuten liegen.'))
    for key in ['host','username','password','directory']:
        if not isinstance(config[key],str) or any(c in config[key] for c in '\r\n\x00'):raise ValueError('Ungueltiges Feld: '+key)
    if any(part=='..' for part in config['directory'].split('/')):raise ValueError('Zielordner darf kein .. enthalten')
    if config['enabled'] and (not config['host'] or not config['username']):raise ValueError('Server und Benutzername erforderlich')
    if '/' in config['host'] or '://' in config['host']:raise ValueError('Server ohne Protokoll oder Pfad eingeben')
    return config

def configure(root,raw):
    config=validate(root,raw)
    save_json(Path(root)/'transfer-config.json',config,private=True)
    return safe_config(config)

def filenames(projects,names):
    result={};groups={}
    for p in projects:
        name=unicodedata.normalize('NFC',names.get(p['channel'],'Kanal'))
        name=re.sub(r'[\x00-\x1f<>:"/\\|?*]', '_',name).strip(' .')[:80] or 'Kanal'
        try:
            if p.get('day'):stamp=datetime.strptime(p['day'],'%Y-%m-%d').strftime('%d.%m.%Y')
            else:
                settings=json.loads(p.get('settings') or '{}')
                stamp='Saison_ab_'+datetime.fromtimestamp(p['started'],ZoneInfo(settings.get('timezone','Europe/Berlin'))).strftime('%d.%m.%Y')
        except (ValueError,KeyError,TypeError):stamp='Aufnahme'
        stem=name.encode('utf-8')[:120].decode('utf-8','ignore')+'_'+stamp
        groups.setdefault(stem.casefold(),[]).append(p['id']);result[p['id']]=stem
    for ids in groups.values():
        if len(ids)>1:
            for pid in ids:result[pid]+='_'+pid
    return {pid:stem+'.mp4' for pid,stem in result.items()}


def send_stream(connection,stream,report,idle_timeout=120):
    """Bounded buffer; timeout measures lack of successful socket writes only."""
    connection.setblocking(False)
    sent=0;last=time.monotonic();pending=b'';want_read=False
    while True:
        if not pending:
            pending=stream.read(65536)
            if not pending:break
        idle=time.monotonic()-last
        report(sent,idle)
        if idle>=idle_timeout:raise TimeoutError('No upload progress')
        ready=select.select([connection] if want_read else [],[] if want_read else [connection],[],min(1,idle_timeout-idle))
        if not ready[0] and not ready[1]:continue
        try:
            count=connection.send(pending)
        except ssl.SSLWantReadError:
            want_read=True;continue
        except (ssl.SSLWantWriteError,BlockingIOError):
            want_read=False;continue
        if count<=0:raise ConnectionError('Data connection closed')
        pending=pending[count:];sent+=count;last=time.monotonic();want_read=False
        report(sent,0)
    return sent


def upload_one(ftp,source,remote,progress=None):
    temporary='.'+remote+'.nkl-upload.part'
    progress=progress or (lambda **values: None)
    sent=0
    try:
        with source.open('rb') as stream:
            size=os.fstat(stream.fileno()).st_size
            progress(phase='Datei übertragen',sentBytes=0,totalBytes=size,file=remote)
            ftp.voidcmd('TYPE I')
            with ftp.transfercmd('STOR '+temporary) as connection:
                def advanced(count,idle):
                    progress(phase='Datei übertragen',sentBytes=count,totalBytes=size,file=remote,
                             idleSeconds=int(idle),heartbeatAt=time.time())
                sent=send_stream(connection,stream,advanced)
                progress(phase='Abschlussbestätigung abwarten',sentBytes=sent,totalBytes=size,file=remote,idleSeconds=0)
                if isinstance(connection,ssl.SSLSocket):
                    connection.settimeout(120)
                    connection.unwrap()
            ftp.voidresp()
        progress(phase='Dateigröße prüfen',sentBytes=sent,totalBytes=size,file=remote)
        ftp.voidcmd('TYPE I')
        if ftp.size(temporary)!=size:raise ValueError('Remote size mismatch')
        progress(phase='Datei fertigstellen',sentBytes=sent,totalBytes=size,file=remote)
        ftp.rename(temporary,remote)
    except Exception:
        # A timed-out control connection must not be reused for cleanup: its
        # pending reply may belong to STOR. The next upload replaces this part.
        ftp.close()
        raise


def execute(root,channel=None,plan=None):
    root=Path(root);config=read_config(root)
    if not config['enabled'] and plan is None:return
    now=time.time();save_json(root/'transfer-result.json',{'state':'running','at':now,'uploaded':0,'origin':(plan or {}).get('origin','automatic')})
    ftp=None;details={'origin':(plan or {}).get('origin','automatic')};last_write=0
    def progress(**values):
        nonlocal last_write
        changed=details.get('phase')!=values.get('phase')
        details.update(values)
        if changed or time.monotonic()-last_write>=1:
            save_json(root/'transfer-result.json',{'state':'running','at':time.time(),**details})
            last_write=time.monotonic()
    try:
        progress(phase='Verbindung und Anmeldung')
        ftp=ftplib.FTP_TLS(context=ssl.create_default_context(),timeout=20) if config['protocol']=='ftps' else ftplib.FTP(timeout=20)
        ftp.connect(config['host'],config['port']);ftp.login(config['username'],config['password'])
        if config['protocol']=='ftps':ftp.prot_p()
        ftp.timeout=120
        ftp.sock.settimeout(120)
        progress(phase='Zielordner öffnen')
        ftp.set_pasv(True);ftp.cwd(config['directory'] or '/')
        with sqlite3.connect(root/'state.sqlite') as db:
            rows=db.execute('SELECT id,channel,day FROM projects').fetchall()
        record_path=root/'transfer-records.json'
        records=json.loads(record_path.read_text()) if record_path.exists() else {}
        import hashlib
        target=hashlib.sha256(json.dumps([config[k] for k in ['protocol','host','port','username','directory']]).encode()).hexdigest()
        valid_ids={row[0] for row in rows}
        updated={k:v for k,v in records.items() if k in valid_ids};uploaded=0
        for pid,channel_id,day in rows:
            if plan is not None and pid not in plan['files']:continue
            if channel and channel_id!=channel:continue
            if plan is None and config['mode']!='both' and (config['mode']=='daily')!=bool(day):continue
            source=root/pid/'export.mp4'
            if not source.is_file():continue
            stat=source.stat();remote=plan['files'][pid] if plan is not None else channel_id+'-'+pid+'.mp4'
            signature=[stat.st_size,stat.st_mtime_ns,target,remote]
            if records.get(pid)==signature:updated[pid]=signature;continue
            upload_one(ftp,source,remote,progress)
            updated[pid]=signature;uploaded+=1
            save_json(record_path,{**records,**updated})
        save_json(record_path,updated)
        save_json(root/'transfer-result.json',{'state':'success','at':time.time(),'uploaded':uploaded,'origin':details['origin']})
    except Exception as error:
        save_json(root/'transfer-result.json',{'state':'error','at':time.time(),**details,'message':friendly_error(error,details.get('phase','Übertragung'))+' Lokale Dateien bleiben erhalten. Eine unvollständige .part-Datei wird beim nächsten Versuch ersetzt.'})
    finally:
        if ftp:
            try:ftp.close()
            except Exception:pass


def friendly_error(error,stage='Übertragung'):
    if isinstance(error,ssl.SSLCertVerificationError):
        return 'TLS-Zertifikat nicht vertrauenswürdig oder nicht für diesen Servernamen gültig. Einen zum Zertifikat passenden Hostnamen und ein vertrauenswürdiges Zertifikat verwenden.'
    if isinstance(error,ssl.SSLError):return 'TLS-Verbindung fehlgeschlagen. Der Server muss explizites FTPS (AUTH TLS) unterstützen.'
    if isinstance(error,socket.gaierror):return 'Servername konnte nicht aufgelöst werden.'
    if isinstance(error,ConnectionRefusedError):return 'Verbindung abgelehnt. Serveradresse, FTP-Port und Freigabe prüfen.'
    if isinstance(error,(TimeoutError,socket.timeout)):return stage+': Zeitüberschreitung beim Warten auf die FTP-Verbindung. Zielgerät, freien Speicher und Verbindungsstabilität prüfen.'
    code=re.match(r'^\d{3}',str(error))
    if code:
        n=code[0]
        if n=='530':return 'Anmeldung abgelehnt (FTP 530). Benutzername, Passwort und FTP-Zugriffsrecht prüfen.'
        if n in ('425','426'):return 'FTP-Datenverbindung fehlgeschlagen ('+n+'). Passive Datenverbindung/Firewall prüfen.'
        if n in ('550','553'):return stage+' abgelehnt (FTP '+n+'). Zielordner und Lese-/Schreibrechte prüfen.'
        if n=='552':return 'Zielspeicher voll oder Speicherlimit erreicht (FTP 552).'
        return stage+' fehlgeschlagen (FTP '+n+').'
    return stage+' fehlgeschlagen ('+type(error).__name__+').'

def test_connection(config):
    ftp=None;temporary=None;stage='Verbindung';entries=[]
    try:
        ftp=ftplib.FTP_TLS(context=ssl.create_default_context(),timeout=8) if config['protocol']=='ftps' else ftplib.FTP(timeout=8)
        ftp.connect(config['host'],config['port']);stage='Anmeldung'
        ftp.login(config['username'],config['password'])
        if config['protocol']=='ftps':ftp.prot_p()
        ftp.set_pasv(True);stage='Zielordner'
        ftp.cwd(config['directory'] or '/')
        stage='Verzeichnis lesen';entries=[]
        def entry(line):
            if len(entries)<20:entries.append(line[:200])
        ftp.retrlines('NLST',entry)
        stage='Testdatei schreiben';temporary='vortex-connection-test-'+uuid.uuid4().hex+'.tmp'
        ftp.storbinary('STOR '+temporary,io.BytesIO(b'Vortex FTP connection test\n'),blocksize=65536)
        stage='Testdatei löschen';ftp.delete(temporary);temporary=None
        return {'state':'success','message':'Verbindung, Anmeldung, Verzeichniszugriff, Schreiben und Löschen erfolgreich.','entries':entries}
    except Exception as error:
        return {'state':'error','message':friendly_error(error,stage),'entries':entries}
    finally:
        if ftp:
            if temporary:
                try:ftp.delete(temporary)
                except Exception:pass
            try:ftp.close()
            except Exception:pass

if __name__=='__main__':
    if len(sys.argv)>2 and sys.argv[2]=='--plan-file':execute(sys.argv[1],plan=json.loads(Path(sys.argv[3]).read_text()))
    else:execute(sys.argv[1],sys.argv[2] if len(sys.argv)>2 else None)
