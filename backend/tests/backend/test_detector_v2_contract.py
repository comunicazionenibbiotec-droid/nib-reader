"""Safe contract tests. Adapt import path to the deployed project structure."""
import pytest

@pytest.mark.skip(reason="Enable after the project test client is configured")
def test_detector_v2_health_contract(client):
    response = client.get('/detector-v2/health')
    assert response.status_code == 200
    payload = response.json()
    assert payload['status'] == 'online'
    assert payload['persistence'] is False
    assert payload['clinical'] is False

@pytest.mark.skip(reason="Enable with a synthetic image fixture")
def test_detector_v2_analyze_has_no_persistence(client, synthetic_cassette_data_url):
    response = client.post('/detector-v2/analyze', json={'image': synthetic_cassette_data_url})
    assert response.status_code == 200
    payload = response.json()
    assert payload['persistence'] is False
    assert payload['used_for_clinical_result'] is False
