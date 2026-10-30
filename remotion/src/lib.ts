// What a film's own graphics (<event>/graphics/*.tsx) import:  import {GfxProps, unit, pulse, ...} from 'beatcut';
// Every graphic gets width/height/fps/frames, `beats` and `bars` (music beat / bar times in seconds from the
// graphic's first frame, can be negative), `accent` (style.accent) and whatever the plan passes (text, ...).
import {spring} from 'remotion';
import {Size} from './common';

export {FILM_FONT, Full, clamp01, easeOut, unit, useFilmFont} from './common';
export type {Size} from './common';

export type GfxProps = Size & {beats: number[]; bars: number[]; accent: string; text?: string};

export const easeIn = (x: number) => Math.pow(Math.min(1, Math.max(0, x)), 3);
export const easeInOut = (x: number) => {
	const t = Math.min(1, Math.max(0, x));
	return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
};

// index of the last beat at or before t (seconds), -1 before the first
export const beatAt = (t: number, beats: number[]) => {
	let i = -1;
	for (let k = 0; k < beats.length && beats[k] <= t + 1e-6; k++) i = k;
	return i;
};

// 1 on every beat, decaying to 0 (decay = seconds to ~37 %): scale / glow / shake by it
export const pulse = (t: number, beats: number[], decay = 0.15) => {
	const i = beatAt(t, beats);
	return i < 0 ? 0 : Math.exp(-(t - beats[i]) / decay);
};

// a springy 0 -> 1 (overshoots a little) that starts at `delay` seconds
export const pop = (frame: number, fps: number, delay = 0, stiffness = 220, damping = 11) =>
	spring({frame: frame - Math.round(delay * fps), fps, config: {stiffness, damping}});

// 0 while the graphic is on, -> 1 over the last `dur` seconds: use for the exit
export const exit = (frame: number, {frames, fps}: Size, dur = 0.25) =>
	Math.min(1, Math.max(0, (frame - (frames - dur * fps)) / (dur * fps)));
