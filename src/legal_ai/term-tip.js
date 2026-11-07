/* Term explanations on hover, focus or tap. Any element with data-term="<key>" shows the
 * glossary entry for that key. Text is inserted as text, never as HTML. Shared by the demo
 * workspace and both graph viewers; the glossary comes from legal_ai/glossary.py. */
(() => {
  'use strict';
  const source = document.getElementById('lexora-glossary');
  if (!source) return;
  const glossary = JSON.parse(source.textContent);
  const tip = document.createElement('div');
  tip.id = 'term-tip';
  tip.setAttribute('role', 'tooltip');
  tip.hidden = true;
  let anchor = null;
  let hideTimer = 0;

  function el(tag, cls, text) {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text) e.textContent = text;
    return e;
  }
  function exampleNode(entry) {
    const quote = el('p', 'tt-quote');
    const text = entry.example;
    const at = entry.highlight ? text.indexOf(entry.highlight) : -1;
    if (at < 0) quote.textContent = text;
    else quote.append(text.slice(0, at), el('mark', null, entry.highlight), text.slice(at + entry.highlight.length));
    return quote;
  }
  function fill(entry) {
    const parts = [el('p', 'tt-term', entry.term), el('p', 'tt-def', entry.definition)];
    if (entry.cues) {
      const cues = el('p', 'tt-cues');
      cues.append(el('span', 'tt-label', 'Dấu hiệu nhận biết'), entry.cues);
      parts.push(cues);
    }
    if (entry.example) {
      const box = el('div', 'tt-example');
      box.append(el('span', 'tt-label', 'Ví dụ minh họa'), exampleNode(entry));
      parts.push(box);
    }
    tip.replaceChildren(...parts);
  }
  function place() {
    const r = anchor.getBoundingClientRect();
    const gap = 8;
    const w = tip.offsetWidth;
    const hgt = tip.offsetHeight;
    let left = Math.min(Math.max(8, r.left + r.width / 2 - w / 2), window.innerWidth - w - 8);
    let top = r.bottom + gap;
    let below = true;
    if (top + hgt > window.innerHeight - 8 && r.top - gap - hgt > 8) { top = r.top - gap - hgt; below = false; }
    tip.style.left = `${Math.round(left)}px`;
    tip.style.top = `${Math.round(top)}px`;
    tip.dataset.side = below ? 'below' : 'above';
  }
  function show(target) {
    const entry = glossary[target.dataset.term];
    if (!entry) return;
    clearTimeout(hideTimer);
    if (anchor === target && !tip.hidden) return;
    if (anchor) anchor.removeAttribute('aria-describedby');
    anchor = target;
    fill(entry);
    if (!tip.isConnected) document.body.append(tip);
    tip.hidden = false;
    place();
    anchor.setAttribute('aria-describedby', 'term-tip');
  }
  function hide(now) {
    clearTimeout(hideTimer);
    const go = () => {
      tip.hidden = true;
      if (anchor) anchor.removeAttribute('aria-describedby');
      anchor = null;
    };
    if (now) go(); else hideTimer = setTimeout(go, 140);
  }
  const termOf = node => (node && node.closest ? node.closest('[data-term]') : null);

  document.addEventListener('pointerover', e => {
    if (tip.contains(e.target)) { clearTimeout(hideTimer); return; }
    const target = termOf(e.target);
    if (target) show(target); else if (anchor) hide(false);
  });
  document.addEventListener('focusin', e => { const target = termOf(e.target); if (target) show(target); else if (anchor) hide(true); });
  document.addEventListener('focusout', e => { if (termOf(e.target) === anchor) hide(false); });
  document.addEventListener('keydown', e => { if (e.key === 'Escape' && anchor) hide(true); });
  window.addEventListener('scroll', () => { if (anchor) hide(true); }, true);
  window.addEventListener('resize', () => { if (anchor) hide(true); });
  window.LexoraTerms = { has: key => Object.prototype.hasOwnProperty.call(glossary, key), entry: key => glossary[key] };
})();
