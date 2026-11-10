import React from 'react';
import {render,screen,fireEvent,waitFor} from '@testing-library/react';
import {ThemeProvider} from '@mui/material/styles';
import theme from '../theme';
import TimelapseOverlay from './TimelapseOverlay';
jest.mock('./Publication/PlayerOverlay',()=>({__esModule:true,default:({settings,onChange})=><input aria-label="Overlay text" value={settings.template} onChange={e=>onChange({...settings,template:e.target.value})}/>}));
const channels=[{id:'a',name:'Kamera A'},{id:'b',name:'Kamera B'}];
function setup(){
 const metadata={a:{meta:{name:'A'},player:{poster:'keep.jpg',overlay:{enabled:true,template:'A'}}},b:{meta:{name:'B'},player:{overlay:{enabled:true,template:'B'}}}};
 const restreamer={GetIngest:jest.fn(async id=>({metadata:JSON.parse(JSON.stringify(metadata[id]))})),InitPlayerSettings:p=>p,SetIngestMetadata:jest.fn(async(id,data)=>{metadata[id]=data;return true;}),UpdatePlayer:jest.fn().mockResolvedValue(true)};
 const onClose=jest.fn(),onSaved=jest.fn();
 render(<ThemeProvider theme={theme}><TimelapseOverlay restreamer={restreamer} channels={channels} initialChannel="a" onClose={onClose} onSaved={onSaved}/></ThemeProvider>);
 return {restreamer,metadata,onClose,onSaved};
}
test('saves canonical channel overlay and preserves latest unrelated player values',async()=>{
 const {metadata,restreamer,onSaved}=setup();
 const input=await screen.findByLabelText('Overlay text');
 fireEvent.change(input,{target:{value:'New value'}});
 metadata.a.player.poster='new-poster.jpg';
 fireEvent.click(screen.getByText('Speichern'));
 await waitFor(()=>expect(onSaved).toHaveBeenCalled());
 expect(metadata.a.player).toEqual({poster:'new-poster.jpg',overlay:{enabled:true,template:'New value'}});
 expect(metadata.b.player.overlay.template).toBe('B');
 expect(restreamer.UpdatePlayer).toHaveBeenCalledWith('a');
});
test('cancel makes no metadata changes',async()=>{
 const {restreamer,onClose}=setup();
 fireEvent.change(await screen.findByLabelText('Overlay text'),{target:{value:'discard'}});
 fireEvent.click(screen.getByText('Abbrechen'));
 expect(onClose).toHaveBeenCalled();expect(restreamer.SetIngestMetadata).not.toHaveBeenCalled();
});
test('detects an overlay changed in another editor',async()=>{
 const {metadata,restreamer,onClose}=setup();
 fireEvent.change(await screen.findByLabelText('Overlay text'),{target:{value:'edit'}});
 metadata.a.player.overlay.template='changed elsewhere';
 fireEvent.click(screen.getByText('Speichern'));
 expect(await screen.findByText(/inzwischen geändert/)).toBeTruthy();
 expect(restreamer.SetIngestMetadata).not.toHaveBeenCalled();expect(onClose).not.toHaveBeenCalled();
});
test('switching channels loads that channels actual saved overlay',async()=>{
 setup();await screen.findByLabelText('Overlay text');
 fireEvent.mouseDown(screen.getByLabelText('Overlay-Kanal'));
 fireEvent.click(await screen.findByRole('option',{name:'Kamera B'}));
 await waitFor(()=>expect(screen.getByLabelText('Overlay text').value).toBe('B'));
});
test('save failure stays visible and does not close dialog',async()=>{
 const {restreamer,onClose}=setup();await screen.findByLabelText('Overlay text');
 restreamer.SetIngestMetadata.mockResolvedValue(false);
 fireEvent.click(screen.getByText('Speichern'));
 expect(await screen.findByText('Overlay konnte nicht gespeichert werden.')).toBeTruthy();expect(onClose).not.toHaveBeenCalled();
});
test('dialog overrides sidebar theme and centers a scrollable mobile layout',async()=>{
 setup();await screen.findByLabelText('Overlay text');
 const dialog=screen.getByRole('dialog');
 expect(getComputedStyle(dialog.parentElement).justifyContent).toBe('center');
 expect(getComputedStyle(dialog.parentElement).alignItems).toBe('center');
 expect(getComputedStyle(screen.getByText('Overlay-Einstellungen')).textAlign).toBe('center');
});
