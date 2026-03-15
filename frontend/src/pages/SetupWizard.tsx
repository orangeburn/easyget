import React, { useState } from 'react';
import { apiService } from '../services/api';
import './SetupWizard.css';
import { ChevronRight, Check, Upload, Loader2 } from 'lucide-react';

import { DynamicForm } from '../components/DynamicForm';

type Step = 1 | 2 | 3 | 4 | 5;

export const SetupWizard: React.FC = () => {
  const [currentStep, setCurrentStep] = useState<Step>(1);
  const [inputText, setInputText] = useState('');
  const [isParsing, setIsParsing] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [constraint, setConstraint] = useState<any>(null);
  const [newQual, setNewQual] = useState('');
  const [formSchema, setFormSchema] = useState<any>(null);
  const [formData, setFormData] = useState<Record<string, any>>({});
  const [strategy, setStrategy] = useState({
    search_keywords: '',
    target_urls: '',
    wechat_accounts: '',
    scan_frequency: 30
  });

  const steps = [
    { id: 1, name: '文档初始化' },
    { id: 2, name: '资质确认' },
    { id: 3, name: '动态补全' },
    { id: 4, name: '任务激活' },
  ];

  const handleInitialParse = async () => {
    if (!inputText.trim()) return;
    setIsParsing(true);
    try {
      const result = await apiService.parseInitialDocument(inputText);
      setConstraint(result);
      setCurrentStep(2);
    } catch (error: any) {
      console.error(error);
      alert(error.message || '解析失败，请检查后端连接');
    } finally {
      setIsParsing(false);
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    try {
      const result = await apiService.uploadDocument(file);
      setInputText(result.text);
    } catch (error) {
      console.error(error);
      alert('文件读取失败，请检查格式是否正确');
    } finally {
      setIsUploading(false);
    }
  };

  const handleAddQual = () => {
    if (!newQual.trim()) return;
    const updated = { ...constraint };
    updated.qualifications.push({ name: newQual, value: "已具备", is_must_have: true });
    setConstraint(updated);
    setNewQual('');
  };

  const handleToggleQual = (index: number) => {
    const updated = { ...constraint };
    const qual = updated.qualifications[index];
    qual.value = qual.value === "已具备" ? "不具备" : "已具备";
    setConstraint(updated);
  };

  const nextStep = async () => {
    if (currentStep === 2) {
      setIsParsing(true);
      try {
        const schema = await apiService.generateDynamicForm(constraint);
        setFormSchema(schema);
        setCurrentStep(3);
      } catch (error) {
        console.error(error);
        alert('获取表单失败');
      } finally {
        setIsParsing(false);
      }
    } else if (currentStep === 3) {
      setIsParsing(true);
      try {
        const updated = await apiService.updateConstraint(constraint, formData);
        setConstraint(updated);
        
        const kwResult = await apiService.generateKeywords(updated);
        setStrategy(prev => ({
          ...prev,
          search_keywords: kwResult.keywords.join(', ')
        }));
        
        setCurrentStep(4);
      } catch (error: any) {
        console.error(error);
        alert(error.message || '保存失败');
      } finally {
        setIsParsing(false);
      }
    } else if (currentStep === 4) {
      console.log('Step 4: Attempting to activate task...');
      console.log('Constraint:', constraint);
      console.log('Strategy:', strategy);
      setIsParsing(true);
      try {
        const result = await apiService.activateTask(constraint, strategy);
        console.log('Activation API Success:', result);
        setCurrentStep(5); 
      } catch (error) {
        console.error('Activation API Error:', error);
        alert('激活失败，请重试');
      } finally {
        setIsParsing(false);
      }
    }
  };

  // 当到达步骤 5 时，自动跳转到 dashboard
  React.useEffect(() => {
    if (currentStep === 5) {
      const timer = setTimeout(() => {
        window.location.href = '/dashboard';
      }, 1500);
      return () => clearTimeout(timer);
    }
  }, [currentStep]);

  return (
    <div className="setup-container">
      <div className="setup-card">
        <header className="setup-header">
          <div className="stepper">
            {steps.map((s) => (
              <div key={s.id} className={`step-item ${currentStep >= s.id ? 'active' : ''}`}>
                <div className="step-circle">
                  {currentStep > s.id ? <Check size={14} /> : s.id}
                </div>
                <span className="step-name">{s.name}</span>
                {s.id < 4 && <div className="step-line" />}
              </div>
            ))}
          </div>
        </header>

        <main className="setup-content">
          {currentStep === 1 && (
            <div className="step-fade-in">
              <h2 className="content-title">导入企业资料</h2>
              <p className="content-desc">
                粘贴您的公司简介、产品说明，或直接上传文档，AI 将自动分析您的业务领域。
              </p>

              <div className="upload-section">
                <label className={`upload-dropzone ${isUploading ? 'loading' : ''}`}>
                  <input 
                    type="file" 
                    className="hidden-input" 
                    accept=".docx,.txt,.md"
                    onChange={handleFileUpload}
                    disabled={isUploading}
                  />
                  {isUploading ? (
                    <Loader2 className="animate-spin" size={24} />
                  ) : (
                    <Upload size={24} />
                  )}
                  <div className="upload-text">
                    {isUploading ? '正在解析文档...' : '点击或拖拽上传 (docx, txt, md)'}
                  </div>
                </label>
              </div>

              <textarea
                className="document-input"
                placeholder="或在此处粘贴文本内容..."
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
              />
              <div className="actions">
                <button 
                  className="primary-btn" 
                  onClick={handleInitialParse}
                  disabled={isParsing || isUploading || !inputText.trim()}
                >
                  {isParsing ? '解析画像中...' : '开始画像解析'}
                  {!isParsing && <ChevronRight size={18} />}
                </button>
              </div>
            </div>
          )}

          {currentStep === 2 && (
            <div className="step-fade-in">
              <h2 className="content-title">核对企业资质</h2>
              <p className="content-desc">
                以下是从资料中识别的能力标签。您可以根据实际情况勾选或补充缺少的资质。
              </p>
              
              <div className="qual-list">
                {constraint?.qualifications.map((q: any, idx: number) => (
                  <label key={idx} className="qual-item">
                    <input 
                      type="checkbox" 
                      checked={q.value === "已具备"} 
                      onChange={() => handleToggleQual(idx)}
                    />
                    <span className="qual-name">{q.name}</span>
                  </label>
                ))}
              </div>

              <div className="add-qual-box">
                <input 
                  type="text" 
                  placeholder="手动添加其他资质..." 
                  value={newQual}
                  onChange={(e) => setNewQual(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleAddQual()}
                />
                <button onClick={handleAddQual}>添加</button>
              </div>

              <div className="actions">
                <button className="secondary-btn" onClick={() => setCurrentStep(1)}>上一步</button>
                <button className="primary-btn" onClick={nextStep} disabled={isParsing}>
                  {isParsing ? '获取配置...' : '下一步'}
                  {!isParsing && <ChevronRight size={18} />}
                </button>
              </div>
            </div>
          )}

          {currentStep === 3 && (
            <div className="step-fade-in">
              <h2 className="content-title">补充详细信息</h2>
              <p className="content-desc">
                基于识别出的行业特征，请补充以下关键信息以优化采集精准度。
              </p>
              
              <DynamicForm 
                schema={formSchema} 
                values={formData} 
                onChange={(field, value) => {
                  setFormData(prev => ({ ...prev, [field]: value }));
                }}
              />

              <div className="actions">
                <button className="secondary-btn" onClick={() => setCurrentStep(2)}>上一步</button>
                <button className="primary-btn" onClick={nextStep} disabled={isParsing}>
                  {isParsing ? '正在核算...' : '下一步'}
                  {!isParsing && <ChevronRight size={18} />}
                </button>
              </div>
            </div>
          )}
          
          {currentStep === 4 && (
            <div className="step-fade-in">
              <h2 className="content-title">配置采集任务</h2>
              <p className="content-desc">
                最后一步，告诉系统在哪里为您寻找情报。
              </p>
              
              <div className="strategy-form">
                <div className="form-item">
                  <label className="form-label">搜索关键词</label>
                  <input 
                    className="form-input" 
                    placeholder="例如：广州 智慧医院 软件开发 招标" 
                    value={strategy.search_keywords}
                    onChange={e => setStrategy({...strategy, search_keywords: e.target.value})}
                  />
                </div>
                <div className="form-item">
                  <label className="form-label">定向监控 URL (每行一个)</label>
                  <p className="form-desc">粘贴您关注的行业招标网、政采网列表，系统将深度自动检索。</p>
                  <textarea 
                    className="form-input" 
                    rows={4} 
                    style={{ height: 'auto', fontFamily: 'monospace', fontSize: '13px' }}
                    placeholder="https://www.ccgp.gov.cn/&#10;https://bulletin.cebpubservice.com/" 
                    value={strategy.target_urls}
                    onChange={e => setStrategy({...strategy, target_urls: e.target.value})}
                  />
                </div>
                <div className="form-item">
                  <label className="form-label">微信公众号 (每行一个)</label>
                  <textarea 
                    className="form-input" 
                    rows={2} 
                    style={{ height: 'auto' }}
                    placeholder="广州发布" 
                    value={strategy.wechat_accounts}
                    onChange={e => setStrategy({...strategy, wechat_accounts: e.target.value})}
                  />
                </div>
                <div className="form-item">
                  <label className="form-label">采集频率</label>
                  <select 
                    className="form-input"
                    value={strategy.scan_frequency}
                    onChange={e => setStrategy({...strategy, scan_frequency: parseInt(e.target.value)})}
                  >
                    <option value={30}>每 30 分钟 (极速)</option>
                    <option value={60}>每 1 小时 (标准)</option>
                    <option value={1440}>每天 (低频)</option>
                  </select>
                </div>
              </div>

              <div className="actions">
                <button className="secondary-btn" onClick={() => setCurrentStep(3)}>上一步</button>
                <button className="primary-btn" onClick={nextStep} disabled={isParsing}>
                  {isParsing ? '激活中...' : '提交并激活'}
                  {!isParsing && <Check size={18} />}
                </button>
              </div>
            </div>
          )}

          {currentStep === 5 && (
            <div className="step-fade-in text-center">
              <div className="completion-icon">
                <Check size={48} color="var(--status-success)" />
              </div>
              <h2 className="content-title">准备就绪</h2>
              <p className="content-desc">
                采集器已正式激活并正在启动扫描任务...
                <br />
                即将为您跳转到仪表盘。
              </p>
            </div>
          )}
        </main>
      </div>
    </div>
  );
};
