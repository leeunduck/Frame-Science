"""Live Vite + API smoke test with local Seed accounts; no password changes.
Run while both servers are running: python -m scripts.smoke_auth
"""
from concurrent.futures import ThreadPoolExecutor
import httpx
from app.config import get_settings


def main():
    if get_settings().app_env != 'local':
        raise SystemExit('Smoke test is available only in APP_ENV=local')
    base = 'http://127.0.0.1:5173'
    with httpx.Client(base_url=base) as client:
        assert client.get('/login').status_code == 200
        for phone, role in [('01012345678', 'STUDENT'), ('01023456789', 'PARENT'), ('01034567890', 'STAFF')]:
            result = client.post('/api/auth/login', json={'phone': phone, 'password': phone[-4:]}, headers={'Origin': base})
            assert result.status_code == 200, f'{role}: expected original Seed password'
            assert result.json()['role'] == role
            assert client.cookies.get('refresh_token')
            assert client.post('/api/auth/refresh').status_code == 200
            assert client.post('/api/auth/logout').status_code == 204
            assert not client.cookies.get('refresh_token')
            assert client.post('/api/auth/refresh').status_code == 401
        client.post('/api/auth/login', json={'phone': '01012345678', 'password': '5678'}).raise_for_status()
        token = client.cookies.get('refresh_token')

        def refresh(_):
            return httpx.post(base + '/api/auth/refresh', cookies={'refresh_token': token})

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(refresh, range(2)))
        assert sorted(r.status_code for r in results) == [200, 401]
        winner = next(r for r in results if r.status_code == 200)
        assert httpx.post(base + '/api/auth/logout', cookies=winner.cookies).status_code == 204
    print('PASS: live Vite proxy, 3 roles, cookies, refresh, logout, concurrent rotation')


if __name__ == '__main__':
    main()
