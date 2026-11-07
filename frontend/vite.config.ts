import adapter from '@sveltejs/adapter-static';
import { sveltekit } from '@sveltejs/kit/vite';
import { defineConfig } from 'vite';

// Static SPA: FastAPI serves build/index.html for every client route and injects the POST token.
export default defineConfig({
	plugins: [
		sveltekit({
			adapter: adapter({ pages: 'build', assets: 'build', fallback: 'index.html', strict: true })
		})
	],
	server: {
		// `npm run dev` proxies API and viewer pages to a running `python -m legal_ai.web` on 8766.
		proxy: { '/api': 'http://127.0.0.1:8766', '/viewer': 'http://127.0.0.1:8766', '/structure.html': 'http://127.0.0.1:8766' }
	}
});
