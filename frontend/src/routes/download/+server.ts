import type { RequestHandler } from '@sveltejs/kit';
import { promises as fs, existsSync as exists } from 'fs';

export const GET: RequestHandler = async ({ url }) => {
	const id = url.searchParams.get('id');
	console.log('download request for file with id:', id);
	const filePath = `./downloads/${id}.zip`;
	if (!exists(filePath)) {
		return new Response('File not found', {
			status: 404
		});
	}
	const file = await fs.readFile(filePath);

	return new Response(file, {
		status: 200,
		headers: {
			'Content-Disposition': `attachment; filename=practice_tracks.zip`,
			'Content-Type': 'application/zip'
		}
	});
};
