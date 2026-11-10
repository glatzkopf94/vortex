const fs=require('node:fs'),path=require('node:path');
const {hevcCodecFromSampleEntry}=require('./hevc-codec.cjs');
const marker='/* Vortex HEVC hvcC parser v1 */';
function patchSource(source) {
  if(source.includes(marker))return source;
  const pattern=/\/\/ flac, opus, etc\s*track\.codec = track\.codec\.toLowerCase\(\);/g;
  const matches=source.match(pattern)||[];
  if(matches.length!==1)throw new Error('Unsupported player source: expected exactly one MP4 codec probe, got '+matches.length);
  return source.replace(pattern,()=>`${marker}\ntrack.codec = (${hevcCodecFromSampleEntry.toString()})(track.codec.toLowerCase(), codecBox);`);
}
async function patchAll(){
 const root=path.resolve(__dirname,'..');
 for(const name of ['node_modules/mux.js/lib/mp4/probe.js','node_modules/video.js/dist/video.cjs.js','node_modules/video.js/dist/video.es.js','node_modules/video.js/dist/video.js']) {
  const file=path.join(root,name),old=fs.readFileSync(file,'utf8'),updated=patchSource(old);
  if(updated!==old)fs.writeFileSync(file,updated);
 }
 const {minify}=require('terser');
 const result=await minify(fs.readFileSync(path.join(root,'node_modules/video.js/dist/video.js'),'utf8'),{format:{comments:/@license/}});
 if(!result.code)throw new Error('Player minification failed');
 fs.writeFileSync(path.join(root,'public/_player/videojs/dist/video.min.js'),result.code+'\n');
 console.log('Vortex HEVC probe: admin and public player synchronized.');
}
module.exports={patchSource,patchAll};
if(require.main===module)patchAll().catch(error=>{console.error(error);process.exitCode=1;});
