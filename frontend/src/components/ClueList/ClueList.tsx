import React, { useEffect, useState } from 'react';
import { ChevronRight, Loader2, Download } from 'lucide-react';
import { ClueDetailDrawer } from './ClueDetailDrawer';
import { apiService } from '../../services/api';
import './ClueList.css';

interface Clue {
  id: string;
  title: string;
  source: string;
  match_score: number;
  veto_reason?: string;
  extracted_metadata?: {
    company_name?: string;
    location?: string;
    is_matched_core_business?: boolean;
    required_qualifications?: string[];
  };
  publish_time?: string;
}

export const ClueList: React.FC = () => {
  const [clues, setClues] = useState<Clue[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedClue, setSelectedClue] = useState<Clue | null>(null);

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
    const interval = setInterval(fetchClues, 10000); // Poll every 10s
    return () => clearInterval(interval);
  }, []);

  if (loading && clues.length === 0) {
    return (
      <div className="loading-state">
        <Loader2 className="animate-spin" />
        <p>正在寻找新线索...</p>
      </div>
    );
  }

  return (
    <div className="clue-list-wrapper">
      <div className="clue-list-header">
        <h3 className="list-title">发现线索 ({clues.length})</h3>
        <button className="btn-export" onClick={() => apiService.exportClues()}>
          <Download size={16} /> 导出 CSV
        </button>
      </div>

      {clues.length === 0 ? (
        <div className="empty-state">
          <p>暂无发现，采集器正在努力工作中...</p>
        </div>
      ) : (
        clues.map(clue => (
          <div 
            key={clue.id} 
            className={`clue-row simplified ${clue.veto_reason ? 'vetoed' : ''}`}
            onClick={() => setSelectedClue(clue)}
          >
            <div className="clue-content">
              <h4 className="clue-title">{clue.title}</h4>
              <div className="clue-primary-meta">
                <span className="company-name">{clue.extracted_metadata?.company_name || '未知机构'}</span>
                <span className="dot">•</span>
                <span className="location-tag">{clue.extracted_metadata?.location || '全国'}</span>
              </div>
              <div className="clue-secondary-meta">
                <span className="meta-tag">{clue.source}</span>
                {clue.publish_time && <span className="meta-time">{new Date(clue.publish_time).toLocaleString()}</span>}
              </div>
            </div>
            
            <div className="clue-match-stats">
              <div className="stat-box match">
                <span className="stat-num">{clue.match_score || 0}</span>
                <span className="stat-label">AI 评分</span>
              </div>
              {clue.veto_reason && (
                <div className="stat-box mismatch">
                  <span className="stat-num">!</span>
                  <span className="stat-label">一票否决</span>
                </div>
              )}
              <ChevronRight size={20} className="arrow-icon" />
            </div>
          </div>
        ))
      )}

      <ClueDetailDrawer 
        clue={selectedClue as any} 
        isOpen={!!selectedClue} 
        onClose={() => setSelectedClue(null)} 
      />
    </div>
  );
};
