import { useState } from 'react';
import type { ReactNode } from 'react';
import { Navigate, Route, Routes } from 'react-router-dom';
import LoginPage from '../common/auth/LoginPage';
import ResetPage from '../common/auth/ResetPage';
import { useAuth } from '../common/auth/useAuth';
import { logout, errorMessage } from '../services/api';
import { MessageModal } from '../common/auth/MessageModal';
import styles from './PlaceholderPage.module.css';

// 화면 접근을 제어하며 실제 API 권한 검사는 Backend Dependency가 담당한다.
function Guard({ admin, children }: { admin: boolean; children: ReactNode }) {
  const { session } = useAuth();
  if (!session) return <Navigate to="/login" replace />;
  if ((session.role === 'STAFF') !== admin) return <Navigate to={session.role === 'STAFF' ? '/admin' : '/student'} replace />;
  return children;
}
function Placeholder({ admin = false }: { admin?: boolean }) {
  const [message, setMessage] = useState('');
  const [loggingOut, setLoggingOut] = useState(false);
  async function handleLogout() {
    if (loggingOut) return;
    setLoggingOut(true);
    try { await logout(); }
    catch (error) { setMessage(errorMessage(error)); }
    finally { setLoggingOut(false); }
  }
  return <main className={styles.page}><section className={styles.card}>
    <p className={styles.brand}>FRAME SCIENCE</p><h1>{admin ? '관리자' : '학생'} 메인 개발 예정</h1>
    <p>로그인되었습니다.</p><button className={styles.primaryButton} disabled={loggingOut} onClick={handleLogout}>{loggingOut ? '로그아웃 중…' : '로그아웃'}</button>
    <MessageModal message={message} onClose={() => setMessage('')} />
  </section></main>;
}
export default function AppRoutes() {
  const { ready } = useAuth();
  if (!ready) return <main className={styles.page} role="status">로그인 상태 확인 중…</main>;
  return <Routes>
    <Route path="/login" element={<LoginPage />} />
    <Route path="/password-reset" element={<ResetPage />} />
    <Route path="/student" element={<Guard admin={false}><Placeholder /></Guard>} />
    <Route path="/admin" element={<Guard admin><Placeholder admin /></Guard>} />
    <Route path="*" element={<Navigate to="/login" replace />} />
  </Routes>;
}
