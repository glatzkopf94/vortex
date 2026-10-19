const {firefox}=require('playwright');
const assert=require('node:assert/strict');
const path=require('node:path');
const root=path.resolve(__dirname,'..');
(async()=>{
 const browser=await firefox.launch({headless:true});
 try {
  const page=await browser.newPage({viewport:{width:1100,height:800}});
  await page.setContent('<div style="width:800px"><video id="outer" class="video-js vjs-public"></video></div>');
  for(const file of ['ui/public/_player/videojs/dist/video-js.css','ui/public/_player/videojs/dist/video-js-skin.min.css','bundle/timelapse/player.css'])await page.addStyleTag({path:path.join(root,file)});
  for(const file of ['ui/public/_player/videojs/dist/video.min.js','ui/src/misc/Player/timelineMarkers.js','bundle/timelapse/player.js'])await page.addScriptTag({path:path.join(root,file)});
  await page.evaluate(async()=>{
   window.p=videojs('outer',{controls:true,fluid:true,aspectRatio:'16:9',preload:'none'});
   window.fetch=async url=>({ok:true,json:async()=>url.includes('qualities.json')?[{id:'original',label:'3840×2160',ready:true,url:'index.m3u8'},{id:'1080',label:'1920×1080',ready:true,url:'quality-1080.m3u8',bitrate:3072}]:url.includes('timeline.json')?{}:{projects:[{id:'test',label:'2026-10-17',last:1800000000,previewFrames:20}]}});
   await nklOpenTimelapse({player:p,channel:'test',button:{focus(){}},onOpen(){},onPlay(){},onPause(){}});
   document.querySelector('.nkl-timelapse-video').classList.add('vjs-has-started','vjs-user-active');
  });
  const toggle=page.locator('.nkl-timelapse-video .vjs-fullscreen-control');
  await toggle.click({force:true});
  await page.waitForFunction(()=>document.fullscreenElement===p.el());
  const layout=await page.evaluate(()=>{
   const toolbar=document.querySelector('.nkl-timelapse-toolbar');const video=document.querySelector('.nkl-timelapse-video');
   return {contains:document.fullscreenElement.contains(toolbar),barBottom:toolbar.getBoundingClientRect().bottom,videoTop:video.getBoundingClientRect().top,videoBottom:video.getBoundingClientRect().bottom,height:innerHeight};
  });
  assert.ok(layout.contains);assert.ok(layout.videoTop>=layout.barBottom);assert.ok(layout.videoBottom<=layout.height+1);
  await page.locator('.nkl-quality-toggle').click();await page.getByRole('button',{name:'3840×2160',exact:true}).click();
  await page.waitForFunction(()=>document.querySelector('.nkl-quality-toggle').title.includes('3840'));
  await page.locator('.nkl-timelapse-refresh').click();await page.waitForFunction(()=>document.querySelector('.nkl-timelapse-refresh').textContent.includes('Aktualisiert'));
  await toggle.click({force:true});await page.waitForFunction(()=>!document.fullscreenElement);
  assert.equal(await page.locator('.nkl-timelapse-panel').count(),1);
  await toggle.click({force:true});await page.waitForFunction(()=>document.fullscreenElement===p.el());
  // Escape delivered to the panel must not dispose the preview while fullscreen.
  await page.locator('.nkl-quality-toggle').dispatchEvent('keydown',{key:'Escape',bubbles:true});
  assert.equal(await page.locator('.nkl-timelapse-panel').count(),1);
  await page.evaluate(()=>document.exitFullscreen());await page.waitForFunction(()=>!document.fullscreenElement);
  await page.locator('.nkl-live-return').click();assert.equal(await page.locator('.nkl-timelapse-panel').count(),0);
  await page.evaluate(()=>p.dispose());
  console.log('PASS: real Firefox fullscreen contains toolbar; quality and refresh work; exit/reenter and Live return work.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
