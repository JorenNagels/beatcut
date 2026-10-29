// Shared bits: frame size from props, the film font (render/fonts/title.ttf, served as a static file), easing.
import React, {useEffect, useState} from 'react';
import {cancelRender, continueRender, delayRender, staticFile} from 'remotion';

export type Size = {width: number; height: number; fps: number; frames: number};

// text scale: the height of a 16:9 frame this wide (same rule as 14_render / 16_title)
export const unit = (w: number, h: number) => Math.min(h, (w * 9) / 16);
export const clamp01 = (x: number) => Math.min(1, Math.max(0, x));
export const easeOut = (x: number) => 1 - Math.pow(1 - clamp01(x), 3);

export const FILM_FONT = 'FilmFont';

// loads the film's font once per page; rendering waits until it is ready
export const useFilmFont = () => {
	const [handle] = useState(() => delayRender('film font'));
	useEffect(() => {
		const f = new FontFace(FILM_FONT, `url(${staticFile('title.ttf')})`, {weight: '100 900'});
		f.load()
			.then(() => {
				document.fonts.add(f);
				continueRender(handle);
			})
			.catch((e) => cancelRender(e));
	}, [handle]);
};

export const Full: React.FC<{children?: React.ReactNode; style?: React.CSSProperties}> = ({children, style}) => (
	<div style={{position: 'absolute', inset: 0, overflow: 'hidden', ...style}}>{children}</div>
);
