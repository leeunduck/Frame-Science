import { test } from 'node:test';
import assert from 'node:assert/strict';
import { AxiosError } from 'axios';
import { api, authApi, setSession, getSession, refreshSession, initializeAuth, logout } from '../node_modules/.cache/auth-test/api.js';
const response = (config, data, status = 200) => ({ config, data, status, statusText: '', headers: {} });
const unauthorized = config => Promise.reject(new AxiosError('Unauthorized', 'ERR_BAD_REQUEST', config, null, response(config, {}, 401)));
const tick = () => new Promise(resolve => setTimeout(resolve, 10));

test('StrictMode initialization shares one refresh', async () => {
  let count = 0;
  authApi.defaults.adapter = async config => { count++; await tick(); return response(config, { accessToken: 'initial', role: 'STUDENT' }); };
  initializeAuth(); initializeAuth();
  await refreshSession();
  assert.equal(count, 1);
  assert.equal(getSession().accessToken, 'initial');
});

test('concurrent 401s share refresh and replay with new bearer', async () => {
  setSession({ accessToken: 'old', role: 'PARENT' });
  let refreshes = 0;
  authApi.defaults.adapter = async config => { refreshes++; await tick(); return response(config, { accessToken: 'new', role: 'PARENT' }); };
  api.defaults.adapter = async config => config.headers.get('Authorization') === 'Bearer new' ? response(config, 'ok') : unauthorized(config);
  const results = await Promise.all([api.get('/protected-a'), api.get('/protected-b'), api.get('/protected-c')]);
  assert.equal(refreshes, 1);
  assert.deepEqual(results.map(r => r.data), ['ok', 'ok', 'ok']);
});

test('failed refresh clears memory without looping', async () => {
  let refreshes = 0;
  setSession({ accessToken: 'old', role: 'STAFF' });
  authApi.defaults.adapter = config => { refreshes++; return unauthorized(config); };
  api.defaults.adapter = unauthorized;
  await assert.rejects(api.get('/protected'));
  assert.equal(refreshes, 1);
  assert.equal(getSession(), null);
});

test('replayed 401 stops after one retry and clears session', async () => {
  let refreshes = 0, calls = 0;
  setSession({ accessToken: 'old', role: 'STAFF' });
  authApi.defaults.adapter = async config => { refreshes++; return response(config, { accessToken: 'new', role: 'STAFF' }); };
  api.defaults.adapter = config => { calls++; return unauthorized(config); };
  await assert.rejects(api.get('/protected'));
  assert.equal(refreshes, 1); assert.equal(calls, 2); assert.equal(getSession(), null);
});

test('auth endpoint errors do not trigger refresh', async () => {
  let refreshes = 0;
  authApi.defaults.adapter = config => { refreshes++; return unauthorized(config); };
  api.defaults.adapter = unauthorized;
  await assert.rejects(api.post('/auth/login'));
  assert.equal(refreshes, 0);
});

test('logout during refresh cannot resurrect memory session', async () => {
  setSession({ accessToken: 'old', role: 'STAFF' });
  const paths = [];
  authApi.defaults.adapter = async config => { paths.push(config.url); await tick(); return response(config, { accessToken: 'new', role: 'STAFF' }); };
  const refresh = refreshSession();
  await logout(); await refresh;
  assert.equal(getSession(), null);
  assert.deepEqual(paths, ['/auth/refresh', '/auth/logout']);
});

test('late 401 after logout does not restore a session', async () => {
  setSession(null);
  let refreshes = 0;
  authApi.defaults.adapter = config => { refreshes++; return unauthorized(config); };
  api.defaults.adapter = unauthorized;
  await assert.rejects(api.get('/protected'));
  assert.equal(refreshes, 0);
});

function deferred() {
  let resolve, reject;
  const promise = new Promise((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
}

test('Logout keeps Session until server success and shares duplicate clicks', async () => {
  const original = { accessToken: 'old', role: 'STAFF' };
  setSession(original);
  const pending = deferred();
  const started = deferred();
  let calls = 0;
  authApi.defaults.adapter = async config => { calls++; started.resolve(); await pending.promise; return response(config, {}); };
  const first = logout();
  const second = logout();
  assert.equal(first, second);
  await started.promise;
  assert.deepEqual(getSession(), original);
  pending.resolve();
  await first;
  assert.equal(calls, 1);
  assert.equal(getSession(), null);
});

test('Logout network and server failures preserve Session and propagate error for Modal', async () => {
  for (const status of [undefined, 500]) {
    const original = { accessToken: 'old', role: 'STUDENT' };
    setSession(original);
    authApi.defaults.adapter = config => Promise.reject(new AxiosError('Logout failed', status ? 'ERR_BAD_RESPONSE' : 'ERR_NETWORK', config, null, status ? response(config, {}, status) : undefined));
    await assert.rejects(logout(), /Logout failed/);
    assert.deepEqual(getSession(), original);
    authApi.defaults.adapter = async config => response(config, {});
    await logout();
    assert.equal(getSession(), null);
  }
});

test('Logout blocks new refresh and concurrent 401 while waiting for existing rotation', async () => {
  const original = { accessToken: 'old', role: 'STAFF' };
  setSession(original);
  const rotation = deferred();
  const started = deferred();
  const paths = [];
  authApi.defaults.adapter = async config => {
    paths.push(config.url);
    if (config.url === '/auth/refresh') { started.resolve(); await rotation.promise; }
    return response(config, { accessToken: 'rotated', role: 'STAFF' });
  };
  api.defaults.adapter = unauthorized;
  const refreshing = refreshSession();
  await started.promise;
  const loggingOut = logout();
  assert.equal(await refreshSession(), null);
  await assert.rejects(api.get('/protected'));
  assert.deepEqual(getSession(), original);
  assert.deepEqual(paths, ['/auth/refresh']);
  rotation.resolve();
  await Promise.all([refreshing, loggingOut]);
  assert.deepEqual(paths, ['/auth/refresh', '/auth/logout']);
  assert.equal(getSession(), null);
});

test('Failed Logout after rotation remains visible and allows later refresh', async () => {
  const original = { accessToken: 'old', role: 'PARENT' };
  setSession(original);
  const rotation = deferred();
  const started = deferred();
  authApi.defaults.adapter = async config => {
    if (config.url === '/auth/logout') throw new AxiosError('offline', 'ERR_NETWORK', config);
    started.resolve(); await rotation.promise;
    return response(config, { accessToken: 'new', role: 'PARENT' });
  };
  const refreshing = refreshSession();
  await started.promise;
  const failure = assert.rejects(logout(), /offline/);
  rotation.resolve();
  await Promise.all([refreshing, failure]);
  assert.deepEqual(getSession(), original);
  await refreshSession();
  assert.equal(getSession().accessToken, 'new');
});

test('Auth errors preserve user messages and Reset field versus Modal mapping', async () => {
  const { errorMessage, resetErrorField } = await import('../node_modules/.cache/auth-test/api.js');
  const cases = [
    ['AUTH_INVALID_CREDENTIALS', '등록되지 않은 휴대폰 번호이거나 비밀번호가 올바르지 않습니다.', undefined],
    ['ACCOUNT_INACTIVE', '비활성 계정입니다. 관리자에게 문의해주세요.', undefined],
    ['PASSWORD_RESET_CODE_INVALID', '인증번호가 올바르지 않습니다.', 'code'],
    ['PASSWORD_RESET_CODE_EXPIRED', '인증번호가 만료되었습니다. 새 인증번호를 요청해주세요.', undefined],
    ['PASSWORD_RESET_CODE_ATTEMPTS_EXCEEDED', '인증번호 입력 횟수를 초과했습니다. 새 인증번호를 요청해주세요.', undefined],
    ['PASSWORD_POLICY_VIOLATION', '비밀번호 정책 안내', 'password'],
    ['PASSWORD_CONFIRM_MISMATCH', '비밀번호 확인 안내', 'confirm'],
  ];
  for (const [code, message, field] of cases) {
    const error = new AxiosError('failed', 'ERR_BAD_REQUEST', {}, null, response({}, { code, message }, 400));
    assert.equal(errorMessage(error), message);
    assert.equal(resetErrorField(error), field);
  }
  const server = new AxiosError('private', 'ERR_BAD_RESPONSE', {}, null, response({}, { message: 'private' }, 503));
  assert.equal(errorMessage(server), '서버에 연결할 수 없습니다. 잠시 후 다시 시도해주세요.');
  assert.equal(resetErrorField(server), undefined);
});
