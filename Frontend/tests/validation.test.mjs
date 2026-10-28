import { test } from 'node:test';
import assert from 'node:assert/strict';
import { normalizePhone, validatePhone, validateLogin, validateCode, validateNewPassword, submitIfValid } from '../node_modules/.cache/validation-test/validation.js';

test('Login empty phone and password have separate field errors', () => {
  assert.deepEqual(validateLogin('', ''), { phone: '휴대폰 번호를 입력해주세요.', password: '비밀번호를 입력해주세요.' });
});

test('Login invalid phone format rejects non-010 and wrong length', () => {
  for (const phone of ['01112345678', '0101234', '010123456789', 'abc']) {
    assert.equal(validateLogin(phone, '5678').phone, '휴대폰 번호 형식을 확인해주세요.');
  }
});

test('Login accepts initial passwords without new password policy', () => {
  for (const password of ['5678', '6789', '7890', 'a', ' ']) {
    assert.deepEqual(validateLogin('010-1234-5678', password), {});
  }
  assert.equal(normalizePhone('010-1234-5678'), '01012345678');
});

test('Reset phone and code use explicit field validation', () => {
  assert.equal(validatePhone(' ').phone, '휴대폰 번호를 입력해주세요.');
  assert.equal(validateCode('').code, '인증번호를 입력해주세요.');
  for (const code of ['12345', '1234567', 'abc123', '１２３４５６']) assert.ok(validateCode(code).code);
  assert.deepEqual(validateCode('012345'), {});
});

test('New password requires ASCII letter, digit, punctuation and 8 characters', () => {
  for (const password of ['5678', 'Frame123', 'Frame!!!', '1234567!', 'Fr12!']) {
    assert.equal(validateNewPassword(password, password).password, '영문, 숫자, 특수문자를 포함해 8자 이상 입력해주세요.');
  }
  for (const password of ['Frame123!', 'Frame123_', 'Frame123`']) assert.deepEqual(validateNewPassword(password, password), {});
  assert.ok(validateNewPassword('A1!' + 'a'.repeat(126), 'A1!' + 'a'.repeat(126)).password);
});

test('New password and confirmation distinguish empty and mismatch', () => {
  assert.deepEqual(validateNewPassword('', ''), { password: '새 비밀번호를 입력해주세요.', confirm: '비밀번호를 한 번 더 입력해주세요.' });
  assert.equal(validateNewPassword('Frame123!', '').confirm, '비밀번호를 한 번 더 입력해주세요.');
  assert.equal(validateNewPassword('Frame123!', 'Frame456!').confirm, '비밀번호가 일치하지 않습니다.');
});

test('Invalid form submissions never invoke API callback', async () => {
  let calls = 0;
  for (const errors of [validateLogin('', '5678'), validateLogin('bad', '5678'), validateLogin('01012345678', ''), validatePhone(''), validateCode(''), validateNewPassword('short', 'short'), validateNewPassword('Frame123!', 'different')]) {
    let displayed;
    await submitIfValid(errors, value => { displayed = value; }, async () => { calls++; });
    assert.deepEqual(displayed, errors);
  }
  assert.equal(calls, 0);
});

test('Valid submit clears old field errors and invokes API once', async () => {
  let displayed = { phone: 'old' };
  let calls = 0;
  await submitIfValid(validateLogin('01012345678', '5678'), value => { displayed = value; }, async () => { calls++; });
  assert.deepEqual(displayed, {});
  assert.equal(calls, 1);
});

test('Phone formatter handles typing, pasted text and maximum length', async () => {
  const { formatPhone } = await import('../node_modules/.cache/validation-test/validation.js');
  const cases = [
    ['', ''], ['abc', ''], ['0', '0'], ['01', '01'], ['010', '010'],
    ['0101', '010-1'], ['01012', '010-12'], ['010123', '010-123'],
    ['0101234', '010-1234'], ['01012345', '010-1234-5'],
    ['010123456', '010-1234-56'], ['0101234567', '010-1234-567'],
    ['01012345678', '010-1234-5678'], ['010-1234-5678', '010-1234-5678'],
    ['010 1234 5678', '010-1234-5678'], ['abc010 1234-5678!', '010-1234-5678'],
    ['01012345678999', '010-1234-5678'],
  ];
  for (const [input, expected] of cases) assert.equal(formatPhone(input), expected);
  assert.equal(normalizePhone(formatPhone('01012345678')), '01012345678');
  assert.deepEqual(validateLogin(formatPhone('01012345678'), '5678'), {});
  assert.deepEqual(validatePhone(formatPhone('01012345678')), {});
  assert.ok(validatePhone(formatPhone('01112345678')).phone);
  assert.ok(validatePhone(formatPhone('0101234')).phone);
});
