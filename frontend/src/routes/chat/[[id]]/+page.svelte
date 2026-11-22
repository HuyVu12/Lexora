<script lang="ts">
	import { page } from '$app/state';
	import ChatView from '#lib/components/ChatView.svelte';

	// One route for a new conversation (/chat, optionally ?kb=...) and an open one (/chat/<id>): the view stays
	// mounted between them, so sending the first question or switching conversations never reloads the screen.
	const preselect = $derived(page.url.searchParams.getAll('kb'));
</script>

<ChatView sessionId={page.params.id} {preselect} />
