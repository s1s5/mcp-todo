<script lang="ts">
	import { onMount } from 'svelte';

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

	let extensions: Extension[] = $state([]);
	let loading = $state(true);
	let error = $state('');

	async function fetchExtensions() {
		loading = true;
		error = '';
		try {
			const res = await fetch('/api/extensions/');
			if (!res.ok) throw new Error('Failed to fetch');
			extensions = await res.json();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Unknown error';
		} finally {
			loading = false;
		}
	}

	onMount(() => {
		fetchExtensions();
	});
</script>

<div class="p-6 max-w-4xl mx-auto">
	<a href="/" id="back-link" class="text-blue-600 hover:text-blue-800 mb-4 inline-block">← 戻る</a>
	
	<div class="flex justify-between items-center mb-6">
		<h1 class="text-2xl font-bold">Extensions</h1>
		<button
			id="refresh-button"
			onclick={fetchExtensions}
			class="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition"
		>
			Refresh
		</button>
	</div>

	<div class="mb-4">
		<a
			href="/extension/create/"
			class="inline-flex items-center px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700 transition"
		>
			<svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
			</svg>
			新規作成
		</a>
	</div>

	{#if loading}
		<p id="loading-indicator" class="text-gray-500">Loading...</p>
	{:else if error}
		<p class="text-red-500">{error}</p>
	{:else if extensions.length === 0}
		<p id="no-extensions" class="text-gray-500">No Extensions found.</p>
	{:else}
		<div id="extensions-table" class="bg-white shadow rounded-lg overflow-hidden">
			<table class="min-w-full divide-y divide-gray-200">
				<thead class="bg-gray-50">
					<tr>
						<th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
							ID
						</th>
						<th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
							Name
						</th>
						<th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
							Type
						</th>
						<th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
							Command
						</th>
						<th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
							Timeout
						</th>
						<th class="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase tracking-wider">
							Actions
						</th>
					</tr>
				</thead>
				<tbody class="bg-white divide-y divide-gray-200">
					{#each extensions as ext}
						<tr class="hover:bg-gray-50">
							<td class="px-6 py-4 whitespace-nowrap text-sm text-blue-600 font-medium">
								{ext.id}
							</td>
							<td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900 font-medium">
								{ext.name}
							</td>
							<td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
								{ext.type}
							</td>
							<td class="px-6 py-4 text-sm text-gray-500 font-mono max-w-xs truncate" title={ext.cmd}>
								{ext.cmd || '-'}
							</td>
							<td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
								{ext.timeout}s
							</td>
							<td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
								<a
									href="/extension/{ext.id}/"
									class="text-blue-600 hover:text-blue-800 mr-3"
								>
									詳細
								</a>
								<a
									href="/extension/{ext.id}/update/"
									class="text-green-600 hover:text-green-800 mr-3"
								>
									編集
								</a>
								<a
									href="/extension/{ext.id}/delete/"
									class="text-red-600 hover:text-red-800"
								>
									削除
								</a>
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
	{/if}
</div>
