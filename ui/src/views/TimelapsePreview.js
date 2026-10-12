import React from 'react';
import {useStatusNotifications} from '../contexts/Notify';
import videojs from 'video.js';
import '../misc/Player/styles';
import '../misc/Player/timelineMarkers';
import { Box, Typography } from '@mui/material';

export default function TimelapsePreview({restreamer, project}) {
  const host=React.useRef(null);
  const instance=React.useRef(null);
  const [error,setError]=React.useState('');
  useStatusNotifications({'timelapse:preview':error?{severity:'error',message:error}:null});
  React.useEffect(()=>{
    if (!project.previewFrames) return;
    let closed=false, player=null, timer=null, token='', posterURL=null;
    const controller=new AbortController();
    const api=restreamer.api;
    const prefix=new URL(api.address+api.base+'/v3/timelapse/project/'+project.id+'/',window.location.href).href;
    async function refreshToken(){token=typeof api.token==='function'?await api.token():api.token;}
    (async()=>{
      try {
        await refreshToken(); if(closed)return;
        const element=document.createElement('video-js');element.className='video-js vjs-public nkl-timelapse-video';host.current.appendChild(element);
        player=videojs(element,{controls:true,autoplay:false,loop:false,preload:'none',fluid:true,html5:{vhs:{overrideNative:true}}});
        instance.current=player;
        player.on('xhr-hooks-ready',()=>{
          const xhr=player.tech().vhs.xhr;
          xhr.onRequest(options=>{
            if(new URL(options.uri,window.location.href).href.startsWith(prefix)) options.headers={...options.headers,Authorization:'Bearer '+token};
            return options;
          });
        });
        player.on('error',()=>setError('Vorschau konnte nicht geladen werden. Bitte Kanal erneut auswählen; die Aufnahme läuft unabhängig weiter.'));
        fetch(prefix+'poster.jpg',{headers:{Authorization:'Bearer '+token},cache:'no-store',signal:controller.signal})
          .then(response=>{if(!response.ok)throw new Error('Vorschaubild noch nicht verfügbar.');return response.blob();})
          .then(blob=>{if(closed)return;posterURL=URL.createObjectURL(blob);player.poster(posterURL);})
          .catch(error=>{if(!closed)setError(error.message);});
        fetch(prefix+'timeline.json',{headers:{Authorization:'Bearer '+token},cache:'no-store',signal:controller.signal})
          .then(r=>{if(!r.ok)throw new Error('Zeitmarkierungen noch nicht verfügbar.');return r.json();})
          .then(data=>{if(!closed)window.nklTimelineMarkers(player,data);}).catch(()=>{});
        player.src({src:prefix+'index.m3u8',type:'application/x-mpegURL'});
        timer=setInterval(()=>refreshToken().catch(()=>setError('Anmeldung für Vorschau konnte nicht erneuert werden.')),60000);
      } catch(e){if(!closed)setError(e.message);}
    })();
    return ()=>{closed=true;controller.abort();clearInterval(timer);if(posterURL)URL.revokeObjectURL(posterURL);if(player)player.dispose();instance.current=null;};
  },[restreamer,project.id,Boolean(project.previewFrames)]);
  return <Box sx={{my:2,maxWidth:960}}>
    {!project.previewFrames&&<Typography>Vorschau wird ab zwei aufgenommenen Bildern vorbereitet.</Typography>}
    <div ref={host}/>
    {project.previewFrames>0&&<Typography variant="caption">{project.previewFrames} Bilder verfügbar · Wiedergabe mit Play starten. Neueste Abschnitte nach erneutem Auswählen des Kanals.</Typography>}
  </Box>;
}
