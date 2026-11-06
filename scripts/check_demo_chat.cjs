/* Runs the real UI JavaScript against an isolated loopback test server.
 * Minimal DOM mock only: not a screenshot or a substitute for browser QA.
 * Python 3.11+ runner: python .my_docs/verify_chat_ui.py (Node required).
 */
const assert=require('node:assert/strict'),vm=require('node:vm');
const base=process.argv[2];
if(!/^http:\/\/127\.0\.0\.1:\d+$/.test(base||''))throw Error('Only a loopback test server URL is allowed');
class Element{
 constructor(tag){this.tag=tag;this.children=[];this.attrs={};this.dataset={};this.events={};this.value='';this._text='';this.className='';this.disabled=false;this.checked=false;}
 append(...children){this.children.push(...children);}
 replaceChildren(...children){this.children=children;this._text='';}
 set textContent(value){this._text=String(value);this.children=[];}
 get textContent(){return this._text+this.children.map(c=>c.textContent).join(' ');}
 set innerHTML(_){throw Error('Unsafe HTML insertion');}
 setAttribute(k,v){this.attrs[k]=String(v);}
 addEventListener(k,fn){this.events[k]=fn;}
 get classList(){const e=this;return{toggle(name,on){const values=new Set(e.className.split(/\s+/));const enable=on===undefined?!values.has(name):on;enable?values.add(name):values.delete(name);e.className=[...values].join(' ');},add(name){e.className+=' '+name;},remove(name){e.className=e.className.split(/\s+/).filter(v=>v!==name).join(' ');}};}
}
async function waitFor(predicate){const start=Date.now();while(!predicate()){if(Date.now()-start>5000)throw Error('DOM state did not settle');await new Promise(resolve=>setTimeout(resolve,10));}}
async function main(){
 const html=await(await fetch(base+'/')).text();
 const extension=await(await fetch(base+'/demo-chat.js')).text();
 const script=html.match(/<script>\s*([\s\S]*?)<\/script>/)[1];
 const ids=new Map([...html.matchAll(/<([a-z][a-z0-9]*)\b([^>]*\bid="([^"]+)"[^>]*)>/g)].map(m=>{const e=new Element(m[1]);e.disabled=/\bdisabled\b/.test(m[2]);e.className=(m[2].match(/class="([^"]*)"/)||[])[1]||'';return[m[3],e];}));
 const document={getElementById(id){assert(ids.has(id),'Missing id '+id);return ids.get(id);},createElement:t=>new Element(t)};
 const context=vm.createContext({document,console,TextDecoder,fetch:(url,options)=>{const u=new URL(url,base);assert.equal(u.origin,base);return fetch(u,options);}});
 vm.runInContext(script,context,{timeout:2000});vm.runInContext(extension,context,{timeout:2000});
 await waitFor(()=>ids.get('sourceLibrary').children.length===6&&ids.get('chatRevision').children.length===1);
 assert.equal(ids.get('llmOption').disabled,true);
 await ids.get('startChat').onclick();
 assert(ids.get('message').textContent.includes('chưa có quy phạm'));
 const sourceButton=ids.get('sourceLibrary').children[0].children.find(e=>e.tag==='button');
 await sourceButton.onclick();assert.equal(ids.get('claims').children.length,2,ids.get('message').textContent);
 // Real-source draft above is never published. Synthetic data is isolated in this test DB.
 ids.get('title').value='SYNTHETIC UI TEST — NOT REAL LAW';
 ids.get('text').value='Điều 1. TỔNG HỢP KHÔNG PHẢI LUẬT\n1. Người lao động phải thông báo kết quả thử việc cho người lao động.\n2. Người sử dụng lao động phải trả khoản bí mật.\n';
 ids.get('synthetic').checked=true;await ids.get('prepare').onclick();
 for(const card of ids.get('claims').children){const select=card.children[0].children.find(e=>e.tag==='select');select.value=card.textContent.includes('bí mật')?'reject':'approve';select.onchange();}
 ids.get('reviewer').value='DOM-TEST';ids.get('reason').value='Isolated synthetic UI verification';ids.get('confirm').checked=true;
 await ids.get('publish').onclick();
 assert(ids.get('success').textContent.includes('Đã gộp'));
 assert.equal(ids.get('chatRevision').children.length,2);
 assert(ids.get('chatRevision').value);
 await ids.get('startChat').onclick();assert.equal(ids.get('askChat').disabled,false);
 ids.get('chatQuestion').value='thong bao ket qua thu viec';await ids.get('askChat').onclick();
 assert(ids.get('chatTurns').textContent.includes('Đoạn nguồn phù hợp'));
 assert(ids.get('chatTurns').textContent.includes('Text hash:'));
 assert(ids.get('chatTurns').textContent.includes('KHÔNG PHẢI LUẬT THẬT'));
 ids.get('chatQuestion').value='khoản bí mật';await ids.get('askChat').onclick();
 assert(ids.get('chatTurns').textContent.includes('Chưa tìm thấy đủ căn cứ'));
 const state=await(await fetch(base+'/api/state')).json();
 const session=await(await fetch(base+'/api/chat/session?id='+state.chat_sessions[0].id)).json();
 assert.equal(session.turns.length,2);assert.equal(session.turns[1].citations.length,0);
 assert(!JSON.stringify(session.turns[0].citations).includes('bí mật'));
 console.log('PASS: source library draft, confirm gate, synthetic-only test publication, current revision selection, no-accent chat, citations, rejected-source exclusion and saved turns; no provider calls');
}
main().catch(e=>{console.error(e);process.exitCode=1;});
