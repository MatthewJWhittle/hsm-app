import { readStorage, writeStorage } from '../../utils/persistedStorage'

const STORAGE_KEY = 'hsm.dismissMapContextHint.v1'

export function markMapContextHintSeen(): void {
  writeStorage(STORAGE_KEY, '1')
}

export function isMapContextHintSeen(): boolean {
  return readStorage(STORAGE_KEY) === '1'
}
