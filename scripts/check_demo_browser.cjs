/* Real-browser E2E for the local demo: drives headless Chrome over the DevTools protocol,
 * runs the F-KB-02 flow with synthetic data, captures screenshots and fails on console errors.
 * Usage: node scripts/check_demo_browser.cjs http://127.0.0.1:8770 <screenshot-dir> [chrome-path] [--ai]
 * --ai picks "Bằng AI" for the first import (demo started with --extract-model; sends the synthetic text to that model).
 * Start the demo first with a NEW store: python -m legal_ai.demo --store <new.sqlite> --port 8770
 * Only loopback URLs are allowed. No npm dependencies (Node 22+ for global WebSocket/fetch).
 */
const { spawn } = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const assert = require('node:assert/strict');

const base = process.argv[2];
const out = process.argv[3];
const flags = process.argv.slice(4).filter(a => a.startsWith('--'));
const useAi = flags.includes('--ai');
const chromePath = process.argv.slice(4).find(a => !a.startsWith('--')) || ['C:/Program Files/Google/Chrome/Application/chrome.exe',
  'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe', '/usr/bin/google-chrome', '/usr/bin/chromium'].find(p => fs.existsSync(p));
if (!/^http:\/\/127\.0\.0\.1:\d+$/.test(base || '')) throw Error('Only a loopback demo URL is allowed');
if (!out) throw Error('Screenshot directory required');
if (!chromePath) throw Error('Chrome or Edge not found; pass its path as the third argument');
fs.mkdirSync(out, { recursive: true });

const DOC_A = 'Điều 1. Thử việc (DỮ LIỆU MINH HỌA, KHÔNG PHẢI LUẬT)\n1. Người sử dụng lao động phải thông báo kết quả thử việc cho người lao động.\n2. Người lao động có quyền chấm dứt thỏa thuận thử việc mà không cần báo trước.\nĐiều 2. Tiền lương thử việc\nNgười sử dụng lao động phải trả lương thử việc ít nhất bằng 85% mức lương của công việc đó. Thời gian thử việc do hai bên thỏa thuận.\n';
const DOC_B = 'Điều 3. Hợp đồng lao động (DỮ LIỆU MINH HỌA)\n1. Người sử dụng lao động phải cung cấp thông tin về công việc cho người lao động.\n2. Người lao động không được tiết lộ bí mật kinh doanh trong thời gian làm việc.\n3. Hợp đồng lao động được lập thành hai bản.\n';
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function main() {
  const port = 9300 + Math.floor(Math.random() * 500);
  const profile = fs.mkdtempSync(path.join(os.tmpdir(), 'lexora-chrome-'));
  const chrome = spawn(chromePath, ['--headless=new', `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`,
    '--no-first-run', '--no-default-browser-check', '--disable-extensions', '--window-size=1440,1000', 'about:blank'], { stdio: 'ignore' });
  const errors = [];
  let ws;
  try {
    let target;
    for (let i = 0; i < 50 && !target; i++) {
      try { target = await (await fetch(`http://127.0.0.1:${port}/json/new?about:blank`, { method: 'PUT' })).json(); } catch { await sleep(200); }
    }
    assert(target, 'Chrome DevTools endpoint did not start');
    ws = new WebSocket(target.webSocketDebuggerUrl);
    await new Promise((resolve, reject) => { ws.onopen = resolve; ws.onerror = reject; });
    let id = 0;
    const pending = new Map();
    ws.onmessage = event => {
      const msg = JSON.parse(event.data);
      if (msg.id && pending.has(msg.id)) { const { resolve, reject } = pending.get(msg.id); pending.delete(msg.id); msg.error ? reject(Error(msg.error.message)) : resolve(msg.result); }
      if (msg.method === 'Runtime.exceptionThrown') errors.push(msg.params.exceptionDetails.exception?.description || msg.params.exceptionDetails.text);
      if (msg.method === 'Runtime.consoleAPICalled' && msg.params.type === 'error') errors.push(msg.params.args.map(a => a.value || a.description).join(' '));
      if (msg.method === 'Log.entryAdded' && msg.params.entry.level === 'error' && !/favicon/.test(msg.params.entry.url || '')) errors.push(msg.params.entry.text);
    };
    const send = (method, params = {}) => new Promise((resolve, reject) => { const n = ++id; pending.set(n, { resolve, reject }); ws.send(JSON.stringify({ id: n, method, params })); });
    await send('Runtime.enable'); await send('Log.enable'); await send('Page.enable');
    await send('Emulation.setDeviceMetricsOverride', { width: 1440, height: 1000, deviceScaleFactor: 1, mobile: false });
    const evaluate = async expression => {
      const result = await send('Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true });
      if (result.exceptionDetails) throw Error(result.exceptionDetails.exception?.description || result.exceptionDetails.text);
      return result.result.value;
    };
    const waitFor = async (expression, label) => {
      for (let i = 0; i < 100; i++) { if (await evaluate(expression)) return; await sleep(100); }
      const toast = await evaluate('document.getElementById("toast").textContent');
      const page = await evaluate('location.hash + " | " + document.getElementById("view").textContent.slice(0, 300)');
      throw Error(`Timed out waiting for ${label}${toast ? ` (app message: ${toast})` : ''}; page: ${page}`);
    };
    let shot = 0;
    const screenshot = async name => {
      await sleep(250);
      // Full-page captures would paint viewport-fixed bars mid-page; render them in flow while capturing.
      await evaluate('document.querySelectorAll(".footer-bar,.sidebar").forEach(e => { e.style.position = e.classList.contains("sidebar") ? "static" : "relative"; e.style.left = "0"; e.style.height = "auto"; }); document.querySelectorAll(".chat-setup,.review-bar").forEach(e => e.style.position = "static"); true');
      const { cssContentSize } = await send('Page.getLayoutMetrics');
      const height = Math.min(Math.ceil(cssContentSize.height), 6000);
      const { data } = await send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: true, clip: { x: 0, y: 0, width: 1440, height, scale: 1 } });
      const file = path.join(out, `${String(++shot).padStart(2, '0')}-${name}.png`);
      fs.writeFileSync(file, Buffer.from(data, 'base64'));
      await evaluate('document.querySelectorAll(".footer-bar,.sidebar").forEach(e => { e.style.position = ""; e.style.left = ""; e.style.height = ""; }); document.querySelectorAll(".chat-setup,.review-bar").forEach(e => e.style.position = ""); true');
      console.log('screenshot', file);
    };
    // In-page helpers: find controls by visible text like a person would.
    const helpers = `
      window.__byText = (sel, text) => [...document.querySelectorAll(sel)].find(e => e.textContent.trim().startsWith(text));
      window.__click = (sel, text) => { const e = __byText(sel, text); if (!e) throw Error('No ' + sel + ' ' + text); e.click(); return true; };
      window.__fill = (el, value) => { el.value = value; el.dispatchEvent(new Event('input', { bubbles: true })); el.dispatchEvent(new Event('change', { bubbles: true })); };
      window.__select = (text, within) => {
        for (const p of document.querySelectorAll('[data-uv]')) {
          if (within && !p.textContent.includes(within)) continue;
          const nodes = []; const walker = document.createTreeWalker(p, NodeFilter.SHOW_TEXT);
          let n, all = '';
          while ((n = walker.nextNode())) { if (n.parentElement.closest('sup')) continue; nodes.push([n, all.length]); all += n.data; }
          const at = all.indexOf(text); if (at < 0) continue;
          const locate = pos => { for (const [node, start] of nodes) if (pos <= start + node.data.length) return [node, pos - start]; };
          const r = document.createRange(); r.setStart(...locate(at)); r.setEnd(...locate(at + text.length));
          const s = getSelection(); s.removeAllRanges(); s.addRange(r); return true;
        }
        throw Error('Text not found in statute: ' + text);
      };`;
    const open = async hash => { await send('Page.navigate', { url: base + '/' + hash }); await waitFor('document.readyState === "complete" && !!document.querySelector("#view").children.length', 'page ' + hash); await evaluate(helpers); };

    await open('#/');
    assert(await evaluate('document.body.textContent.includes("Mỗi câu trả lời đều chỉ về đúng câu trong luật")'), 'introduction on empty home');
    await screenshot('empty-home');
    // A glossary term explains itself on hover: a real mouse move over the coloured "actor" segment.
    const hover = async selector => {
      // Scroll first and let the scroll settle: the tooltip closes on scroll by design.
      await evaluate(`document.querySelector(${JSON.stringify(selector)}).scrollIntoView({ block: 'center' }); true`);
      await sleep(200);
      const box = await evaluate(`(() => { const r = document.querySelector(${JSON.stringify(selector)}).getClientRects()[0]; /* first line box: wrapped text has a gap in its bounding box */ return { x: r.left + r.width / 2, y: r.top + r.height / 2 }; })()`);
      await send('Input.dispatchMouseEvent', { type: 'mouseMoved', x: box.x, y: box.y });
      await waitFor('(document.getElementById("term-tip") || { hidden: true }).hidden === false', 'term tooltip for ' + selector);
    };
    const viewportShot = async name => {
      const { data } = await send('Page.captureScreenshot', { format: 'png' });
      const file = path.join(out, `${String(++shot).padStart(2, '0')}-${name}.png`);
      fs.writeFileSync(file, Buffer.from(data, 'base64'));
      console.log('screenshot', file);
    };
    await hover('.specimen .seg[data-term="actor"]');
    assert(await evaluate('document.getElementById("term-tip").textContent.includes("Chủ thể") && !!document.querySelector("#term-tip mark")'), 'actor tooltip with highlighted example');
    await viewportShot('term-tooltip-home');
    await send('Input.dispatchMouseEvent', { type: 'mouseMoved', x: 5, y: 995 });
    await waitFor('document.getElementById("term-tip").hidden', 'tooltip hides when the pointer leaves');
    await open('#/about');
    await waitFor('document.body.textContent.includes("Câu hỏi nghiên cứu") && document.body.textContent.includes("ĐK4")', 'about page');
    await screenshot('about');
    await open('#/');

    // Import document A into a new KB.
    await evaluate('__click("a", "Nhập tài liệu")');
    await waitFor('!!__byText("label.choice", "Dán nội dung")', 'import form');
    await evaluate(helpers);
    await evaluate('__byText("label.choice", "Dán nội dung").querySelector("input").click()');
    await evaluate(`(() => { const f = document.querySelectorAll('.form input:not([type]), .form textarea'); __fill(f[0], 'Quy định thử việc (minh họa)'); __fill(document.querySelector('.form textarea'), ${JSON.stringify(DOC_A)}); document.querySelector('.form input[type=checkbox]').click(); return true; })()`);
    await evaluate(`(() => { const name = [...document.querySelectorAll('.form input')].find(i => i.placeholder.startsWith('Ví dụ: Hợp đồng')); __fill(name, 'Hợp đồng lao động'); __byText('label.choice', 'Công khai').querySelector('input').click(); return true; })()`);
    if (useAi) {
      await evaluate('__byText("label.choice", "Bằng AI").querySelector("input").click()');
      assert(await evaluate('__byText("label.choice", "Bằng AI").querySelector("input").checked'), 'AI extraction option');
    }
    await screenshot('import-form');
    await evaluate('__click("button", "Tách quy phạm")');
    if (useAi) {
      await waitFor('!!document.querySelector(".extracting") || !!document.querySelector(".statute")', 'extraction progress');
      if (await evaluate('!!document.querySelector(".extracting")')) await screenshot('extracting');
      for (let i = 0; i < 120 && !(await evaluate('!!document.querySelector(".statute")')); i++) await sleep(1000);
    }
    await waitFor('location.hash.startsWith("#/draft/") && !!document.querySelector(".statute")', 'review page');
    await evaluate(helpers);
    await screenshot('review');
    await hover('.note .slots .term[data-term="actor"]');
    assert(await evaluate('document.getElementById("term-tip").textContent.includes("Ví dụ minh họa")'), 'slot tooltip with example');
    await viewportShot('term-tooltip-review');
    await hover('.note .modality');
    assert(await evaluate('/Nghĩa vụ|Quyền|Điều cấm|Được phép/.test(document.getElementById("term-tip").textContent)'), 'modality tooltip');
    await send('Input.dispatchMouseEvent', { type: 'mouseMoved', x: 5, y: 5 });

    // Edit claim 1: choose the object slot by selecting source text, then add a note.
    await evaluate('document.querySelector("#note-1 .note-actions .quiet").click()');
    await waitFor('!!document.querySelector(".editor")', 'editor');
    await evaluate('__select("kết quả thử việc cho người lao động"); __click("button", "Dùng đoạn đã chọn")');
    await waitFor('document.querySelector("#note-1 .edited-tag") !== null', 'edited claim');
    await evaluate(helpers);
    await screenshot('claim-edited');
    await evaluate('__click("button", "Đóng")');
    await evaluate(helpers);
    // Reject claim 2.
    await evaluate('document.querySelector("#note-2 .btn.reject").click()');
    await waitFor('document.querySelector("#note-2").classList.contains("reject")', 'rejected claim');
    await evaluate(helpers);
    // A sentence without any norm cue is a gap: add a norm from it and fill actor and action from the source text.
    if (await evaluate('!!document.querySelector(".gap-note")')) {
      await evaluate('document.querySelector(".gap-note .note-actions .btn").click()');
      await waitFor('!!document.querySelector(".note .editor")', 'manual claim editor');
      await evaluate(helpers);
      await evaluate('__select("hai bên"); __click("button", "Dùng đoạn đã chọn")');
      await waitFor('[...document.querySelectorAll(".note")].some(n => n.querySelector(".origin.manual") && n.textContent.includes("hai bên"))', 'manual actor');
      await evaluate(helpers);
      await evaluate('(() => { const s = document.querySelector(".editor select"); s.value = "action"; s.dispatchEvent(new Event("change", { bubbles: true })); return true; })()');
      await evaluate(helpers);
      await evaluate('__select("thỏa thuận", "Thời gian thử việc do hai bên"); __click("button", "Dùng đoạn đã chọn")');
      await waitFor('[...document.querySelectorAll(".note")].some(n => n.querySelector(".origin.manual") && n.textContent.includes("thỏa thuận"))', 'manual action');
      await evaluate(helpers);
      await screenshot('manual-claim');
      await evaluate('__click("button", "Đóng")');
      await evaluate(helpers);
    }
    // Batch-approve the rest of each article.
    for (let i = 0; i < 4; i++) {
      const clicked = await evaluate('(() => { const b = [...document.querySelectorAll(".article-head button")].find(b => /^Duyệt|^Đánh dấu/.test(b.textContent)); if (b) { b.click(); return true; } return false; })()');
      if (!clicked) break;
      await sleep(500);
    }
    await waitFor('document.body.textContent.includes("Đã xử lý tất cả quy phạm và câu trong tài liệu")', 'all decided');
    await screenshot('review-decided');
    await evaluate('__click("a", "Xem trước thay đổi")');
    await waitFor('!!document.querySelector(".summary-line")', 'preview');
    await evaluate(helpers);
    await evaluate(`(() => { const f = document.querySelectorAll('.form input:not([type]), .form textarea'); __fill(f[0], 'Người duyệt thử'); __fill(f[1], 'Đối chiếu từng quy phạm với nguyên văn (kiểm thử tự động)'); document.querySelector('.form input[type=checkbox]').click(); return true; })()`);
    await screenshot('preview');
    await evaluate('__click("button", "Công bố vào kho")');
    await waitFor('(document.querySelector(".section.empty h2") || {}).textContent?.startsWith("Đã công bố")', 'published');
    await evaluate(helpers);
    await screenshot('published');

    // Merge document B into the same KB, linking a same-name entity.
    await open('#/import');
    await waitFor('location.hash === "#/import" && !!__byText("label.choice", "Gộp vào kho có sẵn") && !__byText("label.choice", "Gộp vào kho có sẵn").querySelector("input").disabled', 'merge import form');
    await evaluate('__byText("label.choice", "Dán nội dung").querySelector("input").click()');
    await evaluate(`(() => { __fill(document.querySelector('.form input:not([type])'), 'Giao kết hợp đồng (minh họa)'); __fill(document.querySelector('.form textarea'), ${JSON.stringify(DOC_B)}); document.querySelector('.form input[type=checkbox]').click(); __byText('label.choice', 'Gộp vào kho có sẵn').querySelector('input').click(); return true; })()`);
    await evaluate('__click("button", "Tách quy phạm")');
    await waitFor('!!document.querySelector(".statute")', 'merge review');
    await evaluate(helpers);
    assert(await evaluate('!!document.querySelector(".gap-note")'), 'merge document has a gap');
    await screenshot('merge-gap');
    for (let i = 0; i < 4; i++) {
      const clicked = await evaluate('(() => { const b = [...document.querySelectorAll(".article-head button")].find(b => /^Duyệt|^Đánh dấu/.test(b.textContent)); if (b) { b.click(); return true; } return false; })()');
      if (!clicked) break;
      await sleep(500);
    }
    await waitFor('document.body.textContent.includes("Đã xử lý tất cả quy phạm và câu trong tài liệu")', 'merge decided');
    const hasEntities = await evaluate('!!document.querySelector(".entities")');
    if (hasEntities) {
      await evaluate('__click(".entities button", "Cùng một thực thể")');
      await waitFor('document.querySelector(".entities .btn.approve").getAttribute("aria-pressed") === "true"', 'entity linked');
    }
    await screenshot('merge-review');
    await evaluate('__click("a", "Xem trước thay đổi")');
    await waitFor('!!document.querySelector(".summary-line")', 'merge preview');
    await evaluate(helpers);
    await evaluate(`(() => { const f = document.querySelectorAll('.form input:not([type]), .form textarea'); __fill(f[0], 'Người duyệt thử'); __fill(f[1], 'Kiểm thử gộp'); document.querySelector('.form input[type=checkbox]').click(); return true; })()`);
    await screenshot('merge-preview');
    await evaluate('__click("button", "Công bố vào kho")');
    await waitFor('(document.querySelector(".section.empty h2") || {}).textContent?.startsWith("Đã công bố")', 'merge published');
    await evaluate(helpers);

    // KB detail, then chat on the KB.
    await evaluate('__click("a", "Mở kho")');
    await waitFor('!!document.querySelector(".facts")', 'kb page');
    await screenshot('kb-detail');
    // Both graph viewers of the published revision render, explain their vocabulary and log no errors.
    const viewerUrl = await evaluate('[...document.querySelectorAll("a")].find(a => a.textContent.includes("Xem sơ đồ tri thức")).href');
    const kbHash = await evaluate('location.hash');
    await send('Page.navigate', { url: viewerUrl });
    await waitFor('document.readyState === "complete" && document.querySelectorAll("#graph .node").length > 2', 'entity graph viewer');
    await viewportShot('graph-entity');
    await hover('#graph .node .role[data-term="actor"]');
    await viewportShot('graph-entity-tooltip');
    await send('Input.dispatchMouseEvent', { type: 'mouseMoved', x: 5, y: 5 });
    await send('Page.navigate', { url: viewerUrl.replace('/viewer?', '/structure.html?') });
    await waitFor('document.readyState === "complete" && document.querySelectorAll("#graph .node").length > 2', 'structure graph viewer');
    await viewportShot('graph-structure');
    await open(kbHash);
    await waitFor('!!document.querySelector(".facts")', 'kb page again');
    await evaluate(helpers);
    await evaluate('__click("button", "Hỏi đáp trên kho này")');
    await waitFor('!!__byText("button", "Bắt đầu cuộc trò chuyện")', 'chat setup');
    await evaluate(helpers);
    await evaluate('__click("button", "Bắt đầu cuộc trò chuyện")');
    await waitFor('!!document.querySelector(".ask-box")', 'chat session');
    await evaluate(helpers);
    await evaluate('__fill(document.querySelector(".ask-box textarea"), "Người sử dụng lao động phải thông báo kết quả thử việc không?"); __click("button", "Hỏi")');
    await waitFor('!!document.querySelector(".citation")', 'answer citations');
    await evaluate(helpers);
    await evaluate('__fill(document.querySelector(".ask-box textarea"), "Lương thử việc ít nhất bao nhiêu phần trăm?"); __click("button", "Hỏi")');
    await waitFor('document.querySelectorAll(".turn").length === 2', 'second answer');
    await screenshot('chat');
    await open('#/');
    await waitFor('!!document.querySelector(".kb-card:not(.new)")', 'home knowledge base cards');
    await screenshot('home');
    // Mobile layout.
    await send('Emulation.setDeviceMetricsOverride', { width: 390, height: 844, deviceScaleFactor: 1, mobile: true });
    await open('#/');
    const { data } = await send('Page.captureScreenshot', { format: 'png' });
    fs.writeFileSync(path.join(out, `${String(++shot).padStart(2, '0')}-mobile-home.png`), Buffer.from(data, 'base64'));
    assert.deepEqual(errors, [], 'Browser console errors');
    console.log('browser E2E ok');
  } finally {
    try { ws && ws.close(); } catch {}
    chrome.kill();
    await sleep(500);
    try { fs.rmSync(profile, { recursive: true, force: true }); } catch {}
  }
}
main().catch(e => { console.error(e); process.exit(1); });
