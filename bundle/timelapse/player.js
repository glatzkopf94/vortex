/* Loaded only when Zeitraffer is selected. Never preloads media on Live. */
(function () {
  'use strict';
  window.nklOpenTimelapse = async function (context) {
    if (window.nklTimelapseClose) return;
    if(!window.nklTimelineMarkers || !window.nklConfigureTimelapseBuffer){
      await new Promise(resolve=>{var script=document.createElement('script');script.src='player/videojs/dist/timeline-markers.js?nkl=timelapse-buffer-v3';script.onload=resolve;script.onerror=resolve;document.head.appendChild(script);});
    }
    if(window.nklTimelapseClose)return;
    context.onOpen();
    var wasPlaying = !context.player.paused();
    context.player.pause();
    var root = document.createElement('section');
    root.className = 'nkl-timelapse-panel';
    root.setAttribute('aria-label', 'Zeitraffer');
    root.innerHTML = '<div class="nkl-timelapse-toolbar"><button type="button" class="nkl-live-return"><span style="color:#f44">●</span> Live</button><select aria-label="Zeitraffer auswählen"></select><div class="nkl-quality-control"><button type="button" class="nkl-quality-toggle" aria-label="Wiedergabequalität einstellen" title="Wiedergabequalität" aria-expanded="false">⚙</button><div class="nkl-quality-menu" hidden role="group" aria-label="Wiedergabequalität"></div></div><button type="button" class="nkl-timelapse-refresh">Aktualisieren</button></div><p role="status">Zeitraffer werden geladen …</p><video class="video-js vjs-public nkl-timelapse-video" controls playsinline hidden></video>';
    context.player.el().appendChild(root);
    var message = root.querySelector('p');
    var select = root.querySelector('select');
    var refreshButton = root.querySelector('.nkl-timelapse-refresh');
    var refreshing = false;
    var qualityToggle=root.querySelector('.nkl-quality-toggle');
    var qualityMenu=root.querySelector('.nkl-quality-menu');
    var qualityChoice=null, qualityRequest=0;
    qualityToggle.onclick=function(){qualityMenu.hidden=!qualityMenu.hidden;qualityToggle.setAttribute('aria-expanded',String(!qualityMenu.hidden));};

    var preview = null;
    var closed = false;
    var clearMarkers = function(){};
    var clearFullscreen = function(){};
    var markerRequest = 0;
    var controller = new AbortController();
    function close(resume) {
      if (closed) return;
      closed = true;
      controller.abort();
      clearMarkers();
      clearFullscreen();
      if (preview) preview.dispose();
      root.remove();
      window.nklTimelapseClose = null;
      if (resume && wasPlaying) {
        var promise = context.player.play();
        if (promise && promise.catch) promise.catch(function () {});
      }
      context.button.focus();
    }
    window.nklTimelapseClose = close;
    root.querySelector('.nkl-live-return').onclick = function () { close(true); };
    root.addEventListener('keydown', function (event) { if (event.key === 'Escape' && !(context.player.isFullscreen && context.player.isFullscreen())) close(true); });
    async function show(preserve) {
      var option = select.options[select.selectedIndex];
      if (!option || option.disabled) return;
      message.textContent = option.dataset.description;
      root.querySelector('video').hidden = false;
      if (!preview) {
        preview = videojs(root.querySelector('video'), {controls:true, autoplay:false, preload:'none', loop:false, fluid:false});
        // The toolbar is a sibling of the preview. Fullscreen the enclosing
        // live player so date, quality and refresh remain available.
        var fullscreenToggle=preview.controlBar && preview.controlBar.fullscreenToggle;
        if(fullscreenToggle && context.player.requestFullscreen){
          fullscreenToggle.handleClick=function(){
            var result=context.player.isFullscreen()?context.player.exitFullscreen():context.player.requestFullscreen();
            if(result && result.catch)result.catch(function(){message.textContent='Vollbild konnte nicht geöffnet werden.';});
          };
          var syncFullscreen=function(){fullscreenToggle.controlText(context.player.isFullscreen()?'Non-Fullscreen':'Fullscreen');};
          context.player.on('fullscreenchange',syncFullscreen);
          clearFullscreen=function(){context.player.off('fullscreenchange',syncFullscreen);};
          syncFullscreen();
        }
        if (window.nklConfigureTimelapseBuffer) window.nklConfigureTimelapseBuffer(preview);
        preview.on('play', context.onPlay);
        preview.on('pause', context.onPause);
        preview.on('error', function () { message.textContent = 'Vorschau derzeit nicht verfügbar. Live bleibt erreichbar.'; });
      }
      var stamp=++qualityRequest;
      var position=preserve?preview.currentTime():0;
      var playing=preserve&&!preview.paused();
      var variants;
      try {
        var response=await fetch('timelapse/project/'+encodeURIComponent(option.value)+'/qualities.json',{cache:'no-store',signal:controller.signal});
        if(!response.ok)throw new Error('Qualitäten nicht erreichbar');
        variants=await response.json();
        if(closed||stamp!==qualityRequest)return;
      } catch(error) {
        if(closed||stamp!==qualityRequest)return;
        message.textContent+=' · Qualitätsauswahl nicht verfügbar, Quellvideo wird verwendet.';
        variants=[{id:'original',label:'Quellauflösung',ready:true,url:'index.m3u8'}];
      }
      var selected=variants.find(function(q){return q.id===qualityChoice&&q.ready;}) || variants.find(function(q){return q.id==='1080'&&q.ready;}) || variants[0];
      qualityMenu.replaceChildren();
      variants.forEach(function(q){
        var button=document.createElement('button');button.type='button';button.disabled=!q.ready;
        button.textContent=q.label+(q.ready?'':' · wird vorbereitet');button.setAttribute('aria-pressed',String(q.id===selected.id));
        button.onclick=function(){qualityChoice=q.id;qualityMenu.hidden=true;qualityToggle.setAttribute('aria-expanded','false');show(true);};qualityMenu.appendChild(button);
      });
      qualityToggle.title='Wiedergabequalität: '+selected.label;
      qualityToggle.setAttribute('aria-label',qualityToggle.title);
      preview.nklTimelapseBitrate=selected.bitrate||0;
      clearMarkers();
      var request=++markerRequest;
      fetch('timelapse/project/'+encodeURIComponent(option.value)+'/timeline.json',{cache:'no-store',signal:controller.signal})
        .then(function(r){if(!r.ok)throw new Error('timeline');return r.json();})
        .then(function(data){if(!closed&&request===markerRequest&&window.nklTimelineMarkers)clearMarkers=window.nklTimelineMarkers(preview,data);}).catch(function(){});
      preview.pause();
      preview.poster('timelapse/project/'+encodeURIComponent(option.value)+'/poster.jpg?t='+Date.now());
      if(preserve)preview.one('loadedmetadata',function(){if(closed||stamp!==qualityRequest)return;preview.currentTime(position);if(playing){var promise=preview.play();if(promise&&promise.catch)promise.catch(function(){});}});
      preview.src({src:'timelapse/project/'+encodeURIComponent(option.value)+'/'+selected.url+'?t='+Date.now(), type:'application/x-mpegURL'});
    }

    async function refresh(manual) {
      if (refreshing || closed) return;
      refreshing = true;
      refreshButton.disabled = true;
      refreshButton.setAttribute('aria-busy', 'true');
      refreshButton.textContent = 'Wird aktualisiert …';
      var succeeded = false;
      try {
        var response = await fetch('timelapse/channel/'+encodeURIComponent(context.channel), {cache:'no-store', signal:controller.signal});
        if (!response.ok) throw new Error('unavailable');
        var data = await response.json();
        if (closed) return;
        var previous = select.value;
        select.replaceChildren();
        data.projects.forEach(function (project) {
          var option = document.createElement('option');
          option.value = project.id;
          option.textContent = project.label.replace(/^(\d{4})-(\d{2})-(\d{2})$/, '$3.$2.$1') + (project.status === 'recording' ? ' · läuft' : '');
          option.disabled = !project.previewFrames;
          option.dataset.description = project.previewFrames ? 'Vorschau: '+project.previewFrames+' Bilder · Letzte Aufnahme: '+new Date(project.last*1000).toLocaleString('de-DE',{day:'2-digit',month:'2-digit',year:'numeric',hour:'2-digit',minute:'2-digit'}) : 'Die erste Vorschau wird vorbereitet.';
          select.appendChild(option);
        });
        if ([].some.call(select.options, function (option) {return option.value===previous && !option.disabled;})) select.value=previous;
        else {var first=[].find.call(select.options,function(option){return !option.disabled;}); if(first)select.value=first.value;}
        if (!data.projects.some(function (p) {return p.previewFrames>0;})) message.textContent = 'Noch keine veröffentlichte Zeitraffervorschau vorhanden.';
        else await show(false);
        succeeded = true;
        if (manual) message.textContent = 'Aktualisiert. ' + message.textContent;
      } catch (error) {
        if (!closed) message.textContent = 'Zeitraffer derzeit nicht erreichbar. Zurück zu Live ist jederzeit möglich.';
      } finally {
        refreshing = false;
        if (!closed) {
          refreshButton.disabled = false;
          refreshButton.setAttribute('aria-busy', 'false');
          refreshButton.textContent = manual ? (succeeded ? '✓ Aktualisiert' : 'Erneut versuchen') : 'Aktualisieren';
        }
      }
    }
    select.onchange = function(){qualityChoice=null;show(false);};
    refreshButton.onclick = function () { return refresh(true); };
    root.querySelector('.nkl-live-return').focus();
    await refresh();
  };
})();
