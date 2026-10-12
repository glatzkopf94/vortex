const {chromium}=require('playwright');
const esbuild=require('esbuild');
const assert=require('node:assert/strict');
(async()=>{
 const browser=await chromium.launch({executablePath:process.env.CHROMIUM_EXECUTABLE_PATH,headless:true,args:['--no-sandbox']});
 try{
  const page=await browser.newPage({timezoneId:'Europe/Berlin'});
  await page.setContent('<div style="width:640px"><video id="p" class="video-js vjs-public vjs-live-dvr"></video></div>');
  await page.addStyleTag({path:require.resolve('video.js/dist/video-js.min.css')});
  await page.addStyleTag({path:'ui/src/misc/Player/video-js-skin-public.min.css'});
  await page.addScriptTag({path:require.resolve('video.js/dist/video.min.js')});
  const built=esbuild.buildSync({entryPoints:['ui/src/misc/Player/dvrMarkers.js'],bundle:true,write:false,format:'iife',globalName:'DVR'});
  await page.addScriptTag({content:built.outputFiles[0].text});
  await page.evaluate(()=>{
   window.p=videojs('p',{controls:true,fluid:true,aspectRatio:'16:9'});
   p.addClass('vjs-has-started');p.addClass('vjs-user-active');
   p.seekable=()=>({length:1,start:()=>0,end:()=>10800});
   p.tech(true).vhs={playlists:{media:()=>({segments:[{dateTimeString:'2026-10-06T12:00:00Z',start:0,duration:10800}]})}};
   DVR.default(p,'https://example.invalid/stream.m3u8');
  });
  const labels=await page.locator('.lc-dvr-tick-label').allTextContents();
  assert.ok(labels.includes('14:30')&&labels.includes('16:30'),JSON.stringify(labels));
  await page.evaluate(()=>p.dispose());
  await page.addScriptTag({path:'ui/src/misc/Player/timelineMarkers.js'});
  for(const width of [360,640]){
   await page.evaluate(width=>{
    document.body.innerHTML=`<div style="width:${width}px"><video id="time" class="video-js vjs-public nkl-timelapse-video"></video></div>`;
    window.p=videojs('time',{controls:true,fluid:true,aspectRatio:'16:9'});
    p.addClass('vjs-has-started');p.addClass('vjs-user-active');
    window.cleanup=nklTimelineMarkers(p,{duration:48,markers:Array.from({length:24},(_,hour)=>({hour,position:hour*2,label:String(hour).padStart(2,'0')+':00'}))});
   },width);
   const count=await page.locator('.lc-dvr-tick-label').count();assert.ok(count>0&&count<=Math.floor(width/70));
   await page.evaluate(()=>cleanup());assert.equal(await page.locator('.lc-dvr-markers').count(),0);
   await page.evaluate(()=>{nklTimelineMarkers(p,{markers:[]});});assert.equal(await page.locator('.lc-dvr-markers').count(),0);
   await page.evaluate(()=>p.dispose());
  }
  console.log('PASS: DVR PROGRAM-DATE-TIME marks, adaptive daily labels at 360/640px, empty season timeline, cleanup.');
 }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
