// Modified 2026-10-10 by Alexander / Nistkasten Livestream: Vortex UI branding.
/* eslint-disable import/no-anonymous-default-export */
export default {
	common: {
		// MuiButton, ChannelList.js, index.js, Player.js
		black: '#000',
		// Header.js, ChannelList.js, Edit->index.js
		white: '#fff',
	},
	background: {
		// MuiAccordion
		accordion: 'rgba(67, 77, 89, .4)',
		// MuiAccordion
		accordion_border: 'rgba(117, 131, 147, .6)',
		// MuiMenuItem, Header.js (MenuIcon, MenuItem), Progress.js (Progress boxes)
		box_default: 'rgb(67, 77, 89)',
		// MuiListItem, Progress.js (Progress boxes - danger)
		box_danger: 'rgb(193, 39, 45)',
		// MuiButton, global.js (Page background)
		button_disabled: '#29333f',
		// MuiButton, MuiMenu, MuiToggleButton, MultiSelectOption.js (MenuItem)
		dark1: 'rgba(0, 0, 0, .1)',
		// MuiOutlinedInput, BoxText.js (color=dark)
		dark2: 'rgba(0, 0, 0, .25)',
		// Footer.js, Textarea.js, global.js (Scrollbar)
		footer1: 'rgba(47, 58, 72, .9)',
		// Footer.js, Textarea.js
		footer2: 'rgba(27, 36, 48, .9)',
		// MuiAppBar, BoxText.js (color=light = default), TabsHorizontal.js, Paper.js
		light1: 'rgba(255, 255, 255, .1)',
		// MuiDialog, MuiPaper, MuiTooltip, Header.js, ModalContent.js, Dialog.js
		modal: 'rgb(57, 69, 84)',
		// BoxTextarea.js, Progress.js, Process.js, Textarea.js, gobal.js (textarea)
		modalbox: 'rgb(76, 89, 106)',
		// MuiFab, MuiListItem, MuiPaper, Headerjs,
		paper: 'rgba(42, 54, 69, .95)',
	},
	default: {
		main: '#5c6b7b',
	},
	primary: {
		// MuiOutlinedInput
		light: '#8997a8',
		// MuiAlert, MuiMenu, MuiOutlinedInput, MuiSelect
		main: '#5c6b7b',
		// MuiMenu, MuiOutlinedInput
		dark: '#43505f',
		// MuiButton
		contrastText: '#fff',
	},
	secondary: {
		// MuiAlert, MuiButton, MuiFab, MuiOutlinedInput, MuiSelect, MuiToggleButton
		main: '#39B54A',
		// MuiButton, MuiFab
		contrastText: '#fff',
	},
	service: {
		// MuiButton, Login.js
		main: '#EAEA05',
		// Paper.js
		contrastText: 'rgba(32,42,55,.95)',
	},
	error: {
		// MuiAlert, MuiButton, BoxText.js (color=danger), Env.js
		main: '#C1272D',
		// MuiButton
		contrastText: '#fff',
	},
	warning: {
		// MuiAlert, Main->index.js
		main: '#E28014',
	},
	selected: {
		// MuiFab
		main: '#fff',
	},
	text: {
		// MuiBackdrop, MuiButton, MuiDialog, MuiFormLabel, MuiIconButton,
		// MuiInputLabel, MuiMenu, MuiOutlinedInput, MuiPaper, MuiSelect, MuiTab,
		// MuiToggleButton, MuiTypography,
		// Header.js, Checkbox.js, Env.js, LanguageSelect.js, ModalContent.js,
		// TabsHorizontal.js, Dialog.js, global.js (Textarea)
		primary: '#fff',
		// MuiSelect, MuiTab, Footer.js, Header.js
		secondary: 'rgba(255, 255, 255, 0.7)',
		// MuiCheckbox, Checkbox.js
		disabled: 'rgba(255, 255, 255, 0.38)',
		// MuiTypography
		hint: 'rgba(255, 255, 255, 0.7)',
	},
};
