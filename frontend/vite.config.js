import path from 'path';
import { sveltekit } from '@sveltejs/kit/vite';
import tailwindcss from '@tailwindcss/vite';
import { defineConfig } from 'vite';

export default defineConfig({
	plugins: [tailwindcss(), sveltekit()],
	resolve: {
		alias: {
			'$data': path.resolve('../backend/data')
		}
	},
	server: {
		fs: {
			allow: ['..']
		},
		allowedHosts: ['.ngrok-free.app']
	}
});
