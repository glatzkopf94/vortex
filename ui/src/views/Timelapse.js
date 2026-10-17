import React from 'react';
import LinkIcon from '@mui/icons-material/Link';
import NotifyContext, {useStatusNotifications} from '../contexts/Notify';
import TimelapsePreview from './TimelapsePreview';
import { Box, Button, Checkbox, LinearProgress, FormControlLabel, MenuItem, Stack, TextField, Typography } from '@mui/material';

const outline = color => ({'&&&&':{borderColor:color,color:'#fff'},'&&&&:hover':{borderColor:color},'&&&&.Mui-disabled':{borderColor:color,opacity:0.55}});
const statusText = {recording:'Aufnahme läuft', paused:'Pausiert', finished:'Beendet'};
export default function Timelapse({restreamer,onOpenFTP}) {
  const notify=React.useContext(NotifyContext);
  const [data,setData]=React.useState(null);
  const [channel,setChannel]=React.useState(()=>{try{return sessionStorage.getItem('nkl-timelapse-channel')||'';}catch{return '';}});
  const [form,setForm]=React.useState(null);
  const [error,setError]=React.useState('');
  const [busy,setBusy]=React.useState(false);
  const [operation,setOperation]=React.useState(null);
  const [qualityForm,setQualityForm]=React.useState(null);
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
  React.useEffect(()=>{let active=true,id;const poll=async()=>{await refresh();if(active)id=setTimeout(poll,500);};poll();return()=>{active=false;clearTimeout(id);};},[refresh]);
  React.useEffect(()=>{
    if(!data||!channel)return;
    const saved=data.channels.find(c=>c.id===channel&&c.active);
    if(!saved){setChannel('');setForm(null);try{sessionStorage.removeItem('nkl-timelapse-channel');}catch{}}
    else if(!form)setForm({...saved.settings});
  },[data,channel,form]);
  const choose=(id)=>{try{sessionStorage.setItem('nkl-timelapse-channel',id);}catch{}setChannel(id);setForm({...data.channels.find(c=>c.id===id).settings});setNotice('');};
  const change=(key,value)=>{setForm(previous=>({...previous,[key]:value,...(key==='mode'&&value==='season'?{interval:Math.max(30,previous.interval)}:{})}));setNotice('Ungespeicherte Änderungen – bitte Einstellungen speichern.');};
  async function action(body) {
    setBusy(true);setError('');setOperation({project:body.project,label:body.action==='export'||body.action==='stop'?'MP4-Verarbeitung wird angefordert …':'Änderung wird gespeichert …'});
    try {const result=await call(body);if(body.action==='configure')setForm({...result});await refresh();success(body.action==='delete_finished'?`${result.deleted} abgeschlossene ${body.mode==='daily'?'Tages':'Saison'}zeitraffer lokal gelöscht.`:({configure_qualities:'Vorschauqualitäten gespeichert. Neue Transcoding-Aufträge verwenden diese Bitraten.',configure_retention:'Automatische Löschung gespeichert.',set_channel_active:'Kanalauswahl gespeichert.',configure_global:'Globale Overlay-Einstellung gespeichert. Gilt für die nächsten Einzelbilder aller Kanäle.',configure_transfer:'Externe Ablage gespeichert.',transfer_now:'Übertragung beauftragt.',configure:'Einstellungen gespeichert. Änderungen an Auflösung/FPS gelten für das nächste Projekt.',start:form?.mode==='season'?'Saisonaufnahme gestartet.':'Aufnahmeplan gestartet. Die Aufnahme erfolgt innerhalb des gespeicherten Zeitfensters.',pause:'Aufnahme pausiert.',resume:'Aufnahme fortgesetzt.',stop:'Aufnahme beendet; Abschlussvideo wird erstellt.',export:'MP4-Aktualisierung beauftragt.',publish:'Veröffentlichung geändert.',delete:'Lokales Projekt gelöscht.'})[body.action] || 'Änderung gespeichert.');return result;}catch(e){setError(String(e.message));}
    finally{setBusy(false);setOperation(null);}
  }
  async function download(project) {
    setBusy(true);setError('');setOperation({project:project.id,label:'MP4 wird heruntergeladen …'});
    try {
      const [val,err]=await restreamer._call(restreamer.api._call,'GET','/v3/timelapse/project/'+project.id+'/export.mp4',{expect:'blob',onprogress:(known,fraction,bytes)=>{
        const percent=known?Math.min(100,Math.floor(fraction*100)):null;
        const received=known?fraction*bytes:bytes;
        setOperation({project:project.id,percent,label:known?`MP4 herunterladen: ${percent} % · ${(received/1048576).toFixed(1)} / ${(bytes/1048576).toFixed(1)} MB`:`MP4 herunterladen: ${(received/1048576).toFixed(1)} MB empfangen`});
      }});
      if(err)throw new Error(err.message);
      const url=URL.createObjectURL(val);const a=document.createElement('a');a.href=url;a.download=project.filename;a.click();success('MP4-Download an den Browser übergeben.');setTimeout(()=>URL.revokeObjectURL(url),60000);
    }catch(e){setError(String(e.message));}finally{setBusy(false);setOperation(null);}
  }
  const number=(key,label,props={})=><TextField key={key} label={label} type="number" value={form[key]} onChange={e=>change(key,Number(e.target.value))} inputProps={props} fullWidth/>;
  const select=(key,label,options)=><TextField key={key} select label={label} value={form[key]} onChange={e=>change(key,e.target.value)} fullWidth>{options.map(([v,t])=><MenuItem key={v} value={v}>{t}</MenuItem>)}</TextField>;
  return <Stack spacing={2} sx={{p:2,minWidth:0,maxWidth:'100%',overflowWrap:'anywhere','& .MuiButton-outlined:not(.MuiButton-outlinedSecondary)':{color:'#fff',borderColor:'#aab4be',backgroundColor:'#303b45','&:hover':{backgroundColor:'#455461'},'&.Mui-disabled':{color:'#b9c0c7',borderColor:'#66717c',backgroundColor:'#30363c'}}}}>
    <Typography variant="h2">Zeitraffer · lokale Vorschau</Typography>
    <Typography>Eigene Aufnahme und Verarbeitung, unabhängig vom DVR. Eine Vorschau entsteht ab zwei Bildern und wird bei neuen Bildern etwa alle fünf Minuten ergänzt. Fehlzeiten werden übersprungen, nicht mit alten Bildern aufgefüllt.</Typography>
    {notice.startsWith('Ungespeicherte')&&<Typography>{notice}</Typography>}
    {data&&<>
      <TextField select label="Zeitraffer für Kanäle aktivieren" value={data.channels.filter(c=>c.active).map(c=>c.id)} disabled={busy||!data.channels.length} fullWidth
        SelectProps={{multiple:true,displayEmpty:true,renderValue:ids=>ids.length===0?'Keine Kanäle aktiviert':`${ids.length} ${ids.length===1?'Kanal aktiviert':'Kanäle aktiviert'}`,MenuProps:{PaperProps:{sx:{maxHeight:360}}}}}
        InputLabelProps={{shrink:true}}
        onChange={e=>{
          const ids=typeof e.target.value==='string'?e.target.value.split(','):e.target.value;
          const changed=data.channels.find(c=>ids.includes(c.id)!==!!c.active);
          if(changed)action({action:'set_channel_active',channel:changed.id,active:ids.includes(changed.id)});
        }}>
        {data.channels.map(c=><MenuItem key={c.id} value={c.id}><Checkbox checked={!!c.active} tabIndex={-1} disableRipple sx={{pointerEvents:'none'}}/>{c.name}</MenuItem>)}
      </TextField>
      <Typography variant="body2">Haken werden sofort gespeichert. Nur aktivierte Kanäle stehen unten zur Auswahl und zeigen den Zeitraffer-Button im Player.</Typography>
      <FormControlLabel control={<Checkbox disabled={busy} checked={!!data.globalSettings?.includeBurnedOverlays} onChange={e=>action({action:'configure_global',includeBurnedOverlays:e.target.checked})}/>} label="Eingebrannte Vortex-Overlays im Zeitraffer übernehmen (alle Kanäle)"/>
      <Typography variant="body2">Ausgeschaltet: Bei Kanälen mit eingebrannten Vortex-Overlays wird pro Einzelbild kurz die ursprüngliche RTSP-/HTTP-Quelle abgerufen. Kameraeigene Einblendungen bleiben erhalten. Eingeschaltet: Bild aus dem laufenden Stream inklusive eingebrannter Overlays. Browser-Player-Overlays werden nicht übernommen. Gilt für neue Bilder, auch in laufenden Aufnahmen.</Typography>
      <Stack spacing={2} sx={{minWidth:0}}>
        <Typography variant="h3">Transcoding</Typography>
        <Typography variant="body2">1080p wird im Player bevorzugt, sobald vollständig verfügbar. Zusätzliche Fassungen benötigen CPU und Speicher. Die Originalqualität und MP4-Downloads bleiben erhalten. Änderungen gelten ab dem nächsten Transcoding-Auftrag; bestehende Abschnitte behalten ihre Bitrate. Ausschalten beendet die Warteschlange nach dem laufenden Abschnitt und blendet Zusatzqualitäten aus.</Typography>
        <FormControlLabel label="1080p und 720p zusätzlich erzeugen" control={<Checkbox checked={(qualityForm||data.globalSettings.qualities)?.enabled??true} onChange={e=>setQualityForm({...data.globalSettings.qualities,...qualityForm,enabled:e.target.checked})}/>}/>
        <Box sx={{display:'grid',gridTemplateColumns:'repeat(2,minmax(0,1fr))',gap:2}}>
        {[['bitrate1080','1920×1080'],['bitrate720','1280×720']].map(([key,label])=><TextField key={key} type="number" label={label+' · kbit/s'} value={(qualityForm||data.globalSettings.qualities)?.[key]??(key==='bitrate1080'?3072:2048)} onChange={e=>setQualityForm({...data.globalSettings.qualities,...qualityForm,[key]:Number(e.target.value)})} inputProps={{min:256,max:20000}} fullWidth sx={{minWidth:0}}/>)}
        </Box>
        <Button variant="outlined" sx={outline('#4caf50')} disabled={busy||!qualityForm} onClick={async()=>{if(await action({action:'configure_qualities',settings:qualityForm}))setQualityForm(null);}}>Einstellungen speichern</Button>
      </Stack>
      <Typography variant="h3">Kanal-Einstellungen</Typography>
      <TextField select label="Kanal" value={data.channels.some(c=>c.id===channel&&c.active)?channel:''} disabled={!data.channels.some(c=>c.active)} onChange={e=>choose(e.target.value)} fullWidth>{data.channels.filter(c=>c.active).map(c=><MenuItem key={c.id} value={c.id}>{c.name}</MenuItem>)}</TextField>
      {form&&data.channels.some(c=>c.id===channel&&c.active)&&<>
        {select('mode','Betriebsart',[['daily','Tageszeitraffer'],['season','Saison / manuell']])}
        <Box sx={{display:'grid',gridTemplateColumns:'repeat(auto-fit,minmax(min(100%,220px),1fr))',gap:2}}>
          {form.mode==='daily'?number('interval','Bildintervall in Sekunden',{min:15,max:86400,step:1}):<TextField label="Bildintervall in Minuten" type="text" inputProps={{inputMode:'decimal'}} defaultValue={form.interval/60} key={'minutes-'+channel} onBlur={e=>{const minutes=Number(e.target.value.replace(',','.'));change('interval',Math.round(minutes*60));}} helperText="0,5 bis 1440 Minuten (ein Bild pro Tag)." fullWidth/>}
          {number('fps','Videobilder pro Sekunde',{min:1,max:60})}
          {select('width','Bildbreite',[[0,'Originalauflösung der Streamquelle'],[640,'640 Pixel'],[1280,'1280 Pixel'],[1920,'1920 Pixel'],[3840,'3840 Pixel']])}
          <TextField label="Zeitzone" value={form.timezone} onChange={e=>change('timezone',e.target.value)} helperText="Zum Beispiel Europe/Berlin"/>
        </Box>
        <Typography variant="body2">Beschleunigung: {form.interval * form.fps}×. 24 Stunden ohne Lücken ergeben etwa {(86400 / form.interval / form.fps).toFixed(1)} Sekunden Video. FPS bestimmen die Abspielgeschwindigkeit, das Intervall die Aufnahmehäufigkeit.</Typography>
        <Typography variant="body2">Seitenverhältnis bleibt erhalten. Neue Bilder werden mit konstanter Qualität (CRF 18) verarbeitet; die Bitrate richtet sich nach dem Bildinhalt.</Typography>
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
        <Box sx={{display:'flex',flexDirection:'column',gap:1,mt:1}}>
          <Button variant="outlined" sx={outline('#4caf50')} disabled={busy} onClick={()=>action({action:'configure',channel,settings:form})}>Einstellungen speichern</Button>
          <Button variant="outlined" sx={outline('#4caf50')} disabled={busy||!form.enabled||JSON.stringify(form)!==JSON.stringify(data.channels.find(c=>c.id===channel)?.settings)||(form.mode==='daily'?!!data.channels.find(c=>c.id===channel)?.armed:data.projects.some(p=>p.channel===channel&&!p.day&&['recording','paused'].includes(p.status)))} onClick={()=>action({action:'start',channel})}>Aufnahme starten</Button>
          <Typography variant="caption">Einstellungen zuerst speichern, dann Aufnahme starten. Tagesaufnahmen wiederholen sich danach automatisch im eingestellten Zeitfenster.</Typography>
        </Box>
      </>}
      {data.projects.filter(p=>!channel||p.channel===channel).map(p=><Box key={p.id} sx={{p:2,border:'1px solid',borderColor:'divider',borderRadius:1}}>
        <Typography variant="h3">{p.label.replace(/^(\d{4})-(\d{2})-(\d{2})$/, '$3.$2.$1')} · {statusText[p.status]}</Typography>
        <TimelapsePreview restreamer={restreamer} project={p}/>
        <Typography>{data.channels.find(c=>c.id===p.channel)?.name} · {p.frames} Bilder · {p.missed} verpasste Aufnahmezeitpunkte · Vorschau: {p.previewFrames} Bilder</Typography>
        {p.ends&&<Typography variant="body2">Aufnahmefenster: {new Date(p.started*1000).toLocaleString('de-DE',{timeZone:p.settings.timezone,day:'2-digit',month:'2-digit',year:'numeric',hour:'2-digit',minute:'2-digit'})} bis {new Date(p.ends*1000).toLocaleString('de-DE',{timeZone:p.settings.timezone,day:'2-digit',month:'2-digit',year:'numeric',hour:'2-digit',minute:'2-digit'})} ({p.settings.timezone})</Typography>}
        <Typography variant="body2">Intervall: {p.settings.interval} s · Letzte Aufnahme: {p.last?new Date(p.last*1000).toLocaleString('de-DE',{day:'2-digit',month:'2-digit',year:'numeric',hour:'2-digit',minute:'2-digit'}):'noch keine'} · {p.settings.public?'Öffentlich':'Nur Admin'}</Typography>
        {(operation?.project===p.id||p.exportPending||p.progress)&&<Box role="status" aria-live="polite" sx={{my:1}}>
          <Typography variant="body2">{operation?.project===p.id?operation.label:p.progress?`${p.progress.phase}: ${p.progress.percent} %`:'MP4 wartet auf Verarbeitung …'}</Typography>
          <LinearProgress aria-label="Zeitraffer-Fortschritt" variant={(operation?.project===p.id?operation.percent==null:!p.progress)?'indeterminate':'determinate'} value={operation?.project===p.id?(operation.percent??0):(p.progress?.percent||0)} sx={{mt:1}}/>
        </Box>}
        {p.nas&&<Typography>NAS: {p.nas}</Typography>}
        <Box sx={{display:'flex',flexDirection:'column',gap:1,mt:1}}>
          {p.status==='recording'&&<Button variant="outlined" disabled={busy} sx={outline('#fdd835')} onClick={()=>action({action:'pause',project:p.id})}>Pausieren</Button>}
          {p.status==='paused'&&<Button variant="outlined" disabled={busy} onClick={()=>action({action:'resume',project:p.id})}>Fortsetzen</Button>}
          {p.status!=='finished'&&<Button variant="outlined" disabled={busy} sx={outline('#ef5350')} onClick={()=>{if(window.confirm('Projekt beenden und Abschlussvideo erstellen?'))action({action:'stop',project:p.id});}}>Beenden</Button>}
          <Button variant="outlined" disabled={busy||p.exportPending||!p.frames} sx={outline('#fdd835')} onClick={()=>action({action:'export',project:p.id})}>{p.exportPending?(p.progress ? p.progress.phase+' '+p.progress.percent+' %' : 'MP4 wartet auf Verarbeitung …'):'MP4 aktualisieren'}</Button>
          <Button variant="outlined" disabled={busy||!p.exported} sx={outline('#66bb6a')} onClick={()=>download(p)}>MP4 herunterladen ({p.exported} Bilder)</Button>
          {p.status==='finished'&&<Button variant="outlined" disabled={busy} sx={outline('#f44336')} onClick={()=>{if(window.confirm('Dieses Projekt und alle lokalen Zeitrafferdateien löschen? Eine NAS-Kopie bleibt erhalten.'))action({action:'delete',project:p.id});}}>Lokal löschen</Button>}
          <Button variant="outlined" disabled={busy} sx={p.settings.public?outline('#fdd835'):undefined} onClick={()=>action({action:'publish',project:p.id,public:!p.settings.public})}>{p.settings.public?'Veröffentlichung stoppen':'Veröffentlichen'}</Button>
        </Box>
      </Box>)}
      <Box component="section" aria-labelledby="timelapse-retention-heading" sx={{p:2,border:'1px solid',borderColor:'divider',borderRadius:1}}>
        <Stack spacing={2}>
          <Typography variant="h3" id="timelapse-retention-heading">Alte Aufnahmen löschen</Typography>
      <Typography>Speicherplatz · Zeitraffer: {(data.storageBytes/1073741824).toFixed(2)} GB / {(data.quotaBytes/1073741824).toFixed(1)} GB. Auf dem Datenträger frei: {(data.diskFreeBytes/1073741824).toFixed(1)} GB von {(data.diskTotalBytes/1073741824).toFixed(1)} GB. Freie Reserve: {(data.reserveBytes/1073741824).toFixed(1)} GB.</Typography>
      <TextField select label="Automatisch löschen nach" value={data.globalSettings?.retentionDays??0} disabled={busy} onChange={e=>action({action:'configure_retention',days:Number(e.target.value)})} fullWidth>
        {[[1,'1 Tag'],[3,'3 Tagen'],[7,'7 Tagen'],[0,'Nie']].map(([value,label])=><MenuItem key={value} value={value}>{label}</MenuItem>)}
      </TextField>
      <Typography variant="body2">Die Frist zählt ab Aufnahmeende. „Nie“: keine Altersgrenze; bei erreichtem Zeitrafferbudget oder freier Speicherreserve werden die ältesten abgeschlossenen Aufnahmen zuerst gelöscht. Laufende und pausierte Projekte sowie laufende Verarbeitung/Übertragungen bleiben geschützt. Gibt es keine löschbaren Aufnahmen, pausiert die Aufnahme bei Speichermangel.</Typography>
      <Typography variant="body2">Eine Sicherung per FTP wird empfohlen. Die automatische Löschung entfernt lokale Zeitraffer, unabhängig davon, ob bereits eine Sicherung vorhanden ist. Externe Sicherungen und DVR-Aufnahmen bleiben erhalten.</Typography>
      <Box><Button variant="outlined" sx={outline('#4caf50')} startIcon={<LinkIcon/>} onClick={onOpenFTP}>Sicherung per FTP</Button></Box>

      <Typography variant="body2">Sammellöschung für alle Kanäle: Nur abgeschlossene Aufnahmen werden lokal gelöscht. Laufende/pausierte Projekte und NAS-Kopien bleiben erhalten.</Typography>
      <Box sx={{display:'flex',flexWrap:'wrap',gap:1}}>
        {['daily','season'].map(mode=>{
          const count=data.projects.filter(p=>p.status==='finished'&&p.settings.mode===mode).length;
          const label=mode==='daily'?'Tageszeitraffer':'Saisonzeitraffer';
          return <Box key={mode}><Typography variant="subtitle2">{label}</Typography><Button variant="outlined" sx={outline('#f44336')} disabled={busy||!count} onClick={()=>{if(window.confirm(`${count} abgeschlossene ${label} über ALLE Kanäle endgültig lokal löschen? Die andere Betriebsart, laufende/pausierte Projekte und NAS-Kopien bleiben erhalten.`))action({action:'delete_finished',mode});}}>Fertige Zeitraffer löschen ({count})</Button></Box>;
        })}
      </Box>
        </Stack>
      </Box>
    </>}
  </Stack>;
}
