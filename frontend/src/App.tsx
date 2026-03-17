import { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { SetupWizard } from './pages/SetupWizard';
import { Dashboard } from './pages/Dashboard';
import { apiService } from './services/api';
import './index.css';

function App() {
  const [hasConstraint, setHasConstraint] = useState<boolean | null>(null);

  useEffect(() => {
    const checkState = async () => {
      try {
        const state = await apiService.getSystemState(6000);
        setHasConstraint(state.has_constraint);
      } catch (e) {
        console.error("Failed to check system state", e);
        setHasConstraint(false);
      }
    };
    checkState();
    const fallback = setTimeout(() => {
      setHasConstraint(prev => (prev === null ? false : prev));
    }, 8000);
    return () => clearTimeout(fallback);
  }, []);

  if (hasConstraint === null) {
    return (
      <div className="app-loading">
        <div className="spinner"></div>
        <p>正在初始化环境...</p>
      </div>
    );
  }

  return (
    <Router>
      <div className="app-container">
        <Routes>
          <Route 
            path="/" 
            element={<Navigate to={hasConstraint ? "/dashboard" : "/setup"} replace />} 
          />
          <Route path="/setup" element={<SetupWizard />} />
          <Route path="/dashboard/*" element={<Dashboard />} />
        </Routes>
      </div>
    </Router>
  );
}

export default App;
