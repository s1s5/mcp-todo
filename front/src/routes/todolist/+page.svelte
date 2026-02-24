<script lang="ts">
	import { onMount } from 'svelte';

	interface TodoList {
		id: number;
		workdir: string;
		created_at: string;
	}

	let todolists: TodoList[] = $state([]);
	let loading = $state(true);
	let error = $state('');

	async function fetchTodoLists() {
		loading = true;
		error = '';
		try {
			const res = await fetch('/api/todolists/');
			if (!res.ok) throw new Error('Failed to fetch');
			todolists = await res.json();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Unknown error';
		} finally {
			loading = false;
		}
	}

	onMount(() => {
		fetchTodoLists();
	});
</script>

<div class="p-6 max-w-4xl mx-auto">
	<div class="flex justify-between items-center mb-6">
		<h1 class="text-2xl font-bold">Todo Lists</h1>
		<button
			onclick={fetchTodoLists}
			class="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition"
		>
			Refresh
		</button>
	</div>

	{#if loading}
		<p class="text-gray-500">Loading...</p>
	{:else if error}
		<p class="text-red-500">{error}</p>
	{:else if todolists.length === 0}
		<p class="text-gray-500">No TodoLists found.</p>
	{:else}
		<div class="bg-white shadow rounded-lg overflow-hidden">
			<table class="min-w-full divide-y divide-gray-200">
				<thead class="bg-gray-50">
					<tr>
						<th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
							ID
						</th>
						<th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
							Workdir
						</th>
						<th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
							Created
						</th>
					</tr>
				</thead>
				<tbody class="bg-white divide-y divide-gray-200">
					{#each todolists as list}
						<a href="/todolist/{list.id}" class="block">
							<tr class="hover:bg-gray-50 cursor-pointer">
								<td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
									{list.id}
								</td>
								<td class="px-6 py-4 whitespace-nowrap text-sm text-gray-900 font-mono">
									{list.workdir}
								</td>
								<td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
									{new Date(list.created_at).toLocaleString()}
								</td>
							</tr>
						</a>
					{/each}
				</tbody>
			</table>
		</div>
	{/if}
</div>
