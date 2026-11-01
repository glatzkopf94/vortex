import React from 'react';

import { Trans } from '@lingui/macro';
import Button from '@mui/material/Button';
import Grid from '@mui/material/Grid';
import MenuItem from '@mui/material/MenuItem';
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';

import Checkbox from '../Checkbox';
import Select from '../Select';

function init(settings) {
	const initSettings = {
		lhls: false,
		segmentDuration: 2,
		listSize: 6,
		cleanup: true,
		version: 3,
		storage: 'memfs',
		master_playlist: true,
		dvr: {
			enabled: false,
			hours: 4,
		},
		...settings,
	};
	initSettings.dvr = {
		enabled: false,
		hours: 4,
		...(settings.dvr || {}),
	};

	return initSettings;
}

function applyDVRSettings(candidate, dvrMaxHours = 4) {
	if (!candidate.dvr.enabled) return candidate;
	const maxHours = Math.min(168, Math.max(1, parseInt(dvrMaxHours, 10) || 4));
	const segmentDuration = Math.min(30, Math.max(1, parseInt(candidate.segmentDuration, 10) || 2));
	return {
		...candidate,
		storage: 'diskfs',
		cleanup: true,
		segmentDuration,
		listSize: Math.ceil((maxHours * 3600) / segmentDuration),
		dvr: { enabled: true, hours: maxHours },
	};
}

export default function Control({ settings = {}, dvrMaxHours = 4, onChange = function (settings, automatic) {}, onPurgeDVR = null, purging = false }) {
	settings = init(settings);
	const maxHours = Math.min(168, Math.max(1, parseInt(dvrMaxHours, 10) || 4));

	// Set the defaults
	React.useEffect(() => {
		onChange(applyDVRSettings(settings, maxHours), true);
		// eslint-disable-next-line react-hooks/exhaustive-deps
	}, []);

	const handleChange = (what) => (event) => {
		const value = event.target.value;

		if (what === 'dvr') {
			settings.dvr = { enabled: !settings.dvr.enabled, hours: maxHours };
			if (!settings.dvr.enabled) {
				// DVR overrides these values; return explicitly to bounded live buffering.
				settings.storage = 'memfs';
				settings.listSize = 6;
				settings.cleanup = true;
			}
		} else if (['lhls', 'cleanup', 'master_playlist'].includes(what)) {
			settings[what] = !settings[what];
		} else {
			settings[what] = value;
		}

		onChange(applyDVRSettings(settings, maxHours), false);
	};

	return (
		<Grid container spacing={2}>
			<Grid item xs={12}>
				<Checkbox label={<Trans>Enable DVR rewind</Trans>} checked={settings.dvr.enabled} onChange={handleChange('dvr')} />
				<Typography variant="caption" display="block">
					<Trans>The administrator allows up to {maxHours} hours. DVR always uses persistent disk storage and automatic cleanup.</Trans>
				</Typography>
				{settings.dvr.enabled && (
					<React.Fragment>
						<Typography variant="caption" color="secondary" display="block">
							<Trans>
								This stream retains approximately {maxHours} hours and creates{' '}
								{Math.ceil((maxHours * 3600) / (parseInt(settings.segmentDuration, 10) || 2))} HLS segments.
							</Trans>
						</Typography>
						{typeof onPurgeDVR === 'function' && (
							<React.Fragment>
								<Button variant="outlined" color="secondary" disabled={purging} onClick={onPurgeDVR} sx={{ mt: 1 }}>
									<Trans>Delete DVR content</Trans>
								</Button>
								<Typography variant="caption" display="block">
									<Trans>Deletes the stored rewind history without changing the channel or DVR settings.</Trans>
								</Typography>
							</React.Fragment>
						)}
					</React.Fragment>
				)}
			</Grid>
			{/*
				lhls problems:
				- naming of the manifests and media files does not work
				- segmentation of audio and video creates a playback error
				- hls inputs requires encoding
				- have to wait for the final integration in hls.js

				<Grid item xs={12}>
					<Checkbox label={<Trans>Low latency Mode (LHLS/CMAF)</Trans>} checked={settings.lhls} onChange={handleChange('lhls')} />
					<Typography variant="caption">
						<Trans>Experimental function. Older browsers and clients may not be supported.</Trans>
					</Typography>
				</Grid>
			*/}
			<Grid item xs={12}>
				<Select
					label={<Trans>Storage</Trans>}
					value={settings.dvr.enabled ? 'diskfs' : settings.storage}
					disabled={settings.dvr.enabled}
					onChange={handleChange('storage')}
				>
					<MenuItem value="memfs">
						<Trans>In-memory</Trans>
					</MenuItem>
					<MenuItem value="diskfs">
						<Trans>Disk</Trans>
					</MenuItem>
				</Select>
				<Typography variant="caption">
					<Trans>Where to store the HLS playlist and segments. In-Memory is recommended.</Trans>
				</Typography>
			</Grid>
			<Grid item xs={12}>
				<Select label={<Trans>EXT-X-VERSION</Trans>} value={settings.version} onChange={handleChange('version')}>
					<MenuItem value={3}>3</MenuItem>
					<MenuItem value={6}>
						<Trans>6 (+ guaranteed to start with a Key frame)</Trans>
					</MenuItem>
					<MenuItem value={7}>
						<Trans>7 (+ fragmented MP4 format)</Trans>
					</MenuItem>
				</Select>
				<Typography variant="caption">
					<Trans>Playlist version (M3U8). Version 3 has the best browser/client compatibility.</Trans>
				</Typography>
			</Grid>
			<Grid item xs={12} md={6}>
				<TextField
					variant="outlined"
					fullWidth
					label={<Trans>Segment length (seconds)</Trans>}
					value={settings.segmentDuration}
					onChange={handleChange('segmentDuration')}
				/>
				<Typography variant="caption">
					<Trans>Segment will be cut on the following keyframe after this time has passed. 2 is recommended.</Trans>
				</Typography>
			</Grid>
			<Grid item xs={12} md={6}>
				<TextField
					variant="outlined"
					fullWidth
					label={<Trans>List size (segments)</Trans>}
					value={settings.dvr.enabled ? Math.ceil((maxHours * 3600) / (parseInt(settings.segmentDuration, 10) || 2)) : settings.listSize}
					disabled={settings.dvr.enabled}
					onChange={handleChange('listSize')}
				/>
				<Typography variant="caption">
					<Trans>The maximum number of playlist segments. 0 will contain all the segments. 6 is recommended.</Trans>
				</Typography>
			</Grid>
			<Grid item xs={12}>
				<Checkbox
					label={<Trans>Master playlist (increases browser/client compatibility)</Trans>}
					checked={settings.master_playlist}
					onChange={handleChange('master_playlist')}
				/>
			</Grid>
			<Grid item xs={12}>
				<Checkbox
					label={<Trans>Automatic cleanup of all media data</Trans>}
					checked={settings.dvr.enabled ? true : settings.cleanup}
					disabled={settings.dvr.enabled}
					onChange={handleChange('cleanup')}
				/>
			</Grid>
		</Grid>
	);
}

export { applyDVRSettings };
