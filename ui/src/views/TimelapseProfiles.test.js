import {profileValues,updateProfile,switchMode,planStarted} from './TimelapseProfiles';
const daily={mode:'daily',interval:45,fps:25,width:1280,timezone:'Europe/Berlin',window:'solar',latitude:51,longitude:10,startEvent:'sunrise',endEvent:'sunset',startOffset:-60,endOffset:60,formatVersion:2};
test('daily settings remain identical across all switches and reload',()=>{
 let form=switchMode(daily,'both');
 form=updateProfile(form,'daily','interval',90);
 form=updateProfile(form,'daily','width',1920);
 form=updateProfile(form,'season','interval',1800);
 form=JSON.parse(JSON.stringify(form));
 form=switchMode(form,'season');expect(form.interval).toBe(1800);
 form=switchMode(form,'daily');expect(form.interval).toBe(90);expect(form.width).toBe(1920);
 form=switchMode(form,'both');expect(profileValues(form,'daily').interval).toBe(90);
 expect(profileValues(form,'season').interval).toBe(1800);
 expect(profileValues(form,'daily').window).toBe('solar');
});
test('season-only legacy values and separate interval are retained',()=>{
 let form={...daily,mode:'season',interval:7200};
 form=switchMode(form,'both');form=updateProfile(form,'daily','interval',30);
 form=switchMode(form,'season');expect(form.interval).toBe(7200);
});
test('15 second daily setting does not become invalid season interval',()=>{
 const form=switchMode({...daily,interval:15},'both');
 expect(profileValues(form,'daily').interval).toBe(15);expect(profileValues(form,'season').interval).toBe(30);
});
test('combined plan can start a missing season while daily is armed',()=>{
 expect(planStarted('both',true,false)).toBe(false);
 expect(planStarted('both',true,true)).toBe(true);
 expect(planStarted('daily',true,false)).toBe(true);
});
