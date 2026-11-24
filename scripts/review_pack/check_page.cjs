/* Real-browser smoke of the review page (headless Chrome/Edge over the DevTools protocol, Node 22+, no npm deps).
 * Usage: node scripts/review_pack/check_page.cjs <review.html> <screenshot-dir> [chrome-path]
 * Walks every tab in light and dark, drives the keyboard, checks gold validation, export and fails on console errors.
 * Opens a local file only; no network.
 */
const { spawn } = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const assert = require('node:assert/strict');
const { pathToFileURL } = require('node:url');

const page = path.resolve(process.argv[2] || '');
const out = process.argv[3];
const chromePath = process.argv[4] || ['C:/Program Files/Google/Chrome/Application/chrome.exe',
  'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe', '/usr/bin/google-chrome', '/usr/bin/chromium'].find(p => fs.existsSync(p));
if (!fs.existsSync(page) || !out || !chromePath) throw Error('usage: check_page.cjs <review.html> <screenshot-dir> [chrome-path]');
fs.mkdirSync(out, { recursive: true });
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function main() {
  const port = 9600 + Math.floor(Math.random() * 300);
  const profile = fs.mkdtempSync(path.join(os.tmpdir(), 'lexora-rp-'));
  const chrome = spawn(chromePath, ['--headless=new', `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`, '--no-first-run', '--window-size=1280,1000', 'about:blank'], { stdio: 'ignore' });
  let target;
  for (let i = 0; i < 60 && !target; i++) {
    await sleep(250);
    try { target = (await (await fetch(`http://127.0.0.1:${port}/json`)).json()).find(t => t.type === 'page'); } catch (e) { /* not up yet */ }
  }
  if (!target) throw Error('Chrome did not start');
  const ws = new WebSocket(target.webSocketDebuggerUrl);
  await new Promise(r => ws.addEventListener('open', r));
  let id = 0; const pending = new Map(); const errors = [];
  ws.addEventListener('message', m => {
    const d = JSON.parse(m.data);
    if (d.id && pending.has(d.id)) { pending.get(d.id)(d); pending.delete(d.id); }
    if (d.method === 'Runtime.exceptionThrown') errors.push(d.params.exceptionDetails.exception?.description || d.params.exceptionDetails.text);
    if (d.method === 'Runtime.consoleAPICalled' && d.params.type === 'error') errors.push(d.params.args.map(a => a.value).join(' '));
  });
  const send = (method, params = {}) => new Promise(r => { const n = ++id; pending.set(n, r); ws.send(JSON.stringify({ id: n, method, params })); });
  const ev = async expr => { const r = await send('Runtime.evaluate', { expression: expr, returnByValue: true, awaitPromise: true }); if (r.result.exceptionDetails) throw Error(JSON.stringify(r.result.exceptionDetails)); return r.result.result.value; };
  const key = async (k, text) => { const digit = /^\d$/.test(k); const vk = k === 'Enter' ? 13 : k.toUpperCase().charCodeAt(0); await send('Input.dispatchKeyEvent', { type: 'keyDown', key: k, code: k === 'Enter' ? 'Enter' : (digit ? 'Digit' + k : 'Key' + k.toUpperCase()), windowsVirtualKeyCode: vk, text: k === 'Enter' ? '\r' : (text ?? k) }); await send('Input.dispatchKeyEvent', { type: 'keyUp', key: k, windowsVirtualKeyCode: vk }); };
  const shot = async name => { const r = await send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: true }); fs.writeFileSync(path.join(out, name + '.png'), Buffer.from(r.result.data, 'base64')); };
  await send('Runtime.enable'); await send('Page.enable');
  await send('Emulation.setDeviceMetricsOverride', { width: 1280, height: 900, deviceScaleFactor: 1, mobile: false });
  const open = async hash => { await send('Page.navigate', { url: 'about:blank' }); await sleep(100); await send('Page.navigate', { url: pathToFileURL(page).href + hash }); await sleep(600); };

  await open('#reviewer=Test&theme=light');
  const tasks = await ev('PACK.order');
  console.log('tabs', tasks.join(','), 'mode', await ev('PACK.mode'));
  for (const theme of ['light', 'dark']) {
    for (const t of tasks) {
      await open(`#reviewer=Test&theme=${theme}&tab=${t}`);
      await shot(`${t}-${theme}`);
      const overflow = await ev('document.documentElement.scrollWidth > innerWidth + 1');
      assert.equal(overflow, false, `horizontal overflow on ${t} ${theme}`);
    }
  }
  // Keyboard and state, first non-gold task
  const task = tasks.find(t => t !== 'gold');
  if (task) {
    await open(`#reviewer=Test&theme=light&tab=${task}`);
    const blind = await ev('BLIND');
    const before = await ev('state.data[state.tab].items && Object.keys(state.data[state.tab].items).length');
    await send('Page.bringToFront'); console.log('focus', await ev('document.hasFocus() + " " + document.activeElement.tagName + " " + state.tab')); await key('2', '2'); await sleep(100);
    assert.equal(await ev('Object.values(state.data[state.tab].items).filter(s => s.done).length'), 1, 'key 2 picks and marks done');
    await key('Enter'); await sleep(100);
    await key('j'); await key('k');
    await shot(`${task}-after-keys`);
    const exported = await ev(`(() => { let body; const real = URL.createObjectURL; URL.createObjectURL = b => { b.text().then(t => window.__exp = t); return 'blob:x'; }; document.getElementById('export').click(); URL.createObjectURL = real; return new Promise(r => setTimeout(() => r(window.__exp), 200)); })()`);
    const parsed = JSON.parse(exported);
    assert.equal(parsed.task, task); assert.equal(parsed.mode, blind ? 'blind' : 'suggestions');
    assert.ok(parsed.items.length >= 1);
    console.log(task, 'export', JSON.stringify(parsed.items[0]));
    // persisted across reload
    await open(`#reviewer=Test&theme=light&tab=${task}`);
    assert.ok(await ev('Object.values(state.data[state.tab].items).some(s => s.done)'), 'autosave restored after reload');
    void before;
  }
  if (tasks.includes('gold')) {
    await open('#reviewer=Test&theme=light&tab=gold');
    await ev(`(() => { const i = document.querySelector('.norm .slots input[id^="s0action"]'); if (!i) return; i.focus(); i.value = 'không có trong câu'; i.dispatchEvent(new Event('input', {bubbles: true})); })()`);
    const bad = await ev(`document.querySelectorAll('input.bad').length`);
    const done = await ev(`Object.values(state.data.gold.items).filter(s => s.done).length`);
    console.log('gold invalid inputs flagged:', bad, 'done:', done);
    if (!(await ev('BLIND'))) assert.ok(bad >= 1, 'a value that is not in the sentence is flagged');
    await shot('gold-invalid');
    await ev('document.getElementById("accept").click()');
    assert.equal(await ev(`Object.values(state.data.gold.items).filter(s => s.done).length`), 0, 'invalid row cannot be done');
    await key('n', 'n'); // focus is on a button/body, not typing
  }
  assert.deepEqual(errors, [], 'console errors: ' + errors.join('\n'));
  ws.close(); chrome.kill();
  console.log('ok');
}
main().catch(e => { console.error(e); process.exit(1); });
