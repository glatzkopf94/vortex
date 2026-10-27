import React from 'react';

import { Trans } from '@lingui/macro';
import Grid from '@mui/material/Grid';
import MenuItem from '@mui/material/MenuItem';
import Typography from '@mui/material/Typography';
import TextField from '@mui/material/TextField';

import * as Encoders from '../coders/Encoders';
import Checkbox from '../Checkbox';
import Select from '../Select';

function init(settings) {
	const initSettings = {
		enable: false,
		fallbackOnly: true,
		height: 720,
		bitrate: 2048,
		video_encoder: 'libx264',
		audio_encoder: 'aac',
		...settings,
	};

	return initSettings;
}

export default function Control({ settings = {}, availableEncoders = [], onChange = function (settings, automatic) {} }) {
	settings = init(settings);

	// Set the defaults
	React.useEffect(() => {
		onChange(settings, true);
		// eslint-disable-next-line react-hooks/exhaustive-deps
	}, []);

	const handleChange = (what) => (event) => {
		const value = event.target.value;

		if (['enable', 'fallbackOnly'].includes(what)) {
			settings[what] = !settings[what];
		} else {
			settings[what] = value;
		}

		onChange(settings, false);
	};

	const encoders = Encoders.Video.GetCodersForCodec('h264', availableEncoders, 'any');

	return (
		<Grid container spacing={2}>
			<Grid item xs={12}>
				<Checkbox label="H.264-Substream aus der Hauptquelle erzeugen" checked={settings.enable} onChange={handleChange('enable')} />
				<Typography variant="caption" display="block">Der Hauptstream bleibt unverändert. Bei Aktivierung wird ein zusätzlicher Stream einmal pro Kanal umkodiert. Dies benötigt CPU und bei DVR zusätzlichen Speicher.</Typography>
			</Grid>
			<Grid item xs={12}>
				<Checkbox label="Nur als Fallback bei fehlender Browserunterstützung verwenden" checked={settings.fallbackOnly} disabled={!settings.enable} onChange={handleChange('fallbackOnly')} />
				<Typography variant="caption" display="block">H.265 benötigt Passthrough im Videoprofil. HLS/fMP4 wird beim Speichern automatisch gesetzt. Ohne Fallback benötigen Zuschauer einen passenden HEVC-Decoder.</Typography>
			</Grid>
			<Grid item xs={12} md={6}>
				<Select label="Maximale Fallback-Höhe" value={settings.height} disabled={!settings.enable || !settings.fallbackOnly} onChange={handleChange('height')}>
					{[360,480,720,1080,1440].map((height) => <MenuItem key={height} value={height}>{height}p</MenuItem>)}
				</Select>
			</Grid>
			<Grid item xs={12} md={6}>
				<TextField fullWidth label="Fallback-Bitrate (kbit/s)" type="number" value={settings.bitrate} disabled={!settings.enable || !settings.fallbackOnly} onChange={handleChange('bitrate')} inputProps={{min:256,max:12000}} helperText="Seitenverhältnis bleibt erhalten; kein Hochskalieren. Ausgabe mit 25 fps." />
			</Grid>
			<Grid item xs={12} md={6}>
				<Select label={<Trans>Video Codec</Trans>} value={settings.video_encoder} disabled={!settings.enable || settings.fallbackOnly} onChange={handleChange('video_encoder')}>
					{encoders.map((encoder) => (
						<MenuItem key={encoder.coder} value={encoder.coder}>
							{encoder.name}
						</MenuItem>
					))}
				</Select>
				<Typography variant="caption">
					<Trans>The H.264 encoder used.</Trans>
				</Typography>
			</Grid>
		</Grid>
	);
}
