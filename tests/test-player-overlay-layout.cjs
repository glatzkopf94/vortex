const fs=require('fs'),vm=require('vm'),assert=require('assert/strict');
const html=fs.readFileSync('ui/public/_player/videojs/player.html','utf8');
const code=html.split('// BEGIN SNAPSHOT MATCHED LAYOUT')[1].split('// END SNAPSHOT MATCHED LAYOUT')[0];
function element(){return {style:{setProperty(k,v){this[k]=v;}},appendChild(){},textContent:''};}
const canvas=element();canvas.getContext=()=>({font:'',measureText(s){return {width:s.length*48,actualBoundingBoxAscent:70,actualBoundingBoxDescent:20,fontBoundingBoxAscent:90,fontBoundingBoxDescent:24};},fillRect(){},fillText(){}});
const video={videoWidth:3840,videoHeight:2160};const el={clientWidth:2048,clientHeight:1152,querySelector:()=>video};
const c={document:{createElement:()=>canvas},window:{},player:{el:()=>el,on(){}},playerOverlay:{font:'sans-bold',box:true,position:'top-center'},overlayBaseFontSize:32,overlayPositions:['top-left','top-center','top-right','bottom-left','bottom-center','bottom-right'],overlayRoot:element(),overlayText:element(),responsiveLogos:[{image:element(),baseWidth:240}],colorValue:()=> '#fff',rgba:()=> '#000',console};
vm.createContext(c);vm.runInContext(code,c);c.overlayFontReady=true;c.overlayLabel='Temp: 3.9 °C';let count=0;
for(const [w,h,sw,sh] of [[2048,1152,3840,2160],[360,640,3840,2160],[640,480,1280,960]]){
 el.clientWidth=w;el.clientHeight=h;video.videoWidth=sw;video.videoHeight=sh;
 for(const pos of c.overlayPositions){c.playerOverlay.position=pos;c.updatePlayerOverlayLayout();const r=Math.min(w/sw,h/sh),tw=canvas.width-32,th=canvas.height-32;
 const x=pos.endsWith('left')?8:pos.endsWith('center')?(sw-tw)/2-16:sw-tw-40,y=pos.startsWith('top')?8:sh-th-40;
 assert.equal(parseFloat(c.overlayText.style.left),x*r);assert.equal(parseFloat(c.overlayText.style.top),y*r);
 assert.equal(parseFloat(c.overlayRoot.style.left),(w-sw*r)/2);assert.equal(parseFloat(canvas.style.width),canvas.width*r);
 assert.equal(parseFloat(c.responsiveLogos[0].image.style.width),Math.round(Math.min(sw*.45,240*Math.min(sw/1280,sh/720)))*r);count++;
 }
}
c.overlayLabel='';c.updatePlayerOverlayLayout();assert.equal(c.overlayText.style.display,'none');
assert(html.includes('face.load()'));assert(html.includes("player.on('loadedmetadata',updatePlayerOverlayLayout)"));
console.log('PASS '+count+' layouts: all positions, mobile letterbox, 4:3, logos, empty text');
