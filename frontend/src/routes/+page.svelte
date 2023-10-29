<script lang="ts">
	import { browser } from '$app/environment';
	import { onMount } from 'svelte';

	let files: FileList | null = null;
	let fileInput: HTMLInputElement | null = null;
	let fileDownloadUrl: string | null = null;

	onMount(() => {
		// document is not available in SSR
		// TODO: figure out how to solve this more cleanly
		if (browser) fileInput = document.getElementById('file-input') as HTMLInputElement | null;
	});

	const statusMessages = {
		nodata: 'Upload 2 or more audio files',
		data: 'Click below to upload your files',
		uploading: 'Processing your files...',
		pending: 'Success! Download the zip file below.',
		error: 'Upload failed'
	};

	function getStatusMessage(status: keyof typeof statusMessages) {
		return statusMessages[status];
	}

	let status: keyof typeof statusMessages = 'nodata';

	function handleFileChange(event: Event) {
		const newFiles = (event.target as HTMLInputElement).files;
		if (!newFiles || newFiles.length < 2) {
			alert('Please upload at least 2 files');
			status = 'nodata';
			files = null;
			if (fileInput) {
				fileInput.value = '';
			}
			return;
		}
		files = newFiles;
		status = 'data';
	}

	async function handleUpload(event: Event) {
		event.preventDefault();
		const formData = new FormData();

		if (!files || files.length < 2) {
			status = 'nodata';
			return;
		}

		for (const file of files) {
			formData.append('files', file);
		}

		console.log('uploading the following files:', formData.getAll('files'));

		try {
			status = 'uploading';
			const response = await fetch('http://localhost:5000/practice_tracks', {
				method: 'POST',
				body: formData
			});
			try {
				const blob = await response.blob();
				const url = window.URL.createObjectURL(blob);
				fileDownloadUrl = url;
			} catch (error) {
				console.error(error);
				status = 'error';
			}

			if (response.ok) {
				status = 'pending';
			} else {
				status = 'error';
			}
		} catch (error) {
			status = 'error';
		}
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
				<form method="POST" on:submit={handleUpload}>
					<input
						type="file"
						class="file-input file-input-bordered w-full max-w-xs"
						multiple
						accept="audio/mpeg"
						id="file-input"
						on:change={handleFileChange}
					/>
					{#if status}
						<p class="text-xs mt-1">{getStatusMessage(status)}</p>
					{/if}
					<div class="flex justify-center mt-4 w-full">
						{#if status !== 'pending'}
							<button class="btn btn-primary" disabled={!files || status === 'uploading'}
								>{status === 'uploading' ? 'Please wait...' : 'Upload'}</button
							>
						{:else}
							<a
								class="btn btn-primary"
								download="practice_tracks.zip"
								href={fileDownloadUrl}
								on:click={() => {
									status = 'nodata';
									files = null;
								}}>Download</a
							>
						{/if}
					</div>
				</form>
			</div>
		</div>
	</div>
</div>
