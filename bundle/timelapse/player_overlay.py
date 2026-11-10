"""Draw channel player overlays during the existing single-frame capture only.

Read canonical Core metadata and the same polled text as the live player. Never
fetch camera/JSON URLs or change a live process from the capture worker.
"""
import json
import math
from pathlib import Path
import re
import time

FONTS = {'sans':'DejaVuSans.ttf','sans-bold':'DejaVuSans-Bold.ttf',
         'serif':'DejaVuSerif.ttf','mono':'DejaVuSansMono.ttf'}
TOKEN = re.compile(r'{{\s*[A-Za-z][A-Za-z0-9_-]*\.[A-Za-z0-9_.-]+(?:\s*\|\s*number\s*:\s*[0-3])?\s*}}')


def number(value, low, high, default):
    try:
        n=float(value)
        return min(high,max(low,n)) if math.isfinite(n) else default
    except (ValueError,TypeError): return default


def quoted(path):
    # Two filtergraph escaping layers, no shell interpolation.
    s=str(path).replace('\\','\\\\').replace("'", "'\\''").replace(':','\\:')
    return "'"+s+"'"


def color(value, default):
    return '0x'+(value if isinstance(value,str) and re.fullmatch(r'#[0-9a-fA-F]{6}',value) else default)[1:]


def position(value, gap, logo=False):
    if value not in ('top-left','top-center','top-right','bottom-left','bottom-center','bottom-right'):
        value='bottom-left'
    w,h,tw,th=('W','H','w','h') if logo else ('w','h','tw','th')
    x=str(gap) if value.endswith('left') else f'({w}-{tw})/2' if value.endswith('center') else f'{w}-{tw}-{gap}'
    y=str(gap) if value.startswith('top') else f'{h}-{th}-{gap}'
    return x,y


def capture_filter(core_db, data, channel, width, height, base, text_snapshot, now=None):
    """Return a graph with [tlout], or None when the channel overlay is off."""
    if not re.fullmatch(r'[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}',channel):
        raise ValueError('Ungültiger Overlay-Kanal')
    database=json.loads(Path(core_db).read_text())
    metadata=database.get('metadata',{}).get('process',{}).get('restreamer-ui:ingest:'+channel,{}).get('restreamer-ui',{})
    cfg=(metadata.get('player') or {}).get('overlay') or {}
    if cfg.get('enabled') is not True: return None
    scale=min(width/1280,height/720)
    # Match TextOverlay.js: fixed pixel offsets, not browser CSS scaling.
    # drawtext x/y anchor the text; the 16px box extends toward the image edge.
    gap=24; filters=[f'[0:v]{base}[tl0]']; current='tl0'; index=0
    template=str(cfg.get('template') or '')[:16384]
    text=TOKEN.sub('--',template)
    cache=Path(data)/'channels'/channel/'player-overlay.txt'
    interval=number(cfg.get('interval'),15,3600,60)
    # Old values must not silently become historic measurements in a recording.
    try:
        if not cache.is_symlink() and cache.resolve().is_relative_to(Path(data).resolve()) and (time.time() if now is None else now)-cache.stat().st_mtime<=2*interval+15:
            with cache.open('rb') as f: text=f.read(16384).decode('utf-8','replace')
    except FileNotFoundError: pass
    if text:
        Path(text_snapshot).write_text(text,encoding='utf-8')
        font=FONTS.get(cfg.get('font'),'DejaVuSans.ttf')
        size=max(1,round(number(cfg.get('fontSize'),8,200,32)*scale))
        x,y=position(cfg.get('position'),gap)
        opts=[f'textfile={quoted(text_snapshot)}','expansion=none',
              f'fontfile={quoted("/usr/share/fonts/truetype/dejavu/"+font)}',
              f'fontsize={size}',f'fontcolor={color(cfg.get("fontColor"),"#ffffff")}',f'x={x}',f'y={y}']
        if cfg.get('box') is True:
            opts.extend(['box=1',f'boxcolor={color(cfg.get("boxColor"),"#000000")}@{number(cfg.get("boxOpacity"),0,1,.55):.3f}','boxborderw=16'])
        index+=1;filters.append(f'[{current}]drawtext='+':'.join(opts)+f'[tl{index}]');current=f'tl{index}'
    for n in (1,2):
        logo=cfg.get(f'logo{n}') or {};path=logo.get('path','')
        if logo.get('enabled') is not True: continue
        if not isinstance(path,str) or not re.fullmatch('/channels/'+re.escape(channel)+f'/playeroverlaylogo{n}\\.(png|jpg|jpeg|webp)',path,re.I):
            raise ValueError('Ungültiger Player-Logo-Pfad')
        image=Path(data)/path.lstrip('/')
        if image.is_symlink() or not image.resolve().is_relative_to(Path(data).resolve()) or not image.is_file():
            raise ValueError('Player-Logo nicht verfügbar')
        size=max(1,round(min(width*.45,number(logo.get('width'),16,2000,240)*scale)))
        opacity=number(logo.get('opacity'),.05,1,1)
        filters.append(f'movie=filename={quoted(image)},scale={size}:-1,format=rgba,colorchannelmixer=aa={opacity:.3f}[logo{n}]')
        x,y=position(logo.get('position'),gap,True)
        index+=1;filters.append(f'[{current}][logo{n}]overlay=x={x}:y={y}:shortest=1[tl{index}]');current=f'tl{index}'
    filters.append(f'[{current}]null[tlout]')
    return ';'.join(filters)
