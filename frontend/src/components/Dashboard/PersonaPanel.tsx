import React from 'react';
import './DashboardPanels.css';

export const PersonaPanel: React.FC = () => {
  return (
    <div className="panel-card">
      <div className="panel-header">
        <h3 className="panel-title">当前企业画像</h3>
        <button className="text-btn">编辑</button>
      </div>
      <div className="panel-content">
        <div className="persona-info">
          <div className="info-row">
            <span className="info-label">核 心 业 务</span>
            <span className="info-value">建筑工程、水利水电</span>
          </div>
          <div className="info-row">
            <span className="info-label">已录入资质</span>
            <div className="tags-container">
              <span className="tag">建筑工程施工总承包一级</span>
              <span className="tag">安全生产许可证</span>
            </div>
          </div>
          <div className="info-row">
            <span className="info-label">地域及门槛</span>
            <span className="info-value text-muted">广东省内 / 预算&gt;1000万</span>
          </div>
        </div>
      </div>
    </div>
  );
};
