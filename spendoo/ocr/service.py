from flask import json
from mistralai import Mistral
from spendoo.core.config import settings
import base64
from google import genai
from google.genai import types
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential

class OCRService:

    def __init__(self):
        self.mistralClient = Mistral(api_key=settings.MISTRAL_API_KEY)
        self.geminiClient = genai.Client(api_key=settings.GEMINI_API_KEY)
        self.geminiModels = settings.GEMINI_OCR_MODELS
        self.prompt = settings.OCR_PROMPT

        if settings.AZURE_ENDPOINT and settings.AZURE_KEY:
            self.azureClient = DocumentAnalysisClient(
                endpoint=settings.AZURE_ENDPOINT,
                credential=AzureKeyCredential(settings.AZURE_KEY)
            )
        else:
            self.azureClient = None


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


    def try_azure_ocr(self, image_bytes: bytes):
        if not self.azureClient:
            raise ValueError("Azure Form Recognizer client is not initialized.")
        poller = self.azureClient.begin_analyze_document("prebuilt-read", image_bytes)
        result = poller.result()
        return result.content




    def extract_text(self, image_bytes):
        # Try Azure Form Recognizer first
        if self.azureClient:
            try:
                items = self.try_azure_ocr(image_bytes)
                if items:
                    return items, "azure-form-recognizer"
            except Exception as e:
                print(f"Azure OCR failed, falling back: {e}")
        
        # Try Gemini models next
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

