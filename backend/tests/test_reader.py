from app.services.reader_service import ReaderService


def test_reader_basic_structure():
    html = """
    <html>
      <head><title>Test</title></head>
      <body>
        <h1>招标公告</h1>
        <p>项目编号：ABC-123</p>
        <ul>
          <li>预算：500万元</li>
          <li>截止：2026-03-20</li>
        </ul>
        <p>联系人：张三</p>
        <a href="http://example.com/doc">下载标书</a>
      </body>
    </html>
    """
    reader = ReaderService()
    md = reader.to_markdown(html)
    assert "# 招标公告" in md
    assert "项目编号：ABC-123" in md
    assert "- 预算：500万元" in md
    assert "- 截止：2026-03-20" in md
    assert "下载标书 (http://example.com/doc)" in md


def test_reader_strips_script_and_style():
    html = """
    <html>
      <head>
        <style>.x{color:red}</style>
        <script>console.log('x')</script>
      </head>
      <body>
        <p>正文内容</p>
      </body>
    </html>
    """
    reader = ReaderService()
    md = reader.to_markdown(html)
    assert "console.log" not in md
    assert ".x{color:red}" not in md
    assert "正文内容" in md
