import React from 'react';
import { useNavigate } from 'react-router-dom';
import { ClueList } from '../ClueList/ClueList';
import './MainGrid.css';

export const MainGrid: React.FC = () => {
  const navigate = useNavigate();

  return (
    <div className="main-grid-container simplified">
      <div className="clue-list-section">
        <div className="section-header">
          <h2 className="section-title-large">招标线索发现</h2>
          <div className="filter-actions">
            <button className="filter-btn wall-entry" onClick={() => navigate('/dashboard/wall')}>
              判定墙
            </button>
            <button className="filter-btn active">最新发布</button>
            <button className="filter-btn">评分优先</button>
          </div>
        </div>

        <div className="wall-banner">
          <div className="wall-banner-copy">
            <span className="banner-kicker">判定墙</span>
            <h3>左右滑动，三秒判定一个线索</h3>
            <p>收藏与忽略会直接写入反馈，形成评分闭环。</p>
          </div>
          <div className="wall-banner-actions">
            <button className="banner-btn primary" onClick={() => navigate('/dashboard/wall')}>
              进入判定墙
            </button>
            <button className="banner-btn ghost" onClick={() => navigate('/dashboard/clues')}>
              查看列表
            </button>
          </div>
        </div>
        
        <ClueList />
      </div>
    </div>
  );
};
