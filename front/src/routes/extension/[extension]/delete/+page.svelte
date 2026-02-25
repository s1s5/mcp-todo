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
	let loading = $state(true);
	let error = $state('');
	let deleteError = $state('');
	let deleting = $state(false);

	const extensionId = $page.params.extension;

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

	async function fetchExtension() {
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

	async function handleDelete() {
		if (!extension) return;
		deleting = true;
		deleteError = '';
		try {
			const res = await fetch(`/api/extensions/${extension.id}/`, {
				method: 'DELETE',
				headers: {
					'X-CSRFToken': getCSRFToken()
				}
			});
			if (!res.ok) {
				const data = await res.json().catch(() => ({}));
				throw new Error(data.detail || 'Failed to delete extension');
			}
			goto('/extension/');
		} catch (e) {
			deleteError = e instanceof Error ? e.message : 'Unknown error';
		} finally {
			deleting = false;
		}
	}

	onMount(() => {
		fetchExtension();
	});
</script>

<div class="p-6 max-w-2xl mx-auto">
	<div class="mb-6">
		<a
			href="/extension/{extensionId}/"
			class="text-blue-600 hover:text-blue-800 inline-flex items-center"
			id="back-link"
		>
			← Back to Detail
		</a>
	</div>

	<h1 class="text-2xl font-bold mb-6">Delete Extension</h1>

	{#if loading}
		<p class="text-gray-500" id="loading-indicator">Loading...</p>
	{:else if error}
		<p class="text-red-500" id="error-message">{error}</p>
	{:else if extension}
		<div class="bg-white shadow rounded-lg p-6">
			<div class="mb-6" id="warning-message">
				<h2 class="text-lg font-semibold text-red-600 mb-2">⚠️ このExtensionを削除しますか？</h2>
				<p class="text-gray-600" id="warning-text">この操作は取り消せません。</p>
			</div>

			<div class="bg-gray-50 rounded-lg p-4 mb-6">
				<dl class="space-y-3">
					<div>
						<dt class="text-sm font-medium text-gray-500">ID</dt>
						<dd class="text-sm text-gray-900">{extension.id}</dd>
					</div>
					<div>
						<dt class="text-sm font-medium text-gray-500">Name</dt>
						<dd class="text-sm text-gray-900 font-medium">{extension.name}</dd>
					</div>
					<div>
						<dt class="text-sm font-medium text-gray-500">Type</dt>
						<dd class="text-sm text-gray-900">{extension.type}</dd>
					</div>
					<div>
						<dt class="text-sm font-medium text-gray-500">Command</dt>
						<dd class="text-sm text-gray-900 font-mono">{extension.cmd || '-'}</dd>
					</div>
					<div>
						<dt class="text-sm font-medium text-gray-500">Args</dt>
						<dd class="text-sm text-gray-900 font-mono">
							{extension.args && extension.args.length > 0 ? JSON.stringify(extension.args) : '-'}
						</dd>
					</div>
					<div>
						<dt class="text-sm font-medium text-gray-500">Envs</dt>
						<dd class="text-sm text-gray-900 font-mono whitespace-pre-wrap">
							{extension.envs && Object.keys(extension.envs).length > 0 ? JSON.stringify(extension.envs) : '-'}
						</dd>
					</div>
					<div>
						<dt class="text-sm font-medium text-gray-500">Timeout</dt>
						<dd class="text-sm text-gray-900">{extension.timeout}s</dd>
					</div>
					<div>
						<dt class="text-sm font-medium text-gray-500">Created</dt>
						<dd class="text-sm text-gray-900">{new Date(extension.created_at).toLocaleString()}</dd>
					</div>
				</dl>
			</div>

			{#if deleteError}
				<div class="mb-4 p-3 bg-red-50 border border-red-200 rounded text-red-600 text-sm" id="delete-error">
					{deleteError}
				</div>
			{/if}

			<div class="flex gap-4">
				<button
					onclick={handleDelete}
					disabled={deleting}
					class="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 transition disabled:opacity-50 disabled:cursor-not-allowed"
					id="delete-button"
				>
					{deleting ? 'Deleting...' : 'Delete'}
				</button>
				<a
					href="/extension/{extensionId}/"
					class="px-4 py-2 bg-gray-200 text-gray-700 rounded hover:bg-gray-300 transition"
					id="cancel-button"
				>
					Cancel
				</a>
			</div>
		</div>
	{/if}
</div>
