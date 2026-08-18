import httpx
import pytest

from python_backend.services.trends import trends_service


VALID_RSS = """<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:ht="https://trends.google.com/trending/rss">
  <channel>
    <item>
      <title> Dólar blue </title>
      <ht:approx_traffic>20K+</ht:approx_traffic>
      <pubDate>Mon, 27 Jul 2026 10:00:00 GMT</pubDate>
      <category>Economía</category>
    </item>
    <item>
      <title>Dolar blue</title>
      <ht:approx_traffic>10K+</ht:approx_traffic>
      <pubDate>Mon, 27 Jul 2026 10:00:00 GMT</pubDate>
    </item>
    <item>
      <title>   </title>
      <ht:approx_traffic>5K+</ht:approx_traffic>
    </item>
    <item>
      <title>Selección Argentina</title>
      <ht:approx_traffic>2,000+</ht:approx_traffic>
      <pubDate>Mon, 27 Jul 2026 11:00:00 GMT</pubDate>
    </item>
  </channel>
</rss>
"""


def mock_response(text: str, status_code: int = 200) -> httpx.Response:
    request = httpx.Request("GET", trends_service.GOOGLE_TRENDS_RSS_URL)
    return httpx.Response(status_code=status_code, text=text, request=request)


def test_valid_rss_returns_normalized_unique_items(monkeypatch):
    monkeypatch.setattr(httpx, "get", lambda *args, **kwargs: mock_response(VALID_RSS))

    result = trends_service.collect_trending_topics(country="ar", limit=10)

    assert result.country == "AR"
    assert result.used_fallback is False
    assert result.error is None
    assert result.items == [
        {
            "title": "Dólar blue",
            "normalized_title": "dolar blue",
            "source": "google_trends",
            "category": "Economía",
            "date": "2026-07-27",
            "score": 20000,
        },
        {
            "title": "Selección Argentina",
            "normalized_title": "seleccion argentina",
            "source": "google_trends",
            "category": "general",
            "date": "2026-07-27",
            "score": 2000,
        },
    ]


def test_rss_with_more_than_limit_respects_limit(monkeypatch):
    items = "".join(f"<item><title>Tema {index}</title></item>" for index in range(12))
    monkeypatch.setattr(
        httpx,
        "get",
        lambda *args, **kwargs: mock_response(f"<rss><channel>{items}</channel></rss>"),
    )

    result = trends_service.collect_trending_topics(limit=10)

    assert len(result.items) == 10
    assert result.items[-1]["title"] == "Tema 9"


@pytest.mark.parametrize(
    "raised_error",
    [
        httpx.TimeoutException("timeout de prueba"),
        httpx.HTTPStatusError(
            "status 500",
            request=httpx.Request("GET", trends_service.GOOGLE_TRENDS_RSS_URL),
            response=httpx.Response(500),
        ),
    ],
)
def test_timeout_or_http_error_activates_fallback(monkeypatch, raised_error):
    def raise_error(*args, **kwargs):
        raise raised_error

    monkeypatch.setattr(httpx, "get", raise_error)

    result = trends_service.collect_trending_topics(limit=3)

    assert result.used_fallback is True
    assert result.error
    assert len(result.items) == 3
    assert {item["source"] for item in result.items} == {"fallback"}


@pytest.mark.parametrize("rss_text", ["<rss>", "<rss><channel></channel></rss>"])
def test_invalid_xml_or_empty_list_activates_fallback(monkeypatch, rss_text):
    monkeypatch.setattr(httpx, "get", lambda *args, **kwargs: mock_response(rss_text))

    result = trends_service.collect_trending_topics(limit=2)

    assert result.used_fallback is True
    assert result.error
    assert len(result.items) == 2
    assert all(item["source"] == "fallback" for item in result.items)


@pytest.mark.parametrize("country", ["", "ARG", "A1", 123])
def test_invalid_country_returns_clear_error(country):
    with pytest.raises(ValueError, match="country"):
        trends_service.collect_trending_topics(country=country)


@pytest.mark.parametrize("limit", [0, 11, "10"])
def test_invalid_limit_returns_clear_error(limit):
    with pytest.raises(ValueError, match="limit"):
        trends_service.collect_trending_topics(limit=limit)


def test_get_trending_topics_returns_only_items(monkeypatch):
    monkeypatch.setattr(httpx, "get", lambda *args, **kwargs: mock_response(VALID_RSS))

    items = trends_service.get_trending_topics()

    assert isinstance(items, list)
    assert items[0]["source"] == "google_trends"


def test_save_trends_output_success_matches_schema_and_filename(monkeypatch, tmp_path):
    monkeypatch.setattr(httpx, "get", lambda *args, **kwargs: mock_response(VALID_RSS))

    output_path = trends_service.save_trends_output(output_dir=tmp_path)

    assert output_path.parent == tmp_path
    assert output_path.name.startswith("trends_v1_")

    from tools.validate_output import validate_output_file

    output = validate_output_file(output_path)
    assert output.status == "success"
    assert output.errors == []
    assert output.data["country"] == "AR"
    assert output.data["used_fallback"] is False
    assert output_path.name == f"trends_v1_{str(output.run_id)[:8]}.json"


def test_save_trends_output_fallback_is_draft_with_error(monkeypatch, tmp_path):
    def raise_timeout(*args, **kwargs):
        raise httpx.TimeoutException("timeout de prueba")

    monkeypatch.setattr(httpx, "get", raise_timeout)

    output_path = trends_service.save_trends_output(output_dir=tmp_path)

    from tools.validate_output import validate_output_file

    output = validate_output_file(output_path)
    assert output.status == "draft"
    assert output.data["used_fallback"] is True
    assert output.errors == ["timeout de prueba"]
    assert all(item["source"] == "fallback" for item in output.data["items"])
