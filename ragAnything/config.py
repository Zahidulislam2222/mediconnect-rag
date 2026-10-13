"""Construct the optional SDK from validated settings; imports remain inert."""
from settings import ProcessorSettings


def create_rag(settings: ProcessorSettings):
    import numpy as np
    from engine_adapter import ProcessorRuntime
    from gemini_adapter import GeminiAdapter
    from lightrag.utils import wrap_embedding_func_with_attrs
    from raganything import RAGAnything, RAGAnythingConfig

    adapter = GeminiAdapter(settings)
    rag_config = RAGAnythingConfig(
        working_dir=str(settings.working_dir),
        parser_output_dir=str(settings.output_dir),
        parser=settings.parser,
        parse_method=settings.parse_method,
        enable_image_processing=settings.enable_image_processing,
        enable_table_processing=settings.enable_table_processing,
        enable_equation_processing=settings.enable_equation_processing,
        use_full_path=True,
    )
    # The SDK legacy environment alias must not override the validated boundary.
    rag_config.parse_method = settings.parse_method

    async def llm_model_func(prompt, system_prompt=None, history_messages=None,
                             keyword_extraction=False, **kwargs) -> str:
        return await adapter.generate(prompt, system_prompt=system_prompt,
                                      history_messages=history_messages, **kwargs)

    async def vision_model_func(prompt, system_prompt=None, history_messages=None,
                                image_data=None, messages=None, **kwargs) -> str:
        return await adapter.generate(prompt, system_prompt=system_prompt,
            history_messages=history_messages, image_data=image_data, messages=messages, **kwargs)

    @wrap_embedding_func_with_attrs(embedding_dim=settings.embedding_dim,
                                    max_token_size=settings.embedding_max_tokens)
    async def embedding_func(texts: list[str]) -> np.ndarray:
        return await adapter.embed(texts)

    rag = RAGAnything(config=rag_config, llm_model_func=llm_model_func,
                     vision_model_func=vision_model_func, embedding_func=embedding_func,
                     lightrag_kwargs={'llm_model_name': settings.llm_model,
                                      'tiktoken_model_name': settings.tokenizer_model})
    return ProcessorRuntime(rag, adapter)
