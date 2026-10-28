import { useSyncExternalStore } from 'react';
import { getSession, isInitialized, subscribe } from '../../services/api';
export function useAuth() {
  const session = useSyncExternalStore(subscribe, getSession);
  const ready = useSyncExternalStore(subscribe, isInitialized);
  return { session, ready };
}
