import Restreamer, { countUniqueHLSViewers, getHLSSegmentCleanupAge, getIngestRTSPStability, getPlayerAspectRatio, isDVRChannelId } from './restreamer';
import { v4 as uuidv4 } from 'uuid';
import * as M from './metadata';

jest.mock('uuid', () => ({
	v4: jest.fn(),
}));

test('DVR cleanup has no independent nominal age limit', () => {
	expect(getHLSSegmentCleanupAge({ hls: { dvr: { enabled: true }, listSize: 7200, segmentDuration: 2 } })).toBe(0);
	expect(getHLSSegmentCleanupAge({ hls: { dvr: { enabled: false }, listSize: 6, segmentDuration: 2 } })).toBe(24);
});

test('standard RTSP keeps permissive decoder handling and reconnect choice', () => {
	expect(getIngestRTSPStability([], false)).toEqual({
		profile: 'standard',
		decoderErrorMode: 'ignore_err',
		exitOnError: false,
		reconnect: false,
	});
});

test('stable RTSP uses careful decoder handling without forcing reconnect', () => {
	expect(getIngestRTSPStability([{ livechasing: { rtspStability: 'stable' } }], false)).toEqual({
		profile: 'stable',
		decoderErrorMode: 'careful',
		exitOnError: false,
		reconnect: false,
	});
});

test('strict RTSP exits on decoder errors and always reconnects', () => {
	expect(getIngestRTSPStability([{ livechasing: { rtspStability: 'strict' } }], false)).toEqual({
		profile: 'strict',
		decoderErrorMode: 'explode',
		exitOnError: true,
		reconnect: true,
	});
});

test('player selects the nearest supported aspect ratio before playback', () => {
	expect(getPlayerAspectRatio({ streams: [{ type: 'video', width: 1920, height: 1080 }] })).toBe('16:9');
	expect(getPlayerAspectRatio({ streams: [{ type: 'video', width: 1440, height: 1080 }] })).toBe('4:3');
	expect(getPlayerAspectRatio({ streams: [{ type: 'audio', width: 0, height: 0 }] })).toBe('16:9');
	expect(getPlayerAspectRatio({ streams: [{ type: 'video', width: 640, height: 480 }] }, false)).toBe('16:9');
});

test('responsive iframe code is generated with the detected 4:3 geometry', () => {
	const context = {
		GetChannel: () => ({ channelid: 'camera-4x3' }),
		GetPublicHTTPAddress: () => 'https://stream.example.test',
	};
	const iframe = Restreamer.prototype.GetPublicIframeCode.call(context, 'camera-4x3', '4:3');

	expect(iframe).toContain('width="640" height="480"');
	expect(iframe).toContain('aspect-ratio:4 / 3');
});

test('new player bandwidth safeguards default to enabled', () => {
	const settings = Restreamer.prototype.InitPlayerSettings.call({}, {});
	expect(settings.playback).toEqual({
		autoAspectRatio: true,
		singleActiveStream: true,
		sessionLimitEnabled: true,
	});
});

test('global viewer count deduplicates one browser across all channels', () => {
	const browser = '[viewer:viewer-browser-0001] [192.0.2.0] Firefox';
	const sessions = {
		hls: [
			{ id: 'stream-a', reference: 'channel-a', extra: browser, bandwidth_tx_kbit: 4096 },
			{ id: 'stream-b', reference: 'channel-b', extra: browser, bandwidth_tx_kbit: 4096 },
			{ id: 'stream-c', reference: 'channel-c', extra: browser, bandwidth_tx_kbit: 0 },
		],
	};

	expect(countUniqueHLSViewers(sessions)).toBe(1);
});

test('global viewer count keeps different browsers separate and supports legacy players', () => {
	const sessions = {
		hls: [
			{ id: 'stream-a', extra: '[viewer:viewer-browser-0001] [192.0.2.0] Firefox', bandwidth_tx_kbit: 4096 },
			{ id: 'stream-b', extra: '[viewer:viewer-browser-0002] [192.0.2.0] Firefox', bandwidth_tx_kbit: 4096 },
			{ id: 'legacy-a', extra: '[198.51.100.0] Safari', bandwidth_tx_kbit: 2048 },
			{ id: 'legacy-b', extra: '[198.51.100.0] Safari', bandwidth_tx_kbit: 2048 },
		],
	};

	expect(countUniqueHLSViewers(sessions)).toBe(3);
});

test('DVR cleanup accepts only canonical channel IDs', () => {
	expect(isDVRChannelId('8672be5b-5a35-4a56-a970-877d7d728983')).toBe(true);
	expect(isDVRChannelId('../channels')).toBe(false);
	expect(isDVRChannelId('8672be5b-5a35-4a56-a970-877d7d728983/extra')).toBe(false);
});

test('DVR cleanup accepts the manager response after the file existence check', async () => {
	const channelId = '8672be5b-5a35-4a56-a970-877d7d728983';
	const requestId = '00000000-0000-4000-8000-000000000001';
	const dataHasFile = jest.fn();
	const dataGetFile = jest.fn();
	const dataPutFile = jest.fn();
	const dataDeleteFile = jest.fn();
	const context = {
		api: { DataHasFile: dataHasFile, DataGetFile: dataGetFile, DataPutFile: dataPutFile, DataDeleteFile: dataDeleteFile },
		_call: jest.fn(async (fn) => {
			if (fn === dataPutFile || fn === dataHasFile || fn === dataDeleteFile) return [null, null];
			if (fn === dataGetFile) return [{ ok: true, requestId, channelCount: 1, deletedFiles: 42 }, null];
			throw new Error('unexpected API call');
		}),
	};

	uuidv4.mockReturnValueOnce(requestId);
	const result = await Restreamer.prototype._requestDVRPurge.call(context, [channelId]);

	expect(result).toEqual({ ok: true, requestId, channelCount: 1, deletedFiles: 42 });
	expect(context._call).toHaveBeenCalledWith(dataHasFile, `/livechasing-control/responses/${requestId}.json`);
	expect(context._call).toHaveBeenCalledWith(dataGetFile, `/livechasing-control/responses/${requestId}.json`);
	expect(context._call).toHaveBeenCalledWith(dataDeleteFile, `/livechasing-control/requests/${requestId}.json`);
	expect(context._call).toHaveBeenCalledWith(dataDeleteFile, `/livechasing-control/responses/${requestId}.json`);
});

test('DVR cleanup pauses an active channel and restarts it after deletion', async () => {
	const channelId = '8672be5b-5a35-4a56-a970-877d7d728983';
	const context = {
		GetChannel: jest.fn(() => ({ channelid: channelId })),
		GetIngestProgress: jest.fn(async () => ({ order: 'start' })),
		StopIngest: jest.fn(async () => true),
		_waitForIngestStopped: jest.fn(async () => true),
		_requestDVRPurge: jest.fn(async () => ({ ok: true, channelCount: 1, deletedFiles: 42, freedBytes: 2048 })),
		StartIngest: jest.fn(async () => true),
	};

	const result = await Restreamer.prototype.PurgeDVRChannels.call(context, [channelId]);

	expect(result.success).toBe(true);
	expect(result.deletedFiles).toBe(42);
	expect(context.StopIngest).toHaveBeenCalledWith(channelId);
	expect(context._requestDVRPurge).toHaveBeenCalledWith([channelId]);
	expect(context.StartIngest).toHaveBeenCalledWith(channelId);
});

test('global DVR cleanup selects only DVR-enabled channels', async () => {
	const enabled = '8672be5b-5a35-4a56-a970-877d7d728983';
	const disabled = '2579719c-8d8b-4f59-a936-3048b181710b';
	const context = {
		ListChannels: () => [{ channelid: enabled }, { channelid: disabled }],
		GetIngestMetadata: jest.fn(async (channelId) => ({ control: { hls: { dvr: { enabled: channelId === enabled } } } })),
		PurgeDVRChannels: jest.fn(async () => ({ success: true })),
	};

	await Restreamer.prototype.PurgeAllDVR.call(context);

	expect(context.PurgeDVRChannels).toHaveBeenCalledWith([enabled]);
});

function hevcContext() {
 return {GetChannel:()=>({id:'restreamer-ui:ingest:camera',channelid:'camera'}),
 ConfigActive:()=>({source:{network:{rtmp:{enabled:false},srt:{enabled:false}}}}),
 GetPublicHTTPAddress:()=> 'https://test.example', SetChannel:jest.fn(),
 _upsertProcess:jest.fn(async()=>[{},null]), _startProcess:jest.fn(async()=>true), _stopProcess:jest.fn(async()=>true)};
}
function hevcControl(dvr=false) {
 return {hls:{storage:dvr?'diskfs':'memfs',version:3,lhls:false,master_playlist:true,segmentDuration:2,listSize:6,cleanup:true,dvr:{enabled:dvr,hours:4}},
 process:{autostart:true,reconnect:true,delay:2,staleTimeout:30},limits:{cpu_usage:0,memory_mbytes:0,waitfor_seconds:5},rtmp:{enable:false},srt:{enable:false},
 preview:{enable:true,fallbackOnly:true,height:720,bitrate:2048,video_encoder:'libx264',audio_encoder:'aac'}};
}
test('HEVC passthrough copies video to fMP4 with hvc1; AVC path remains TS', async()=>{
 for(const codec of ['hevc','h264']) {
  const ctx=hevcContext(), control=hevcControl(true);
  const [,err]=await Restreamer.prototype.UpsertIngest.call(ctx,'camera',[],[{address:'rtsp://test/live',options:[]}],[{videoCodec:codec,options:['-map','0:v:0','-codec:v','copy','-an']}],control);
  expect(err).toBeNull();
  const proc=ctx._upsertProcess.mock.calls[0][1], out=proc.output[0];
  expect(out.options).toEqual(expect.arrayContaining(['-codec:v','copy']));
  expect(out.options.includes('fmp4')).toBe(codec==='hevc');
  if(codec==='hevc') {
   expect(out.options).toEqual(expect.arrayContaining(['-tag:v','hvc1']));
   expect(out.address).toMatch(/_hevc_\d+\.m3u8$/);
   expect(out.cleanup.find(c=>c.pattern.includes('_hevc_')&&c.pattern.endsWith('.mp4')&&!c.pattern.includes('*')).max_file_age_seconds).toBe(0);
  }
 }
});
test('fallback is reduced once per channel, has DVR when enabled and stops when disabled', async()=>{
 const ctx=hevcContext(), control=hevcControl(true);
 await Restreamer.prototype.UpsertIngestPreview.call(ctx,'camera',control);
 const out=ctx._upsertProcess.mock.calls[0][1].output[0];
 expect(out.address).toBe('{diskfs}/camera_output_0_h264.m3u8');
 expect(out.options).toEqual(expect.arrayContaining(['scale=-2:min(ih\\,720)','2048k','-hls_list_size','7200','-hls_max_window_duration','14400']));
 expect(ctx._startProcess).toHaveBeenCalledWith('restreamer-ui:ingest:camera_h264');
 control.preview.enable=false;
 await Restreamer.prototype.UpsertIngestPreview.call(ctx,'camera',control);
 expect(ctx._stopProcess).toHaveBeenCalledWith('restreamer-ui:ingest:camera_h264');
 expect(ctx._upsertProcess.mock.calls[1][1].autostart).toBe(false);
});

test('player configuration keeps the original and publishes optional fallback in its actual storage', async()=>{
 const ctx={InitPlayerSettings:Restreamer.prototype.InitPlayerSettings,GetChannelManifestPath:(id,storage)=>storage+'/'+id+'.m3u8',GetChannelPosterPath:()=>'',_uploadAssetData:jest.fn()};
 for(const enabled of [false,true]) {
  const control=hevcControl(true);control.preview.enable=enabled;
  await Restreamer.prototype.UpdatePlayerConfig.call(ctx,'camera',{player:{},control,streams:[{type:'video',codec:'hevc'}],license:'',meta:{name:'Test',author:{name:''}}});
  const config=JSON.parse(ctx._uploadAssetData.mock.calls.at(-1)[1].replace('var playerConfig = ',''));
  expect(config.source).toBe('diskfs/camera.m3u8');
  expect(config.videoCodec).toBe('hevc');
  expect(config.fallbackSource).toBe(enabled?'diskfs/camera_h264.m3u8':'');
 }
});

test('HEVC source defaults to passthrough and a new fallback is opt-in',()=>{
 const metadata=M.getDefaultIngestMetadata();
 expect(metadata.control.preview.enable).toBe(false);
 expect(metadata.control.preview.fallbackOnly).toBe(true);
 const profile=M.initProfile();
 const result=M.preselectProfile('video',[{type:'video',codec:'hevc',width:3840,height:2160}],profile,{video:['libx264'],audio:['aac']},false);
 expect(result.video.encoder.coder).toBe('copy');
});
