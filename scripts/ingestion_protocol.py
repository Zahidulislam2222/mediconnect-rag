"""Stable request syntax verified against LightRAG v1.4.6 document_routes.py."""
TEXT_ROUTE = '/documents/text'
API_KEY_HEADER = 'X-API-Key'


def text_payload(text: str, source: str) -> dict[str, str]:
    return {'text': text, 'file_source': source}


def accepted(body: object) -> bool:
    return (isinstance(body, dict) and body.get('status') == 'success'
            and isinstance(body.get('track_id'), str) and bool(body['track_id'].strip()))
