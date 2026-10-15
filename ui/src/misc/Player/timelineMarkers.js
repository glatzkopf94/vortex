// Shared by admin and public timelapse players; loaded only with timelapse UI.
window.nklConfigureTimelapseBuffer = function (player) {
  player.on('loadstart', function () {
    const vhs=player.tech() && player.tech().vhs;
    const controller=vhs && vhs.playlistController_;
    const loader=controller && controller.mainSegmentLoader_;
    if (!loader) return; // Native HLS has its own buffer management.
    // VHS 3 (Video.js 8): its default 30–60 seconds ahead plus 30 seconds
    // behind can exceed Firefox's MSE quota for existing 100+ MB segments.
    // Quota recovery removes through the next keyframe, including unplayed
    // pictures. Keep this policy instance-local: Live/DVR must be untouched.
    controller.goalBufferLength=()=>1;
    loader.trimBackBuffer_=function () {
      const playlist=this.playlist_;
      if (!playlist || !playlist.endList) return;
      const time=this.currentTime_();
      let cut=0;
      for (const segment of playlist.segments) {
        if (Number.isFinite(segment.end) && segment.end<time-1) {
          cut=Math.max(cut,segment.end);
        }
      }
      // Every timelapse segment starts with a keyframe. Remove only completed
      // segments, never at an arbitrary point in the currently playing GOP.
      // Use measured ends rather than accumulated, rounded EXTINF durations;
      // stay just before the boundary to tolerate MSE timestamp rounding.
      if (cut>0.001) this.remove(0,cut-0.001);
    };
  });
};

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
