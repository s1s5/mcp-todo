<script lang="ts">
	import { onMount } from 'svelte';

	interface Agent {
		id: number;
		name: string;
		system_message: string;
		created_at: string;
		updated_at: string;
	}

	let agents: Agent[] = $state([]);
	let loading = $state(true);
	let error = $state('');

	async function fetchAgents() {
		loading = true;
		error = '';
		try {
			const res = await fetch('/api/agents/');
			if (!res.ok) throw new Error('Failed to fetch');
			agents = await res.json();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Unknown error';
		} finally {
			loading = false;
		}
	}

	onMount(() => {
		fetchAgents();
	});
</script>

<div class="p-6 max-w-4xl mx-auto">
	<a href="/" class="text-blue-600 hover:text-blue-800 mb-4 inline-block">← Back to Home</a>
	
	<div class="flex justify-between items-center mb-6">
		<h1 class="text-2xl font-bold">Agents</h1>
		<button
			onclick={fetchAgents}
			class="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition"
		>
			Refresh
		</button>
	</div>

	{#if loading}
		<p class="text-gray-500">Loading...</p>
	{:else if error}
		<p class="text-red-500">{error}</p>
	{:else if agents.length === 0}
		<p class="text-gray-500">No Agents found.</p>
	{:else}
		<div class="bg-white shadow rounded-lg overflow-hidden">
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
							System Message
						</th>
						<th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
							Created
						</th>
					</tr>
				</thead>
				<tbody class="bg-white divide-y divide-gray-200">
					{#each agents as agent}
						<tr class="hover:bg-gray-50">
							<td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
								{agent.id}
							</td>
							<td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900 font-medium">
								{agent.name}
							</td>
							<td class="px-6 py-4 text-sm text-gray-500 max-w-xs truncate" title={agent.system_message}>
								{agent.system_message || '-'}
							</td>
							<td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
								{new Date(agent.created_at).toLocaleString()}
							</td>
						</tr>
					{/each}
				</tbody>
			</table>
		</div>
	{/if}
</div>
