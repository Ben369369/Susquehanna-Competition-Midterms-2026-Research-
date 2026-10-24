import {spawn} from 'node:child_process';
import {mkdtempSync,writeFileSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join} from 'node:path';
const profile=mkdtempSync(join(tmpdir(),'susq-browser-'));
const child=spawn('C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',['--headless','--disable-gpu','--no-first-run','--remote-debugging-port=9237','--user-data-dir='+profile,'about:blank'],{stdio:'ignore',windowsHide:true});
const pause=ms=>new Promise(r=>setTimeout(r,ms));
let socket;let seq=0;const pending=new Map();const errors=[];
async function call(method,params={}){const id=++seq;return new Promise((resolve,reject)=>{pending.set(id,{resolve,reject});socket.send(JSON.stringify({id,method,params}));});}
async function evaluate(expression){const r=await call('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});if(r.exceptionDetails)throw Error(JSON.stringify(r.exceptionDetails));return r.result.value;}
function assert(value,message){if(!value)throw Error(message);}
try{
 let targets;
 for(let i=0;i<50;i++){try{targets=await(await fetch('http://127.0.0.1:9237/json')).json();break;}catch{await pause(200);}}
 assert(targets?.length,'Browser failed to start');
 socket=new WebSocket(targets.find(t=>t.type==='page').webSocketDebuggerUrl);
 await new Promise(r=>socket.onopen=r);
 socket.onmessage=event=>{const m=JSON.parse(event.data);if(m.id){const p=pending.get(m.id);pending.delete(m.id);m.error?p.reject(Error(JSON.stringify(m.error))):p.resolve(m.result);}else if(m.method==='Runtime.exceptionThrown')errors.push(m.params);};
 await call('Runtime.enable');await call('Page.enable');
 await call('Emulation.setDeviceMetricsOverride',{width:1440,height:1100,deviceScaleFactor:1,mobile:false});
 await call('Page.navigate',{url:'http://127.0.0.1:8765'});
 for(let i=0;i<50;i++){if(await evaluate("Boolean(document.querySelector('#metrics .metric'))"))break;await pause(200);}
 assert(await evaluate("document.querySelectorAll('#metrics .metric').length===4"),'Overview missing');
 await evaluate("document.querySelector('[data-view=races]').click(); document.getElementById('search').value='Texas';document.getElementById('search').dispatchEvent(new Event('input'))");
 assert(await evaluate("document.querySelectorAll('#race-table tr').length===2"),'Search failed');
 await evaluate("document.querySelector('#race-table button').click()");
 assert(await evaluate("document.getElementById('detail').open"),'Detail modal failed');
 await evaluate("document.getElementById('close-detail').click();document.querySelector('[data-view=scenarios]').click();document.getElementById('shift').value=-3;document.getElementById('run').click()");
 for(let i=0;i<100;i++){if(await evaluate("document.querySelectorAll('.hist-bin').length>0"))break;await pause(200);}
 assert(await evaluate("document.querySelectorAll('.hist-bin').length>100"),'Simulation histogram failed');
 await evaluate("document.querySelector('[data-view=sources]').click()");
 assert(await evaluate("document.querySelectorAll('.source-card').length>=15"),'Sources missing');
 await evaluate("document.querySelector('[data-view=history]').click()");await pause(300);
 assert(await evaluate("document.querySelectorAll('.journal').length>0"),'Journal missing');
 await evaluate("document.querySelector('[data-view=overview]').click()");
 const desktop=await call('Page.captureScreenshot',{format:'png'});writeFileSync('research/portal-preview.png',Buffer.from(desktop.data,'base64'));
 await call('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:true});await pause(300);
 assert(await evaluate("document.documentElement.scrollWidth<=window.innerWidth+1"),'Mobile horizontal overflow');
 const mobile=await call('Page.captureScreenshot',{format:'png'});writeFileSync('research/portal-mobile.png',Buffer.from(mobile.data,'base64'));
 assert(errors.length===0,'Browser JavaScript exceptions');
 console.log('PASS: overview, race search, detail dialog, scenario simulation, evidence library, journal, mobile width; no JavaScript exceptions.');
}finally{if(socket)socket.close();child.kill();}
