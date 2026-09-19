def test_metrics_endpoint_returns_prometheus_text_format(client):
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers["content-type"]
    assert "# HELP forgeai_tool_calls_total" in response.text
    assert "# TYPE forgeai_tool_calls_total counter" in response.text


def test_metrics_endpoint_requires_no_authentication(client):
    # Prometheus scrapers don't carry a user's bearer token.
    response = client.get("/metrics")
    assert response.status_code == 200
