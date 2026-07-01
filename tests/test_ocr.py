import pytest
from unittest.mock import MagicMock, patch
from spendoo.ocr.service import OCRService

def test_azure_ocr_called_first():
    # Patch the Azure client and settings
    with patch("spendoo.ocr.service.settings") as mock_settings:
        mock_settings.AZURE_ENDPOINT = "https://mock-azure.cognitiveservices.azure.com/"
        mock_settings.AZURE_KEY = "mockkey123"
        mock_settings.GEMINI_OCR_MODELS = ["gemini-mock"]
        mock_settings.MISTRAL_API_KEY = "mistral-mock"
        mock_settings.GEMINI_API_KEY = "gemini-mock"

        # Mock DocumentAnalysisClient constructor
        with patch("spendoo.ocr.service.DocumentAnalysisClient") as mock_client_class:
            mock_azure_client = MagicMock()
            mock_client_class.return_value = mock_azure_client

            # Setup the mocked response for Azure Form Recognizer
            mock_poller = MagicMock()
            mock_azure_client.begin_analyze_document.return_value = mock_poller
            
            mock_result = MagicMock()
            mock_result.content = "Merchant: Mock Store\nTotal: 100.50\nDate: 2026-06-28\nItem A: 10.50"
            mock_poller.result.return_value = mock_result

            # Instantiate OCRService
            service = OCRService()
            assert service.azureClient is not None

            # Mock fallback methods to ensure they are NOT called
            service.try_gemini_ocr = MagicMock()
            service.try_mistral = MagicMock()

            # Execute extract_text
            items, model = service.extract_text(b"mockimagebytes")

            # Assert Azure OCR was called and returned the expected structure
            mock_azure_client.begin_analyze_document.assert_called_once_with("prebuilt-read", b"mockimagebytes")
            assert model == "azure-form-recognizer"
            assert items == "Merchant: Mock Store\nTotal: 100.50\nDate: 2026-06-28\nItem A: 10.50"

            # Fallbacks should not have been called
            service.try_gemini_ocr.assert_not_called()
            service.try_mistral.assert_not_called()


