"""
RAG-Anything document processor.

Usage:
  # Process a single document
  docker compose run raganything /app/data/inputs/document.pdf

  # Process all files in a directory
  docker compose run raganything --dir /app/data/inputs/

  # Query after processing
  docker compose run raganything --query "What are the main findings?"
"""

import asyncio
import argparse
import os
import sys
import glob
from pathlib import Path

from raganything import RAGAnything
from config import rag_config, llm_model_func, vision_model_func, embedding_func


async def process_document(rag: RAGAnything, file_path: str, output_dir: str):
    """Process a single document through RAG-Anything."""
    print(f"Processing: {file_path}")
    try:
        await rag.process_document_complete(
            file_path=file_path,
            output_dir=output_dir,
            parse_method="auto",
        )
        print(f"Done: {file_path}")
    except Exception as e:
        print(f"Error processing {file_path}: {e}", file=sys.stderr)


async def process_directory(rag: RAGAnything, dir_path: str, output_dir: str):
    """Process all supported documents in a directory."""
    supported_extensions = [
        "*.pdf", "*.docx", "*.doc", "*.pptx", "*.ppt",
        "*.xlsx", "*.xls", "*.txt", "*.md", "*.html",
        "*.png", "*.jpg", "*.jpeg", "*.bmp", "*.tiff",
    ]
    files = []
    for ext in supported_extensions:
        files.extend(glob.glob(os.path.join(dir_path, ext)))

    if not files:
        print(f"No supported documents found in {dir_path}")
        return

    print(f"Found {len(files)} documents to process")
    for f in files:
        await process_document(rag, f, output_dir)

    print(f"All {len(files)} documents processed.")


async def query(rag: RAGAnything, question: str, mode: str = "hybrid"):
    """Query the processed knowledge base."""
    print(f"Query: {question}")
    print(f"Mode: {mode}")
    print("---")

    result = await rag.aquery(question, mode=mode)
    print(result)
    return result


async def main():
    parser = argparse.ArgumentParser(description="RAG-Anything Document Processor")
    parser.add_argument("file", nargs="?", help="Path to document to process")
    parser.add_argument("--dir", help="Process all documents in directory")
    parser.add_argument("--query", "-q", help="Query the knowledge base")
    parser.add_argument("--mode", default="hybrid",
                        choices=["naive", "local", "global", "hybrid"],
                        help="Query mode (default: hybrid)")
    parser.add_argument("--output", "-o", default="/app/output",
                        help="Output directory for parsed content")

    args = parser.parse_args()

    if not any([args.file, args.dir, args.query]):
        parser.print_help()
        sys.exit(1)

    # Initialize RAG-Anything
    rag = RAGAnything(
        config=rag_config,
        llm_model_func=llm_model_func,
        vision_model_func=vision_model_func,
        embedding_func=embedding_func,
    )

    if args.file:
        await process_document(rag, args.file, args.output)
    elif args.dir:
        await process_directory(rag, args.dir, args.output)

    if args.query:
        await query(rag, args.query, args.mode)


if __name__ == "__main__":
    asyncio.run(main())
