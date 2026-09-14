#!/usr/bin/env python3
"""
HyDE — Hypothetical Question Generation for RAG Ingestion

Generates 3-5 hypothetical patient questions per knowledge base document.
Appends questions to augmented copies (originals preserved).
Improves retrieval by enabling question-to-question matching.

Usage:
  python3 scripts/generate-questions.py --dir knowledge/medical/faqs/
  python3 scripts/generate-questions.py --file knowledge/medical/faqs/appointments.md
  python3 scripts/generate-questions.py --dir knowledge/medical/faqs/ --output knowledge/medical/augmented/faqs/

Environment:
  GEMINI_API_KEY  — Required (same key used by LightRAG)
  HYDE_MODEL      — Required configured model for question generation

Compliance:
  - Operator must ensure inputs are approved public knowledge, without PHI
  - No cloud resource creation (read files, call Gemini API, write files)
  - One-time ingestion cost, not per-user
"""

import argparse
import glob
import json
import os
import sys
import time

# HTTPS-only transport; keys are sent in a header, never a URL.
import requests
from urllib.parse import urlsplit, quote
from hyde_config import load_settings


def get_api_key() -> str:
    return load_settings().api_key


def get_model() -> str:
    return load_settings().model


def generate_questions(content: str, filename: str, api_key: str, model: str) -> list:
    settings = load_settings()
    endpoint = urlsplit(settings.api_base)
    if endpoint.scheme != 'https' or not endpoint.hostname or endpoint.username or endpoint.password:
        raise ValueError('HyDE requires an HTTPS provider endpoint without embedded credentials')
    prompt = settings.prompt.format(filename=filename, content=content[:settings.content_characters], question_count=settings.question_count)
    payload = json.dumps({'contents': [{'parts': [{'text': prompt}]}], 'generationConfig': {'maxOutputTokens': settings.max_output_tokens, 'temperature': settings.temperature}})
    try:
        route = f"{endpoint.path.rstrip('/')}/{settings.api_version}/models/{quote(model, safe='')}:generateContent"
        # Requests manages certificate/hostname verification and connection cleanup.
        # Redirects are refused so the API-key header cannot follow another origin.
        with requests.post(f'https://{endpoint.netloc}{route}', data=payload.encode('utf-8'),
                           headers={'Content-Type': 'application/json', 'x-goog-api-key': api_key},
                           timeout=settings.timeout_seconds, verify=True, allow_redirects=False) as response:
            if response.status_code != 200:
                raise ValueError('Provider rejected generation')
            data = response.json()
        text = data['candidates'][0]['content']['parts'][0]['text'].strip()
        if text.startswith('```'):
            text = text.split('\n', 1)[1].rsplit('```', 1)[0].strip()
        questions = json.loads(text)
        if not isinstance(questions, list) or len(questions) != settings.question_count or not all(isinstance(q, str) and q.strip() for q in questions):
            raise ValueError('Invalid generated question list')
        return questions
    except (requests.RequestException, OSError, ValueError, KeyError, IndexError, TypeError):
        print('WARNING: Question generation failed; no provider response or credentials logged.', file=sys.stderr)
        return []


def augment_document(filepath: str, api_key: str, model: str) -> str:
    """Read document, generate questions, return augmented content."""
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    filename = os.path.basename(filepath)
    questions = generate_questions(content, filename, api_key, model)

    if not questions:
        return content  # Return original if generation failed

    # Append questions section
    questions_section = "\n\n## Related Questions Patients Might Ask\n\n"
    for q in questions:
        questions_section += f"- {q}\n"

    return content + questions_section


def process_file(filepath: str, output_dir: str, api_key: str, model: str) -> bool:
    """Process a single file and write augmented version."""
    filename = os.path.basename(filepath)
    print(f"  Processing: {filename} ... ", end="", flush=True)

    augmented = augment_document(filepath, api_key, model)

    # Write to output directory
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, filename)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(augmented)

    print("OK")
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Generate hypothetical questions for RAG knowledge base documents"
    )
    parser.add_argument("--file", help="Process a single .md file")
    parser.add_argument("--dir", help="Process all .md files in directory")
    parser.add_argument(
        "--output", "-o",
        help="Output directory for augmented files (default: <input_dir>/augmented/)",
    )

    args = parser.parse_args()

    if not args.file and not args.dir:
        parser.print_help()
        sys.exit(1)

    api_key = get_api_key()
    model = get_model()

    print(f"HyDE Question Generator")
    print(f"  Model: {model}")
    print()

    files = []
    if args.file:
        files = [args.file]
        default_output = os.path.join(os.path.dirname(args.file), "augmented")
    else:
        files = sorted(glob.glob(os.path.join(args.dir, "**", "*.md"), recursive=True))
        default_output = os.path.join(args.dir, "augmented")

    output_dir = args.output or default_output

    if not files:
        print(f"No .md files found")
        sys.exit(0)

    print(f"  Found {len(files)} files to process")
    print(f"  Output: {output_dir}")
    print()

    succeeded = 0
    failed = 0

    for filepath in files:
        try:
            if process_file(filepath, output_dir, api_key, model):
                succeeded += 1
            else:
                failed += 1
        except Exception as e:
            print(f"ERROR: {e}", file=sys.stderr)
            failed += 1

        # Rate limit: 1 request per second to avoid API throttling
        time.sleep(1)

    print()
    print(f"Complete: {succeeded} succeeded, {failed} failed")
    print(f"Augmented files in: {output_dir}")


if __name__ == "__main__":
    main()
