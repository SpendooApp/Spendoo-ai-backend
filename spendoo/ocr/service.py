import base64
from mistralai import Mistral
from spendoo.core.config import settings
from groq import Groq
import base64

class OCRService:

    def __init__(self):
        self.client = Mistral(api_key=settings.MISTRAL_API_KEY)

    def extract_text(self, base64_image):

        response = self.client.ocr.process(
        model="mistral-ocr-latest",
        document={
            "type": "image_url",
            "image_url": f"data:image/jpeg;base64,{base64_image}"
            },
        # table_format="markdown"
        )

        return "\n\n".join(
                f"### Page {i+1}\n{response.pages[i].markdown}"
                for i in range(len(response.pages))
            )