import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { StatusBar } from '../components/Dashboard/StatusBar';
import { DecisionWall } from './DecisionWall';
import { MainGrid } from '../components/Dashboard/MainGrid';
import { SetupWizard } from './SetupWizard';
import { SystemSettings } from './SystemSettings';
import './Dashboard.css';

export const Dashboard: React.FC = () => {
  return (
    <div className="dashboard-root">
      <StatusBar />
      <main className="dashboard-view">
        <Routes>
          <Route path="/" element={<Navigate to="clues" replace />} />
          <Route path="clues" element={<MainGrid />} />
          <Route path="wall" element={<div className="dashboard-main-content"><DecisionWall /></div>} />
          <Route path="persona" element={<div className="dashboard-main-content"><SetupWizard /></div>} />
          <Route path="settings" element={<div className="dashboard-main-content"><SetupWizard /></div>} />
          <Route path="system-settings" element={<div className="dashboard-main-content"><SystemSettings /></div>} />
        </Routes>
      </main>
    </div>
  );
};
