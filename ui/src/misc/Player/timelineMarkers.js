// Shared by admin and public timelapse players; loaded only with timelapse UI.
window.nklTimelineMarkers = function (player, data) {
  const holder=player.el().querySelector('.vjs-progress-holder');
  if(!holder || !data.markers || !data.markers.length) return ()=>{};
  player.addClass('nkl-time-markers');
  const layer=document.createElement('div');layer.className='lc-dvr-markers';layer.setAttribute('aria-hidden','true');holder.appendChild(layer);
  function render(){
    const duration=Number.isFinite(player.duration())&&player.duration()>0?player.duration():data.duration;
    const width=holder.clientWidth;
    if(!duration||!width)return;
    const capacity=Math.max(1,Math.floor(width/70));
    const hours=[1,2,3,4,6,12,24];
    const step=hours.find(h=>data.markers.filter(m=>m.hour%h===0).length<=capacity)||24;
    const fragment=document.createDocumentFragment();let last=-100;
    data.markers.forEach(m=>{
      const x=m.position/duration*width;
      if(m.hour%step || x<25 || x>width-25 || x-last<65)return;
      const tick=document.createElement('span');tick.className='lc-dvr-tick';tick.style.left=(m.position/duration*100)+'%';
      const label=document.createElement('span');label.className='lc-dvr-tick-label';label.textContent=m.label;tick.appendChild(label);fragment.appendChild(tick);last=x;
    });
    layer.replaceChildren(fragment);
  }
  const events=['loadedmetadata','durationchange','playerresize'];events.forEach(e=>player.on(e,render));
  const observer=typeof ResizeObserver==='function'?new ResizeObserver(render):null;if(observer)observer.observe(holder);
  let disposed=false;
  function cleanup(){if(disposed)return;disposed=true;if(observer)observer.disconnect();events.forEach(e=>player.off(e,render));layer.remove();player.off('dispose',cleanup);}
  player.on('dispose',cleanup);render();return cleanup;
};
