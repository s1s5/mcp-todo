<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';

	interface Agent {
		id: number;
		name: string;
		system_message: string;
		command: string;
		created_at: string;
		updated_at: string;
	}

	let agent: Agent | null = $state(null);
	let loading = $state(true);
	let error = $state('');
	let deleteError = $state('');
	let deleting = $state(false);

	const agentId = $page.params.agent;

	function getCSRFToken(): string {
		const name = 'csrftoken';
		let cookieValue = '';
		if (document.cookie && document.cookie !== '') {
			const cookies = document.cookie.split(';');
			for (let i = 0; i < cookies.length; i++) {
				const cookie = cookies[i].trim();
				if (cookie.substring(0, name.length + 1) === (name + '=')) {
					cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
					break;
				}
			}
		}
		return cookieValue;
	}

	async function fetchAgent() {
		loading = true;
		error = '';
		try {
			const res = await fetch(`/api/agents/${agentId}/`);
			if (!res.ok) throw new Error('Failed to fetch agent');
			agent = await res.json();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Unknown error';
		} finally {
			loading = false;
		}
	}

	async function handleDelete() {
		if (!agent) return;
		deleting = true;
		deleteError = '';
		try {
			const res = await fetch(`/api/agents/${agent.id}/`, {
				method: 'DELETE',
				headers: {
					'X-CSRFToken': getCSRFToken()
				}
			});
			if (!res.ok) {
				const data = await res.json().catch(() => ({}));
				throw new Error(data.detail || 'Failed to delete agent');
			}
			goto('/agent/');
		} catch (e) {
			deleteError = e instanceof Error ? e.message : 'Unknown error';
		} finally {
			deleting = false;
		}
	}

	onMount(() => {
		fetchAgent();
	});
</script>

<div class="p-6 max-w-2xl mx-auto">
	<div class="mb-6">
		<a
			href="/agent/{agentId}/"
			class="text-blue-600 hover:text-blue-800 inline-flex items-center"
		>
			← Back to Detail
		</a>
	</div>

	<h1 class="text-2xl font-bold mb-6">Delete Agent</h1>

	{#if loading}
		<p class="text-gray-500">Loading...</p>
	{:else if error}
		<p class="text-red-500">{error}</p>
	{:else if agent}
		<div class="bg-white shadow rounded-lg p-6">
			<div class="mb-6">
				<h2 class="text-lg font-semibold text-red-600 mb-2">⚠️ このAgentを削除しますか？</h2>
				<p class="text-gray-600">この操作は取り消せません。</p>
			</div>

			<div class="bg-gray-50 rounded-lg p-4 mb-6">
				<dl class="space-y-3">
					<div>
						<dt class="text-sm font-medium text-gray-500">ID</dt>
						<dd class="text-sm text-gray-900">{agent.id}</dd>
				</div>
					<div>
						<dt class="text-sm font-medium text-gray-500">Name</dt>
						<dd class="text-sm text-gray-900 font-medium">{agent.name}</dd>
					</div>
					<div>
						<dt class="text-sm font-medium text-gray-500">System Message</dt>
						<dd class="text-sm text-gray-900 whitespace-pre-wrap">{agent.system_message || '-'}</dd>
					</div>
					<div>
						<dt class="text-sm font-medium text-gray-500">Command</dt>
						<dd class="text-sm text-gray-900 font-mono">{agent.command || '-'}</dd>
					</div>
					<div>
						<dt class="text-sm font-medium text-gray-500">Created</dt>
						<dd class="text-sm text-gray-900">{new Date(agent.created_at).toLocaleString()}</dd>
					</div>
				</dl>
			</div>

			{#if deleteError}
				<div class="mb-4 p-3 bg-red-50 border border-red-200 rounded text-red-600 text-sm">
					{deleteError}
				</div>
			{/if}

			<div class="flex gap-4">
				<button
					onclick={handleDelete}
					disabled={deleting}
					class="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 transition disabled:opacity-50 disabled:cursor-not-allowed"
				>
					{deleting ? 'Deleting...' : 'Delete'}
				</button>
				<a
					href="/agent/{agentId}/"
					class="px-4 py-2 bg-gray-200 text-gray-700 rounded hover:bg-gray-300 transition"
				>
					Cancel
				</a>
			</div>
		</div>
	{/if}
</div>
