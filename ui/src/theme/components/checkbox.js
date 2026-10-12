/* eslint-disable import/no-anonymous-default-export */
import base from '../base';

export default {
 styleOverrides: {
  root: {
   '&.Mui-checked, &.MuiCheckbox-indeterminate': { color: '#64b5f6' },
   '&.Mui-disabled': { color: base.palette.text.disabled },
  },
 },
};
