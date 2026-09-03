import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Toaster } from 'sonner';
import Layout from './components/layout/Layout';
import LandingPage from './pages/LandingPage';
import DashboardPage from './pages/DashboardPage';
import AnalyticsPage from './pages/AnalyticsPage';
import ReasoningLogPage from './pages/ReasoningLogPage';
import PositionsPage from './pages/PositionsPage';
import ChatPage from './pages/ChatPage';

export default function App() {
  return (
    <BrowserRouter>
      <Toaster position="bottom-right" theme="dark" expand={true} richColors />
      <Routes>
        {/* Landing page */}
        <Route
          path="/"
          element={
            <div className="min-h-screen bg-[#0D0F14] overflow-hidden">
              <div className="retro-grid opacity-20 fixed inset-0 pointer-events-none" />
              <LandingPage />
            </div>
          }
        />

        {/* App shell with Navbar Layout */}
        <Route
          path="/*"
          element={
            <Layout>
              <Routes>
                <Route path="/dashboard" element={<DashboardPage />} />
                <Route path="/analytics" element={<AnalyticsPage />} />
                <Route path="/logs" element={<ReasoningLogPage />} />
                <Route path="/positions" element={<PositionsPage />} />
                <Route path="/chat" element={<ChatPage />} />
                <Route path="*" element={<DashboardPage />} />
              </Routes>
            </Layout>
          }
        />
      </Routes>
    </BrowserRouter>
  );
}
