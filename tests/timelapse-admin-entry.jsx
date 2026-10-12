import React from 'react';
import {createRoot} from 'react-dom/client';
import {ThemeProvider,createTheme,CssBaseline} from '@mui/material';
import Timelapse from '../ui/src/views/Timelapse.js';
import API from '../ui/src/utils/api.js';
const api=new API('');api.SetToken(()=>sessionStorage.getItem('test-token')||'');
createRoot(document.getElementById('root')).render(<ThemeProvider theme={createTheme({palette:{mode:'dark'},typography:{h2:{fontSize:24},h3:{fontSize:19}}})}><CssBaseline/><Timelapse restreamer={{api,_call:async(fn,...args)=>{const r=await fn.apply(api,args);return [r.val,r.err];}}}/></ThemeProvider>);
