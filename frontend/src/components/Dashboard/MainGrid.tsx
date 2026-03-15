import React from 'react';
import { ClueList } from '../ClueList/ClueList';
import './MainGrid.css';

export const MainGrid: React.FC = () => {
  return (
    <div className="main-grid-container simplified">
      <div className="clue-list-section">
        <div className="section-header">
          <h2 className="section-title-large">招标线索发现</h2>
          <div className="filter-actions">
            <button className="filter-btn active">最新发布</button>
            <button className="filter-btn">评分优先</button>
          </div>
        </div>
        
        <ClueList />
      </div>
    </div>
  );
};
