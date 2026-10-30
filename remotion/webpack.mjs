// Lets a film's own graphics (<event>/graphics/*.tsx, outside this folder) join the bundle: `import ... from
// 'beatcut'` is src/lib.ts, react/remotion resolve from this node_modules, and 'beatcut-event' is the generated
// list of the film's components (src/no-event.ts when there is none).
import path from 'node:path';
import {fileURLToPath} from 'node:url';

const here = path.dirname(fileURLToPath(import.meta.url));

export const withBeatcut = (c, eventEntry) => ({
	...c,
	resolve: {
		...c.resolve,
		alias: {...(c.resolve?.alias || {}), beatcut: path.join(here, 'src', 'lib.ts'),
			'beatcut-event': eventEntry || path.join(here, 'src', 'no-event.ts')},
		modules: [...(c.resolve?.modules || ['node_modules']), path.join(here, 'node_modules')],
	},
});
