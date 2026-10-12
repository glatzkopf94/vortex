import React from 'react';
import NotifyContext, {useStatusNotifications} from '../contexts/Notify';
import TimelapsePreview from './TimelapsePreview';
import { Box, Button, Checkbox, FormControlLabel, MenuItem, Stack, TextField, Typography } from '@mui/material';

const statusText = {recording:'Aufnahme läuft', paused:'Pausiert', finished:'Beendet'};
export default function Timelapse({restreamer}) {
  const notify=React.useContext(NotifyContext);
  const [data,setData]=React.useState(null);
  const [channel,setChannel]=React.useState(()=>{try{return sessionStorage.getItem('nkl-timelapse-channel')||'';}catch{return '';}});
  const [form,setForm]=React.useState(null);
  const [error,setError]=React.useState('');
  const [busy,setBusy]=React.useState(false);
  const [notice,setNotice]=React.useState('');
  useStatusNotifications({
    'timelapse:error':error?{severity:'error',message:error}:null,
    'timelapse:background':data?.projects?.some(p=>p.error)||data?.channels?.some(c=>c.error)?{severity:'error',message:[...(data.projects||[]).filter(p=>p.error).map(p=>`${p.label}: ${p.error}`),...(data.channels||[]).filter(c=>c.error).map(c=>`${c.name}: ${c.error}`)].join(' · ')}:null,
  });
  const success=(message)=>{setNotice(message);notify.Dispatch('success','timelapse:action',message);};
  const call=React.useCallback(async (action) => {
    const [val,err]=await restreamer._call(restreamer.api._call,action?'POST':'GET','/v3/timelapse/'+(action?'action':'status'),action?{headers:{'Content-Type':'application/json'},body:JSON.stringify(action)}:{});
    if(err)throw new Error(err.message);
    return val;
  },[restreamer]);
  const refresh=React.useCallback(async()=>{
    try {setData(await call());} catch(e){setError(String(e.message));}
  },[call]);
  React.useEffect(()=>{refresh(); const id=setInterval(refresh,2000);return()=>clearInterval(id);},[refresh]);
  React.useEffect(()=>{if(data&&channel&&!form){const saved=data.channels.find(c=>c.id===channel);if(saved)setForm({...saved.settings});else setChannel('');}},[data,channel,form]);
  const choose=(id)=>{try{sessionStorage.setItem('nkl-timelapse-channel',id);}catch{}setChannel(id);setForm({...data.channels.find(c=>c.id===id).settings});setNotice('');};
  const change=(key,value)=>{setForm(previous=>({...previous,[key]:value,...(key==='mode'&&value==='season'?{interval:Math.max(30,previous.interval)}:{})}));setNotice('Ungespeicherte Änderungen – bitte Einstellungen speichern.');};
  async function action(body) {
    setBusy(true);setError('');
    try {const result=await call(body);await refresh();success(body.action==='delete_finished'?`${result.deleted} abgeschlossene ${body.mode==='daily'?'Tages':'Saison'}zeitraffer lokal gelöscht.`:({configure_global:'Globale Overlay-Einstellung gespeichert. Gilt für die nächsten Einzelbilder aller Kanäle.',configure_transfer:'Externe Ablage gespeichert.',transfer_now:'Übertragung beauftragt.',configure:'Einstellungen gespeichert. Änderungen an Auflösung/FPS gelten für das nächste Projekt.',start:'Saisonaufnahme gestartet.',pause:'Aufnahme pausiert.',resume:'Aufnahme fortgesetzt.',stop:'Aufnahme beendet; Abschlussvideo wird erstellt.',export:'MP4-Aktualisierung beauftragt.',publish:'Veröffentlichung geändert.',delete:'Lokales Projekt gelöscht.'})[body.action] || 'Änderung gespeichert.');return result;}catch(e){setError(String(e.message));}
    finally{setBusy(false);}
  }
  async function download(project) {
    setBusy(true);
    try {
      const [val,err]=await restreamer._call(restreamer.api._call,'GET','/v3/timelapse/project/'+project.id+'/export.mp4',{expect:'blob'});
      if(err)throw new Error(err.message);
      const url=URL.createObjectURL(val);const a=document.createElement('a');a.href=url;a.download='Zeitraffer-'+project.id+'.mp4';a.click();success('MP4-Download an den Browser übergeben.');setTimeout(()=>URL.revokeObjectURL(url),60000);
    }catch(e){setError(String(e.message));}finally{setBusy(false);}
  }
  const number=(key,label,props={})=><TextField key={key} label={label} type="number" value={form[key]} onChange={e=>change(key,Number(e.target.value))} inputProps={props} fullWidth/>;
  const select=(key,label,options)=><TextField key={key} select label={label} value={form[key]} onChange={e=>change(key,e.target.value)} fullWidth>{options.map(([v,t])=><MenuItem key={v} value={v}>{t}</MenuItem>)}</TextField>;
  return <Stack spacing={2} sx={{p:2,minWidth:0,maxWidth:'100%',overflowWrap:'anywhere','& .MuiButton-outlined:not(.MuiButton-outlinedSecondary)':{color:'#fff',borderColor:'#aab4be',backgroundColor:'#303b45','&:hover':{backgroundColor:'#455461'},'&.Mui-disabled':{color:'#b9c0c7',borderColor:'#66717c',backgroundColor:'#30363c'}}}}>
    <Typography variant="h2">Zeitraffer · lokale Vorschau</Typography>
    <Typography>Eigene Aufnahme und Verarbeitung, unabhängig vom DVR. Eine Vorschau entsteht ab zwei Bildern und wird bei neuen Bildern etwa alle fünf Minuten ergänzt. Fehlzeiten werden übersprungen, nicht mit alten Bildern aufgefüllt.</Typography>
    {notice.startsWith('Ungespeicherte')&&<Typography>{notice}</Typography>}
    {data&&<>
      <FormControlLabel control={<Checkbox disabled={busy} checked={!!data.globalSettings?.includeBurnedOverlays} onChange={e=>action({action:'configure_global',includeBurnedOverlays:e.target.checked})}/>} label="Eingebrannte Vortex-Overlays im Zeitraffer übernehmen (alle Kanäle)"/>
      <Typography variant="body2">Ausgeschaltet: Bei Kanälen mit eingebrannten Vortex-Overlays wird pro Einzelbild kurz die ursprüngliche RTSP-/HTTP-Quelle abgerufen. Kameraeigene Einblendungen bleiben erhalten. Eingeschaltet: Bild aus dem laufenden Stream inklusive eingebrannter Overlays. Browser-Player-Overlays werden nicht übernommen. Gilt für neue Bilder, auch in laufenden Aufnahmen.</Typography>
      <Typography>Speicherplatz · Zeitraffer: {(data.storageBytes/1073741824).toFixed(2)} GB / {(data.quotaBytes/1073741824).toFixed(1)} GB. Auf dem Datenträger frei: {(data.diskFreeBytes/1073741824).toFixed(1)} GB von {(data.diskTotalBytes/1073741824).toFixed(1)} GB. Freie Reserve: {(data.reserveBytes/1073741824).toFixed(1)} GB.</Typography>
      <Typography variant="body2">Sammellöschung für alle Kanäle: Nur abgeschlossene Aufnahmen werden lokal gelöscht. Laufende/pausierte Projekte und NAS-Kopien bleiben erhalten.</Typography>
      <Box sx={{display:'flex',flexWrap:'wrap',gap:1}}>
        {['daily','season'].map(mode=>{
          const count=data.projects.filter(p=>p.status==='finished'&&p.settings.mode===mode).length;
          const label=mode==='daily'?'Tageszeitraffer':'Saisonzeitraffer';
          return <Box key={mode}><Typography variant="subtitle2">{label}</Typography><Button variant="outlined" color="secondary" disabled={busy||!count} onClick={()=>{if(window.confirm(`${count} abgeschlossene ${label} über ALLE Kanäle endgültig lokal löschen? Die andere Betriebsart, laufende/pausierte Projekte und NAS-Kopien bleiben erhalten.`))action({action:'delete_finished',mode});}}>Fertige Zeitraffer löschen ({count})</Button></Box>;
        })}
      </Box>
      <TextField select label="Kanal" value={channel} onChange={e=>choose(e.target.value)} fullWidth>{data.channels.map(c=><MenuItem key={c.id} value={c.id}>{c.name}</MenuItem>)}</TextField>
      {form&&<>
        {select('mode','Betriebsart',[['daily','Tageszeitraffer'],['season','Saison / manuell']])}
        <Box sx={{display:'grid',gridTemplateColumns:'repeat(auto-fit,minmax(min(100%,220px),1fr))',gap:2}}>
          {form.mode==='daily'?number('interval','Bildintervall in Sekunden',{min:15,max:86400,step:1}):<TextField label="Bildintervall in Minuten" type="text" inputProps={{inputMode:'decimal'}} defaultValue={form.interval/60} key={'minutes-'+channel} onBlur={e=>{const minutes=Number(e.target.value.replace(',','.'));change('interval',Math.round(minutes*60));}} helperText="0,5 bis 1440 Minuten (ein Bild pro Tag)." fullWidth/>}
          {number('fps','Videobilder pro Sekunde',{min:1,max:60})}
          {select('width','Bildbreite',[[0,'Originalauflösung der Streamquelle'],[640,'640 Pixel'],[1280,'1280 Pixel'],[1920,'1920 Pixel'],[3840,'3840 Pixel']])}
          <TextField label="Zeitzone" value={form.timezone} onChange={e=>change('timezone',e.target.value)} helperText="Zum Beispiel Europe/Berlin"/>
        </Box>
        <Typography variant="body2">Beschleunigung: {form.interval * form.fps}×. 24 Stunden ohne Lücken ergeben etwa {(86400 / form.interval / form.fps).toFixed(1)} Sekunden Video. FPS bestimmen die Abspielgeschwindigkeit, das Intervall die Aufnahmehäufigkeit.</Typography>
        <Typography variant="body2">Seitenverhältnis bleibt erhalten. Die gemeldete HLS-Bandbreite wird beim ersten Bild als Zielbitrate übernommen; die tatsächliche Videobitrate kann abweichen.</Typography>
        <Typography variant="body2">Täglich: 15 bis 86400 Sekunden. Saison: 0,5 bis 1440 Minuten (ein Bild pro Tag). Intervalländerungen gelten auch für laufende Projekte. Videoformat und Tagesfenster gelten ab dem nächsten Projekt.</Typography>
        {form.mode==='daily'&&<>
          {select('window','Aufnahmefenster',[['full','Ganzer Kalendertag'],['solar','Nach Sonnenstand']])}
          {form.window==='solar'&&<Box sx={{display:'grid',gridTemplateColumns:'repeat(auto-fit,minmax(min(100%,220px),1fr))',gap:2}}>
            {number('latitude','Breitengrad',{min:-89.8,max:89.8,step:0.001})}{number('longitude','Längengrad',{min:-180,max:180,step:0.001})}
            {select('startEvent','Beginn',[['sunrise','Sonnenaufgang'],['sunset','Sonnenuntergang']])}{number('startOffset','Beginn: Versatz in Minuten',{min:-360,max:360})}
            {select('endEvent','Ende',[['sunrise','Sonnenaufgang'],['sunset','Sonnenuntergang']])}{number('endOffset','Ende: Versatz in Minuten',{min:-360,max:360})}
            <Typography>−60 beginnt eine Stunde davor; +60 endet eine Stunde danach. Sonnenzeiten sind Näherungswerte ohne örtliche Horizontabschattung.</Typography>
          </Box>}
        </>}
        {[['enabled','Aufnahmeplan aktiv'],['public','Projekte im öffentlichen Player anbieten'],['nas','Fertige MP4 zusätzlich auf NAS sichern'],['keepFrames','Einzelbilder nach Videoverarbeitung behalten (mehr Speicherbedarf)']].map(([k,label])=><FormControlLabel key={k} control={<Checkbox checked={form[k]} onChange={e=>change(k,e.target.checked)}/>} label={label}/>)}
        <Typography variant="body2">NAS muss im Testcontainer eingebunden sein. Bei Ausfall bleibt der Export lokal. Die NAS-Anbindung hat keinen Einfluss auf Live/DVR.</Typography>
        <Box sx={{display:'flex',flexWrap:'wrap',gap:1,mt:1,'& > button':{flex:'1 1 150px',maxWidth:'100%',whiteSpace:'normal',overflowWrap:'normal'}}}>
          <Button variant="contained" disabled={busy} onClick={()=>action({action:'configure',channel,settings:form})}>Einstellungen speichern</Button>
          {form.mode==='season'&&<Button variant="outlined" disabled={busy} onClick={()=>action({action:'start',channel})}>Gespeicherte Saisonaufnahme starten</Button>}
        </Box>
      </>}
      {data.projects.filter(p=>!channel||p.channel===channel).map(p=><Box key={p.id} sx={{p:2,border:'1px solid',borderColor:'divider',borderRadius:1}}>
        <Typography variant="h3">{p.label.replace(/^(\d{4})-(\d{2})-(\d{2})$/, '$3.$2.$1')} · {statusText[p.status]}</Typography>
        <TimelapsePreview restreamer={restreamer} project={p}/>
        <Typography>{data.channels.find(c=>c.id===p.channel)?.name} · {p.frames} Bilder · {p.missed} verpasste Aufnahmezeitpunkte · Vorschau: {p.previewFrames} Bilder</Typography>
        {p.ends&&<Typography variant="body2">Aufnahmefenster: {new Date(p.started*1000).toLocaleString('de-DE',{timeZone:p.settings.timezone,day:'2-digit',month:'2-digit',year:'numeric',hour:'2-digit',minute:'2-digit'})} bis {new Date(p.ends*1000).toLocaleString('de-DE',{timeZone:p.settings.timezone,day:'2-digit',month:'2-digit',year:'numeric',hour:'2-digit',minute:'2-digit'})} ({p.settings.timezone})</Typography>}
        <Typography variant="body2">Intervall: {p.settings.interval} s · Letzte Aufnahme: {p.last?new Date(p.last*1000).toLocaleString('de-DE',{day:'2-digit',month:'2-digit',year:'numeric',hour:'2-digit',minute:'2-digit'}):'noch keine'} · {p.settings.public?'Öffentlich':'Nur Admin'}</Typography>
        {busy&&<Typography role="status">Vorgang läuft …</Typography>}
        {p.nas&&<Typography>NAS: {p.nas}</Typography>}
        <Box sx={{display:'flex',flexWrap:'wrap',gap:1,mt:1,'& > button':{flex:'1 1 150px',maxWidth:'100%',whiteSpace:'normal',overflowWrap:'normal'}}}>
          {p.status==='recording'&&<Button variant="outlined" disabled={busy} onClick={()=>action({action:'pause',project:p.id})}>Pausieren</Button>}
          {p.status==='paused'&&<Button variant="outlined" disabled={busy} onClick={()=>action({action:'resume',project:p.id})}>Fortsetzen</Button>}
          {p.status!=='finished'&&<Button variant="outlined" disabled={busy} onClick={()=>{if(window.confirm('Projekt beenden und Abschlussvideo erstellen?'))action({action:'stop',project:p.id});}}>Beenden</Button>}
          <Button variant="outlined" disabled={busy||p.exportPending||!p.frames} onClick={()=>action({action:'export',project:p.id})}>{p.exportPending?(p.progress ? p.progress.phase+' '+p.progress.percent+' %' : 'MP4 wartet auf Verarbeitung …'):'MP4 aktualisieren'}</Button>
          <Button variant="outlined" disabled={busy||!p.exported} onClick={()=>download(p)}>MP4 herunterladen ({p.exported} Bilder)</Button>
          {p.status==='finished'&&<Button variant="outlined" disabled={busy} color="secondary" onClick={()=>{if(window.confirm('Dieses Projekt und alle lokalen Zeitrafferdateien löschen? Eine NAS-Kopie bleibt erhalten.'))action({action:'delete',project:p.id});}}>Lokal löschen</Button>}
          <Button variant="outlined" disabled={busy} onClick={()=>action({action:'publish',project:p.id,public:!p.settings.public})}>{p.settings.public?'Veröffentlichung aufheben':'Veröffentlichen'}</Button>
        </Box>
      </Box>)}
    </>}
  </Stack>;
}
