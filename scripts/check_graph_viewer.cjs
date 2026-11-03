/* DOM unit smoke, not a substitute for visual/browser QA. No dependencies/network. */
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const path = require('node:path');
const input = process.argv[2];
if (!input) throw new Error('usage: node scripts/check_graph_viewer.cjs <generated index.html>');
const html = fs.readFileSync(input, 'utf8');
const payload = html.match(/<script id="graph-data" type="application\/json">([\s\S]*?)<\/script>/)[1];
const script = html.match(/<script>\s*([\s\S]*?)<\/script>/)[1];
const graph = JSON.parse(payload);
class Element {
  constructor(tag) { this.tag=tag;this.children=[];this.attrs={};this.dataset={};this.events={};this.value='';this._text='';this.className=''; }
  append(...children) { this.children.push(...children); }
  replaceChildren(...children) { this.children=children;this._text=''; }
  set textContent(value) { this._text=String(value);this.children=[]; }
  get textContent() { return this._text + this.children.map(e=>e.textContent).join(' '); }
  setAttribute(name,value) { this.attrs[name]=String(value);if(name==='class')this.className=String(value); }
  addEventListener(name,action) { this.events[name]=action; }
  get classList() { return {toggle:(name,on)=>{const values=new Set(this.className.split(/\s+/));on?values.add(name):values.delete(name);this.className=[...values].join(' ');}}; }
  querySelectorAll(selector) { const found=[];for(const child of this.children){if(child.className.split(/\s+/).includes(selector.slice(1)))found.push(child);found.push(...child.querySelectorAll(selector));}return found; }
  scrollIntoView() {}
}
const ids=new Map([...html.matchAll(/\bid="([^"]+)"/g)].map(m=>[m[1],new Element('div')]));
ids.get('graph-data').textContent=payload;
ids.get('layer').value='structure';
const document={getElementById:id=>{if(!ids.has(id))throw new Error('missing DOM id '+id);return ids.get(id);},createElement:tag=>new Element(tag),createElementNS:(_,tag)=>new Element(tag)};
vm.runInNewContext(script,{document,console,Map,Set}, {timeout:5000,filename:input});
assert(ids.get('inspector').textContent.includes('85%'),'initial evidence not shown');
const svg=ids.get('graph');
assert.equal(svg.querySelectorAll('.node').length,38);
const crossReference=svg.querySelectorAll('.edge-hit').find(e=>e.attrs['aria-label'].includes('dẫn chiếu đến: Điều 6.'));
assert(crossReference,'cross-document reference missing');
crossReference.events.click();
assert(ids.get('inspector').textContent.includes('khoản 1 Điều 21 của Bộ luật Lao động'));
ids.get('layer').value='claims';ids.get('layer').onchange();
assert(svg.querySelectorAll('.node').some(e=>e.attrs['aria-label'].startsWith('Ứng viên quy phạm')));
const candidate=svg.querySelectorAll('.node').find(e=>e.attrs['aria-label'].startsWith('Ứng viên quy phạm'));
candidate.events.click();
assert(ids.get('inspector').textContent.includes('Cần review'));
ids.get('search').value='Điều 25';ids.get('search').oninput();
assert(ids.get('matches').children.length>0);
ids.get('document').value='nd-145-2020';ids.get('document').onchange();
assert(!svg.querySelectorAll('.node').some(e=>e.attrs['aria-label'].includes('Điều 26.')));
ids.get('reset').onclick();
assert.equal(svg.querySelectorAll('.node').length,38);
console.log('PASS: viewer JS initialization, evidence panel, cross-document edge, candidate layer, search, document filter, reset');
