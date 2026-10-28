export type FieldErrors = Partial<Record<'phone' | 'password' | 'code' | 'confirm', string>>;
// 화면 포맷과 API 정규화를 분리해 하이픈이 Auth API에 전달되지 않게 한다.
export const normalizePhone = (phone: string) => phone.replace(/\D/g, '');

export function formatPhone(value: string): string {
  const digits = normalizePhone(value).slice(0, 11);
  if (digits.length <= 3) return digits;
  if (digits.length <= 7) return `${digits.slice(0, 3)}-${digits.slice(3)}`;
  return `${digits.slice(0, 3)}-${digits.slice(3, 7)}-${digits.slice(7)}`;
}

export function validatePhone(phone: string): FieldErrors {
  if (!phone.trim()) return { phone: '휴대폰 번호를 입력해주세요.' };
  return /^010[0-9]{8}$/.test(normalizePhone(phone))
    ? {} : { phone: '휴대폰 번호 형식을 확인해주세요.' };
}

export function validateLogin(phone: string, password: string): FieldErrors {
  return { ...validatePhone(phone), ...(!password ? { password: '비밀번호를 입력해주세요.' } : {}) };
}

export function validateCode(code: string): FieldErrors {
  if (!code) return { code: '인증번호를 입력해주세요.' };
  return /^[0-9]{6}$/.test(code) ? {} : { code: '인증번호 6자리를 입력해주세요.' };
}

export function validateNewPassword(password: string, confirm: string): FieldErrors {
  const errors: FieldErrors = {};
  if (!password) errors.password = '새 비밀번호를 입력해주세요.';
  else if (Array.from(password).length < 8 || !/[A-Za-z]/.test(password) || !/[0-9]/.test(password) || !/[\x21-\x2f\x3a-\x40\x5b-\x60\x7b-\x7e]/.test(password)) {
    errors.password = '영문, 숫자, 특수문자를 포함해 8자 이상 입력해주세요.';
  } else if (Array.from(password).length > 128) {
    errors.password = '비밀번호는 128자 이하로 입력해주세요.';
  }
  if (!confirm) errors.confirm = '비밀번호를 한 번 더 입력해주세요.';
  else if (password !== confirm) errors.confirm = '비밀번호가 일치하지 않습니다.';
  return errors;
}

// 입력 오류는 API 호출 전에 필드로 안내하고, 계정·서버 오류는 응답 이후 Modal로 처리한다.
export async function submitIfValid(errors: FieldErrors, showErrors: (errors: FieldErrors) => void, submit: () => Promise<void>) {
  showErrors(errors);
  if (Object.keys(errors).length === 0) await submit();
}
