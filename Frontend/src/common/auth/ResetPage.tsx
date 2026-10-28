import { useState } from 'react';
import type { FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { authApi, errorMessage, resetErrorField } from '../../services/api';
import { MessageModal } from './MessageModal';
import { AuthField } from './AuthField';
import { formatPhone, normalizePhone, submitIfValid, validatePhone, validateCode, validateNewPassword } from './validation';
import type { FieldErrors } from './validation';
import styles from './AuthPage.module.css';

export default function ResetPage() {
  const [step, setStep] = useState<'phone' | 'code' | 'password' | 'done'>('phone');
  const [phone, setPhone] = useState('');
  const [code, setCode] = useState('');
  const [resetToken, setResetToken] = useState('');
  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [errors, setErrors] = useState<FieldErrors>({});
  const [message, setMessage] = useState('');
  const [busy, setBusy] = useState(false);
  const navigate = useNavigate();

  function clearError(field: keyof FieldErrors) {
    setErrors(current => ({ ...current, [field]: undefined }));
  }

  async function submit(event: FormEvent) {
    event.preventDefault();
    if (busy || step === 'done') return;
    const validation = step === 'phone' ? validatePhone(phone)
      : step === 'code' ? validateCode(code) : validateNewPassword(password, confirm);
    await submitIfValid(validation, setErrors, async () => {
      setBusy(true);
      const normalized = normalizePhone(phone);
      try {
        if (step === 'phone') {
          await authApi.post('/auth/password-reset/request', { phone: normalized });
          setStep('code');
        } else if (step === 'code') {
          const { data } = await authApi.post<{ resetToken: string }>('/auth/password-reset/verify', { phone: normalized, code });
          setResetToken(data.resetToken);
          setStep('password');
        } else {
          await authApi.post('/auth/password-reset/confirm', { resetToken, newPassword: password, newPasswordConfirm: confirm });
          setResetToken('');
          setPassword('');
          setConfirm('');
          setStep('done');
          setMessage('비밀번호가 변경되었습니다. 새 비밀번호로 로그인해주세요.');
        }
      } catch (error) {
        const field = resetErrorField(error);
        if (field) setErrors({ [field]: errorMessage(error) });
        else setMessage(errorMessage(error));
      } finally { setBusy(false); }
    });
  }

  function restart() {
    setStep('phone');
    setCode('');
    setResetToken('');
    setPassword('');
    setConfirm('');
    setErrors({});
  }

  return (
    <main className={styles.page}>
      <section className={styles.card}>
        <h1 className={styles.title}>비밀번호 재설정</h1>
        <p className={styles.description}>
          {step === 'phone' ? '등록된 휴대폰 번호를 입력해주세요.'
            : step === 'code' ? '발송된 인증번호 6자리를 입력해주세요.'
            : step === 'done' ? '새 비밀번호로 로그인해주세요.'
            : '새 비밀번호는 8자 이상, 영문·숫자·특수문자를 포함해주세요.'}
        </p>
        {step !== 'done' && <form className={styles.form} onSubmit={submit} noValidate>
          {step === 'phone' && <AuthField id="reset-phone" label="휴대폰 번호" type="tel" inputMode="numeric" autoComplete="tel"
            value={phone} error={errors.phone} onChange={e => { setPhone(formatPhone(e.target.value)); clearError('phone'); }} />}
          {step === 'code' && <AuthField id="reset-code" label="인증번호" inputMode="numeric" autoComplete="one-time-code"
            value={code} error={errors.code} onChange={e => { setCode(e.target.value); clearError('code'); }} />}
          {step === 'password' && <>
            <AuthField id="new-password" label="새 비밀번호" type="password" autoComplete="new-password"
              value={password} error={errors.password} onChange={e => { setPassword(e.target.value); clearError('password'); }} />
            <AuthField id="password-confirm" label="새 비밀번호 확인" type="password" autoComplete="new-password"
              value={confirm} error={errors.confirm} onChange={e => { setConfirm(e.target.value); clearError('confirm'); }} />
          </>}
          <button className={styles.primaryButton} disabled={busy}>
            {busy ? '처리 중…' : step === 'phone' ? '인증번호 요청' : step === 'code' ? '인증번호 확인' : '비밀번호 변경'}
          </button>
          {step !== 'phone' && <button className={styles.secondaryButton} type="button" disabled={busy} onClick={restart}>처음부터 다시 요청</button>}
        </form>}
        <Link className={styles.textLink} to="/login">로그인으로 돌아가기</Link>
        <MessageModal message={message} onClose={() => {
          setMessage('');
          if (step === 'done') navigate('/login', { replace: true });
        }} />
      </section>
    </main>
  );
}
