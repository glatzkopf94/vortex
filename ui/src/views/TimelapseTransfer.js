// Modified 2026-10-11: separate manual/automatic FTP selection and cancellation.
import React from 'react';
import {useStatusNotifications} from '../contexts/Notify';
import {Alert,Box,Button,Checkbox,Dialog,DialogTitle,DialogContent,DialogActions,FormControlLabel,MenuItem,LinearProgress,TextField,Typography} from '@mui/material';
const grid={display:'grid',gridTemplateColumns:{xs:'1fr',sm:'repeat(2,minmax(0,1fr))'},gap:2};
const section={display:'flex',flexDirection:'column',gap:3,minWidth:0};
const menu={PaperProps:{style:{maxHeight:480}}};
export default function TimelapseTransfer({data,busy,action}) {
  const [form,setForm]=React.useState(()=>({...data.transfer,password:''}));
  const [testSettings,setTestSettings]=React.useState(null);
  const [dismissed,setDismissed]=React.useState(null);
  const [verified,setVerified]=React.useState(false);
  const set=(key,value)=>{
    setTestSettings(null);setVerified(false);
    setForm(old=>({...old,[key]:value,...(['host','port','protocol'].includes(key)?{tlsTrust:null}:{})}));
  };
  const [channel,setChannel]=React.useState('');
  const [files,setFiles]=React.useState(['*']);
  const [onlyFinished,setOnlyFinished]=React.useState(false);
  const [validation,setValidation]=React.useState('');
  const status=data.transferStatus||{};const test=data.transferTest;
  useStatusNotifications({
    'ftp:validation':validation?{severity:'error',message:validation}:null,
    'ftp:test':['success','error'].includes(test?.state)?{severity:test.state,message:test.message}:null,
    'ftp:result':['success','error'].includes(status.state)?{severity:status.state,message:status.state==='success'?`Übertragung abgeschlossen: ${status.uploaded||0} Dateien.`:status.message,at:status.at}:null,
  }, ['ftp:test','ftp:result']);
  const active=['preparing','running','cancelling'].includes(status.state);
  const projects=(data.projects||[]).filter(p=>(!channel||p.channel===channel)&&(!onlyFinished||p.status==='finished'));
  const submit=async(kind)=>{
    const port=String(form.port).trim(), interval=String(form.intervalMinutes).trim();
    if(!/^\d+$/.test(port)||Number(port)<1||Number(port)>65535){setValidation('Port muss zwischen 1 und 65535 liegen.');return;}
    if(!/^\d+$/.test(interval)||Number(interval)<1||Number(interval)>1440){setValidation('Intervall muss zwischen 1 und 1440 Minuten liegen.');return;}
    setValidation('');
    const settings={...form,port:Number(port),intervalMinutes:Number(interval)};
    if(kind==='test_transfer'){
      setDismissed(test?.certificate?.id);setVerified(false);setTestSettings(settings);
    }
    const result=await action({action:kind,settings});
    if(result&&kind==='configure_transfer')set('password','');
  };
  const certificate=test?.state==='certificate_required'?test.certificate:null;
  const showCertificate=!!(certificate&&testSettings&&certificate.id!==dismissed&&
    certificate.host===form.host&&certificate.port===Number(form.port)&&form.protocol==='ftps');
  const confirmCertificate=async()=>{
    if(!verified||!showCertificate)return;
    const settings={...testSettings,tlsTrust:{host:certificate.host,port:certificate.port,sha256:certificate.sha256}};
    const result=await action({action:'configure_transfer',settings});
    if(!result)return;
    setForm({...settings,password:''});setDismissed(certificate.id);setVerified(false);
    setTestSettings({...settings,password:''});
    await action({action:'test_transfer',settings:{...settings,password:''}});
  };
  const feedback=(origin)=><>
    {status.origin===origin&&['preparing','running','cancelling'].includes(status.state)&&<Box sx={section}>
      {status.totalBytes>0&&<Box><Typography sx={{overflowWrap:'anywhere',mb:1}}>{status.file}</Typography>
        <LinearProgress variant="determinate" value={Math.min(100,100*(status.sentBytes||0)/status.totalBytes)}/>
        <Typography sx={{mt:1}}>{Math.floor(100*(status.sentBytes||0)/status.totalBytes)} % gesendet · {((status.sentBytes||0)/1048576).toFixed(1)} / {(status.totalBytes/1048576).toFixed(1)} MiB</Typography>
        {status.sentBytes>=status.totalBytes&&<Typography>Abschlussbestätigung und Prüfung auf dem Zielgerät können noch ausstehen.</Typography>}
        {status.idleSeconds>0&&<Typography>Warte auf Datenfortschritt seit {status.idleSeconds} Sekunden.</Typography>}
      </Box>}
      <Typography role="status">{{preparing:'MP4-Dateien werden vorbereitet …',running:status.phase||'Übertragung läuft …',cancelling:'Upload wird abgebrochen …',success:`Übertragung abgeschlossen: ${status.uploaded||0} Dateien.`,error:status.message}[status.state]||''}</Typography>
    </Box>}
  </>;
  const cancel=(origin)=><Button variant="outlined" color="secondary" disabled={busy||status.state==='cancelling'||(active&&status.origin!==origin)||(!active&&(status.origin!==origin||status.state==='idle'))} onClick={()=>action({action:'cancel_transfer',origin})}>Upload abbrechen</Button>;
  return <Box sx={{...section,border:'1px solid',borderColor:'divider',borderRadius:1,p:2,
    '& .MuiFormHelperText-root:not(.Mui-error)':{color:'#ffe082'},
    '& .MuiAlert-message, & .MuiAlert-message .MuiTypography-root':{color:'inherit'}}}>
    <Typography variant="h3">Externe Ablage · NAS / FTP-Cloud</Typography>
    <Typography>FTP-Zugang für manuelle und automatische Uploads. Lokale Aufnahmen bleiben erhalten.</Typography>
    <Box sx={grid}>
      <TextField select label="Verbindung" value={form.protocol} onChange={e=>set('protocol',e.target.value)}><MenuItem value="ftps">FTPS (explizites TLS)</MenuItem><MenuItem value="ftp">FTP (unverschlüsselt)</MenuItem></TextField>
      <TextField label="Servername oder IP" value={form.host} onChange={e=>set('host',e.target.value)} helperText="Ohne ftp:// oder Ordnerpfad"/>
      <TextField label="Port" type="text" value={form.port} onChange={e=>set('port',e.target.value)} inputProps={{inputMode:'numeric',maxLength:5}} helperText="FTP / explizites FTPS: normalerweise 21. Port 22 gehört zu SFTP (hier nicht unterstützt). Abweichende Ports bleiben möglich."/>
      <TextField label="Zielordner" value={form.directory} onChange={e=>set('directory',e.target.value)} helperText="Vorhandener Ordner. Mit / testen, um die sichtbaren Einträge zu prüfen."/>
      <TextField label="Benutzername" value={form.username} onChange={e=>set('username',e.target.value)} autoComplete="off"/>
      <TextField label="Passwort" type="password" placeholder={data.transfer.passwordConfigured?'••••••••••••':''} InputLabelProps={{shrink:true}} value={form.password} onChange={e=>set('password',e.target.value)} autoComplete="new-password" helperText={data.transfer.passwordConfigured?'Passwort hinterlegt. Nur zum Ändern neu eingeben.':'Zugangspasswort eingeben'}/>
    </Box>
    {form.protocol==='ftps'&&form.tlsTrust&&<Alert severity="info">
      Zertifikatsfreigabe für {form.tlsTrust.host}:{form.tlsTrust.port}<br/>
      <Box component="span" sx={{overflowWrap:'anywhere'}}>SHA-256: {form.tlsTrust.sha256.match(/.{2}/g)?.join(':')}</Box><br/>
      <Button disabled={busy||active} onClick={()=>set('tlsTrust',null)}>Freigabe entfernen (anschließend speichern)</Button>
    </Alert>}
    <Dialog open={showCertificate} onClose={()=>{if(!busy)setDismissed(certificate?.id);}} maxWidth="sm" fullWidth aria-labelledby="ftps-certificate-title"
      sx={{position:'fixed',inset:0,width:'100%',height:'100%',maxWidth:'none',maxHeight:'none',p:0,
        overflow:'hidden',backgroundColor:'transparent',display:'block',
        '& .MuiDialog-container':{width:'100%',alignItems:'center',justifyContent:'center'}}}
      PaperProps={{sx:{m:{xs:1.5,sm:3},p:0,width:{xs:'calc(100% - 24px)',sm:'calc(100% - 48px)'},
        maxHeight:'calc(100dvh - 24px)',backgroundColor:'background.modal',backgroundImage:'none',
        display:'flex',flexDirection:'column',overflow:'hidden',borderRadius:2}}}>
      <DialogTitle id="ftps-certificate-title" sx={{textAlign:'center',fontFamily:'\"Dosis\", \"Roboto\", sans-serif',fontSize:{xs:'1.6rem',sm:'2rem'},lineHeight:1.2,px:2,py:2,flexShrink:0}}>{certificate?.changed?'Serverzertifikat geändert':'Serverzertifikat bestätigen'}</DialogTitle>
      <DialogContent sx={{display:'flex',flexDirection:'column',gap:2,px:{xs:2,sm:3},overflowY:'auto',minHeight:0,overflowWrap:'anywhere'}}>
        <Alert severity="warning">{test?.message} Bisher wurden bei dieser Zertifikatsabfrage keine Zugangsdaten gesendet.</Alert>
        <Typography>Server: {certificate?.host}:{certificate?.port}</Typography>
        <Typography sx={{overflowWrap:'anywhere'}}>SHA-256: {certificate?.sha256?.match(/.{2}/g)?.join(':')}</Typography>
        <Typography>Vergleiche den Fingerabdruck mit dem Serveradministrator oder einer bereits geprüften Verbindung. Die Freigabe ersetzt für diesen Server und Port die normale Zertifikatsketten-, Namens- und Gültigkeitsprüfung durch den exakten Fingerabdruck. Ein anderes Zertifikat wird abgelehnt.</Typography>
        <FormControlLabel control={<Checkbox checked={verified} disabled={busy} onChange={e=>setVerified(e.target.checked)}/>} label="Fingerabdruck geprüft – diesem Zertifikat vertrauen"/>
        <Typography variant="body2">Die Bestätigung speichert auch die aktuellen FTP-Eingaben und startet den Verbindungstest mit einer kleinen Testdatei erneut.</Typography>
      </DialogContent>
      <DialogActions disableSpacing sx={{display:'grid',gridTemplateColumns:{xs:'1fr',sm:'repeat(2,minmax(0,1fr))'},gap:1.5,p:2,flexShrink:0,
        '& .MuiButton-root':{width:'100%',minHeight:48,m:0,px:1,textTransform:'none',fontWeight:700}}}>
        <Button variant="contained" sx={{backgroundColor:'#2e7d32',color:'#fff','&:hover':{backgroundColor:'#1b5e20'},'&.Mui-disabled':{backgroundColor:'#2e7d32',color:'#fff',opacity:0.45}}}
          disabled={busy||active||!verified} onClick={confirmCertificate}>Bestätigen &amp; Speichern</Button>
        <Button variant="contained" sx={{backgroundColor:'#c62828',color:'#fff','&:hover':{backgroundColor:'#b71c1c'}}}
          disabled={busy} onClick={()=>setDismissed(certificate?.id)}>Abbrechen</Button>
      </DialogActions>
    </Dialog>
    {form.protocol==='ftp'&&<Alert severity="info">FTP überträgt Zugangsdaten unverschlüsselt. Für Internetverbindungen FTPS oder ein VPN verwenden.</Alert>}
    <Box sx={grid}>
      <Button variant="outlined" color="primary" disabled={busy||active} onClick={()=>submit('configure_transfer')}>Eingabe speichern</Button>
      <Button variant="outlined" disabled={busy||test?.state==='running'} onClick={()=>submit('test_transfer')}>FTP-Verbindung testen</Button>
    </Box>
    <Typography variant="body2">Der Verbindungstest prüft aktuelle Eingaben, ohne sie zu speichern. Er schreibt und löscht eine kleine eigene Testdatei.</Typography>
    <Box component="section" sx={{...section,borderTop:'1px solid',borderColor:'divider',pt:3}}>
      <Typography variant="h3">Manueller Upload</Typography>
      <TextField select label="Kanal" value={channel} InputLabelProps={{shrink:true}} SelectProps={{displayEmpty:true,MenuProps:menu}} onChange={e=>{setChannel(e.target.value);setFiles(['*']);}}>
        <MenuItem value="">Alle Kanäle</MenuItem>{(data.channels||[]).map(c=><MenuItem key={c.id} value={c.id}>{c.name}</MenuItem>)}
      </TextField>
      <FormControlLabel control={<Checkbox checked={onlyFinished} onChange={e=>{setOnlyFinished(e.target.checked);setFiles(['*']);}}/>} label="Nur abgeschlossene Aufnahmen"/>
      <TextField select label="Dateien" value={files} SelectProps={{multiple:true,MenuProps:menu,displayEmpty:true,renderValue:v=>v.includes('*')?'Alle Dateien':`${v.length} Dateien ausgewählt`}} InputLabelProps={{shrink:true}}
        onChange={e=>{const v=e.target.value;setFiles(v.includes('*')&&!files.includes('*')?['*']:v.filter(x=>x!=='*'));}} helperText="Mehrfachauswahl möglich. Laufende Aufnahmen werden vor dem Upload aktualisiert.">
        <MenuItem value="*"><Checkbox checked={files.includes('*')}/>Alle Dateien</MenuItem>
        {projects.map(p=><MenuItem key={p.id} value={p.id} sx={{whiteSpace:'normal'}}><Checkbox checked={files.includes('*')||files.includes(p.id)}/>{p.filename||p.label}{p.status==='finished'?'':' (laufend/pausiert)'}</MenuItem>)}
      </TextField>
      <Box sx={grid}>
        <Button variant="outlined" color="primary" disabled={busy||active||!projects.length||!files.length||!data.transfer.host} onClick={()=>action({action:'transfer_now',channel:channel||null,projects:files.includes('*')?null:files,onlyFinished})}>Jetzt übertragen</Button>
        {cancel('manual')}
      </Box>
      {feedback('manual')}
    </Box>
    <Box component="section" sx={{...section,borderTop:'1px solid',borderColor:'divider',pt:3}}>
      <Typography variant="h3">Automatischer Upload</Typography>
      <FormControlLabel control={<Checkbox checked={form.enabled} onChange={e=>set('enabled',e.target.checked)}/>} label="Regelmäßige FTP-Übertragung aktiv"/>
      <TextField select label="Kanäle" value={form.autoChannels?.length?form.autoChannels:['*']} SelectProps={{multiple:true,MenuProps:menu,renderValue:v=>v.includes('*')?'Alle Kanäle':v.map(id=>(data.channels||[]).find(c=>c.id===id)?.name||id).join(', ')}}
        onChange={e=>{const v=e.target.value;set('autoChannels',v.includes('*')&&form.autoChannels?.length?[]:v.filter(x=>x!=='*'));}}>
        <MenuItem value="*"><Checkbox checked={!form.autoChannels?.length}/>Alle Kanäle</MenuItem>
        {(data.channels||[]).map(c=><MenuItem key={c.id} value={c.id}><Checkbox checked={!form.autoChannels?.length||form.autoChannels.includes(c.id)}/>{c.name}</MenuItem>)}
      </TextField>
      <Box sx={grid}>
        <TextField label="Intervall in Minuten" value={form.intervalMinutes} onChange={e=>set('intervalMinutes',e.target.value)} inputProps={{inputMode:'numeric',maxLength:4}}/>
        <TextField select label="Aufnahmen übertragen" value={form.mode} onChange={e=>set('mode',e.target.value)}><MenuItem value="both">Tages- und Saisonzeitraffer</MenuItem><MenuItem value="daily">Nur Tageszeitraffer</MenuItem><MenuItem value="season">Nur Saisonzeitraffer</MenuItem></TextField>
      </Box>
      <FormControlLabel control={<Checkbox checked={!!form.onlyFinished} onChange={e=>set('onlyFinished',e.target.checked)}/>} label="Nur abgeschlossene Aufnahmen"/>
      <Typography variant="body2">Nur geänderte Dateien der ausgewählten Kanäle werden übertragen. Nach dem Speichern beginnt das Intervall neu. Abbrechen beendet den aktuellen Auftrag; die Automatik bleibt für das nächste Intervall aktiv.</Typography>
      <Box sx={grid}><Button variant="outlined" color="primary" disabled={busy||active} onClick={()=>submit('configure_transfer')}>Automatik speichern</Button>{cancel('automatic')}</Box>
      {feedback('automatic')}
    </Box>
  </Box>;
}
