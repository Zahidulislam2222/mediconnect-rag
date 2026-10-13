"""Pinned RAG-Anything lifecycle and completion protocol; no provider fallback."""
import inspect
from dataclasses import dataclass
from datetime import datetime, timezone
from types import MethodType
from typing import Any

from gemini_adapter import GeminiAdapter


@dataclass
class ProcessorRuntime:
    rag: Any
    provider: GeminiAdapter

    def __post_init__(self):
        # Own this boundary: pinned SDK batch/individual fallback can hide partial
        # storage failures and repeat generation. Never enter that fallback path.
        self.rag._process_multimodal_content = MethodType(self._multimodal, self.rag)
        self.rag._mark_multimodal_processing_complete = MethodType(self._mark_complete, self.rag)

    async def _multimodal(self, rag, multimodal_items, file_path, doc_id,
                          pipeline_status=None, pipeline_status_lock=None):
        if not multimodal_items:
            return
        self.provider.assert_healthy()
        status = await rag.lightrag.doc_status.get_by_id(doc_id)
        if status is None:
            # The pinned text pipeline creates no record for image-only parses.
            from lightrag.base import DocStatus
            now = datetime.now(timezone.utc).isoformat()
            status = {'content_summary': '', 'content_length': 0, 'file_path': file_path,
                'status': DocStatus.PROCESSING, 'created_at': now, 'updated_at': now,
                'chunks_count': 0, 'chunks_list': [], 'metadata': {'multimodal_only': True}}
            await rag.lightrag.full_docs.upsert({doc_id: {'content': '', 'file_path': file_path}})
            await rag.lightrag.full_docs.index_done_callback()
            await rag.lightrag.doc_status.upsert({doc_id: status})
            await rag.lightrag.doc_status.index_done_callback()
        if status and status.get('multimodal_processed') is True:
            return
        existing_count = status.get('chunks_count', 0) if status else 0
        if type(existing_count) is not int or existing_count < 0:
            raise RuntimeError('Invalid knowledge chunk status')
        from raganything.utils import get_processor_for_type

        descriptions = []
        for index, item in enumerate(multimodal_items):
            content_type = item.get('type')
            processor = get_processor_for_type(rag.modal_processors, content_type)
            if processor is None:
                raise RuntimeError('Unsupported document content')
            item_info = {'page_idx': item.get('page_idx', 0), 'index': index, 'type': content_type}
            description, entity_info = await processor.generate_description_only(
                modal_content=item, content_type=content_type, item_info=item_info, entity_name=None)
            self.provider.assert_healthy()
            if not isinstance(description, str) or not description.strip() or not isinstance(entity_info, dict):
                raise RuntimeError('Incomplete document description')
            descriptions.append({'index': index, 'content_type': content_type,
                'description': description, 'entity_info': entity_info, 'original_item': item,
                'item_info': item_info, 'chunk_order_index': existing_count + index,
                'processor': processor, 'file_path': file_path})
        chunks = rag._convert_to_lightrag_chunks_type_aware(descriptions, file_path, doc_id)
        if len(chunks) != len(descriptions):
            raise RuntimeError('Incomplete document chunks')
        await rag._store_chunks_to_lightrag_storage_type_aware(chunks)
        await rag._store_multimodal_main_entities(descriptions, chunks, file_path, doc_id)
        results = await rag._batch_extract_entities_lightrag_style_type_aware(chunks)
        self.provider.assert_healthy()
        enhanced = await rag._batch_add_belongs_to_relations_type_aware(results, descriptions)
        await rag._batch_merge_lightrag_style_type_aware(enhanced, file_path, doc_id)
        self.provider.assert_healthy()
        await self._update_chunks(rag, doc_id, list(chunks))
        self.provider.assert_healthy()
        await rag._mark_multimodal_processing_complete(doc_id)

    async def _update_chunks(self, rag, doc_id, chunk_ids):
        status = await rag.lightrag.doc_status.get_by_id(doc_id)
        if not isinstance(status, dict):
            raise TypeError('Knowledge document status is missing')
        existing = status.get('chunks_list', [])
        count = status.get('chunks_count', 0)
        if not isinstance(existing, list) or type(count) is not int or count < 0:
            raise RuntimeError('Invalid knowledge chunk status')
        await rag.lightrag.doc_status.upsert({doc_id: {**status,
            'chunks_list': existing + chunk_ids, 'chunks_count': count + len(chunk_ids),
            'updated_at': datetime.now(timezone.utc).isoformat()}})
        await rag.lightrag.doc_status.index_done_callback()

    async def _mark_complete(self, rag, doc_id):
        status = await rag.lightrag.doc_status.get_by_id(doc_id)
        if not isinstance(status, dict):
            raise TypeError('Knowledge document status is missing')
        # A text pipeline owns its status; a no-text document completes here.
        if status.get('metadata', {}).get('multimodal_only') is True:
            from lightrag.base import DocStatus
            status = {**status, 'status': DocStatus.PROCESSED}
        await rag.lightrag.doc_status.upsert({doc_id: {**status, 'multimodal_processed': True,
            'updated_at': datetime.now(timezone.utc).isoformat()}})
        await rag.lightrag.doc_status.index_done_callback()

    def _guard_storages(self):
        # Fixed namespace contract of pinned LightRAG1.4.6. Guard actual I/O,
        # including nested SDK helpers that catch and suppress exceptions.
        for name in ('full_docs', 'text_chunks', 'full_entities', 'full_relations',
                     'entities_vdb', 'relationships_vdb', 'chunks_vdb',
                     'chunk_entity_relation_graph', 'llm_response_cache', 'doc_status'):
            storage = getattr(self.rag.lightrag, name, None)
            if storage is None:
                continue
            for method_name in dir(storage):
                if method_name.startswith('_'):
                    continue
                descriptor = inspect.getattr_static(storage, method_name)
                if inspect.iscoroutinefunction(descriptor):
                    method = getattr(storage, method_name)
                    setattr(storage, method_name, self._guard_io(method, method_name))

    def _guard_io(self, method, method_name):
        async def guarded(*args, **kwargs):
            try:
                result = await method(*args, **kwargs)
                if method_name == 'index_done_callback' and result is False:
                    raise RuntimeError('Knowledge storage persistence was not confirmed')
                return result
            except BaseException:
                self.provider.mark_failed()
                raise
        return guarded

    async def initialize(self):
        result = await self.rag._ensure_lightrag_initialized()
        self.provider.assert_healthy()
        if not isinstance(result, dict) or result.get('success') is not True or self.rag.lightrag is None:
            raise RuntimeError('Knowledge storage initialization failed')
        self._guard_storages()

    async def process_document(self, file_path: str, output_dir: str, doc_id: str,
                               parse_method: str | None):
        self.provider.assert_healthy()
        result = await self.rag.process_document_complete(file_path=file_path, output_dir=output_dir,
                                                        doc_id=doc_id, parse_method=parse_method)
        # The pinned ordinary API returns None. It can swallow provider failures,
        # so neither a return value nor a status flag establishes success alone.
        self.provider.assert_healthy()
        if result is not None:
            raise RuntimeError('Unexpected pinned document protocol result')
        status = await self.rag.get_document_processing_status(doc_id)
        if not isinstance(status, dict) or status.get('fully_processed') is not True:
            raise RuntimeError('Document processing was not confirmed')

    async def query(self, question: str, mode: str):
        self.provider.assert_healthy()
        result = await self.rag.aquery(question, mode=mode)
        self.provider.assert_healthy()
        return result

    async def finalize(self):
        await self.rag.finalize_storages()
        self.provider.assert_healthy()
