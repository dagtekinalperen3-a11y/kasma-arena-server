/**
 * SVG simge seti (oyunun simge adlarıyla). Her boyutta keskin.
 */
const P: Record<string, string> = {
  sword: '<path d="M19 3l2 2-9.5 9.5-2-2z" fill="currentColor"/><path d="M8.5 12.5l3 3-2 2-1.5-1.5-3 3-1.5-1.5 3-3L5 13z" fill="currentColor" opacity=".85"/>',
  shield: '<path d="M12 2l8 3v6c0 5-3.4 9.3-8 11-4.6-1.7-8-6-8-11V5z" fill="currentColor"/><path d="M12 5v14c3-1.5 5-4.6 5-8V7z" fill="#fff" opacity=".25"/>',
  star: '<path d="M12 2l2.9 6.3 6.9.7-5.2 4.6 1.5 6.8L12 17l-6.1 3.4 1.5-6.8L2.2 9l6.9-.7z" fill="currentColor"/>',
  dash: '<path d="M3 7h9M2 12h12M4 17h8" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"/><path d="M14 5l7 7-7 7z" fill="currentColor"/>',
  drop: '<path d="M12 2s7 7.6 7 12.5A7 7 0 0 1 5 14.5C5 9.6 12 2 12 2z" fill="currentColor"/><ellipse cx="9.5" cy="14" rx="1.6" ry="2.6" fill="#fff" opacity=".45"/>',
  boot: '<path d="M7 2h6v10l6 3c1.6.8 2 2 2 3v2H4V12c0-1 .5-2 3-2z" fill="currentColor"/><path d="M4 18h17" stroke="#000" opacity=".3" stroke-width="2"/>',
  snow: '<path d="M12 2v20M3.3 7l17.4 10M3.3 17L20.7 7" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"/><path d="M9 4l3 2 3-2M9 20l3-2 3 2" stroke="currentColor" stroke-width="1.8" fill="none" stroke-linecap="round"/>',
  ghost: '<path d="M12 2a7 7 0 0 0-7 7v12l2.3-2 2.4 2 2.3-2 2.3 2 2.4-2 2.3 2V9a7 7 0 0 0-7-7z" fill="currentColor"/><circle cx="9.5" cy="10" r="1.6" fill="#141420"/><circle cx="14.5" cy="10" r="1.6" fill="#141420"/>',
  orbit: '<circle cx="12" cy="12" r="3.5" fill="currentColor"/><ellipse cx="12" cy="12" rx="10" ry="4.5" stroke="currentColor" stroke-width="2" fill="none" transform="rotate(-25 12 12)"/><circle cx="20" cy="8.5" r="2" fill="currentColor"/>',
  skull: '<path d="M12 2a8 8 0 0 0-8 8c0 3 1.6 5 3 6v3h10v-3c1.4-1 3-3 3-6a8 8 0 0 0-8-8z" fill="currentColor"/><circle cx="9" cy="11" r="2" fill="#141420"/><circle cx="15" cy="11" r="2" fill="#141420"/><path d="M10 19v3M14 19v3" stroke="currentColor" stroke-width="2"/>',
  bolt: '<path d="M13 2L4 14h7l-2 8 9-12h-7z" fill="currentColor"/>',
  flame: '<path d="M12 2c1 4 6 6 6 12a6 6 0 0 1-12 0c0-3 2-5 3-6 0 2 1 3 2 3 0-3-1-6 1-9z" fill="currentColor"/><path d="M12 13c1 2 3 3 3 5a3 3 0 0 1-6 0c0-1.5 1-2.5 3-5z" fill="#fff" opacity=".45"/>',
  target: '<circle cx="12" cy="12" r="9" stroke="currentColor" stroke-width="2.2" fill="none"/><circle cx="12" cy="12" r="5" stroke="currentColor" stroke-width="2.2" fill="none"/><circle cx="12" cy="12" r="1.8" fill="currentColor"/>',
  heart: '<path d="M12 21s-8-5.3-8-11.2A4.6 4.6 0 0 1 12 7a4.6 4.6 0 0 1 8 2.8C20 15.7 12 21 12 21z" fill="currentColor"/>',
  coin: '<circle cx="12" cy="12" r="9" fill="currentColor"/><circle cx="12" cy="12" r="6" stroke="#fff" stroke-opacity=".5" stroke-width="1.6" fill="none"/><path d="M12 8v8M10 10h3a1.5 1.5 0 0 1 0 3h-2a1.5 1.5 0 0 0 0 3h3" stroke="#000" stroke-opacity=".35" stroke-width="1.4" fill="none"/>',
  gem: '<path d="M6 3h12l4 6-10 12L2 9z" fill="currentColor"/><path d="M2 9h20M8 3l4 18 4-18" stroke="#fff" stroke-opacity=".4" stroke-width="1.2" fill="none"/>',
  clover: '<circle cx="8.5" cy="8.5" r="4" fill="currentColor"/><circle cx="15.5" cy="8.5" r="4" fill="currentColor"/><circle cx="12" cy="14.5" r="4" fill="currentColor"/><path d="M12 15v7" stroke="currentColor" stroke-width="2"/>',
  clover4: '<circle cx="8" cy="8" r="3.8" fill="currentColor"/><circle cx="16" cy="8" r="3.8" fill="currentColor"/><circle cx="8" cy="15" r="3.8" fill="currentColor"/><circle cx="16" cy="15" r="3.8" fill="currentColor"/><path d="M12 12l5 10" stroke="currentColor" stroke-width="2"/>',
  cross: '<path d="M9 3h6v6h6v6h-6v6H9v-6H3V9h6z" fill="currentColor"/>',
  fist: '<path d="M6 9a2 2 0 0 1 4 0V8a2 2 0 0 1 4 0v1a2 2 0 0 1 4 0v6a6 6 0 0 1-6 6h-1a6 6 0 0 1-6-6v-3a2 2 0 0 1 1-2z" fill="currentColor"/>',
  magnet: '<path d="M5 3h4v8a3 3 0 0 0 6 0V3h4v8a7 7 0 0 1-14 0z" fill="currentColor"/><path d="M5 3h4v3H5zM15 3h4v3h-4z" fill="#fff"/>',
  horseshoe: '<path d="M5 3h4v8a3 3 0 0 0 6 0V3h4v8a7 7 0 0 1-14 0z" fill="currentColor"/><circle cx="7" cy="9" r=".9" fill="#000" opacity=".4"/><circle cx="17" cy="9" r=".9" fill="#000" opacity=".4"/>',
  book: '<path d="M4 4a2 2 0 0 1 2-2h13v17H6a2 2 0 0 0-2 2z" fill="currentColor"/><path d="M4 21a2 2 0 0 1 2-2h13v3H6a2 2 0 0 1-2-1z" fill="#fff" opacity=".6"/>',
  pause: '<rect x="6" y="4" width="4" height="16" rx="1.2" fill="currentColor"/><rect x="14" y="4" width="4" height="16" rx="1.2" fill="currentColor"/>',
  play: '<path d="M7 4l13 8-13 8z" fill="currentColor"/>',
  cart: '<path d="M3 4h3l2.5 11h10L21 7H7" stroke="currentColor" stroke-width="2.2" fill="none" stroke-linejoin="round"/><circle cx="10" cy="19" r="1.8" fill="currentColor"/><circle cx="17" cy="19" r="1.8" fill="currentColor"/>',
  gear: '<circle cx="12" cy="12" r="3.2" stroke="currentColor" stroke-width="2.2" fill="none"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M4.9 19.1L7 17M17 7l2.1-2.1" stroke="currentColor" stroke-width="2.4" stroke-linecap="round"/>',
  trophy: '<path d="M7 3h10v5a5 5 0 0 1-10 0z" fill="currentColor"/><path d="M7 5H3v2a4 4 0 0 0 4 4M17 5h4v2a4 4 0 0 1-4 4" stroke="currentColor" stroke-width="2" fill="none"/><path d="M10 14h4v4h3v3H7v-3h3z" fill="currentColor"/>',
  medal: '<path d="M7 2h4l1 6-3 1zM17 2h-4l-1 6 3 1z" fill="currentColor" opacity=".7"/><circle cx="12" cy="15" r="6" fill="currentColor"/><path d="M12 11.5l1 2.2 2.4.3-1.8 1.6.5 2.4-2.1-1.2-2.1 1.2.5-2.4-1.8-1.6 2.4-.3z" fill="#fff" opacity=".6"/>',
  user: '<circle cx="12" cy="8" r="4.5" fill="currentColor"/><path d="M3 21a9 9 0 0 1 18 0z" fill="currentColor"/>',
  map: '<path d="M3 6l6-3 6 3 6-3v15l-6 3-6-3-6 3z" fill="currentColor" opacity=".9"/><path d="M9 3v15M15 6v15" stroke="#000" stroke-opacity=".3" stroke-width="1.5"/>',
  back: '<path d="M15 4l-8 8 8 8" stroke="currentColor" stroke-width="3" fill="none" stroke-linecap="round" stroke-linejoin="round"/>',
  close: '<path d="M5 5l14 14M19 5L5 19" stroke="currentColor" stroke-width="3" stroke-linecap="round"/>',
  refresh: '<path d="M20 12a8 8 0 1 1-2.3-5.7" stroke="currentColor" stroke-width="2.6" fill="none" stroke-linecap="round"/><path d="M20 3v6h-6" fill="currentColor"/>',
  skip: '<path d="M5 5l8 7-8 7zM13 5l8 7-8 7z" fill="currentColor"/>',
  lock: '<rect x="5" y="10" width="14" height="11" rx="2" fill="currentColor"/><path d="M8 10V7a4 4 0 0 1 8 0v3" stroke="currentColor" stroke-width="2.4" fill="none"/>',
  gift: '<rect x="3" y="9" width="18" height="4" rx="1" fill="currentColor"/><rect x="5" y="13" width="14" height="8" rx="1" fill="currentColor" opacity=".85"/><path d="M12 9v12" stroke="#000" stroke-opacity=".3" stroke-width="2"/><path d="M12 9c-2-4-6-4-6-1.5S10 9 12 9zm0 0c2-4 6-4 6-1.5S14 9 12 9z" fill="currentColor"/>',
  volume: '<path d="M4 9h4l5-4v14l-5-4H4z" fill="currentColor"/><path d="M16 8a5 5 0 0 1 0 8M18.5 5.5a8.5 8.5 0 0 1 0 13" stroke="currentColor" stroke-width="2" fill="none" stroke-linecap="round"/>',
  check: '<path d="M4 12l5 5L20 6" stroke="currentColor" stroke-width="3" fill="none" stroke-linecap="round" stroke-linejoin="round"/>',
  info: '<circle cx="12" cy="12" r="10" fill="currentColor"/><path d="M12 10v7M12 6.5v.5" stroke="#141420" stroke-width="2.6" stroke-linecap="round"/>',
  globe: '<circle cx="12" cy="12" r="9.5" stroke="currentColor" stroke-width="2" fill="none"/><path d="M2.5 12h19M12 2.5c3 3 3 16 0 19M12 2.5c-3 3-3 16 0 19" stroke="currentColor" stroke-width="1.6" fill="none"/>',
  muted: '<circle cx="12" cy="12" r="9" stroke="currentColor" stroke-width="2.4" fill="none"/><path d="M5.6 5.6l12.8 12.8" stroke="currentColor" stroke-width="2.4"/>',
  hand: '<path d="M8 11V5a1.5 1.5 0 0 1 3 0v5V3.5a1.5 1.5 0 0 1 3 0V10V5a1.5 1.5 0 0 1 3 0v8c0 4-2.5 8-7 8-3 0-4.5-1.5-6-4l-2-3.5a1.5 1.5 0 0 1 2.4-1.8z" fill="currentColor"/>',
};

export function icon(name: string, size = 24, color = "currentColor") {
  const body = P[name] || P.star;
  return `<svg class="ic" viewBox="0 0 24 24" width="${size}" height="${size}" style="color:${color}" aria-hidden="true">${body}</svg>`;
}

export const ICONS = Object.keys(P);
