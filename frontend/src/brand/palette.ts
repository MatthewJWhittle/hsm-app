/**
 * Brand palette (single source of truth). MUI theme and CSS variables are derived from this.
 */
export const brandPalette = {
  dustyMauve: '#916c80',
  jungleTeal: '#55917f',
  lightCaramel: '#fcb97d',
  midnightViolet: '#1f0318',
  inkBlack: '#101419',
} as const

const { dustyMauve, jungleTeal, lightCaramel, midnightViolet, inkBlack } = brandPalette
const g = [dustyMauve, jungleTeal, lightCaramel, midnightViolet, inkBlack].join(', ')

export const brandGradients = {
  top: `linear-gradient(0deg, ${g})`,
  right: `linear-gradient(90deg, ${g})`,
  bottom: `linear-gradient(180deg, ${g})`,
  left: `linear-gradient(270deg, ${g})`,
  topRight: `linear-gradient(45deg, ${g})`,
  bottomRight: `linear-gradient(135deg, ${g})`,
  topLeft: `linear-gradient(225deg, ${g})`,
  bottomLeft: `linear-gradient(315deg, ${g})`,
  radial: `radial-gradient(circle, ${g})`,
} as const

/** Pushes `brandPalette` and gradients onto `:root` for raw CSS. */
export function injectBrandTokens(): void {
  if (typeof document === 'undefined') return
  const r = document.documentElement
  r.style.setProperty('--dusty-mauve', dustyMauve)
  r.style.setProperty('--jungle-teal', jungleTeal)
  r.style.setProperty('--light-caramel', lightCaramel)
  r.style.setProperty('--midnight-violet', midnightViolet)
  r.style.setProperty('--ink-black', inkBlack)
  r.style.setProperty('--gradient-top', brandGradients.top)
  r.style.setProperty('--gradient-right', brandGradients.right)
  r.style.setProperty('--gradient-bottom', brandGradients.bottom)
  r.style.setProperty('--gradient-left', brandGradients.left)
  r.style.setProperty('--gradient-top-right', brandGradients.topRight)
  r.style.setProperty('--gradient-bottom-right', brandGradients.bottomRight)
  r.style.setProperty('--gradient-top-left', brandGradients.topLeft)
  r.style.setProperty('--gradient-bottom-left', brandGradients.bottomLeft)
  r.style.setProperty('--gradient-radial', brandGradients.radial)
}
