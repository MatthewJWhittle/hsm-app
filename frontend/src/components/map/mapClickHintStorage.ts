import { readStorage, writeStorage } from '../../utils/persistedStorage'

const STORAGE_KEY = 'hsm.dismissClickHint.v1'

export function dismissClickHintStorage(): void {
  writeStorage(STORAGE_KEY, '1')
}

export function isClickHintDismissedInStorage(): boolean {
  return readStorage(STORAGE_KEY) === '1'
}
