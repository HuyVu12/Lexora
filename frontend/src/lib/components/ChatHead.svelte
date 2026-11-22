<script lang="ts">
	import Skeleton from './Skeleton.svelte';
	import { cachedAppState } from '#lib/app-state.svelte.js';
	import { t } from '#lib/i18n/index.svelte.js';

	// The title of the chat pages with one line of facts: what can be asked, how many conversations, and the
	// standing reminder that answers are not legal advice. The page guide explains the rest.
	const app = $derived(cachedAppState());
	const usable = $derived(app?.knowledge_bases.filter((k) => k.approved_claims > 0).length ?? 0);
</script>

<header class="page-head">
	<div>
		<h1 class="title">{t('chat.title')}</h1>
		<p class="facts">
			{#if app}
				<span><strong>{usable}</strong> {t('chat.facts.kbs', { n: usable })}</span>
				<span><strong>{app.chat_sessions.length}</strong> {t('chat.facts.chats', { n: app.chat_sessions.length })}</span>
			{:else}
				<span><Skeleton width="120px" height="12px" /></span><span><Skeleton width="130px" height="12px" /></span>
			{/if}
			<span>{t('chat.facts.notAdvice')}</span>
		</p>
	</div>
</header>
