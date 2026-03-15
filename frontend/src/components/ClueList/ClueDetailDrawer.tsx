import React, { useState } from 'react';
import { X, ExternalLink, AlertTriangle, CheckCircle, ThumbsUp, ThumbsDown } from 'lucide-react';
import { apiService } from '../../services/api';
import './ClueDetailDrawer.css';

interface ClueDetailProps {
  clue: any;
  isOpen: boolean;
  onClose: () => void;
}

export const ClueDetailDrawer: React.FC<ClueDetailProps> = ({ clue, isOpen, onClose }) => {
  const [currentFeedback, setCurrentFeedback] = useState<number>(clue?.user_feedback || 0);
  const [isSubmitting, setIsSubmitting] = useState(false);

  if (!clue) return null;

  const metadata = clue.extracted_metadata || {};
  const isVetoed = !!clue.veto_reason || currentFeedback === -1;
  const isConfirmed = currentFeedback === 1;

  const handleFeedback = async (val: number) => {
    if (isSubmitting) return;
    setIsSubmitting(true);
    try {
      await apiService.updateClueFeedback(clue.id, val);
      setCurrentFeedback(val);
    } catch (error) {
      console.error(error);
      alert('操作失败');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className={`drawer-overlay ${isOpen ? 'open' : ''}`} onClick={onClose}>
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
                  <a href={clue.url} target="_blank" rel="noreferrer" className="clue-link" title={clue.url}>
                    {clue.url || '未知'}
                  </a>
                </span>
              </div>
            </div>
          </section>

          <section className="drawer-section">
            <h3 className="section-title">AI 深度分析</h3>
            <div className={`analysis-card ${isVetoed ? 'card-danger' : 'card-success'}`}>
              <div className="analysis-header">
                <div className="score-display">
                  <span className="score-num">{clue.match_score || 0}</span>
                  <span className="score-lbl">匹配分</span>
                </div>
                <div className="analysis-status">
                  {isConfirmed ? (
                    <><CheckCircle size={18} className="icon-success" /> <span>用户确认为：有用</span></>
                  ) : isVetoed && currentFeedback === -1 ? (
                    <><AlertTriangle size={18} className="icon-danger" /> <span>用户标记为：误报</span></>
                  ) : isVetoed ? (
                    <><AlertTriangle size={18} className="icon-danger" /> <span>建议放弃：风险预警</span></>
                  ) : (
                    <><CheckCircle size={18} className="icon-success" /> <span>匹配度高：建议跟进</span></>
                  )}
                </div>
                <div className="feedback-actions">
                  <button 
                    className={`feedback-btn ${currentFeedback === 1 ? 'active-useful' : ''}`}
                    onClick={() => handleFeedback(1)}
                    disabled={isSubmitting}
                    title="准确/有用"
                  >
                    <ThumbsUp size={16} />
                  </button>
                  <button 
                    className={`feedback-btn ${currentFeedback === -1 ? 'active-useless' : ''}`}
                    onClick={() => handleFeedback(-1)}
                    disabled={isSubmitting}
                    title="误报/无用"
                  >
                    <ThumbsDown size={16} />
                  </button>
                </div>
              </div>
              <div className="analysis-reason">
                <p><strong>评估结论：</strong></p>
                <p className="reason-text">
                  {isVetoed 
                    ? `触发一票否决：${clue.veto_reason}`
                    : metadata.analysis_summary || "该项目契合度较高，建议详细阅读招标文件并准备资料。"
                  }
                </p>
              </div>
            </div>
          </section>

          <section className="drawer-section">
            <h3 className="section-title">内容概要</h3>
            <div className="content-summary">
              <p>{metadata.summary || clue.snippet || "暂无详细摘要"}</p>
            </div>
          </section>

          {clue.full_text && (
            <section className="drawer-section">
              <h3 className="section-title">网页全文/正文</h3>
              <div className="full-text-container">
                <pre>{clue.full_text}</pre>
              </div>
            </section>
          )}
        </div>

        <footer className="drawer-footer">
          <a href={clue.url || '#'} target="_blank" rel="noreferrer" className="btn-link">
            查看原文 <ExternalLink size={16} />
          </a>
          <button className="btn-primary">设为正在跟进</button>
        </footer>
      </div>
    </div>
  );
};
