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
  HYDE_MODEL      — Model for question generation (default: gemini-2.0-flash-lite)

Compliance:
  - No PHI in prompts (knowledge base docs contain only FAQ/policy text)
  - No cloud resource creation (read files, call Gemini API, write files)
  - One-time ingestion cost, not per-user
"""

import argparse
import glob
import json
import os
import sys
import time

# Gemini API via REST (no heavy SDK dependency)
import urllib.request
import urllib.error


def get_api_key() -> str:
    key = os.getenv("GEMINI_API_KEY")
    if not key:
        print("ERROR: GEMINI_API_KEY environment variable is required", file=sys.stderr)
        sys.exit(1)
    return key


def get_model() -> str:
    return os.getenv("HYDE_MODEL", "gemini-2.0-flash-lite")


def generate_questions(content: str, filename: str, api_key: str, model: str) -> list:
    """Generate 3-5 hypothetical questions for a document using Gemini API."""
    prompt = f"""You are helping improve a healthcare chatbot's search system.
Given this knowledge base document, generate exactly 5 questions that a patient would naturally ask that this document answers.

Rules:
- Questions must be in simple, conversational language (like a real patient would type)
- Questions must be answerable by the document content
- Include variations in phrasing (some short, some longer)
- Do NOT include any personal health information
- Focus on the specific topics covered in this document

Document ({filename}):
---
{content[:3000]}
---

Respond with a JSON array of exactly 5 questions, nothing else:
["question 1", "question 2", "question 3", "question 4", "question 5"]"""

    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"

    payload = json.dumps({
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"maxOutputTokens": 500, "temperature": 0.7}
    }).encode("utf-8")

    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            text = data["candidates"][0]["content"]["parts"][0]["text"]
            # Extract JSON array from response
            text = text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
            questions = json.loads(text)
            if isinstance(questions, list) and len(questions) > 0:
                return questions[:5]
            return []
    except (urllib.error.URLError, json.JSONDecodeError, KeyError, IndexError) as e:
        print(f"  WARNING: Question generation failed for {filename}: {e}", file=sys.stderr)
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
