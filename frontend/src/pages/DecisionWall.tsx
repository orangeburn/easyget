import React, { useEffect, useMemo, useState } from 'react';
import { Heart, Ban, ExternalLink } from 'lucide-react';
import { apiService } from '../services/api';
import { normalizeClueUrl } from '../utils/url';
import './DecisionWall.css';

interface ClueMeta {
  budget?: string;
  location?: string;
  deadline?: string;
  summary?: string;
  requirements?: string;
}

interface Clue {
  id: string;
  title: string;
  source: string;
  url: string;
  semantic_score?: number;
  veto_reason?: string;
  publish_time?: string;
  extracted_metadata?: ClueMeta;
  user_feedback?: number;
  is_archived?: boolean;
}

export const DecisionWall: React.FC = () => {
  const [clues, setClues] = useState<Clue[]>([]);
  const [loading, setLoading] = useState(true);

  const fetchClues = async () => {
    try {
      const data = await apiService.getClues();
      setClues(data);
    } catch (error) {
      console.error('Failed to fetch clues:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchClues();
    const closeStream = apiService.streamClues((item: Clue) => {
      setClues(prev => {
        const idx = prev.findIndex(c => c.id === item.id);
        if (idx >= 0) {
          const next = [...prev];
          next[idx] = { ...next[idx], ...item };
          return next;
        }
        return [item, ...prev];
      });
      setLoading(false);
    });
    return () => {
      closeStream();
    };
  }, []);

  const pendingClues = useMemo(
    () => clues.filter(c => (c.user_feedback ?? 0) === 0 && !c.is_archived),
    [clues]
  );
  const approvedCount = useMemo(
    () => clues.filter(c => (c.user_feedback ?? 0) === 1).length,
    [clues]
  );
  const ignoredCount = useMemo(
    () => clues.filter(c => (c.user_feedback ?? 0) === 2 || (c.user_feedback ?? 0) === -1).length,
    [clues]
  );

  const handleDecision = async (id: string, dir: 'left' | 'right') => {
    // 乐观更新 UI
    setClues(prev =>
      prev.map(c =>
        c.id === id ? { ...c, user_feedback: dir === 'right' ? 1 : 2 } : c
      )
    );
    try {
      await apiService.updateClueFeedback(id, dir === 'right' ? 1 : 2);
    } catch (error) {
      console.error('Failed to update feedback:', error);
      // 改回原状态
      setClues(prev =>
        prev.map(c =>
          c.id === id ? { ...c, user_feedback: 0 } : c
        )
      );
    }
  };

  return (
    <section className="decision-wall">
      <header className="wall-header">
        <div>
          <h2 className="wall-title">线索列表</h2>
          <p className="wall-subtitle">
            浏览自动搜集到的线索，快速标记您需要的项目。
          </p>
        </div>
        <div className="wall-stats">
          <div className="stat-pill">
            <span className="stat-label">待处理</span>
            <span className="stat-value">{pendingClues.length}</span>
          </div>
          <div className="stat-pill success">
            <span className="stat-label">已收藏</span>
            <span className="stat-value">{approvedCount}</span>
          </div>
          <div className="stat-pill danger">
            <span className="stat-label">已忽略</span>
            <span className="stat-value">{ignoredCount}</span>
          </div>
        </div>
      </header>

      {loading && clues.length === 0 ? (
        <div className="wall-loading">正在加载数据...</div>
      ) : pendingClues.length === 0 ? (
        <div className="wall-empty">
          <h3>目前没有待处理的线索</h3>
          <p>请确保后台爬虫任务正在运行，稍等片刻自动刷新。</p>
        </div>
      ) : (
        <div className="clue-list-container">
          <div className="clue-list">
            {pendingClues.map(clue => (
              <div key={clue.id} className="clue-list-item">
                <div className="clue-item-main">
                  <div className="clue-item-header">
                    <span className="clue-source">{clue.source}</span>
                  </div>
                  <h3 className="clue-title" title={clue.title}>{clue.title}</h3>
                  <p className="clue-snippet">
                    {clue.extracted_metadata?.summary || clue.extracted_metadata?.requirements || "内容摘要加载中/暂无内容"}
                  </p>
                  <div className="clue-item-footer">
                    <a href={normalizeClueUrl(clue.url, clue.source)} target="_blank" rel="noreferrer" className="clue-link">
                      <ExternalLink size={14} />
                      查看原文
                    </a>
                  </div>
                </div>
                <div className="clue-item-actions">
                  <button
                    className="action-btn accept"
                    onClick={() => handleDecision(clue.id, 'right')}
                    title="收藏此线索"
                  >
                    <Heart size={18} />
                    收藏
                  </button>
                  <button
                    className="action-btn reject"
                    onClick={() => handleDecision(clue.id, 'left')}
                    title="忽略此线索"
                  >
                    <Ban size={18} />
                    忽略
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </section>
  );
};
