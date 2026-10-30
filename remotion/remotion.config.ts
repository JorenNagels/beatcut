// `npm run studio`: same imports as render.mjs. To see a film's own graphics in the studio, set
// BEATCUT_EVENT_ENTRY to its generated list (<work>/render/gfx/event_graphics.ts, written by every render).
import {Config} from '@remotion/cli/config';
// @ts-ignore  plain JS helper shared with render.mjs
import {withBeatcut} from './webpack.mjs';

Config.overrideWebpackConfig((c) => withBeatcut(c, process.env.BEATCUT_EVENT_ENTRY));
