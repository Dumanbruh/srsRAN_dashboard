import { useEffect } from 'react';
import { Outlet } from 'react-router-dom';
import Layout from '../components/layout/Layout';
import { useAuth } from '../context/AuthContext';

export default function ProtectedLayout() {
  const { user, loading, error } = useAuth();
  const shouldRedirect = !loading && (error || !user);

  useEffect(() => {
    if (shouldRedirect) window.location.href = '/login/';
  }, [shouldRedirect]);

  if (loading || shouldRedirect) return null;

  return (
    <Layout>
      <Outlet />
    </Layout>
  );
}
