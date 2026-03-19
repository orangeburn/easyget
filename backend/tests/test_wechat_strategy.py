from app.engines.collector.wechat_strategy import WechatStrategy


def test_build_targets_prefers_account_keyword_pairs():
    strategy = WechatStrategy()

    targets = strategy._build_targets(["中国招标投标公共服务平台"], "工程\n招标")

    assert len(targets) == 3
    assert targets[0]["type"] == "account"
    assert targets[0]["query"] == "中国招标投标公共服务平台"
    assert targets[0]["keywords"] == ["工程", "招标"]
    assert targets[1]["type"] == "account_keyword"
    assert targets[1]["query"] == "中国招标投标公共服务平台 工程"
    assert targets[1]["source_label"] == "定向公号"


def test_matching_account_accepts_historical_name():
    strategy = WechatStrategy()

    assert strategy._is_matching_account("中国招标投标公共服务平台", "中国招标公共服务平台")
    assert not strategy._is_matching_account("中国招标投标公共服务平台", "上海市建设工程咨询行业协会资讯")


def test_keyword_hit_requires_keyword_presence():
    strategy = WechatStrategy()

    assert strategy._keyword_hit(
        "关于严格执行《工程建设项目招标代理机构管理暂行办法》相关规定的通知",
        "来源：中国招标公共服务平台",
        "各招标代理机构，根据行业监管部门核查反馈……",
        ["工程"],
    )
    assert not strategy._keyword_hit(
        "中国招标投标公共服务平台召开座谈会",
        "从招标数据看新产业发展",
        "会议围绕平台建设开展交流。",
        ["工程"],
    )


def test_clean_url_keeps_real_wechat_link():
    strategy = WechatStrategy()

    url = "https://mp.weixin.qq.com/s?__biz=MzA&mid=1&idx=1&sn=abc&utm_source=x"
    assert strategy._clean_url(url) == "https://mp.weixin.qq.com/s?__biz=MzA&mid=1&idx=1&sn=abc"

    short_url = "https://mp.weixin.qq.com/s"
    assert strategy._clean_url(short_url) == short_url
