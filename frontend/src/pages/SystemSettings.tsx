import React, { useEffect, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { apiService } from '../services/api';
import './SetupWizard.css';
import './SystemSettings.css';

type SystemSettingsState = {
  model_api_enabled: boolean;
  model_api_key: string;
  model_base_url: string;
  model_name: string;
  serper_api_enabled: boolean;
  serper_api_key: string;
  tavily_api_enabled: boolean;
  tavily_api_key: string;
  browser_search_enabled?: boolean;
};

type ProviderTestResult = {
  ok: boolean;
  message: string;
};

type SystemSettingsTestResult = {
  model?: ProviderTestResult;
  serper?: ProviderTestResult;
  tavily?: ProviderTestResult;
  browser?: ProviderTestResult;
};

const DEFAULT_SETTINGS: SystemSettingsState = {
  model_api_enabled: false,
  model_api_key: '',
  model_base_url: 'https://api.openai.com/v1',
  model_name: 'gpt-4-turbo-preview',
  serper_api_enabled: false,
  serper_api_key: '',
  tavily_api_enabled: false,
  tavily_api_key: '',
  browser_search_enabled: true
};

const SETTINGS_CACHE_KEY = 'easyget_system_settings_cache';

export const SystemSettings: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [settings, setSettings] = useState<SystemSettingsState>(DEFAULT_SETTINGS);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [isTesting, setIsTesting] = useState(false);
  const [isSaved, setIsSaved] = useState(false);
  const [testResult, setTestResult] = useState<SystemSettingsTestResult | null>(null);

  useEffect(() => {
    let isCancelled = false;

    const readCachedSettings = () => {
      try {
        const raw = localStorage.getItem(SETTINGS_CACHE_KEY);
        if (!raw) return null;
        const parsed = JSON.parse(raw);
        if (!parsed || typeof parsed !== 'object') return null;
        return { ...DEFAULT_SETTINGS, ...parsed };
      } catch {
        return null;
      }
    };

    const persistSettingsCache = (nextSettings: SystemSettingsState) => {
      try {
        localStorage.setItem(SETTINGS_CACHE_KEY, JSON.stringify(nextSettings));
      } catch {
        // ignore storage errors
      }
    };

    const fetchSettings = async () => {
      setIsLoading(true);
      const cached = readCachedSettings();
      if (cached) {
        setSettings(cached);
      }

      let loaded = false;
      let lastError: unknown = null;
      for (let attempt = 0; attempt < 2; attempt += 1) {
        try {
          const data = await apiService.getSystemSettings() as SystemSettingsState;
          if (isCancelled) return;
          const nextSettings = { ...DEFAULT_SETTINGS, ...data };
          setSettings(nextSettings);
          persistSettingsCache(nextSettings);
          loaded = true;
          break;
        } catch (error) {
          lastError = error;
        }
      }

      if (!loaded && !cached) {
        console.error('Failed to fetch system settings:', lastError);
        setSettings(DEFAULT_SETTINGS);
      }

      if (!isCancelled) {
        setIsLoading(false);
      }
    };

    fetchSettings();
    return () => {
      isCancelled = true;
    };
  }, [location.pathname]);

  const handleSave = async () => {
    if (!validateSettings()) return;
    setIsSaving(true);
    try {
      const data = await apiService.updateSystemSettings(settings) as SystemSettingsState;
      const nextSettings = { ...DEFAULT_SETTINGS, ...data };
      setSettings(nextSettings);
      try {
        localStorage.setItem(SETTINGS_CACHE_KEY, JSON.stringify(nextSettings));
      } catch {
        // ignore storage errors
      }
      setIsSaved(true);
      setTestResult(null);
      setTimeout(() => {
        setIsSaved(false);
        navigate('/dashboard');
      }, 800);
    } catch (error) {
      console.error('Failed to save system settings:', error);
      alert('保存失败，请检查后端服务是否启动');
    } finally {
      setIsSaving(false);
    }
  };

  const handleTest = async () => {
    if (!validateSettings()) return;
    setIsTesting(true);
    try {
      const data = await apiService.testSystemSettings(settings) as SystemSettingsTestResult;
      setTestResult(data);
    } catch (error) {
      console.error('Failed to test system settings:', error);
      alert('测试失败，请检查后端服务是否启动');
    } finally {
      setIsTesting(false);
    }
  };

  const validateSettings = () => {
    if (settings.model_api_enabled && !settings.model_api_key.trim()) {
      alert('模型 API 已开启，请填写模型 API Key');
      return false;
    }
    if (settings.model_api_enabled && settings.model_base_url && !/^https?:\/\//i.test(settings.model_base_url)) {
      alert('模型 Base URL 格式不正确，请以 http:// 或 https:// 开头');
      return false;
    }
    if (settings.serper_api_enabled && !settings.serper_api_key.trim()) {
      alert('Serper 已开启，请填写 Serper API Key');
      return false;
    }
    if (settings.tavily_api_enabled) {
      const key = settings.tavily_api_key.trim();
      if (!key) {
        alert('Tavily 已开启，请填写 Tavily API Key');
        return false;
      }
      if (!key.startsWith('tvly-')) {
        alert('Tavily API Key 格式不正确，应以 tvly- 开头');
        return false;
      }
    }
    return true;
  };

  const renderTestLine = (label: string, result?: ProviderTestResult) => {
    if (!result) return null;
    return (
      <div className={`test-line ${result.ok ? 'ok' : 'fail'}`}>
        <span className="test-label">{label}</span>
        <span className="test-message">{result.message}</span>
      </div>
    );
  };

  return (
    <div className="setup-container in-dashboard">
      <div className="setup-card step-fade-in">
        <header className="setup-header">
          <div className="settings-header-row">
            <h1 className="content-title">系统设置</h1>
            <button className="back-trigger" onClick={() => navigate('/dashboard/clues')}>
              返回
            </button>
          </div>
          <p className="content-desc">
            在这里配置模型与搜索服务的 API。所有配置保存在系统中，无需再修改本地环境变量。
          </p>
        </header>

        <main className="setup-content">
          {isLoading ? (
            <div style={{ padding: '30px 0' }}>
              <p className="content-desc" style={{ marginBottom: 0 }}>正在加载配置...</p>
            </div>
          ) : (
            <div className="strategy-form">
              <section className="settings-section">
                <div className="settings-header">
                  <div>
                    <div className="settings-title">模型 API</div>
                    <div className="settings-subtitle">用于关键词扩展与画像解析。</div>
                  </div>
                  <label className="switch">
                    <input
                      type="checkbox"
                      checked={settings.model_api_enabled}
                      onChange={() =>
                        setSettings((prev) => ({
                          ...prev,
                          model_api_enabled: !prev.model_api_enabled
                        }))
                      }
                    />
                    <span className="slider" />
                  </label>
                </div>

                <div className="settings-grid">
                  <div className="form-item">
                    <label className="form-label">模型 API Key</label>
                    <input
                      className="form-input"
                      type="password"
                      placeholder="sk-..."
                      value={settings.model_api_key}
                      onChange={(e) =>
                        setSettings((prev) => ({ ...prev, model_api_key: e.target.value }))
                      }
                    />
                  </div>
                  <div className="form-item">
                    <label className="form-label">模型 Base URL</label>
                    <input
                      className="form-input"
                      placeholder="https://api.openai.com/v1"
                      value={settings.model_base_url}
                      onChange={(e) =>
                        setSettings((prev) => ({ ...prev, model_base_url: e.target.value }))
                      }
                    />
                  </div>
                  <div className="form-item">
                    <label className="form-label">模型名称</label>
                    <input
                      className="form-input"
                      placeholder="gpt-4-turbo-preview"
                      value={settings.model_name}
                      onChange={(e) =>
                        setSettings((prev) => ({ ...prev, model_name: e.target.value }))
                      }
                    />
                  </div>
                </div>
              </section>

              <section className="settings-section">
                <div className="settings-header">
                  <div>
                    <div className="settings-title">搜索 API</div>
                    <div className="settings-subtitle">可开启第三方搜索引擎补充结果。</div>
                  </div>
                  <button className="secondary-btn small" onClick={handleTest} disabled={isTesting}>
                    {isTesting ? '正在测试...' : '测试连接'}
                  </button>
                </div>

                <div className="settings-provider">
                  <div className="settings-header compact">
                    <div className="settings-title-small">Serper Search API</div>
                    <label className="switch">
                      <input
                        type="checkbox"
                        checked={settings.serper_api_enabled}
                        onChange={() =>
                          setSettings((prev) => ({
                            ...prev,
                            serper_api_enabled: !prev.serper_api_enabled
                          }))
                        }
                      />
                      <span className="slider" />
                    </label>
                  </div>
                  <div className="form-item">
                    <label className="form-label">Serper API Key</label>
                    <input
                      className="form-input"
                      type="password"
                      placeholder="serper-..."
                      value={settings.serper_api_key}
                      onChange={(e) =>
                        setSettings((prev) => ({ ...prev, serper_api_key: e.target.value }))
                      }
                    />
                  </div>
                </div>

                <div className="settings-provider">
                  <div className="settings-header compact">
                    <div className="settings-title-small">Tavily Search API</div>
                    <label className="switch">
                      <input
                        type="checkbox"
                        checked={settings.tavily_api_enabled}
                        onChange={() =>
                          setSettings((prev) => ({
                            ...prev,
                            tavily_api_enabled: !prev.tavily_api_enabled
                          }))
                        }
                      />
                      <span className="slider" />
                    </label>
                  </div>
                  <div className="form-item">
                    <label className="form-label">Tavily API Key</label>
                    <input
                      className="form-input"
                      type="password"
                      placeholder="tavily-..."
                      value={settings.tavily_api_key}
                      onChange={(e) =>
                        setSettings((prev) => ({ ...prev, tavily_api_key: e.target.value }))
                      }
                    />
                  </div>
                </div>

                <div className="settings-provider locked">
                  <div className="settings-header compact">
                    <div className="settings-title-small">本地浏览器搜索 (Playwright)</div>
                    <label className="switch disabled">
                      <input type="checkbox" checked disabled />
                      <span className="slider" />
                    </label>
                  </div>
                  <div className="settings-note">本地搜索默认开启</div>
                </div>
              </section>

              {testResult && (
                <div className="test-result">
                  {renderTestLine('模型 API', testResult.model)}
                  {renderTestLine('Serper', testResult.serper)}
                  {renderTestLine('Tavily', testResult.tavily)}
                  {renderTestLine('本地搜索', testResult.browser)}
                </div>
              )}

              <div className="actions settings-actions">
                <button className="primary-btn" onClick={handleSave} disabled={isSaving}>
                  {isSaving ? '正在保存...' : isSaved ? '已保存' : '保存设置'}
                </button>
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
};
