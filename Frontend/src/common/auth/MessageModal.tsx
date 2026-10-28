import { useEffect, useRef } from 'react';
import styles from './MessageModal.module.css';
export function MessageModal({ message, onClose }: { message: string; onClose: () => void }) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    if (message) ref.current?.showModal();
    else ref.current?.close();
  }, [message]);
  return <dialog ref={ref} className={styles.dialog} aria-labelledby="modal-title" onCancel={onClose} onClose={onClose}>
    <h2 id="modal-title">안내</h2><p>{message}</p>
    <button className={styles.primaryButton} onClick={onClose} autoFocus>확인</button>
  </dialog>;
}
