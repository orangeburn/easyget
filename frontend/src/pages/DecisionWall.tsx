import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Heart, Ban, ArrowLeftRight, RefreshCw } from 'lucide-react';
import { apiService } from '../services/api';
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
  match_score?: number;
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
  const [dragging, setDragging] = useState(false);
  const [offset, setOffset] = useState({ x: 0, y: 0 });
  const [swipeDir, setSwipeDir] = useState<'left' | 'right' | null>(null);
  const startRef = useRef({ x: 0, y: 0 });

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
    () => clues.filter(c => (c.user_feedback ?? 0) === -1).length,
    [clues]
  );

  const current = pendingClues[0];
  const next = pendingClues[1];

  const handleDecision = async (dir: 'left' | 'right') => {
    if (!current) {
      return;
    }
    setSwipeDir(dir);
    try {
      await apiService.updateClueFeedback(current.id, dir === 'right' ? 1 : -1);
    } catch (error) {
      console.error('Failed to update feedback:', error);
    }
    window.setTimeout(() => {
      setClues(prev =>
        prev.map(c =>
          c.id === current.id ? { ...c, user_feedback: dir === 'right' ? 1 : -1 } : c
        )
      );
      setSwipeDir(null);
      setOffset({ x: 0, y: 0 });
    }, 220);
  };

  const handleSkip = () => {
    if (!current) {
      return;
    }
    setClues(prev => {
      const rest = prev.filter(c => c.id !== current.id);
      return [...rest, current];
    });
    setOffset({ x: 0, y: 0 });
  };

  const onPointerDown = (event: React.PointerEvent) => {
    if (!current) {
      return;
    }
    setDragging(true);
    startRef.current = { x: event.clientX, y: event.clientY };
    (event.target as HTMLElement).setPointerCapture(event.pointerId);
  };

  const onPointerMove = (event: React.PointerEvent) => {
    if (!dragging) {
      return;
    }
    const dx = event.clientX - startRef.current.x;
    const dy = event.clientY - startRef.current.y;
    setOffset({ x: dx, y: dy });
  };

  const onPointerUp = () => {
    if (!dragging) {
      return;
    }
    setDragging(false);
    if (offset.x > 130) {
      handleDecision('right');
      return;
    }
    if (offset.x < -130) {
      handleDecision('left');
      return;
    }
    setOffset({ x: 0, y: 0 });
  };

  const rotation = Math.min(18, Math.max(-18, offset.x / 12));
  const swipeHint = offset.x > 40 ? 'right' : offset.x < -40 ? 'left' : null;

  return (
    <section className="decision-wall">
      <header className="wall-header">
        <div>
          <div className="wall-eyebrow">判定墙</div>
          <h2 className="wall-title">左右滑动，快速标记线索价值</h2>
          <p className="wall-subtitle">
            收藏与忽略会进入反馈闭环，影响后续评分权重。
          </p>
        </div>
        <div className="wall-stats">
          <div className="stat-pill">
            <span className="stat-label">待判定</span>
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

      {loading ? (
        <div className="wall-loading">加载中...</div>
      ) : !current ? (
        <div className="wall-empty">
          <h3>当前没有需要判定的线索</h3>
          <p>稍后再来，或回到列表查看全部线索。</p>
        </div>
      ) : (
        <div className="wall-stage">
          <div className="wall-stack">
            {next && (
              <article className="wall-card ghost">
                <div className="card-header">
                  <span className="card-source">{next.source}</span>
                  <span className="card-score">评分 {next.match_score ?? 0}</span>
                </div>
                <h3 className="card-title">{next.title}</h3>
                <p className="card-summary">{next.extracted_metadata?.summary || '暂无摘要'}</p>
              </article>
            )}
            <article
              className={`wall-card active ${swipeDir ? `swipe-${swipeDir}` : ''}`}
              onPointerDown={onPointerDown}
              onPointerMove={onPointerMove}
              onPointerUp={onPointerUp}
              onPointerCancel={onPointerUp}
              style={{
                transform: `translate3d(${offset.x}px, ${offset.y}px, 0) rotate(${rotation}deg)`,
                transition: dragging ? 'none' : 'transform 0.2s ease'
              }}
            >
              <div className={`swipe-badge left ${swipeHint === 'left' ? 'show' : ''}`}>忽略</div>
              <div className={`swipe-badge right ${swipeHint === 'right' ? 'show' : ''}`}>收藏</div>
              <div className="card-header">
                <span className="card-source">{current.source}</span>
                <span className="card-score">评分 {current.match_score ?? 0}</span>
              </div>
              <h3 className="card-title">{current.title}</h3>
              <div className="card-tags">
                <span className="tag">语义 {current.semantic_score ?? 0}</span>
                <span className="tag">{current.extracted_metadata?.location || '全国'}</span>
                {current.extracted_metadata?.budget && (
                  <span className="tag">{current.extracted_metadata.budget}</span>
                )}
                {current.extracted_metadata?.deadline && (
                  <span className="tag">截止 {current.extracted_metadata.deadline}</span>
                )}
              </div>
              {current.veto_reason && (
                <div className="card-veto">一票否决：{current.veto_reason}</div>
              )}
              <p className="card-summary">{current.extracted_metadata?.summary || '暂无摘要'}</p>
              {current.extracted_metadata?.requirements && (
                <div className="card-requirements">
                  <span>准入要求</span>
                  <p>{current.extracted_metadata.requirements}</p>
                </div>
              )}
              {current.url && (
                <a className="card-link" href={current.url} target="_blank" rel="noreferrer">
                  查看原文
                </a>
              )}
            </article>
          </div>

          <div className="wall-actions">
            <button className="action-btn ghost" onClick={handleSkip}>
              <RefreshCw size={16} />
              暂缓
            </button>
            <button className="action-btn reject" onClick={() => handleDecision('left')}>
              <Ban size={16} />
              忽略
            </button>
            <button className="action-btn accept" onClick={() => handleDecision('right')}>
              <Heart size={16} />
              收藏
            </button>
          </div>

          <div className="wall-hint">
            <ArrowLeftRight size={16} />
            拖拽卡片左右滑动即可快速判定
          </div>
        </div>
      )}
    </section>
  );
};
