// Modified 2026-10-10 by Alexander / Nistkasten Livestream: Vortex UI branding.
import { i18n } from '@lingui/core';

const topics = {
	'edit-general': {
		en: 'https://github.com/glatzkopf94/vortex/blob/main/README.md',
		de: 'https://github.com/glatzkopf94/vortex/blob/main/README.md',
	},
	'edit-control': {
		en: 'https://github.com/glatzkopf94/vortex/blob/main/README.md',
		de: 'https://github.com/glatzkopf94/vortex/blob/main/README.md',
	},
	'edit-meta': {
		en: 'https://github.com/glatzkopf94/vortex/blob/main/README.md',
		de: 'https://github.com/glatzkopf94/vortex/blob/main/README.md',
	},
	'edit-license': {
		en: 'https://github.com/glatzkopf94/vortex/blob/main/README.md',
		de: 'https://github.com/glatzkopf94/vortex/blob/main/README.md',
	},
	login: {
		en: 'https://github.com/glatzkopf94/vortex/blob/main/README.md',
		de: 'https://github.com/glatzkopf94/vortex/blob/main/README.md',
	},
	main: {
		en: 'https://github.com/glatzkopf94/vortex/blob/main/README.md',
		de: 'https://github.com/glatzkopf94/vortex/blob/main/README.md',
	},
	'player-embed': {
		en: 'https://github.com/glatzkopf94/vortex/blob/main/README.md',
		de: 'https://github.com/glatzkopf94/vortex/blob/main/README.md',
	},
	'player-colors': {
		en: 'https://github.com/glatzkopf94/vortex/blob/main/README.md',
		de: 'https://github.com/glatzkopf94/vortex/blob/main/README.md',
	},
	'player-logo': {
		en: 'https://github.com/glatzkopf94/vortex/blob/main/README.md',
		de: 'https://github.com/glatzkopf94/vortex/blob/main/README.md',
	},
	'player-statistic': {
		en: 'https://github.com/glatzkopf94/vortex/blob/main/README.md',
		de: 'https://github.com/glatzkopf94/vortex/blob/main/README.md',
	},
	'player-playback': {
		en: 'https://github.com/glatzkopf94/vortex/blob/main/README.md',
		de: 'https://github.com/glatzkopf94/vortex/blob/main/README.md',
	},
	'player-poster': {
		en: 'https://github.com/glatzkopf94/vortex/blob/main/README.md',
		de: 'https://github.com/glatzkopf94/vortex/blob/main/README.md',
	},
	'playersite-general': {
		en: 'https://github.com/glatzkopf94/vortex/blob/main/README.md',
		de: 'https://github.com/glatzkopf94/vortex/blob/main/README.md',
	},
	'playersite-template': {
		en: 'https://github.com/glatzkopf94/vortex/blob/main/README.md',
		de: 'https://github.com/glatzkopf94/vortex/blob/main/README.md',
	},
	'playersite-design': {
		en: 'https://github.com/glatzkopf94/vortex/blob/main/README.md',
		de: 'https://github.com/glatzkopf94/vortex/blob/main/README.md',
	},
	'playersite-notes': {
		en: 'https://github.com/glatzkopf94/vortex/blob/main/README.md',
		de: 'https://github.com/glatzkopf94/vortex/blob/main/README.md',
	},
	'playersite-code_injection': {
		en: 'https://github.com/glatzkopf94/vortex/blob/main/README.md',
		de: 'https://github.com/glatzkopf94/vortex/blob/main/README.md',
	},
	'process-details': {
		en: 'https://github.com/glatzkopf94/vortex/blob/main/README.md',
		de: 'https://github.com/glatzkopf94/vortex/blob/main/README.md',
	},
	'process-report': {
		en: 'https://github.com/glatzkopf94/vortex/blob/main/README.md',
		de: 'https://github.com/glatzkopf94/vortex/blob/main/README.md',
	},
	publication: {
		en: 'https://github.com/glatzkopf94/vortex/blob/main/README.md',
		de: 'https://github.com/glatzkopf94/vortex/blob/main/README.md',
	},
	'publication-add': {
		en: 'https://github.com/glatzkopf94/vortex/blob/main/README.md',
		de: 'https://github.com/glatzkopf94/vortex/blob/main/README.md',
	},
	'publication-general': {
		en: 'https://github.com/glatzkopf94/vortex/blob/main/README.md',
		de: 'https://github.com/glatzkopf94/vortex/blob/main/README.md',
	},
	'publication-process': {
		en: 'https://github.com/glatzkopf94/vortex/blob/main/README.md',
		de: 'https://github.com/glatzkopf94/vortex/blob/main/README.md',
	},
	'publication-encoding': {
		en: 'https://github.com/glatzkopf94/vortex/blob/main/README.md',
		de: 'https://github.com/glatzkopf94/vortex/blob/main/README.md',
	},
	'settings-general': {
		en: 'https://github.com/glatzkopf94/vortex/blob/main/README.md',
		de: 'https://github.com/glatzkopf94/vortex/blob/main/README.md',
	},
	'settings-update-link': {
		en: 'https://github.com/glatzkopf94/vortex/releases',
		de: 'https://github.com/glatzkopf94/vortex/releases',
	},
	'settings-service': {
		en: 'https://github.com/glatzkopf94/vortex/blob/main/README.md',
		de: 'https://github.com/glatzkopf94/vortex/blob/main/README.md',
	},
	'settings-network': {
		en: 'https://github.com/glatzkopf94/vortex/blob/main/README.md',
		de: 'https://github.com/glatzkopf94/vortex/blob/main/README.md',
	},
	'settings-auth': {
		en: 'https://github.com/glatzkopf94/vortex/blob/main/README.md',
		de: 'https://github.com/glatzkopf94/vortex/blob/main/README.md',
	},
	'settings-playback': {
		en: 'https://github.com/glatzkopf94/vortex/blob/main/README.md',
		de: 'https://github.com/glatzkopf94/vortex/blob/main/README.md',
	},
	'settings-storage': {
		en: 'https://github.com/glatzkopf94/vortex/blob/main/README.md',
		de: 'https://github.com/glatzkopf94/vortex/blob/main/README.md',
	},
	'settings-rtmp': {
		en: 'https://github.com/glatzkopf94/vortex/blob/main/README.md',
		de: 'https://github.com/glatzkopf94/vortex/blob/main/README.md',
	},
	'settings-srt': {
		en: 'https://github.com/glatzkopf94/vortex/blob/main/README.md',
		de: 'https://github.com/glatzkopf94/vortex/blob/main/README.md',
	},
	'settings-logging': {
		en: 'https://github.com/glatzkopf94/vortex/blob/main/README.md',
		de: 'https://github.com/glatzkopf94/vortex/blob/main/README.md',
	},
	'wizard-video-setup': {
		en: 'https://github.com/glatzkopf94/vortex/blob/main/README.md',
		de: 'https://github.com/glatzkopf94/vortex/blob/main/README.md',
	},
	'wizard-video-settings': {
		en: 'https://github.com/glatzkopf94/vortex/blob/main/README.md',
		de: 'https://github.com/glatzkopf94/vortex/blob/main/README.md',
	},
	'wizard-video-result': {
		en: 'https://github.com/glatzkopf94/vortex/blob/main/README.md',
		de: 'https://github.com/glatzkopf94/vortex/blob/main/README.md',
	},
	'wizard-audio-settings': {
		en: 'https://github.com/glatzkopf94/vortex/blob/main/README.md',
		de: 'https://github.com/glatzkopf94/vortex/blob/main/README.md',
	},
	'wizard-audio-result': {
		en: 'https://github.com/glatzkopf94/vortex/blob/main/README.md',
		de: 'https://github.com/glatzkopf94/vortex/blob/main/README.md',
	},
	'wizard-license': {
		en: 'https://github.com/glatzkopf94/vortex/blob/main/README.md',
		de: 'https://github.com/glatzkopf94/vortex/blob/main/README.md',
	},
	'wizard-error': {
		en: 'https://github.com/glatzkopf94/vortex/blob/main/README.md',
		de: 'https://github.com/glatzkopf94/vortex/blob/main/README.md',
	},
	'wizard-abort': {
		en: 'https://github.com/glatzkopf94/vortex/blob/main/README.md',
		de: 'https://github.com/glatzkopf94/vortex/blob/main/README.md',
	},
	'encoder-h264_omx': {
		en: 'https://github.com/glatzkopf94/vortex/blob/main/README.md',
		de: 'https://github.com/glatzkopf94/vortex/blob/main/README.md',
	},
	'encoder-h264_v4l2m2m': {
		en: 'https://github.com/glatzkopf94/vortex/blob/main/README.md',
		de: 'https://github.com/glatzkopf94/vortex/blob/main/README.md',
	},
	'encoder-h264_nvenc': {
		en: 'https://github.com/glatzkopf94/vortex/blob/main/README.md',
		de: 'https://github.com/glatzkopf94/vortex/blob/main/README.md',
	},
	'encoder-h264_vaapi': {
		en: 'https://github.com/glatzkopf94/vortex/blob/main/README.md',
		de: 'https://github.com/glatzkopf94/vortex/blob/main/README.md',
	},
	'encoder-h264_videotoolbox': {
		en: 'https://github.com/glatzkopf94/vortex/blob/main/README.md',
		de: 'https://github.com/glatzkopf94/vortex/blob/main/README.md',
	},
	'encoder-libx264': {
		en: 'https://github.com/glatzkopf94/vortex/blob/main/README.md',
		de: 'https://github.com/glatzkopf94/vortex/blob/main/README.md',
	},
	'encoder-libx265': {
		en: 'https://github.com/glatzkopf94/vortex/blob/main/README.md',
		de: 'https://github.com/glatzkopf94/vortex/blob/main/README.md',
	},
	'encoder-libvpx-vp9': {
		en: 'https://github.com/glatzkopf94/vortex/blob/main/README.md',
		de: 'https://github.com/glatzkopf94/vortex/blob/main/README.md',
	},
};

function getTopicURL(topic, locale) {
	if (!(topic in topics)) {
		console.warn(`help topic "${topic}" not found`);
		// If topic doesn't exist, return default URL
		return 'https://github.com/glatzkopf94/vortex/blob/main/README.md';
	}

	if (!(locale in topics[topic])) {
		// If locale doesn't exist, return default locale (en) URL
		// This requires that "en" exists for all topics.
		return topics[topic].en;
	}

	return topics[topic][locale];
}

export default function Help(topic) {
	const url = getTopicURL(topic, i18n.locale);

	window.open(url);
}
