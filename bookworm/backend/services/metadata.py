import io
import re
from pathlib import Path
from typing import Dict, Any, Optional

import httpx


def extract_epub_metadata(path: str) -> Dict[str, Any]:
    import ebooklib
    from ebooklib import epub

    meta: Dict[str, Any] = {
        "title": None,
        "author": None,
        "isbn": None,
        "description": None,
        "cover_bytes": None,
        "total_pages": None,
        "total_words": None,
        "genres": [],
    }

    try:
        book = epub.read_epub(path)

        # Title
        titles = book.get_metadata("DC", "title")
        if titles:
            meta["title"] = titles[0][0]

        # Author
        creators = book.get_metadata("DC", "creator")
        if creators:
            meta["author"] = creators[0][0]

        # ISBN / identifier
        identifiers = book.get_metadata("DC", "identifier")
        for ident, attrs in identifiers:
            if "isbn" in str(attrs).lower() or re.match(r"^97[89]\d{10}$", str(ident).strip()):
                meta["isbn"] = str(ident).strip()
                break

        # Description
        descs = book.get_metadata("DC", "description")
        if descs:
            meta["description"] = descs[0][0]

        # Subject / genres
        subjects = book.get_metadata("DC", "subject")
        meta["genres"] = [s[0] for s in subjects if s]

        # Cover image
        for item in book.get_items():
            if item.get_type() == ebooklib.ITEM_COVER:
                meta["cover_bytes"] = item.get_content()
                break
        # Fallback: look for cover in images
        if not meta["cover_bytes"]:
            for item in book.get_items_of_type(ebooklib.ITEM_IMAGE):
                name = item.get_name().lower()
                if "cover" in name:
                    meta["cover_bytes"] = item.get_content()
                    break

        # Estimate word count from HTML items
        total_words = 0
        for item in book.get_items_of_type(ebooklib.ITEM_DOCUMENT):
            content = item.get_content().decode("utf-8", errors="ignore")
            # Strip HTML tags
            text = re.sub(r"<[^>]+>", " ", content)
            words = len(text.split())
            total_words += words
        meta["total_words"] = total_words if total_words > 0 else None

    except Exception:
        pass

    return meta


def extract_pdf_metadata(path: str) -> Dict[str, Any]:
    meta: Dict[str, Any] = {
        "title": None,
        "author": None,
        "isbn": None,
        "description": None,
        "cover_bytes": None,
        "total_pages": None,
        "total_words": None,
        "genres": [],
    }

    try:
        import fitz  # PyMuPDF

        doc = fitz.open(path)
        pdf_meta = doc.metadata

        meta["title"] = pdf_meta.get("title") or None
        meta["author"] = pdf_meta.get("author") or None
        meta["total_pages"] = doc.page_count

        # Extract text for word count
        total_words = 0
        for page in doc:
            text = page.get_text()
            total_words += len(text.split())
        meta["total_words"] = total_words if total_words > 0 else None

        # Extract first page as cover image
        if doc.page_count > 0:
            page = doc[0]
            mat = fitz.Matrix(1.5, 1.5)
            pix = page.get_pixmap(matrix=mat)
            meta["cover_bytes"] = pix.tobytes("jpeg")

        doc.close()
    except Exception:
        pass

    return meta


def fetch_openlibrary_cover(isbn_or_title: str) -> Optional[bytes]:
    try:
        # Try ISBN first
        if re.match(r"^97[89]\d{10}$", str(isbn_or_title).strip()):
            url = f"https://covers.openlibrary.org/b/isbn/{isbn_or_title}-L.jpg"
        else:
            # Search by title
            search_url = "https://openlibrary.org/search.json"
            resp = httpx.get(search_url, params={"q": isbn_or_title, "limit": 1}, timeout=10.0)
            resp.raise_for_status()
            data = resp.json()
            docs = data.get("docs", [])
            if not docs:
                return None
            cover_id = docs[0].get("cover_i")
            if not cover_id:
                return None
            url = f"https://covers.openlibrary.org/b/id/{cover_id}-L.jpg"

        resp = httpx.get(url, timeout=10.0, follow_redirects=True)
        if resp.status_code == 200 and len(resp.content) > 1000:
            return resp.content
    except Exception:
        pass
    return None
