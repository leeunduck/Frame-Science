import type { InputHTMLAttributes } from 'react';
import styles from './AuthPage.module.css';

type Props = InputHTMLAttributes<HTMLInputElement> & {
  id: string;
  label: string;
  error?: string;
};

export function AuthField({ id, label, error, ...inputProps }: Props) {
  return (
    <div className={styles.field}>
      <div className={styles.labelRow}>
        <label htmlFor={id}>{label}</label>
        {error && <span id={`${id}-error`} className={styles.fieldError} role="alert">{error}</span>}
      </div>
      <input
        {...inputProps}
        id={id}
        className={`${styles.input} ${error ? styles.inputError : ''}`}
        aria-invalid={Boolean(error)}
        aria-describedby={error ? `${id}-error` : undefined}
      />
    </div>
  );
}
