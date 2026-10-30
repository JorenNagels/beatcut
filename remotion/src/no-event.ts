// Stand-in for a film's own graphics when it has none (render.mjs points the 'beatcut-event' import at a
// generated file listing <event>/graphics/*.tsx instead).
import React from 'react';

export const EVENT: Record<string, React.FC<any>> = {};
