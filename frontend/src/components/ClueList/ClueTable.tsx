import React, { useEffect, useState, useMemo } from 'react';
import { Loader2, Download, Star, X, Info } from 'lucide-react';
import { ClueDetailDrawer } from './ClueDetailDrawer';
import { apiService } from '../../services/api';
import './ClueTable.css';

interface Clue {
  id: string;
  title: string;
  source: string;
  veto_reason?: string;
  user_feedback: number; // 0: none, 1: star, 2: ignore
  extracted_metadata?: {
    company_name?: string;
    location?: string;
    is_matched_core_business?: boolean;
    required_qualifications?: string[];
  };
  publish_time?: string;
}

type TabType = 'pending' | 'starred' | 'ignored' | 'filtered';

export const ClueTable: React.FC = () => {
  const [clues, setClues] = useState<Clue[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedClue, setSelectedClue] = useState<Clue | null>(null);
  const [activeTab, setActiveTab] = useState<TabType>('pending');

  const fetchClues = async () => {
    try {
      const data = await apiService.getClues();
      setClues(data as Clue[]);
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

  const handleFeedback = async (clueId: string, feedback: number) => {
    try {
      await apiService.updateClueFeedback(clueId, feedback);
      // Update local state to show change immediately
      setClues(prev => prev.map(c => c.id === clueId ? { ...c, user_feedback: feedback } : c));
    } catch (error) {
      console.error('Failed to update feedback:', error);
    }
  };

  const filteredClues = useMemo(() => {
    switch (activeTab) {
      case 'pending':
        // 未否决且未反馈
        return clues.filter(c => !c.veto_reason && c.user_feedback === 0);
      case 'starred':
        return clues.filter(c => c.user_feedback === 1);
      case 'ignored':
        return clues.filter(c => c.user_feedback === 2);
      case 'filtered':
        // 被否决且未反馈
        return clues.filter(c => c.veto_reason && c.user_feedback === 0);
      default:
        return clues;
    }
  }, [clues, activeTab]);

  if (loading && clues.length === 0) {
    return (
      <div className="loading-state">
        <Loader2 className="animate-spin" />
        <p>正在寻找新线索...</p>
      </div>
    );
  }

  const tabs: { key: TabType; label: string; count: number }[] = [
    { key: 'pending', label: '待处理', count: clues.filter(c => !c.veto_reason && c.user_feedback === 0).length },
    { key: 'starred', label: '已收藏', count: clues.filter(c => c.user_feedback === 1).length },
    { key: 'ignored', label: '已忽略', count: clues.filter(c => c.user_feedback === 2).length },
    { key: 'filtered', label: '已过滤', count: clues.filter(c => c.veto_reason && c.user_feedback === 0).length },
  ];

  // Force HMR Update - New Table Version v2
  return (
    <div className="clue-table-view-container">
      <div className="clue-list-header-new">
        <div className="tabs-container">
          {tabs.map(tab => (
            <div 
              key={tab.key} 
              className={`tab-item ${activeTab === tab.key ? 'active' : ''}`}
              onClick={() => setActiveTab(tab.key)}
            >
              <span className="tab-label">{tab.label}</span>
              {tab.count > 0 && <span className="tab-count">{tab.count}</span>}
            </div>
          ))}
        </div>
        <button className="btn-export-minimal" onClick={() => apiService.exportClues()}>
          <Download size={14} /> 导出
        </button>
      </div>

      <div className="clue-table-wrapper">
        <table className="clue-table">
          <thead>
            <tr>
              <th className="th-title">线索名称</th>
              <th className="th-source">来源</th>
              <th className="th-time">招标信息发布时间</th>
              <th className="th-actions">操作</th>
            </tr>
          </thead>
          <tbody>
            {filteredClues.length === 0 ? (
              <tr>
                <td colSpan={4} className="td-empty">
                  当前分类下暂无发现...
                </td>
              </tr>
            ) : (
              filteredClues.map(clue => (
                <tr key={clue.id} className={`tr-clue ${clue.veto_reason && activeTab !== 'filtered' ? 'row-vetoed' : ''}`}>
                  <td className="td-title" onClick={() => setSelectedClue(clue)}>
                    <div className="title-cell" title={clue.title}>
                      <span className="main-title">{clue.title}</span>
                      <span className="sub-company">{clue.extracted_metadata?.company_name || '未知机构'}</span>
                    </div>
                  </td>
                  <td className="td-source">
                    <span className="source-tag">{clue.source}</span>
                  </td>
                  <td className="td-time">
                    {clue.publish_time ? new Date(clue.publish_time).toLocaleDateString() : '-'}
                  </td>
                  <td className="td-actions">
                    <div className="actions-group">
                      <button 
                        className={`action-btn star ${clue.user_feedback === 1 ? 'active' : ''}`}
                        onClick={() => handleFeedback(clue.id, 1)}
                        title="收藏"
                      >
                        <Star size={16} fill={clue.user_feedback === 1 ? "#EAB308" : "none"} stroke="currentColor" />
                      </button>
                      <button 
                        className={`action-btn ignore ${clue.user_feedback === 2 ? 'active' : ''}`}
                        onClick={() => handleFeedback(clue.id, 2)}
                        title="忽略"
                      >
                        <X size={16} stroke="currentColor" />
                      </button>
                      <button 
                        className="action-btn detail"
                        onClick={() => setSelectedClue(clue)}
                        title="详情"
                      >
                        <Info size={16} stroke="currentColor" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      <ClueDetailDrawer 
        clue={selectedClue as any} 
        isOpen={!!selectedClue} 
        onClose={() => setSelectedClue(null)} 
      />
    </div>
  );
};
