"""Test the E-Redes Smart Metering Plus webhook handling."""
import json
from unittest.mock import AsyncMock, patch

import pytest
from aiohttp.web import Request, Response

from custom_components.e_redes_smart_metering_plus.webhook import handle_webhook


@pytest.fixture
def sample_webhook_data():
    """Return sample webhook data."""
    return {
        "clock": "2025-08-01 12:41:10",
        "cpe": "PT000XXXXXXXXXXXXXXX",
        "instantaneousActivePowerImport": 85.85,
        "maxActivePowerImport": 85.75,
        "maxActivePowerImportTime": "2024-04-29 12:41:10",
        "activeEnergyImport": 198114.34,
        "instantaneousActivePowerExport": 64.93,
        "maxActivePowerExport": 96.86,
        "maxActivePowerExportTime": "2024-04-29 12:41:10",
        "activeEnergyExport": 612865.24,
        "voltageL1": 231.58,
    }


@pytest.mark.asyncio
async def test_webhook_handler_success(hass, sample_webhook_data):
    """Test successful webhook handling."""
    # Create mock request
    request = AsyncMock(spec=Request)
    request.json = AsyncMock(return_value=sample_webhook_data)

    # Mock the async functions
    with patch(
        "custom_components.e_redes_smart_metering_plus.webhook.async_ensure_device"
    ) as mock_ensure_device, patch(
        "custom_components.e_redes_smart_metering_plus.webhook.async_process_sensor_data"
    ) as mock_process_data:

        response = await handle_webhook(hass, "test_webhook_id", request)

        # Verify calls
        mock_ensure_device.assert_called_once_with(hass, "PT000XXXXXXXXXXXXXXX")
        mock_process_data.assert_called_once_with(
            hass, "PT000XXXXXXXXXXXXXXX", sample_webhook_data
        )

        # Verify response
        assert response.status == 200
        assert response.text == "OK"


@pytest.mark.asyncio
async def test_webhook_handler_missing_cpe(hass):
    """Test webhook handling with missing CPE."""
    # Create mock request with invalid data
    invalid_data = {"someField": "someValue"}
    request = AsyncMock(spec=Request)
    request.json = AsyncMock(return_value=invalid_data)

    response = await handle_webhook(hass, "test_webhook_id", request)

    # Verify error response
    assert response.status == 400
    assert response.text == "Missing 'cpe' field"


@pytest.mark.asyncio
async def test_webhook_handler_invalid_json(hass):
    """Test webhook handling with invalid JSON."""
    # Create mock request that raises JSONDecodeError
    request = AsyncMock(spec=Request)
    request.json = AsyncMock(side_effect=json.JSONDecodeError("msg", "doc", 0))

    response = await handle_webhook(hass, "test_webhook_id", request)

    # Verify error response
    assert response.status == 400
    assert response.text == "Invalid JSON"
