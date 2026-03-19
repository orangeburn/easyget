from app.engines.collector.playwright_strategy import SiteSpecificStrategy


def test_expand_paged_urls_from_query_param():
    strategy = SiteSpecificStrategy()

    urls = strategy._expand_paged_urls(
        "https://bulletin.cebpubservice.com/xxfbcmses/search/bulletin.html?dates=300&categoryId=88&page=1&showStatus=1",
        max_pages=3,
    )

    assert urls == [
        "https://bulletin.cebpubservice.com/xxfbcmses/search/bulletin.html?dates=300&categoryId=88&page=1&showStatus=1",
        "https://bulletin.cebpubservice.com/xxfbcmses/search/bulletin.html?dates=300&categoryId=88&page=2&showStatus=1",
        "https://bulletin.cebpubservice.com/xxfbcmses/search/bulletin.html?dates=300&categoryId=88&page=3&showStatus=1",
    ]


def test_resolve_special_detail_url_for_ceb_bulletin():
    strategy = SiteSpecificStrategy()

    resolved = strategy._resolve_special_detail_url(
        "javascript:urlOpen('8a94947595375a5b019d052f726d11d3')",
        "https://bulletin.cebpubservice.com/xxfbcmses/search/bulletin.html?dates=300&categoryId=88&page=1&showStatus=1",
    )

    assert resolved == (
        "https://ctbpsp.com/#/bulletinDetail?uuid=8a94947595375a5b019d052f726d11d3"
        "&inpvalue=&dataSource=0&tenderAgency="
    )


def test_parse_text_date_supports_dash_and_chinese():
    strategy = SiteSpecificStrategy()

    assert strategy._parse_text_date("2026-03-19").strftime("%Y-%m-%d") == "2026-03-19"
    assert strategy._parse_text_date("2026年3月17日").strftime("%Y-%m-%d") == "2026-03-17"
