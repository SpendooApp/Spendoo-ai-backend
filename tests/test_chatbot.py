import pytest
from unittest.mock import patch, MagicMock
import uuid
import json
from spendoo.chatbot.service import ChatbotService
from spendoo.chatbot.models import ChatRequest

@patch('spendoo.chatbot.service.LLMClient')
def test_chatbot_process_chat(mock_llm_class):
    mock_db = MagicMock()
    mock_llm = MagicMock()
    mock_llm_class.return_value = mock_llm
    
    mock_llm_response = MagicMock()
    mock_llm_response.content = json.dumps({
        "response": "Hello World",
        "chatSummary": "User said hi"
    })
    mock_llm_response.tool_calls = []
    
    mock_llm.chat_with_tools.return_value = mock_llm_response
    
    service = ChatbotService(mock_db)
    request = ChatRequest(
        userId=uuid.uuid4(),
        message="Hi",
        chatSummary="",
        timezone="UTC"
    )
    
    response = service.process_chat(request)
    
    assert response.response == "Hello World"
    assert response.chatSummary == "User said hi"
    mock_llm.chat_with_tools.assert_called_once()


