import React from 'react';
import {Alert,Button,Dialog,DialogTitle,DialogContent,DialogActions,Grid,MenuItem,TextField,Typography} from '@mui/material';
import PlayerOverlay from './Publication/PlayerOverlay';

export default function TimelapseOverlay({restreamer,channels,initialChannel,onClose,onSaved}) {
  const [channel,setChannel]=React.useState(channels.some(c=>c.id===initialChannel)?initialChannel:channels[0]?.id||'');
  const [settings,setSettings]=React.useState(null);
  const [baseline,setBaseline]=React.useState('');
  const [busy,setBusy]=React.useState(false);
  const [error,setError]=React.useState('');
  const dirty=settings&&JSON.stringify(settings)!==baseline;
  React.useEffect(()=>{
    let active=true;setSettings(null);setError('');
    if(channel)restreamer.GetIngest(channel,['metadata']).then(proc=>{
      if(!active)return;
      if(!proc)throw new Error('Kanal nicht mehr verfügbar.');
      const overlay=restreamer.InitPlayerSettings(proc.metadata.player).overlay;
      setSettings(overlay);setBaseline(JSON.stringify(overlay));
    }).catch(e=>{if(active)setError(e.message);});
    return()=>{active=false;};
  },[channel,restreamer]);
  async function save(){
    setBusy(true);setError('');
    try{
      const proc=await restreamer.GetIngest(channel,['metadata']);
      if(!proc)throw new Error('Kanal nicht mehr verfügbar.');
      const player=restreamer.InitPlayerSettings(proc.metadata.player);
      if(JSON.stringify(player.overlay)!==baseline)throw new Error('Die Player-Einstellungen wurden inzwischen geändert. Dialog schließen und erneut öffnen, um den aktuellen Stand zu laden.');
      const result=await restreamer.SetIngestMetadata(channel,{...proc.metadata,player:{...player,overlay:settings}});
      if(result===false)throw new Error('Overlay konnte nicht gespeichert werden.');
      setBaseline(JSON.stringify(settings));
      if(await restreamer.UpdatePlayer(channel)===false)throw new Error('Einstellungen gespeichert, Playerdateien konnten nicht aktualisiert werden. Bitte erneut speichern.');
      onSaved();onClose();
    }catch(e){setError(e.message);}finally{setBusy(false);}
  }
  async function store(name,data){
    try{return await restreamer.UploadData(channel,name,data);}
    catch(e){setError('Logo konnte nicht hochgeladen werden.');return '';}
    finally{setBusy(false);}
  }
  return <Dialog open onClose={()=>{if(!busy)onClose();}} maxWidth="md" fullWidth aria-labelledby="timelapse-overlay-title"
    sx={{position:'fixed',inset:0,width:'100%',height:'100%',maxWidth:'none',maxHeight:'none',p:0,overflow:'hidden',backgroundColor:'transparent',display:'block','& .MuiDialog-container':{width:'100%',alignItems:'center',justifyContent:'center'}}}
    PaperProps={{sx:{m:{xs:1.5,sm:3},p:0,width:{xs:'calc(100% - 24px)',sm:'calc(100% - 48px)'},maxHeight:'calc(100dvh - 24px)',backgroundColor:'background.modal',backgroundImage:'none',display:'flex',flexDirection:'column',overflow:'hidden',borderRadius:2}}}>
    <DialogTitle id="timelapse-overlay-title" sx={{textAlign:'center',fontFamily:'"Dosis", "Roboto", sans-serif',fontSize:{xs:'1.6rem',sm:'2rem'},flexShrink:0}}>Overlay-Einstellungen</DialogTitle>
    <DialogContent sx={{overflowY:'auto',minHeight:0,px:{xs:2,sm:3},overflowWrap:'anywhere'}}>
      <Typography sx={{mb:2}}>Gemeinsame Player- und Zeitraffer-Overlays je Kanal. Änderungen gelten im Liveplayer und für neue Zeitrafferbilder. Bereits aufgenommene Bilder behalten ihre damaligen Werte. Vor einem Kanalwechsel bitte speichern oder abbrechen.</Typography>
      {error&&<Alert severity="error" sx={{mb:2}}>{error}</Alert>}
      <TextField select fullWidth label="Overlay-Kanal" value={channel} disabled={busy||!!dirty} onChange={e=>setChannel(e.target.value)} sx={{mb:3}}>{channels.map(c=><MenuItem value={c.id} key={c.id}>{c.name}</MenuItem>)}</TextField>
      {!channel&&<Typography>Keine Kanäle vorhanden.</Typography>}
      {channel&&!settings&&!error&&<Typography>Einstellungen werden geladen …</Typography>}
      {settings&&<fieldset disabled={busy} style={{border:0,padding:0,margin:0,minWidth:0}}><Grid container spacing={2}><PlayerOverlay key={channel} settings={settings} onChange={setSettings} onStore={store} onStart={()=>setBusy(true)} onError={()=>()=>{setBusy(false);setError('Logo konnte nicht hochgeladen werden.');}}/></Grid></fieldset>}
    </DialogContent>
    <DialogActions disableSpacing sx={{display:'grid',gridTemplateColumns:{xs:'1fr',sm:'repeat(2,minmax(0,1fr))'},gap:1.5,p:2,flexShrink:0,'& .MuiButton-root':{width:'100%',minHeight:48,m:0,textTransform:'none',fontWeight:700}}}>
      <Button variant="contained" disabled={busy||!settings} onClick={save} sx={{backgroundColor:'#2e7d32',color:'#fff','&:hover':{backgroundColor:'#1b5e20'}}}>Speichern</Button>
      <Button variant="contained" disabled={busy} onClick={onClose} sx={{backgroundColor:'#c62828',color:'#fff','&:hover':{backgroundColor:'#b71c1c'}}}>Abbrechen</Button>
    </DialogActions>
  </Dialog>;
}
