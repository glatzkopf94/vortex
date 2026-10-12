import React from 'react';

import VideoJS from './videojs';
import attachDVRMarkers from './dvrMarkers';

export default function Player({
	type = 'videojs-internal',
	source = '',
	poster = '',
	controls = false,
	autoplay = false,
	mute = false,
	ga = {
		account: '',
		name: '',
	},
	colors = {
		seekbar: '#fff',
		buttons: '#fff',
	},
	statistics = false,
	dvr = { enabled: false, hours: 0 },
	aspectRatio = '16:9',
}) {
	type = type ? type : 'videojs-internal';

	if (type === 'videojs-internal' || type === 'videojs-public') {
		const config = {
			controls: controls,
			poster: poster,
			autoplay: type === 'videojs-internal' ? true : autoplay ? (mute === 'muted' ? true : false) : false,
			muted: type === 'videojs-internal' ? 'muted' : mute,
			liveui: true,
			responsive: true,
			fluid: true,
			aspectRatio: aspectRatio === '4:3' ? '4:3' : '16:9',
			plugins: {
				reloadSourceOnError: {},
			},
			sources: [{ src: source, type: 'application/x-mpegURL' }],
		};

		return (
			<VideoJS
				type={type}
				options={config}
				onReady={(player) => {
					if (dvr && dvr.enabled) {
						player.addClass('vjs-live-dvr');
						if(type==='videojs-public') attachDVRMarkers(player,source);
					} else {
						player.addClass('vjs-live-no-dvr');
					}

					if (autoplay === true) {
						// https://videojs.com/blog/autoplay-best-practices-with-video-js/
						const p = player.play();

						if (!p) {
							// no autoplay;
						} else {
							p.then(
								() => {
									// autoplay worked;
								},
								() => {
									// autoplay did not work
								},
							);
						}
					}
				}}
			/>
		);
	}
}
