import { readStorage, writeStorage } from '../../utils/persistedStorage'

const WELCOME_KEY = 'hsm.mapWelcomeSeen.v1'

/** Legacy: dismissible top banner; treat as “already seen” for welcome. */
const LEGACY_STRIP_KEY = 'hsm.dismissInterpretationStrip.v1'

export function markMapWelcomeSeen(): void {
  writeStorage(WELCOME_KEY, '1')
}

/**
 * True if the user has completed the first-visit experience (old banner or new modal).
 */
export function isMapWelcomeSeen(): boolean {
  if (readStorage(WELCOME_KEY) === '1') return true
  if (readStorage(LEGACY_STRIP_KEY) === '1') return true
  return false
}
