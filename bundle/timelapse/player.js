/* Loaded only when Zeitraffer is selected. Never preloads media on Live. */
(function () {
  'use strict';
  window.nklOpenTimelapse = async function (context) {
    if (window.nklTimelapseClose) return;
    if(!window.nklTimelineMarkers || !window.nklConfigureTimelapseBuffer){
      await new Promise(resolve=>{var script=document.createElement('script');script.src='player/videojs/dist/timeline-markers.js?nkl=timelapse-buffer-v1';script.onload=resolve;script.onerror=resolve;document.head.appendChild(script);});
    }
    if(window.nklTimelapseClose)return;
    context.onOpen();
    var wasPlaying = !context.player.paused();
    context.player.pause();
    var root = document.createElement('section');
    root.className = 'nkl-timelapse-panel';
    root.setAttribute('aria-label', 'Zeitraffer');
    root.innerHTML = '<div class="nkl-timelapse-toolbar"><button type="button" class="nkl-live-return"><span style="color:#f44">●</span> Live</button><select aria-label="Zeitraffer auswählen"></select><button type="button" class="nkl-timelapse-refresh">Aktualisieren</button></div><p role="status">Zeitraffer werden geladen …</p><video class="video-js vjs-public nkl-timelapse-video" controls playsinline hidden></video>';
    context.player.el().appendChild(root);
    var message = root.querySelector('p');
    var select = root.querySelector('select');
    var preview = null;
    var closed = false;
    var clearMarkers = function(){};
    var markerRequest = 0;
    var controller = new AbortController();
    function close(resume) {
      if (closed) return;
      closed = true;
      controller.abort();
      clearMarkers();
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
    root.addEventListener('keydown', function (event) { if (event.key === 'Escape') close(true); });
    function show() {
      var option = select.options[select.selectedIndex];
      if (!option || option.disabled) return;
      message.textContent = option.dataset.description;
      root.querySelector('video').hidden = false;
      if (!preview) {
        preview = videojs(root.querySelector('video'), {controls:true, autoplay:false, preload:'none', loop:false, fluid:false});
        if (window.nklConfigureTimelapseBuffer) window.nklConfigureTimelapseBuffer(preview);
        preview.on('play', context.onPlay);
        preview.on('pause', context.onPause);
        preview.on('error', function () { message.textContent = 'Vorschau derzeit nicht verfügbar. Live bleibt erreichbar.'; });
      }
      clearMarkers();
      var request=++markerRequest;
      fetch('timelapse/project/'+encodeURIComponent(option.value)+'/timeline.json',{cache:'no-store',signal:controller.signal})
        .then(function(r){if(!r.ok)throw new Error('timeline');return r.json();})
        .then(function(data){if(!closed&&request===markerRequest&&window.nklTimelineMarkers)clearMarkers=window.nklTimelineMarkers(preview,data);}).catch(function(){});
      preview.pause();
      preview.poster('timelapse/project/'+encodeURIComponent(option.value)+'/poster.jpg?t='+Date.now());
      preview.src({src:'timelapse/project/'+encodeURIComponent(option.value)+'/index.m3u8?t='+Date.now(), type:'application/x-mpegURL'});

    }
    async function refresh() {
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
        else show();
      } catch (error) {
        if (!closed) message.textContent = 'Zeitraffer derzeit nicht erreichbar. Zurück zu Live ist jederzeit möglich.';
      }
    }
    select.onchange = show;
    root.querySelector('.nkl-timelapse-refresh').onclick = refresh;
    root.querySelector('.nkl-live-return').focus();
    await refresh();
  };
})();
