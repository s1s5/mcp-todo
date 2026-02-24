<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';

	interface Extension {
		id: number;
		name: string;
		type: string;
		cmd: string;
		args: string[];
		envs: Record<string, string>;
		timeout: number;
		created_at: string;
		updated_at: string;
	}

	let extension: Extension | null = $state(null);
	let name = $state('');
	let type = $state('stdio');
	let cmd = $state('');
	let args = $state('');
	let envs = $state('');
	let timeout = $state(300);
	let loading = $state(true);
	let submitting = $state(false);
	let error = $state('');

	// URLパラメータからextension IDを取得
	const extensionId = $derived($page.params.extension);

	function getCSRFToken(): string {
		const cookieName = 'csrftoken';
		let cookieValue = '';
		if (document.cookie && document.cookie !== '') {
			const cookies = document.cookie.split(';');
			for (let i = 0; i < cookies.length; i++) {
				const cookie = cookies[i].trim();
				if (cookie.substring(0, cookieName.length + 1) === (cookieName + '=')) {
					cookieValue = decodeURIComponent(cookie.substring(cookieName.length + 1));
					break;
				}
			}
		}
		return cookieValue;
	}

	async function fetchExtensionDetail() {
		loading = true;
		error = '';
		try {
			const res = await fetch(`/api/extensions/${extensionId}/`);
			if (!res.ok) throw new Error('Failed to fetch extension');
			extension = await res.json();
			// フォームの初期値を設定
			name = extension!.name;
			type = extension!.type || 'stdio';
			cmd = extension!.cmd || '';
			args = extension!.args && extension!.args.length > 0 ? JSON.stringify(extension!.args) : '';
			envs = extension!.envs && Object.keys(extension!.envs).length > 0 ? JSON.stringify(extension!.envs) : '';
			timeout = extension!.timeout || 300;
		} catch (e) {
			error = e instanceof Error ? e.message : 'Unknown error';
		} finally {
			loading = false;
		}
	}

	async function handleSubmit(event: Event) {
		event.preventDefault();
		submitting = true;
		error = '';

		try {
			// JSON文字列をパース
			let parsedArgs: string[] = [];
			let parsedEnvs: Record<string, string> = {};
			
			if (args.trim()) {
				parsedArgs = JSON.parse(args);
			}
			if (envs.trim()) {
				parsedEnvs = JSON.parse(envs);
			}

			const res = await fetch(`/api/extensions/${extensionId}/`, {
				method: 'PUT',
				headers: {
					'Content-Type': 'application/json',
					'X-CSRFToken': getCSRFToken()
				},
				body: JSON.stringify({
					name,
					type,
					cmd,
					args: parsedArgs,
					envs: parsedEnvs,
					timeout
				})
			});

			if (!res.ok) {
				const data = await res.json();
				throw new Error(data.detail || 'Failed to update extension');
			}

			await goto(`/extension/${extensionId}/`);
		} catch (e) {
			if (e instanceof SyntaxError) {
				error = 'Invalid JSON format in args or envs';
			} else {
				error = e instanceof Error ? e.message : 'Unknown error';
			}
		} finally {
			submitting = false;
		}
	}

	onMount(() => {
		fetchExtensionDetail();
	});
</script>

<div class="p-6 max-w-2xl mx-auto">
	<div class="flex items-center gap-4 mb-6">
		<a
			href="/extension/{extensionId}/"
			class="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded transition"
		>
			<svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
			</svg>
		</a>
		<h1 class="text-2xl font-bold">Update Extension</h1>
	</div>

	{#if loading}
		<p class="text-gray-500">Loading...</p>
	{:else if error && !name}
		<p class="text-red-500">{error}</p>
	{:else}
		<form onsubmit={handleSubmit} class="bg-white shadow rounded-lg p-6 space-y-6">
			{#if error}
				<div class="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded">
					{error}
				</div>
			{/if}

			<div>
				<label for="name" class="block text-sm font-medium text-gray-700 mb-1">
					Name <span class="text-red-500">*</span>
				</label>
				<input
					type="text"
					id="name"
					bind:value={name}
					required
					class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
					placeholder="Enter extension name"
				/>
			</div>

			<div>
				<label for="type" class="block text-sm font-medium text-gray-700 mb-1">
					Type
				</label>
				<select
					id="type"
					bind:value={type}
					class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
				>
					<option value="stdio">stdio</option>
					<option value="http">http</option>
				</select>
				<p class="mt-1 text-sm text-gray-500">Default: stdio</p>
			</div>

			<div>
				<label for="cmd" class="block text-sm font-medium text-gray-700 mb-1">
					Command <span class="text-red-500">*</span>
				</label>
				<input
					type="text"
					id="cmd"
					bind:value={cmd}
					required
					class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent font-mono"
					placeholder="e.g., python, node"
				/>
			</div>

			<div>
				<label for="args" class="block text-sm font-medium text-gray-700 mb-1">
					Args (JSON Array)
				</label>
				<textarea
					id="args"
					bind:value={args}
					rows="3"
					class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent font-mono resize-y"
					placeholder='e.g., ["script.py", "--arg1"]'
				></textarea>
				<p class="mt-1 text-sm text-gray-500">Optional. JSON array format. Default: []</p>
			</div>

			<div>
				<label for="envs" class="block text-sm font-medium text-gray-700 mb-1">
					Envs (JSON Object)
				</label>
				<textarea
					id="envs"
					bind:value={envs}
					rows="3"
					class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent font-mono resize-y"
					placeholder={`{"KEY": "value"}`}
				></textarea>
				<p class="mt-1 text-sm text-gray-500">Optional. JSON object format. Default: {}</p>
			</div>

			<div>
				<label for="timeout" class="block text-sm font-medium text-gray-700 mb-1">
					Timeout (seconds)
				</label>
				<input
					type="number"
					id="timeout"
					bind:value={timeout}
					min="1"
					class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
				/>
				<p class="mt-1 text-sm text-gray-500">Default: 300</p>
			</div>

			<div class="flex gap-3 pt-2">
				<button
					type="submit"
					disabled={submitting}
					class="flex-1 px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition disabled:bg-blue-400 disabled:cursor-not-allowed"
				>
					{submitting ? 'Updating...' : 'Update'}
				</button>
				<a
					href="/extension/{extensionId}/"
					class="px-4 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50 transition"
				>
					Cancel
				</a>
			</div>
		</form>
	{/if}
</div>
