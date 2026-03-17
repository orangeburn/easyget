import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Search, Activity } from 'lucide-react';
import { apiService } from '../../services/api';
import './StatusBar.css';

export const StatusBar: React.FC = () => {
  const [state, setState] = useState<any>(null);
  const navigate = useNavigate();

  const fetchState = async () => {
    try {
      const data = await apiService.getSystemState();
      setState(data);
    } catch (error) {
      console.error('Failed to fetch state:', error);
    }
  };

  useEffect(() => {
    fetchState();
    const interval = setInterval(fetchState, 5000); // Poll every 5s
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="status-bar">
      <div className="status-bar-inner">
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
        <div className="status-item">
          <Activity size={16} />
          <span className="label">任务状态:</span>
          <span className="value">
            {state?.is_running
              ? `${state.current_step} (${state.current_progress}%)`
              : '空闲 · 随时可启动任务'}
          </span>
        </div>
        <div className="status-info">
          <button className="config-trigger" onClick={() => navigate('/setup')}>
            任务配置
          </button>
        </div>
      </div>
    </div>
  );
};
