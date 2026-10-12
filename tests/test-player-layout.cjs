// NODE_PATH must include playwright and video.js. Uses actual Video.js/CSS.
const {chromium}=require('playwright');
const fs=require('node:fs');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({headless:true,executablePath:process.env.CHROMIUM_EXECUTABLE_PATH||undefined,args:['--no-sandbox']});
 try {
  const page=await browser.newPage();
  for(const width of [360,960]) for(const ratio of ['16:9','4:3']) for(const skin of ['internal','public','standalone']) for(const dvr of [false,true]) {
   await page.setViewportSize({width:width+40,height:1100});
   await page.setContent(`<div style="width:${width}px"><video id="player" class="video-js ${dvr?'vjs-live-dvr':'vjs-live-no-dvr'} vjs-public ${skin==='internal'?'vjs-internal':''}"></video></div>`);
   await page.addStyleTag({path:require.resolve('video.js/dist/video-js.min.css')});
   await page.addStyleTag({path:'ui/public/_player/videojs/dist/video-js-skin.min.css'});
   if(skin==='internal')await page.addStyleTag({path:'ui/src/misc/Player/video-js-skin-internal.min.css'});
   await page.addScriptTag({path:require.resolve('video.js/dist/video.min.js')});
   await page.evaluate(ratio=>{
    window.p=videojs('player',{controls:true,liveui:true,fluid:true,aspectRatio:ratio,preload:'none'});
    p.addClass('vjs-has-started');p.addClass('vjs-user-active');
   },ratio);
   const layout=await page.evaluate(()=>{
    const rect=e=>{const r=e.getBoundingClientRect();return {top:r.top,bottom:r.bottom,left:r.left,right:r.right};};
    const root=document.querySelector('.video-js');
    return {gradient:getComputedStyle(root.querySelector('.vjs-control-bar')).backgroundImage,yellow:getComputedStyle(root.querySelector('.vjs-play-progress')).backgroundColor,root:rect(root),bar:rect(root.querySelector('.vjs-control-bar')),buttons:[...root.querySelectorAll('.vjs-control-bar .vjs-button')].filter(e=>getComputedStyle(e).display!=='none'&&e.getBoundingClientRect().width>0).map(rect)};
   });
   const label=`${skin} ${width} ${ratio}`;
   assert.match(layout.gradient,/linear-gradient/,label);assert.equal(layout.yellow,'rgb(234, 234, 5)',label);
   assert.ok(Math.abs(layout.root.bottom-layout.bar.bottom)<1,label+' bar bottom');
   for(const b of layout.buttons)assert.ok(b.top>=layout.bar.top-1&&b.bottom<=layout.root.bottom+1,label+' button inside image '+JSON.stringify(layout));
   await page.evaluate(()=>p.dispose());
  }
  for(const width of [360,960]) {
   await page.setViewportSize({width:width+40,height:900});
   await page.setContent(`<div style="width:${width}px"><video id="outer" class="video-js vjs-public"></video></div>`);
   await page.addStyleTag({path:require.resolve('video.js/dist/video-js.min.css')});
   await page.addStyleTag({path:'ui/public/_player/videojs/dist/video-js-skin.min.css'});
   await page.addStyleTag({path:'bundle/timelapse/player.css'});
   await page.addScriptTag({path:require.resolve('video.js/dist/video.min.js')});
   await page.addScriptTag({path:'ui/src/misc/Player/timelineMarkers.js'});
   await page.addScriptTag({path:'bundle/timelapse/player.js'});
   await page.evaluate(async()=>{
    window.p=videojs('outer',{controls:true,fluid:true,aspectRatio:'16:9',preload:'none'});
    window.fetch=async()=>({ok:true,json:async()=>({projects:[{id:'test',label:'2026-10-07',last:1800000000,previewFrames:20}]})});
    await window.nklOpenTimelapse({player:p,channel:'test',button:{focus(){}},onOpen(){},onPlay(){},onPause(){}});
   });
   const nested=await page.evaluate(()=>{
    const inner=document.querySelector('.nkl-timelapse-video');
    inner.classList.add('vjs-has-started','vjs-user-active');
    const rect=e=>{const r=e.getBoundingClientRect();return {top:r.top,bottom:r.bottom,height:r.height};};
    return {outer:rect(p.el()),inner:rect(inner),bar:rect(inner.querySelector('.vjs-control-bar')),yellow:getComputedStyle(inner.querySelector('.vjs-play-progress')).backgroundColor,gradient:getComputedStyle(inner.querySelector('.vjs-control-bar')).backgroundImage,paused:videojs.getPlayer(inner.id).paused()};
   });
   assert.ok(nested.inner.bottom<=nested.outer.bottom+1,JSON.stringify(nested));
   assert.ok(nested.bar.top>=nested.inner.top-1&&nested.bar.bottom<=nested.inner.bottom+1,JSON.stringify(nested));
   assert.equal(nested.bar.height,70);
   assert.equal(nested.yellow,'rgb(234, 234, 5)');
   assert.match(nested.gradient,/linear-gradient/);assert.equal(nested.paused,true);
   await page.evaluate(()=>{window.nklTimelapseClose(false);p.dispose();});
  }
  console.log('PASS: nested actual timelapse players with shared yellow/gradient skin;  24 actual Chromium layouts, internal/admin-public/standalone, 360/960 px, 16:9/4:3, DVR on/off.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
