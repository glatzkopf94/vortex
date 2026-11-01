import Restreamer from './restreamer';

const id = '1a4bad70-0e9c-410a-84d9-10d1752f5065';
function context() {
 const c = { channelid: id, id: `restreamer-ui:ingest:${id}`, egresses: ['publication'] };
 return {
  GetChannel: () => c, channels: new Map([[id, c], ['other', { channelid: 'other' }]]),
  StopAllEgresses: jest.fn(), DeleteEgress: jest.fn().mockResolvedValue(true),
  DeleteIngestSnapshot: jest.fn().mockResolvedValue(true), DeleteIngest: jest.fn().mockResolvedValue(true),
  SelectChannel: jest.fn(),
 };
}
test.each(['DeleteEgress', 'DeleteIngestSnapshot', 'DeleteIngest'])('failed %s keeps channel visible for retry', async method => {
 const c = context(); c[method].mockResolvedValue(false);
 expect(await Restreamer.prototype.DeleteChannel.call(c, id)).toBe(false);
 expect(c.channels.has(id)).toBe(true);
 if (method !== 'DeleteIngest') expect(c.DeleteIngest).not.toHaveBeenCalled();
});
test('channel disappears only after deleting all its processes', async () => {
 const c = context();
 expect(await Restreamer.prototype.DeleteChannel.call(c, id)).toBe(true);
 expect(c.channels.has(id)).toBe(false);
 expect(c.DeleteEgress).toHaveBeenCalledWith(id, 'publication');
 expect(c.DeleteIngest.mock.invocationCallOrder[0]).toBeGreaterThan(c.DeleteIngestSnapshot.mock.invocationCallOrder[0]);
});
test('failed fallback deletion preserves the main ingest', async () => {
 const c = context(); c._deleteProcess = jest.fn().mockResolvedValue(false);
 expect(await Restreamer.prototype.DeleteIngest.call(c, id)).toBe(false);
 expect(c._deleteProcess).toHaveBeenCalledTimes(1);
 expect(c._deleteProcess).toHaveBeenCalledWith(`restreamer-ui:ingest:${id}_h264`);
});
test('deleting an egress of a nonselected channel updates the correct channel', async () => {
 const c = context();
 c.channels.get(id).egresses = new Map([['publication', {}]]);
 c.GetChannel = () => ({ channelid: id, egresses: ['publication'] });
 c.channel = { egresses: new Map([['publication', {}]]) };
 c._deleteProcess = jest.fn().mockResolvedValue(true);
 expect(await Restreamer.prototype.DeleteEgress.call(c, id, 'publication')).toBe(true);
 expect(c.channels.get(id).egresses.size).toBe(0);
 expect(c.channel.egresses.size).toBe(1);
});
test.each(['', 'stale-reference'])('canonical main ingest remains visible with reference %s', async reference => {
 const c = {
  _listProcesses: jest.fn().mockResolvedValue([{ id: `restreamer-ui:ingest:${id}`, reference, metadata: {} }, { id: `restreamer-ui:ingest:${id}_h264`, reference: id, metadata: {} }]),
  ID: () => 'test-instance', SelectChannel: jest.fn(), CreateChannel: jest.fn(),
 };
 await Restreamer.prototype._discoverChannels.call(c);
 expect(c.channels.size).toBe(1);
 expect(c.channels.get(id).name).toBe(id);
 expect(c.CreateChannel).not.toHaveBeenCalled();
});

test('resource CPU excludes I/O wait and exposes it separately', async () => {
 const c = {
  api: { Metrics: 'metrics', ActiveSessions: 'sessions' },
  _call: jest.fn().mockResolvedValueOnce([{ metrics: [
   { name: 'cpu_idle', values: [[0, 1]] }, { name: 'cpu_iowait', values: [[0, 97]] },
  ] }, null]).mockResolvedValueOnce([{ hls: [] }, null]),
 };
 const result = await Restreamer.prototype._getResources.call(c);
 expect(result.system.cpu_used).toBe(2);
 expect(result.system.cpu_iowait).toBe(97);
});

test('opening the channel list reconciles server processes and preserves unsaved drafts', async () => {
 const c = {
  api: { Processes: 'processes' },
  _call: jest.fn().mockResolvedValue([[{ id: `restreamer-ui:ingest:${id}`, reference: id, metadata: {} }], null]),
  _sanitizeProcess: process => process,
  _discoverChannels: Restreamer.prototype._discoverChannels,
  channels: new Map([['draft', { available: false, name: 'Unsaved' }], ['removed', { available: true }]]),
  ID: () => 'refresh-test', SelectChannel: jest.fn(), CreateChannel: jest.fn(),
 };
 expect(await Restreamer.prototype.RefreshChannels.call(c)).toBe(true);
 expect([...c.channels.keys()]).toEqual([id, 'draft']);
});
test('channel refresh on API failure preserves the current registry', async () => {
 const channels = new Map([['existing', { available: true }]]);
 const c = { api: { Processes: 'processes' }, _call: jest.fn().mockResolvedValue([null, { message: 'offline' }]), channels, _discoverChannels: jest.fn() };
 expect(await Restreamer.prototype.RefreshChannels.call(c)).toBe(false);
 expect(c.channels).toBe(channels);
 expect(c._discoverChannels).not.toHaveBeenCalled();
});
