import { useEffect, useState } from 'react';
import { X, ExternalLink, AlertTriangle } from 'lucide-react';
import { normalizeClueUrl } from '../../utils/url';
import './ClueDetailDrawer.css';

interface ClueDetailProps {
  clue: any;
  isOpen: boolean;
  onClose: () => void;
  onFeedback?: (clueId: string, feedback: number) => Promise<void> | void;
}

export const ClueDetailDrawer: React.FC<ClueDetailProps> = ({ clue, isOpen, onClose, onFeedback }) => {
  if (!clue) return null;

  const metadata = clue.extracted_metadata || {};
  const [isSubmitting, setIsSubmitting] = useState(false);

  useEffect(() => {
    if (!isOpen) {
      setIsSubmitting(false);
    }
  }, [isOpen]);

  const handleCopyTitle = () => {
    if (!clue.title) return;
    navigator.clipboard.writeText(clue.title);
    alert('标题已复制，请在微信中搜索');
  };

  const handleFavorite = async () => {
    if (!clue?.id || !onFeedback || isSubmitting || clue.user_feedback === 1) {
      return;
    }
    try {
      setIsSubmitting(true);
      await onFeedback(clue.id, 1);
    } catch {
      // Error feedback is surfaced by the parent handler; keep the drawer open.
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <>
      <div className={`drawer-overlay ${isOpen ? 'open' : ''}`} onClick={onClose} />
      <div className={`drawer-content ${isOpen ? 'open' : ''}`} onClick={e => e.stopPropagation()}>
        <header className="drawer-header">
          <button className="close-btn" onClick={onClose}><X size={20} /></button>
          <div className="header-main">
            <h2 className="drawer-title">{clue.title}</h2>
            <div className="drawer-subtitle">
              <span>{clue.source}</span>
              <span className="dot">•</span>
              <span>{clue.publish_time ? new Date(clue.publish_time).toLocaleString() : '未知时间'}</span>
            </div>
            {clue.source === 'wechat' && (
              <div className="header-actions-inline">
                <button className="btn-copy-title-header" onClick={handleCopyTitle}>
                  复制标题并在微信搜索
                </button>
              </div>
            )}
          </div>
        </header>

        <div className="drawer-body">
          <section className="drawer-section">
            <h3 className="section-title">核心信息</h3>
            <div className="info-grid">
              <div className="info-item">
                <span className="info-label">项目金额</span>
                <span className="info-value highlight">{metadata.budget || '未提及'}</span>
              </div>
              <div className="info-item">
                <span className="info-label">项目地点</span>
                <span className="info-value">{metadata.location || '全国'}</span>
              </div>
              <div className="info-item">
                <span className="info-label">截止时间</span>
                <span className="info-value">{metadata.deadline || '未提及'}</span>
              </div>
              <div className="info-item info-item-full">
                <span className="info-label">来源链接</span>
                <span className="info-value">
                  <a
                    href={normalizeClueUrl(clue.url, clue.source)}
                    target="_blank"
                    rel="noreferrer"
                    className="clue-link"
                    title={clue.url}
                  >
                    {clue.url || '未知'}
                  </a>
                  {clue.source === 'wechat' && (
                    <div className="link-hint">
                      <AlertTriangle size={12} /> 链接可能失效，已为您抓取全文展示在下方
                    </div>
                  )}
                </span>
              </div>
            </div>
          </section>

          <section className="drawer-section">
            <h3 className="section-title">内容概要</h3>
            <div className="content-summary">
              <p>{metadata.summary || clue.snippet || "暂无详细摘要"}</p>
            </div>
          </section>

          <section className="drawer-section">
            <h3 className="section-title">网页全文/正文</h3>
            <div className="full-text-container fancy-scroll">
              <div className="full-text-content">
                {(() => {
                  const fullText = clue.full_text || clue.markdown_text || '';
                  if (!fullText) {
                    return <p>暂无正文</p>;
                  }
                  return fullText.split('\n').map((line: string, i: number) => (
                    <p key={i}>{line}</p>
                  ));
                })()}
              </div>
            </div>
          </section>
        </div>

        <footer className="drawer-footer">
          <a href={normalizeClueUrl(clue.url, clue.source) || '#'} target="_blank" rel="noreferrer" className="btn-link">
            查看原文 <ExternalLink size={16} />
          </a>
          <button
            className={`btn-primary ${clue.user_feedback === 1 ? 'is-active' : ''}`}
            onClick={handleFavorite}
            disabled={isSubmitting || clue.user_feedback === 1}
          >
            {clue.user_feedback === 1 ? '已收藏' : isSubmitting ? '收藏中...' : '收藏此线索'}
          </button>
        </footer>
      </div>
    </>
  );
};
