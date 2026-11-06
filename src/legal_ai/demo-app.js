/* Lexora local workspace. Same-origin requests only; all text is inserted as text, never as HTML. */
(() => {
  'use strict';
  const token = document.querySelector('meta[name="lexora-token"]').content;
  const view = document.getElementById('view');
  const toastEl = document.getElementById('toast');
  let state = null;
  let draft = null;
  const ui = { filter: 'all', editing: null, editField: 'object', editModality: 'obligation', chatPreselect: [], reviewer: '' };

  const MODALITY = { obligation: 'Nghĩa vụ', prohibition: 'Điều cấm', entitlement: 'Quyền', permission: 'Được phép',
    definition: 'Định nghĩa', procedure: 'Thủ tục', unknown: 'Chưa rõ loại' };
  const MODALITY_TERM = { unknown: 'unknown_modality' };
  const SLOT = { actor: 'Chủ thể', action: 'Hành vi', object: 'Đối tượng', beneficiary: 'Bên thụ hưởng', recipient: 'Bên nhận',
    outcome: 'Kết quả', conditions: 'Điều kiện', exceptions: 'Ngoại lệ', quantities: 'Định lượng', deadlines: 'Thời hạn' };
  const SLOT_ORDER = ['actor', 'action', 'object', 'conditions', 'exceptions', 'quantities', 'deadlines', 'beneficiary', 'recipient', 'outcome'];
  const STATUS = { sources_found: 'Các đoạn đã duyệt liên quan', answered: 'Câu trả lời do model tạo từ các đoạn đã duyệt',
    insufficient_evidence: 'Chưa tìm thấy căn cứ trong các kho đã chọn', provider_disabled: 'Model chưa được bật',
    transfer_not_approved: 'Chưa đồng ý gửi dữ liệu cho lượt này', private_transfer_blocked: 'Không gửi dữ liệu của kho riêng tư',
    provider_error: 'Model chưa trả lời được', answer_rejected: 'Câu trả lời của model không đạt kiểm tra trích dẫn' };

  // Helpers -----------------------------------------------------------------
  function h(tag, attrs, ...children) {
    const e = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if (v === null || v === undefined || v === false) continue;
      if (k === 'class') e.className = v;
      else if (k === 'text') e.textContent = v;
      else if (k.startsWith('on')) e.addEventListener(k.slice(2), v);
      else if (k === 'checked' || k === 'disabled' || k === 'selected') e[k] = Boolean(v);
      else if (k === 'value') e.value = v;
      else e.setAttribute(k, v === true ? '' : v);
    }
    for (const child of children.flat(Infinity)) {
      if (child === null || child === undefined || child === false) continue;
      e.append(child instanceof Node ? child : document.createTextNode(String(child)));
    }
    return e;
  }
  // A glossary word: dotted underline, explanation on hover, focus or tap (term-tip.js).
  function term(key, text, focusable = true) {
    return h('span', { class: 'term', 'data-term': key, tabindex: focusable ? 0 : null }, text || (window.LexoraTerms && window.LexoraTerms.has(key) ? window.LexoraTerms.entry(key).term : key));
  }
  const ICONS = {
    upload: 'M12 15V3m0 0-4.5 4.5M12 3l4.5 4.5M4 15v4a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-4',
    review: 'M9 11l3 3 8-8M20 12v7a2 2 0 0 1-2 2H6a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h9',
    chat: 'M20 12a8 8 0 0 1-11.6 7.1L4 20l1-4.1A8 8 0 1 1 20 12z',
    quote: 'M7 7h4v4c0 3-1.5 5-4 6M14 7h4v4c0 3-1.5 5-4 6',
    person: 'M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8zm-7 9a7 7 0 0 1 14 0',
    lock: 'M6 11h12v10H6zM8.5 11V7.5a3.5 3.5 0 0 1 7 0V11',
    history: 'M3 12a9 9 0 1 0 3-6.7L3 8m0-5v5h5m4-1v5l3 2',
    doc: 'M14 3H7a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V8zm0 0v5h5M9 13h6M9 17h4',
    graph: 'M6 6m-2.5 0a2.5 2.5 0 1 0 5 0a2.5 2.5 0 1 0-5 0M18 6m-2.5 0a2.5 2.5 0 1 0 5 0a2.5 2.5 0 1 0-5 0M12 18m-2.5 0a2.5 2.5 0 1 0 5 0a2.5 2.5 0 1 0-5 0M8 7.5l3 8M16 7.5l-3 8',
    plus: 'M12 5v14M5 12h14',
    check: 'M5 12.5l4.5 4.5L19 7',
    x: 'M6 6l12 12M18 6L6 18',
    edit: 'M4 20h4L19 9l-4-4L4 16zM13.5 6.5l4 4',
    warn: 'M12 9v4m0 3.5v.5M10.3 4.2 2.8 17.5A2 2 0 0 0 4.5 20.5h15a2 2 0 0 0 1.7-3L13.7 4.2a2 2 0 0 0-3.4 0z',
    arrow: 'M5 12h14m-5-5 5 5-5 5',
  };
  function icon(name) {
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('viewBox', '0 0 24 24');
    svg.setAttribute('class', 'i');
    svg.setAttribute('aria-hidden', 'true');
    const path = document.createElementNS('http://www.w3.org/2000/svg', 'path');
    path.setAttribute('d', ICONS[name]);
    svg.append(path);
    return svg;
  }
  function mount(...nodes) {
    view.replaceChildren(...nodes.flat(Infinity).filter(n => n !== null && n !== undefined && n !== false));
  }
  async function api(path, body) {
    const response = await fetch(path, body ? { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-Lexora-Token': token }, body: JSON.stringify(body) } : {});
    const value = await response.json();
    if (!response.ok) {
      const error = new Error(value.error || 'Yêu cầu không thành công');
      error.code = value.code;
      throw error;
    }
    return value;
  }
  let toastTimer;
  function toast(text, error = false) {
    toastEl.textContent = text;
    toastEl.className = error ? 'error' : '';
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => { toastEl.textContent = ''; }, error ? 9000 : 4000);
  }
  async function act(button, fn) {
    if (button) button.disabled = true;
    try { await fn(); } catch (e) { toast(e.message, true); } finally { if (button && button.isConnected) button.disabled = false; }
  }
  function when(iso) {
    return new Date(iso).toLocaleString('vi-VN', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' });
  }
  function kbName(id) { return (state.knowledge_bases.find(k => k.id === id) || {}).name; }
  function targetText(target, kbLabel) {
    return target.mode === 'new' ? `Tạo kho mới “${target.name}”` : `Gộp vào kho “${kbLabel || kbName(target.kb_id) || ''}”`;
  }
  function claimTitle(c) {
    const part = name => c.slots[name] && c.slots[name].state === 'present' ? c.slots[name].text : '';
    const action = part('action');
    const object = part('object');
    const text = [part('actor'), action, object && !action.includes(object) ? object : ''].filter(Boolean).join(' ');
    return text || (c.quote && c.quote.quote) || c.label;
  }
  function unitLabel(unitId) {
    const names = { article: 'Điều', clause: 'khoản', point: 'điểm', chapter: 'Chương', section: 'Mục' };
    return unitId.split('/').slice(1).map(part => {
      const [type, ...rest] = part.split('-');
      return `${names[type] || type} ${rest.join('-')}`;
    }).join(', ');
  }
  function pageHead(title, lead, ...actions) {
    return h('header', { class: 'page-head' }, h('div', {}, h('h1', { text: title }), lead ? h('p', {}, lead) : null),
      actions.length ? h('div', { class: 'actions' }, actions) : null);
  }
  function stepper(current) {
    const steps = ['Chọn văn bản và nơi lưu', 'Duyệt quy phạm', 'Xem trước và công bố'];
    return h('ol', { class: 'stepper', 'aria-label': 'Các bước nhập tài liệu' },
      steps.map((s, i) => h('li', { class: i + 1 < current ? 'done' : i + 1 === current ? 'current' : '', 'aria-current': i + 1 === current ? 'step' : null, text: s })));
  }

  // Navigation ----------------------------------------------------------------
  async function refreshState() { state = await api('/api/state'); }
  function renderNav(parts) {
    const section = { '': 'home', kb: 'home', import: 'import', draft: 'import', chat: 'chat', about: 'about' }[parts[0]] || 'home';
    document.querySelectorAll('#navMain a').forEach(a => {
      if (a.dataset.nav === section && !(parts[0] === 'kb' || parts[0] === 'draft')) a.setAttribute('aria-current', 'page'); else a.removeAttribute('aria-current');
    });
    const kbs = document.getElementById('navKbs');
    kbs.replaceChildren(...(state.knowledge_bases.length ? state.knowledge_bases.map(kb => h('li', {},
      h('a', { href: `#/kb/${kb.id}`, 'aria-current': parts[0] === 'kb' && parts[1] === kb.id ? 'page' : null },
        h('span', { text: kb.name }), h('span', { class: 'count', text: kb.approved_claims, title: 'Quy phạm đã duyệt' }),
        h('span', { class: 'sub', text: `${kb.documents} tài liệu` })))) : [h('li', { class: 'nav-empty', text: 'Chưa có kho nào.' })]));
    const drafts = state.drafts.filter(d => d.status === 'draft');
    document.getElementById('navDrafts').replaceChildren(...(drafts.length ? drafts.map(d => h('li', {},
      h('a', { href: `#/draft/${d.id}`, 'aria-current': parts[0] === 'draft' && parts[1] === d.id ? 'page' : null },
        h('span', { text: d.title }), ['queued', 'running'].includes(d.extraction_state)
          ? h('span', { class: 'count', text: 'AI…', title: 'Đang tách bằng AI' })
          : h('span', { class: 'count', text: `${Math.min(d.decided, d.claims)}/${d.claims}`, title: 'Quy phạm đã quyết định' }),
        h('span', { class: 'sub', text: targetText(d.target, d.kb_name) })))) : [h('li', { class: 'nav-empty', text: 'Không có bản nháp.' })]));
  }
  async function route() {
    const parts = location.hash.replace(/^#\/?/, '').split('/');
    try {
      await refreshState();
      renderNav(parts);
      const page = parts[0];
      if (page === 'kb') await renderKb(parts[1]);
      else if (page === 'import') await renderImport(parts[1]);
      else if (page === 'draft') await renderDraft(parts[1], parts[2]);
      else if (page === 'chat') await renderChat(parts[1]);
      else if (page === 'about') renderAbout();
      else renderHome();
    } catch (e) {
      mount(h('div', { class: 'section notice error', text: e.message }));
    }
  }
  function go(hash) { if (location.hash === hash) route(); else location.hash = hash; }

  // Home and KB --------------------------------------------------------------
  // Introduction ---------------------------------------------------------------
  // One annotated sentence shows what Lexora extracts; every coloured part explains itself on hover.
  function specimen() {
    const seg = (key, text) => h('span', { class: 'seg', 'data-term': key, tabindex: 0 }, text);
    const row = (key, color, value) => [h('dt', {}, h('i', { style: `background:${color}` }), term(key)), h('dd', { text: value })];
    return h('figure', { class: 'specimen', style: 'margin:0' },
      h('div', { class: 'label' }, h('span', { text: 'Một câu, sau khi tách' }), h('span', {}, term('norm', 'Quy phạm'), ': ', term('obligation', 'Nghĩa vụ'))),
      h('p', { class: 'sentence' }, seg('conditions', 'Khi kết thúc thời gian thử việc'), ', ', seg('actor', 'người sử dụng lao động'), ' ', seg('obligation', 'phải'), ' ',
        seg('action', 'thông báo'), ' ', seg('object', 'kết quả thử việc'), ' cho ', seg('recipient', 'người lao động'), '.'),
      h('dl', {}, row('actor', 'var(--m-obligation)', 'người sử dụng lao động'), row('action', 'var(--m-entitlement)', 'thông báo'),
        row('object', 'var(--m-permission)', 'kết quả thử việc'), row('recipient', '#8a5a3a', 'người lao động'),
        row('conditions', 'var(--m-procedure)', 'khi kết thúc thời gian thử việc')),
      h('p', { class: 'hint', text: 'Rê chuột vào phần tô màu hoặc chữ gạch chân chấm để xem định nghĩa và ví dụ. Câu ví dụ chỉ để minh họa.' }));
  }
  function introBlock(compact) {
    return h('section', { class: `intro ${compact ? 'compact' : ''}`, 'aria-label': 'Giới thiệu Lexora' },
      h('div', {},
        h('span', { class: 'eyebrow', text: 'Đồ án tốt nghiệp · Hỏi đáp pháp luật lao động có kiểm chứng' }),
        h(compact ? 'h2' : 'h1', { class: 'lead', text: 'Mỗi câu trả lời đều chỉ về đúng câu trong luật.' }),
        h('p', { class: 'pitch' }, 'Lexora biến văn bản pháp luật thành ', term('norm', 'các quy phạm'), ' có cấu trúc: ai, phải làm gì, trong điều kiện nào. Bạn duyệt từng quy phạm với nguyên văn; chỉ những gì bạn duyệt mới được dùng để trả lời câu hỏi, kèm trích dẫn chính xác đến từng ký tự.'),
        h('div', { class: 'actions' },
          state.knowledge_bases.length ? h('a', { class: 'btn primary', href: '#/chat' }, icon('chat'), 'Đặt câu hỏi') : h('a', { class: 'btn primary', href: '#/import' }, icon('upload'), 'Nhập văn bản đầu tiên'),
          h('a', { class: 'btn', href: '#/about' }, 'Lexora hoạt động thế nào', icon('arrow')))),
      specimen());
  }
  function renderHome() {
    const pending = state.drafts.filter(d => d.status === 'draft');
    const kbs = state.knowledge_bases;
    const continueDraft = pending.length ? h('div', { class: 'notice info', style: 'display:flex;justify-content:space-between;align-items:center;gap:12px;flex-wrap:wrap' },
      h('span', {}, `Bạn đang duyệt dở “${pending[0].title}”.`), h('a', { class: 'btn', href: `#/draft/${pending[0].id}`, text: 'Tiếp tục duyệt' })) : null;
    if (!kbs.length) {
      mount(introBlock(false), continueDraft, workflowSteps());
      return;
    }
    mount(
      introBlock(true),
      continueDraft,
      pageHead('Kho tri thức', 'Mỗi kho giữ lịch sử từng lần cập nhật. Câu trả lời chỉ dùng các quy phạm đã được duyệt.'),
      h('div', { class: 'kb-grid' },
        kbs.map(kb => h('a', { class: 'kb-card', href: `#/kb/${kb.id}` },
          h('div', { style: 'display:flex;justify-content:space-between;gap:10px;align-items:flex-start' }, h('h3', { text: kb.name }),
            h('span', { class: `tag ${kb.data_class}`, text: kb.data_class === 'private' ? 'Riêng tư' : 'Công khai' })),
          kb.description ? h('p', { class: 'desc', text: kb.description }) : null,
          h('div', { class: 'stats' },
            h('div', {}, h('b', { text: kb.documents }), h('span', { text: 'tài liệu' })),
            h('div', {}, h('b', { text: kb.approved_claims }), h('span', { text: 'quy phạm đã duyệt' }))),
          h('span', { class: 'when', text: `Cập nhật ${when(kb.updated_at)}` }))),
        h('a', { class: 'kb-card new', href: '#/import' }, h('span', { class: 'plus' }, icon('plus')), h('strong', { text: 'Nhập tài liệu' }), h('span', { class: 'muted small', text: 'Tạo kho mới hoặc bổ sung vào kho có sẵn' }))));
  }
  function workflowSteps() {
    const step = (ico, title, text) => h('li', {}, h('span', { class: 'ico' }, icon(ico)), h('h3', { text: title }), h('p', {}, text));
    return h('ol', { class: 'steps', 'aria-label': 'Ba bước làm việc với Lexora' },
      step('upload', 'Nhập văn bản', 'Chọn văn bản trong thư viện có kiểm tra checksum, tải tệp TXT hoặc dán nội dung. Lexora chia văn bản thành Điều, khoản, điểm.'),
      step('review', 'Duyệt quy phạm', ['Lexora đề xuất các quy phạm kèm ', term('evidence', 'bằng chứng'), ' nguyên văn. Bạn duyệt, loại hoặc sửa từng quy phạm rồi công bố vào kho.']),
      step('chat', 'Hỏi đáp có trích dẫn', 'Câu trả lời chỉ dựa trên quy phạm đã duyệt và dẫn về đúng đoạn trong văn bản gốc. Không tìm thấy căn cứ thì Lexora nói rõ là không có.'));
  }
  // Written for the thesis committee: research question, contributions, architecture,
  // evaluation design and an honest implementation status. Targets are plans, not results.
  function renderAbout() {
    const value = (ico, title, text) => h('div', { class: 'value' }, h('span', { class: 'ico' }, icon(ico)), h('h3', { text: title }), h('p', {}, text));
    const contribution = (n, title, text) => h('li', {}, h('span', { class: 'n', text: n }), h('div', {}, h('h3', { text: title }), h('p', {}, text)));
    const flow = (items) => h('ol', { class: 'flow', 'aria-label': 'Luồng xử lý' }, items.map(([title, sub, kind]) =>
      h('li', { class: kind || '' }, h('strong', { text: title }), sub ? h('span', { text: sub }) : null)));
    const status = (done, text) => h('li', { class: done ? 'done' : 'plan' }, h('span', { class: 'mark' }, icon(done ? 'check' : 'history')), h('span', {}, text));
    mount(
      introBlock(false),

      h('h2', { class: 'h-section', text: 'Bài toán và câu hỏi nghiên cứu' }),
      h('div', { class: 'compare' },
        h('div', {}, h('h3', {}, icon('warn'), 'RAG thông thường trên văn bản luật'), h('ul', {},
          h('li', { text: 'Cắt văn bản thành đoạn cố định, dễ tách rời quy định khỏi điều kiện hoặc ngoại lệ của nó.' }),
          h('li', { text: 'Trích dẫn ở mức đoạn, khó kiểm tra câu trả lời dựa vào câu nào.' }),
          h('li', { text: 'Tri thức trích xuất bằng mô hình ngôn ngữ chưa được kiểm chứng trước khi dùng.' }))),
        h('div', {}, h('h3', {}, icon('check'), 'Hướng tiếp cận của Lexora'), h('ul', {},
          h('li', {}, 'Biểu diễn văn bản thành ', term('norm', 'quy phạm'), ' có cấu trúc: ', term('actor', 'chủ thể'), ', ', term('action', 'hành vi'), ', ', term('modality', 'tính quy phạm'), ', ', term('conditions', 'điều kiện'), ', ', term('exceptions', 'ngoại lệ'), '...'),
          h('li', {}, 'Mỗi thành phần neo vào một ', term('evidence', 'bằng chứng'), ' nguyên văn, kiểm tra được bằng máy.'),
          h('li', {}, 'Kiểm chứng tự động, sau đó người duyệt quyết định; chỉ ', term('approved', 'quy phạm đã duyệt'), ' được dùng để trả lời.')))),
      h('section', { class: 'section rq' },
        h('span', { class: 'eyebrow', text: 'Câu hỏi nghiên cứu' }),
        h('p', { class: 'rq-text', text: 'So với truy xuất trên các đoạn văn bản cắt cố định hoặc cắt theo cấu trúc, một kho tri thức gồm các quy phạm có bằng chứng, đã qua kiểm chứng, có giúp hệ thống hỏi đáp pháp luật lao động truy xuất đúng căn cứ hơn, trích dẫn chính xác hơn và từ chối đúng khi thiếu căn cứ hay không?' })),

      h('h2', { class: 'h-section', text: 'Đóng góp chính' }),
      h('ol', { class: 'contributions' },
        contribution('1', 'Lược đồ quy phạm có bằng chứng', 'Hợp đồng dữ liệu phiên bản 1.0.0-pilot: mỗi thành phần của quy phạm kèm đoạn trích nguyên văn, vị trí ký tự Unicode chính xác và mã SHA-256 của văn bản đã chuẩn hóa. Trích dẫn sai một ký tự là bị phát hiện.'),
        contribution('2', 'Kiểm chứng tự động kết hợp người duyệt', ['Kiểm tra lược đồ, tham chiếu và bằng chứng; giao diện duyệt đặt quy phạm cạnh nguyên văn; mọi ', term('gap', 'câu chưa có quy phạm'), ' phải được xử lý trước khi công bố, tránh bỏ sót nội dung.']),
        contribution('3', 'Hỏi đáp chỉ trên tri thức đã duyệt', 'Truy xuất BM25 không phân biệt dấu, tùy chọn kết hợp tìm theo ngữ nghĩa. Khi dùng mô hình ngôn ngữ, câu trả lời bị từ chối nếu trích dẫn nằm ngoài các đoạn đã cung cấp.'),
        contribution('4', 'Thiết kế thực nghiệm có kiểm soát', 'Bốn cấu hình dùng chung nguồn, câu hỏi, mô hình sinh và ngân sách ngữ cảnh, chỉ khác nguồn tri thức, để tách riêng tác động của cấu trúc và của bước kiểm chứng.')),

      h('h2', { class: 'h-section', text: 'Kiến trúc hệ thống' }),
      h('section', { class: 'section' },
        flow([['Nguồn chính thống', 'Cổng VBPL'], ['Bản chụp bất biến', 'kèm checksum'], ['Chuẩn hóa', 'mốc neo của mọi vị trí'], ['Phân cấp', 'Chương, Điều, khoản, điểm'],
          ['Tách quy phạm', 'theo quy tắc hoặc bằng AI', 'accent'], ['Kiểm chứng tự động', 'lược đồ, tham chiếu, bằng chứng', 'accent'], ['Người duyệt', 'duyệt, loại, sửa', 'accent'],
          ['Kho có phiên bản', 'mỗi lần công bố một phiên bản'], ['Truy xuất', 'chỉ quy phạm đã duyệt'], ['Trả lời', 'kèm trích dẫn kiểm tra được', 'end']]),
        h('p', { class: 'muted small', style: 'margin:14px 0 0', text: 'Toàn bộ chạy cục bộ bằng Python, chỉ dùng thư viện chuẩn. Gọi mô hình ngôn ngữ là tùy chọn, phải được bật rõ ràng, và chỉ áp dụng cho kho công khai.' })),

      h('h2', { class: 'h-section', text: 'Thiết kế thực nghiệm' }),
      h('section', { class: 'section' },
        h('table', { class: 'conditions' },
          h('thead', {}, h('tr', {}, h('th', { text: 'Cấu hình' }), h('th', { text: 'Nguồn tri thức để truy xuất' }), h('th', { text: 'So sánh để trả lời' }))),
          h('tbody', {},
            h('tr', {}, h('td', {}, h('strong', { text: 'ĐK1' })), h('td', { text: 'Đoạn văn bản cắt cố định' }), h('td', { text: 'Mốc cơ sở' })),
            h('tr', {}, h('td', {}, h('strong', { text: 'ĐK2' })), h('td', { text: 'Đoạn cắt theo cấu trúc Điều, khoản, điểm' }), h('td', { text: 'ĐK2 so với ĐK1: tác động của cấu trúc văn bản' })),
            h('tr', {}, h('td', {}, h('strong', { text: 'ĐK3' })), h('td', { text: 'Kho quy phạm do mô hình ngôn ngữ trích xuất, trước kiểm chứng' }), h('td', { text: 'ĐK3 so với ĐK2: tác động của biểu diễn quy phạm' })),
            h('tr', {}, h('td', {}, h('strong', { text: 'ĐK4' })), h('td', { text: 'Cùng kho của ĐK3, sau kiểm chứng tự động' }), h('td', { text: 'ĐK4 so với ĐK3: tác động của bước kiểm chứng' })))),
        h('div', { class: 'grid-2', style: 'margin-top:20px' },
          h('div', {}, h('h3', { class: 'sub-h', text: 'Chỉ số' }), h('ul', { class: 'plain' },
            h('li', {}, h('strong', { text: 'Recall@K' }), ': tỷ lệ đơn vị luật liên quan được truy xuất'),
            h('li', {}, h('strong', { text: 'Độ chính xác trích dẫn' }), ': trích dẫn đúng căn cứ trên tổng trích dẫn'),
            h('li', {}, h('strong', { text: 'Độ bám nguồn' }), ': tỷ lệ phát biểu được bằng chứng hỗ trợ, người chấm theo rubric'),
            h('li', {}, h('strong', { text: 'Độ đúng' }), ': thang 0, 1, 2 theo rubric'),
            h('li', {}, h('strong', { text: 'Từ chối đúng' }), ': khi câu hỏi ngoài phạm vi hoặc thiếu căn cứ'),
            h('li', {}, h('strong', { text: 'Chất lượng trích xuất' }), ': precision, recall, F1 và Cohen’s kappa giữa hai người gán nhãn'))),
          h('div', {}, h('h3', { class: 'sub-h', text: 'Dữ liệu dự kiến' }), h('ul', { class: 'plain' },
            h('li', { text: 'Khoảng 150 câu hỏi: tra cứu, tổng hợp, hiệu lực và sửa đổi, ngoài phạm vi.' }),
            h('li', { text: 'Tách khoảng 70% phát triển và 30% kiểm tra giữ kín; tập kiểm tra không dùng để chọn mô hình hay tham số.' }),
            h('li', { text: '40 đến 60 điều khoản được hai người gán nhãn độc lập rồi đối soát.' }),
            h('li', { text: 'Con số là mục tiêu theo đề cương, sẽ chốt sau giai đoạn thử nghiệm.' }))))),

      h('h2', { class: 'h-section', text: 'Trạng thái hiện thực' }),
      h('section', { class: 'section' }, h('ul', { class: 'status-list' },
        status(true, 'Lấy bản chụp văn bản từ VBPL kèm checksum, phân tích Điều, khoản, điểm.'),
        status(true, 'Hợp đồng dữ liệu và bộ kiểm chứng lược đồ, tham chiếu, bằng chứng.'),
        status(true, 'Tách quy phạm theo quy tắc; tách bằng AI ở bản demo (tùy chọn, có đối chiếu nguyên văn).'),
        status(true, 'Kho tri thức nhiều phiên bản với quy trình duyệt và công bố.'),
        status(true, 'Hỏi đáp có trích dẫn trên quy phạm đã duyệt; sơ đồ quy phạm và cấu trúc văn bản.'),
        status(false, 'Pipeline bốn cấu hình ĐK1 đến ĐK4 và kho quy phạm trích xuất bằng mô hình ngôn ngữ cho ĐK3, ĐK4.'),
        status(false, 'Bộ câu hỏi đánh giá, tập gán nhãn chuẩn và chạy thực nghiệm. Chưa có kết quả.'))),

      h('h2', { class: 'h-section', text: 'Giá trị mang lại' }),
      h('div', { class: 'values' },
        value('quote', 'Truy vết được đến từng câu', 'Người đọc bấm vào trích dẫn là thấy đúng câu trong Điều, khoản, điểm gốc để tự đối chiếu.'),
        value('person', 'Con người kiểm soát tri thức', 'Máy chỉ đề xuất. Người duyệt quyết định quy phạm nào được vào kho, và mọi chỉnh sửa đều neo vào nguyên văn.'),
        value('history', 'Tái lập được', ['Bản chụp bất biến, mã băm và ', term('revision', 'phiên bản'), ' của kho cho phép chạy lại và kiểm tra lại mọi kết quả.']),
        value('lock', 'Riêng tư theo mặc định', ['Chạy trên máy này. ', term('private', 'Kho riêng tư'), ' không bao giờ gửi nội dung ra ngoài; AI chỉ dùng cho kho công khai khi người dùng đồng ý.'])),

      h('h2', { class: 'h-section', text: 'Giới hạn' }),
      h('section', { class: 'section' }, h('ul', { class: 'limits' },
        h('li', { text: 'Không phải tư vấn pháp lý; người gán nhãn không thay cho chuyên gia pháp lý.' }),
        h('li', { text: 'Hiệu lực pháp luật của văn bản (còn hiệu lực, đã sửa đổi) chưa được xác minh.' }),
        h('li', { text: 'Phạm vi thử nghiệm là một phần pháp luật lao động Việt Nam.' }),
        h('li', {}, 'Bộ tách tự động có thể bỏ sót hoặc tách sai; vì vậy mọi ', term('gap', 'câu chưa có quy phạm'), ' phải được xử lý trước khi công bố.'))));
  }

  async function renderKb(id) {
    const kb = await api('/api/kb?id=' + encodeURIComponent(id));
    const chat = h('button', { class: 'btn primary', type: 'button', disabled: !kb.approved_claims,
      onclick: () => { ui.chatPreselect = [kb.id]; go('#/chat'); } }, icon('chat'), 'Hỏi đáp trên kho này');
    const dataClass = kb.data_class === 'private' ? 'private' : 'public';
    mount(
      pageHead(kb.name, kb.description || null,
        h('a', { class: 'btn', href: `/viewer?revision=${kb.current_revision}`, target: '_blank', rel: 'noopener' }, icon('graph'), 'Xem sơ đồ tri thức'),
        h('a', { class: 'btn', href: `#/import/${kb.id}` }, icon('upload'), 'Nhập tài liệu vào kho này'), chat),
      h('dl', { class: 'facts' },
        h('div', {}, h('dt', { text: 'Tài liệu' }), h('dd', { text: kb.documents.length })),
        h('div', {}, h('dt', {}, term('approved')), h('dd', { text: kb.approved_claims })),
        h('div', {}, h('dt', {}, term('revision', 'Số phiên bản')), h('dd', { text: kb.revisions.length })),
        h('div', {}, h('dt', { text: 'Dữ liệu' }), h('dd', {}, term(dataClass, dataClass === 'private' ? 'Riêng tư' : 'Công khai')))),
      h('div', { class: 'grid-2' },
        h('section', { class: 'section' }, h('h2', { text: 'Tài liệu' }),
          h('p', { text: 'Hiệu lực pháp luật của các văn bản chưa được xác minh.' }),
          kb.documents.length ? h('ul', { class: 'list' }, kb.documents.map(d => h('li', {},
            h('div', { class: 'doc-row' }, h('span', { class: 'ico' }, icon('doc')),
              h('div', {}, h('div', { class: 'doc-title', text: d.title }), d.synthetic ? h('span', { class: 'tag synthetic', text: 'Dữ liệu minh họa' }) : null)),
            /^https:\/\//.test(d.source_url) ? h('a', { href: d.source_url, target: '_blank', rel: 'noopener', text: 'Văn bản gốc' }) : h('span', { class: 'muted small', text: 'Tệp tải lên' })))) :
            h('p', { class: 'muted', text: 'Kho chưa có tài liệu.' })),
        h('section', { class: 'section' }, h('h2', { text: 'Lịch sử cập nhật' }),
          h('p', {}, 'Mỗi lần công bố tạo một ', term('revision', 'phiên bản'), ' mới; phiên bản cũ được giữ nguyên.'),
          h('ol', { class: 'timeline' }, kb.revisions.map((r, i) => h('li', {},
            h('div', {}, h('strong', { text: when(r.created_at) }), i === 0 ? h('span', { class: 'tag current', text: 'Hiện tại', style: 'margin-left:8px' }) : null),
            h('div', { class: 'muted small', text: r.reviewer ? `${r.reviewer}: ${r.reason}` : r.reason }),
            h('details', { class: 'tech' }, h('summary', { text: 'Chi tiết' }), h('dl', {}, h('dt', { text: 'Mã phiên bản' }), h('dd', { text: r.id })))))))));
  }

  // Import step 1 -------------------------------------------------------------
  async function renderImport(presetKb) {
    const sources = (await api('/api/sources')).entries;
    const kbs = state.knowledge_bases;
    const form = { source: sources.length ? 'library' : 'file', sourceId: sources[0] && sources[0].id, title: '', text: '', synthetic: false,
      mode: presetKb && kbs.some(k => k.id === presetKb) ? 'merge' : 'new', kbId: presetKb || (kbs[0] && kbs[0].id), name: '', description: '', dataClass: 'private',
      extraction: 'rules' };
    const sourceBody = h('div', { class: 'choice-body' });
    const targetBody = h('div', { class: 'choice-body' });
    const methodBody = h('div', { class: 'choice-grid' });
    const footNote = h('span', { class: 'muted small' });
    const targetIsPublic = () => form.mode === 'new' ? form.dataClass === 'public' : (kbs.find(k => k.id === form.kbId) || {}).data_class === 'public';
    function drawMethod() {
      const aiAllowed = Boolean(state.extraction_model) && targetIsPublic();
      if (!aiAllowed) form.extraction = 'rules';
      methodBody.replaceChildren(
        radio('method', 'rules', form.extraction, 'Theo quy tắc', 'Chạy trên máy này, không gửi dữ liệu đi đâu. Tách tốt các câu theo mẫu quen thuộc.', v => { form.extraction = v; drawMethod(); }),
        state.extraction_model ? radio('method', 'llm', form.extraction, 'Bằng AI',
          targetIsPublic() ? `Gửi nội dung văn bản tới model ${state.extraction_model} để tách các câu quy tắc chưa tách được. Mọi đoạn AI đề xuất đều được đối chiếu đúng nguyên văn.`
            : 'Chỉ dùng cho kho công khai. Nội dung kho riêng tư không được gửi ra ngoài máy.', v => { form.extraction = v; drawMethod(); }, !aiAllowed) : null);
      footNote.textContent = form.extraction === 'llm' ? 'Việc tách bằng AI chạy nền; bạn sẽ thấy tiến độ ở bước sau.' : 'Việc tách chạy trên máy này, không gọi model.';
    }

    function radio(name, value, current, title, hint, onpick, disabled) {
      return h('label', { class: 'choice' }, h('strong', {}, h('input', { type: 'radio', name, value, checked: current === value, disabled,
        onchange: () => { onpick(value); } }), title), h('span', { text: hint }));
    }
    function drawSource() {
      if (form.source === 'library') {
        sourceBody.replaceChildren(h('div', { class: 'source-list' }, sources.map(s => h('label', { class: 'source-item' },
          h('input', { type: 'radio', name: 'libsrc', checked: form.sourceId === s.id, onchange: () => { form.sourceId = s.id; } }),
          h('span', { class: 'doc-title', text: s.title }), h('span', { class: 'muted small', text: `Tải ngày ${s.downloaded_at.slice(0, 10).split('-').reverse().join('/')}` })))));
      } else {
        const file = form.source === 'file' ? h('label', { class: 'field' }, 'Tệp TXT', h('span', { class: 'hint', text: 'UTF-8, tối đa 1 MB. Mỗi Điều bắt đầu bằng “Điều 1.” trên một dòng riêng.' }),
          h('input', { type: 'file', accept: '.txt,text/plain', onchange: e => act(null, async () => {
            const f = e.target.files[0];
            if (!f) return;
            if (!f.name.toLowerCase().endsWith('.txt') || f.size > 1000000) throw Error('Chỉ nhận tệp TXT UTF-8 tối đa 1 MB');
            form.text = new TextDecoder('utf-8', { fatal: true }).decode(await f.arrayBuffer());
            form.title = form.title || f.name.replace(/\.txt$/i, '');
            titleInput.value = form.title;
            toast('Đã đọc tệp. Kiểm tra tên tài liệu rồi bấm Tách quy phạm.');
          }) })) : null;
        const titleInput = h('input', { value: form.title, maxlength: 200, oninput: e => { form.title = e.target.value; } });
        sourceBody.replaceChildren(h('div', { class: 'form' }, file,
          h('label', { class: 'field' }, 'Tên tài liệu', titleInput),
          form.source === 'paste' ? h('label', { class: 'field' }, 'Nội dung', h('textarea', { placeholder: 'Điều 1. ...\n1. Người sử dụng lao động phải ...', oninput: e => { form.text = e.target.value; } }, form.text)) : null,
          h('label', { class: 'check' }, h('input', { type: 'checkbox', checked: form.synthetic, onchange: e => { form.synthetic = e.target.checked; } }),
            'Đây là dữ liệu minh họa, không phải văn bản pháp luật thật')));
      }
    }
    function drawTarget() {
      if (form.mode === 'new') {
        targetBody.replaceChildren(h('div', { class: 'form' },
          h('label', { class: 'field' }, 'Tên kho', h('input', { value: form.name, maxlength: 100, placeholder: 'Ví dụ: Hợp đồng lao động', oninput: e => { form.name = e.target.value; } })),
          h('label', { class: 'field' }, 'Mô tả', h('span', { class: 'hint', text: 'Không bắt buộc.' }), h('input', { value: form.description, maxlength: 500, oninput: e => { form.description = e.target.value; } })),
          h('div', { class: 'choice-grid' },
            radio('dataclass', 'private', form.dataClass, 'Riêng tư', 'Không bao giờ gửi nội dung kho ra ngoài máy.', v => { form.dataClass = v; drawMethod(); }),
            radio('dataclass', 'public', form.dataClass, 'Công khai', 'Cho phép gửi nội dung sang dịch vụ AI khi bạn chọn dùng AI.', v => { form.dataClass = v; drawMethod(); }))));
      } else {
        targetBody.replaceChildren(h('div', { class: 'form' }, h('label', { class: 'field' }, 'Kho', h('select', { onchange: e => { form.kbId = e.target.value; drawMethod(); } },
          kbs.map(k => h('option', { value: k.id, selected: k.id === form.kbId, text: `${k.name} (${k.documents} tài liệu)` })))),
          h('p', { class: 'muted small', text: 'Bạn sẽ thấy trước mọi thay đổi trước khi công bố vào kho.' })));
      }
    }
    const submit = h('button', { class: 'btn primary', type: 'button', text: 'Tách quy phạm', onclick: () => act(submit, async () => {
      const target = form.mode === 'new' ? { mode: 'new', name: form.name, description: form.description, data_class: form.dataClass } : { mode: 'merge', kb_id: form.kbId };
      const result = form.source === 'library'
        ? await api('/api/prepare-source', { source_id: form.sourceId, target, extraction: form.extraction })
        : await api('/api/prepare', { title: form.title, text: form.text, synthetic: form.synthetic, target, extraction: form.extraction });
      ui.filter = 'all'; ui.editing = null;
      go(`#/draft/${result.id}`);
    }) });
    mount(stepper(1),
      pageHead('Nhập tài liệu', 'Kho chưa thay đổi cho đến khi bạn duyệt và công bố.'),
      h('section', { class: 'section' }, h('h2', { text: 'Văn bản' }), h('p', { text: 'Chọn văn bản pháp luật cần đưa vào kho.' }),
        h('div', { class: 'choice-grid' },
          sources.length ? radio('source', 'library', form.source, 'Thư viện văn bản', 'Trích đoạn chính thức đã tải sẵn, có kiểm tra checksum.', v => { form.source = v; drawSource(); }) : null,
          radio('source', 'file', form.source, 'Tải tệp TXT', 'Tệp văn bản có cấu trúc Điều, khoản, điểm.', v => { form.source = v; drawSource(); }),
          radio('source', 'paste', form.source, 'Dán nội dung', 'Dán trực tiếp văn bản vào ô soạn thảo.', v => { form.source = v; drawSource(); })),
        sourceBody),
      h('section', { class: 'section' }, h('h2', { text: 'Lưu vào' }), h('p', { text: 'Tạo một kho mới hoặc bổ sung vào kho đã có.' }),
        h('div', { class: 'choice-grid' },
          radio('target', 'new', form.mode, 'Tạo kho mới', 'Kho chỉ được tạo khi bạn công bố.', v => { form.mode = v; drawTarget(); }),
          radio('target', 'merge', form.mode, 'Gộp vào kho có sẵn', kbs.length ? 'Thêm tài liệu và quy phạm vào một kho đã có.' : 'Chưa có kho nào để gộp.', v => { form.mode = v; drawTarget(); }, !kbs.length)),
        targetBody),
      h('section', { class: 'section' }, h('h2', { text: 'Cách tách quy phạm' }),
        h('p', { text: 'Dù chọn cách nào, bạn vẫn duyệt từng quy phạm trước khi công bố.' }), methodBody),
      h('div', { class: 'actions' }, submit, footNote));
    drawSource();
    drawTarget();
    drawMethod();
  }

  // Draft: review, preview, done ---------------------------------------------
  async function renderDraft(id, step) {
    draft = await api('/api/draft?id=' + encodeURIComponent(id));
    if (draft.status === 'merged') return renderDone();
    if (draft.status !== 'draft') {
      mount(pageHead(draft.title, 'Bản nháp này đã được hủy.'), h('a', { class: 'btn', href: '#/import', text: 'Nhập tài liệu khác' }));
      return;
    }
    if (['queued', 'running'].includes(draft.extraction.state)) return renderExtracting();
    if (step === 'preview') return renderPreview();
    renderReview();
  }
  let pollTimer;
  function renderExtracting() {
    const x = draft.extraction;
    const hash = location.hash;
    const pct = x.total ? Math.round(100 * x.done / x.total) : 0;
    mount(stepper(2),
      pageHead(draft.title, `${targetText(draft.target, draft.kb && draft.kb.name)}.`),
      h('section', { class: 'section extracting', 'aria-live': 'polite' },
        h('h2', { text: 'Đang tách quy phạm bằng AI' }),
        h('p', { text: `Model ${x.model} đang đọc các câu mà bộ quy tắc chưa tách được. Mỗi đoạn AI đề xuất sẽ được đối chiếu đúng nguyên văn trước khi đưa vào bản nháp.` }),
        h('div', { class: 'progress-track big', role: 'progressbar', 'aria-valuemin': 0, 'aria-valuemax': 100, 'aria-valuenow': pct },
          h('i', { class: 'a', style: `width:${x.total ? Math.max(4, pct) : 4}%` })),
        h('p', { class: 'muted small', text: x.total ? `Đã xử lý ${x.done}/${x.total} nhóm câu (theo Điều).` : 'Đang chuẩn bị...' }),
        h('p', { class: 'muted small', text: 'Bạn có thể rời trang này; bản nháp nằm ở thanh bên trái.' })));
    clearTimeout(pollTimer);
    pollTimer = setTimeout(() => { if (location.hash === hash) route(); }, 1500);
  }
  async function review(itemId, decision, payload) {
    const scroll = window.scrollY;
    draft = await api('/api/draft/review', { draft_id: draft.id, item_id: itemId, decision, payload });
    await refreshState();
    renderNav(['draft', draft.id]);
    renderReview();
    window.scrollTo(0, scroll);
  }
  function selectionIn(unitsById) {
    const selection = window.getSelection();
    if (!selection || selection.rangeCount === 0 || selection.isCollapsed) throw Error('Hãy bôi đen một đoạn trong văn bản bên trái trước.');
    const range = selection.getRangeAt(0);
    const startEl = (range.startContainer.nodeType === 1 ? range.startContainer : range.startContainer.parentElement).closest('[data-uv]');
    const endEl = (range.endContainer.nodeType === 1 ? range.endContainer : range.endContainer.parentElement).closest('[data-uv]');
    if (!startEl || startEl !== endEl) throw Error('Đoạn chọn phải nằm trọn trong một khoản hoặc điểm.');
    const offset = (node, at) => {
      const r = document.createRange();
      r.setStart(startEl, 0);
      r.setEnd(node, at);
      const fragment = r.cloneContents();
      fragment.querySelectorAll('sup').forEach(s => s.remove());
      return fragment.textContent.length;
    };
    const unit = unitsById[startEl.dataset.uv];
    let start = offset(range.startContainer, range.startOffset);
    let end = offset(range.endContainer, range.endOffset);
    while (start < end && /\s/.test(unit.text[start])) start++;
    while (end > start && /\s/.test(unit.text[end - 1])) end--;
    if (start >= end) throw Error('Đoạn chọn chỉ có khoảng trắng.');
    return { unit_version_id: unit.unit_version_id, start, end };
  }
  function renderReview() {
    const numbers = new Map(draft.claims.map((c, i) => [c.id, i + 1]));
    const unitsById = {};
    for (const a of draft.articles) for (const u of a.units) unitsById[u.unit_version_id] = u;
    const p = draft.progress;
    const decided = p.total - p.undecided;
    const visible = c => ui.filter === 'all' || (ui.filter === 'undecided' && !c.decision) || (ui.filter === 'attention' && c.reasons.length);
    const gapVisible = g => ui.filter === 'all' || !g.decision;
    const focusNote = idx => {
      document.querySelectorAll('.focus').forEach(e => e.classList.remove('focus'));
      const note = document.getElementById('note-' + idx);
      const mark = document.querySelector(`mark[data-ref="${idx}"]`);
      if (note) { note.classList.add('focus'); note.scrollIntoView({ block: 'nearest', behavior: 'smooth' }); }
      if (mark) mark.classList.add('focus');
    };

    const focusGap = id => {
      document.querySelectorAll('.focus').forEach(e => e.classList.remove('focus'));
      const note = document.getElementById('note-' + id);
      const span = document.querySelector(`[data-gap="${CSS.escape(id)}"]`);
      if (note) { note.classList.add('focus'); note.scrollIntoView({ block: 'nearest', behavior: 'smooth' }); }
      if (span) span.classList.add('focus');
    };
    function statute(article) {
      return h('div', { class: 'statute', id: 'statute-' + article.id.replace(/[^\w-]/g, '_') }, article.units.map(unit => {
        const marks = draft.claims.filter(c => c.quote && c.quote.unit_version_id === unit.unit_version_id)
          .map(c => ({ start: c.quote.start, end: c.quote.end, claim: c }))
          .concat(draft.gaps.filter(g => g.unit_version_id === unit.unit_version_id).map(g => ({ start: g.start, end: g.end, gap: g })))
          .sort((a, b) => a.start - b.start || b.end - a.end);
        const parts = [];
        let at = 0;
        for (const m of marks) {
          if (m.start < at) continue; // Overlapping quotes keep their margin note; only the first is underlined.
          parts.push(unit.text.slice(at, m.start));
          if (m.gap) {
            parts.push(h('span', { class: `gap ${m.gap.decision ? 'dismissed' : ''}`, 'data-gap': m.gap.id, title: m.gap.decision ? 'Đã đánh dấu không phải quy phạm' : 'Chưa có quy phạm cho câu này',
              onclick: () => focusGap(m.gap.id) }, unit.text.slice(m.start, m.end)));
          } else {
            const n = numbers.get(m.claim.id);
            parts.push(h('mark', { class: m.claim.decision || '', 'data-ref': n, title: `Quy phạm ${n}`, onclick: () => focusNote(n) },
              unit.text.slice(m.start, m.end), h('sup', { text: n })));
          }
          at = m.end;
        }
        parts.push(unit.text.slice(at));
        return h('p', { class: `unit u-${unit.unit_type}`, 'data-uv': unit.unit_version_id }, parts);
      }));
    }
    function slotRows(c) {
      const rows = [];
      for (const name of SLOT_ORDER) {
        const slot = c.slots[name];
        if (slot && slot.state === 'present') rows.push(h('dt', {}, term(name, SLOT[name])), h('dd', { text: slot.text }));
        else if (name === 'actor' || name === 'action') rows.push(h('dt', {}, term(name, SLOT[name])), h('dd', { class: 'unknown', text: slot && slot.state === 'not_present' ? 'Không có' : 'Chưa xác định' }));
      }
      return h('dl', { class: 'slots' }, rows);
    }
    function editor(c) {
      const isModality = ui.editField === 'modality';
      const note = h('textarea', { rows: 2, maxlength: 1000, style: 'min-height:60px', placeholder: 'Ghi chú cho người đọc sau. Không dùng làm căn cứ trả lời.' }, c.reviewer_note || '');
      const use = h('button', { class: 'btn primary', type: 'button', text: 'Dùng đoạn đã chọn', onclick: () => act(use, async () => {
        const anchor = selectionIn(unitsById);
        const payload = isModality ? { field: 'modality', modality: ui.editModality, ...anchor } : { field: 'slot', slot: ui.editField, state: 'present', ...anchor };
        await review(c.id, 'edit', payload);
        toast('Đã cập nhật quy phạm bằng đoạn trích trong văn bản.');
      }) });
      const setState = (stateName, label) => {
        const b = h('button', { class: 'btn', type: 'button', text: label, onclick: () => act(b, () =>
          review(c.id, 'edit', isModality ? { field: 'modality', modality: 'unknown' } : { field: 'slot', slot: ui.editField, state: stateName })) });
        return b;
      };
      return h('div', { class: 'editor' },
        h('label', { class: 'field' }, 'Sửa thành phần', h('select', { onchange: e => { ui.editField = e.target.value; renderReview(); } },
          [...SLOT_ORDER.map(k => h('option', { value: k, selected: ui.editField === k, text: SLOT[k] })), h('option', { value: 'modality', selected: isModality, text: 'Loại quy phạm' })])),
        isModality ? h('label', { class: 'field' }, 'Loại mới', h('select', { onchange: e => { ui.editModality = e.target.value; } },
          Object.entries(MODALITY).filter(([k]) => k !== 'unknown').map(([k, v]) => h('option', { value: k, selected: ui.editModality === k, text: v })))) : null,
        h('p', { class: 'muted small', text: isModality
          ? 'Bôi đen từ chỉ loại quy phạm trong văn bản bên trái (ví dụ “phải”, “không được”), rồi bấm Dùng đoạn đã chọn.'
          : 'Bôi đen đúng đoạn trong khoản hoặc điểm của quy phạm này ở bên trái, rồi bấm Dùng đoạn đã chọn.' }),
        h('div', { class: 'row' }, use, isModality ? setState('unknown', 'Chưa rõ loại') : [setState('not_present', 'Không có'), setState('unknown', 'Chưa xác định')]),
        h('div', { class: 'row' }, note, (() => { const b = h('button', { class: 'btn', type: 'button', text: 'Lưu ghi chú', onclick: () => act(b, () => review(c.id, 'edit', { field: 'note', text: note.value })) }); return b; })()),
        h('div', { class: 'row' }, c.edited ? (() => { const b = h('button', { class: 'btn quiet', type: 'button', text: 'Khôi phục bản máy tách', onclick: () => act(b, () => review(c.id, 'edit', { field: 'restore' })) }); return b; })() : null,
          h('button', { class: 'btn quiet', type: 'button', text: 'Đóng', onclick: () => { ui.editing = null; renderReview(); } })));
    }
    const ORIGIN = { ai: 'AI đề xuất', manual: 'Thêm thủ công', cue: 'Cần bổ sung' };
    function noteFor(c) {
      const n = numbers.get(c.id);
      const decide = (value, label, cls) => {
        const b = h('button', { class: `btn ${cls}`, type: 'button', 'aria-pressed': String(c.decision === value),
          onclick: () => act(b, () => review(c.id, c.decision === value ? 'clear' : value)) }, icon(value === 'approve' ? 'check' : 'x'), label);
        return b;
      };
      const remove = c.origin === 'manual' ? h('button', { class: 'btn quiet', type: 'button', text: 'Xóa', onclick: () => act(remove, async () => {
        if (ui.editing === c.id) ui.editing = null;
        await review(c.id, 'remove_claim');
        toast('Đã xóa quy phạm thêm thủ công.');
      }) }) : null;
      return h('article', { class: `note ${c.decision || ''}`, id: 'note-' + n, onclick: e => { if (e.target === e.currentTarget) focusNote(n); } },
        h('div', { class: 'note-head' }, h('h3', {}, h('span', { class: 'ref', text: n }), h('span', { class: 'title', title: claimTitle(c), text: claimTitle(c) })), h('span', { class: `modality ${c.modality}`, 'data-term': MODALITY_TERM[c.modality] || c.modality, tabindex: 0, text: MODALITY[c.modality] || c.modality })),
        h('div', { class: 'note-body' },
          ORIGIN[c.origin] || c.edited ? h('div', { class: 'tags' },
            ORIGIN[c.origin] ? h('span', { class: `origin ${c.origin}`, 'data-term': c.origin, tabindex: 0, text: ORIGIN[c.origin] }) : null,
            c.edited ? h('span', { class: 'edited-tag', text: `Đã chỉnh sửa (${c.edits.length} thay đổi)` }) : null) : null,
          slotRows(c),
          c.reasons.map(r => h('div', { class: 'attention', text: r })),
          c.ai_note ? h('p', { class: 'small muted', text: c.ai_note }) : null,
          c.reviewer_note ? h('p', { class: 'small muted', text: 'Ghi chú: ' + c.reviewer_note }) : null,
          c.decision_mode === 'batch' ? h('div', { class: 'muted small', text: 'Đã duyệt cùng cả Điều' }) : null),
        h('div', { class: 'note-actions' }, decide('approve', 'Duyệt', 'approve'), decide('reject', 'Loại', 'reject'),
          h('button', { class: 'btn quiet', type: 'button', 'aria-expanded': String(ui.editing === c.id), text: ui.editing === c.id ? 'Đang sửa' : 'Sửa',
            onclick: () => { ui.editing = ui.editing === c.id ? null : c.id; renderReview(); } }), remove),
        ui.editing === c.id ? editor(c) : null);
    }
    async function addClaim(anchor) {
      await review(null, 'add_claim', anchor);
      const added = draft.claims.find(c => c.origin === 'manual' && c.quote && c.quote.unit_version_id === anchor.unit_version_id && c.quote.start === anchor.start && c.quote.end === anchor.end);
      if (added) {
        ui.editing = added.id;
        ui.editField = 'actor';
        renderReview();
        const note = document.querySelector('.note .editor');
        if (note) note.scrollIntoView({ block: 'center' });
      }
      toast('Đã thêm quy phạm. Bôi đen chủ thể, hành vi và từ chỉ loại quy phạm rồi dùng các ô Sửa.');
    }
    function gapNote(g) {
      const add = h('button', { class: 'btn', type: 'button', text: 'Thêm quy phạm', onclick: () => act(add, () => addClaim({ unit_version_id: g.unit_version_id, start: g.start, end: g.end })) });
      const dismiss = h('button', { class: 'btn', type: 'button', 'aria-pressed': String(g.decision === 'no_norm'), text: 'Không phải quy phạm',
        onclick: () => act(dismiss, () => review(g.id, g.decision ? 'clear' : 'no_norm')) });
      return h('article', { class: `note gap-note ${g.decision ? 'dismissed' : ''}`, id: 'note-' + g.id },
        h('div', { class: 'note-head' }, h('h3', {}, h('span', { class: 'ref gap-ref', text: '?' }),
          h('span', { class: 'title' }, g.decision ? 'Không phải quy phạm' : term('gap', 'Chưa có quy phạm')))),
        h('div', { class: 'note-body' },
          h('p', { class: 'gap-quote', text: g.text }),
          g.ai_note ? h('p', { class: 'small muted', text: g.ai_note }) : null,
          g.decision ? null : h('p', { class: 'small muted', text: 'Nếu câu này nêu nghĩa vụ, quyền hay điều cấm, hãy thêm quy phạm; nếu không, đánh dấu không phải quy phạm.' })),
        h('div', { class: 'note-actions' }, g.decision ? null : add, dismiss));
    }

    const articles = draft.articles.map(article => {
      const claims = draft.claims.filter(c => c.article_id === article.id);
      const gaps = draft.gaps.filter(g => g.article_id === article.id);
      const unitOrder = new Map(article.units.map((u, i) => [u.unit_version_id, i]));
      const items = claims.filter(visible).map(c => ({ uv: c.quote ? c.quote.unit_version_id : '', start: c.quote ? c.quote.start : 0, node: () => noteFor(c) }))
        .concat(gaps.filter(gapVisible).map(g => ({ uv: g.unit_version_id, start: g.start, node: () => gapNote(g) })))
        .sort((a, b) => (unitOrder.get(a.uv) ?? 0) - (unitOrder.get(b.uv) ?? 0) || a.start - b.start);
      if (ui.filter !== 'all' && !items.length) return null;
      const open = claims.filter(c => !c.decision).length;
      const openGaps = gaps.filter(g => !g.decision).length;
      const batch = h('button', { class: 'btn', type: 'button', text: `Duyệt ${open} quy phạm còn lại trong Điều`,
        onclick: () => act(batch, () => review(null, 'approve_article', { article_id: article.id })) });
      const dismissAll = h('button', { class: 'btn', type: 'button', text: `Đánh dấu ${openGaps} câu còn lại không phải quy phạm`,
        onclick: () => act(dismissAll, () => review(null, 'no_norm_article', { article_id: article.id })) });
      const fromSelection = h('button', { class: 'btn quiet', type: 'button', title: 'Bôi đen một đoạn trong một khoản hoặc điểm bên trái rồi bấm nút này',
        onclick: () => act(fromSelection, () => addClaim(selectionIn(unitsById))) }, icon('plus'), 'Thêm quy phạm từ đoạn bôi đen');
      return h('section', { class: 'article', 'aria-label': article.label },
        h('div', { class: 'article-head' }, h('h2', { text: article.label }),
          h('div', { class: 'actions' }, fromSelection, openGaps ? dismissAll : null, open ? batch : claims.length && !openGaps ? h('span', { class: 'muted small', text: 'Đã quyết định cả Điều' }) : null)),
        statute(article),
        h('div', { class: 'margin' }, items.length ? items.map(i => i.node()) : h('p', { class: 'muted small', text: 'Điều này không có câu nào cần duyệt. Nội dung vẫn được lưu làm nguồn.' })));
    });
    const x = draft.extraction;
    const retry = state.extraction_model && x.mode === 'llm' && !decided && !draft.gaps.some(g => g.decision)
      ? h('button', { class: 'btn', type: 'button', text: 'Chạy lại tách bằng AI', onclick: () => act(retry, async () => {
        draft = await api('/api/draft/extract', { draft_id: draft.id });
        route();
      }) }) : null;
    const extractionNotice = x.mode !== 'llm' ? null
      : x.state === 'done' && !x.checked ? h('div', { class: 'notice info', text: 'Bộ quy tắc đã tách được mọi câu trong tài liệu nên không cần gọi AI.' })
      : x.state === 'done' && !x.ai_claims ? h('div', { class: 'notice info', text: `AI (${x.model}) đã đọc ${x.checked} câu bộ quy tắc chưa tách được và không đề xuất thêm quy phạm nào. Bạn vẫn có thể thêm quy phạm cho từng câu.` })
      : x.state === 'done' ? h('div', { class: 'notice info', text: `AI (${x.model}) đã đọc ${x.checked} câu bộ quy tắc chưa tách được và đề xuất ${x.ai_claims} quy phạm, có nhãn “AI đề xuất”.` })
      : x.state === 'partial' ? h('div', { class: 'notice' }, h('p', { text: `AI (${x.model}) xử lý được một phần (${x.ai_claims} quy phạm). Các câu còn lại giữ kết quả tách theo quy tắc. Mã lỗi: ${x.errors.join(', ')}.` }), retry)
      : x.state === 'failed' ? h('div', { class: 'notice error' }, h('p', { text: `Tách bằng AI không thành công (mã lỗi: ${x.errors.join(', ')}). Bản nháp đang dùng kết quả tách theo quy tắc.` }), retry)
      : x.state === 'interrupted' ? h('div', { class: 'notice' }, h('p', { text: 'Tách bằng AI bị gián đoạn do máy chủ khởi động lại. Bản nháp đang dùng kết quả tách theo quy tắc.' }), retry)
      : null;

    const entities = draft.entities.filter(e => e.suggestions.length);
    const entitySection = draft.target.mode === 'merge' && entities.length ? h('section', { class: 'section entities' },
      h('h2', { text: 'Thực thể trùng tên trong kho' }),
      h('p', { text: 'Lexora chỉ so khớp tên. Liên kết khi bạn chắc hai đề cập cùng chỉ một đối tượng; liên kết chỉ áp dụng trong kho này.' }),
      entities.map(e => {
        const owner = draft.claims.find(c => c.id === e.claim_id);
        const ready = owner && owner.decision === 'approve';
        const target = e.target || e.suggestions[0].id;
        const suggestion = e.suggestions.find(s => s.id === target) || e.suggestions[0];
        const link = h('button', { class: 'btn approve', type: 'button', disabled: !ready, 'aria-pressed': String(e.decision === 'link'), text: 'Cùng một thực thể',
          onclick: () => act(link, () => review(e.id, e.decision === 'link' ? 'clear' : 'link', { target: suggestion.id })) });
        const differ = h('button', { class: 'btn', type: 'button', disabled: !ready, 'aria-pressed': String(e.decision === 'no_link'), text: 'Khác nhau',
          onclick: () => act(differ, () => review(e.id, e.decision === 'no_link' ? 'clear' : 'no_link')) });
        return h('div', { class: 'entity' },
          h('div', {}, h('strong', { text: e.label }), h('div', { class: 'muted small', text: `Trong tài liệu mới, quy phạm ${numbers.get(e.claim_id)}` }), e.context ? h('blockquote', { text: e.context }) : null),
          h('div', {}, h('strong', { text: suggestion.label }), h('div', { class: 'muted small', text: 'Đã có trong kho' }), suggestion.context ? h('blockquote', { text: suggestion.context }) : null),
          h('div', { class: 'actions' }, link, differ, ready ? null : h('span', { class: 'muted small', text: 'Duyệt quy phạm trước' })));
      })) : null;

    const filters = [['all', 'Tất cả'], ['undecided', `Chưa quyết định (${p.undecided + p.gaps_open})`], ['attention', 'Cần chú ý']];
    const filterTerm = { attention: 'attention' };
    const discard = h('button', { class: 'btn quiet', type: 'button', text: 'Hủy bản nháp', onclick: () => act(discard, async () => {
      if (!window.confirm('Hủy bản nháp này? Các quyết định đã lưu sẽ không được dùng.')) return;
      await api('/api/draft/discard', { draft_id: draft.id });
      toast('Đã hủy bản nháp.');
      go('#/');
    }) });
    mount(stepper(2),
      pageHead(draft.title, [`${targetText(draft.target, draft.kb && draft.kb.name)}. Đối chiếu từng quy phạm với nguyên văn bên trái. `,
        draft.document.synthetic ? h('span', { class: 'tag synthetic', text: 'Dữ liệu minh họa' }) : null]),
      h('div', { class: 'review-bar' },
        h('div', { class: 'progress' }, h('span', { text: `Đã quyết định ${decided}/${p.total}` }),
          h('div', { class: 'progress-track', role: 'img', 'aria-label': `${p.approved} duyệt, ${p.rejected} loại` },
            h('i', { class: 'a', style: `width:${p.total ? 100 * p.approved / p.total : 0}%` }), h('i', { class: 'r', style: `width:${p.total ? 100 * p.rejected / p.total : 0}%` })),
          h('div', { class: 'legend' }, h('span', { class: 'a' }, h('i'), `${p.approved} duyệt`), h('span', { class: 'r' }, h('i'), `${p.rejected} loại`),
            h('span', {}, h('i'), `${p.undecided} chưa quyết định`), p.gaps ? h('span', {}, term('gap', `${p.gaps_open} câu chưa có quy phạm`)) : null)),
        h('div', { class: 'filters', role: 'group', 'aria-label': 'Lọc quy phạm' }, filters.map(([k, label]) =>
          h('button', { type: 'button', 'aria-pressed': String(ui.filter === k), 'data-term': filterTerm[k] || null, text: label, onclick: () => { ui.filter = k; renderReview(); } })))),
      h('p', { class: 'review-hint' }, 'Mẹo: rê chuột vào các từ gạch chân chấm như ', term('actor', 'chủ thể'), ', ', term('modality', 'tính quy phạm'), ' hay ', term('beneficiary', 'bên thụ hưởng'), ' để xem định nghĩa và ví dụ.'),
      extractionNotice,
      p.total || p.gaps ? null : h('div', { class: 'notice', text: 'Không tìm thấy câu nào trong tài liệu này. Kiểm tra lại cấu trúc văn bản.' }),
      articles.filter(Boolean).length ? articles : h('p', { class: 'muted', style: 'padding:24px 0', text: 'Không có quy phạm nào khớp bộ lọc.' }),
      entitySection,
      draft.unassigned_text.trim() ? h('details', { class: 'section' }, h('summary', { text: 'Phần văn bản chưa được đưa vào Điều nào' }), h('p', { class: 'small', style: 'white-space:pre-wrap', text: draft.unassigned_text })) : null,
      h('div', { class: 'footer-bar' },
        h('span', { text: [p.undecided ? `Còn ${p.undecided} quy phạm chưa quyết định` : '', p.gaps_open ? `${p.gaps_open} câu chưa có quy phạm` : '']
          .filter(Boolean).join(', ') || 'Đã xử lý tất cả quy phạm và câu trong tài liệu' }),
        h('div', { class: 'actions' }, discard, h('a', { class: 'btn primary', href: `#/draft/${draft.id}/preview` }, 'Xem trước thay đổi', icon('arrow')))));
  }

  function renderPreview() {
    const d = draft.diff;
    const target = draft.target.mode === 'new' ? `kho mới “${draft.target.name}”` : `kho “${draft.kb.name}”`;
    const row = (label, before, after) => h('tr', {}, h('td', { text: label }), h('td', { class: 'num', text: before }), h('td', { class: 'num', text: after }),
      h('td', { class: 'num delta', text: after > before ? `+${after - before}` : '' }));
    const reviewer = h('input', { value: ui.reviewer, maxlength: 200, oninput: e => { ui.reviewer = e.target.value; } });
    const reason = h('textarea', { rows: 3, style: 'min-height:80px', maxlength: 2000, placeholder: 'Ví dụ: Đã đối chiếu từng quy phạm với nguyên văn các Điều trong tài liệu.' });
    const confirm = h('input', { type: 'checkbox' });
    const blocked = draft.progress.undecided > 0 || draft.progress.gaps_open > 0 || draft.progress.approved === 0;
    const conflict = h('div');
    const publish = h('button', { class: 'btn primary', type: 'button', disabled: blocked, text: 'Công bố vào kho', onclick: () => act(publish, async () => {
      if (!confirm.checked) throw Error('Hãy xác nhận bạn đã đối chiếu các quy phạm trước khi công bố.');
      try {
        await api('/api/publish', { draft_id: draft.id, reviewer: reviewer.value, reason: reason.value });
      } catch (e) {
        if (e.code !== 'base_changed') throw e;
        conflict.replaceChildren(h('div', { class: 'notice error' }, h('p', { text: e.message }),
          h('a', { class: 'btn', href: `#/import/${draft.target.kb_id}`, text: 'Nhập lại trên phiên bản mới' })));
        return;
      }
      toast('Đã công bố vào kho.');
      go(`#/draft/${draft.id}/done`);
    }) });
    mount(stepper(3),
      pageHead('Xem trước thay đổi', draft.title),
      h('section', { class: 'section' },
        h('p', { class: 'summary-line', text: `Công bố sẽ thêm 1 tài liệu và ${d.approved} quy phạm đã duyệt vào ${target}.` }),
        h('table', { class: 'change-table' },
          h('thead', {}, h('tr', {}, h('th', { text: '' }), h('th', { class: 'num', text: 'Hiện có' }), h('th', { class: 'num', text: 'Sau khi công bố' }), h('th', { text: '' }))),
          h('tbody', {}, row('Tài liệu', d.documents_before, d.documents_after), row('Quy phạm đã duyệt', d.claims_before, d.claims_after))),
        h('ul', { class: 'list', style: 'max-width:640px;margin-top:12px' },
          h('li', {}, h('span', { text: 'Quy phạm bị loại, không đưa vào kho' }), h('strong', { text: d.rejected })),
          h('li', {}, h('span', { text: 'Quy phạm đã chỉnh sửa' }), h('strong', { text: d.edited })),
          draft.progress.gaps ? h('li', {}, h('span', { text: 'Câu được đánh dấu không phải quy phạm' }), h('strong', { text: draft.progress.gaps - draft.progress.gaps_open })) : null,
          draft.target.mode === 'merge' ? h('li', {}, h('span', { text: 'Thực thể liên kết với thực thể đã có' }), h('strong', { text: d.entities_linked })) : null,
          h('li', {}, h('span', { text: 'Thực thể mới' }), h('strong', { text: d.entities_new }))),
        d.warnings.map(w => h('div', { class: 'notice', text: w })),
        draft.progress.undecided ? h('div', { class: 'notice error', text: `Còn ${draft.progress.undecided} quy phạm chưa quyết định. Quay lại để duyệt hoặc loại trước khi công bố.` }) : null,
        draft.progress.gaps_open ? h('div', { class: 'notice error', text: `Còn ${draft.progress.gaps_open} câu chưa có quy phạm. Quay lại để thêm quy phạm hoặc đánh dấu không phải quy phạm.` }) : null,
        draft.progress.total && !draft.progress.approved && !draft.progress.undecided ? h('div', { class: 'notice error', text: 'Chưa có quy phạm nào được duyệt nên kho sẽ không thay đổi.' }) : null,
        h('div', { class: 'notice info', text: 'Hiệu lực pháp luật của văn bản chưa được xác minh. Phiên bản hiện tại của kho được giữ nguyên trong lịch sử.' })),
      h('section', { class: 'section' }, h('h2', { text: 'Xác nhận công bố' }),
        h('div', { class: 'form' },
          h('label', { class: 'field' }, 'Người duyệt', reviewer),
          h('label', { class: 'field' }, 'Phạm vi đã kiểm tra', reason),
          h('label', { class: 'check' }, confirm, 'Tôi đã đối chiếu các quy phạm với nguyên văn và đồng ý công bố vào kho.'),
          conflict,
          h('div', { class: 'actions' }, h('a', { class: 'btn', href: `#/draft/${draft.id}`, text: 'Quay lại duyệt' }), publish))));
  }

  function renderDone() {
    const kbId = draft.kb && draft.kb.id;
    const name = draft.kb ? draft.kb.name : draft.target.name;
    const chat = h('button', { class: 'btn primary', type: 'button', text: 'Hỏi đáp trên kho này', onclick: () => { ui.chatPreselect = [kbId]; go('#/chat'); } });
    mount(h('ol', { class: 'stepper' }, ['Chọn văn bản và nơi lưu', 'Duyệt quy phạm', 'Xem trước và công bố'].map(s => h('li', { class: 'done', text: s }))),
      h('section', { class: 'section empty' }, h('h2', { text: `Đã công bố vào kho “${name}”` }),
        h('p', { text: `${draft.title}: ${draft.diff.approved} quy phạm đã duyệt được thêm vào kho. Các cuộc trò chuyện trước đó vẫn dùng phiên bản cũ của kho.` }),
        h('div', { class: 'actions' }, chat, h('a', { class: 'btn', href: `#/kb/${kbId}`, text: 'Mở kho' }), h('a', { class: 'btn', href: '#/import', text: 'Nhập tài liệu khác' }))));
  }

  // Chat -------------------------------------------------------------------------
  async function renderChat(sessionId) {
    const session = sessionId ? await api('/api/chat/session?id=' + encodeURIComponent(sessionId)) : null;
    const usable = state.knowledge_bases.filter(k => k.approved_claims > 0);
    const picked = new Set(ui.chatPreselect.length ? ui.chatPreselect : session ? session.bindings.map(b => b.kb_id) : []);
    ui.chatPreselect = [];
    const start = h('button', { class: 'btn primary block', type: 'button', text: 'Bắt đầu cuộc trò chuyện', onclick: () => act(start, async () => {
      if (!picked.size) throw Error('Chọn ít nhất một kho.');
      const created = await api('/api/chat/start', { kb_ids: [...picked] });
      go(`#/chat/${created.id}`);
    }) });
    const setup = h('aside', { class: 'section chat-setup' }, h('h2', { text: 'Phạm vi hỏi đáp' }),
      h('p', { class: 'small', text: 'Chọn từ một đến năm kho. Chỉ quy phạm đã duyệt được dùng.' }),
      state.knowledge_bases.length ? h('div', { class: 'kb-pick' }, state.knowledge_bases.map(kb => h('label', {},
        h('input', { type: 'checkbox', checked: picked.has(kb.id), disabled: !kb.approved_claims, onchange: e => { e.target.checked ? picked.add(kb.id) : picked.delete(kb.id); } }),
        h('span', {}, kb.name, h('div', { class: 'muted small', text: kb.approved_claims ? `${kb.approved_claims} quy phạm` : 'Chưa có quy phạm đã duyệt' }))))) :
        h('p', { class: 'muted small' }, 'Chưa có kho nào. ', h('a', { href: '#/import', text: 'Nhập tài liệu' })),
      usable.length ? start : null,
      state.chat_sessions.length ? [h('h2', { text: 'Cuộc trò chuyện trước', style: 'font-size:15px;margin-top:22px' }),
        h('ul', { class: 'session-list' }, state.chat_sessions.map(s => h('li', {}, h('button', { type: 'button', 'aria-current': String(session && session.id === s.id),
          onclick: () => go(`#/chat/${s.id}`) }, h('div', { text: s.bindings.map(b => b.kb_name || 'Kho đã xóa').join(', ') }),
          h('div', { class: 'muted small', text: `${when(s.created_at)}, ${s.turns} câu hỏi` })))))] : null);

    let main;
    if (!session) {
      main = h('section', { class: 'section empty chat-main' }, h('h2', {}, 'Hỏi về các ', term('approved', 'quy phạm đã duyệt')),
        h('p', { text: 'Chọn kho ở bên trái rồi bắt đầu một cuộc trò chuyện. Mỗi câu trả lời dẫn về đúng câu trong văn bản gốc để bạn đối chiếu. Không tìm thấy căn cứ thì Lexora nói rõ là không có.' }));
    } else {
      const question = h('textarea', { rows: 3, style: 'min-height:84px', maxlength: 1500, placeholder: 'Ví dụ: Thời gian thử việc tối đa là bao lâu?' });
      const llm = state.router_enabled;
      const mode = h('select', { 'aria-label': 'Cách trả lời', onchange: () => { consentRow.classList.toggle('hide', mode.value !== 'llm'); } },
        h('option', { value: 'extractive', text: 'Trích nguyên văn, không gọi model' }), llm ? h('option', { value: 'llm', text: 'Trả lời bằng model 9Router' }) : null);
      const consent = h('input', { type: 'checkbox' });
      const consentRow = h('label', { class: 'check hide small' }, consent, 'Tôi đồng ý gửi câu hỏi và các trích đoạn công khai sang 9Router cho lượt này.');
      const allPublic = session.bindings.every(b => (state.knowledge_bases.find(k => k.id === b.kb_id) || {}).data_class === 'public');
      const semanticOn = Boolean(state.embedding_model) && allPublic;
      const semantic = h('input', { type: 'checkbox', checked: semanticOn && ui.semantic !== false, disabled: !semanticOn, onchange: e => { ui.semantic = e.target.checked; } });
      const semanticRow = state.embedding_model ? h('label', { class: 'check small' }, semantic, allPublic
        ? `Tìm thêm theo ý nghĩa: gửi câu hỏi và các trích đoạn đã duyệt tới ${state.embedding_model} để tìm cả những đoạn không trùng từ khóa.`
        : 'Tìm theo ý nghĩa chỉ dùng được khi mọi kho trong cuộc trò chuyện là kho công khai.') : null;
      const ask = h('button', { class: 'btn primary', type: 'button', text: 'Hỏi', onclick: () => act(ask, async () => {
        await api('/api/chat/ask', { session_id: session.id, question: question.value, mode: mode.value, allow_public_transfer: mode.value === 'llm' && consent.checked,
          semantic: semantic.checked });
        await route();
        window.scrollTo(0, document.body.scrollHeight);
      }) });
      question.addEventListener('keydown', e => { if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) ask.click(); });
      const SAMPLES = ['Thời gian thử việc tối đa là bao lâu?', 'Lương thử việc ít nhất bao nhiêu phần trăm?', 'Người sử dụng lao động phải thông báo kết quả thử việc không?'];
      main = h('div', { class: 'chat-main' },
        h('p', { class: 'scope-line' }, 'Đang hỏi trên:', session.bindings.map(b => h('span', { class: 'tag', text: b.kb_name || 'Kho đã xóa' })),
          h('span', {}, 'Cập nhật mới của kho sau thời điểm bắt đầu cần một cuộc trò chuyện mới (', term('revision', 'phiên bản'), ' được giữ cố định).')),
        h('div', { class: 'conversation' }, session.turns.length ? session.turns.map(turn) : h('section', { class: 'section' },
          h('p', { style: 'margin:0', text: 'Chưa có câu hỏi nào. Thử một câu hỏi mẫu:' }),
          h('div', { class: 'suggest' }, SAMPLES.map(q => h('button', { type: 'button', text: q, onclick: () => { question.value = q; question.focus(); } }))))),
        h('div', { class: 'ask-box' }, question, semanticRow, consentRow,
          h('div', { class: 'row' }, mode, h('div', { class: 'actions' }, h('span', { class: 'muted small', text: 'Ctrl + Enter để gửi' }), ask))));
    }
    mount(pageHead('Hỏi đáp', 'Tra cứu trong các kho bạn chọn. Đây không phải ý kiến pháp lý; hãy đối chiếu nguyên văn trước khi sử dụng.'),
      h('div', { class: 'chat-layout' }, setup, main));
  }
  function turn(t) {
    return h('article', { class: 'section turn' },
      h('div', { class: 'question', text: t.question }),
      h('div', { class: 'status', text: (STATUS[t.status] || t.status) + (t.error_code ? ` (mã lỗi ${t.error_code})` : '') }),
      t.statements.map(s => h('p', { class: 'statement' }, s.text, ' ', s.citation_ids.map(id => h('sup', { text: `[${id}]` })))),
      t.citations.map(c => h('div', { class: 'citation' },
        h('div', { class: 'cite-head' }, h('span', { class: 'num', text: `[${c.id}]` }), h('strong', { text: c.title }), h('span', { text: `${unitLabel(c.evidence.unit_id)} · Kho: ${c.sources.map(s => s.kb_name).join(', ')}` }),
          c.edited ? h('span', { class: 'edited-tag', text: ' Đã chỉnh sửa bởi người duyệt.' }) : null,
          c.dense_rank && !c.lexical_rank ? h('span', { class: 'muted small', text: ' Tìm thấy nhờ ý nghĩa, không trùng từ khóa.' }) : null,
          c.synthetic ? h('span', { class: 'tag synthetic', text: 'Dữ liệu minh họa', style: 'margin-left:6px' }) : null),
        h('blockquote', { text: c.evidence.quote }),
        c.scope.length ? h('div', { class: 'context' }, term('context', 'Ngữ cảnh'), ': ' + c.scope.map(s => s.quote.trim()).join(' ')) : null,
        h('details', { class: 'tech' }, h('summary', { text: 'Chi tiết nguồn' }), h('dl', {},
          h('dt', { text: 'Đơn vị' }), h('dd', { text: c.evidence.unit_id }),
          h('dt', { text: 'Vị trí ký tự' }), h('dd', { text: `${c.evidence.start} đến ${c.evidence.end}` }),
          h('dt', { text: 'Hash văn bản' }), h('dd', { text: c.evidence.normalized_sha256 }),
          c.similarity !== undefined && c.similarity !== null ? [h('dt', { text: 'Độ tương đồng ý nghĩa' }), h('dd', { text: String(c.similarity) })] : null,
          c.sources.map(s => [h('dt', { text: s.kb_name }), h('dd', { text: `Phiên bản ${s.revision}` })]),
          /^https:\/\//.test(c.source_url) ? [h('dt', { text: 'Văn bản gốc' }), h('dd', {}, h('a', { href: c.source_url, target: '_blank', rel: 'noopener', text: c.source_url }))] : null)))),
      h('p', { class: 'muted small', style: 'margin-top:10px', text: t.note }));
  }

  window.addEventListener('hashchange', route);
  route();
})();
