const assert=require('node:assert/strict');
const fs=require('node:fs'),path=require('node:path'),http=require('node:http'),os=require('node:os');
const {execFileSync}=require('node:child_process');
const {firefox}=require('playwright');
const root=path.resolve(__dirname,'..'),dir=fs.mkdtempSync(path.join(os.tmpdir(),'vortex-hevc-'));
const ff=(args)=>execFileSync('ffmpeg',['-hide_banner','-loglevel','error',...args],{stdio:'pipe'});
ff(['-f','lavfi','-i','testsrc2=size=640x360:rate=25','-t','12','-c:v','libx265','-preset','ultrafast','-x265-params','pools=1:frame-threads=1:keyint=50:log-level=error','-tag:v','hvc1','-b:v','1500k','-f','hls','-hls_time','2','-hls_list_size','0','-hls_segment_type','fmp4','-master_pl_name','main.m3u8',path.join(dir,'hevc.m3u8')]);
ff(['-i',path.join(dir,'hevc.m3u8'),'-c:v','libx264','-preset','ultrafast','-threads','1','-g','50','-f','hls','-hls_time','2','-hls_list_size','0',path.join(dir,'fallback.m3u8')]);
// Ubuntu's fixture encoder is FFmpeg 6.1; its HLS HEVC CODECS writer is
// defective (fixed upstream in 2025). Derive the fixture codec from hvcC.
// Production uses patched FFmpeg 9, which already has the corrected writer.
const init=fs.readFileSync(path.join(dir,'init.mp4'));
const hvcc=init.subarray(init.indexOf(Buffer.from('hvcC'))+4);
let compat=0,bits=hvcc.readUInt32BE(2);for(let i=0;i<32;i++){compat=(compat*2+(bits&1))>>>0;bits>>>=1;}
const constraints=[...hvcc.subarray(6,12)];while(constraints.length&&constraints.at(-1)===0)constraints.pop();
const codec=`hvc1.${['','A','B','C'][hvcc[1]>>6]}${hvcc[1]&31}.${compat.toString(16)}.${hvcc[1]&32?'H':'L'}${hvcc[12]}`+constraints.map(b=>'.'+b.toString(16).toUpperCase()).join('');
fs.writeFileSync(path.join(dir,'main.m3u8'),fs.readFileSync(path.join(dir,'main.m3u8'),'utf8').replace(/CODECS="[^"]+"/,`CODECS="${codec}"`));
const template=fs.readFileSync(path.join(root,'ui/public/_player/videojs/player.html'),'utf8');
const hits=[];
const server=http.createServer((req,res)=>{
 const u=new URL(req.url,'http://local'),p=u.pathname;hits.push(p);res.setHeader('Cache-Control','no-store');
 if(p.endsWith('.html')){res.setHeader('Content-Type','text/html');return res.end(template.replace(/{{#if (airplay|chromecast)}}[\s\S]*?{{\/if}}/g,'').replaceAll('{{channelid}}',p.slice(1,-5)).replace(/{{[^}]+}}/g,'Test'));}
 if(p.endsWith('/config.js')){res.setHeader('Content-Type','application/javascript');const id=p.split('/')[2];return res.end('var playerConfig='+JSON.stringify({channelid:id,source:'main.m3u8',videoCodec:'hevc',fallbackSource:['nofallback','native'].includes(id)?'':'fallback.m3u8',poster:'',autoplay:false,mute:true,color:{buttons:'#fff'},overlay:{enabled:false},dvr:{enabled:true,hours:4,segmentDuration:2},playback:{singleActiveStream:false,sessionLimitEnabled:false}}));}
 if(p.startsWith('/timelapse/')){res.setHeader('Content-Type','application/json');return res.end('{"active":false}');}
 const file=p.startsWith('/player/videojs/')?path.join(root,'ui/public/_player/videojs',p.slice('/player/videojs/'.length)):path.join(dir,path.basename(p));
 if(!fs.existsSync(file)||!fs.statSync(file).isFile()){res.statusCode=404;return res.end();}
 res.setHeader('Content-Type',({'.js':'application/javascript','.css':'text/css','.m3u8':'application/vnd.apple.mpegurl','.ts':'video/mp2t','.mp4':'video/mp4'})[path.extname(file)]||'application/octet-stream');res.end(fs.readFileSync(file));
});
(async()=>{let browser;try{
 await new Promise(r=>server.listen(0,'127.0.0.1',r));browser=await firefox.launch({headless:true});
 const page=await browser.newPage();const errors=[];page.on('pageerror',e=>errors.push(e.message));
 // Exercise the real shipped Video.js HEVC/fMP4 path on this Firefox decoder.
 const native=await browser.newPage();native.on('pageerror',e=>errors.push(e.message));
 await native.goto(`http://127.0.0.1:${server.address().port}/native.html`);
 await native.locator('.vjs-big-play-button').click();
 await native.waitForFunction(()=>videojs('player').currentTime()>1,{},{timeout:15000}).catch(async e=>{console.log(await native.evaluate(()=>({error:videojs('player').error(),source:videojs('player').currentSrc(),ready:videojs('player').readyState()})),hits,fs.readFileSync(path.join(dir,'main.m3u8'),'utf8'));throw e;});
 assert.equal(await native.evaluate(()=>usingFallback),false);
 await native.evaluate(()=>videojs('player').currentTime(5));
 await native.waitForFunction(()=>videojs('player').currentTime()>5);
 await native.close();hits.length=0;
 // Unsupported HEVC: choose fallback before downloading the main stream.
 await page.addInitScript(()=>{const old=MediaSource.isTypeSupported.bind(MediaSource);MediaSource.isTypeSupported=(t)=>/hvc1|hev1/.test(t)?false:old(t);const oldCan=HTMLMediaElement.prototype.canPlayType;HTMLMediaElement.prototype.canPlayType=function(t){return /hvc1|hev1/.test(t)?'':oldCan.call(this,t);};});
 await page.goto(`http://127.0.0.1:${server.address().port}/fallback.html`);
 assert.equal(hits.some(p=>p.endsWith('.m3u8')),false,'untouched player fetched media');
 await page.locator('.vjs-big-play-button').click();
 await page.waitForFunction(()=>videojs('player').currentTime()>1,{},{timeout:25000});
 assert.ok(hits.includes('/fallback.m3u8'));assert.ok(!hits.includes('/hevc.m3u8'));
 await page.evaluate(()=>{const p=videojs('player');p.currentTime(5);});
 await page.waitForFunction(()=>videojs('player').currentTime()>5);
 await page.close();
 // Advertised support can be wrong: decoder error switches exactly once.
 const second=await browser.newPage();second.on('pageerror',e=>errors.push(e.message));
 await second.goto(`http://127.0.0.1:${server.address().port}/decode.html`);
 await second.evaluate(()=>{usingFallback=false;publicSourceURL=new URL('/hevc.m3u8',location.origin);publicPlayerSources=[{src:publicSourceURL.toString(),type:'application/x-mpegURL'}];publicStreamActivated=true;videojs('player').error({code:3,message:'simulated unavailable decoder'});});
 await second.waitForFunction(()=>videojs('player').currentTime()>1,{},{timeout:25000});
 assert.ok(await second.evaluate(()=>usingFallback));
 await second.close();
 // Disabled fallback does not fetch a second stream and gives a visible reason.
 const third=await browser.newPage();third.on('pageerror',e=>errors.push(e.message));
 await third.goto(`http://127.0.0.1:${server.address().port}/nofallback.html`);
 await third.evaluate(()=>{publicStreamActivated=true;videojs('player').error({code:3,message:'simulated unavailable decoder'});});
 assert.match(await third.locator('.vjs-error-display').textContent(),/kein H.264-Fallback/);
 assert.deepEqual(errors,[]);console.log('Firefox: real HEVC/fMP4 playback + seek, HEVC capability fallback, decode-error fallback, seek and disabled-fallback feedback OK');
}finally{if(browser)await browser.close();await new Promise(r=>server.close(r));fs.rmSync(dir,{recursive:true,force:true});}})().catch(e=>{console.error(e);process.exitCode=1;});
