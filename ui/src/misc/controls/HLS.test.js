import React from 'react';
import { fireEvent } from '@testing-library/react';

import Control, { applyDVRSettings } from './HLS';
import { render, screen } from '../../utils/testing';

test('DVR enforces persistent storage, cleanup and the configured time window', () => {
	const settings = applyDVRSettings(
		{
			dvr: { enabled: true, hours: 1 },
			storage: 'memfs',
			cleanup: false,
			segmentDuration: 2,
			listSize: 6,
		},
		4,
	);

	expect(settings.storage).toBe('diskfs');
	expect(settings.cleanup).toBe(true);
	expect(settings.segmentDuration).toBe(2);
	expect(settings.listSize).toBe(7200);
	expect(settings.dvr).toEqual({ enabled: true, hours: 4 });
});

test('DVR duration and segment length are clamped to safe bounds', () => {
	const settings = applyDVRSettings({ dvr: { enabled: true }, segmentDuration: 100 }, 500);
	expect(settings.segmentDuration).toBe(30);
	expect(settings.dvr.hours).toBe(168);
	expect(settings.listSize).toBe(20160);
});

test.each([
	[2, 3600],
	[3, 5400],
	[6, 10800],
])('DVR keeps %i hours as %i two-second segments', (hours, expectedListSize) => {
	const settings = applyDVRSettings({ dvr: { enabled: true, hours }, segmentDuration: 2 }, hours);

	expect(settings.storage).toBe('diskfs');
	expect(settings.dvr.hours).toBe(hours);
	expect(settings.segmentDuration).toBe(2);
	expect(settings.listSize).toBe(expectedListSize);
});

test('disabled DVR leaves ordinary HLS settings unchanged', () => {
	const settings = { dvr: { enabled: false }, storage: 'memfs', listSize: 6 };
	expect(applyDVRSettings(settings, 4)).toBe(settings);
});

test('enabled DVR offers the channel cleanup action', () => {
	const onPurgeDVR = jest.fn();
	render(<Control settings={{ dvr: { enabled: true, hours: 4 }, segmentDuration: 2 }} dvrMaxHours={4} onChange={() => {}} onPurgeDVR={onPurgeDVR} />);

	fireEvent.click(screen.getByRole('button', { name: 'Delete DVR content' }));
	expect(onPurgeDVR).toHaveBeenCalledTimes(1);
});

test('disabling DVR resets disk retention to six memory segments', () => {
 const onChange = jest.fn();
 render(<Control settings={{ dvr: { enabled: true, hours: 3 }, storage: 'diskfs', listSize: 5400, segmentDuration: 2 }} dvrMaxHours={3} onChange={onChange} />);
 fireEvent.click(screen.getByRole('checkbox', { name: 'Enable DVR rewind' }));
 expect(onChange).toHaveBeenLastCalledWith(expect.objectContaining({ storage: 'memfs', listSize: 6, cleanup: true, dvr: { enabled: false, hours: 3 } }), false);
});

test('ordinary disk HLS is preserved when opening settings with DVR already off', () => {
 const onChange = jest.fn();
 render(<Control settings={{ dvr: { enabled: false }, storage: 'diskfs', listSize: 12 }} onChange={onChange} />);
 expect(onChange).toHaveBeenLastCalledWith(expect.objectContaining({ storage: 'diskfs', listSize: 12 }), true);
});
