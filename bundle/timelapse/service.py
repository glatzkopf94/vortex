#!/usr/bin/env python3
# Modified 2026-10-11: validated FTP connection tests and actionable errors.
"""Independent, resumable timelapse service. Private state outside public diskfs.
Only loopback HTTP; Core authenticates /admin, /public is publication-filtered.
Overlay-free captures may briefly read the configured original camera source.
"""
from __future__ import annotations
import concurrent.futures
import hashlib
import functools
import json
import math
import os
from pathlib import Path
import re
import shutil
import sqlite3
import subprocess
import threading
import time
import uuid
import urllib.request
from urllib.parse import urljoin, urlsplit
from email.utils import parsedate_to_datetime
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from solar import window
import transfer

UUID = re.compile(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}')
DEFAULT = dict(mode='daily', interval=120, fps=25, width=0, formatVersion=2, timezone='Europe/Berlin', window='full', latitude=51.0, longitude=10.0,
               startEvent='sunrise', endEvent='sunset', startOffset=-60, endOffset=60, public=False, enabled=True, nas=False, keepFrames=False)


def settings(raw):
    if not isinstance(raw,dict): raise ValueError('Einstellungen muessen ein Objekt sein')
    s = {**DEFAULT, **{k: v for k, v in raw.items() if k in DEFAULT}}
    for key, low, high in [('interval',15 if s['mode']=='daily' else 30,86400),('fps',1,60),('width',0,8192),('startOffset',-360,360),('endOffset',-360,360)]:
        if isinstance(s[key], bool) or not isinstance(s[key], (float,int)) or not math.isfinite(s[key]) or int(s[key]) != s[key] or not low <= s[key] <= high:
            raise ValueError(f'Ungueltiger Wert: {key} ({low} bis {high})')
        s[key] = int(s[key])
    if s['width'] and (s['width'] < 320 or s['width'] % 16): raise ValueError('Bildbreite muss durch 16 teilbar sein.')
    for k in ('enabled','public','nas','keepFrames'):
        if not isinstance(s[k], bool): raise ValueError('Boolescher Wert erwartet: '+k)
    for k, allowed in [('mode',('daily','season')),('window',('full','solar')),('startEvent',('sunrise','sunset')),('endEvent',('sunrise','sunset'))]:
        if s[k] not in allowed: raise ValueError('Ungueltige Auswahl: '+k)
    for k, limit in [('latitude',89.8),('longitude',180)]:
        if not isinstance(s[k], (int,float)) or not math.isfinite(s[k]) or abs(s[k]) > limit: raise ValueError('Ungueltiger Standort')
    ZoneInfo(s['timezone'])
    return s


def atomic(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    import uuid
    tmp = path.with_name('.'+path.name+'.'+uuid.uuid4().hex+'.tmp')
    with tmp.open('wb') as f:
        f.write(data); f.flush(); os.fsync(f.fileno())
    os.replace(tmp, path)


def run(args, timeout=60):
    try:
        return subprocess.run(args, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout, check=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(e.stderr.decode('utf-8','replace')[-1000:]) from e


@functools.lru_cache(maxsize=1)
def ffmpeg_progress_options():
    # The bundled JSON-stats patch bypasses FFmpeg's standard -progress writer.
    # Stock FFmpeg does not know this switch, so detect support once per process.
    result=subprocess.run(['ffmpeg','-hide_banner','-h','full'],stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=15,check=True)
    return ['-nojsonstats'] if re.search(rb'(?m)^-jsonstats\s',result.stdout) else []


class Service:
    def __init__(self, root, core_db=None, data=None, min_free=None, quota=None, recover=True):
        self.root = Path(root); self.root.mkdir(parents=True, exist_ok=True)
        self.core_db = Path(core_db or os.environ.get('CORE_DB_DIR','/core/config'))
        if self.core_db.is_dir(): self.core_db /= 'db.json'
        self.data = Path(data or os.environ.get('CORE_STORAGE_DISK_DIR','/core/data'))
        self.min_free = min_free if min_free is not None else int(os.environ.get('NKL_TIMELAPSE_RESERVE_BYTES', 2*1024**3))
        self.quota = quota if quota is not None else int(os.environ.get('NKL_TIMELAPSE_QUOTA_BYTES', 20*1024**3))
        self.lock = threading.RLock()
        self.db = sqlite3.connect(self.root/'state.sqlite', check_same_thread=False)
        self.db.row_factory = sqlite3.Row
        self.db.executescript('''PRAGMA journal_mode=WAL; PRAGMA synchronous=FULL;
        CREATE TABLE IF NOT EXISTS media_info(project TEXT PRIMARY KEY, width INTEGER, height INTEGER);
        CREATE TABLE IF NOT EXISTS quality_segments(project TEXT, quality INTEGER, number INTEGER, bitrate INTEGER, PRIMARY KEY(project,quality,number));
        CREATE TABLE IF NOT EXISTS global_settings(key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS deleted_days(channel TEXT, day TEXT, PRIMARY KEY(channel,day));
        CREATE TABLE IF NOT EXISTS channels(id TEXT PRIMARY KEY, settings TEXT NOT NULL, error TEXT DEFAULT '');
        CREATE TABLE IF NOT EXISTS projects(id TEXT PRIMARY KEY, channel TEXT, label TEXT, day TEXT, settings TEXT, status TEXT, started REAL, ends REAL, next REAL, last REAL DEFAULT 0, missed INTEGER DEFAULT 0, error TEXT DEFAULT '', export INTEGER DEFAULT 0, exported INTEGER DEFAULT 0, nas TEXT DEFAULT '', UNIQUE(channel,day));
        CREATE TABLE IF NOT EXISTS attempts(project TEXT, slot INTEGER, status TEXT, PRIMARY KEY(project,slot));
        CREATE TABLE IF NOT EXISTS frames(project TEXT, slot INTEGER, path TEXT, bytes INTEGER, PRIMARY KEY(project,slot));
        CREATE TABLE IF NOT EXISTS timeline(project TEXT, segment INTEGER, slots TEXT, PRIMARY KEY(project,segment));
        CREATE TABLE IF NOT EXISTS segments(project TEXT, number INTEGER, path TEXT, frames INTEGER, bytes INTEGER, created REAL, PRIMARY KEY(project,number));
        ''')
        # Keep previously configured channels active; unknown channels remain off.
        if 'active' not in {row['name'] for row in self.db.execute('PRAGMA table_info(channels)')}:
            self.db.execute('ALTER TABLE channels ADD COLUMN active INTEGER NOT NULL DEFAULT 1')
        if 'armed' not in {row['name'] for row in self.db.execute('PRAGMA table_info(channels)')}:
            self.db.execute('ALTER TABLE channels ADD COLUMN armed INTEGER NOT NULL DEFAULT 1')
        saved_quota=self.db.execute("SELECT value FROM global_settings WHERE key='quotaBytes'").fetchone()
        if saved_quota:
            value=json.loads(saved_quota['value'])
            if type(value) is int and 1024**3<=value<=10000*1024**3:self.quota=value
        self.db.commit()
        self.capture_pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        self.render_pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        self.capture_job = None; self.render_job = None
        self.archive_pool = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        self.archive_job = None; self.next_archive = 0
        self.transfer_pool=concurrent.futures.ThreadPoolExecutor(max_workers=1)
        self.transfer_test_pool=concurrent.futures.ThreadPoolExecutor(max_workers=1)
        self.transfer_test_job=None
        self.transfer_plan=None; self.transfer_cancel=threading.Event(); self.transfer_channel=None; self.transfer_job=None; self.transfer_pending=False; self.next_transfer=time.time()+transfer.read_config(self.root)['intervalMinutes']*60; self.transfer_started=0
        try:
            previous=json.loads((self.root/'transfer-result.json').read_text())
            if previous.get('state')=='running':
                transfer.save_json(self.root/'transfer-result.json',{**previous,'state':'error','at':time.time(),'message':'Vorherige Übertragung durch Dienstneustart unterbrochen. Erneuter manueller Upload möglich.'})
        except (OSError,ValueError):pass
        self.last_usage = (0,0)
        self.next_retention = 0
        self.render_retry = {}
        self.processing = {}
        if recover: self.recover_attempts()

    def recover_attempts(self):
        # A process kill between the atomic JPEG rename and DB commit is safe.
        for attempt in self.rows("SELECT * FROM attempts WHERE status='pending'"):
            path=self.root/attempt['project']/f"{attempt['slot']}.jpg"
            if path.is_file() and path.stat().st_size>100:
                with path.open('rb') as f:
                    magic=f.read(2); f.seek(-2,2); complete=magic==b'\xff\xd8' and f.read()==b'\xff\xd9'
                if complete:
                    with self.lock,self.db:
                        self.db.execute('INSERT OR IGNORE INTO frames VALUES(?,?,?,?)',(attempt['project'],attempt['slot'],str(path),path.stat().st_size))
                        self.db.execute("UPDATE attempts SET status='done' WHERE project=? AND slot=?",(attempt['project'],attempt['slot']))
                    continue
            with self.lock,self.db:
                self.db.execute('UPDATE projects SET missed=missed+1 WHERE id=?',(attempt['project'],))
                self.db.execute("UPDATE attempts SET status='failed' WHERE project=? AND slot=?",(attempt['project'],attempt['slot']))

        # Clean leftovers only after committed segments are recorded. Pending
        # frames and intentionally retained originals are never removed here.
        for p in self.rows('SELECT * FROM projects'):
            folder=self.root/p['id']
            for temporary in folder.glob('.*.capture.jpg'): temporary.unlink(missing_ok=True)
            if not json.loads(p['settings'])['keepFrames']:
                pending={row['slot'] for row in self.rows('SELECT slot FROM frames WHERE project=?',(p['id'],))}
                completed={row['slot'] for row in self.rows("SELECT slot FROM attempts WHERE project=? AND status='done'",(p['id'],))}
                for path in folder.glob('*.jpg'):
                    if path.stem.isdigit() and int(path.stem) in completed-pending: path.unlink(missing_ok=True)

    def rows(self, sql, args=()):
        with self.lock: return [dict(r) for r in self.db.execute(sql,args)]

    def write(self, sql, args=()):
        with self.lock, self.db: self.db.execute(sql,args)

    def known_channels(self):
        try:
            db=json.loads(self.core_db.read_text())
            result=[]
            for pid, wrapped in (db.get('metadata',{}).get('process',{}) or {}).items():
                channel=pid.removeprefix('restreamer-ui:ingest:')
                if pid.startswith('restreamer-ui:ingest:') and UUID.fullmatch(channel):
                    metadata=(wrapped or {}).get('restreamer-ui') or {}
                    result.append({'id':channel,'name':(metadata.get('meta') or {}).get('name',channel)})
            return result
        except (OSError,ValueError): return []

    def channel_active(self, channel):
        rows=self.rows('SELECT active FROM channels WHERE id=?',(channel,))
        return bool(rows and rows[0]['active'])

    def set_channel_active(self, channel, active):
        if channel not in {c['id'] for c in self.known_channels()}: raise ValueError('Unbekannter Kanal')
        if not isinstance(active,bool): raise ValueError('Boolescher Wert erwartet')
        self.write('INSERT INTO channels(id,settings,active,armed) VALUES(?,?,?,0) ON CONFLICT(id) DO UPDATE SET active=excluded.active',
                   (channel,json.dumps(DEFAULT),int(active)))
        # Re-enabling resumes at the current time, without counting the disabled
        # period as failed camera captures. Existing paused projects stay paused.
        if active:
            self.write("UPDATE projects SET next=? WHERE channel=? AND status='recording'",(time.time(),channel))
        return {'active':active}

    def configure(self, channel, raw):
        if channel not in {c['id'] for c in self.known_channels()}: raise ValueError('Unbekannter Kanal')
        s=settings(raw)
        self.write('INSERT INTO channels(id,settings,armed) VALUES(?,?,0) ON CONFLICT(id) DO UPDATE SET settings=excluded.settings,error=\'\'',(channel,json.dumps(s)))
        # Existing recordings retain interval/resolution; publicity can be revoked immediately.
        with self.lock, self.db:
            for p in self.rows('SELECT * FROM projects WHERE channel=?',(channel,)):
                old=json.loads(p['settings']); old['public']=s['public']; old['nas']=s['nas']
                if p['status'] in ('recording','paused'):
                    old['interval']=s['interval']
                    self.db.execute('UPDATE projects SET next=MIN(next,?) WHERE id=?',(time.time()+s['interval'],p['id']))
                self.db.execute('UPDATE projects SET settings=? WHERE id=?',(json.dumps(old),p['id']))
        return s

    def create_project(self, channel, s, now, day=None, start=None, end=None):
        if day and self.rows('SELECT day FROM deleted_days WHERE channel=? AND day=?',(channel,day)): return None
        pid=str(uuid.uuid4()); label=day or datetime.fromtimestamp(now,ZoneInfo(s['timezone'])).strftime('Saison %d.%m.%Y')
        if s['mode']=='season' and self.rows("SELECT id FROM projects WHERE channel=? AND status IN ('recording','paused') AND day IS NULL",(channel,)):
            raise ValueError('Es gibt bereits ein laufendes Saisonprojekt.')
        self.write('INSERT OR IGNORE INTO projects(id,channel,label,day,settings,status,started,ends,next) VALUES(?,?,?,?,?,?,?,?,?)',
                   (pid,channel,label,day,json.dumps(s),'recording',start if start is not None else now,end,now))
        return pid

    def action(self, request, now=None):
        with self.lock:
            return self._action_locked(request,now)

    def _action_locked(self, request, now=None):
        now=time.time() if now is None else now
        if not isinstance(request, dict): raise ValueError('Ungueltiger Auftrag')
        action=request.get('action'); channel=request.get('channel')
        if action=='set_channel_active': return self.set_channel_active(channel,request.get('active'))
        if action=='configure_qualities':
            value=request.get('settings',{})
            if type(value.get('enabled')) is not bool: raise ValueError('Transcoding muss ein- oder ausgeschaltet sein.')
            for key in ('bitrate1080','bitrate720'):
                if type(value.get(key)) is not int or not 256<=value[key]<=20000:
                    raise ValueError('Bitrate muss zwischen 256 und 20000 kbit/s liegen.')
            self.write('INSERT OR REPLACE INTO global_settings VALUES(?,?)',('qualities',json.dumps(value)))
            return self.global_settings()
        if action=='configure_storage':
            value=request.get('quotaGiB')
            if type(value) is not int or not 1<=value<=10000:
                raise ValueError('Zeitrafferlimit muss eine ganze Zahl von 1 bis 10000 GiB sein.')
            self.write('INSERT OR REPLACE INTO global_settings VALUES(?,?)',('quotaBytes',json.dumps(value*1024**3)))
            self.quota=value*1024**3
            self.last_usage=(0,0)
            self.render_retry.clear()
            return {'quotaBytes':self.quota}
        if action=='configure_retention':
            days=request.get('days')
            if type(days) is not int or days not in (0,1,3,7): raise ValueError('Aufbewahrung muss nie, 1, 3 oder 7 Tage sein.')
            self.write('INSERT OR REPLACE INTO global_settings VALUES(?,?)',('retentionDays',json.dumps(days)))
            self.next_retention=0
            return self.global_settings()
        if action=='configure_global':
            value=request.get('includeBurnedOverlays')
            if not isinstance(value,bool): raise ValueError('Boolescher Wert erwartet')
            self.write('INSERT OR REPLACE INTO global_settings VALUES(?,?)',('includeBurnedOverlays',json.dumps(value)))
            return self.global_settings()
        if action=='test_transfer':
            if self.transfer_test_job and not self.transfer_test_job.done(): raise ValueError('Verbindungstest läuft bereits.')
            config=transfer.validate(self.root,request.get('settings'))
            if not config['host'] or not config['username']: raise ValueError('Server und Benutzername für den Test eingeben.')
            self.transfer_test_job=self.transfer_test_pool.submit(transfer.test_connection,config)
            return {'ok':True}
        if action=='configure_transfer':
            if self.transfer_pending or (self.transfer_job and not self.transfer_job.done()): raise ValueError('Übertragung läuft; zuerst abbrechen oder Abschluss abwarten.')
            result=transfer.configure(self.root,request.get('settings'));self.next_transfer=now+result['intervalMinutes']*60
            return result
        if action=='cancel_transfer':
            origin=request.get('origin')
            if origin not in ('manual','automatic'):raise ValueError('Ungültiger Uploadbereich')
            if (self.transfer_pending or (self.transfer_job and not self.transfer_job.done())) and self.transfer_plan and self.transfer_plan['origin']!=origin:raise ValueError('Im anderen Bereich läuft eine Übertragung.')
            self.transfer_cancel.set();self.transfer_pending=False
            self.next_transfer=now+transfer.read_config(self.root)['intervalMinutes']*60
            active=self.transfer_job and not self.transfer_job.done()
            transfer.save_json(self.root/'transfer-result.json',{'state':'cancelling' if active else 'idle','origin':origin})
            return {'ok':True}
        if action=='transfer_now':
            config=transfer.read_config(self.root)
            if not config['host'] or not config['username']:raise ValueError('FTP-Zugang zuerst speichern.')
            if self.transfer_pending or (self.transfer_job and not self.transfer_job.done()): raise ValueError('Übertragung bereits beauftragt.')
            if channel and channel not in {c['id'] for c in self.known_channels()}: raise ValueError('Unbekannter Kanal')
            selected=request.get('projects')
            if selected is not None and (not isinstance(selected,list) or not selected or any(not isinstance(v,str) for v in selected)):raise ValueError('Mindestens eine Datei auswählen.')
            finished=request.get('onlyFinished',False)
            if not isinstance(finished,bool):raise ValueError('Ungültiger Aufnahmefilter')
            projects=self.rows('SELECT * FROM projects')
            candidates=[p for p in projects if (not channel or p['channel']==channel) and (not finished or p['status']=='finished')]
            if selected is not None:
                if set(selected)-{p['id'] for p in candidates}:raise ValueError('Dateiauswahl passt nicht zum Kanal oder Aufnahmefilter. Bitte neu auswählen.')
                candidates=[p for p in candidates if p['id'] in selected]
            if not candidates:raise ValueError('Keine passenden Aufnahmen vorhanden.')
            self.prepare_transfer(candidates,'manual',now)
            return {'ok':True}
        if action=='configure': return self.configure(channel,request['settings'])
        if action=='start':
            if not self.channel_active(channel): raise ValueError('Zeitraffer fuer diesen Kanal ist deaktiviert.')
            rows=self.rows('SELECT settings FROM channels WHERE id=?',(channel,))
            if not rows: raise ValueError('Zuerst Kanaleinstellungen speichern.')
            s=json.loads(rows[0]['settings'])
            if not s['enabled']: raise ValueError('Zuerst Aufnahmeplan aktivieren und Einstellungen speichern.')
            if s['mode']=='season':
                pid=self.create_project(channel,s,now)
                self.write('UPDATE channels SET armed=1 WHERE id=?',(channel,))
                return {'id':pid}
            self.write('UPDATE channels SET armed=1 WHERE id=?',(channel,))
            self.schedule(now)
            return {'armed':True}

        if action=='delete_finished':
            mode=request.get('mode')
            if mode not in ('daily','season'): raise ValueError('Betriebsart fuer Sammelloeschung erforderlich.')
            targets=self.rows("SELECT id FROM projects WHERE status='finished' AND "+('day IS NOT NULL' if mode=='daily' else 'day IS NULL'))
            if any(job and not job.done() for job in (self.capture_job,self.render_job,self.archive_job,self.transfer_job)):
                raise ValueError('Verarbeitung laeuft; bitte kurz danach erneut versuchen.')
            deleted=0
            for target in targets:
                try:
                    self._action_locked({'action':'delete','project':target['id']},now)
                    deleted+=1
                except (OSError,ValueError) as error:
                    raise ValueError(f'{deleted} Projekte geloescht; danach Fehler: {error}') from error
            return {'ok':True,'deleted':deleted,'mode':mode}
        pid=request.get('project')
        projects=self.rows('SELECT * FROM projects WHERE id=?',(pid,))
        if not projects: raise ValueError('Unbekanntes Projekt')
        p=projects[0]
        if action=='pause' and p['status']=='recording': self.write("UPDATE projects SET status='paused' WHERE id=?",(pid,))
        elif action=='resume' and p['status']=='paused': self.write("UPDATE projects SET status='recording',next=? WHERE id=?",(now,pid))
        elif action=='stop' and p['status'] in ('recording','paused'): self.write("UPDATE projects SET status='finished',ends=?,export=1 WHERE id=?",(now,pid))
        elif action=='export': self.write('UPDATE projects SET export=1 WHERE id=?',(pid,))
        elif action=='delete':
            if p['status']!='finished': raise ValueError('Projekt zuerst beenden.')
            if (self.transfer_job and not self.transfer_job.done()) or (self.capture_job and not self.capture_job.done()) or (self.render_job and not self.render_job.done()) or (self.archive_job and not self.archive_job.done()):
                raise ValueError('Verarbeitung laeuft; bitte kurz danach erneut versuchen.')
            if not UUID.fullmatch(pid): raise ValueError('Ungueltige Projekt-ID')
            shutil.rmtree(self.root/pid,ignore_errors=False) if (self.root/pid).exists() else None
            with self.lock,self.db:
                if p['day']: self.db.execute('INSERT OR IGNORE INTO deleted_days VALUES(?,?)',(p['channel'],p['day']))
                for table in ('frames','segments','attempts','timeline','quality_segments','media_info'): self.db.execute('DELETE FROM '+table+' WHERE project=?',(pid,))
                self.db.execute('DELETE FROM projects WHERE id=?',(pid,))
            self.render_retry.pop(pid,None)
            self.processing.pop(pid,None)
            self.last_usage=(0,0)
        elif action=='publish':
            s=json.loads(p['settings']); s['public']=request.get('public') is True
            self.write('UPDATE projects SET settings=? WHERE id=?',(json.dumps(s),pid))
        else: raise ValueError('Aktion fuer diesen Projektzustand nicht moeglich.')
        return {'ok':True}

    def schedule(self, now):
        for channel in self.rows('SELECT * FROM channels'):
            s=json.loads(channel['settings'])
            if not channel['active'] or not channel['armed'] or not s['enabled'] or s['mode']!='daily': continue
            today=datetime.fromtimestamp(now,ZoneInfo(s['timezone'])).date()
            self.write('DELETE FROM deleted_days WHERE channel=? AND day<?',(channel['id'],(today-timedelta(days=2)).isoformat()))
            try:
                # Adjacent dates cover offsets spanning midnight.
                for shift in (-1,0,1):
                    day=today+timedelta(days=shift); start,end=window(day,s)
                    if start <= now < end:
                        self.create_project(channel['id'],s,now,day.isoformat(),start,end)
                self.write("UPDATE channels SET error='' WHERE id=?",(channel['id'],))
            except ValueError as e: self.write('UPDATE channels SET error=? WHERE id=?',(str(e),channel['id']))
        self.write("UPDATE projects SET status='finished',export=1 WHERE ends IS NOT NULL AND ends<=? AND status IN ('recording','paused')",(now,))

    def enough_space(self, extra=0):
        now=time.time()
        if now-self.last_usage[0]>15:
            usage=sum(p.stat().st_size for p in self.root.rglob('*') if p.is_file())
            self.last_usage=(now,usage)
        return self.last_usage[1]+extra < self.quota and shutil.disk_usage(self.root).free > self.min_free+extra

    def require_space(self, extra=0):
        if self.enough_space(extra):return
        if self.last_usage[1]+extra>=self.quota:
            raise ValueError(f'Zeitrafferlimit erreicht ({self.last_usage[1]/1024**3:.2f} / {self.quota/1024**3:.1f} GiB). Limit erhöhen oder alte Aufnahmen löschen.')
        raise ValueError(f'Freie Festplattenreserve unterschritten ({self.min_free/1024**3:.1f} GiB). Speicherplatz freigeben.')

    def global_settings(self):
        rows=self.rows('SELECT value FROM global_settings WHERE key=?',('includeBurnedOverlays',))
        retention=self.rows('SELECT value FROM global_settings WHERE key=?',('retentionDays',))
        days=json.loads(retention[0]['value']) if retention else 0
        return {'includeBurnedOverlays':bool(rows and json.loads(rows[0]['value']) is True),
                'retentionDays':days if type(days) is int and days in (0,1,3,7) else 0,'qualities':self.quality_settings()}

    def quality_settings(self):
        rows=self.rows("SELECT value FROM global_settings WHERE key='qualities'")
        return json.loads(rows[0]['value']) if rows else {'enabled':True,'bitrate1080':3072,'bitrate720':2048}

    def qualities(self,pid):
        info=self.rows('SELECT width,height FROM media_info WHERE project=?',(pid,))
        count=self.rows('SELECT COUNT(*) AS n FROM segments WHERE project=?',(pid,))[0]['n']
        label=f"{info[0]['width']}×{info[0]['height']}" if info else 'Quellauflösung (wird ermittelt)'
        result=[{'id':'original','label':label,'ready':bool(count),'url':'index.m3u8'}]
        cfg=self.quality_settings()
        if cfg['enabled']:
            for q,w in ((1080,1920),(720,1280)):
                ready=self.rows('SELECT COUNT(*) AS n FROM quality_segments WHERE project=? AND quality=?',(pid,q))[0]['n']
                highest=self.rows('SELECT MAX(bitrate) AS b FROM quality_segments WHERE project=? AND quality=?',(pid,q))[0]['b'] or 0
                result.append({'id':str(q),'label':f'{w}×{q}','ready':bool(count and ready==count),'bitrate':max(highest,cfg[f'bitrate{q}']),'url':f'quality-{q}.m3u8'})
        return result

    def render_quality(self,p):
        pid=p['id'];folder=self.root/pid
        try:
            segments=self.rows('SELECT * FROM segments WHERE project=? ORDER BY number',(pid,))
            if not segments:return
            if not self.rows('SELECT project FROM media_info WHERE project=?',(pid,)):
                # The runtime ships FFmpeg without ffprobe. Decode one frame and
                # read showinfo's dimensions, including with the JSON-stats build.
                probe=run(['ffmpeg',*ffmpeg_progress_options(),'-nostdin','-hide_banner','-v','info','-i',segments[0]['path'],'-map','0:v:0','-an','-vf','showinfo','-frames:v','1','-f','null','-'],30)
                size=re.search(rb'\b s:(\d+)x(\d+)\b',probe.stderr)
                if not size:raise ValueError('Quellauflösung konnte mit FFmpeg nicht ermittelt werden.')
                self.write('INSERT OR REPLACE INTO media_info VALUES(?,?,?)',(pid,int(size[1]),int(size[2])))
            # Read settings for each new transcode, not from the project's snapshot.
            # Existing encoded segments retain their original bitrate.
            cfg=self.quality_settings()
            if not cfg['enabled']:return
            self.require_space(64*1024**2)
            for segment in segments:
                for q,w in ((1080,1920),(720,1280)):
                    if self.rows('SELECT number FROM quality_segments WHERE project=? AND quality=? AND number=?',(pid,q,segment['number'])):continue
                    cfg=self.quality_settings()
                    if not cfg['enabled']:return
                    bitrate=cfg[f'bitrate{q}'];s=json.loads(p['settings'])
                    expected=int(segment['frames']/s['fps']*bitrate*125*1.5)+16*1024**2
                    self.require_space(expected)
                    name=f"quality-{q}-segment-{segment['number']:06d}.ts"
                    target=folder/name;tmp=folder/('.'+name)
                    filters=f'scale={w}:{q}:force_original_aspect_ratio=decrease:force_divisible_by=2,pad={w}:{q}:(ow-iw)/2:(oh-ih)/2,setsar=1'
                    try:
                        run(['ffmpeg','-nostdin','-v','error','-r',str(s['fps']),'-i',segment['path'],'-an','-vf',filters,'-r',str(s['fps']),'-fps_mode','cfr','-frames:v',str(segment['frames']),'-c:v','libx264','-preset','veryfast','-pix_fmt','yuv420p','-threads','1','-b:v',f'{bitrate}k','-maxrate',f'{bitrate}k','-bufsize',f'{bitrate*2}k','-g',str(s['fps']*2),'-f','mpegts','-y',str(tmp)],600)
                        with tmp.open('ab') as output:
                            while output.tell()<188*64:output.write(b'\x47\x1f\xff\x10'+b'\xff'*184)
                        os.replace(tmp,target)
                        self.write('INSERT OR REPLACE INTO quality_segments VALUES(?,?,?,?)',(pid,q,segment['number'],bitrate))
                        self.write("UPDATE projects SET error='' WHERE id=? AND error NOT LIKE 'Aufnahmeluecke:%'",(pid,))
                        self.last_usage=(0,0)
                    finally:tmp.unlink(missing_ok=True)
                    return # One segment per job; original rendering always has priority.
        except Exception as error:
            self.render_retry[pid]=time.time()+60
            self.write("UPDATE projects SET error=? WHERE id=? AND error NOT LIKE 'Aufnahmeluecke:%'",('Vorschauqualität: '+str(error)[:200],pid))

    def cleanup_retention(self, now):
        # Called under the scheduler lock, before launching workers. Never delete
        # files that capture, rendering, NAS or FTP is currently using.
        if now<self.next_retention: return 0
        if self.transfer_pending or any(job and not job.done() for job in
                (self.capture_job,self.render_job,self.archive_job,self.transfer_job)):
            return 0
        self.next_retention=now+60
        days=self.global_settings()['retentionDays']
        self.last_usage=(0,0)
        candidates=self.rows("SELECT * FROM projects WHERE status='finished' AND export=0 ORDER BY COALESCE(ends,started),started,id")
        deleted=0
        for project in candidates:
            if days:
                if (project['ends'] if project['ends'] is not None else project['started'])>now-days*86400: break
            elif self.enough_space(32*1024**2):
                break
            try:
                self._action_locked({'action':'delete','project':project['id']},now)
                deleted+=1
            except (OSError,ValueError):
                # A failed deletion is not a reason to erase newer recordings.
                break
        self.enough_space()
        return deleted

    def capture_input(self, channel):
        # Validate freshness even when the original source is used; a stopped
        # channel must not silently become a separately running camera.
        local=self.fresh_source(channel)
        hls=['-live_start_index','-1','-i',local]
        if self.global_settings()['includeBurnedOverlays']: return hls,''
        database=json.loads(self.core_db.read_text())
        key='restreamer-ui:ingest:'+channel
        processes=database.get('process',{})
        process=(next((p for p in processes if p.get('id')==key),{})
                 if isinstance(processes,list) else processes.get(key,{}))
        config=process.get('config',process)
        outputs=config.get('output',[])
        options=outputs[0].get('options',[]) if outputs else []
        filters=[options[i+1] for i,v in enumerate(options[:-1]) if v in ('-vf','-filter:v','-filter_complex')]
        if not any(re.search(r'(?:^|[,;\]])(?:drawtext|overlay)=',f) for f in filters): return hls,''
        # Vortex emits either a simple chain ending in drawtext, or its named
        # logo graph. Only these known forms can be bypassed safely.
        if len(filters)!=1 or '-filter_complex' in options:
            raise ValueError('Overlayfreie Aufnahme: dieser Filtergraph wird noch nicht unterstützt.')
        graph=filters[0]
        if '[lc_base0]' in graph:
            match=re.match(r'^\[in\](.*?)\[lc_base0\];',graph)
            if not match: raise ValueError('Overlayfreie Aufnahme: unbekannter Logo-Filtergraph.')
            ordinary=match[1]
        else:
            ordinary=re.split(r'(?:^|,)drawtext=',graph,maxsplit=1)[0]
        if re.search(r'(?:drawtext|overlay|movie|hwupload|hwdownload)\s*=',ordinary) or '[' in ordinary or ';' in ordinary:
            raise ValueError('Overlayfreie Aufnahme: vorgeschaltete Filter werden nicht unterstützt.')
        mapping=options[options.index('-map')+1] if '-map' in options else '0:v:0'
        match=re.fullmatch(r'(\d+):(v(?::\d+)?|\d+)',mapping)
        if not match: raise ValueError('Overlayfreie Aufnahme: Videoquelle nicht eindeutig.')
        inputs=config.get('input',[]); index=int(match[1])
        if index>=len(inputs): raise ValueError('Overlayfreie Aufnahme: Videoquelle fehlt.')
        source=inputs[index]; address=source.get('address','')
        if urlsplit(address).scheme not in ('rtsp','rtsps','http','https') or '{' in address:
            raise ValueError('Overlayfreie Aufnahme benötigt eine direkt abrufbare RTSP- oder HTTP-Videoquelle.')
        args=[]; raw=source.get('options',[])
        for i,option in enumerate(raw[:-1]):
            if option in ('-rtsp_transport','-rtsp_flags','-headers','-user_agent','-referer'):
                args.extend([option,str(raw[i+1])])
        if urlsplit(address).scheme in ('rtsp','rtsps') and '-rtsp_transport' not in args:
            args.extend(['-rtsp_transport','tcp'])
        return args+['-i',address,'-map','0:'+match[2]],ordinary

    def source(self, channel):
        # Generated config is data only, never evaluated as JavaScript.
        text=(self.data/'channels'/channel/'config.js').read_text()
        match=re.fullmatch(r'\s*var playerConfig\s*=\s*(\{.*\})\s*;?\s*',text,re.S)
        if not match: raise ValueError('Playerquelle nicht verfuegbar')
        source=json.loads(match[1]).get('source','')
        if not re.fullmatch(r'(?:memfs/)?'+re.escape(channel)+r'(?:_h264)?\.m3u8',source): raise ValueError('Ungueltige lokale Quelle')
        return 'http://127.0.0.1:8080/'+source

    def fresh_source(self,channel,now=None):
        now=time.time() if now is None else now
        url=self.source(channel)
        initial=url
        for _ in range(3):
            with urllib.request.urlopen(url,timeout=8) as response:
                body=response.read(2*1024*1024+1)
                if len(body)>2*1024*1024: raise ValueError('Playlist zu gross')
                text=body.decode('utf-8'); modified=response.headers.get('Last-Modified')
            if '#EXT-X-STREAM-INF:' in text:
                variant=next((line.strip() for line in text.splitlines() if line.strip() and not line.startswith('#')),None)
                url=urljoin(url,variant or '')
                parsed=urlsplit(url)
                if parsed.hostname!='127.0.0.1' or parsed.port!=8080: raise ValueError('Nur lokale Playlists erlaubt')
                continue
            timestamps=re.findall(r'^#EXT-X-PROGRAM-DATE-TIME:(.+)$',text,re.M)
            newest=datetime.fromisoformat(timestamps[-1].strip().replace('Z','+00:00')).timestamp() if timestamps else parsedate_to_datetime(modified).timestamp() if modified else 0
            if not newest or now-newest>120 or newest-now>120: raise ValueError('Stream ist nicht aktuell; kein altes Standbild gespeichert')
            return initial
        raise ValueError('Keine aktuelle Medienplaylist')

    def source_format(self, channel):
        with urllib.request.urlopen(self.source(channel), timeout=8) as response:
            text=response.read(65536).decode('utf-8')
        line=next((line for line in text.splitlines() if line.startswith('#EXT-X-STREAM-INF:')), '')
        rate=re.search(r'(?:[:,])BANDWIDTH=(\d+)',line)
        size=re.search(r'(?:[:,])RESOLUTION=(\d+)x(\d+)',line)
        if not rate or not size: raise ValueError('Quellaufloesung / Bandbreite fehlt in der HLS-Masterplaylist')
        width,height=map(int,size.groups()); bitrate=int(rate[1])
        if not (1<=width<=16384 and 1<=height<=16384 and 1<=bitrate<=1000000000): raise ValueError('Ungueltiges Quellformat')
        return width,height,bitrate

    def capture(self,p,slot):
        folder=self.root/p['id']; folder.mkdir(exist_ok=True)
        path=folder/f'{slot}.jpg'; temp=folder/f'.{slot}.capture.jpg'
        try:
            self.require_space(16*1024**2)
            s=json.loads(p['settings'])
            if 'sourceBitrate' not in s:
                sw,sh,rate=self.source_format(p['channel'])
                s.update(sourceWidth=sw,sourceHeight=sh,sourceBitrate=rate)
                with self.lock,self.db:
                    current=json.loads(self.rows('SELECT settings FROM projects WHERE id=?',(p['id'],))[0]['settings'])
                    current.update(sourceWidth=sw,sourceHeight=sh,sourceBitrate=rate)
                    self.db.execute('UPDATE projects SET settings=? WHERE id=?',(json.dumps(current),p['id']))
            width=s['width'] or s['sourceWidth']
            height=round(width*s['sourceHeight']/s['sourceWidth']) if s.get('formatVersion',1)>=2 else width*9//16
            width+=width%2; height+=height%2
            capture_args,ordinary=self.capture_input(p['channel'])
            try:
                run(['ffmpeg','-nostdin','-hide_banner','-loglevel','error','-threads','1','-rw_timeout','8000000',*capture_args,
                 '-frames:v','1','-an','-vf',(ordinary+',' if ordinary else '')+f'scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2',
                 '-threads','1','-q:v','3','-y',str(temp)],30)
            except (RuntimeError,subprocess.TimeoutExpired):
                # FFmpeg diagnostics may contain camera URLs/passwords.
                raise ValueError('Einzelbild konnte nicht abgerufen werden. Quelle/Erreichbarkeit und Filter prüfen.') from None
            if temp.stat().st_size<100: raise ValueError('Kein vollstaendiges Bild empfangen')
            os.replace(temp,path)
            atomic(folder/'poster.jpg',path.read_bytes())
            with self.lock,self.db:
                self.db.execute('INSERT OR IGNORE INTO frames VALUES(?,?,?,?)',(p['id'],slot,str(path),path.stat().st_size))
                self.db.execute("UPDATE projects SET last=?,error='' WHERE id=?",(time.time(),p['id']))
                self.db.execute("UPDATE attempts SET status='done' WHERE project=? AND slot=?",(p['id'],slot))
        except Exception as e:
            self.write('UPDATE projects SET missed=missed+1,error=? WHERE id=?',(f'Aufnahmeluecke: {type(e).__name__}: {str(e)[:200]}',p['id']))
            self.write("UPDATE attempts SET status='failed' WHERE project=? AND slot=?",(p['id'],slot))
        finally: temp.unlink(missing_ok=True)

    def progress_args(self, pid, phase, duration):
        path=self.root/pid/'ffmpeg-progress.txt'
        path.write_text('')
        self.processing[pid]=(phase,max(duration,0.001),path)
        return [*ffmpeg_progress_options(),'-stats_period','0.25','-progress',str(path),'-nostats']

    def progress(self,pid):
        job=self.processing.get(pid)
        if not job: return None
        phase,duration,path=job
        try:
            with path.open('rb') as f:
                f.seek(max(0,path.stat().st_size-8192))
                text=f.read().decode('utf-8','replace')
            values=re.findall(r'^out_time_us=(\d+)$',text,re.M)
            percent=min(99,int(int(values[-1])/1000000/duration*100)) if values else 0
            return {'phase':phase,'percent':percent}
        except OSError: return {'phase':phase,'percent':0}

    def render(self,p):
        folder=self.root/p['id']; folder.mkdir(exist_ok=True)
        frames=self.rows('SELECT * FROM frames WHERE project=? ORDER BY slot LIMIT 250',(p['id'],))
        s=json.loads(p['settings']); seq=len(self.rows('SELECT number FROM segments WHERE project=?',(p['id'],)))
        work=folder/'work'; work.mkdir(exist_ok=True)
        try:
            self.require_space(32*1024**2)
            if frames:
                if not (folder/'poster.jpg').is_file():
                    atomic(folder/'poster.jpg',Path(frames[-1]['path']).read_bytes())
                for old in work.glob('*.jpg'): old.unlink()
                for index,f in enumerate(frames): os.symlink(f['path'],work/f'{index:06d}.jpg')
                target=folder/f'segment-{seq:06d}.ts'; tmp=folder/f'.segment-{seq:06d}.ts'
                run(['ffmpeg','-nostdin','-v','error',*self.progress_args(p['id'],'Bilder verarbeiten',len(frames)/s['fps']),'-framerate',str(s['fps']),'-i',str(work/'%06d.jpg'),'-frames:v',str(len(frames)),
                     '-an','-c:v','libx264','-preset','veryfast','-crf','18','-pix_fmt','yuv420p','-threads','1','-g',str(s['fps']*10),'-f','mpegts','-y',str(tmp)],180)
                # Very short first previews can otherwise be misdetected as MPEG-PS.
                # Valid MPEG-TS null packets guarantee enough sync bytes for probing.
                with tmp.open('ab') as output:
                    while output.tell() < 188*64:
                        output.write(b'\x47\x1f\xff\x10'+b'\xff'*184)
                os.replace(tmp,target)
                with self.lock,self.db:
                    self.db.execute('INSERT OR REPLACE INTO timeline VALUES(?,?,?)',(p['id'],seq,json.dumps([f['slot'] for f in frames])))
                    self.db.execute('INSERT INTO segments VALUES(?,?,?,?,?,?)',(p['id'],seq,str(target),len(frames),target.stat().st_size,time.time()))
                    self.db.executemany('DELETE FROM frames WHERE project=? AND slot=?',[(p['id'],f['slot']) for f in frames])
                for f in frames:
                    if not s['keepFrames']: Path(f['path']).unlink(missing_ok=True)
            remaining=self.rows('SELECT slot FROM frames WHERE project=? LIMIT 1',(p['id'],))
            segments=self.rows('SELECT * FROM segments WHERE project=? ORDER BY number',(p['id'],))
            if segments and not (folder/'poster.jpg').is_file():
                # Backfill older projects when rendering/exporting, never on the Live request path.
                poster=folder/'.poster.jpg'
                run(['ffmpeg','-nostdin','-v','error','-i',segments[-1]['path'],'-frames:v','1','-threads','1','-q:v','3','-y',str(poster)],30)
                os.replace(poster,folder/'poster.jpg')
            if p['export'] and not remaining and segments:
                concat=folder/'concat.txt'
                atomic(concat,''.join("file '"+Path(x['path']).name+"'\n" for x in segments).encode())
                dest=folder/'export.mp4'; tmp=folder/'.export.mp4'
                run(['ffmpeg','-nostdin','-v','error',*self.progress_args(p['id'],'MP4 zusammenfügen',sum(x['frames'] for x in segments)/s['fps']),'-f','concat','-safe','1','-i',str(concat),'-c','copy','-movflags','+faststart','-y',str(tmp)],600)
                os.replace(tmp,dest)
                self.write("UPDATE projects SET export=0,nas='',exported=? WHERE id=?",(sum(x['frames'] for x in segments),p['id']))
            if p['export'] and not frames and not segments:
                self.write("UPDATE projects SET export=0,error='Noch keine Bilder fuer den Export vorhanden.' WHERE id=?",(p['id'],))
            self.write("UPDATE projects SET error='' WHERE id=? AND error NOT LIKE 'Aufnahmeluecke:%'",(p['id'],))
            self.render_retry.pop(p['id'],None)
        except Exception as e:
            self.render_retry[p['id']]=time.time()+60
            self.write("UPDATE projects SET error=? WHERE id=? AND error NOT LIKE 'Aufnahmeluecke:%'",(f'Verarbeitung: {type(e).__name__}: {str(e)[:200]}',p['id']))
        finally:
            self.processing.pop(p['id'],None)
            for link in work.glob('*.jpg'): link.unlink(missing_ok=True)

    def archive(self,p):
        # An absent mount must never silently fill the underlying local directory.
        dest=Path(os.environ.get('NKL_TIMELAPSE_NAS','/mnt/nkl-timelapse'))
        marker=dest/'.nkl-timelapse-target'
        if not os.path.ismount(dest) or not marker.is_file() or marker.read_text().strip()!='NKL_TIMELAPSE':
            self.write('UPDATE projects SET nas=? WHERE id=?',('NAS nicht verfuegbar; Export bleibt lokal.',p['id'])); return
        source=self.root/p['id']/'export.mp4'
        target=dest/(p['channel']+'-'+p['id']+'.mp4'); temp=target.with_suffix('.partial')
        if target.is_file() and target.stat().st_size==source.stat().st_size and p['nas']=='gesichert':
            if p['status']=='finished': source.unlink(missing_ok=True)
            return
        run(['cp',str(source),str(temp)],600)
        def digest(path):
            with path.open('rb') as f: return hashlib.file_digest(f,'sha256').hexdigest()
        if digest(temp)!=digest(source): raise ValueError('NAS-Pruefsumme stimmt nicht')
        os.replace(temp,target)
        self.write("UPDATE projects SET nas='gesichert' WHERE id=?",(p['id'],))
        if p['status']=='finished': source.unlink(missing_ok=True)

    def archive_isolated(self,p):
        # NAS filesystems may hang in kernel I/O; isolate them from scheduler,
        # capture and rendering. Even an unavailable NAS cannot stall Live.
        try:
            run(['python3', str(Path(__file__).with_name('archive.py')), str(self.root), p['id']], 90)
        except Exception as e:
            self.write('UPDATE projects SET nas=? WHERE id=?',('NAS nicht erreichbar; Export bleibt lokal. '+type(e).__name__,p['id']))

    def transfer_isolated(self,plan):
        process=None
        try:
            plan_path=self.root/'transfer-plan.json'
            transfer.save_json(plan_path,plan,private=True)
            args=['python3',str(Path(__file__).with_name('transfer.py')),str(self.root),'--plan-file',str(plan_path)]
            if self.transfer_cancel.is_set():return
            process=subprocess.Popen(args,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
            last_change=time.monotonic();previous=None
            while process.poll() is None:
                if self.transfer_cancel.is_set():
                    process.kill();process.wait();return
                try: current=(self.root/'transfer-result.json').stat().st_mtime_ns
                except OSError: current=None
                if current!=previous:
                    previous=current;last_change=time.monotonic()
                if time.monotonic()-last_change>300:
                    raise TimeoutError('Uploadworker ohne Statusaktualisierung')
                time.sleep(1)
            if process.returncode:raise RuntimeError('Uploadworker beendet')
        except Exception as error:
            if process and process.poll() is None:
                process.kill();process.wait()
            try: details=json.loads((self.root/'transfer-result.json').read_text())
            except (OSError,ValueError):details={}
            transfer.save_json(self.root/'transfer-result.json',{**details,'origin':plan['origin'],'state':'error','at':time.time(),'message':'Uploadworker beendet oder ohne Rückmeldung ('+type(error).__name__+'). Lokale Dateien bleiben erhalten.'})

        finally:
            if self.transfer_cancel.is_set():
                transfer.save_json(self.root/'transfer-result.json',{'state':'idle','origin':plan['origin']})

    def prepare_transfer(self,projects,origin,now):
        self.transfer_cancel.clear()
        names=transfer.filenames(self.rows('SELECT * FROM projects'),{c['id']:c['name'] for c in self.known_channels()})
        self.transfer_plan={'origin':origin,'files':{p['id']:names[p['id']] for p in projects}}
        self.transfer_pending=True;self.transfer_started=now
        for p in projects:
            pending=self.rows('SELECT COUNT(*) AS n FROM frames WHERE project=?',(p['id'],))[0]['n']
            rendered=self.rows('SELECT COALESCE(SUM(frames),0) AS n FROM segments WHERE project=?',(p['id'],))[0]['n']
            if pending or rendered>p['exported'] or (rendered and not (self.root/p['id']/'export.mp4').exists()):
                self.write('UPDATE projects SET export=1 WHERE id=?',(p['id'],))

    def schedule_transfer(self,now):
        config=transfer.read_config(self.root)
        if self.transfer_job and not self.transfer_job.done():return
        if config['enabled'] and now>=self.next_transfer and not self.transfer_pending:
            self.next_transfer=now+config['intervalMinutes']*60
            candidates=[p for p in self.rows('SELECT * FROM projects')
                        if (not config['autoChannels'] or p['channel'] in config['autoChannels'])
                        and (not config['onlyFinished'] or p['status']=='finished')
                        and (config['mode']=='both' or (config['mode']=='daily')==bool(p['day']))]
            if candidates:self.prepare_transfer(candidates,'automatic',now)
        if self.transfer_pending:
            waiting=any(p['id'] in self.transfer_plan['files'] and p['export'] and not p['error'] for p in self.rows('SELECT id,export,error FROM projects'))
            if not waiting or now-self.transfer_started>900:
                self.transfer_pending=False
                self.transfer_job=self.transfer_pool.submit(self.transfer_isolated,dict(self.transfer_plan))

    def tick(self,now=None):
        with self.lock:
            return self._tick_locked(now)

    def _tick_locked(self,now=None):
        now=time.time() if now is None else now
        self.schedule(now)
        self.cleanup_retention(now)
        self.schedule_transfer(now)
        if now>=self.next_archive and not self.transfer_pending and (not self.transfer_job or self.transfer_job.done()) and (not self.archive_job or self.archive_job.done()):
            self.next_archive=now+60
            for p in self.rows("SELECT * FROM projects WHERE exported>0 AND (nas!='gesichert' OR status='finished') ORDER BY started"):
                if json.loads(p['settings'])['nas'] and (self.root/p['id']/'export.mp4').is_file():
                    self.archive_job=self.archive_pool.submit(self.archive_isolated,p); break
        if not self.capture_job or self.capture_job.done():
            for p in self.rows("SELECT * FROM projects WHERE status='recording' AND next<=? ORDER BY next",(now,)):
                s=json.loads(p['settings']); channel=self.rows('SELECT settings FROM channels WHERE id=?',(p['channel'],))
                if not self.channel_active(p['channel']) or not channel or not json.loads(channel[0]['settings'])['enabled']: continue
                missed=max(0,int((now-p['next'])//s['interval']))
                slot=int(now//s['interval'])*s['interval']
                # Persist the slot before launching the worker: crash recovery cannot duplicate it.
                with self.lock,self.db:
                    self.db.execute('UPDATE projects SET next=?,missed=missed+? WHERE id=?',(slot+s['interval'],missed,p['id']))
                    self.db.execute("INSERT OR IGNORE INTO attempts VALUES(?,?,'pending')",(p['id'],slot))
                self.capture_job=self.capture_pool.submit(self.capture,p,slot); break
        if not self.render_job or self.render_job.done():
            for p in self.rows('SELECT * FROM projects ORDER BY last'):
                if self.render_retry.get(p['id'],0)>now: continue
                if self.archive_job and not self.archive_job.done() and p['export']: continue
                frames=self.rows('SELECT COUNT(*) AS n FROM frames WHERE project=?',(p['id'],))[0]['n']
                segments=self.rows('SELECT MAX(created) AS last FROM segments WHERE project=?',(p['id'],))
                last=segments[0]['last'] or 0
                needs_poster=bool(last) and not (self.root/p['id']/'poster.jpg').is_file()
                if needs_poster or (frames and (frames>=250 or (frames>=2 and (not last or now-last>=300)) or p['export'])) or (p['export'] and not frames):
                    self.render_job=self.render_pool.submit(self.render,p); break

        if not self.render_job or self.render_job.done():
            for p in self.rows('SELECT * FROM projects ORDER BY started DESC'):
                if self.render_retry.get(p['id'],0)>now:continue
                variants=self.qualities(p['id'])
                info=self.rows('SELECT project FROM media_info WHERE project=?',(p['id'],))
                if variants[0]['ready'] and (not info or any(not q['ready'] for q in variants)):
                    self.render_job=self.render_pool.submit(self.render_quality,p);break

    def timeline(self,p):
        if not p['day']: return {'markers':[]}
        s=json.loads(p['settings'])
        segments=self.rows('SELECT number,frames FROM segments WHERE project=? ORDER BY number',(p['id'],))
        total=sum(x['frames'] for x in segments)
        saved={x['segment']:json.loads(x['slots']) for x in self.rows('SELECT * FROM timeline WHERE project=?',(p['id'],))}
        old=self.rows("SELECT slot FROM attempts WHERE project=? AND status='done' AND slot NOT IN (SELECT slot FROM frames WHERE project=?) ORDER BY slot",(p['id'],p['id']))
        fallback=[x['slot'] for x in old] if len(old)==total else []
        markers=[]; offset=0; previous=None
        for segment in segments:
            slots=saved.get(segment['number'],fallback[offset:offset+segment['frames']])
            if len(slots)==segment['frames']:
                for index,slot in enumerate(slots):
                    stamp=datetime.fromtimestamp(slot,ZoneInfo(s['timezone']))
                    bucket=stamp.strftime('%Y-%m-%d %H %z')
                    if bucket!=previous:
                        markers.append({'position':(offset+index)/s['fps'],'label':stamp.strftime('%H:%M'),'hour':stamp.hour})
                        previous=bucket
            offset+=segment['frames']
        return {'markers':markers,'duration':total/s['fps'] if total else 0}

    def status(self,channel=None,public=False):
        result=[]
        project_rows=self.rows('SELECT * FROM projects ORDER BY started DESC')
        file_names=transfer.filenames(project_rows,{c['id']:c['name'] for c in self.known_channels()})
        for p in project_rows:
            s=json.loads(p['settings'])
            if channel and p['channel']!=channel: continue
            if public and (not self.channel_active(p['channel']) or not s['public']): continue
            segments=self.rows('SELECT SUM(frames) AS n FROM segments WHERE project=?',(p['id'],))
            pending=self.rows('SELECT COUNT(*) AS n FROM frames WHERE project=?',(p['id'],))[0]['n']
            item={k:p[k] for k in ('id','channel','label','status','started','last','ends','next')}
            item.update(frames=(segments[0]['n'] or 0)+pending,previewFrames=segments[0]['n'] or 0, fps=s['fps'])
            if not public: item.update(filename=file_names[p['id']],day=p['day'],settings=s,missed=p['missed'],error=p['error'],exported=p['exported'],exportPending=bool(p['export']),nas=p['nas'],progress=self.progress(p['id']))
            result.append(item)
        if public: return {'active':self.channel_active(channel),'projects':result}
        target=transfer.safe_config(transfer.read_config(self.root))
        try: target_status=json.loads((self.root/'transfer-result.json').read_text())
        except (OSError,ValueError): target_status={'state':'idle'}
        if self.transfer_pending: target_status={'state':'preparing','origin':self.transfer_plan['origin']}
        channels={c['id']:c for c in self.rows('SELECT * FROM channels')}
        return {'globalSettings':self.global_settings(),'transfer':target,'transferTest':(self.transfer_test_job.result() if self.transfer_test_job.done() else {'state':'running','message':'Verbindung wird geprüft …'}) if self.transfer_test_job else None,'transferStatus':target_status,'projects':result,'channels':[{**c,'active':bool(channels.get(c['id'],{}).get('active',False)),'armed':bool(channels.get(c['id'],{}).get('armed',False)),'settings':json.loads(channels[c['id']]['settings']) if c['id'] in channels else DEFAULT,'error':channels.get(c['id'],{}).get('error','')} for c in self.known_channels()], 'quotaBytes':self.quota,'reserveBytes':self.min_free,'storageBytes':self.last_usage[1],'diskFreeBytes':shutil.disk_usage(self.root).free,'diskTotalBytes':shutil.disk_usage(self.root).total}

    def close(self):
        self.capture_pool.shutdown(wait=True); self.render_pool.shutdown(wait=True); self.archive_pool.shutdown(wait=True); self.transfer_pool.shutdown(wait=True); self.transfer_test_pool.shutdown(wait=True); self.db.close()
