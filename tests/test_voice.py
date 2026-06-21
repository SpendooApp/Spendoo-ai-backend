import uuid
from unittest.mock import MagicMock, patch
import pytest

@patch('spendoo.voice.routes.voice_service')
@patch('spendoo.voice.routes.CategorizationService')
def test_process_voice_raw_pcm(mock_cat_service_class, mock_voice_service, client):
    # Setup mocks
    mock_voice_service.transcribe.return_value = "Coffee 10 dollars"
    
    mock_cat_service = MagicMock()
    mock_cat_service_class.return_value = mock_cat_service
    mock_cat_service.extract.return_value = {"items": [], "grand_total": 10.0}

    # Dummy raw PCM data (zeros)
    pcm_data = b'\x00' * 1000
    user_id = str(uuid.uuid4())

    # Send raw PCM data with .wav filename extension
    response = client.post(
        f"/api/v1/voice/process/{user_id}",
        files={"file": ("voice.wav", pcm_data, "audio/x-wav")}
    )

    assert response.status_code == 200
    assert response.json() == {"items": [], "grand_total": 10.0}

    # Verify transcription was called with prepended WAV header
    # The header is 44 bytes, so length of passed bytes should be 1044
    args, kwargs = mock_voice_service.transcribe.call_args
    passed_bytes = args[0]
    assert len(passed_bytes) == 1044
    assert passed_bytes.startswith(b'RIFF')
    assert b'WAVE' in passed_bytes
