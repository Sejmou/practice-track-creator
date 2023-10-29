import type { RequestHandler } from '@sveltejs/kit';
import { promises as fs, existsSync as exists } from 'fs';
import { TEMP_DOWNLOAD_DIR } from '$env/static/private';

export const GET: RequestHandler = async ({ url }) => {
	const id = url.searchParams.get('id');
	console.log('download request for file with id:', id);
	const filePath = `${TEMP_DOWNLOAD_DIR}/${id}.zip`;
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
