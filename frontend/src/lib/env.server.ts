import { createEnv } from '@t3-oss/env-core';
import { z } from 'zod';
import dotenv from 'dotenv';

dotenv.config();

const env = createEnv({
	server: {
		API_URL: z.string().url()
	},
	runtimeEnv: process.env
});

export default env;
