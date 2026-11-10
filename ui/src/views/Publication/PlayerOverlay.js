import React from 'react';

import { useLingui } from '@lingui/react';
import { Trans, t } from '@lingui/macro';
import Alert from '@mui/material/Alert';
import Box from '@mui/material/Box';
import Button from '@mui/material/Button';
import Grid from '@mui/material/Grid';
import MenuItem from '@mui/material/MenuItem';
import TextField from '@mui/material/TextField';
import Typography from '@mui/material/Typography';

import Checkbox from '../../misc/Checkbox';
import Select from '../../misc/Select';
import UploadButton from '../../misc/UploadButton';
import { flattenJSON, lookup, parseSources, removeSource, renderPreview, upsertSource, validSource, validSourceName } from './PlayerOverlayHelpers';

const logoTypes = [
	{ extension: 'png', mimetype: 'image/png', maxSize: 5 * 1024 * 1024 },
	{ extension: 'jpg', mimetype: 'image/jpeg', maxSize: 5 * 1024 * 1024 },
	{ extension: 'webp', mimetype: 'image/webp', maxSize: 5 * 1024 * 1024 },
];

function colorWithOpacity(color, opacity) {
	if (!/^#[0-9a-fA-F]{6}$/.test(color)) return 'transparent';
	const value = parseInt(color.slice(1), 16);
	const alpha = Math.min(1, Math.max(0, Number(opacity) || 0));
	return `rgba(${(value >> 16) & 255}, ${(value >> 8) & 255}, ${value & 255}, ${alpha})`;
}

function Position({ label, value, onChange }) {
	return (
		<Select fullWidth label={label} value={value} onChange={onChange}>
			<MenuItem value="top-left">
				<Trans>Top left</Trans>
			</MenuItem>
			<MenuItem value="top-center">
				<Trans>Top center</Trans>
			</MenuItem>
			<MenuItem value="top-right">
				<Trans>Top right</Trans>
			</MenuItem>
			<MenuItem value="bottom-left">
				<Trans>Bottom left</Trans>
			</MenuItem>
			<MenuItem value="bottom-center">
				<Trans>Bottom center</Trans>
			</MenuItem>
			<MenuItem value="bottom-right">
				<Trans>Bottom right</Trans>
			</MenuItem>
		</Select>
	);
}

function PlayerLogo({ number, settings, onChange, onStore, onStart, onError }) {
	const update = (what) => (event) =>
		onChange({
			...settings,
			[what]: what === 'enabled' ? !settings.enabled : event.target.value,
		});
	const handleUpload = async (data, extension) => {
		const path = await onStore(`playeroverlaylogo${number}.${extension}`, data);
		if (path) onChange({ ...settings, enabled: true, path });
	};

	return (
		<React.Fragment>
			<Grid item xs={12}>
				<Checkbox label={<Trans>Show player logo {number}</Trans>} checked={settings.enabled} onChange={update('enabled')} />
			</Grid>
			{settings.enabled && (
				<React.Fragment>
					<Grid item xs={12} md={4}>
						<UploadButton label={<Trans>Upload logo</Trans>} acceptTypes={logoTypes} onStart={onStart} onError={onError} onUpload={handleUpload} />
					</Grid>
					<Grid item xs={12} md={8}>
						<TextField fullWidth label={<Trans>Stored logo</Trans>} value={settings.path} InputProps={{ readOnly: true }} />
					</Grid>
					<Grid item xs={12} md={4}>
						<Position label={<Trans>Logo position</Trans>} value={settings.position} onChange={update('position')} />
					</Grid>
					<Grid item xs={6} md={2}>
						<TextField
							fullWidth
							type="number"
							inputProps={{ min: 16, max: 2000 }}
							label={<Trans>Logo width</Trans>}
							value={settings.width}
							onChange={update('width')}
						/>
					</Grid>
					<Grid item xs={6} md={2}>
						<TextField
							fullWidth
							type="number"
							inputProps={{ min: 0.05, max: 1, step: 0.05 }}
							label={<Trans>Opacity</Trans>}
							value={settings.opacity}
							onChange={update('opacity')}
						/>
					</Grid>
					<Grid item xs={12} md={4}>
						<TextField fullWidth label={<Trans>Optional link</Trans>} value={settings.link} onChange={update('link')} />
					</Grid>
				</React.Fragment>
			)}
		</React.Fragment>
	);
}

export default function PlayerOverlay({
	settings,
	onChange,
	onStore,
	onStart,
	onError,
	showToggle = true,
	showAppearance = true,
	showLogos = true,
	assistantType = 'player',
}) {
	const { i18n } = useLingui();
	const initialSource = parseSources(settings.sources)[0] || { name: 'wetter', url: '' };
	const [$sourceName, setSourceName] = React.useState(initialSource.name);
	const [$sourceURL, setSourceURL] = React.useState(initialSource.url);
	const [$testStatus, setTestStatus] = React.useState('idle');
	const [$testError, setTestError] = React.useState('');
	const [$fields, setFields] = React.useState([]);
	const [$payloads, setPayloads] = React.useState({});
	const [$preset, setPreset] = React.useState('');
	const [$fieldPath, setFieldPath] = React.useState('');
	const [$fieldLabel, setFieldLabel] = React.useState('');
	const [$fieldUnit, setFieldUnit] = React.useState('');
	const [$fieldDecimals, setFieldDecimals] = React.useState('');

	const update = (what) => (event) =>
		onChange({
			...settings,
			[what]: ['enabled', 'box'].includes(what) ? !settings[what] : event.target.value,
		});

	const storeSource = () => {
		const name = $sourceName.trim();
		const url = $sourceURL.trim();
		if (!validSource(name, url)) {
			setTestStatus('invalid');
			return false;
		}
		onChange({ ...settings, sources: upsertSource(settings.sources, name, url) });
		setTestStatus('saved');
		return true;
	};

	const deleteSource = (name) => () => {
		onChange({ ...settings, sources: removeSource(settings.sources, name) });
		if ($sourceName === name) {
			setSourceName('wetter');
			setSourceURL('');
			setFields([]);
		}
	};

	const editSource = (source) => () => {
		setSourceName(source.name);
		setSourceURL(source.url);
		setTestStatus('idle');
		setFields([]);
	};

	const testSource = async () => {
		const name = $sourceName.trim();
		const url = $sourceURL.trim();
		if (!validSource(name, url)) {
			setTestStatus('invalid');
			return;
		}

		onChange({ ...settings, sources: upsertSource(settings.sources, name, url) });
		setTestStatus('checking');
		setTestError('');
		const controller = new AbortController();
		const timeout = window.setTimeout(() => controller.abort(), 15000);
		try {
			const response = await fetch(url, {
				headers: { Accept: 'application/json' },
				cache: 'no-store',
				signal: controller.signal,
			});
			if (!response.ok) throw new Error(`HTTP ${response.status}`);
			const text = await response.text();
			if (text.length > 256 * 1024) throw new Error('JSON response exceeds 256 KiB');
			const payload = JSON.parse(text);
			const fields = flattenJSON(payload);
			setFields(fields);
			setPayloads((current) => ({ ...current, [name]: payload }));
			if (fields.length && !$fieldPath) setFieldPath(fields[0].path);
			setTestStatus('ok');
		} catch (error) {
			setTestError(error instanceof Error ? error.message : String(error));
			setTestStatus('failed');
		} finally {
			window.clearTimeout(timeout);
		}
	};

	const applyPreset = (event) => {
		const preset = event.target.value;
		setPreset(preset);
		if (!preset) return;
		const firstSource = parseSources(settings.sources)[0];
		const name = validSourceName($sourceName.trim()) ? $sourceName.trim() : firstSource?.name || 'wetter';
		let template = settings.template;
		if (preset === 'weather') template = `Temp: {{ ${name}.temperature_c | number:1 }} °C   F: {{ ${name}.humidity_pct | number:0 }} %`;
		if (preset === 'webcam-weather')
			template = `${i18n._(t`Webcam name – Location`)}\nTemp: {{ ${name}.temperature_c | number:1 }} °C   F: {{ ${name}.humidity_pct | number:0 }} %`;
		if (preset === 'webcam') template = i18n._(t`Webcam name – Location`);
		if (preset === 'sponsor') template = i18n._(t`Presented by: Sponsor`);
		if (preset === 'empty') template = '';

		let sources = settings.sources;
		if (validSource($sourceName.trim(), $sourceURL.trim())) sources = upsertSource(sources, $sourceName.trim(), $sourceURL.trim());
		onChange({ ...settings, sources, template });
	};

	const addField = () => {
		const name = $sourceName.trim();
		const path = $fieldPath.trim();
		if (!validSourceName(name) || !/^[A-Za-z0-9_.-]+$/.test(path)) return;
		const format = $fieldDecimals === '' ? '' : ` | number:${$fieldDecimals}`;
		const label = $fieldLabel.trim() ? `${$fieldLabel.trim()}: ` : '';
		const unit = $fieldUnit.trim() ? ` ${$fieldUnit.trim()}` : '';
		const element = `${label}{{ ${name}.${path}${format} }}${unit}`;
		const separator = settings.template && !settings.template.endsWith('\n') ? '   ' : '';
		onChange({ ...settings, template: `${settings.template}${separator}${element}` });
	};

	const sources = parseSources(settings.sources);
	const preview = renderPreview(settings.template, $payloads);
	const sourceTimestamp = lookup($payloads[$sourceName.trim()], 'updated_at');

	return (
		<div data-livechasing-overlay-assistant={assistantType === 'burnin' ? 'overlay-assistant-v2-burnin' : 'overlay-assistant-v2-player'}>
			<Grid container spacing={2}>
				{showToggle && (
					<Grid item xs={12}>
						<Checkbox label={<Trans>Enable resource-saving player overlay</Trans>} checked={settings.enabled} onChange={update('enabled')} />
						<Typography variant="caption" display="block">
							<Trans>
								Text, measurements and logos are placed over the web player without transcoding the video. They are not part of direct HLS/RTMP
								playback or recordings.
							</Trans>
						</Typography>
					</Grid>
				)}
				{(settings.enabled || !showToggle) && (
					<React.Fragment>
                        {assistantType !== 'burnin' && (
                            <Grid item xs={12}>
                                <Select fullWidth label="Player-Overlay im DVR anzeigen" value={Number(settings.dvrWindowMinutes) === 10 ? '10' : '5'} onChange={update('dvrWindowMinutes')}>
                                    <MenuItem value="5">Live und letzte 5 Minuten</MenuItem>
                                    <MenuItem value="10">Live und letzte 10 Minuten</MenuItem>
                                </Select>
                                <Typography variant="caption" display="block">
                                    Aktuelle Texte, Messwerte und Logos werden bei älteren DVR-Aufnahmen ausgeblendet. Eingebrannte Overlays und Zeitrafferbilder bleiben unverändert.
                                </Typography>
                            </Grid>
                        )}
						<Grid item xs={12}>
							<Typography variant="h4">
								<Trans>Overlay assistant</Trans>
							</Typography>
							<Alert severity="info">
								<Trans>
									Give the JSON source a short name, enter its HTTP(S) address and test it. Then choose a template or insert discovered fields
									into your own text.
								</Trans>
							</Alert>
						</Grid>
						<Grid item xs={12} md={3}>
							<TextField
								fullWidth
								label={<Trans>Source name</Trans>}
								value={$sourceName}
								onChange={(event) => setSourceName(event.target.value)}
								placeholder="wetter"
							/>
						</Grid>
						<Grid item xs={12} md={9}>
							<TextField
								fullWidth
								label={<Trans>JSON address</Trans>}
								value={$sourceURL}
								onChange={(event) => setSourceURL(event.target.value)}
								placeholder="https://example.org/environment.json"
							/>
						</Grid>
						<Grid item xs={12}>
							<Button variant="outlined" color="primary" onClick={storeSource} sx={{ mr: 1, mb: 1 }}>
								<Trans>Save source</Trans>
							</Button>
							<Button variant="outlined" color="primary" onClick={testSource} disabled={$testStatus === 'checking'} sx={{ mb: 1 }}>
								<Trans>Test JSON and find fields</Trans>
							</Button>
						</Grid>
						{$testStatus === 'invalid' && (
							<Grid item xs={12}>
								<Alert severity="error">
									<Trans>The source name must start with a letter and the address must begin with http:// or https://.</Trans>
								</Alert>
							</Grid>
						)}
						{$testStatus === 'saved' && (
							<Grid item xs={12}>
								<Alert severity="success">
									<Trans>The JSON source has been added. Save the settings to activate it.</Trans>
								</Alert>
							</Grid>
						)}
						{$testStatus === 'checking' && (
							<Grid item xs={12}>
								<Alert severity="info">
									<Trans>Checking the JSON source …</Trans>
								</Alert>
							</Grid>
						)}
						{$testStatus === 'ok' && (
							<Grid item xs={12}>
								<Alert severity="success">
									<Trans>JSON successfully checked. {`${$fields.length}`} usable fields were found.</Trans>
									{sourceTimestamp ? ` updated_at: ${sourceTimestamp}` : ''}
								</Alert>
							</Grid>
						)}
						{$testStatus === 'failed' && (
							<Grid item xs={12}>
								<Alert severity="warning">
									<Trans>
										The browser could not read the JSON source. A CORS restriction may be the cause; server-side updates can still work
										after saving.
									</Trans>{' '}
									{$testError}
								</Alert>
							</Grid>
						)}
						{sources.length > 0 && (
							<Grid item xs={12}>
								<Typography variant="subtitle1">
									<Trans>Configured sources</Trans>
								</Typography>
								{sources.map((source) => (
									<Box key={source.name} sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.5, overflowWrap: 'anywhere' }}>
										<Typography variant="body2" sx={{ flexGrow: 1 }}>
											<strong>{source.name}</strong> = {source.url}
										</Typography>
										<Button size="small" onClick={editSource(source)}>
											<Trans>Edit</Trans>
										</Button>
										<Button size="small" color="error" onClick={deleteSource(source.name)}>
											<Trans>Remove</Trans>
										</Button>
									</Box>
								))}
							</Grid>
						)}
						{$fields.length > 0 && (
							<Grid item xs={12}>
								<Typography variant="subtitle1">
									<Trans>Fields found in the JSON response</Trans>
								</Typography>
								<Box sx={{ maxHeight: 150, overflow: 'auto', p: 1, bgcolor: 'rgba(0,0,0,0.18)', borderRadius: 1 }}>
									{$fields.map((field) => (
										<Typography key={field.path} variant="body2" component="div">
											{field.path}: {String(field.value)}
										</Typography>
									))}
								</Box>
							</Grid>
						)}
						<Grid item xs={12} md={4}>
							<Select fullWidth label={<Trans>Quick template</Trans>} value={$preset} onChange={applyPreset}>
								<MenuItem value="">
									<Trans>Select …</Trans>
								</MenuItem>
								<MenuItem value="weather">
									<Trans>Temperature and humidity</Trans>
								</MenuItem>
								<MenuItem value="webcam-weather">
									<Trans>Webcam name and weather</Trans>
								</MenuItem>
								<MenuItem value="webcam">
									<Trans>Webcam name and location</Trans>
								</MenuItem>
								<MenuItem value="sponsor">
									<Trans>Sponsor text</Trans>
								</MenuItem>
								<MenuItem value="empty">
									<Trans>Empty custom template</Trans>
								</MenuItem>
							</Select>
						</Grid>
						<Grid item xs={12}>
							<Typography variant="subtitle1">
								<Trans>Insert a measurement field</Trans>
							</Typography>
						</Grid>
						<Grid item xs={12} md={4}>
							<TextField
								fullWidth
								label={<Trans>JSON field</Trans>}
								value={$fieldPath}
								onChange={(event) => setFieldPath(event.target.value)}
								placeholder="temperature_c"
								inputProps={{ list: 'lc-overlay-json-fields' }}
							/>
							<datalist id="lc-overlay-json-fields">
								{$fields.map((field) => (
									<option key={field.path} value={field.path} />
								))}
							</datalist>
						</Grid>
						<Grid item xs={12} md={3}>
							<TextField
								fullWidth
								label={<Trans>Label</Trans>}
								value={$fieldLabel}
								onChange={(event) => setFieldLabel(event.target.value)}
								placeholder="Temp"
							/>
						</Grid>
						<Grid item xs={6} md={2}>
							<TextField
								fullWidth
								label={<Trans>Unit</Trans>}
								value={$fieldUnit}
								onChange={(event) => setFieldUnit(event.target.value)}
								placeholder="°C"
							/>
						</Grid>
						<Grid item xs={6} md={2}>
							<Select
								fullWidth
								label={<Trans>Decimal places</Trans>}
								value={$fieldDecimals}
								onChange={(event) => setFieldDecimals(event.target.value)}
							>
								<MenuItem value="">
									<Trans>Unchanged</Trans>
								</MenuItem>
								<MenuItem value="0">0</MenuItem>
								<MenuItem value="1">1</MenuItem>
								<MenuItem value="2">2</MenuItem>
								<MenuItem value="3">3</MenuItem>
							</Select>
						</Grid>
						<Grid item xs={12} md={1}>
							<Button fullWidth variant="outlined" color="primary" onClick={addField} sx={{ minHeight: 56 }}>
								+
							</Button>
						</Grid>
						<Grid item xs={12}>
							<TextField
								multiline
								minRows={4}
								fullWidth
								label={<Trans>Overlay template</Trans>}
								value={settings.template}
								onChange={update('template')}
								placeholder={'Temp: {{ wetter.temperature_c | number:1 }} °C   F: {{ wetter.humidity_pct | number:0 }} %'}
								helperText={
									<Trans>
										Static text can be entered directly. Dynamic values use double braces: source.field and optionally number:0 to number:3.
									</Trans>
								}
							/>
						</Grid>
						<Grid item xs={12}>
							<Typography variant="subtitle1">
								<Trans>Live preview</Trans>
							</Typography>
							<Box
								component="pre"
								sx={{
									m: 0,
									p: 1.5,
									minHeight: 48,
									whiteSpace: 'pre-wrap',
									fontFamily: 'inherit',
									color: settings.fontColor,
									backgroundColor: settings.box ? colorWithOpacity(settings.boxColor, settings.boxOpacity) : 'transparent',
									border: '1px solid rgba(255,255,255,0.16)',
									borderRadius: 1,
								}}
							>
								{preview || '—'}
							</Box>
						</Grid>
						<Grid item xs={12} md={9}>
							<TextField
								multiline
								minRows={2}
								fullWidth
								label={<Trans>Expert mode: JSON sources</Trans>}
								value={settings.sources}
								onChange={update('sources')}
								placeholder="wetter=https://example.org/environment.json"
								helperText={<Trans>One source per line in the form name=URL. Lines beginning with # are comments.</Trans>}
							/>
						</Grid>
						<Grid item xs={12} md={3}>
							<TextField
								fullWidth
								type="number"
								inputProps={{ min: 15, max: 3600 }}
								label={<Trans>Update interval (seconds)</Trans>}
								value={settings.interval}
								onChange={update('interval')}
							/>
						</Grid>
						{showAppearance && (
							<React.Fragment>
								<Grid item xs={12}>
									<Typography variant="h4">
										<Trans>Appearance</Trans>
									</Typography>
								</Grid>
								<Grid item xs={12} md={4}>
									<Position label={<Trans>Text position</Trans>} value={settings.position} onChange={update('position')} />
								</Grid>
								<Grid item xs={6} md={2}>
									<TextField
										fullWidth
										type="number"
										inputProps={{ min: 8, max: 200 }}
										label={<Trans>Font size</Trans>}
										value={settings.fontSize}
										onChange={update('fontSize')}
									/>
								</Grid>
								<Grid item xs={6} md={3}>
									<Select fullWidth label={<Trans>Font family</Trans>} value={settings.font} onChange={update('font')}>
										<MenuItem value="sans">Sans</MenuItem>
										<MenuItem value="sans-bold">Sans Bold</MenuItem>
										<MenuItem value="serif">Serif</MenuItem>
										<MenuItem value="mono">Monospace</MenuItem>
									</Select>
								</Grid>
								<Grid item xs={12} md={3}>
									<TextField
										fullWidth
										type="color"
										label={<Trans>Text color</Trans>}
										value={settings.fontColor}
										onChange={update('fontColor')}
										InputLabelProps={{ shrink: true }}
									/>
								</Grid>
								<Grid item xs={12}>
									<Checkbox label={<Trans>Draw translucent background box</Trans>} checked={settings.box} onChange={update('box')} />
								</Grid>
								{settings.box && (
									<React.Fragment>
										<Grid item xs={6} md={3}>
											<TextField
												fullWidth
												type="color"
												label={<Trans>Background color</Trans>}
												value={settings.boxColor}
												onChange={update('boxColor')}
												InputLabelProps={{ shrink: true }}
											/>
										</Grid>
										<Grid item xs={6} md={3}>
											<TextField
												fullWidth
												type="number"
												inputProps={{ min: 0, max: 1, step: 0.05 }}
												label={<Trans>Background opacity</Trans>}
												value={settings.boxOpacity}
												onChange={update('boxOpacity')}
											/>
										</Grid>
									</React.Fragment>
								)}
							</React.Fragment>
						)}
						{showLogos && (
							<React.Fragment>
								<Grid item xs={12}>
									<Typography variant="h4">
										<Trans>Player logos without transcoding</Trans>
									</Typography>
								</Grid>
								<PlayerLogo
									number={1}
									settings={settings.logo1}
									onChange={(logo1) => onChange({ ...settings, logo1 })}
									onStore={onStore}
									onStart={onStart}
									onError={onError}
								/>
								<PlayerLogo
									number={2}
									settings={settings.logo2}
									onChange={(logo2) => onChange({ ...settings, logo2 })}
									onStore={onStore}
									onStart={onStart}
									onError={onError}
								/>
							</React.Fragment>
						)}
					</React.Fragment>
				)}
			</Grid>
		</div>
	);
}
