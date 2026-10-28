import { useState } from 'react';
import type { FormEvent } from 'react';
import { Link, Navigate } from 'react-router-dom';
import { errorMessage, login } from '../../services/api';
import { useAuth } from './useAuth';
import { MessageModal } from './MessageModal';
import { AuthField } from './AuthField';
import { formatPhone, normalizePhone, submitIfValid, validateLogin } from './validation';
import type { FieldErrors } from './validation';
import styles from './AuthPage.module.css';

export default function LoginPage() {
  const { session } = useAuth();
  const [phone, setPhone] = useState('');
  const [password, setPassword] = useState('');
  const [errors, setErrors] = useState<FieldErrors>({});
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);
  if (session) return <Navigate to={session.role === 'STAFF' ? '/admin' : '/student'} replace />;

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (busy) return;
    await submitIfValid(validateLogin(phone, password), setErrors, async () => {
      setBusy(true);
      try { await login(normalizePhone(phone), password); }
      catch (error) { setMessage(errorMessage(error)); }
      finally { setBusy(false); }
    });
  }

  return (
    <main className={styles.page}>
      <section className={styles.card}>
        <img src="/Logo.png" alt="제이에이치사이언스랩" className={styles.logo} />
        <h1 className={styles.title}>로그인</h1>
        <p className={styles.description}>등록된 휴대폰 번호로 로그인해주세요.</p>
        <form className={styles.form} onSubmit={submit} noValidate>
          <AuthField id="phone" label="휴대폰 번호" type="tel" inputMode="numeric" autoComplete="username"
            placeholder="010-1234-5678" value={phone} error={errors.phone}
            onChange={e => { setPhone(formatPhone(e.target.value)); setErrors(current => ({ ...current, phone: undefined })); }} />
          <AuthField id="password" label="비밀번호" type="password" autoComplete="current-password"
            value={password} error={errors.password}
            onChange={e => { setPassword(e.target.value); setErrors(current => ({ ...current, password: undefined })); }} />
          <button className={styles.primaryButton} disabled={busy}>{busy ? '로그인 중…' : '로그인'}</button>
        </form>
        <Link className={styles.textLink} to="/password-reset">비밀번호 재설정</Link>
        <MessageModal message={message} onClose={() => setMessage('')} />
      </section>
    </main>
  );
}
