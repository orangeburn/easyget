import React, { useEffect, useMemo, useRef, useState } from 'react';
import { Loader2, Download, Star, X, Info, ChevronLeft, ChevronRight } from 'lucide-react';
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
const PAGE_SIZE = 10;

export const ClueTable: React.FC = () => {
  const [clues, setClues] = useState<Clue[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedClue, setSelectedClue] = useState<Clue | null>(null);
  const [activeTab, setActiveTab] = useState<TabType>('pending');
  const [selectionMode, setSelectionMode] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [currentPage, setCurrentPage] = useState(1);
  const selectAllRef = useRef<HTMLInputElement | null>(null);

  const cacheKey = 'easyget_clues_cache';

  const loadCachedClues = () => {
    try {
      const raw = localStorage.getItem(cacheKey);
      if (!raw) return null;
      const parsed = JSON.parse(raw);
      return Array.isArray(parsed) ? (parsed as Clue[]) : null;
    } catch {
      return null;
    }
  };

  const persistClues = (data: Clue[]) => {
    try {
      localStorage.setItem(cacheKey, JSON.stringify(data));
    } catch {
      // ignore storage errors
    }
  };

  const fetchClues = async () => {
    try {
      const data = await apiService.getClues();
      const list = Array.isArray(data) ? (data as Clue[]) : [];
      if (list.length > 0) {
        setClues(list);
        persistClues(list);
      } else {
        const cached = loadCachedClues();
        if (cached && cached.length > 0) {
          setClues(cached);
        } else {
          setClues([]);
        }
      }
    } catch (error) {
      console.error('Failed to fetch clues:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    const cached = loadCachedClues();
    if (cached && cached.length > 0) {
      setClues(cached);
      setLoading(false);
    }
    fetchClues();
    const closeStream = apiService.streamClues((item: Clue) => {
      if (!item || !item.id) return;
      setClues(prev => {
        const idx = prev.findIndex(c => c.id === item.id);
        if (idx >= 0) {
          const next = [...prev];
          next[idx] = { ...next[idx], ...item };
          persistClues(next);
          return next;
        }
        const next = [item, ...prev];
        persistClues(next);
        return next;
      });
      setLoading(false);
    });
    return () => {
      closeStream();
    };
  }, []);

  const handleFeedback = async (clueId: string, feedback: number) => {
    let previousClue: Clue | undefined;
    setClues(prev => {
      previousClue = prev.find(c => c.id === clueId);
      const next = prev.map(c => c.id === clueId ? { ...c, user_feedback: feedback } : c);
      persistClues(next);
      return next;
    });
    setSelectedClue(prev => prev && prev.id === clueId ? { ...prev, user_feedback: feedback } : prev);

    try {
      await apiService.updateClueFeedback(clueId, feedback);
    } catch (error) {
      console.error('Failed to update feedback:', error);
      if (previousClue) {
        setClues(prev => {
          const next = prev.map(c => c.id === clueId ? previousClue as Clue : c);
          persistClues(next);
          return next;
        });
        setSelectedClue(prev => prev && prev.id === clueId ? previousClue as Clue : prev);
      }
      alert('操作失败，请检查后端服务');
      throw error;
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

  const totalPages = Math.max(1, Math.ceil(filteredClues.length / PAGE_SIZE));

  useEffect(() => {
    setCurrentPage(prev => Math.min(prev, totalPages));
  }, [totalPages]);

  useEffect(() => {
    setCurrentPage(1);
  }, [activeTab]);

  const paginatedClues = useMemo(() => {
    const start = (currentPage - 1) * PAGE_SIZE;
    return filteredClues.slice(start, start + PAGE_SIZE);
  }, [filteredClues, currentPage]);

  const scopedIds = useMemo(() => filteredClues.map(c => c.id), [filteredClues]);
  const pageIds = useMemo(() => paginatedClues.map(c => c.id), [paginatedClues]);
  const allSelected = selectionMode && pageIds.length > 0 && pageIds.every(id => selectedIds.has(id));
  const someSelected = selectionMode && pageIds.some(id => selectedIds.has(id));
  const selectedCount = selectedIds.size;
  const pageStart = filteredClues.length === 0 ? 0 : (currentPage - 1) * PAGE_SIZE + 1;
  const pageEnd = Math.min(currentPage * PAGE_SIZE, filteredClues.length);
  const paginationWindow = useMemo(() => {
    const start = Math.max(1, currentPage - 2);
    const end = Math.min(totalPages, start + 4);
    const adjustedStart = Math.max(1, end - 4);
    return Array.from({ length: end - adjustedStart + 1 }, (_, idx) => adjustedStart + idx);
  }, [currentPage, totalPages]);

  useEffect(() => {
    if (selectAllRef.current) {
      selectAllRef.current.indeterminate = !allSelected && someSelected;
    }
  }, [allSelected, someSelected]);

  useEffect(() => {
    if (!selectionMode) return;
    const allowed = new Set(scopedIds);
    setSelectedIds(prev => new Set([...prev].filter(id => allowed.has(id))));
  }, [selectionMode, scopedIds]);

  useEffect(() => {
    setSelectionMode(false);
    setSelectedIds(new Set());
  }, [activeTab]);

  const toggleSelectAll = () => {
    if (!selectionMode) return;
    if (allSelected) {
      setSelectedIds(prev => {
        const next = new Set(prev);
        pageIds.forEach(id => next.delete(id));
        return next;
      });
      return;
    }
    setSelectedIds(prev => {
      const next = new Set(prev);
      pageIds.forEach(id => next.add(id));
      return next;
    });
  };

  const toggleSelectOne = (id: string) => {
    if (!selectionMode) return;
    setSelectedIds(prev => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const handleExportClick = async () => {
    if (!selectionMode) {
      setSelectionMode(true);
      return;
    }
    if (selectedIds.size === 0) return;
    try {
      await apiService.exportCluesSelected(Array.from(selectedIds));
      setSelectionMode(false);
      setSelectedIds(new Set());
    } catch (error) {
      console.error('Failed to export selected clues:', error);
      alert('导出失败，请检查后端服务');
    }
  };

  const cancelSelectionMode = () => {
    setSelectionMode(false);
    setSelectedIds(new Set());
  };

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

  const tabTips: Record<TabType, string> = {
    pending: '未处理且未被过滤的线索，建议优先查看。',
    starred: '已收藏的高意向线索。',
    ignored: '已被你手动忽略的线索，有效期 7 天。',
    filtered: '被 LLM 或规则判定为无效的线索，有效期 7 天。'
  };

  // Force HMR Update - New Table Version v2
  return (
    <div className="clue-table-view-container">
      <div className="clue-list-header-new">
        <div className="header-primary">
          <div className="tabs-container">
            {tabs.map(tab => (
              <div 
                key={tab.key} 
                className={`tab-item ${activeTab === tab.key ? 'active' : ''}`}
                onClick={() => setActiveTab(tab.key)}
                title={tabTips[tab.key]}
              >
                <span className="tab-label">{tab.label}</span>
                {tab.count > 0 && <span className="tab-count">{tab.count}</span>}
              </div>
            ))}
          </div>
          {selectionMode && (
            <div className="selection-status">
              已选 <strong>{selectedCount}</strong> 项，翻页后保留勾选
            </div>
          )}
        </div>
        <div className="header-actions">
          {selectionMode && (
            <button className="btn-secondary-minimal" onClick={cancelSelectionMode}>
              取消选择
            </button>
          )}
          <button
            className="btn-export-minimal"
            onClick={handleExportClick}
            disabled={selectionMode && selectedCount === 0}
            title={selectionMode ? '下载当前已勾选线索（支持跨页）' : '进入导出选择模式'}
          >
            <Download size={14} /> {selectionMode ? `下载已选 (${selectedCount})` : '导出'}
          </button>
        </div>
      </div>

      <div className="clue-table-wrapper">
        <table className="clue-table">
          <thead>
            <tr>
              {selectionMode && (
                <th className="th-select">
                  <input
                    ref={selectAllRef}
                    type="checkbox"
                    className="select-checkbox"
                    checked={allSelected}
                    onChange={toggleSelectAll}
                  />
                </th>
              )}
              <th className="th-title">线索名称</th>
              <th className="th-source">来源</th>
              <th className="th-time">招标信息发布时间</th>
              <th className="th-actions">操作</th>
            </tr>
          </thead>
          <tbody>
            {filteredClues.length === 0 ? (
              <tr>
                <td colSpan={selectionMode ? 5 : 4} className="td-empty">
                  当前分类下暂无发现...
                </td>
              </tr>
            ) : (
              paginatedClues.map(clue => (
                <tr key={clue.id} className={`tr-clue ${clue.veto_reason && activeTab !== 'filtered' ? 'row-vetoed' : ''}`}>
                  {selectionMode && (
                    <td className="td-select">
                      <input
                        type="checkbox"
                        className="select-checkbox"
                        checked={selectedIds.has(clue.id)}
                        onChange={() => toggleSelectOne(clue.id)}
                      />
                    </td>
                  )}
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

      {filteredClues.length > 0 && (
        <div className="table-pagination">
          <div className="pagination-summary">
            当前显示 {pageStart}-{pageEnd} / 共 {filteredClues.length} 条
          </div>
          <div className="pagination-controls">
            <button
              className="pagination-btn"
              onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
              disabled={currentPage === 1}
              title="上一页"
            >
              <ChevronLeft size={14} />
            </button>
            {paginationWindow.map(page => (
              <button
                key={page}
                className={`pagination-btn page-number ${currentPage === page ? 'active' : ''}`}
                onClick={() => setCurrentPage(page)}
              >
                {page}
              </button>
            ))}
            <button
              className="pagination-btn"
              onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
              disabled={currentPage === totalPages}
              title="下一页"
            >
              <ChevronRight size={14} />
            </button>
          </div>
        </div>
      )}

      <ClueDetailDrawer 
        clue={selectedClue as any} 
        isOpen={!!selectedClue} 
        onClose={() => setSelectedClue(null)}
        onFeedback={handleFeedback}
      />
    </div>
  );
};
