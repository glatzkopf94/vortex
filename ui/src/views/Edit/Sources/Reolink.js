import React from 'react';
import VideocamIcon from '@mui/icons-material/Videocam';
import { Button, MenuItem, Stack, TextField, Typography } from '@mui/material';

export const id = 'reolink';
export const name = 'Reolink-Kamera per UID';
export const capabilities = ['video'];
export const ffversion = '^9.0.0';
export const icon = VideocamIcon;
const empty = { id: '', name: '', uid: '', username: '', password: '' };
export const func = {
	initSettings: (settings) => ({ stream: 'main', ...settings }),
	createInputs: ({ id, port, stream }) => [
		{
			address: `rtsp://reolink:${port}/${id}/${stream}`,
			options: ['-rtsp_transport', 'tcp', '-timeout', '25000000', '-analyzeduration', '3000000', '-probesize', '8000000'],
		},
	],
};

export function CameraSource({ restreamer, settings = {}, onChange, onProbe, onPending }) {
	const [list, setList] = React.useState([]);
	const [camera, setCamera] = React.useState(empty);
	const [stream, setStream] = React.useState(settings.stream || 'main');
	const [busy, setBusy] = React.useState(false);
	const [message, setMessage] = React.useState('');
	const mounted = React.useRef(false);
	const initial = React.useRef(settings.id);
	const call = React.useCallback(
		async (path, body) => {
			const [result, error] = await restreamer._call(
				restreamer.api._call,
				body ? 'POST' : 'GET',
				'/v3/reolink/' + path,
				body ? { headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) } : {},
			);
			if (error) throw new Error(error.message || 'Empfangsdienst nicht erreichbar');
			return result;
		},
		[restreamer],
	);

	React.useEffect(() => {
		mounted.current = true;
		let active = true;
		call('cameras')
			.then(({ cameras }) => {
				if (!active) return;
				setList(cameras);
				setCamera({ ...empty, ...cameras.find((c) => c.id === initial.current) });
			})
			.catch((e) => {
				if (active) setMessage(e.message);
			});
		return () => {
			active = false;
			mounted.current = false;
		};
	}, [call]);

	function invalidate() {
		setMessage('');
		if (onPending) onPending();
		else onChange({});
	}
	function edit(key, value) {
		invalidate();
		setCamera({ ...camera, [key]: value });
	}
	async function check() {
		invalidate();
		setBusy(true);
		setMessage('Verbindung wird geprüft …');
		try {
			const saved = await call('save', camera);
			if (!mounted.current) return;
			setCamera({ ...empty, ...saved });
			setList((rows) => [...rows.filter((c) => c.id !== saved.id), saved]);
			const source = { id: saved.id, port: saved.port, stream };
			let job = await call('probe', source);
			const deadline = Date.now() + 420000;
			while (mounted.current && job.status === 'running' && Date.now() < deadline) {
				setMessage(job.message);
				await new Promise((resolve) => setTimeout(resolve, 900));
				if (!mounted.current) return;
				job = await call('status', { ...source, token: job.token });
			}
			if (!mounted.current) return;
			if (job.status !== 'ok') throw new Error(job.status === 'running' ? 'Zeitlimit der Prüfung erreicht' : job.message);
			const inputs = func.createInputs(source);
            if (job.token) {
                restreamer.uidProbeTokens ??= new Map();
                restreamer.uidProbeTokens.set(inputs[0].address, { ...source, token: job.token });
            }
            setMessage('Bildprüfung am Empfänger · ' + job.message);
			onChange(source);
			if (onProbe) {
                const ok = await onProbe(source, inputs);
                if (mounted.current) setMessage(ok ? job.message + ' · Vortex-Quelle bestätigt' : 'Vortex-Quellprüfung fehlgeschlagen · siehe Prüfdetails');
            }
		} catch (e) {
			if (mounted.current) setMessage(e.message);
		} finally {
			if (mounted.current) setBusy(false);
		}
	}
	return (
		<Stack spacing={2}>
			<TextField
				select
				disabled={busy}
				label="Gespeicherte Kamera"
				value={camera.id}
				onChange={(e) => {
					invalidate();
					setCamera({ ...empty, ...list.find((c) => c.id === e.target.value) });
				}}
			>
				<MenuItem value="">Neue Kamera</MenuItem>
				{list.map((c) => (
					<MenuItem key={c.id} value={c.id}>
						{c.name}
					</MenuItem>
				))}
			</TextField>
			{[
				['name', 'Kameraname'],
				['uid', 'UID'],
				['username', 'Kamerabenutzer'],
				['password', 'Kamerapasswort'],
			].map(([key, label]) => (
				<TextField
					key={key}
					label={label}
					type={key === 'password' ? 'password' : 'text'}
					disabled={busy}
					autoComplete={key === 'password' ? 'new-password' : 'off'}
					value={camera[key]}
					InputLabelProps={camera.id && key === 'password' ? { shrink: true } : undefined}
					placeholder={camera.id && key === 'password' ? '••••••••' : ''}
					onChange={(e) => edit(key, e.target.value)}
				/>
			))}
			<TextField
				select
				disabled={busy}
				label="Stream"
				value={stream}
				onChange={(e) => {
					invalidate();
					setStream(e.target.value);
				}}
			>
				<MenuItem value="main">Hauptstream</MenuItem>
				<MenuItem value="sub">Substream</MenuItem>
			</TextField>
			<Button variant="outlined" disabled={busy || !camera.name || !camera.uid || !camera.username || (!camera.id && !camera.password)} onClick={check}>
				Quelle prüfen
			</Button>
			<Typography role="status">{message}</Typography>
		</Stack>
	);
}
export { CameraSource as component };
