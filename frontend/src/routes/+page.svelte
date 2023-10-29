<script lang="ts">
	import { browser } from '$app/environment';
	import { onMount } from 'svelte';
	import type { ActionData } from './$types';

	let files: FileList | null = null;
	let fileInput: HTMLInputElement | null = null;
	export let form: ActionData;

	const statusMessages = {
		nodata: 'Upload 2 or more audio files',
		data: 'Click below to upload your files',
		uploading: 'Processing your files...',
		pending: 'Success! Download the zip file below.',
		error: 'Upload failed'
	};
	let status: keyof typeof statusMessages = 'nodata';

	$: fileDownloadUrl = form?.status === 'success' ? `/download/?id=${form.fileId}` : null;

	$: if (form?.status === 'success') {
		status = 'pending';
	}

	$: if (form?.status === 'error') {
		status = 'error';
	}

	$: if (!files || files.length < 2) {
		status = 'nodata';
	} else {
		status = 'data';
	}

	$: if (fileDownloadUrl) {
		status = 'pending';
	}

	onMount(() => {
		// document is not available in SSR
		// TODO: figure out how to solve this more cleanly
		if (browser) fileInput = document.getElementById('file-input') as HTMLInputElement | null;
	});

	function getStatusMessage(status: keyof typeof statusMessages) {
		return statusMessages[status];
	}

	function handleFileChange(event: Event) {
		const newFiles = (event.target as HTMLInputElement).files;
		if (newFiles && newFiles.length === 1) {
			// length 0 is allowed as it means that the user probably deliberately removed all files (or cancelled the file picker)
			alert('Please upload at least 2 files');
			status = 'nodata';
			if (fileInput) {
				fileInput.value = '';
				files = null;
			}
			return;
		}
		files = newFiles;
	}
</script>

<svelte:head>
	<title>Practice Track Creator</title>
</svelte:head>

<div class="my-auto mx-auto">
	<div class="flex flex-col items-center">
		<h1 class="mb-8">🎵 Practice Track Creator 🎶</h1>
		<div class="card w-96 bg-base-100 shadow-xl">
			<div class="card-body items-center">
				<h2 class="card-title">Create combined audio tracks from single track files</h2>
				<p class="text-sm">
					A zip file with several variants of mixes of all tracks will be created. This includes
				</p>
				<ol class="text-sm list-decimal list-inside">
					<li>a regular mix of all tracks and</li>
					<li>
						'highlight' mixes for every individual track where that track is louder compared to the
						rest
					</li>
				</ol>
				<form
					method="POST"
					on:submit={() => (status = 'uploading')}
					enctype="multipart/form-data"
					action="?/upload"
				>
					<input
						type="file"
						class="file-input file-input-bordered w-full max-w-xs"
						multiple
						accept="audio/mpeg"
						id="file-input"
						name="files"
						bind:files
						on:change={handleFileChange}
					/>
					{#if status}
						<p class="text-xs mt-1">{getStatusMessage(status)}</p>
					{/if}
					<div class="flex justify-center mt-4 w-full">
						{#if status !== 'pending'}
							<button
								class="btn btn-primary"
								disabled={status === 'uploading' || status === 'nodata'}
								>{status === 'uploading' ? 'Please wait...' : 'Upload'}</button
							>
						{:else}
							<a class="btn btn-primary" download="practice_tracks.zip" href={fileDownloadUrl}
								>Download</a
							>
						{/if}
					</div>
				</form>
			</div>
		</div>
	</div>
</div>
