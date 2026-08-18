from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
import re
from threading import Lock


DOCS_ROOT = Path(__file__).resolve().parents[3] / "docs"


@dataclass(frozen=True)
class IndexedDoc:
    category: str
    slug: str
    title: str
    body: str
    path: str


class DocumentationIndexService:
    def __init__(self) -> None:
        self._lock = Lock()
        self._docs: list[IndexedDoc] = []
        self._last_indexed_at: datetime | None = None

    def refresh_if_stale(self, *, max_age: timedelta = timedelta(hours=1)) -> None:
        with self._lock:
            now = datetime.now(UTC)
            if self._last_indexed_at and now - self._last_indexed_at < max_age:
                return
            self._docs = self._load_docs()
            self._last_indexed_at = now

    def search(self, query: str) -> list[dict[str, str]]:
        self.refresh_if_stale()
        needle = query.strip().lower()
        if not needle:
            return []
        ranked: list[tuple[int, IndexedDoc]] = []
        for doc in self._docs:
            score = doc.body.lower().count(needle) + doc.title.lower().count(needle) * 2
            if score > 0:
                ranked.append((score, doc))
        ranked.sort(key=lambda item: item[0], reverse=True)
        return [
            {
                "category": doc.category,
                "slug": doc.slug,
                "title": doc.title,
                "path": doc.path,
            }
            for _score, doc in ranked
        ]

    def categories(self) -> list[str]:
        self.refresh_if_stale()
        return sorted({doc.category for doc in self._docs})

    def docs_in_category(self, category: str) -> list[dict[str, str]]:
        self.refresh_if_stale()
        slug = category.strip().lower()
        docs = [doc for doc in self._docs if doc.category == slug]
        return [{"slug": doc.slug, "title": doc.title, "path": doc.path} for doc in docs]

    @staticmethod
    def _derive_category(file_name: str) -> str:
        stem = Path(file_name).stem.lower()
        if "faq" in stem:
            return "faq"
        if "guide" in stem:
            return "guides"
        if "troubleshooting" in stem:
            return "troubleshooting"
        if "launch" in stem or "incident" in stem or "oncall" in stem:
            return "operations"
        if "community" in stem:
            return "community"
        return "general"

    def _load_docs(self) -> list[IndexedDoc]:
        docs: list[IndexedDoc] = []
        if not DOCS_ROOT.exists():
            return docs

        for path in sorted(DOCS_ROOT.glob("*.md")):
            body = path.read_text(encoding="utf-8")
            title = self._extract_title(body) or path.stem.replace("-", " ").title()
            docs.append(
                IndexedDoc(
                    category=self._derive_category(path.name),
                    slug=path.stem,
                    title=title,
                    body=body,
                    path=str(path),
                )
            )
        return docs

    @staticmethod
    def _extract_title(markdown: str) -> str | None:
        match = re.search(r"^#\s+(.+)$", markdown, re.MULTILINE)
        if not match:
            return None
        return match.group(1).strip()


_docs_index_service: DocumentationIndexService | None = None
_docs_index_lock = Lock()


def get_docs_index_service() -> DocumentationIndexService:
    global _docs_index_service
    if _docs_index_service is None:
        with _docs_index_lock:
            if _docs_index_service is None:
                _docs_index_service = DocumentationIndexService()
    return _docs_index_service
