import React from 'react';
import Grid from '@mui/material/Grid';
import { component as Camera, func, id } from '../../Sources/Reolink';
export { id, id as type, name, icon, capabilities } from '../../Sources/Reolink';
export function component({ onChange, ...props }) {
	return (
		<Grid item xs={12}>
			<Camera
				{...props}
				onPending={() => onChange(id, {}, [], false)}
				onChange={(settings) => onChange(id, settings, func.createInputs(settings), true)}
			/>
		</Grid>
	);
}
