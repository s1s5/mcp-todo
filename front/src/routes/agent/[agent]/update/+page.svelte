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
	let name = $state('');
	let systemMessage = $state('');
	let command = $state('');
	let loading = $state(true);
	let submitting = $state(false);
	let error = $state('');

	// URLパラメータからagent IDを取得
	const agentId = $derived($page.params.agent);

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

	async function fetchAgentDetail() {
		loading = true;
		error = '';
		try {
			const res = await fetch(`/api/agents/${agentId}/`);
			if (!res.ok) throw new Error('Failed to fetch agent');
			agent = await res.json();
			// フォームの初期値を設定
			name = agent!.name;
			systemMessage = agent!.system_message;
			command = agent!.command || '';
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
			const res = await fetch(`/api/agents/${agentId}/`, {
				method: 'PUT',
				headers: {
					'Content-Type': 'application/json',
					'X-CSRFToken': getCSRFToken()
				},
				body: JSON.stringify({
					name,
					system_message: systemMessage,
					command
				})
			});

			if (!res.ok) {
				const data = await res.json();
				throw new Error(data.detail || 'Failed to update agent');
			}

			await goto(`/agent/${agentId}/`);
		} catch (e) {
			error = e instanceof Error ? e.message : 'Unknown error';
		} finally {
			submitting = false;
		}
	}

	onMount(() => {
		fetchAgentDetail();
	});
</script>

<div class="p-6 max-w-2xl mx-auto">
	<div class="flex items-center gap-4 mb-6">
		<a
			href="/agent/{agentId}/"
			class="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded transition"
		>
			<svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
			</svg>
		</a>
		<h1 class="text-2xl font-bold">Update Agent</h1>
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
					placeholder="Enter agent name"
				/>
			</div>

			<div>
				<label for="systemMessage" class="block text-sm font-medium text-gray-700 mb-1">
					System Message <span class="text-red-500">*</span>
				</label>
				<textarea
					id="systemMessage"
					bind:value={systemMessage}
					required
					rows="6"
					class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-y"
					placeholder="Enter system message"
				></textarea>
			</div>

			<div>
				<label for="command" class="block text-sm font-medium text-gray-700 mb-1">
					Command
				</label>
				<input
					type="text"
					id="command"
					bind:value={command}
					class="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
					placeholder="goose run --recipe"
				/>
				<p class="mt-1 text-sm text-gray-500">Optional. Default: goose run --recipe</p>
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
					href="/agent/{agentId}/"
					class="px-4 py-2 border border-gray-300 text-gray-700 rounded-md hover:bg-gray-50 transition"
				>
					Cancel
				</a>
			</div>
		</form>
	{/if}
</div>
