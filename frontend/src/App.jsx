import { useEffect } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import ProtectedLayout from './routes/ProtectedLayout';
import Dashboard from './pages/Dashboard';
import Scenarios from './pages/Scenarios';
import AI from './pages/AI';
import Login from './pages/Login';
import { primeCsrf } from './api/auth';

export default function App() {
  useEffect(() => { primeCsrf(); }, []);

  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login/" element={<Login />} />
        <Route element={<AuthProvider><ProtectedLayout /></AuthProvider>}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/scenarios/" element={<Scenarios />} />
          <Route path="/ai/" element={<AI />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
