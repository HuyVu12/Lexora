/* Offline DOM unit smoke. This does not render pixels or replace browser QA. */
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
if(!process.argv[2])throw new Error('usage: node scripts/check_entity_graph_viewer.cjs <index.html>');
const html=fs.readFileSync(process.argv[2],'utf8');
const payload=html.match(/<script id="graph-data" type="application\/json">([\s\S]*?)<\/script>/)[1];
const script=html.match(/<script>\s*([\s\S]*?)<\/script>/)[1];
class Element{
 constructor(tag){this.tag=tag;this.children=[];this.attrs={};this.dataset={};this.events={};this.value='';this._text='';this.className='';this.checked=false;}
 append(...children){this.children.push(...children);}
 replaceChildren(...children){this.children=children;this._text='';}
 set textContent(value){this._text=String(value);this.children=[];}
 get textContent(){return this._text+this.children.map(c=>c.textContent).join(' ');}
 setAttribute(k,v){this.attrs[k]=String(v);if(k==='class')this.className=String(v);}
 addEventListener(k,action){this.events[k]=action;}
 get classList(){return{toggle:(name,on)=>{const names=new Set(this.className.split(/\s+/));on?names.add(name):names.delete(name);this.className=[...names].join(' ');}};}
 querySelectorAll(selector){return this.children.flatMap(c=>[...(c.className.split(/\s+/).includes(selector.slice(1))?[c]:[]),...c.querySelectorAll(selector)]);}
}
const ids=new Map([...html.matchAll(/\bid="([^"]+)"/g)].map(m=>[m[1],new Element('div')]));
ids.get('graph-data').textContent=payload;ids.get('only-structured').checked=true;
const document={getElementById:id=>{assert(ids.has(id),'missing DOM id '+id);return ids.get(id);},createElement:t=>new Element(t),createElementNS:(_,t)=>new Element(t)};
vm.runInNewContext(script,{document,console,Map,Set},{timeout:5000});
const graph=ids.get('graph'),panel=ids.get('inspector'),norm=ids.get('norm');
assert.equal(norm.children.length,8);
assert(panel.textContent.includes('người sử dụng lao động'));
const actor=graph.querySelectorAll('.node').find(n=>n.attrs['aria-label'].startsWith('Chủ thể:'));
assert(actor,'typed actor node absent');actor.events.click();
assert(panel.textContent.includes('người sử dụng lao động'));
assert(panel.textContent.includes('Offset và phiên bản bằng chứng'));
const modal=graph.querySelectorAll('.edge-hit').find(n=>n.attrs['aria-label']==='tính quy phạm');
assert(modal);modal.events.click();
assert(panel.textContent.includes('phải'));
ids.get('search').value='85%';ids.get('search').oninput();
assert.equal(norm.children.length,1);assert(panel.textContent.includes('85%'));
assert(!graph.querySelectorAll('.node').some(n=>n.attrs['aria-label'].startsWith('Chủ thể:')),'salary payer was invented');
ids.get('search').value='zzzzzz';ids.get('search').oninput();
assert.equal(norm.children.length,0);assert(panel.textContent.includes('Không có quy phạm'));
ids.get('reset').onclick();assert.equal(norm.children.length,8);
ids.get('only-structured').checked=false;ids.get('only-structured').onchange();assert.equal(norm.children.length,12);
norm.value=norm.children.find(option=>option.textContent.includes('Ứng viên quy phạm')).value;norm.onchange();
assert(panel.textContent.includes('Chưa có quy tắc bóc tách phù hợp'));
assert(!graph.querySelectorAll('.node').some(n=>n.attrs['aria-label'].startsWith('Chủ thể:')));
console.log('PASS: entity graph initialization, typed actor, exact evidence, modality edge, quantity search, unknown actor, empty filter, reset, fallback review');
