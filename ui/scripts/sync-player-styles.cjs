// One canonical skin for admin previews and generated public player pages.
const fs=require('node:fs'),path=require('node:path');
const root=path.resolve(__dirname,'..');
const read=name=>fs.readFileSync(path.join(root,'src/misc/Player',name),'utf8');
const skin=read('video-js-skin-public.css');
for(const name of ['src/misc/Player/video-js-skin-public.min.css','public/_player/videojs/dist/video-js-skin.css','public/_player/videojs/dist/video-js-skin.min.css'])fs.writeFileSync(path.join(root,name),skin);
fs.writeFileSync(path.join(root,'src/misc/Player/video-js-skin-internal.min.css'),read('video-js-skin-internal.css'));

fs.writeFileSync(path.join(root,'public/_player/videojs/dist/timeline-markers.js'),read('timelineMarkers.js'));
