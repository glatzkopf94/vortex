import React from 'react';
import {render,screen,fireEvent,waitFor} from '@testing-library/react';
import TimelapseTransfer from './TimelapseTransfer';
import {ThemeProvider} from '@mui/material/styles';
import theme from '../theme';
jest.mock('../contexts/Notify',()=>({useStatusNotifications:()=>{}}));
const settings={protocol:'ftps',host:'example.test',port:21,username:'user',password:'',directory:'/',intervalMinutes:60,mode:'both',enabled:false};
const certificate={id:'request-1',host:'example.test',port:21,sha256:'a'.repeat(64),changed:false};
const base={transfer:settings,projects:[],channels:[]};
async function challenge(action=jest.fn().mockResolvedValue({ok:true})){
 const view=render(<ThemeProvider theme={theme}><TimelapseTransfer data={base} action={action}/></ThemeProvider>);
 fireEvent.click(screen.getByText('FTP-Verbindung testen'));
 await waitFor(()=>expect(action).toHaveBeenCalledTimes(1));
 view.rerender(<ThemeProvider theme={theme}><TimelapseTransfer data={{...base,transferTest:{state:'certificate_required',certificate,message:'TLS-Zertifikat nicht vertrauenswürdig'}}} action={action}/></ThemeProvider>);
 return {view,action};
}
test('trust requires checkbox, persists exact endpoint and retries',async()=>{
 const {action}=await challenge();
 const confirm=screen.getByText('Bestätigen & Speichern');
 expect(confirm.disabled).toBe(true);
 fireEvent.click(screen.getByLabelText('Fingerabdruck geprüft – diesem Zertifikat vertrauen'));
 fireEvent.click(confirm);
 await waitFor(()=>expect(action).toHaveBeenCalledTimes(3));
 expect(action.mock.calls[1][0]).toMatchObject({action:'configure_transfer',settings:{tlsTrust:{host:certificate.host,port:21,sha256:certificate.sha256}}});
 expect(action.mock.calls[2][0]).toMatchObject({action:'test_transfer',settings:{tlsTrust:{sha256:certificate.sha256}}});
});
test('cancel never saves or retries',async()=>{
 const {action}=await challenge();
 fireEvent.click(screen.getByText('Abbrechen'));
 expect(action).toHaveBeenCalledTimes(1);
 await waitFor(()=>expect(screen.queryByRole('dialog')).toBeNull());
});
test('editing endpoint removes a saved pin and cannot confirm stale result',async()=>{
 const action=jest.fn().mockResolvedValue({ok:true});
 render(<TimelapseTransfer data={{...base,transfer:{...settings,tlsTrust:{host:certificate.host,port:21,sha256:certificate.sha256}}}} action={action}/>);
 fireEvent.change(screen.getByLabelText('Servername oder IP'),{target:{value:'other.test'}});
 fireEvent.click(screen.getByText('Eingabe speichern'));
 await waitFor(()=>expect(action).toHaveBeenCalledTimes(1));
 expect(action.mock.calls[0][0].settings.tlsTrust).toBeNull();
});
test('failed save keeps confirmation open and does not retry',async()=>{
 const action=jest.fn().mockResolvedValueOnce({ok:true}).mockResolvedValueOnce(undefined);
 await challenge(action);
 fireEvent.click(screen.getByLabelText('Fingerabdruck geprüft – diesem Zertifikat vertrauen'));
 fireEvent.click(screen.getByText('Bestätigen & Speichern'));
 await waitFor(()=>expect(action).toHaveBeenCalledTimes(2));
 expect(screen.getByRole('dialog')).toBeTruthy();
});
test('old status cannot open a confirmation on entering settings',()=>{
 render(<TimelapseTransfer data={{...base,transferTest:{state:'certificate_required',certificate}}} action={jest.fn()}/>);
 expect(screen.queryByRole('dialog')).toBeNull();
 expect(screen.getByLabelText('Port').value).toBe('21');
});
