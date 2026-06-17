from flask import json
from mistralai import Mistral
from spendoo.core.config import settings
import base64
from google import genai
from google.genai import types

class OCRService:

    def __init__(self):
        self.mistralClient = Mistral(api_key=settings.MISTRAL_API_KEY)
        self.geminiClient = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.geminiModels = settings.GEMINI_OCR_MODELS
        self.prompt = settings.OCR_PROMPT


    def parse_json(self, response: str):
        try:
            cleaned_response = response.strip().removeprefix("```json").removesuffix("```").strip()
            return json.loads(cleaned_response)
        except json.JSONDecodeError as e:
            print(f"JSON decoding error: {e}")
            return None
        

    def try_gemini_ocr(self, model: str, image_bytes: bytes):
        response = self.geminiClient.models.generate_content(
            model=model,
            contents=[
            types.Part.from_bytes(data=image_bytes, mime_type="image/jpeg"),
            self.prompt
        ]
        )
        return self.parse_json(response.text)
    

    def try_mistral(self, image_bytes: bytes):
        b64 = base64.b64encode(image_bytes).decode()
        ocr_response = self.mistralClient.ocr.process(
            model="mistral-ocr-latest",
            document={
                "type": "image_url",
                "image_url": f"data:image/jpeg;base64,{b64}"
                },
        )
        ocr_text = "\n\n".join(
            f"### Page {i + 1}\n{ocr_response.pages[i].markdown}"
            for i in range(len(ocr_response.pages))
        )

        # Step 2: Parse items from OCR text using a Mistral chat model
        parse_response = self.mistralClient.chat.complete(
            model="mistral-small-latest",
            messages=[{
                "role": "user",
                "content": f"Receipt text:\n{ocr_text}\n\n{self.prompt}"
            }]
        )
        return self.parse_json(parse_response.choices[0].message.content)


    def extract_text(self, image_bytes):
        
        # Try Gemini models first
        for model in self.geminiModels:
            try:
                items = self.try_gemini_ocr(model, image_bytes)
                return items, model
            except Exception as e:
                continue
        
        # Final fallback: Mistral OCR pipeline
        try:
            items = self.try_mistral(image_bytes)
            return items, "mistral-ocr-latest"
        except Exception as e:
            raise RuntimeError("Receipt extraction failed across all models.") from e
