// Run against the disposable fixture, never against production.
const assert=require('node:assert/strict');
const fs=require('node:fs');
const {chromium}=require(process.env.NKL_PLAYWRIGHT||'playwright');
const fixture=JSON.parse(fs.readFileSync('/tmp/nkl-timelapse-fixture.json','utf8'));
(async()=>{
  const browser=await chromium.launch({headless:true,executablePath:process.env.NKL_CHROMIUM||undefined,args:['--no-sandbox','--disable-dev-shm-usage']});
  try {
    const page=await browser.newPage({viewport:{width:960,height:540}});
    const requests=[];const errors=[];page.on('request',r=>requests.push(r.url()));page.on('pageerror',e=>errors.push(e.message));
    await page.goto('http://127.0.0.1:8080/'+fixture.channel+'.html');
    await page.locator('.vjs-big-play-button').click();
    await page.waitForFunction(()=>window.player&&!player.paused()&&player.currentTime()>0&&!player.error());
    assert.equal(requests.filter(u=>u.includes('/timelapse/')).length,0,'Live must make zero timelapse requests');
    const source=await page.evaluate(()=>player.currentSrc());
    for(let i=0;i<2;i++){
      await page.locator('.nkl-timelapse-button').click();
      await page.waitForFunction(()=>{const v=document.querySelector('.nkl-timelapse-panel video');return v&&v.currentTime>0&&!v.paused&&!v.error;});
      assert.equal(await page.evaluate(()=>player.paused()),true);
      await page.getByRole('button',{name:'● Live',exact:true}).click();
      await page.waitForFunction(()=>!player.paused()&&!player.error());
      assert.equal(await page.evaluate(()=>player.currentSrc()),source,'DVR source must remain unchanged');
      assert.equal(await page.locator('.nkl-timelapse-panel').count(),0);
    }
    await page.locator('.nkl-timelapse-button').click();
    await page.waitForSelector('.nkl-timelapse-panel');
    await page.evaluate(()=>deactivatePublicStream('session'));
    assert.equal(await page.locator('.nkl-timelapse-panel').count(),0);
    assert.equal(await page.locator('#lc-playback-gate').isVisible(),true);
    const admin=await browser.newPage({viewport:{width:390,height:900}});
    admin.on('pageerror',e=>errors.push(e.message));
    await admin.addInitScript(token=>sessionStorage.setItem('test-token',token),fixture.token);
    const unauth=await admin.request.get('http://127.0.0.1:8080/api/v3/timelapse/status');assert.equal(unauth.status(),401);
    await admin.goto('http://127.0.0.1:8080/ui/');
    await admin.getByRole('combobox',{name:'Kanal',exact:true}).click();
    await admin.getByRole('option',{name:'Lokale Testkamera'}).click();
    await admin.getByLabel('Bildintervall in Sekunden').fill('900');
    await admin.getByRole('button',{name:'Einstellungen speichern',exact:true}).click();
    await admin.getByText('Gespeichert / Auftrag angenommen.').waitFor();
    const saved=await admin.request.get('http://127.0.0.1:8080/api/v3/timelapse/status',{headers:{Authorization:'Bearer '+fixture.token}});
    assert.equal((await saved.json()).channels[0].settings.interval,900);
    const downloading=admin.waitForEvent('download');
    await admin.getByRole('button',{name:/MP4 herunterladen/}).click();
    const download=await downloading;const bytes=fs.readFileSync(await download.path());
    assert.ok(bytes.length>1000);assert.equal(bytes.toString('ascii',4,8),'ftyp');
    await admin.getByRole('button',{name:'Admin-Vorschau',exact:true}).click();
    await admin.locator('video').waitFor();await admin.locator('video').evaluate(v=>v.play());
    await admin.waitForFunction(()=>document.querySelector('video').currentTime>0);
    await admin.screenshot({path:'/tmp/nkl-timelapse-admin.png',fullPage:true});
    const overflow=await admin.evaluate(()=>Array.from(document.querySelectorAll('*')).filter(e=>e.getBoundingClientRect().right>innerWidth+1).map(e=>({tag:e.tagName,cl:e.className,right:e.getBoundingClientRect().right,text:e.textContent.slice(0,80)})).slice(0,12));
    assert.ok(await admin.evaluate(()=>document.documentElement.scrollWidth<=window.innerWidth+1),'No horizontal overflow on mobile: '+JSON.stringify(overflow));
    await admin.screenshot({path:'/tmp/nkl-timelapse-admin.png',fullPage:true});
    assert.deepEqual(errors,[]);
    console.log('PASS: zero timelapse requests during Live, two preview/Live switches preserving DVR source, session gate, authenticated admin settings, binary MP4 download, admin playback, mobile layout.');
  }finally{await browser.close();}
})().catch(e=>{console.error(e);process.exitCode=1;});
