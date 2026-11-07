/* Real-browser E2E for the SvelteKit app served by `python -m legal_ai.web`: drives headless Chrome over
 * the DevTools protocol through sign-in, import, review, publish, chat, the English locale, reader
 * restrictions and account management, captures screenshots and fails on any console error.
 * Usage: node scripts/check_app_browser.cjs http://127.0.0.1:8790 <screenshot-dir> [chrome-path]
 * The store must be NEW and hold three accounts: admin/"admin password 1", phapche/"review password 1"
 * (reviewer, display name "Nguyễn Pháp Chế"), nhansu/"reader password 1" (reader). Only loopback URLs are allowed.
 * Node 22+, no npm deps.
 */
const { spawn } = require('node:child_process');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const assert = require('node:assert/strict');

const base = process.argv[2];
const out = process.argv[3];
const chromePath = process.argv[4] || ['C:/Program Files/Google/Chrome/Application/chrome.exe',
  'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe', '/usr/bin/google-chrome', '/usr/bin/chromium'].find(p => fs.existsSync(p));
if (!/^http:\/\/127\.0\.0\.1:\d+$/.test(base || '')) throw Error('Only a loopback app URL is allowed');
if (!out) throw Error('Screenshot directory required');
if (!chromePath) throw Error('Chrome or Edge not found; pass its path as the third argument');
fs.mkdirSync(out, { recursive: true });

const DOC = 'Điều 1. Thử việc (DỮ LIỆU MINH HỌA, KHÔNG PHẢI LUẬT)\n1. Người sử dụng lao động phải thông báo kết quả thử việc cho người lao động.\n2. Người lao động có quyền chấm dứt thỏa thuận thử việc mà không cần báo trước.\nĐiều 2. Tiền lương thử việc\nNgười sử dụng lao động phải trả lương thử việc ít nhất bằng 85% mức lương của công việc đó. Thời gian thử việc do hai bên thỏa thuận.\n';
const sleep = ms => new Promise(r => setTimeout(r, ms));

async function main() {
  const port = 9300 + Math.floor(Math.random() * 500);
  const profile = fs.mkdtempSync(path.join(os.tmpdir(), 'lexora-app-'));
  const chrome = spawn(chromePath, ['--headless=new', `--remote-debugging-port=${port}`, `--user-data-dir=${profile}`,
    '--no-first-run', '--no-default-browser-check', '--disable-extensions', '--lang=vi-VN', 'about:blank'], { stdio: 'ignore' });
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
      // Expected 401/403 responses of deliberate permission checks are network entries, not script errors.
      if (msg.method === 'Log.entryAdded' && msg.params.entry.level === 'error' && msg.params.entry.source !== 'network') errors.push(msg.params.entry.text);
    };
    const send = (method, params = {}) => new Promise((resolve, reject) => { const n = ++id; pending.set(n, { resolve, reject }); ws.send(JSON.stringify({ id: n, method, params })); });
    await send('Runtime.enable'); await send('Log.enable'); await send('Page.enable');
    const viewport = (width, height, mobile = false) => send('Emulation.setDeviceMetricsOverride', { width, height, deviceScaleFactor: 1, mobile });
    await viewport(1440, 900);
    const evaluate = async expression => {
      const result = await send('Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true });
      if (result.exceptionDetails) throw Error(result.exceptionDetails.exception?.description || result.exceptionDetails.text);
      return result.result.value;
    };
    const waitFor = async (expression, label) => {
      for (let i = 0; i < 120; i++) { try { if (await evaluate(expression)) return; } catch { /* page in transition */ } await sleep(100); }
      const text = await evaluate('location.pathname + " | toast: " + (document.querySelector(".toast")?.innerText ?? "") + " | " + (document.querySelector("main")?.innerText ?? "").replace(/\\s+/g, " ").slice(0, 600)').catch(() => '');
      throw Error(`Timed out waiting for ${label}; page: ${text}`);
    };
    let shot = 0;
    const capture = async (name, full = false) => {
      await sleep(300);
      let clip;
      if (full) {
        const { cssContentSize } = await send('Page.getLayoutMetrics');
        clip = { x: 0, y: 0, width: Math.ceil(cssContentSize.width), height: Math.min(Math.ceil(cssContentSize.height), 5000), scale: 1 };
      }
      const { data } = await send('Page.captureScreenshot', { format: 'png', captureBeyondViewport: full, ...(clip ? { clip } : {}) });
      const file = path.join(out, `${String(++shot).padStart(2, '0')}-${name}.png`);
      fs.writeFileSync(file, Buffer.from(data, 'base64'));
      console.log('screenshot', file);
    };
    const helpers = `
      window.__q = (sel, text) => [...document.querySelectorAll(sel)].find(e => !text || e.textContent.trim().includes(text));
      window.__click = (sel, text) => { const e = __q(sel, text); if (!e) throw Error('No ' + sel + ' ' + (text || '')); e.click(); return true; };
      window.__fill = (el, value) => { el.value = value; el.dispatchEvent(new Event('input', { bubbles: true })); el.dispatchEvent(new Event('change', { bubbles: true })); return true; };
      window.__select = (text) => {
        for (const p of document.querySelectorAll('[data-uv]')) {
          const walker = document.createTreeWalker(p, NodeFilter.SHOW_TEXT); const nodes = []; let n, all = '';
          while ((n = walker.nextNode())) { nodes.push([n, all.length]); all += n.data; }
          const at = all.indexOf(text); if (at < 0) continue;
          const locate = pos => { for (const [node, start] of nodes) if (pos <= start + node.data.length) return [node, pos - start]; };
          const r = document.createRange(); r.setStart(...locate(at)); r.setEnd(...locate(at + text.length));
          const s = getSelection(); s.removeAllRanges(); s.addRange(r); return true;
        }
        throw Error('Text not found in statute: ' + text);
      };`;
    const open = async pathname => {
      await send('Page.navigate', { url: base + pathname });
      await waitFor('document.readyState === "complete" && !!document.querySelector("main")', 'page ' + pathname);
      await evaluate(helpers);
    };
    const hover = async selector => {
      await evaluate(`document.querySelector(${JSON.stringify(selector)}).scrollIntoView({ block: 'center' }); true`);
      await sleep(250);
      const box = await evaluate(`(() => { const r = document.querySelector(${JSON.stringify(selector)}).getClientRects()[0]; return { x: r.left + r.width / 2, y: r.top + r.height / 2 }; })()`);
      await send('Input.dispatchMouseEvent', { type: 'mouseMoved', x: box.x, y: box.y });
      await waitFor('!!document.getElementById("glossary-tip")', 'glossary tooltip for ' + selector);
    };
    const login = async (username, password) => {
      await open('/login');
      await waitFor('!!document.querySelector("input[name=username]")', 'login form');
      await evaluate(`__fill(document.querySelector('input[name=username]'), ${JSON.stringify(username)}); __fill(document.querySelector('input[name=password]'), ${JSON.stringify(password)}); document.querySelector('form button[type=submit]').click(); true`);
      await waitFor('location.pathname === "/" && !!document.querySelector("h1")', 'home after login as ' + username);
      await evaluate(helpers);
    };
    const logout = async () => {
      await evaluate('__click(".who"); true');
      await waitFor('!!__q(".menu button")', 'user menu');
      await evaluate('__click(".menu button"); true');
      await waitFor('location.pathname === "/login"', 'login after logout');
    };

    // Anonymous visitors land on the login page; the About page is public.
    await open('/');
    await waitFor('location.pathname === "/login" && !!document.querySelector("input[name=password]")', 'redirect to login');
    await capture('login');
    await open('/about');
    await waitFor('document.body.innerText.includes("ĐK4")', 'about page');
    await capture('about', true);

    // A wrong password shows one generic message.
    await open('/login');
    await waitFor('!!document.querySelector("input[name=username]")', 'login form');
    await evaluate(`__fill(document.querySelector('input[name=username]'), 'phapche'); __fill(document.querySelector('input[name=password]'), 'wrong password'); document.querySelector('form button[type=submit]').click(); true`);
    await waitFor('!!document.querySelector("#login-error")', 'login error');

    // Reviewer: import a synthetic document into a new public base.
    await login('phapche', 'review password 1');
    await waitFor('document.body.innerText.includes("Nguyễn Pháp Chế")', 'greeting with display name');
    await capture('home-empty');
    await open('/import');
    await waitFor('!!__q("label.choice", "Dán nội dung")', 'import form');
    await evaluate('__q("label.choice", "Dán nội dung").querySelector("input").click(); true');
    await waitFor('!!document.querySelector("textarea")', 'paste textarea');
    await evaluate(`(() => {
      const fields = [...document.querySelectorAll('.field input:not([type])')];
      __fill(fields[0], 'Quy định thử việc (minh họa)');
      __fill(document.querySelector('textarea'), ${JSON.stringify(DOC)});
      __q('label.check').querySelector('input').click();
      __fill([...document.querySelectorAll('.field input')].find(i => i.placeholder && i.placeholder.includes('Hợp đồng')), 'Hợp đồng lao động');
      __q('label.choice', 'Công khai').querySelector('input').click();
      return true; })()`);
    await capture('import', true);
    await evaluate('__click("button[type=submit]", "Tách quy phạm")');
    await waitFor('location.pathname.startsWith("/drafts/") && !!document.querySelector(".paper [data-uv]")', 'review page');
    await evaluate(helpers);
    await capture('review');
    await capture('review-full', true);

    // The glossary explains a role on hover, with a highlighted example.
    await hover('.card .slots .term[data-term="actor"]');
    assert(await evaluate('document.getElementById("glossary-tip").textContent.includes("Chủ thể") && !!document.querySelector("#glossary-tip mark")'), 'actor tooltip');
    await capture('review-tooltip');
    await send('Input.dispatchMouseEvent', { type: 'mouseMoved', x: 4, y: 880 });

    // Approve the focused norm, then edit norm 1's object from a selection in the statute.
    await evaluate('document.querySelector(".flag.pending").click(); true');
    await waitFor('!!document.querySelector(".card .decide-approve")', 'norm card');
    await evaluate('document.querySelector(".card .decide-approve").click(); true');
    await waitFor('!!document.querySelector(".flag.approve")', 'approved flag');
    await evaluate('__q(".flag", "1").click(); true');
    await waitFor('!!__q(".card .btn.quiet", "Sửa")', 'edit button');
    await evaluate('__click(".card .btn.quiet", "Sửa")');
    await waitFor('!!document.querySelector(".editor select")', 'editor');
    await evaluate('(() => { const s = document.querySelector(".editor select"); s.value = "object"; s.dispatchEvent(new Event("change", { bubbles: true })); return true; })()');
    await evaluate('__select("kết quả thử việc cho người lao động"); __click(".editor .btn.primary"); true');
    await waitFor('document.querySelector(".card").innerText.includes("Đã chỉnh sửa")', 'edited norm');
    await capture('review-edited');
    await evaluate('__select("chấm dứt thỏa thuận thử việc"); true');
    await waitFor('!!document.querySelector(".selection-add")', 'floating add-from-selection button');
    await capture('review-selection');
    await evaluate('getSelection().removeAllRanges(); true');
    await waitFor('!document.querySelector(".selection-add")', 'floating button hides without a selection');

    // The sentence without a norm: add one by hand, then decide every remaining item.
    await evaluate('document.querySelector(".flag.gapflag").click(); true');
    await waitFor('!!document.querySelector(".gapcard")', 'gap card');
    await evaluate('__click(".gapcard .btn.primary"); true');
    await waitFor('[...document.querySelectorAll(".card .chip")].some(c => c.textContent.includes("Thêm thủ công"))', 'manual norm');
    await evaluate('__click(".card .btn.quiet", "Sửa")');
    await waitFor('!!document.querySelector(".editor .danger")', 'delete action inside the editor of a manual norm');
    await capture('review-manual-editor');
    await evaluate('__click(".editor .btn.quiet", "Xong")');
    for (let i = 0; i < 6; i++) {
      const clicked = await evaluate('(() => { const b = [...document.querySelectorAll(".articles .batch button")].find(b => /^Duyệt|^Đánh dấu/.test(b.textContent.trim())); if (b) { b.click(); return true; } return false; })()');
      if (!clicked) break;
      await sleep(600);
    }
    await waitFor('document.querySelector(".bar").innerText.includes("Đã xử lý tất cả")', 'all decided');
    await capture('review-decided');

    // Preview and publish; the reviewer of record is the signed-in account.
    await evaluate('__click(".bar a.btn.primary")');
    await waitFor('location.pathname.endsWith("/preview") && !!document.querySelector(".confirm textarea")', 'preview');
    await evaluate(helpers);
    assert(await evaluate('document.querySelector(".confirm").innerText.includes("Nguyễn Pháp Chế")'), 'reviewer shown from the session');
    await evaluate('__fill(document.querySelector(".confirm textarea"), "Đối chiếu từng quy phạm với nguyên văn (kiểm thử tự động)"); document.querySelector(".confirm input[type=checkbox]").click(); true');
    await capture('preview', true);
    await evaluate('document.querySelector(".confirm button[type=submit]").click(); true');
    await waitFor('location.pathname.startsWith("/kb/") && !!document.querySelector(".page-head .facts")', 'knowledge base after publish');
    await evaluate(helpers);
    assert(await evaluate('document.body.innerText.includes("Nguyễn Pháp Chế (phapche)")'), 'revision reviewer');
    await capture('kb');

    // The knowledge graph opens inside the app: a norm, its parts, and their verbatim evidence.
    const kbPath = await evaluate('location.pathname');
    await evaluate('__click("a.btn", "Xem sơ đồ tri thức")');
    await waitFor('location.pathname.endsWith("/graph") && document.querySelectorAll(".stage canvas").length > 0 && !!document.querySelector(".inspector .slots")', 'graph page');
    await evaluate(helpers);
    // First visit: the guide explains the page; it closes and stays closed.
    await waitFor('!!document.getElementById("graph-guide")', 'graph guide on first visit');
    await capture('graph-guide');
    await evaluate('__click("#graph-guide .btn.primary"); true');
    await waitFor('!document.getElementById("graph-guide")', 'guide closed');
    await sleep(600);
    await capture('graph-norm');
    // Picking a part reads its evidence without moving the view.
    const viewBefore = await evaluate('document.querySelector(".stage .canvas").dataset.view || ""');
    const oneCount = Number(await evaluate('document.querySelector(".stage .canvas").dataset.nodes'));
    await evaluate('document.querySelector(".inspector .slots .linkish").click(); true');
    await waitFor('!!document.querySelector(".inspector blockquote mark:not(.plain)")', 'part evidence in its role colour');
    await sleep(400);
    assert.equal(await evaluate('document.querySelector(".stage .canvas").dataset.view || ""'), viewBefore, 'selecting a node keeps the viewport');
    await capture('graph-part');
    // All norms at once, one row each.
    await evaluate('__click(".toolbar .segmented button", "Tất cả quy phạm"); true');
    await waitFor(`Number(document.querySelector(".stage .canvas").dataset.nodes) > ${oneCount}`, 'all-norms graph shows more nodes');
    await sleep(500);
    assert.ok(Number((await evaluate('document.querySelector(".stage .canvas").dataset.bounds')).split(':')[0]) >= 0, 'all-norms rows start inside the canvas');
    await capture('graph-all');
    // Side columns hide and come back.
    await evaluate('__click(".toolbar .btn", "Danh sách"); __click(".toolbar .btn", "Chi tiết"); true');
    await waitFor('!document.querySelector(".graph-page aside")', 'side columns hidden');
    await sleep(400);
    await capture('graph-canvas-only');
    await evaluate('__click(".toolbar .btn", "Danh sách"); __click(".toolbar .btn", "Chi tiết"); true');
    await waitFor('document.querySelectorAll(".graph-page aside").length === 2', 'side columns back');
    await evaluate('__click(".toolbar .segmented button", "Một quy phạm"); true');
    await evaluate('__click(".toolbar .segmented button", "Cấu trúc văn bản")');
    await waitFor('[...document.querySelectorAll(".segmented button")].some(b => b.getAttribute("aria-pressed") === "true" && b.textContent.includes("Cấu trúc"))', 'structure view');
    await sleep(600);
    assert.ok(Number((await evaluate('document.querySelector(".stage .canvas").dataset.bounds')).split(':')[0]) >= 0, 'structure tree starts inside the canvas');
    await capture('graph-structure');
    await open(kbPath);
    await waitFor('!!document.querySelector(".page-head .facts")', 'knowledge base again');

    // Ask the base; citations open as statute slips.
    await evaluate('__click("button.btn.primary", "Hỏi đáp trên kho này")');
    await waitFor('location.pathname.startsWith("/chat/") && !!document.querySelector(".ask textarea")', 'chat');
    await evaluate(helpers);
    await evaluate('__fill(document.querySelector(".ask textarea"), "Lương thử việc ít nhất bao nhiêu phần trăm?"); true');
    await waitFor('!document.querySelector(".ask button[type=submit]").disabled', 'ask button enabled');
    await evaluate('document.querySelector(".ask button[type=submit]").click(); true');
    await waitFor('!!document.querySelector(".slip blockquote mark")', 'citation');
    await capture('chat');

    // English locale: interface strings switch, statute quotes stay Vietnamese.
    await evaluate('document.querySelector(".lang").click(); true');
    await waitFor('document.querySelector("h1").textContent.trim() === "Ask" && document.documentElement.lang === "en"', 'English locale');
    await capture('chat-en');
    await evaluate('document.querySelector(".lang").click(); true');
    await waitFor('document.documentElement.lang === "vi"', 'Vietnamese locale');
    await logout();

    // Reader: published bases only, no authoring navigation, authoring pages refuse.
    await login('nhansu', 'reader password 1');
    assert(!(await evaluate('[...document.querySelectorAll(".topbar nav a")].some(a => a.getAttribute("href") === "/import")')), 'reader has no import link');
    await waitFor('document.body.innerText.includes("Hợp đồng lao động")', 'reader sees the published base');
    await capture('reader-home');
    await open('/import');
    await waitFor('document.body.innerText.includes("không có quyền")', 'import forbidden for reader');
    await open('/admin/users');
    await waitFor('document.body.innerText.includes("không có quyền")', 'admin forbidden for reader');
    await open('/');
    await waitFor('!!document.querySelector(".who")', 'reader home again');
    await evaluate(helpers);
    await logout();

    // Admin: create an account.
    await login('admin', 'admin password 1');
    await open('/admin/users');
    await waitFor('!!document.querySelector(".create input")', 'accounts page');
    await evaluate(`(() => { const f = document.querySelectorAll('.create .field input'); __fill(f[0], 'ketoan'); __fill(f[1], 'Lê Kế Toán'); __fill(f[2], 'new account pass'); document.querySelector('.create button[type=submit]').click(); return true; })()`);
    await waitFor('document.querySelector(".table").innerText.includes("Lê Kế Toán")', 'created account');
    await capture('admin-users');

    // Phone width: the overview and chat stay usable.
    await viewport(390, 844, true);
    await open('/');
    await waitFor('!!document.querySelector("h1")', 'mobile home');
    await capture('mobile-home');
    assert.deepEqual(errors, [], 'Browser console errors');
    console.log('app browser E2E ok');
  } catch (e) {
    if (errors.length) console.error('Browser console errors before the failure:\n' + errors.join('\n'));
    throw e;
  } finally {
    try { ws && ws.close(); } catch {}
    chrome.kill();
    await sleep(500);
    try { fs.rmSync(profile, { recursive: true, force: true }); } catch {}
  }
}
main().catch(e => { console.error(e); process.exit(1); });
