import React, { useState, useEffect } from 'react';
import { apiService } from '../services/api';
import './SetupWizard.css';
import { Check, Search, Globe, MessageCircle } from 'lucide-react';

export const SetupWizard: React.FC = () => {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isDone, setIsDone] = useState(false);
  const [isLoadingState, setIsLoadingState] = useState(true);
  
  const [strategy, setStrategy] = useState({
    search_keywords: '',
    target_urls: '',
    wechat_accounts: ''
  });

  useEffect(() => {
    // 尝试获取用户之前的配置进行回填
    const fetchPrevConfig = async () => {
      try {
        const data = await apiService.getSystemState();
        if (data.has_constraint) {
          setStrategy({
            search_keywords: data.search_keywords || '',
            target_urls: data.target_urls || '',
            wechat_accounts: data.wechat_accounts || ''
          });
        }
      } catch (err) {
        console.warn('Failed to fetch previous state', err);
      } finally {
        setIsLoadingState(false);
      }
    };
    fetchPrevConfig();
  }, []);

  const handleSubmit = async () => {
    if (!strategy.search_keywords.trim() && !strategy.target_urls.trim() && !strategy.wechat_accounts.trim()) {
      alert('请至少填写一项采集条件！');
      return;
    }

    setIsSubmitting(true);
    
    // 构建极简的约束信息以兼容现有 API
    const constraint = {
      company_name: "手动任务",
      core_business: strategy.search_keywords ? strategy.search_keywords.split(/[,，\s]+/).filter(Boolean) : [],
      wechat_accounts: strategy.wechat_accounts.split('\n').map(s => s.trim()).filter(Boolean),
      qualifications: [],
      geography_limits: []
    };

    // 格式化 URL 和公众号
    const formattedStrategy = {
      search_keywords: strategy.search_keywords,
      target_urls: strategy.target_urls.split('\n').map(s => s.trim()).filter(Boolean),
      wechat_accounts: strategy.wechat_accounts.split('\n').map(s => s.trim()).filter(Boolean),
      scan_frequency: 30
    };

    try {
      await apiService.activateTask(constraint, formattedStrategy);
      setIsDone(true);
      setTimeout(() => {
        window.location.href = '/dashboard/wall'; // 直接跳转到判定墙
      }, 1500);
    } catch (error) {
      console.error('Activation API Error:', error);
      alert('任务启动失败，请检查后端服务');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (isDone) {
    return (
      <div className="setup-container">
        <div className="setup-card">
          <main className="setup-content text-center">
            <div className="completion-icon">
              <Check size={48} color="var(--status-success)" />
            </div>
            <h2 className="content-title">准备就绪</h2>
            <p className="content-desc">
              爬虫任务已提交并在后台运行。<br/>
              即将进入数据清洗墙...
            </p>
          </main>
        </div>
      </div>
    );
  }

  if (isLoadingState) {
    return (
      <div className="setup-container">
        <div className="setup-card" style={{padding: '60px', textAlign: 'center'}}>
          <p>正在加载系统配置...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="setup-container">
      <div className="setup-card">
        <header className="setup-header">
          <h2 className="content-title" style={{marginBottom: 0}}>任务配置</h2>
        </header>

        <main className="setup-content">
          <p className="content-desc">
            请提供搜索关键词或指定要监控的网址，系统将自动汇集最新招标情报。
          </p>

          <div className="strategy-form">
            <div className="form-item">
              <label className="form-label" style={{display: 'flex', alignItems: 'center', gap: '8px'}}>
                <Search size={16}/> 核心搜索词 (多个词用空格或逗号隔开)
              </label>
              <input 
                className="form-input" 
                placeholder="例如：广州 智慧医院 软件开发 招标" 
                value={strategy.search_keywords}
                onChange={e => setStrategy({...strategy, search_keywords: e.target.value})}
              />
            </div>

            <div className="form-item">
              <label className="form-label" style={{display: 'flex', alignItems: 'center', gap: '8px'}}>
                <Globe size={16}/> 定向监控目标网址 (每行一个)
              </label>
              <textarea 
                className="form-input" 
                rows={4} 
                style={{ height: 'auto', fontFamily: 'monospace' }}
                placeholder="https://www.ccgp.gov.cn/&#10;https://bulletin.cebpubservice.com/" 
                value={strategy.target_urls}
                onChange={e => setStrategy({...strategy, target_urls: e.target.value})}
              />
            </div>

            <div className="form-item">
              <label className="form-label" style={{display: 'flex', alignItems: 'center', gap: '8px'}}>
                <MessageCircle size={16}/> 监控微信公众号 (每行一个)
              </label>
              <textarea 
                className="form-input" 
                rows={2} 
                style={{ height: 'auto' }}
                placeholder="广州发布" 
                value={strategy.wechat_accounts}
                onChange={e => setStrategy({...strategy, wechat_accounts: e.target.value})}
              />
            </div>
          </div>

          <div className="actions" style={{justifyContent: 'center', marginTop: '32px'}}>
            <button 
              className="primary-btn" 
              style={{width: '100%', justifyContent: 'center', padding: '16px'}}
              onClick={handleSubmit} 
              disabled={isSubmitting}
            >
              {isSubmitting ? '正在触发引擎...' : '开始全网搜集'}
            </button>
          </div>
        </main>
      </div>
    </div>
  );
};
