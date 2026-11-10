// One persistent daily profile is used by daily and combined operation.
export const profileKeys=['interval','fps','width','formatVersion','timezone','window','latitude','longitude','startEvent','endEvent','startOffset','endOffset'];
const primary=mode=>mode==='season'?'season':'daily';
export function profileValues(form,kind){
 const stored=form[kind+'Settings'];
 return {...form,...(stored||{}),mode:kind,...(!stored&&kind==='season'?{interval:Math.max(30,form.interval)}:{})};
}
export function updateProfile(form,kind,key,value){
 const values=profileValues(form,kind);
 const profile=Object.fromEntries(profileKeys.map(k=>[k,values[k]]));
 profile[key]=value;
 return {...form,[kind+'Settings']:profile,...(primary(form.mode)===kind?{[key]:value}:{})};
}
export function switchMode(form,mode){
 let next={...form};
 const old=primary(form.mode);
 next[old+'Settings']=Object.fromEntries(profileKeys.map(k=>[k,form[k]]));
 const values=profileValues(next,primary(mode));
 return {...next,...Object.fromEntries(profileKeys.map(k=>[k,values[k]])),mode};
}
export function planStarted(mode,armed,season){return mode==='daily'?armed:mode==='season'?season:armed&&season;}
