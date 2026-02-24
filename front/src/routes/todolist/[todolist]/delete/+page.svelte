<script lang="ts">
	import { onMount } from 'svelte';
	import { page } from '$app/stores';
	import { goto } from '$app/navigation';

	interface TodoList {
		id: number;
		workdir: string;
		created_at: string;
		updated_at: string;
	}

	let todolist: TodoList | null = $state(null);
	let loading = $state(true);
	let deleting = $state(false);
	let error = $state('');

	const todolistId = $derived($page.params.todolist);

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

	async function fetchTodoList() {
		loading = true;
		error = '';
		try {
			const res = await fetch(`/api/todolists/${todolistId}/`);
			if (!res.ok) throw new Error('Failed to fetch todolist');
			todolist = await res.json();
		} catch (e) {
			error = e instanceof Error ? e.message : 'Unknown error';
		} finally {
			loading = false;
		}
	}

	async function handleDelete() {
		deleting = true;
		error = '';
		try {
			const csrfToken = getCSRFToken();
			const res = await fetch(`/api/todolists/${todolistId}/`, {
				method: 'DELETE',
				headers: {
					'X-CSRFToken': csrfToken
				}
			});
			if (!res.ok) {
				const data = await res.json();
				throw new Error(data.detail || 'Failed to delete');
			}
			goto('/todolist/');
		} catch (e) {
			error = e instanceof Error ? e.message : 'Unknown error';
		} finally {
			deleting = false;
		}
	}

	onMount(() => {
		fetchTodoList();
	});
</script>

<div class="p-6 max-w-2xl mx-auto">
	<div class="flex items-center gap-4 mb-6">
		<a
			href="/todolist/{todolistId}"
			class="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded transition"
		>
			<svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 19l-7-7 7-7" />
			</svg>
		</a>
		<h1 class="text-2xl font-bold">Delete TodoList</h1>
	</div>

	{#if loading}
		<p class="text-gray-500">Loading...</p>
	{:else if error && !todolist}
		<p class="text-red-500">{error}</p>
	{:else if todolist}
		<!-- 警告メッセージ -->
		<div class="bg-red-50 border-l-4 border-red-500 p-4 mb-6">
			<div class="flex">
				<div class="flex-shrink-0">
					<svg class="h-5 w-5 text-red-400" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
						<path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
					</svg>
				</div>
				<div class="ml-3">
					<p class="text-sm text-red-700">
						このTodoListを削除しますか？関連する全てのTodoも削除されます。
					</p>
				</div>
			</div>
		</div>

		<!-- 削除するTodoListの情報 -->
		<div class="bg-white shadow rounded-lg overflow-hidden mb-6">
			<div class="px-6 py-4 border-b border-gray-200 bg-gray-50">
				<h2 class="text-lg font-semibold text-gray-900">削除するTodoList</h2>
			</div>
			<div class="p-6">
				<dl class="grid grid-cols-1 gap-x-4 gap-y-6">
					<div>
						<dt class="text-sm font-medium text-gray-500">ID</dt>
						<dd class="mt-1 text-sm text-gray-900">{todolist.id}</dd>
					</div>
					<div>
						<dt class="text-sm font-medium text-gray-500">Workdir</dt>
						<dd class="mt-1 text-sm text-gray-900 font-mono">{todolist.workdir}</dd>
					</div>
					<div>
						<dt class="text-sm font-medium text-gray-500">作成日</dt>
						<dd class="mt-1 text-sm text-gray-900">{new Date(todolist.created_at).toLocaleString()}</dd>
					</div>
				</dl>
			</div>
		</div>

		<!-- エラーメッセージ -->
		{#if error}
			<div class="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded mb-6">
				{error}
			</div>
		{/if}

		<!-- アクションボタン -->
		<div class="flex justify-end gap-4">
			<a
				href="/todolist/{todolistId}"
				class="px-4 py-2 bg-gray-200 text-gray-700 rounded hover:bg-gray-300 transition"
			>
				キャンセル
			</a>
			<button
				onclick={handleDelete}
				disabled={deleting}
				class="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 transition disabled:opacity-50 disabled:cursor-not-allowed"
			>
				{deleting ? '削除中...' : '削除'}
			</button>
		</div>
	{/if}
</div>
