// Modified 2026-10-10 by Alexander / Nistkasten Livestream: Vortex UI branding.
import React from 'react';
import logo from './images/nkl-footer.png';
export default function Logo({className}) {
 return <a href="https://nistkasten-livestream.de" className={className} target="_blank" rel="noopener noreferrer" aria-label="Nistkasten Livestream" style={{display:'inline-flex',alignItems:'center',flexShrink:0,marginRight:12}}>
  <img src={logo} alt="Nistkasten Livestream" style={{height:48,width:48,objectFit:'contain',display:'block',maxWidth:'100%'}} />
 </a>;
}
