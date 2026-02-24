<script lang="ts">
	import { onMount } from 'svelte';
	import { marked } from 'marked';
	import { page } from '$app/stores';

	interface Todo {
		id: number;
		todo_list: number;
		todo_list_name: string | null;
		agent: number | null;
		agent_name: string | null;
		ref_files: string[];
		edit_files: string[];
		prompt: string;
		context: string;
		status: string;
		output: string | null;
		error: string | null;
		validation_command: string | null;
		timeout: number;
		created_at: string;
		updated_at: string;
		branch_name: string | null;
	}

	let todo: Todo | null = $state(null);
	let loading = $state(true);
	let error = $state('');
	let processingId = $state<number | null>(null);

	// CSRFトークンを取得する関数
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

	async function fetchTodo() {
		loading = true;
		error = '';
		try {
			const todoId = $page.params.todo;
			const res = await fetch(`/api/todos/${todoId}/`);
			if (!res.ok) throw new Error('Failed to fetch');
			todo = await res.json();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Unknown error';
		} finally {
			loading = false;
		}
	}

	async function startTodo(id: number) {
		processingId = id;
		try {
			const csrfToken = getCSRFToken();
			const res = await fetch(`/api/todos/${id}/start/`, {
				method: 'POST',
				headers: {
					'X-CSRFToken': csrfToken
				},
				credentials: 'same-origin'
			});
			if (!res.ok) throw new Error('Failed to start');
			await fetchTodo();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to start todo';
		} finally {
			processingId = null;
		}
	}

	async function cancelTodo(id: number) {
		processingId = id;
		try {
			const csrfToken = getCSRFToken();
			const res = await fetch(`/api/todos/${id}/cancel/`, {
				method: 'POST',
				headers: {
					'X-CSRFToken': csrfToken
				},
				credentials: 'same-origin'
			});
			if (!res.ok) throw new Error('Failed to cancel');
			await fetchTodo();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to cancel todo';
		} finally {
			processingId = null;
		}
	}

	function getStatusColor(status: string): string {
		switch (status) {
			case 'waiting': return 'bg-gray-100 text-gray-800';
			case 'queued': return 'bg-blue-100 text-blue-800';
			case 'running': return 'bg-yellow-100 text-yellow-800';
			case 'completed': return 'bg-green-100 text-green-800';
			case 'error': return 'bg-red-100 text-red-800';
			case 'cancelled': return 'bg-gray-100 text-gray-600';
			case 'timeout': return 'bg-orange-100 text-orange-800';
			default: return 'bg-gray-100 text-gray-800';
		}
	}

	function formatDate(dateStr: string): string {
		const date = new Date(dateStr);
		return date.toLocaleString('ja-JP', {
			year: 'numeric',
			month: '2-digit',
			day: '2-digit',
			hour: '2-digit',
			minute: '2-digit',
			second: '2-digit'
		});
	}

	onMount(() => {
		fetchTodo();
	});
</script>

<div class="p-6 max-w-4xl mx-auto">
	<div class="flex items-center gap-4 mb-6">
		<a
			href="/todo"
			class="px-4 py-2 bg-gray-200 text-gray-700 rounded hover:bg-gray-300 transition"
		>
			← 戻る
		</a>
		<h1 class="text-2xl font-bold">Todo詳細</h1>
		<div class="flex items-center gap-2 ml-auto">
			{#if todo}
				<a
					href="/todo/{todo.id}/update/"
					class="px-3 py-1 bg-blue-600 text-white rounded text-sm hover:bg-blue-700 transition"
				>
					編集
				</a>
				<a
					href="/todo/{todo.id}/delete/"
					class="px-3 py-1 bg-red-600 text-white rounded text-sm hover:bg-red-700 transition"
				>
					削除
				</a>
			{/if}
		</div>
	</div>

	{#if error}
		<p class="text-red-500 mb-4">{error}</p>
	{/if}

	{#if loading}
		<p class="text-gray-500">Loading...</p>
	{:else if todo}
		<div class="bg-white shadow rounded-lg overflow-hidden">
			<div class="px-6 py-4 border-b border-gray-200">
				<div class="flex items-center justify-between">
					<span class="text-lg font-semibold text-gray-900">ID: {todo.id}</span>
					<div class="flex items-center gap-2">
						{#if todo.status === 'waiting' || todo.status === 'error'}
							<button
								onclick={() => startTodo(todo.id)}
								disabled={processingId === todo.id}
								class="px-3 py-1 bg-green-600 text-white rounded text-sm hover:bg-green-700 transition disabled:opacity-50 cursor-pointer"
							>
								{processingId === todo.id ? 'Starting...' : (todo.status === 'error' ? 'Retry' : 'Start')}
							</button>
						{/if}
						{#if todo.status === 'waiting' || todo.status === 'queued' || todo.status === 'running'}
							<button
								onclick={() => cancelTodo(todo.id)}
								disabled={processingId === todo.id}
								class="px-3 py-1 bg-red-600 text-white rounded text-sm hover:bg-red-700 transition disabled:opacity-50 cursor-pointer"
							>
								{processingId === todo.id ? 'Cancelling...' : 'Cancel'}
							</button>
						{/if}
						<span class="px-3 py-1 text-sm font-medium rounded-full {getStatusColor(todo.status)}">
							{todo.status}
						</span>
					</div>
				</div>
			</div>
			<div class="px-6 py-4 space-y-4">
				<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
					<div>
						<label class="block text-sm font-medium text-gray-500 mb-1">TodoList</label>
						<p class="text-gray-900">{todo.todo_list_name || `ID: ${todo.todo_list}`}</p>
					</div>
					<div>
						<label class="block text-sm font-medium text-gray-500 mb-1">Agent</label>
						<p class="text-gray-900">{todo.agent_name || (todo.agent ? `ID: ${todo.agent}` : '-')}</p>
					</div>
					<div>
						<label class="block text-sm font-medium text-gray-500 mb-1">Branch</label>
						<p class="text-gray-900 font-mono">{todo.branch_name || '-'}</p>
					</div>
					<div>
						<label class="block text-sm font-medium text-gray-500 mb-1">Timeout</label>
						<p class="text-gray-900">{todo.timeout} 秒</p>
					</div>
				</div>

				<div>
					<label class="block text-sm font-medium text-gray-500 mb-1">Prompt</label>
					<div class="p-3 bg-gray-50 rounded text-gray-900 prose prose-sm max-w-none">
						{#if todo.prompt}
							{@html marked(todo.prompt)}
						{:else}
							-
						{/if}
					</div>
				</div>

				{#if todo.context}
					<div>
						<label class="block text-sm font-medium text-gray-500 mb-1">Context</label>
						<div class="p-3 bg-gray-50 rounded text-gray-900 whitespace-pre-wrap text-sm">
							{todo.context}
						</div>
					</div>
				{/if}

				{#if todo.error}
					<div>
						<label class="block text-sm font-medium text-red-600 mb-1">Error</label>
						<div class="p-3 bg-red-50 border border-red-200 rounded text-red-800 whitespace-pre-wrap">
							{todo.error}
						</div>
					</div>
				{/if}

				{#if todo.output}
					<div>
						<label class="block text-sm font-medium text-gray-500 mb-1">Output</label>
						<div class="p-3 bg-gray-50 rounded text-gray-900 whitespace-pre-wrap text-sm max-h-64 overflow-y-auto">
							{todo.output}
						</div>
					</div>
				{/if}

				{#if todo.ref_files && todo.ref_files.length > 0}
					<div>
						<label class="block text-sm font-medium text-gray-500 mb-1">参照ファイル</label>
						<ul class="list-disc list-inside text-gray-900">
							{#each todo.ref_files as file}
								<li class="font-mono text-sm">{file}</li>
							{/each}
						</ul>
					</div>
				{/if}

				{#if todo.edit_files && todo.edit_files.length > 0}
					<div>
						<label class="block text-sm font-medium text-gray-500 mb-1">編集ファイル</label>
						<ul class="list-disc list-inside text-gray-900">
							{#each todo.edit_files as file}
								<li class="font-mono text-sm">{file}</li>
							{/each}
						</ul>
					</div>
				{/if}

				<div class="grid grid-cols-1 md:grid-cols-2 gap-4 pt-4 border-t border-gray-200">
					<div>
						<label class="block text-sm font-medium text-gray-500 mb-1">作成日</label>
						<p class="text-gray-900">{formatDate(todo.created_at)}</p>
					</div>
					<div>
						<label class="block text-sm font-medium text-gray-500 mb-1">更新日</label>
						<p class="text-gray-900">{formatDate(todo.updated_at)}</p>
					</div>
				</div>
			</div>
		</div>
	{:else}
		<p class="text-gray-500">Todoが見つかりません。</p>
	{/if}
</div>
