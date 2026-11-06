<script lang="ts">
	import Icon from '#lib/components/Icon.svelte';
	import Term from '#lib/components/Term.svelte';
	import { i18n } from '#lib/i18n/index.svelte.js';
	import { session } from '#lib/session.svelte.js';

	// Written for the thesis committee: what the project asks, contributes and has built so far.
	// Dataset sizes are targets from the proposal, never results.
	const copy = {
		vi: {
			title: 'Mỗi câu trả lời đều chỉ về đúng câu trong luật',
			pitch: 'Lexora là đồ án tốt nghiệp về hỏi đáp pháp luật lao động Việt Nam. Văn bản luật được tách thành các quy phạm có cấu trúc; người duyệt đối chiếu từng quy phạm với nguyên văn, và chỉ những gì được duyệt mới dùng để trả lời, kèm trích dẫn chính xác đến từng ký tự.',
			open: 'Mở bản demo',
			signin: 'Đăng nhập để dùng thử',
			specimen: 'Một câu, sau khi tách',
			problem: 'Bài toán',
			usual: 'RAG thông thường trên văn bản luật',
			usualItems: ['Cắt văn bản thành đoạn cố định, dễ tách quy định khỏi điều kiện hoặc ngoại lệ của nó.', 'Trích dẫn ở mức đoạn, khó biết câu trả lời dựa vào câu nào.', 'Tri thức do mô hình ngôn ngữ trích xuất chưa được kiểm chứng trước khi dùng.'],
			ours: 'Hướng tiếp cận của Lexora',
			rqLabel: 'Câu hỏi nghiên cứu',
			rq: 'So với truy xuất trên các đoạn cắt cố định hoặc cắt theo cấu trúc, một kho quy phạm có bằng chứng và đã qua kiểm chứng có giúp hệ thống truy xuất đúng căn cứ hơn, trích dẫn chính xác hơn và từ chối đúng khi thiếu căn cứ hay không?',
			contributions: 'Đóng góp chính',
			items: [
				['Lược đồ quy phạm có bằng chứng', 'Mỗi thành phần kèm đoạn trích nguyên văn, vị trí ký tự Unicode và mã SHA-256 của văn bản đã chuẩn hóa. Trích dẫn sai một ký tự là bị phát hiện.'],
				['Kiểm chứng tự động kết hợp người duyệt', 'Kiểm tra lược đồ, tham chiếu và bằng chứng; người duyệt tô từng thành phần trên trang luật; mọi câu chưa có quy phạm phải được xử lý trước khi công bố.'],
				['Hỏi đáp chỉ trên tri thức đã duyệt', 'Truy xuất BM25 không phân biệt dấu, tùy chọn tìm theo ngữ nghĩa; câu trả lời của mô hình bị từ chối nếu trích dẫn nằm ngoài các đoạn đã cung cấp.'],
				['Thiết kế thực nghiệm có kiểm soát', 'Bốn cấu hình dùng chung nguồn, câu hỏi, mô hình sinh và ngân sách ngữ cảnh, chỉ khác nguồn tri thức.']
			],
			architecture: 'Kiến trúc',
			flow: [['Nguồn chính thống', 'Cổng VBPL'], ['Bản chụp bất biến', 'kèm checksum'], ['Chuẩn hóa', 'mốc của mọi vị trí'], ['Phân cấp', 'Điều, khoản, điểm'], ['Tách quy phạm', 'quy tắc hoặc AI'], ['Kiểm chứng', 'lược đồ, bằng chứng'], ['Người duyệt', 'duyệt, loại, sửa'], ['Kho có phiên bản', 'mỗi lần công bố'], ['Truy xuất', 'chỉ quy phạm đã duyệt'], ['Trả lời', 'kèm trích dẫn']],
			stack: 'Lõi pipeline là Python chỉ dùng thư viện chuẩn để tái lập thực nghiệm; lớp web FastAPI có đăng nhập ba vai trò; giao diện SvelteKit song ngữ; chạy cục bộ, không gọi mạng nếu không được bật rõ ràng.',
			experiment: 'Thiết kế thực nghiệm',
			cols: ['Cấu hình', 'Nguồn tri thức', 'So sánh để trả lời'],
			rows: [['ĐK1', 'Đoạn cắt cố định', 'Mốc cơ sở'], ['ĐK2', 'Đoạn cắt theo Điều, khoản, điểm', 'Tác động của cấu trúc văn bản'], ['ĐK3', 'Kho quy phạm do mô hình trích xuất, trước kiểm chứng', 'Tác động của biểu diễn quy phạm'], ['ĐK4', 'Cùng kho đó, sau kiểm chứng tự động', 'Tác động của bước kiểm chứng']],
			metrics: 'Chỉ số: Recall@K, độ chính xác trích dẫn, độ bám nguồn, độ đúng (thang 0 đến 2), tỷ lệ từ chối đúng; chất lượng trích xuất đo bằng precision, recall, F1 và Cohen’s kappa.',
			data: 'Dữ liệu dự kiến theo đề cương: khoảng 150 câu hỏi, tách phát triển và kiểm tra giữ kín; 40 đến 60 điều khoản được hai người gán nhãn độc lập. Các con số là mục tiêu, chưa phải kết quả.',
			status: 'Trạng thái hiện thực',
			done: ['Bản chụp VBPL kèm checksum, phân tích Điều, khoản, điểm', 'Hợp đồng dữ liệu và bộ kiểm chứng', 'Tách quy phạm theo quy tắc; tách bằng AI tùy chọn có đối chiếu nguyên văn', 'Kho nhiều phiên bản, quy trình duyệt và công bố, đăng nhập ba vai trò', 'Hỏi đáp có trích dẫn; sơ đồ quy phạm và cấu trúc'],
			planned: ['Pipeline bốn cấu hình ĐK1 đến ĐK4', 'Bộ câu hỏi, tập gán nhãn chuẩn và kết quả thực nghiệm'],
			limits: 'Giới hạn',
			limitItems: ['Không phải tư vấn pháp lý; người gán nhãn không thay chuyên gia pháp lý.', 'Hiệu lực pháp luật của văn bản chưa được xác minh.', 'Phạm vi thử nghiệm là một phần pháp luật lao động.', 'Bộ tách tự động có thể bỏ sót hoặc tách sai, vì vậy mọi câu đều phải được người duyệt xử lý.']
		},
		en: {
			title: 'Every answer points to the exact sentence in the law',
			pitch: 'Lexora is a thesis project on question answering over Vietnamese labour law. Statutes are split into structured norms; a reviewer checks each norm against the exact text, and only approved norms are used to answer, with citations precise to the character.',
			open: 'Open the demo',
			signin: 'Sign in to try it',
			specimen: 'One sentence, after extraction',
			problem: 'The problem',
			usual: 'Typical RAG over statutes',
			usualItems: ['Fixed-size chunks split a rule from its conditions or exceptions.', 'Citations point to a chunk, so it is hard to see which sentence an answer rests on.', 'Knowledge extracted by a language model is used before anyone checks it.'],
			ours: 'Lexora’s approach',
			rqLabel: 'Research question',
			rq: 'Compared with retrieval over fixed or structural chunks, does a knowledge base of evidence-backed, validated norms help a labour-law QA system retrieve the right grounds, cite more precisely and refuse correctly when evidence is missing?',
			contributions: 'Contributions',
			items: [
				['An evidence-backed norm schema', 'Every part carries a verbatim quote, its Unicode character offsets and the SHA-256 of the normalised text. A citation off by one character is caught.'],
				['Automatic validation with human review', 'Schema, reference and evidence checks; reviewers mark each part on the statute; every sentence without a norm must be handled before publishing.'],
				['Answers from reviewed knowledge only', 'Accent-insensitive BM25 with optional semantic search; model answers are rejected when they cite outside the supplied passages.'],
				['A controlled experiment design', 'Four configurations share sources, questions, generator and context budget, and differ only in the knowledge source.']
			],
			architecture: 'Architecture',
			flow: [['Official source', 'VBPL portal'], ['Immutable snapshot', 'with checksum'], ['Normalisation', 'anchor of every offset'], ['Structure', 'articles, clauses, points'], ['Norm extraction', 'rules or AI'], ['Validation', 'schema, evidence'], ['Reviewer', 'approve, reject, edit'], ['Versioned base', 'one revision per publish'], ['Retrieval', 'approved norms only'], ['Answer', 'with citations']],
			stack: 'The core pipeline is standard-library Python so experiments reproduce; a FastAPI layer adds sign-in with three roles; the SvelteKit interface is bilingual; everything runs locally with no network unless explicitly enabled.',
			experiment: 'Experiment design',
			cols: ['Configuration', 'Knowledge source', 'Comparison answers'],
			rows: [['DK1', 'Fixed-size chunks', 'Baseline'], ['DK2', 'Chunks by article, clause, point', 'Effect of document structure'], ['DK3', 'Model-extracted norm base, before validation', 'Effect of the norm representation'], ['DK4', 'The same base, after automatic validation', 'Effect of validation']],
			metrics: 'Metrics: Recall@K, citation accuracy, groundedness, correctness (0 to 2 rubric) and correct refusal; extraction quality by precision, recall, F1 and Cohen’s kappa.',
			data: 'Planned data from the proposal: about 150 questions split into development and held-out sets; 40 to 60 provisions labelled independently by two annotators. These are targets, not results.',
			status: 'Implementation status',
			done: ['VBPL snapshots with checksums, article, clause and point parsing', 'Data contract and validators', 'Rule-based extraction; optional AI extraction checked against the exact text', 'Versioned bases, review and publish workflow, sign-in with three roles', 'Cited question answering; norm and structure graphs'],
			planned: ['The four-configuration pipeline DK1 to DK4', 'Question set, gold labels and experiment results'],
			limits: 'Limits',
			limitItems: ['Not legal advice; annotators do not replace legal experts.', 'The legal validity of documents is not verified.', 'The pilot covers part of Vietnamese labour law.', 'Automatic extraction can miss or mis-split sentences, so every sentence must be handled by a reviewer.']
		}
	};
	const c = $derived(copy[i18n.locale]);
</script>

<svelte:head><title>{i18n.locale === 'vi' ? 'Giới thiệu' : 'About'} · Lexora</title></svelte:head>

<div class="page about">
	<section class="hero">
		<div>
			<h1 class="title big">{c.title}</h1>
			<p class="lead">{c.pitch}</p>
			<div class="row">
				{#if session.account}<a class="btn primary" href="/">{c.open}<Icon name="arrow" /></a>{:else}<a class="btn primary" href="/login">{c.signin}<Icon name="arrow" /></a>{/if}
			</div>
		</div>
		<figure class="sheet specimen">
			<p class="serif sentence" lang="vi">
				<mark class="hl-condition" data-term="conditions">Khi kết thúc thời gian thử việc</mark>,
				<mark class="hl-actor" data-term="actor">người sử dụng lao động</mark>
				<b data-term="obligation">phải</b>
				<mark class="hl-action" data-term="action">thông báo</mark>
				<mark class="hl-object" data-term="object">kết quả thử việc</mark> cho
				<mark class="hl-party" data-term="recipient">người lao động</mark>.
			</p>
			<p class="small muted">
				<Term key="actor" /> · <Term key="action" /> · <Term key="object" /> · <Term key="recipient" /> · <Term key="conditions" /> · <Term key="modality" />
			</p>
		</figure>
	</section>

	<section class="block">
		<h2 class="subtitle">{c.problem}</h2>
		<div class="compare">
			<div><h3 class="heading"><Icon name="warn" />{c.usual}</h3><ul>{#each c.usualItems as item (item)}<li>{item}</li>{/each}</ul></div>
			<div><h3 class="heading"><Icon name="check" />{c.ours}</h3>
				<ul>
					<li><Term key="norm" />: <Term key="actor" />, <Term key="action" />, <Term key="modality" />, <Term key="conditions" />, <Term key="exceptions" />…</li>
					<li><Term key="evidence" /></li>
					<li><Term key="approved" /></li>
				</ul>
			</div>
		</div>
		<h3 class="subtitle rq-head">{c.rqLabel}</h3>
		<blockquote class="rq sheet"><p class="serif">{c.rq}</p></blockquote>
	</section>

	<section class="block">
		<h2 class="subtitle">{c.contributions}</h2>
		<ol class="contrib">
			{#each c.items as [head, body] (head)}
				<li class="sheet"><div><h3 class="heading">{head}</h3><p class="small">{body}</p></div></li>
			{/each}
		</ol>
	</section>

	<section class="block">
		<h2 class="subtitle">{c.architecture}</h2>
		<ol class="flow">
			{#each c.flow as [head, sub], i (head)}
				<li class:marked={i >= 4 && i <= 6}><strong>{head}</strong><span>{sub}</span></li>
			{/each}
		</ol>
		<p class="small muted">{c.stack}</p>
	</section>

	<section class="block">
		<h2 class="subtitle">{c.experiment}</h2>
		<div class="sheet pad">
			<table class="table">
				<thead><tr>{#each c.cols as col (col)}<th scope="col">{col}</th>{/each}</tr></thead>
				<tbody>{#each c.rows as row (row[0])}<tr><td><strong class="serif">{row[0]}</strong></td><td>{row[1]}</td><td>{row[2]}</td></tr>{/each}</tbody>
			</table>
			<p class="small">{c.metrics}</p>
			<p class="small muted">{c.data}</p>
		</div>
	</section>

	<section class="block two">
		<div class="panel">
			<h2 class="subtitle">{c.status}</h2>
			<ul class="status">
				{#each c.done as item (item)}<li class="done"><Icon name="check" size={16} />{item}</li>{/each}
				{#each c.planned as item (item)}<li class="plan"><Icon name="history" size={16} />{item}</li>{/each}
			</ul>
		</div>
		<div class="panel">
			<h2 class="subtitle">{c.limits}</h2>
			<ul class="limits">{#each c.limitItems as item (item)}<li>{item}</li>{/each}</ul>
		</div>
	</section>
</div>

<style>
	.about {
		display: grid;
		gap: 56px;
	}
	.hero {
		display: grid;
		grid-template-columns: minmax(0, 1.1fr) minmax(0, 1fr);
		gap: 40px;
		align-items: center;
		padding-top: 16px;
	}
	.hero > div {
		display: grid;
		gap: 18px;
	}
	.big {
		font-size: clamp(30px, 3.4vw, 46px);
		line-height: 1.12;
		letter-spacing: -0.02em;
	}
	.hero .lead {
		font-size: 17px;
	}
	.specimen {
		margin: 0;
		padding: 24px 26px;
		display: grid;
		gap: 12px;
	}
	.sentence {
		font-size: 19px;
		line-height: 2;
	}
	.sentence mark {
		background: var(--hl);
		color: var(--ink);
		padding: 1px 3px;
		border-radius: 2px;
		cursor: help;
		box-decoration-break: clone;
		-webkit-box-decoration-break: clone;
	}
	.sentence b {
		font-weight: 600;
		border-radius: 999px;
		box-shadow: 0 0 0 1.5px var(--ink-2);
		padding: 0 4px;
		cursor: help;
	}
	.block {
		display: grid;
		gap: 16px;
	}
	.compare {
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 20px;
	}
	.compare > div {
		padding: 20px 24px;
		border: 1px solid var(--rule);
		border-radius: var(--r-panel);
		background: var(--paper);
	}
	.compare h3 {
		display: flex;
		gap: 8px;
		align-items: center;
		margin-bottom: 8px;
	}
	.compare ul,
	.limits {
		margin: 0;
		padding-left: 20px;
		display: grid;
		gap: 6px;
	}
	.rq-head {
		margin-top: 12px;
		font-size: 17px;
	}
	.rq {
		margin: 0;
		padding: 22px 26px;
		display: grid;
		gap: 6px;
	}
	.rq .serif {
		font-size: 19px;
		line-height: 1.6;
		max-width: 80ch;
	}
	.contrib {
		list-style: none;
		margin: 0;
		padding: 0;
		display: grid;
		grid-template-columns: 1fr 1fr;
		gap: 16px;
	}
	.contrib li {
		display: grid;
		gap: 14px;
		padding: 20px 22px;
	}
	.contrib .heading {
		margin-bottom: 4px;
	}
	.flow {
		list-style: none;
		margin: 0;
		padding: 0;
		display: grid;
		grid-template-columns: repeat(5, minmax(0, 1fr));
		gap: 12px;
	}
	.flow li {
		display: grid;
		gap: 2px;
		padding: 12px 14px;
		background: var(--paper);
		border: 1px solid var(--rule);
		border-radius: var(--r-panel);
	}
	.flow li.marked {
		border-color: var(--ink-2);
		box-shadow: inset 0 0 0 1px var(--ink-2);
	}
	.flow span {
		font-size: 13px;
		color: var(--muted);
	}
	.pad {
		padding: 16px 20px 20px;
		display: grid;
		gap: 12px;
	}
	.two {
		grid-template-columns: 1fr 1fr;
		gap: 20px;
	}
	.two .panel {
		display: grid;
		gap: 12px;
		align-content: start;
	}
	.status {
		list-style: none;
		margin: 0;
		padding: 0;
		display: grid;
		gap: 8px;
	}
	.status li {
		display: flex;
		gap: 10px;
		align-items: flex-start;
	}
	.status .done :global(svg) {
		color: var(--approve);
		margin-top: 3px;
	}
	.status .plan {
		color: var(--muted);
	}
	.status .plan :global(svg) {
		color: var(--attention);
		margin-top: 3px;
	}
	@media (max-width: 960px) {
		.hero,
		.compare,
		.contrib,
		.two {
			grid-template-columns: 1fr;
		}
		.flow {
			grid-template-columns: 1fr 1fr;
		}
	}
</style>
