import React from 'react';
import { Routes, Route } from 'react-router-dom';
import { MainGrid } from '../components/Dashboard/MainGrid';
import { StatusBar } from '../components/Dashboard/StatusBar';
import { DecisionWall } from './DecisionWall';
import './Dashboard.css';

export const Dashboard: React.FC = () => {
  return (
    <div className="dashboard-root">
      <StatusBar />
      <main className="dashboard-view">
        <Routes>
          <Route path="/" element={<div className="dashboard-main-content"><MainGrid /></div>} />
          <Route path="wall" element={<div className="dashboard-main-content"><DecisionWall /></div>} />
          <Route path="clues" element={<div className="dashboard-main-content"><h2>Clue 列表视图</h2></div>} />
          <Route path="persona" element={<div className="dashboard-main-content"><h2>当前需求画像</h2></div>} />
          <Route path="settings" element={<div className="dashboard-main-content"><h2>任务与采集器配置</h2></div>} />
        </Routes>
      </main>
    </div>
  );
};
