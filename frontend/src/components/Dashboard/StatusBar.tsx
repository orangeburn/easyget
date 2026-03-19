import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, Activity } from 'lucide-react';
import { apiService } from '../../services/api';
import './StatusBar.css';

export const StatusBar: React.FC = () => {
  const [state, setState] = useState<any>(null);
  const [isTriggering, setIsTriggering] = useState(false);
  const navigate = useNavigate();

  const fetchState = async () => {
    try {
      const data = await apiService.getSystemState();
      setState(data);
      return data;
    } catch (error) {
      console.error('Failed to fetch state:', error);
      return null;
    }
  };

  useEffect(() => {
    fetchState();
    const interval = setInterval(fetchState, 5000); // Poll every 5s
    return () => clearInterval(interval);
  }, []);

  const normalizeStatusText = (text: string, maxLen: number = 80) => {
    const normalized = text.replace(/\s+/g, ' ').trim();
    if (normalized.length <= maxLen) return normalized;
    return `${normalized.slice(0, maxLen)}...`;
  };

  const rawTaskStatus = state?.is_running
    ? `${state.current_step || ''} (${state.current_progress ?? 0}%)`
    : state?.is_paused
    ? '已暂停 · 可继续开始'
    : '空闲 · 随时可启动任务';
  const taskStatusText = normalizeStatusText(rawTaskStatus, 80);

  const handleImmediateRun = async () => {
    if (isTriggering) return;
    if (state?.is_running) {
      try {
        setIsTriggering(true);
        await apiService.stopTask();
        setState((prev: any) =>
          prev
            ? {
                ...prev,
                is_running: false,
                is_paused: true,
                current_progress: 0,
                current_step: '已暂停'
              }
            : prev
        );
        await fetchState();
      } catch (error) {
        console.error('Pause task failed:', error);
        const data = await fetchState();
        if (data?.is_running) {
          alert('暂停失败，请检查后端服务');
        }
      } finally {
        setIsTriggering(false);
      }
      return;
    }
    if (!state?.has_constraint) {
      alert('请先完成任务配置，再执行爬虫任务。');
      navigate('/dashboard/settings');
      return;
    }

    const constraint = {
      company_name: state?.company_name || '手动任务',
      core_business: state?.search_keywords
        ? String(state.search_keywords).split(/[,，\s]+/).filter(Boolean)
        : [],
      wechat_accounts: state?.wechat_accounts
        ? String(state.wechat_accounts).split('\n').map((s: string) => s.trim()).filter(Boolean)
        : [],
      custom_urls: state?.target_urls
        ? String(state.target_urls).split('\n').map((s: string) => s.trim()).filter(Boolean)
        : [],
      qualifications: [],
      geography_limits: state?.geography_limits || [],
      financial_thresholds: state?.financial_thresholds || [],
      other_constraints: state?.other_constraints || [],
      scan_frequency: Number(state?.scan_frequency) || 30
    };

    const strategy = {
      search_keywords: state?.search_keywords || '',
      target_urls: constraint.custom_urls,
      wechat_accounts: constraint.wechat_accounts,
      scan_frequency: constraint.scan_frequency
    };

    setIsTriggering(true);
    setState((prev: any) =>
      prev
        ? {
            ...prev,
            is_running: true,
            is_paused: false,
            current_progress: 5,
            current_step: '正在启动抓取任务...'
          }
        : prev
    );
    try {
      await apiService.activateTask(constraint, strategy);
      fetchState();
    } catch (error) {
      console.error('Immediate run failed:', error);
      alert('任务启动失败，请检查后端服务');
      fetchState();
    } finally {
      setIsTriggering(false);
    }
  };

  return (
    <div className="status-bar">
      <div className="status-bar-inner">
        <div className="status-brand" aria-label="Easyget">
          <img
            className="status-brand-mark"
            src={`${import.meta.env.BASE_URL}logo.png`}
            alt="Easyget logo"
          />
          <span className="status-brand-name">Easyget</span>
        </div>
        <div className="status-item">
          <Search size={16} />
          <span className="label">当前策略:</span>
          <span className="value">
            {(() => {
              if (!state) return '未配置画像';
              const tags: string[] = [];
              if (state.search_keywords && String(state.search_keywords).trim()) {
                tags.push('全网搜索');
              }
              if (state.target_urls && String(state.target_urls).trim()) {
                const count = String(state.target_urls).split('\n').filter(Boolean).length;
                tags.push(`定向站点(${count})`);
              }
              if (state.wechat_accounts && String(state.wechat_accounts).trim()) {
                const count = String(state.wechat_accounts).split('\n').filter(Boolean).length;
                tags.push(`公众号(${count})`);
              }
              if (tags.length === 0) return '未配置画像';
              return tags.join(' · ');
            })()}
          </span>
        </div>
        <div className="status-item task-status">
          <Activity size={16} />
          <span className="label">任务状态:</span>
          <span className="value" title={rawTaskStatus}>
            {taskStatusText}
          </span>
        </div>
        <div className="status-actions">
          <button
            className={`run-trigger ${state?.is_running ? 'is-running' : 'is-idle'}`}
            onClick={handleImmediateRun}
            disabled={!state?.has_constraint || isTriggering}
            title={
              !state?.has_constraint
                ? '请先完成任务配置'
                : state?.is_running
                ? '暂停任务'
                : '开始任务'
            }
          >
            {isTriggering ? '处理中...' : state?.is_running ? '暂停' : '开始'}
          </button>
        </div>
        <div className="status-info">
          <button className="config-trigger" onClick={() => navigate('/dashboard/settings')}>
            任务配置
          </button>
          <button className="config-trigger settings-trigger" onClick={() => navigate('/dashboard/system-settings')}>
            系统设置
          </button>
        </div>
      </div>
    </div>
  );
};
