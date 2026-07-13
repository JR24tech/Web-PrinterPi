import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from webPrinterPi import app


def test_printers_api_returns_json():
    client = app.test_client()
    response = client.get('/api/printers')

    assert response.status_code == 200
    data = response.get_json()
    assert isinstance(data, list)
