import type { Actions } from '@sveltejs/kit';
import { promises as fs, existsSync as exists, statSync } from 'fs';
import { tempDownloadFolder } from '$lib';
import env from '$lib/env.server';

setInterval(clearOldFiles, 1000 * 60); // cleanup every minute

export const actions: Actions = {
	upload: async ({ request }) => {
		const formData = await request.formData();
		// const files = formData.getAll('files');
		// console.log('files:', files);

		try {
			const response = await fetch(`${env.API_URL}/practice_tracks`, {
				method: 'POST',
				body: formData
			});
			try {
				if (response.ok) {
					// write zip file to file system under temporary downloads folder
					const fileId = crypto.randomUUID();
					console.log('creating temporary file in', tempDownloadFolder);

					const filePath = `${tempDownloadFolder}/${fileId}.zip`;
					const arrayBuffer = await response.arrayBuffer();
					if (!exists(tempDownloadFolder)) {
						await fs.mkdir(tempDownloadFolder);
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
				console.error('Error processing response from Python API');
				console.error(error);
				return {
					status: 'error'
				};
			}
		} catch (error) {
			console.error('Error communicating with Python API');
			console.error(error);
			return {
				status: 'error'
			};
		}
	}
};

async function clearOldFiles() {
	console.log('clearing old files in', tempDownloadFolder);
	if (!exists(tempDownloadFolder)) {
		return;
	}
	const files = await fs.readdir(tempDownloadFolder);
	const now = Date.now();
	const oneMinute = 1000 * 60;
	const oldFiles = files.filter((file) => {
		const stats = statSync(`${tempDownloadFolder}/${file}`);
		return now - stats.mtimeMs > oneMinute;
	});
	await Promise.all(oldFiles.map((file) => fs.unlink(`${tempDownloadFolder}/${file}`)));
}
