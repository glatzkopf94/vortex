import { createGraph } from './Resample';

test.each([undefined, null, '', 'undefined', 'null', 'auto', 'inherit'])('unknown audio properties %s inherit from input', value => {
 expect(createGraph({ sampling: value, layout: value })).toBe('');
});
test('known audio properties are preserved independently', () => {
 expect(createGraph({ sampling: 8000, layout: 'mono' })).toBe('aresample=osr=8000:ochl=mono');
 expect(createGraph({ sampling: undefined, layout: 'stereo' })).toBe('aresample=ochl=stereo');
 expect(createGraph({ sampling: '48000', layout: undefined })).toBe('aresample=osr=48000');
 expect(createGraph({})).toBe('aresample=osr=44100:ochl=stereo');
});
