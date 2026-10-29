// Render overlay jobs for 14_render:  node render.mjs <jobs.json>
// jobs.json: {"publicDir": "<folder with title.ttf>", "concurrency": 4,
//             "jobs": [{"composition": "Title", "props": {...}, "out": "<file>.mov"}, ...]}
// The project is bundled once, then every job renders to ProRes 4444 with alpha (transparent overlay).
import fs from 'node:fs';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {bundle} from '@remotion/bundler';
import {ensureBrowser, renderMedia, selectComposition} from '@remotion/renderer';

const here = path.dirname(fileURLToPath(import.meta.url));
const spec = JSON.parse(fs.readFileSync(process.argv[2], 'utf-8'));
await ensureBrowser();                                       // first run downloads Chrome Headless Shell (~100 MB)
const serveUrl = await bundle({entryPoint: path.join(here, 'src', 'index.ts'), publicDir: spec.publicDir});
for (const [k, job] of spec.jobs.entries()) {
	const t0 = Date.now();
	const composition = await selectComposition({serveUrl, id: job.composition, inputProps: job.props});
	await renderMedia({
		composition, serveUrl, inputProps: job.props, outputLocation: job.out,
		codec: 'prores', proResProfile: '4444', pixelFormat: 'yuva444p10le', imageFormat: 'png',
		concurrency: spec.concurrency || null, logLevel: 'error',
	});
	console.log(`[${k + 1}/${spec.jobs.length}] ${job.composition} ${composition.durationInFrames} frames (${((Date.now() - t0) / 1000).toFixed(0)}s)`);
}
