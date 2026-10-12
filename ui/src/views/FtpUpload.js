// Modified 2026-10-11: readable FTP validation and asynchronous connection-test feedback.
import React from 'react';
import NotifyContext, {useStatusNotifications} from '../contexts/Notify';
import {Stack,Typography} from '@mui/material';
import TimelapseTransfer from './TimelapseTransfer';

export default function FtpUpload({restreamer}) {
  const notify=React.useContext(NotifyContext);
  const [data,setData]=React.useState(null);
  const [error,setError]=React.useState('');
  const [busy,setBusy]=React.useState(false);
  useStatusNotifications({'ftp:error':error?{severity:'error',message:error}:null});
  const call=React.useCallback(async(body)=>{
    const [value,err]=await restreamer._call(restreamer.api._call,body?'POST':'GET','/v3/timelapse/'+(body?'action':'status'),body?{headers:{'Content-Type':'application/json'},body:JSON.stringify(body)}:{});
    if(err){const message=typeof err.message==='string'?err.message:err.message?.message;throw new Error(typeof message==='string'?message:'FTP-Anfrage fehlgeschlagen'+(err.code?' (HTTP '+err.code+')':'')+'.');}
    return value;
  },[restreamer]);
  React.useEffect(()=>{
    let closed=false;
    async function refresh(){try{const value=await call();if(!closed)setData(value);}catch(e){if(!closed)setError(String(e.message));}}
    refresh();const timer=setInterval(refresh,2000);
    return()=>{closed=true;clearInterval(timer);};
  },[call]);
  async function action(body){
    setBusy(true);setError('');
    if(body.action==='test_transfer')setData(previous=>previous?{...previous,transferTest:{state:'running'}}:previous);
    try{
      const result=await call(body);
      setData(await call());
      const message=body.action==='cancel_transfer'?'Upload abgebrochen bzw. Abbruch angefordert.':body.action==='configure_transfer'?'FTP-Einstellungen gespeichert.':body.action==='test_transfer'?'Verbindungstest gestartet.':'Übertragung beauftragt.';
      notify.Dispatch(body.action==='configure_transfer'?'success':'info','ftp:action',message);
      return result;
    }catch(e){setError(String(e.message));}
    finally{setBusy(false);}
  }
  return <Stack spacing={2} sx={{p:2,minWidth:0,maxWidth:'100%',overflowWrap:'anywhere'}}>
    <Typography variant="h2">FTP-Upload</Typography>
    {data?.transfer?<TimelapseTransfer data={data} busy={busy} action={action}/>:<Typography>FTP-Einstellungen werden geladen …</Typography>}
  </Stack>;
}
