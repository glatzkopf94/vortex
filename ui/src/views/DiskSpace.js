import React from 'react';
import {useStatusNotifications} from '../contexts/Notify';
import {Typography} from '@mui/material';
export default function DiskSpace({restreamer}) {
 const [space,setSpace]=React.useState(null);
 const [error,setError]=React.useState('');
 useStatusNotifications({'disk:status':error?{severity:'error',message:error}:null});
 React.useEffect(()=>{
  let closed=false;
  async function refresh(){try{const [data,error]=await restreamer._call(restreamer.api._call,'GET','/v3/timelapse/status',{});if(!closed){if(error)setError('Speicherplatz konnte nicht ermittelt werden.');else{setSpace(data);setError('');}}}catch{if(!closed)setError('Speicherplatz konnte nicht ermittelt werden.');}}
  refresh();const timer=setInterval(refresh,30000);return()=>{closed=true;clearInterval(timer);};
 },[restreamer]);
 return <Typography sx={{fontWeight:700,mt:1,mb:1}}>{space?`Verfügbarer Speicherplatz: ${(space.diskFreeBytes/1073741824).toFixed(1)} GB frei von ${(space.diskTotalBytes/1073741824).toFixed(1)} GB.`:'Freier Plattenplatz wird ermittelt …'}</Typography>;
}
