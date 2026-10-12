// Modified 2026-10-10 by Alexander / Nistkasten Livestream: Vortex UI branding.
import React from 'react';
import logo from './images/vortex.png';
export default function Logo({className}) {
 return <a href="https://github.com/glatzkopf94/vortex" className={className} target="_blank" rel="noopener noreferrer" aria-label="Vortex" style={{display:'inline-flex',alignItems:'center',flexShrink:0}}>
  <img src={logo} alt="Vortex" style={{height:80,width:80,objectFit:'contain',display:'block',maxWidth:'100%'}} />
 </a>;
}
