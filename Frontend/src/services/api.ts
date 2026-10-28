import axios, { AxiosError } from 'axios';

export type Role = 'STUDENT' | 'PARENT' | 'STAFF';
export type AuthSession = { accessToken: string; role: Role };
const config = { baseURL: import.meta.env.VITE_API_BASE_URL ?? '/api', withCredentials: true };
export const api = axios.create(config);
export const authApi = axios.create(config);
// 브라우저 저장소에 토큰을 남기지 않고 현재 앱 수명 동안만 보관한다.
let session: AuthSession | null = null;
let initialized = false;
let generation = 0;
// 동시 401과 초기 복구가 같은 Promise를 공유해 Rotation 중복 호출을 막는다.
let refreshTask: Promise<AuthSession | null> | null = null;
let logoutTask: Promise<void> | null = null;
const listeners = new Set<() => void>();
export const getSession = () => session;
export const isInitialized = () => initialized;
export const subscribe = (listener: () => void) => {
  listeners.add(listener);
  return () => { listeners.delete(listener); };
};
export function setSession(value: AuthSession | null) {
  session = value;
  initialized = true;
  listeners.forEach(listener => listener());
}
export function refreshSession(): Promise<AuthSession | null> {
  if (logoutTask) return Promise.resolve(null);
  if (!refreshTask) {
    // 이전 인증 세대의 응답이 Logout 이후 Session을 복원하지 못하게 한다.
    const version = generation;
    refreshTask = authApi.post<AuthSession>('/auth/refresh').then(({ data }) => {
      if (version !== generation) return null;
      setSession(data);
      return data;
    }).catch(() => {
      if (version === generation) setSession(null);
      return null;
    }).finally(() => { refreshTask = null; });
  }
  return refreshTask;
}
export function initializeAuth() {
  // 새로고침으로 사라진 메모리 상태는 HttpOnly Cookie를 통해 한 번 복구한다.
  if (!initialized) void refreshSession();
}
export async function login(phone: string, password: string) {
  generation += 1;
  const { data } = await authApi.post<AuthSession>('/auth/login', { phone, password });
  setSession(data);
}
export function logout(): Promise<void> {
  if (logoutTask) return logoutTask;
  generation += 1;
  logoutTask = (async () => {
    // 진행 중인 Refresh가 Cookie를 교체할 수 있어 완료 후 Logout으로 폐기한다.
    // 대기 중 새 Refresh는 막고, 실패 Modal이 유지되도록 Session은 성공 후 지운다.
    if (refreshTask) await refreshTask;
    await authApi.post('/auth/logout');
    setSession(null);
  })().finally(() => { logoutTask = null; });
  return logoutTask;
}
api.interceptors.request.use(config => {
  if (session) config.headers.set('Authorization', `Bearer ${session.accessToken}`);
  return config;
});
api.interceptors.response.use(response => response, async (error: AxiosError) => {
  const request = error.config as (NonNullable<typeof error.config> & { retried?: boolean }) | undefined;
  if (error.response?.status !== 401 || !request || request.url?.startsWith('/auth/')) throw error;
  if (logoutTask || !session) throw error;
  // Auth API는 제외하고 원 요청도 한 번만 재시도해 Refresh 루프를 막는다.
  if (request.retried) { setSession(null); throw error; }
  request.retried = true;
  const sentToken = request.headers.get('Authorization');
  // 늦게 도착한 401이 이전 토큰의 응답이면 이미 갱신된 토큰을 재사용한다.
  const restored = session && sentToken !== `Bearer ${session.accessToken}` ? session : await refreshSession();
  if (!restored || logoutTask || !session) throw error;
  request.headers.set('Authorization', `Bearer ${restored.accessToken}`);
  return api(request);
});
export function errorMessage(error: unknown): string {
  if (axios.isAxiosError(error) && error.response && error.response.status < 500) {
    return error.response.data?.message ?? '입력 내용을 확인해주세요.';
  }
  return '서버에 연결할 수 없습니다. 잠시 후 다시 시도해주세요.';
}

export function resetErrorField(error: unknown): 'password' | 'confirm' | 'code' | undefined {
  if (!axios.isAxiosError(error) || !error.response || error.response.status >= 500) return undefined;
  switch (error.response.data?.code) {
    case 'PASSWORD_POLICY_VIOLATION': return 'password';
    case 'PASSWORD_CONFIRM_MISMATCH': return 'confirm';
    case 'PASSWORD_RESET_CODE_INVALID': return 'code';
    // 만료·횟수 초과는 입력 수정만으로 해결되지 않으므로 Modal에서 재요청을 안내한다.
    default: return undefined;
  }
}
