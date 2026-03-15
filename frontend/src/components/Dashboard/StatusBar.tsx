import React, { useEffect, useState } from 'react';
import { Search, Activity, Clock } from 'lucide-react';
import { apiService } from '../../services/api';
import './StatusBar.css';

export const StatusBar: React.FC = () => {
  const [state, setState] = useState<any>(null);

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
            {state?.company_name ? `全网自动采集 · ${state.company_name}` : '未配置画像'}
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
          <div className="info-badge">
            <Clock size={14} />
            <span>实时同步中</span>
          </div>
          <button className="config-trigger" onClick={() => window.location.href = '/setup'}>
            重新配置
          </button>
        </div>
      </div>
    </div>
  );
};
