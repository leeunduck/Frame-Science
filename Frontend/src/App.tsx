import { useEffect } from 'react';
import AppRoutes from './app/router';
import { initializeAuth } from './services/api';
export default function App() {
  useEffect(initializeAuth, []);
  return <AppRoutes />;
}
