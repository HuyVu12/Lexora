<script lang="ts">
	import PageGuide from '#lib/components/PageGuide.svelte';
	import { page } from '$app/state';
	import ChatView from '#lib/components/ChatView.svelte';
	import ChatHead from '#lib/components/ChatHead.svelte';
	import { t } from '#lib/i18n/index.svelte.js';
</script>

<svelte:head><title>{t('chat.title')} · Lexora</title></svelte:head>

<div class="page">
	<ChatHead />
	<PageGuide name="chat" steps={3} />
	{#key page.params.id}<ChatView sessionId={page.params.id} />{/key}
</div>
