import React from 'react';
import './DashboardPanels.css';

export const TaskPanel: React.FC = () => {
  return (
    <div className="panel-card">
      <div className="panel-header">
        <h3 className="panel-title">采集任务状态</h3>
        <span className="status-badge status-active">运行中</span>
      </div>
      <div className="panel-content">
        <div className="stat-group">
          <div className="stat-item">
            <span className="stat-label">今日采集</span>
            <span className="stat-value">256</span>
          </div>
          <div className="stat-item">
            <span className="stat-label">匹配线索</span>
            <span className="stat-value">12</span>
          </div>
          <div className="stat-item">
            <span className="stat-label">上次更新</span>
            <span className="stat-value" style={{ fontSize: '14px' }}>10分钟前</span>
          </div>
        </div>
      </div>
    </div>
  );
};
