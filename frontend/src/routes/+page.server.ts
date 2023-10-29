import type { Actions } from '@sveltejs/kit';
import { promises as fs, existsSync as exists } from 'fs';

export const actions: Actions = {
	upload: async ({ request }) => {
		const formData = await request.formData();
		const files = formData.getAll('files');

		try {
			const response = await fetch('http://localhost:5000/practice_tracks', {
				method: 'POST',
				body: formData
			});
			try {
				if (response.ok) {
					// write zip file to file system under temporary downloads folder
					const fileId = crypto.randomUUID();
					const filePath = `./downloads/${fileId}.zip`;
					const arrayBuffer = await response.arrayBuffer();
					if (!exists('./downloads')) {
						await fs.mkdir('./downloads');
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
