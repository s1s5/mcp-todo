<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';

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
	let loading = $state(true);
	let error = $state('');

	// URLパラメータからextension IDを取得
	const extensionId = $derived($page.params.extension);

	async function fetchExtensionDetail() {
		loading = true;
		error = '';
		try {
			const res = await fetch(`/api/extensions/${extensionId}/`);
			if (!res.ok) throw new Error('Failed to fetch extension');
			extension = await res.json();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Unknown error';
		} finally {
			loading = false;
		}
	}

	onMount(() => {
		fetchExtensionDetail();
	});
</script>

<div class="p-6 max-w-4xl mx-auto">
	<div class="flex items-center gap-4 mb-6">
		<a
			href="/extension/"
			class="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded transition"
		>
			<svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
			</svg>
		</a>
		<h1 class="text-2xl font-bold">Extension Details</h1>
		<div class="flex gap-2 ml-4">
			<a
				href="/extension/{extensionId}/update/"
				class="px-3 py-1.5 text-sm text-blue-600 hover:bg-blue-50 rounded transition"
			>
				編集
			</a>
			<a
				href="/extension/{extensionId}/delete/"
				class="px-3 py-1.5 text-sm text-red-600 hover:bg-red-50 rounded transition"
			>
				削除
			</a>
		</div>
		<button
			onclick={fetchExtensionDetail}
			class="ml-auto px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition"
		>
			Refresh
		</button>
	</div>

	{#if loading}
		<p class="text-gray-500">Loading...</p>
	{:else if error}
		<p class="text-red-500">{error}</p>
	{:else if !extension}
		<p class="text-gray-500">Extension not found.</p>
	{:else}
		<!-- Extension Details Card -->
		<div class="bg-white shadow rounded-lg overflow-hidden">
			<div class="px-6 py-4 border-b border-gray-200 bg-gray-50">
				<h2 class="text-lg font-semibold text-gray-900">Information</h2>
			</div>
			<div class="p-6">
				<dl class="grid grid-cols-1 gap-x-4 gap-y-6">
					<div>
						<dt class="text-sm font-medium text-gray-500">ID</dt>
						<dd class="mt-1 text-sm text-gray-900">{extension.id}</dd>
					</div>
					<div>
						<dt class="text-sm font-medium text-gray-500">Name</dt>
						<dd class="mt-1 text-sm text-gray-900 font-medium">{extension.name}</dd>
					</div>
					<div>
						<dt class="text-sm font-medium text-gray-500">Type</dt>
						<dd class="mt-1 text-sm text-gray-900">{extension.type}</dd>
					</div>
					<div>
						<dt class="text-sm font-medium text-gray-500">Command</dt>
						<dd class="mt-1 text-sm text-gray-900 font-mono bg-gray-50 p-4 rounded-lg">
							{extension.cmd || '-'}
						</dd>
					</div>
					<div>
						<dt class="text-sm font-medium text-gray-500">Args</dt>
						<dd class="mt-1 text-sm text-gray-900 font-mono bg-gray-50 p-4 rounded-lg">
							{extension.args && extension.args.length > 0 ? JSON.stringify(extension.args) : '-'}
						</dd>
					</div>
					<div>
						<dt class="text-sm font-medium text-gray-500">Envs</dt>
						<dd class="mt-1 text-sm text-gray-900 font-mono bg-gray-50 p-4 rounded-lg whitespace-pre-wrap">
							{extension.envs && Object.keys(extension.envs).length > 0 ? JSON.stringify(extension.envs, null, 2) : '-'}
						</dd>
					</div>
					<div>
						<dt class="text-sm font-medium text-gray-500">Timeout</dt>
						<dd class="mt-1 text-sm text-gray-900">{extension.timeout} seconds</dd>
					</div>
					<div>
						<dt class="text-sm font-medium text-gray-500">Created</dt>
						<dd class="mt-1 text-sm text-gray-900">{new Date(extension.created_at).toLocaleString()}</dd>
					</div>
					<div>
						<dt class="text-sm font-medium text-gray-500">Updated</dt>
						<dd class="mt-1 text-sm text-gray-900">{new Date(extension.updated_at).toLocaleString()}</dd>
					</div>
				</dl>
			</div>
		</div>
	{/if}
</div>
