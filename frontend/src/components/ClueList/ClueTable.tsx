import React, { useEffect, useLayoutEffect, useMemo, useRef, useState } from 'react';
import { Loader2, Download, Star, X, Info, ChevronLeft, ChevronRight, ChevronDown, CalendarDays } from 'lucide-react';
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
  created_at?: string;
}

type TabType = 'all' | 'pending' | 'starred' | 'ignored' | 'filtered';
const PAGE_SIZE = 10;

export const ClueTable: React.FC = () => {
  const [clues, setClues] = useState<Clue[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedClue, setSelectedClue] = useState<Clue | null>(null);
  const [activeTab, setActiveTab] = useState<TabType>('pending');
  const [sourceFilter, setSourceFilter] = useState<string>('all');
  const [crawlDateFilter, setCrawlDateFilter] = useState('');
  const [openFilter, setOpenFilter] = useState<'source' | 'date' | null>(null);
  const [selectionMode, setSelectionMode] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [currentPage, setCurrentPage] = useState(1);
  const [calendarMonth, setCalendarMonth] = useState(() => {
    const now = new Date();
    return new Date(now.getFullYear(), now.getMonth(), 1);
  });
  const [popoverPosition, setPopoverPosition] = useState({ top: 0, left: 0 });
  const selectAllRef = useRef<HTMLInputElement | null>(null);
  const sourceFilterRef = useRef<HTMLDivElement | null>(null);
  const dateFilterRef = useRef<HTMLDivElement | null>(null);
  const sourceTriggerRef = useRef<HTMLButtonElement | null>(null);
  const dateTriggerRef = useRef<HTMLButtonElement | null>(null);
  const sourcePopoverRef = useRef<HTMLDivElement | null>(null);
  const datePopoverRef = useRef<HTMLDivElement | null>(null);

  const getPopoverPosition = (
    trigger: HTMLElement,
    filterType: 'source' | 'date',
    popover?: HTMLDivElement | null
  ) => {
    const rect = trigger.getBoundingClientRect();
    const width = popover?.offsetWidth || (filterType === 'date' ? 292 : 192);
    const height = popover?.offsetHeight || (filterType === 'date' ? 430 : 260);
    const viewportWidth = window.innerWidth;
    const viewportHeight = window.innerHeight;
    const gap = 10;

    const fitsBelow = rect.bottom + gap + height <= viewportHeight - 12;
    const top = fitsBelow
      ? rect.bottom + gap
      : Math.max(12, rect.top - height - gap);

    const left = Math.min(
      Math.max(12, rect.left),
      Math.max(12, viewportWidth - width - 12)
    );

    return { top, left };
  };

  const openFilterPopover = (filterType: 'source' | 'date') => {
    const trigger = filterType === 'source' ? sourceTriggerRef.current : dateTriggerRef.current;
    if (trigger) {
      setPopoverPosition(getPopoverPosition(trigger, filterType));
    }
    setOpenFilter(prev => (prev === filterType ? null : filterType));
  };

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

  const tabFilteredClues = useMemo(() => {
    switch (activeTab) {
      case 'all':
        return clues;
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

  const formatDateKey = (value?: string) => {
    if (!value) return '';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return '';
    return formatLocalDate(date);
  };

  const formatLocalDate = (date: Date) => {
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    return `${year}-${month}-${day}`;
  };

  const parseDateKey = (value?: string) => {
    if (!value) return null;
    const [yearStr, monthStr, dayStr] = value.split('-');
    const year = Number(yearStr);
    const month = Number(monthStr);
    const day = Number(dayStr);
    if (!year || !month || !day) return null;
    const date = new Date(year, month - 1, day);
    if (Number.isNaN(date.getTime())) return null;
    return date;
  };

  const filteredClues = useMemo(() => {
    return tabFilteredClues.filter((clue) => {
      const matchesSource = sourceFilter === 'all' || clue.source === sourceFilter;
      const matchesDate = !crawlDateFilter || formatDateKey(clue.created_at) === crawlDateFilter;
      return matchesSource && matchesDate;
    });
  }, [tabFilteredClues, sourceFilter, crawlDateFilter]);

  const sourceOptions = useMemo(() => {
    const preferredOrder = ['定向公号', '定向站点'];
    const seen = new Set<string>();
    const options: string[] = [];

    preferredOrder.forEach((source) => {
      seen.add(source);
      options.push(source);
    });

    clues.forEach((clue) => {
      if (!clue.source || seen.has(clue.source)) return;
      seen.add(clue.source);
      options.push(clue.source);
    });
    return options;
  }, [clues]);

  const totalPages = Math.max(1, Math.ceil(filteredClues.length / PAGE_SIZE));

  useEffect(() => {
    setCurrentPage(prev => Math.min(prev, totalPages));
  }, [totalPages]);

  useEffect(() => {
    setCurrentPage(1);
  }, [activeTab, sourceFilter, crawlDateFilter]);

  useEffect(() => {
    if (!openFilter) return;

    const handlePointerDown = (event: MouseEvent) => {
      const target = event.target as Node;
      const clickedSource = sourceFilterRef.current?.contains(target);
      const clickedDate = dateFilterRef.current?.contains(target);
      const clickedSourcePopover = sourcePopoverRef.current?.contains(target);
      const clickedDatePopover = datePopoverRef.current?.contains(target);
      if (clickedSource || clickedDate || clickedSourcePopover || clickedDatePopover) return;
      setOpenFilter(null);
    };

    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setOpenFilter(null);
      }
    };

    document.addEventListener('mousedown', handlePointerDown);
    document.addEventListener('keydown', handleEscape);
    return () => {
      document.removeEventListener('mousedown', handlePointerDown);
      document.removeEventListener('keydown', handleEscape);
    };
  }, [openFilter]);

  useLayoutEffect(() => {
    if (!openFilter) return;

    const updatePosition = () => {
      const trigger =
        openFilter === 'source' ? sourceTriggerRef.current : dateTriggerRef.current;
      const popover =
        openFilter === 'source' ? sourcePopoverRef.current : datePopoverRef.current;
      if (!trigger) return;
      setPopoverPosition(getPopoverPosition(trigger, openFilter, popover));
    };

    updatePosition();
    window.addEventListener('resize', updatePosition);
    window.addEventListener('scroll', updatePosition, true);
    return () => {
      window.removeEventListener('resize', updatePosition);
      window.removeEventListener('scroll', updatePosition, true);
    };
  }, [openFilter]);

  useEffect(() => {
    if (openFilter !== 'date') return;
    const baseDate = parseDateKey(crawlDateFilter) ?? new Date();
    setCalendarMonth(new Date(baseDate.getFullYear(), baseDate.getMonth(), 1));
  }, [openFilter, crawlDateFilter]);

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

  const formatDateTime = (value?: string) => {
    if (!value) return '-';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return '-';
    return date.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  const getRelativeDate = (offsetDays: number) => {
    const date = new Date();
    date.setDate(date.getDate() + offsetDays);
    return formatLocalDate(date);
  };

  const todayDateKey = getRelativeDate(0);
  const calendarMonthLabel = calendarMonth.toLocaleDateString('zh-CN', {
    year: 'numeric',
    month: 'long'
  });
  const calendarWeekdays = ['一', '二', '三', '四', '五', '六', '日'];
  const calendarDays = useMemo(() => {
    const year = calendarMonth.getFullYear();
    const month = calendarMonth.getMonth();
    const firstDay = new Date(year, month, 1);
    const totalDays = new Date(year, month + 1, 0).getDate();
    const leadingEmpty = (firstDay.getDay() + 6) % 7;
    const days: Array<{ key: string; label?: number; dateKey?: string; empty?: boolean }> = [];

    for (let index = 0; index < leadingEmpty; index += 1) {
      days.push({ key: `empty-${index}`, empty: true });
    }

    for (let day = 1; day <= totalDays; day += 1) {
      const date = new Date(year, month, day);
      days.push({
        key: `day-${day}`,
        label: day,
        dateKey: formatLocalDate(date)
      });
    }

    return days;
  }, [calendarMonth]);

  if (loading && clues.length === 0) {
    return (
      <div className="loading-state">
        <Loader2 className="animate-spin" />
        <p>正在寻找新线索...</p>
      </div>
    );
  }

  const tabs: { key: TabType; label: string; count: number }[] = [
    { key: 'all', label: '全部', count: clues.length },
    { key: 'pending', label: '待处理', count: clues.filter(c => !c.veto_reason && c.user_feedback === 0).length },
    { key: 'starred', label: '已收藏', count: clues.filter(c => c.user_feedback === 1).length },
    { key: 'ignored', label: '已忽略', count: clues.filter(c => c.user_feedback === 2).length },
    { key: 'filtered', label: '已过滤', count: clues.filter(c => c.veto_reason && c.user_feedback === 0).length },
  ];

  const tabTips: Record<TabType, string> = {
    all: '显示系统当前已采集到的全部线索。',
    pending: '未处理且未被过滤的线索，建议优先查看。',
    starred: '已收藏的高意向线索。',
    ignored: '已被你手动忽略的线索，有效期 7 天。',
    filtered: '被 LLM 或规则判定为无效的线索，有效期 7 天。'
  };

  const renderSourcePopover = () => (
    <div
      ref={sourcePopoverRef}
      className="filter-popover filter-popover-floating"
      style={{ top: popoverPosition.top, left: popoverPosition.left }}
    >
      <button
        type="button"
        className={`filter-option ${sourceFilter === 'all' ? 'active' : ''}`}
        onClick={() => {
          setSourceFilter('all');
          setOpenFilter(null);
        }}
      >
        全部来源
      </button>
      {sourceOptions.map((source) => (
        <button
          key={source}
          type="button"
          className={`filter-option ${sourceFilter === source ? 'active' : ''}`}
          onClick={() => {
            setSourceFilter(source);
            setOpenFilter(null);
          }}
        >
          {source}
        </button>
      ))}
    </div>
  );

  const renderDatePopover = () => (
    <div
      ref={datePopoverRef}
      className="filter-popover filter-popover-floating date-filter-popover"
      style={{ top: popoverPosition.top, left: popoverPosition.left }}
    >
      <div className="filter-popover-header">
        <div className="filter-popover-title-row">
          <CalendarDays size={15} />
          <span className="filter-popover-title">按爬取日期筛选</span>
        </div>
        <p className="filter-popover-desc">只显示在所选日期抓取到的线索。</p>
      </div>
      <div className="filter-quick-actions">
        <button
          type="button"
          className={`filter-chip ${crawlDateFilter === getRelativeDate(0) ? 'active' : ''}`}
          onClick={() => setCrawlDateFilter(getRelativeDate(0))}
        >
          今天
        </button>
        <button
          type="button"
          className={`filter-chip ${crawlDateFilter === getRelativeDate(-1) ? 'active' : ''}`}
          onClick={() => setCrawlDateFilter(getRelativeDate(-1))}
        >
          昨天
        </button>
      </div>
      <div className="calendar-panel">
        <div className="calendar-toolbar">
          <button
            type="button"
            className="calendar-nav-btn"
            onClick={() =>
              setCalendarMonth((prev) => new Date(prev.getFullYear(), prev.getMonth() - 1, 1))
            }
            aria-label="上个月"
          >
            <ChevronLeft size={14} />
          </button>
          <div className="calendar-month-label">{calendarMonthLabel}</div>
          <button
            type="button"
            className="calendar-nav-btn"
            onClick={() =>
              setCalendarMonth((prev) => new Date(prev.getFullYear(), prev.getMonth() + 1, 1))
            }
            aria-label="下个月"
          >
            <ChevronRight size={14} />
          </button>
        </div>
        <div className="calendar-weekdays">
          {calendarWeekdays.map((weekday) => (
            <span key={weekday} className="calendar-weekday">
              {weekday}
            </span>
          ))}
        </div>
        <div className="calendar-grid">
          {calendarDays.map((day) =>
            day.empty ? (
              <span key={day.key} className="calendar-day-empty" />
            ) : (
              <button
                key={day.key}
                type="button"
                className={`calendar-day-btn ${crawlDateFilter === day.dateKey ? 'active' : ''} ${todayDateKey === day.dateKey ? 'today' : ''}`}
                onClick={() => setCrawlDateFilter(day.dateKey || '')}
              >
                {day.label}
              </button>
            )
          )}
        </div>
      </div>
      <div className="filter-popover-actions">
        <button
          type="button"
          className="filter-action-btn"
          onClick={() => {
            setCrawlDateFilter('');
            setOpenFilter(null);
          }}
        >
          清除
        </button>
        <button
          type="button"
          className="filter-action-btn primary"
          onClick={() => setOpenFilter(null)}
        >
          完成
        </button>
      </div>
    </div>
  );

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
              <th className="th-source">
                <div className="th-filter-wrap" ref={sourceFilterRef}>
                  <button
                    ref={sourceTriggerRef}
                    type="button"
                    className={`th-filter-trigger ${openFilter === 'source' ? 'open' : ''} ${sourceFilter !== 'all' ? 'active' : ''}`}
                    onClick={() => openFilterPopover('source')}
                  >
                    <span className="th-filter-label">来源</span>
                    <ChevronDown size={14} />
                  </button>
                </div>
              </th>
              <th className="th-time">招标信息发布时间</th>
              <th className="th-time">
                <div className="th-filter-wrap" ref={dateFilterRef}>
                  <button
                    ref={dateTriggerRef}
                    type="button"
                    className={`th-filter-trigger ${openFilter === 'date' ? 'open' : ''} ${crawlDateFilter ? 'active' : ''}`}
                    onClick={() => openFilterPopover('date')}
                  >
                    <span className="th-filter-label">爬取时间</span>
                    <ChevronDown size={14} />
                  </button>
                </div>
              </th>
              <th className="th-actions">操作</th>
            </tr>
          </thead>
          <tbody>
            {filteredClues.length === 0 ? (
              <tr>
                <td colSpan={selectionMode ? 6 : 5} className="td-empty">
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
                    {formatDateTime(clue.publish_time)}
                  </td>
                  <td className="td-time td-crawled-time">
                    {formatDateTime(clue.created_at)}
                  </td>
                  <td className="td-actions">
                    <div className="actions-group">
                      <button 
                        type="button"
                        className={`action-btn star ${clue.user_feedback === 1 ? 'active' : ''}`}
                        onClick={(event) => {
                          event.stopPropagation();
                          handleFeedback(clue.id, 1);
                        }}
                        title="收藏"
                      >
                        <Star size={16} fill={clue.user_feedback === 1 ? "#EAB308" : "none"} stroke="currentColor" />
                      </button>
                      <button 
                        type="button"
                        className={`action-btn ignore ${clue.user_feedback === 2 ? 'active' : ''}`}
                        onClick={(event) => {
                          event.stopPropagation();
                          handleFeedback(clue.id, 2);
                        }}
                        title="忽略"
                      >
                        <X size={16} stroke="currentColor" />
                      </button>
                      <button 
                        type="button"
                        className="action-btn detail"
                        onClick={(event) => {
                          event.stopPropagation();
                          setSelectedClue(clue);
                        }}
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

      {openFilter === 'source' && renderSourcePopover()}
      {openFilter === 'date' && renderDatePopover()}

      {filteredClues.length > 0 && (
        <div className="table-pagination">
          <div className="pagination-summary">
            当前显示 {pageStart}-{pageEnd} / 共 {filteredClues.length} 条
          </div>
          <div className="pagination-controls">
            <button
              className="pagination-btn page-jump"
              onClick={() => setCurrentPage(1)}
              disabled={currentPage === 1}
              title="首页"
            >
              首页
            </button>
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
