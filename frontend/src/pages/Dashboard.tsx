import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { StatusBar } from '../components/Dashboard/StatusBar';
import { DecisionWall } from './DecisionWall';
import './Dashboard.css';

export const Dashboard: React.FC = () => {
  return (
    <div className="dashboard-root">
      <StatusBar />
      <main className="dashboard-view">
        <Routes>
          <Route path="/" element={<Navigate to="wall" replace />} />
          <Route path="wall" element={<div className="dashboard-main-content"><DecisionWall /></div>} />
        </Routes>
      </main>
    </div>
  );
};
