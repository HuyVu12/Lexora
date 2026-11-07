<script lang="ts">
	import PageGuide from '#lib/components/PageGuide.svelte';
	import { page } from '$app/state';
	import ChatView from '#lib/components/ChatView.svelte';
	import { t } from '#lib/i18n/index.svelte.js';
</script>

<svelte:head><title>{t('chat.title')} · Lexora</title></svelte:head>

<div class="page">
	<header class="page-head">
		<div>
			<h1 class="title">{t('chat.title')}</h1>
			<p class="lead">{t('chat.lead')}</p>
		</div>
	</header>
	<PageGuide name="chat" steps={3} />
	{#key page.params.id}<ChatView sessionId={page.params.id} />{/key}
</div>
