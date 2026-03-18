import React, { useState, useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { apiService } from '../services/api';
import './SetupWizard.css';
import { Check } from 'lucide-react';

const REGION_DATA: Record<string, string[]> = {
  '全国': [],
  '北京': ['北京市'],
  '上海': ['上海市'],
  '天津': ['天津市'],
  '重庆': ['重庆市'],
  '广东': ['广州', '深圳', '珠海', '汕头', '佛山', '韶关', '湛江', '肇庆', '江门', '茂名', '惠州', '梅州', '汕尾', '河源', '阳江', '清远', '东莞', '中山', '潮州', '揭阳', '云浮'],
  '江苏': ['南京', '无锡', '徐州', '常州', '苏州', '南通', '连云港', '淮安', '盐城', '扬州', '镇江', '泰州', '宿迁'],
  '浙江': ['杭州', '宁波', '温州', '嘉兴', '湖州', '绍兴', '金华', '衢州', '舟山', '台州', '丽水'],
  '山东': ['济南', '青岛', '淄博', '枣庄', '东营', '烟台', '潍坊', '济宁', '泰安', '威海', '日照', '临沂', '德州', '聊城', '滨州', '菏泽'],
  '河南': ['郑州', '开封', '洛阳', '平顶山', '安阳', '鹤壁', '新乡', '焦作', '濮阳', '许昌', '漯河', '三门峡', '南阳', '商丘', '信阳', '周口', '驻马店'],
  '河北': ['石家庄', '唐山', '秦皇岛', '邯郸', '邢台', '保定', '张家口', '承德', '沧州', '廊坊', '衡水'],
  '四川': ['成都', '自贡', '攀珠花', '泸州', '德阳', '绵阳', '广元', '遂宁', '内江', '乐山', '南充', '眉山', '宜宾', '广安', '达州', '雅安', '巴中', '资阳'],
  '湖北': ['武汉', '黄石', '十堰', '宜昌', '襄阳', '鄂州', '荆门', '孝感', '荆州', '黄冈', '咸宁', '随州', '恩施'],
  '湖南': ['长沙', '株洲', '湘潭', '衡阳', '邵阳', '岳阳', '常德', '张家界', '益阳', '郴州', '永州', '怀化', '娄底', '湘西'],
  '福建': ['福州', '厦门', '莆田', '三明', '泉州', '漳州', '南平', '龙岩', '宁德'],
  '安徽': ['合肥', '芜湖', '蚌埠', '淮南', '马鞍山', '淮北', '铜陵', '安庆', '黄山', '滁州', '阜阳', '宿州', '六安', '亳州', '池州', '宣城'],
  '陕西': ['西安', '铜川', '宝鸡', '咸阳', '渭南', '延安', '汉中', '榆林', '安康', '商洛'],
  '辽宁': ['沈阳', '大连', '鞍山', '抚顺', '本溪', '丹东', '锦州', '营口', '阜新', '辽阳', '盤锦', '铁岭', '朝阳', '葫芦岛'],
  '山西': ['太原', '大同', '阳泉', '长治', '晋城', '朔州', '晋中', '运城', '忻州', '临汾', '吕亮'],
  '江西': ['南昌', '景德镇', '萍乡', '九江', '新余', '鹰潭', '赣州', '吉安', '宜春', '抚州', '上饶'],
  '黑龙江': ['哈尔滨', '齐齐哈尔', '鸡西', '鹤岗', '双鸭山', '大庆', '伊春', '佳木斯', '七台河', '牡丹江', '黑河', '绥化'],
  '吉林': ['长春', '吉林', '四平', '辽源', '通化', '白山', '松原', '白城', '延边'],
  '云南': ['昆明', '曲靖', '玉溪', '保山', '昭通', '丽江', '普洱', '临沧', '大理', '楚雄', '红河', '文山', '西双版纳', '德宏', '怒江', '迪庆'],
  '贵州': ['贵阳', '六盘水', '遵义', '安顺', '毕节', '铜仁', '黔西南', '黔东南', '黔南'],
  '甘肃': ['兰州', '嘉峪关', '金昌', '白银', '天水', '武威', '张掖', '平凉', '酒泉', '庆阳', '定西', '陇南', '临夏', '甘南'],
  '青海': ['西宁', '海东', '海北', '黄南', '海南', '果洛', '玉树', '海西'],
  '广西': ['南宁', '柳州', '桂林', '梧州', '北海', '防城港', '钦州', '贵港', '玉林', '百色', '贺州', '河池', '来宾', '崇左'],
  '宁夏': ['银川', '石嘴山', '吴忠', '固原', '中卫'],
  '新疆': ['乌鲁木齐', '克拉玛依', '吐鲁番', '哈密', '昌吉', '博尔塔拉', '巴音郭楞', '阿克苏', '克孜勒苏柯尔克孜', '喀什', '和田', '伊犁', '塔城', '阿勒泰'],
  '内蒙古': ['呼和浩特', '包头', '乌海', '赤峰', '通辽', '鄂尔多斯', '呼伦贝尔', '巴彦噪尔', '乌兰察布', '兴安', '锡林郭勒', '阿拉善'],
  '海南': ['海口', '三亚', '三沙', '儋州'],
  '西藏': ['拉萨', '日喀则', '昌都', '林芝', '山南', '那曲', '阿里'],
};

export const SetupWizard: React.FC = () => {
  const navigate = useNavigate();
  const location = useLocation();
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [isDone, setIsDone] = useState(false);
  const [isLoadingState, setIsLoadingState] = useState(true);

  const isInDashboard = location.pathname.includes('/dashboard');

  const [strategy, setStrategy] = useState({
    search_keywords: '',
    target_urls: '',
    wechat_accounts: '',
    province: '全国',
    city: '',
    min_amount: '',
    time_range: 'all',
    scan_frequency: 30
  });
  const [expandedKeywords, setExpandedKeywords] = useState<string[]>([]);

  const provinces = Object.keys(REGION_DATA);

  useEffect(() => {
    const fetchPrevConfig = async () => {
      try {
        const data = await apiService.getSystemState() as any;
        if (data.has_constraint) {
          const regionFull = data.geography_limits?.[0]?.value || '全国';
          const [prevProv, prevCity] = regionFull.split('-');

          setStrategy({
            search_keywords: data.search_keywords || '',
            target_urls: data.target_urls || '', // 后端现在返回的是 \n 分隔的字符串
            wechat_accounts: data.wechat_accounts || '', // 同上
            province: prevProv || '全国',
            city: prevCity || '',
            min_amount: data.financial_thresholds?.[0]?.value || '',
            time_range: data.other_constraints?.find((c: any) => c.name === '发布时间')?.value || 'all',
            scan_frequency: data.scan_frequency || 30
          });
        }
        setExpandedKeywords(Array.isArray((data as any).expanded_keywords) ? (data as any).expanded_keywords : []);
      } catch (err) {
        console.warn('Failed to fetch previous state', err);
      } finally {
        setIsLoadingState(false);
      }
    };
    fetchPrevConfig();
  }, []);

  useEffect(() => {
    const interval = setInterval(async () => {
      try {
        const data = await apiService.getSystemState(6000) as any;
        const list = Array.isArray(data?.expanded_keywords) ? data.expanded_keywords : [];
        setExpandedKeywords(list);
      } catch {
        // ignore polling errors
      }
    }, 5000);
    return () => clearInterval(interval);
  }, []);


  const handleSubmit = async () => {
    if (!strategy.search_keywords.trim() && !strategy.target_urls.trim() && !strategy.wechat_accounts.trim()) {
      alert('请至少填写一项采集条件！');
      return;
    }

    setIsSubmitting(true);

    const regionValue = strategy.province === '全国'
      ? '全国'
      : (strategy.city && strategy.city !== '全省' ? `${strategy.province}-${strategy.city}` : strategy.province);

    const constraint = {
      company_name: "手动任务",
      core_business: strategy.search_keywords ? strategy.search_keywords.split(/[,，\s]+/).filter(Boolean) : [],
      wechat_accounts: strategy.wechat_accounts.split('\n').map((s: string) => s.trim()).filter(Boolean),
      custom_urls: strategy.target_urls.split('\n').map((s: string) => s.trim()).filter(Boolean),
      qualifications: [],
      geography_limits: strategy.province !== '全国' ? [{ name: '实施地域', value: regionValue, is_must_have: true }] : [],
      financial_thresholds: strategy.min_amount ? [{ name: '最小项目金额', value: strategy.min_amount, is_must_have: false }] : [],
      other_constraints: strategy.time_range !== 'all' ? [{ name: '发布时间', value: strategy.time_range, is_must_have: true }] : [],
      scan_frequency: Number(strategy.scan_frequency)
    };

    const formattedStrategy = {
      search_keywords: strategy.search_keywords,
      target_urls: strategy.target_urls.split('\n').map((s: string) => s.trim()).filter(Boolean),
      wechat_accounts: strategy.wechat_accounts.split('\n').map((s: string) => s.trim()).filter(Boolean),
      scan_frequency: Number(strategy.scan_frequency)
    };

    try {
      await apiService.activateTask(constraint, formattedStrategy);
      setIsDone(true);
      setTimeout(() => {
        if (isInDashboard) {
          setIsDone(false);
          navigate('/dashboard/clues');
        } else {
          window.location.href = '/dashboard/clues';
        }
      }, 1500);
    } catch (error) {
      console.error('Activation API Error:', error);
      alert('任务启动失败，请检查后端服务');
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleProvinceChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const province = e.target.value;
    setStrategy({
      ...strategy,
      province,
      city: '全省'
    });
  };

  if (isLoadingState) {
    return (
      <div className={`setup-container ${isInDashboard ? 'in-dashboard' : ''}`}>
        <div className="setup-card" style={{ padding: '60px', textAlign: 'center' }}>
          <p className="content-desc" style={{ textAlign: 'center', width: '100%', maxWidth: 'none' }}>正在加载配置...</p>
        </div>
      </div>
    );
  }

  const cities = REGION_DATA[strategy.province] || [];

  return (
    <div className={`setup-container ${isInDashboard ? 'in-dashboard' : ''}`}>
      <div className="setup-card step-fade-in">
        <header className="setup-header">
          <div className="wizard-header-row">
            <h1 className="content-title">{isInDashboard ? (isDone ? '准备就绪' : '修改采集任务') : (isDone ? '准备就绪' : '配置采集任务')}</h1>
            <button className="back-trigger" onClick={() => navigate('/dashboard/clues')}>
              返回
            </button>
          </div>
          <p className="content-desc">
            {isDone ? '爬虫任务已在后台启动。正在跳转至线索列表...' : '输入关键词或监控网址，Easyget 将自动为您汇集全网最新招标情报。'}
          </p>
        </header>

        <main className="setup-content">
          {isDone ? (
            <div className="ready-state">
              <div className="ready-icon">
                <Check size={36} strokeWidth={3} />
              </div>
              <div className="ready-text">
                <div className="ready-title">准备就绪</div>
                <div className="ready-desc">任务已启动，正在跳转至线索列表…</div>
              </div>
            </div>
          ) : (
            <div className="strategy-form">
              <div className="form-item">
                <label className="form-label">核心搜索词</label>
                <input
                  className="form-input"
                  placeholder="例如：广州 智慧医院 软件开发"
                  value={strategy.search_keywords}
                  onChange={e => setStrategy({ ...strategy, search_keywords: e.target.value })}
                />
                <div className="expand-block">
                  <div className="form-label">LLM扩词（只读）</div>
                  <div className="expand-preview">
                    <div className="expand-tags">
                      {expandedKeywords.length > 0 ? (
                        expandedKeywords.map((kw) => (
                          <span className="expand-tag" key={kw}>{kw}</span>
                        ))
                      ) : (
                        <span className="expand-hint">暂无扩词结果</span>
                      )}
                    </div>
                  </div>
                </div>
              </div>

              <div className="filter-grid">
                <div className="form-item">
                  <label className="form-label">目标省份</label>
                  <select
                    className="form-input"
                    value={strategy.province}
                    onChange={handleProvinceChange}
                  >
                    {provinces.map(p => (
                      <option key={p} value={p}>{p}</option>
                    ))}
                  </select>
                </div>

                <div className="form-item" style={{ opacity: strategy.province === '全国' ? 0.3 : 1, pointerEvents: strategy.province === '全国' ? 'none' : 'auto' }}>
                  <label className="form-label">目标城市</label>
                  <select
                    className="form-input"
                    value={strategy.city}
                    onChange={e => setStrategy({ ...strategy, city: e.target.value })}
                  >
                    <option value="全省">全省</option>
                    {cities.map(c => (
                      <option key={c} value={c}>{c}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="filter-grid-3">
                <div className="form-item">
                  <label className="form-label">最低金额 (万)</label>
                  <input
                    type="number"
                    className="form-input"
                    placeholder="如：50"
                    value={strategy.min_amount}
                    onChange={e => setStrategy({ ...strategy, min_amount: e.target.value })}
                  />
                </div>

                <div className="form-item">
                  <label className="form-label">发布时间</label>
                  <select
                    className="form-input"
                    value={strategy.time_range}
                    onChange={e => setStrategy({ ...strategy, time_range: e.target.value })}
                  >
                    <option value="all">不限</option>
                    <option value="3d">三天内</option>
                    <option value="1w">一周内</option>
                    <option value="1m">一个月内</option>
                  </select>
                </div>

                <div className="form-item">
                  <label className="form-label">搜集频率</label>
                  <select
                    className="form-input"
                    value={strategy.scan_frequency}
                    onChange={e => setStrategy({ ...strategy, scan_frequency: Number(e.target.value) })}
                  >
                    <option value={0}>自动循环</option>
                    <option value={1440}>每一天</option>
                  </select>
                </div>
              </div>

              <div className="form-item">
                <label className="form-label">定向监控网址 (每行一个)</label>
                <textarea
                  className="form-input"
                  rows={2}
                  style={{ fontFamily: 'var(--mono)', fontSize: '14px' }}
                  placeholder="https://www.ccgp.gov.cn/"
                  value={strategy.target_urls}
                  onChange={e => setStrategy({ ...strategy, target_urls: e.target.value })}
                />
              </div>

              <div className="form-item">
                <label className="form-label">微信公众号 (每行一个)</label>
                <textarea
                  className="form-input"
                  rows={2}
                  placeholder="公众号名称"
                  value={strategy.wechat_accounts}
                  onChange={e => setStrategy({ ...strategy, wechat_accounts: e.target.value })}
                />
              </div>

              <div className="actions">
                <button
                  className="primary-btn"
                  onClick={handleSubmit}
                  disabled={isSubmitting}
                >
                  {isSubmitting ? '正在启动...' : (isInDashboard ? '应用修改' : '开始全网搜集')}
                </button>
              </div>
            </div>
          )}
        </main>
      </div>
    </div>
  );
};
