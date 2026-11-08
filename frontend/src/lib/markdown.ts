// Small Markdown renderer for the project documents (no dependency). All text is HTML-escaped first, so the output
// only ever contains the tags built here. Supported: headings, paragraphs, bullet and numbered lists (two levels),
// tables, block quotes, fenced code, horizontal rules, **bold**, *italic*, `code` and [links](...) to http(s),
// in-app paths and #anchors.

export type Heading = { level: number; id: string; text: string };

const escape = (s: string) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');

export function slugify(text: string): string {
	const base = text
		.normalize('NFD')
		.replace(/[̀-ͯ]/g, '')
		.replace(/đ/g, 'd')
		.replace(/Đ/g, 'd')
		.toLowerCase()
		.replace(/[^a-z0-9]+/g, '-')
		.replace(/^-|-$/g, '');
	return base || 'muc';
}

function inline(raw: string): string {
	const codes: string[] = [];
	let s = escape(raw).replace(/`([^`]+)`/g, (_, c) => `\u0000${codes.push(c) - 1}\u0000`);
	s = s.replace(/\[([^\]]+)\]\(([^)\s]+)\)/g, (whole, label, href) => {
		const url = href.replace(/&amp;/g, '&');
		if (!/^(https?:\/\/|\/(?!\/)|#)/.test(url)) return whole;
		const external = /^https?:\/\//.test(url);
		return `<a href="${escape(url)}"${external ? ' target="_blank" rel="noopener noreferrer"' : ''}>${label}</a>`;
	});
	// Bare URLs become links too; a URL already inside a link is preceded by a quote or '>' and is left alone.
	s = s.replace(/(^|[\s(])(https?:\/\/[^\s<]*[^\s<.,;:)])/g, (_, lead, url) => `${lead}<a href="${url}" target="_blank" rel="noopener noreferrer">${url}</a>`);
	s = s.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>').replace(/(^|[^*])\*([^*\s][^*]*)\*/g, '$1<em>$2</em>');
	return s.replace(/\u0000(\d+)\u0000/g, (_, i) => `<code>${codes[Number(i)]}</code>`);
}

function cells(line: string): string[] {
	return line.trim().replace(/^\|/, '').replace(/\|$/, '').split('|').map((c) => c.trim());
}

export function render(markdown: string): { html: string; headings: Heading[] } {
	const lines = markdown.replace(/\r\n/g, '\n').split('\n');
	const out: string[] = [];
	const headings: Heading[] = [];
	const used = new Map<string, number>();
	let para: string[] = [];
	const flush = () => {
		if (para.length) out.push(`<p>${para.map(inline).join('<br>')}</p>`);
		para = [];
	};
	let i = 0;
	while (i < lines.length) {
		const line = lines[i];
		if (!line.trim()) {
			flush();
			i++;
			continue;
		}
		const fence = line.match(/^```/);
		if (fence) {
			flush();
			const body: string[] = [];
			i++;
			while (i < lines.length && !/^```/.test(lines[i])) body.push(lines[i++]);
			out.push(`<pre><code>${escape(body.join('\n'))}</code></pre>`);
			i++;
			continue;
		}
		const heading = line.match(/^(#{1,4})\s+(.+)$/);
		if (heading) {
			flush();
			const level = heading[1].length;
			const text = heading[2].trim();
			let id = slugify(text);
			const n = used.get(id) ?? 0;
			used.set(id, n + 1);
			if (n) id = `${id}-${n + 1}`;
			if (level >= 2 && level <= 3) headings.push({ level, id, text });
			out.push(`<h${level} id="${id}">${inline(text)}</h${level}>`);
			i++;
			continue;
		}
		// A line holding only an image becomes a figure; `assets/x.svg` points to the document images.
		const image = line.trim().match(/^!\[([^\]]*)\]\(([^)\s]+)\)$/);
		if (image) {
			flush();
			const src = image[2].startsWith('assets/') ? `/api/docs/${image[2]}` : image[2];
			if (/^\/api\/docs\/assets\/[a-z0-9-]+\.(svg|png)$/.test(src)) {
				out.push(`<figure><img src="${escape(src)}" alt="${escape(image[1])}" loading="lazy"><figcaption>${inline(image[1])}</figcaption></figure>`);
			}
			i++;
			continue;
		}
		if (/^(-{3,}|\*{3,})\s*$/.test(line)) {
			flush();
			out.push('<hr>');
			i++;
			continue;
		}
		if (/^\s*\|/.test(line) && i + 1 < lines.length && /^\s*\|?\s*:?-{3,}/.test(lines[i + 1])) {
			flush();
			const head = cells(line);
			i += 2;
			const rows: string[][] = [];
			while (i < lines.length && /^\s*\|/.test(lines[i])) rows.push(cells(lines[i++]));
			out.push(
				`<div class="md-table"><table><thead><tr>${head.map((c) => `<th scope="col">${inline(c)}</th>`).join('')}</tr></thead><tbody>${rows
					.map((r) => `<tr>${r.map((c) => `<td>${inline(c)}</td>`).join('')}</tr>`)
					.join('')}</tbody></table></div>`
			);
			continue;
		}
		if (/^>\s?/.test(line)) {
			flush();
			const body: string[] = [];
			while (i < lines.length && /^>\s?/.test(lines[i])) body.push(lines[i++].replace(/^>\s?/, ''));
			out.push(`<blockquote>${render(body.join('\n')).html}</blockquote>`);
			continue;
		}
		const item = line.match(/^(\s*)([-*]|\d+\.)\s+(.*)$/);
		if (item) {
			flush();
			const ordered = /\d/.test(item[2]);
			const tag = ordered ? 'ol' : 'ul';
			const parts: string[] = [];
			while (i < lines.length) {
				const m = lines[i].match(/^(\s*)([-*]|\d+\.)\s+(.*)$/);
				if (!m) {
					// A non-empty, indented line continues the current item.
					if (lines[i].trim() && /^\s{2,}/.test(lines[i]) && parts.length) {
						parts[parts.length - 1] += ' ' + inline(lines[i].trim());
						i++;
						continue;
					}
					break;
				}
				if (m[1].length >= 2 && parts.length) {
					const nested: string[] = [];
					const nestedOrdered = /\d/.test(m[2]);
					while (i < lines.length) {
						const n = lines[i].match(/^(\s{2,})([-*]|\d+\.)\s+(.*)$/);
						if (!n) break;
						nested.push(`<li>${inline(n[3])}</li>`);
						i++;
					}
					const t = nestedOrdered ? 'ol' : 'ul';
					parts[parts.length - 1] += `<${t}>${nested.join('')}</${t}>`;
					continue;
				}
				parts.push(inline(m[3]));
				i++;
			}
			out.push(`<${tag}>${parts.map((p) => `<li>${p}</li>`).join('')}</${tag}>`);
			continue;
		}
		para.push(line.trim());
		i++;
	}
	flush();
	return { html: out.join('\n'), headings };
}
