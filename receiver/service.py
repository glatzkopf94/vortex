"""Private Unix-socket control plane and camera process supervisor."""
import json
import math
import os
import re
import socketserver
import subprocess
import tempfile
import threading
import time
import uuid
from http.server import BaseHTTPRequestHandler
from pathlib import Path

ROOT = Path('/var/lib/vortex-reolink')
SOCKET = Path('/run/vortex-reolink/control.sock')
LOCK = threading.RLock()
cameras = {}
workers = {}
states = {}
tests = {}


def restart(cid):
    states[cid] = 'Empfänger wird neu gestartet'
    process = workers[cid]
    process.terminate()

    def finish():
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()

    threading.Thread(target=finish, daemon=True).start()



def atomic(path, data):
    with tempfile.NamedTemporaryFile(mode='w', dir=path.parent, delete=False) as f:
        try:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
            os.replace(f.name, path)
        finally:
            Path(f.name).unlink(missing_ok=True)


def public(cam):
    return {key: cam[key] for key in ('id', 'name', 'port', 'uid', 'username')}


def field(body, key, maximum):
    value = body.get(key)
    if not isinstance(value, str) or not 0 < len(value) <= maximum or any(ord(c) < 32 or ord(c) == 127 for c in value):
        raise ValueError('Ungültiges Feld: ' + key)
    return value


def save(body):
    with LOCK:
        cid = body.get('id')
        old = cameras.get(cid)
        if cid and not old:
            raise ValueError('Kamera unbekannt')
        cam = dict(old or {})
        cam['name'] = field(body, 'name', 100)
        for key in ('uid', 'username', 'password'):
            if not old or body.get(key):
                cam[key] = field(body, key, 256)
        # Preserve existing Test55 preferences for rollback. New or reassigned
        # cameras should also select dynamic ACK if reopened with Test55.
        if not old or cam['uid'] != old['uid']:
            cam.update(profile='auto', dynamic_profile=True)
            cam.pop('detected', None)
            cam.pop('dynamic_detected', None)
        if any(c['uid'] == cam['uid'] and c['id'] != cid for c in cameras.values()):
            raise ValueError('Diese UID ist bereits gespeichert. Kamera aus der Liste auswählen.')
        if not old:
            cam['id'] = uuid.uuid4().hex
            used = {c['port'] for c in cameras.values()}
            cam['port'] = next(p for p in range(18554, 28554) if p not in used)
        cid = cam['id']
        atomic(ROOT / 'cameras.json', json.dumps({**cameras, cid: cam}))
        cameras[cid] = cam
        if cid not in workers or not old or any(cam[k] != old[k] for k in ('uid', 'username', 'password')):
            tests.pop(cid, None)
            if cid in workers:
                restart(cid)
            else:
                start(cam)
        return public(cam)


def start(cam):
    cid = cam['id']
    config = ROOT / (cid + '.toml')
    values = {'name': cid, **{k: cam[k] for k in ('uid', 'username', 'password')}}
    text = 'bind = "0.0.0.0"\nbind_port = %d\n[[cameras]]\n' % cam['port']
    text += 'discovery = "relay"\nstream = "both"\npush_notifications = false\nuse_splash = false\n'
    atomic(config, text + ''.join(k + ' = ' + json.dumps(v, ensure_ascii=False) + '\n' for k, v in values.items()))
    env = {**os.environ, 'VORTEX_ACK_PROFILE': 'dynamic', 'RUST_LOG': 'info', 'NO_COLOR': '1'}
    p = subprocess.Popen(['neolink', 'rtsp', '--config', str(config)], env=env,
                         stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    workers[cid] = p
    states[cid] = 'Suche per UID'
    threading.Thread(target=watch, args=(cid, p), daemon=True).start()


def watch(cid, proc):
    # Keep only known state transitions. Raw upstream logs can contain credentials.
    markers = [(b'Connecting to camera at', 'Suche per UID'), (b': Logging in', 'Kamera gefunden, Anmeldung läuft'),
               (b'Connected and logged in', 'Angemeldet'), (b'Connection Lost:', 'Verbindung unterbrochen'),
               (b'Login credentials were not accepted', 'Kamera gefunden, Anmeldung abgelehnt')]
    with proc.stdout:
        for line in proc.stdout:
            for marker, state in markers:
                if marker in line:
                    with LOCK:
                        previous = states.get(cid)
                        if previous == 'Empfänger wird neu gestartet':
                            break
                        if marker == b'Connection Lost:' and previous == 'Suche per UID':
                            states[cid] = 'UID-Suche: Kamera bisher nicht gefunden'
                        else:
                            states[cid] = state
                    break
    proc.wait()
    time.sleep(4)
    with LOCK:
        if workers.get(cid) is proc:
            start(cameras[cid])


def evaluate(output, duration):
    rows = [dict(part.split('=', 1) for part in line.split('|')[1:] if '=' in part)
            for line in output.splitlines()]
    frames = [float(r['best_effort_timestamp_time']) for r in rows
              if re.fullmatch(r'-?\d+(\.\d+)?', r.get('best_effort_timestamp_time', ''))]
    stream = next((r for r in rows if r.get('codec_name') in ('h264', 'hevc')), {})
    span = frames[-1] - frames[0] if frames else 0
    if not stream:
        raise ValueError('Kein H.264-/H.265-Videostream mit Codec-Angabe')
    if not int(stream.get('width', 0)) or not int(stream.get('height', 0)):
        raise ValueError('Videocodec erkannt, Auflösung fehlt')
    if len(frames) < 8 or not math.isfinite(span) or span < 4:
        raise ValueError(f'Zu wenig Videofortschritt: {len(frames)} Bilder mit Zeitstempel, {span:.1f} s Medienzeit')
    if any(b <= a or b-a > 1.5 for a, b in zip(frames, frames[1:])):
        raise ValueError('Dekodierte Bilder, aber Zeitstempel stehen oder springen')
    if duration > span * 1.25 + 0.35:
        raise ValueError(f'Empfang zu langsam: {span:.1f} s Medienzeit in {duration:.1f} s')
    return f"{stream['width']} × {stream['height']} · {stream['codec_name'].upper()} · {len(frames)} Bilder in {span:.1f} s"


class NoVideoPackets(ValueError):
    pass


def sample(address, options):
    command = ['stdbuf', '-oL', 'ffprobe', '-v', 'error', *options, '-select_streams', 'v:0',
               '-read_intervals', '%+6', '-show_packets', '-show_frames', '-show_streams', '-show_entries',
               'packet=size:frame=best_effort_timestamp_time:stream=codec_name,width,height',
               '-of', 'compact', address]
    with subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True) as process:
        timer = threading.Timer(35, process.kill)
        timer.start()
        try:
            first = last = None
            packets = 0
            lines = []
            reason = ''
            for line in process.stdout:
                if line.startswith('packet|'):
                    packets += 1
                elif line.startswith(('frame|','stream|')):
                    lines.append(line)
                    if len(lines) > 4096:
                        process.kill()
                        raise ValueError('Zu viele Bilder im Prüfintervall')
                    if line.startswith('frame|'):
                        last = time.monotonic()
                        if first is None:
                            first = last
                elif 'timed out' in line.lower():
                    reason = 'RTSP-Zeitlimit erreicht'
                elif 'method DESCRIBE failed' in line or 'Server returned' in line:
                    reason = 'RTSP-Anfrage vom Empfänger abgewiesen'
            status = process.wait()
            if first is None:
                detail = f'{packets} Videopakete, kein dekodiertes Bild' if packets else 'keine auswertbaren Videopakete'
                failure = ValueError if packets else NoVideoPackets
                raise failure((reason or 'RTSP-Prüfung') + ': ' + detail)
            if status:
                raise ValueError(f'Messfenster unvollständig: {packets} Pakete und {len(lines)} Bild-/Streamzeilen')
            return evaluate(''.join(lines), last-first)
        finally:
            timer.cancel()


def check_stream(cam, kind, job):
    cid = cam['id']
    deadline = time.monotonic()+40
    while True:
        with LOCK:
            if tests.get(cid) is not job:
                raise ValueError('Einrichtung geändert')
            state = states.get(cid, 'Suche per UID')
            job['message'] = state
        if state == 'Angemeldet':
            break
        if 'abgelehnt' in state:
            raise ValueError(state)
        if time.monotonic() >= deadline:
            raise ValueError('Anmeldung nicht bestätigt · '+state)
        time.sleep(.4)
    address = f"rtsp://127.0.0.1:{cam['port']}/{cid}/{kind}"
    options = ['-rtsp_transport','tcp','-timeout','25000000','-analyzeduration','3000000','-probesize','8000000']
    job['message'] = 'Angemeldet, prüfe Video und Zeitstempel'
    # Some cameras report login before the real stream is mounted.
    warmup = time.monotonic()+8
    while True:
        try:
            result = sample(address, options)
            break
        except NoVideoPackets:
            if time.monotonic() >= warmup:
                raise
            time.sleep(1)
            with LOCK:
                if tests.get(cid) is not job:
                    raise ValueError('Einrichtung geändert')
    return result


def probe(cam, kind, job):
    cid = cam['id']
    try:
        result = check_stream(cam, kind, job)
        status, message = 'ok', result
    except ValueError as exc:
        status, message = 'error', str(exc)
    except (OSError, subprocess.SubprocessError):
        status, message = 'error', 'Empfangsdienst konnte die Prüfung nicht abschließen'
    with LOCK:
        if tests.get(cid) is job:
            if status == 'error' and cid in workers and 'abgelehnt' not in states.get(cid, ''):
                restart(cid)
                message += ' · Kamera-Empfänger wird neu gestartet'
            job.update(status=status, message=message)


def dispatch(path, body):
    with LOCK:
        if path == '/cameras':
            return {'cameras': [public(c) for c in cameras.values()]}
        if path == '/save':
            return save(body)
        cid = body.get('id')
        if cid not in cameras or body.get('stream') not in ('main', 'sub'):
            raise ValueError('Kamera oder Stream unbekannt')
        kind = body['stream']
        job = tests.get(cid)
        if path == '/status' and body.get('core_failed') is True:
            if not job or job['stream'] != kind or job['token'] != body.get('token'):
                raise ValueError('Prüfung abgelaufen')
            if job['status'] == 'ok':
                restart(cid)
                job.update(status='error', message='Vortex konnte den RTSP-Stream nicht öffnen · Kamera-Empfänger wird neu gestartet')
            return job.copy()
        if path == '/probe' and (not job or job['status'] != 'running'):
            job = tests[cid] = dict(stream=kind, status='running', message='Suche per UID', token=uuid.uuid4().hex)
            threading.Thread(target=probe, args=(cameras[cid], kind, job), daemon=True).start()
        if not job or job['stream'] != kind or (path == '/status' and job['token'] != body.get('token')):
            raise ValueError('Andere Prüfung aktiv oder Ergebnis abgelaufen')
        return job.copy()


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *args):
        pass

    def handle_control(self):
        try:
            length = int(self.headers.get('Content-Length', 0))
            if not 0 <= length <= 8192:
                raise ValueError('Anfrage zu groß')
            body = json.loads(self.rfile.read(length)) if length else {}
            if not isinstance(body, dict):
                raise ValueError('Ungültige Anfrage')
            result = dispatch(self.path, body)
            code = 200
        except (ValueError, TypeError) as exc:
            result, code = {'code':400, 'message': str(exc) if isinstance(exc, ValueError) else 'Ungültige Anfrage'}, 400
        except Exception:
            result, code = {'code':500, 'message': 'Empfangsdienst konnte die Anfrage nicht abschließen'}, 500
        data = json.dumps(result).encode()
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Content-Length', str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    do_GET = do_POST = handle_control


if __name__ == '__main__':
    os.umask(0o077)
    ROOT.mkdir(mode=0o700, parents=True, exist_ok=True)
    db = ROOT / 'cameras.json'
    if db.exists():
        cameras.update(json.loads(db.read_text()))
    with LOCK:
        for camera in cameras.values():
            start(camera)
    SOCKET.parent.mkdir(parents=True, exist_ok=True)
    SOCKET.unlink(missing_ok=True)
    with socketserver.UnixStreamServer(str(SOCKET), Handler) as server:
        server.serve_forever()
