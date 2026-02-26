<script lang="ts">
	import { onMount, onDestroy } from 'svelte';
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
		title: string | null;
		auto_stash: boolean;
		keep_branch: boolean;
		context: string;
		status: string;
		output: string | null;
		error: string | null;
		validation_command: string | null;
		timeout: number;
		priority: number;
		created_at: string;
		updated_at: string;
		branch_name: string | null;
		started_at: string | null;
		finished_at: string | null;
	}

	let todo: Todo | null = $state(null);
	let loading = $state(true);
	let error = $state('');
	let pollInterval: ReturnType<typeof setInterval> | null = null;
	let processingId = $state<number | null>(null);
	let updatingPriority = $state(false);

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

	async function fetchTodoSilent() {
		if (loading) return;
		try {
			const todoId = $page.params.todo;
			const res = await fetch(`/api/todos/${todoId}/`);
			if (!res.ok) return;
			const data: Todo = await res.json();
			todo = data;
		} catch (e) {
			// Silent fail
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
		// 楽観的UI更新: ローカルstateを即座に更新
		if (todo && todo.id === id) {
			todo.status = todo.status === 'queued' ? 'waiting' : 'cancelled';
		}
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
			// 失敗時は再取得して元に戻す
			await fetchTodo();
			error = e instanceof Error ? e.message : 'Failed to cancel todo';
		} finally {
			processingId = null;
		}
	}

	async function updatePriority(priority: number) {
		if (!todo) return;
		updatingPriority = true;
		try {
			const csrfToken = getCSRFToken();
			const res = await fetch(`/api/todos/${todo.id}/`, {
				method: 'PATCH',
				headers: {
					'Content-Type': 'application/json',
					'X-CSRFToken': csrfToken
				},
				credentials: 'same-origin',
				body: JSON.stringify({ priority })
			});
			if (!res.ok) throw new Error('Failed to update priority');
			await fetchTodo();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Failed to update priority';
		} finally {
			updatingPriority = false;
		}
	}

	function getStatusColor(status: string): string {
		switch (status) {
			case 'waiting': return 'bg-cyan-100 text-cyan-800';
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

	function formatDuration(startedAt: string | null, finishedAt: string | null): string | null {
		if (!startedAt || !finishedAt) return null;
		const start = new Date(startedAt);
		const end = new Date(finishedAt);
		const diffMs = end.getTime() - start.getTime();
		if (diffMs < 0) return null;
		const totalSeconds = Math.floor(diffMs / 1000);
		const minutes = Math.floor(totalSeconds / 60);
		const seconds = totalSeconds % 60;
		return `${minutes}分${seconds}秒`;
	}

	const terminalStatuses = ['completed', 'error', 'cancelled', 'timeout'];

	function getProcessingTime(todo: Todo): string | null {
		if (!terminalStatuses.includes(todo.status)) return null;
		return formatDuration(todo.started_at, todo.finished_at);
	}

	function getPriorityColor(priority: number): string {
		if (priority <= -5) {
			// 低緊急性 - 薄い青色
			return 'bg-blue-100 text-blue-800';
		} else if (priority > 5) {
			// 高緊急性 - 赤色
			return 'bg-red-100 text-red-800';
		} else {
			// 通常 - 灰色
			return 'bg-gray-100 text-gray-800';
		}
	}

	onMount(() => {
		fetchTodo();
		// statusがrunningのときは5秒ごとにポーリング
		pollInterval = setInterval(() => {
			if (todo?.status === 'running' || todo?.status === 'queued') {
				fetchTodoSilent();
			}
		}, 5000);
	});

	onDestroy(() => {
		if (pollInterval) {
			clearInterval(pollInterval);
		}
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
					<div class="flex items-center gap-2">
						<span class="text-lg font-semibold text-gray-900">ID: {todo.id}</span>
						{#if todo.title}
							<span class="text-lg font-semibold text-gray-700">{todo.title}</span>
						{/if}
					</div>
					<div class="flex items-center gap-2">
						{#if todo.status === 'waiting' || todo.status === 'error'}
							<button
								onclick={() => todo && startTodo(todo.id)}
								disabled={processingId === todo.id}
								class="px-3 py-1 bg-green-600 text-white rounded text-sm hover:bg-green-700 transition disabled:opacity-50 cursor-pointer"
							>
								{processingId === todo.id ? 'Starting...' : (todo.status === 'error' ? 'Retry' : 'Start')}
							</button>
						{/if}
						{#if todo.status === 'waiting' || todo.status === 'queued' || todo.status === 'running'}
							<button
								onclick={() => todo && cancelTodo(todo.id)}
								disabled={processingId === todo.id}
								class="px-3 py-1 bg-red-600 text-white rounded text-sm hover:bg-red-700 transition disabled:opacity-50 cursor-pointer"
							>
								{processingId === todo.id ? 'Cancelling...' : 'Cancel'}
							</button>
						{/if}
						<span class="px-3 py-1 text-sm font-medium rounded-full {getStatusColor(todo.status)}">
							{todo.status}
						</span>
						{#if getProcessingTime(todo)}
							<span class="text-sm text-gray-600">
								処理時間: {getProcessingTime(todo)}
							</span>
						{/if}
					</div>
				</div>
			</div>
			<div class="px-6 py-4 space-y-4">
				<div class="grid grid-cols-1 md:grid-cols-2 gap-4">
					<div>
						<label for="todo-list" class="block text-sm font-medium text-gray-500 mb-1">TodoList</label>
						<p id="todo-list" class="text-gray-900">{todo.todo_list_name || `ID: ${todo.todo_list}`}</p>
					</div>
					<div>
						<label for="agent" class="block text-sm font-medium text-gray-500 mb-1">Agent</label>
						<p id="agent" class="text-gray-900">{todo.agent_name || (todo.agent ? `ID: ${todo.agent}` : '-')}</p>
					</div>
					<div>
						<label for="branch" class="block text-sm font-medium text-gray-500 mb-1">Branch</label>
						<p id="branch" class="text-gray-900 font-mono">{todo.branch_name || '-'}</p>
					</div>
					<div>
						<label for="timeout" class="block text-sm font-medium text-gray-500 mb-1">Timeout</label>
						<p id="timeout" class="text-gray-900">{todo.timeout}秒</p>
					</div>
					<div>
						<label for="auto-stash" class="block text-sm font-medium text-gray-500 mb-1">自動スタッシュ</label>
						<p id="auto-stash" class="text-gray-900">{todo.auto_stash ? 'はい' : 'いいえ'}</p>
					</div>
					<div>
						<label for="keep-branch" class="block text-sm font-medium text-gray-500 mb-1">ブランチ保持</label>
						<p id="keep-branch" class="text-gray-900">{todo.keep_branch ? 'はい' : 'いいえ'}</p>
					</div>
					<div class="md:col-span-2">
						<label id="priority-label" class="block text-sm font-medium text-gray-500 mb-1">優先度</label>
						<div role="group" aria-labelledby="priority-label" class="flex items-center gap-2">
							<span class="px-3 py-1 text-sm font-medium rounded-full {getPriorityColor(todo.priority)}">
								{todo.priority}
							</span>
							{#if todo.status === 'waiting' || todo.status === 'queued'}
								<button
									onclick={() => updatePriority(-10)}
									disabled={updatingPriority || (todo.status !== 'waiting' && todo.status !== 'queued')}
									class="px-3 py-1 rounded text-sm font-medium transition cursor-pointer {todo.priority === -10 ? 'bg-gray-600 text-white' : 'bg-gray-200 text-gray-600 hover:bg-gray-300'} disabled:opacity-50 disabled:cursor-not-allowed"
								>
									Low
								</button>
								<button
									onclick={() => updatePriority(0)}
									disabled={updatingPriority || (todo.status !== 'waiting' && todo.status !== 'queued')}
									class="px-3 py-1 rounded text-sm font-medium transition cursor-pointer {todo.priority === 0 ? 'bg-blue-600 text-white' : 'bg-blue-100 text-blue-700 hover:bg-blue-200'} disabled:opacity-50 disabled:cursor-not-allowed"
								>
									Middle
								</button>
								<button
									onclick={() => updatePriority(10)}
									disabled={updatingPriority || (todo.status !== 'waiting' && todo.status !== 'queued')}
									class="px-3 py-1 rounded text-sm font-medium transition cursor-pointer {todo.priority === 10 ? 'bg-red-600 text-white' : 'bg-red-100 text-red-700 hover:bg-red-200'} disabled:opacity-50 disabled:cursor-not-allowed"
								>
									High
								</button>
							{/if}
						</div>
					</div>
				</div>

				<div>
					<label for="prompt" class="block text-sm font-medium text-gray-500 mb-1">Prompt</label>
					<div id="prompt" class="p-3 bg-gray-50 rounded text-gray-900 prose prose-sm max-w-none">
						{#if todo.prompt}
							{@html marked(todo.prompt)}
						{:else}
							-
						{/if}
					</div>
				</div>

				{#if todo.validation_command}
					<div>
						<label for="validation-command" class="block text-sm font-medium text-gray-500 mb-1">完了判断コマンド</label>
						<div id="validation-command" class="p-3 bg-gray-50 rounded text-gray-900 font-mono text-sm whitespace-pre-wrap">{todo.validation_command}</div>
					</div>
				{/if}

				{#if todo.context}
					<div>
						<label for="context" class="block text-sm font-medium text-gray-500 mb-1">Context</label>
						<div id="context" class="p-3 bg-gray-50 rounded text-gray-900 whitespace-pre-wrap text-sm">
							{todo.context}
						</div>
					</div>
				{/if}

				{#if todo.system_prompt}
					<div>
						<label for="system-prompt" class="block text-sm font-medium text-gray-500 mb-1">システムプロンプト</label>
						<div id="system-prompt" class="p-3 bg-gray-50 rounded text-gray-900 whitespace-pre-wrap text-sm">{todo.system_prompt}</div>
					</div>
				{/if}

				{#if todo.error}
					<div>
						<label for="error" class="block text-sm font-medium text-red-600 mb-1">Error</label>
						<div id="error" class="p-3 bg-red-50 border border-red-200 rounded text-red-800 whitespace-pre-wrap">
							{todo.error}
						</div>
					</div>
				{/if}

				{#if todo.output}
					<div>
						<label for="output" class="block text-sm font-medium text-gray-500 mb-1">Output</label>
						<div id="output" class="p-3 bg-gray-50 rounded text-gray-900 whitespace-pre-wrap text-sm max-h-64 overflow-y-auto">
							{todo.output}
						</div>
					</div>
				{/if}

				{#if todo.ref_files && todo.ref_files.length > 0}
					<div>
						<label id="ref-files-label" class="block text-sm font-medium text-gray-500 mb-1">参照ファイル</label>
						<ul role="list" aria-labelledby="ref-files-label" class="list-disc list-inside text-gray-900">
							{#each todo.ref_files as file}
								<li class="font-mono text-sm">{file}</li>
							{/each}
						</ul>
					</div>
				{/if}

				{#if todo.edit_files && todo.edit_files.length > 0}
					<div>
						<label id="edit-files-label" class="block text-sm font-medium text-gray-500 mb-1">編集ファイル</label>
						<ul role="list" aria-labelledby="edit-files-label" class="list-disc list-inside text-gray-900">
							{#each todo.edit_files as file}
								<li class="font-mono text-sm">{file}</li>
							{/each}
						</ul>
					</div>
				{/if}

				<div class="grid grid-cols-1 md:grid-cols-2 gap-4 pt-4 border-t border-gray-200">
					<div>
						<label for="created-at" class="block text-sm font-medium text-gray-500 mb-1">作成日</label>
						<p id="created-at" class="text-gray-900">{formatDate(todo.created_at)}</p>
					</div>
					<div>
						<label for="updated-at" class="block text-sm font-medium text-gray-500 mb-1">更新日</label>
						<p id="updated-at" class="text-gray-900">{formatDate(todo.updated_at)}</p>
					</div>
				</div>
			</div>
		</div>
	{:else}
		<p class="text-gray-500">Todoが見つかりません。</p>
	{/if}
</div>
