"""Gemini SDK adapter; no provider import or client creation at module import."""
import asyncio
import base64
import binascii
from typing import Any

from settings import IMAGE_MIME_TYPES, ProcessorSettings


class GeminiAdapter:
    def __init__(self, settings: ProcessorSettings):
        self.settings = settings
        self._failed = False
        self._request_lock = asyncio.Lock()

    def mark_failed(self):
        self._failed = True

    def assert_healthy(self):
        if self._failed:
            raise RuntimeError('Provider operation failed; no further requests allowed')

    async def generate(self, *args, **kwargs) -> str:
        async with self._request_lock:
            self.assert_healthy()
            try:
                return await self._generate(*args, **kwargs)
            except (Exception, asyncio.CancelledError):
                self._failed = True
                raise

    async def embed(self, texts: list[str]):
        async with self._request_lock:
            self.assert_healthy()
            try:
                return await self._embed(texts)
            except (Exception, asyncio.CancelledError):
                self._failed = True
                raise

    def client(self):
        from google import genai
        from google.genai import types
        provider = self.settings.provider
        return genai.Client(vertexai=False, api_key=self.settings.api_key,
                            http_options=types.HttpOptions(
                                base_url=provider.base_url, api_version=provider.api_version,
                                timeout=provider.timeout_ms,
                                # One total attempt prevents retries of ambiguous billable requests.
                                retry_options=types.HttpRetryOptions(attempts=1),
                                client_args={'follow_redirects': False},
                                async_client_args={'follow_redirects': False}))

    def text_part(self, text: str):
        from google.genai import types
        if not isinstance(text, str) or len(text) > self.settings.provider.max_text_characters:
            raise ValueError('Invalid provider text input')
        return types.Part.from_text(text=text)

    def image_part(self, image: str):
        from google.genai import types
        if not isinstance(image, str):
            raise TypeError('Invalid inline image')
        mime = self.settings.provider.image_mime_type
        encoded = image
        if image.startswith('data:'):
            header, separator, encoded = image.partition(',')
            if not separator or not header.endswith(';base64'):
                raise ValueError('Invalid inline image')
            mime = header[5:-7]
        if mime not in IMAGE_MIME_TYPES or len(encoded) > 4 * ((self.settings.provider.max_image_bytes + 2) // 3):
            raise ValueError('Invalid inline image type or limit')
        try:
            data = base64.b64decode(encoded, validate=True)
        except (ValueError, binascii.Error) as exc:
            raise ValueError('Invalid inline image encoding') from exc
        if not data or len(data) > self.settings.provider.max_image_bytes:
            raise ValueError('Invalid inline image size')
        return types.Part.from_bytes(data=data, mime_type=mime)

    def message(self, message: dict[str, Any]):
        from google.genai import types
        role = message.get('role')
        if role not in ['user', 'assistant']:
            raise ValueError('Unsupported provider message role')
        content = message.get('content')
        if isinstance(content, str):
            parts = [self.text_part(content)]
        elif isinstance(content, list) and content:
            parts = []
            for item in content:
                if item.get('type') == 'text':
                    parts.append(self.text_part(item['text']))
                elif item.get('type') == 'image_url':
                    # Accept inline data only. No remote URL fetches or filesystem access.
                    url = item['image_url']['url']
                    if not isinstance(url, str) or not url.startswith('data:'):
                        raise ValueError('Remote provider images are not supported')
                    parts.append(self.image_part(url))
                else:
                    raise ValueError('Unsupported provider message part')
        else:
            raise ValueError('Invalid provider message')
        return types.Content(role='model' if role == 'assistant' else 'user', parts=parts)

    async def _generate(self, prompt, system_prompt=None, history_messages=None,
                       image_data=None, messages=None, **kwargs) -> str:
        import httpx
        from google.genai import types
        from google.genai.errors import APIError
        contents = [self.message(message) for message in (history_messages or [])]
        if messages is not None:
            if contents or image_data is not None:
                raise ValueError('Ambiguous provider message inputs')
            for message in messages:
                if message.get('role') == 'system':
                    if system_prompt is not None:
                        raise ValueError('Ambiguous provider system instructions')
                    system_prompt = message.get('content')
                    self.text_part(system_prompt)
                else:
                    contents.append(self.message(message))
        else:
            parts = [self.text_part(prompt)]
            if image_data is not None:
                parts.append(self.image_part(image_data))
            contents.append(types.Content(role='user', parts=parts))
        if not contents:
            raise ValueError('Empty provider messages')
        if system_prompt is not None:
            self.text_part(system_prompt)
        provider = self.settings.provider
        client = self.client()
        try:
            response = await client.aio.models.generate_content(
                model=self.settings.llm_model, contents=contents,
                config=types.GenerateContentConfig(system_instruction=system_prompt,
                    temperature=provider.temperature, max_output_tokens=provider.max_output_tokens))
            text = response.text
            if not isinstance(text, str) or not text.strip() or len(text) > provider.max_response_characters:
                raise ValueError('Provider returned no bounded text answer')
            return text
        except (APIError, httpx.HTTPError, TimeoutError) as exc:
            raise RuntimeError('Provider generation request failed') from exc
        finally:
            try:
                await client.aio.aclose()
            finally:
                client.close()

    async def _embed(self, texts: list[str]):
        import httpx
        import numpy as np
        from google.genai import types
        from google.genai.errors import APIError
        if not texts or len(texts) > self.settings.provider.max_embedding_batch:
            raise ValueError('Invalid embedding batch')
        for text in texts:
            self.text_part(text)
        client = self.client()
        try:
            response = await client.aio.models.embed_content(
                model=self.settings.embedding_model, contents=texts,
                config=types.EmbedContentConfig(output_dimensionality=self.settings.embedding_dim))
            vectors = np.asarray([item.values for item in response.embeddings or []], dtype=float)
            if vectors.shape != (len(texts), self.settings.embedding_dim) or not np.isfinite(vectors).all():
                raise ValueError('Provider returned incompatible embeddings')
            return vectors
        except (APIError, httpx.HTTPError, TimeoutError) as exc:
            raise RuntimeError('Provider embedding request failed') from exc
        finally:
            try:
                await client.aio.aclose()
            finally:
                client.close()
