import type { Actions } from '@sveltejs/kit';
import { promises as fs, existsSync as exists, statSync } from 'fs';
import { TEMP_DOWNLOAD_DIR, AUDIOPROCESSING_API_URL } from '$env/static/private';

setInterval(clearOldFiles, 1000 * 60); // cleanup every minute

export const actions: Actions = {
	upload: async ({ request }) => {
		const formData = await request.formData();
		const files = formData.getAll('files');
		console.log('uploading', files.length, 'files to Audio Processing API');

		try {
			const response = await fetch(`${AUDIOPROCESSING_API_URL}/practice_tracks`, {
				method: 'POST',
				body: formData
			});
			try {
				if (response.ok) {
					// write zip file to file system under temporary downloads folder
					const fileId = crypto.randomUUID();
					console.log('creating temporary file in', TEMP_DOWNLOAD_DIR);

					const filePath = `${TEMP_DOWNLOAD_DIR}/${fileId}.zip`;
					const arrayBuffer = await response.arrayBuffer();
					if (!exists(TEMP_DOWNLOAD_DIR)) {
						await fs.mkdir(TEMP_DOWNLOAD_DIR);
					}
					await fs.writeFile(filePath, Buffer.from(arrayBuffer));
					return {
						status: 'success',
						fileId
					};
				}
				return {
					status: 'error'
				};
			} catch (error) {
				console.error('Error processing response from Audio Processing API');
				console.error(error);
				return {
					status: 'error'
				};
			}
		} catch (error) {
			console.error('Error communicating with Audio Processing API');
			console.error(error);
			return {
				status: 'error'
			};
		}
	}
};

async function clearOldFiles() {
	if (!exists(TEMP_DOWNLOAD_DIR)) {
		return;
	}
	const files = await fs.readdir(TEMP_DOWNLOAD_DIR);
	const now = Date.now();
	const oneMinute = 1000 * 60;
	const oldFiles = files.filter((file) => {
		const stats = statSync(`${TEMP_DOWNLOAD_DIR}/${file}`);
		return now - stats.mtimeMs > oneMinute;
	});
	await Promise.all(oldFiles.map((file) => fs.unlink(`${TEMP_DOWNLOAD_DIR}/${file}`)));
	console.log('removed', oldFiles.length, 'old files in temporary downloads folder');
}
