"""Hierarchical & Semantic Chunker for Legal Statutes, Cases, and Structured Markdown."""
import re
import uuid
from typing import List, Dict, Any, Tuple, Optional
import numpy as np
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.ingestion.metadata_cleaner import sanitize_metadata


class LegalSentenceSplitter:
    """Splits legal text into atomic semantic sentences and clauses without breaking citations or tables."""

    # Common Indian and legal abbreviations that should NOT trigger a sentence split
    LEGAL_ABBREVIATIONS = [
        r"sec\.", r"secs\.", r"art\.", r"arts\.", r"no\.", r"nos\.",
        r"v\.", r"vs\.", r"hon'ble", r"air", r"scc", r"scr", r"ilr",
        r"para\.", r"paras\.", r"cl\.", r"cls\.", r"sub-sec\.", r"sub-secs\.",
        r"ltd\.", r"pvt\.", r"govt\.", r"ors\.", r"anr\.", r"dept\.",
        r"e\.g\.", r"i\.e\.", r"viz\.", r"al\.", r"vol\.", r"cr\.",
        r"c\.p\.c\.", r"cr\.p\.c\.", r"i\.p\.c\.", r"b\.n\.s\.", r"b\.n\.s\.s\."
    ]
    ABBREV_RE = re.compile(r"\b(" + "|".join(LEGAL_ABBREVIATIONS) + r")", re.IGNORECASE)

    # Markdown table row matcher
    MD_TABLE_LINE_RE = re.compile(r"^\s*\|.*?\|\s*$", re.MULTILINE)

    @classmethod
    def split_into_atomic_units(cls, text: str) -> List[str]:
        """Splits text into atomic units (clauses, sentences, tables) preserving structural coherence."""
        if not text or not text.strip():
            return []

        # 1. Protect Markdown Tables by replacing newlines inside tables with a sentinel
        table_blocks = []
        def preserve_tables(match):
            idx = len(table_blocks)
            table_blocks.append(match.group(0))
            return f"__TABLE_BLOCK_{idx}__"

        # Find continuous table blocks (2 or more pipe lines)
        table_pattern = re.compile(r"(?:^\s*\|[^\n]+\|\s*$\n?){2,}", re.MULTILINE)
        protected_text = table_pattern.sub(preserve_tables, text)

        # 2. Protect legal abbreviations by replacing period with sentinel
        def protect_abbrev(match):
            return match.group(0).replace(".", "__DOT__")

        protected_text = cls.ABBREV_RE.sub(protect_abbrev, protected_text)

        # 3. Identify atomic boundary delimiters:
        # - Paragraph breaks: \n\n+
        # - Numbered subclauses: \n\s*\(\d+[A-Za-z]?\)
        # - Lettered clauses: \n\s*\([a-z]\)
        # - Roman subclauses: \n\s*\([ivx]+\)
        # - Provisos: \n\s*(Provided (that|further)|Explanation|Illustration|Exception)
        # - Markdown subheadings: \n#{1,6}\s
        # - Markdown bullet points: \n\s*[\*\-\+]\s+|\n\s*\d+\.\s+
        # - Sentence ends: [.!?]\s+
        split_pattern = re.compile(
            r"(\n\n+)"
            r"|(\n(?=\s*\(\d+[A-Za-z]?\)))"
            r"|(\n(?=\s*\([a-z]\)))"
            r"|(\n(?=\s*\([ivx]+\)))"
            r"|(\n(?=\s*(?:Provided\s+(?:that|further)|Explanation|Illustration|Exception)[\s\d\.\—\-:]*))"
            r"|(\n(?=#{1,6}\s))"
            r"|(\n(?=\s*(?:[\*\-\+]|\d+\.)\s+))"
            r"|((?<=[.!?])\s+(?=[A-Z0-9\"'\(]))"
        )

        raw_parts = split_pattern.split(protected_text)
        units = []
        for p in raw_parts:
            if not p:
                continue
            cleaned = p.replace("__DOT__", ".").strip()
            # Restore tables
            for idx, tbl in enumerate(table_blocks):
                cleaned = cleaned.replace(f"__TABLE_BLOCK_{idx}__", tbl.strip())
            if cleaned:
                units.append(cleaned)

        return units if units else [text.strip()]


class SemanticChunker:
    """
    Groups atomic sentences/clauses into semantically cohesive micro chunks.
    Supports both embedding-driven semantic breakpoint detection and fast structural semantic grouping.
    """

    def __init__(
        self,
        embedding_model: Optional[Any] = None,
        target_chunk_size: int = 500,
        min_chunk_size: int = 180,
        max_chunk_size: int = 650,
        distance_threshold_percentile: float = 78.0
    ):
        self.embedding_model = embedding_model
        self.target_chunk_size = target_chunk_size
        self.min_chunk_size = min_chunk_size
        self.max_chunk_size = max_chunk_size
        self.distance_threshold_percentile = distance_threshold_percentile

    def _compute_cosine_distances(self, embeddings: np.ndarray) -> np.ndarray:
        """Computes cosine distances between consecutive sentence embeddings."""
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1e-10, norms)
        normed = embeddings / norms
        # Dot product of consecutive vectors
        sims = np.sum(normed[:-1] * normed[1:], axis=1)
        # Cosine distance = 1 - cosine similarity
        return 1.0 - sims

    def split_text_semantically(self, text: str) -> List[str]:
        """Performs semantic chunking on text using atomic legal boundary detection and semantic grouping."""
        units = LegalSentenceSplitter.split_into_atomic_units(text)
        if not units:
            return []
        if len(units) == 1:
            return units

        # Fast path if text is short enough to be a single semantic chunk
        if len(text) <= self.target_chunk_size:
            return [text.strip()]

        # Embedding-Driven Semantic Chunking (when embedding model is supplied)
        if self.embedding_model is not None and len(units) >= 3:
            try:
                # Handle SentenceTransformer or LangChain Embeddings
                if hasattr(self.embedding_model, "encode"):
                    embs = self.embedding_model.encode(units, show_progress_bar=False)
                    if not isinstance(embs, np.ndarray):
                        embs = np.array(embs)
                elif hasattr(self.embedding_model, "embed_documents"):
                    raw = self.embedding_model.embed_documents(units)
                    embs = np.array(raw)
                else:
                    embs = None

                if embs is not None and len(embs) > 1:
                    distances = self._compute_cosine_distances(embs)
                    breakpoint_distance = float(np.percentile(distances, self.distance_threshold_percentile))

                    chunks = []
                    current_units = [units[0]]
                    current_len = len(units[0])

                    for i in range(len(distances)):
                        dist = distances[i]
                        next_unit = units[i + 1]
                        next_len = len(next_unit)

                        # Semantic break condition
                        is_semantic_shift = dist >= breakpoint_distance and current_len >= self.min_chunk_size
                        is_overflow = (current_len + next_len) > self.max_chunk_size

                        if (is_semantic_shift or is_overflow) and current_len >= self.min_chunk_size:
                            chunks.append("\n".join(current_units).strip())
                            current_units = [next_unit]
                            current_len = next_len
                        else:
                            current_units.append(next_unit)
                            current_len += next_len + 1

                    if current_units:
                        chunks.append("\n".join(current_units).strip())

                    return [c for c in chunks if c.strip()]
            except Exception:
                # Fallback to structural semantic grouping on any embedding failure
                pass

        # Structural Semantic Grouping (Fast, zero-overhead, highly accurate)
        chunks = []
        current_chunk_parts = []
        current_length = 0

        for unit in units:
            unit_len = len(unit)
            # If adding unit exceeds target size and current chunk is at least min size, flush
            if (current_length + unit_len > self.target_chunk_size) and (current_length >= self.min_chunk_size):
                chunks.append("\n".join(current_chunk_parts).strip())
                # Overlap with the last sentence if meaningful
                if len(current_chunk_parts) > 1 and len(current_chunk_parts[-1]) < 120:
                    current_chunk_parts = [current_chunk_parts[-1], unit]
                    current_length = len(current_chunk_parts[0]) + unit_len + 1
                else:
                    current_chunk_parts = [unit]
                    current_length = unit_len
            else:
                current_chunk_parts.append(unit)
                current_length += unit_len + 1

        if current_chunk_parts:
            chunks.append("\n".join(current_chunk_parts).strip())

        return [c for c in chunks if c.strip()]


class HierarchicalChunker:
    """
    Hierarchical Parent/Child Chunker with Semantic Micro Chunking.
    - Parent (Macro): Complete legal provision, article, section, or markdown heading scope (~2000 chars).
    - Child (Micro): Semantically grouped coherent statutory units (~500 chars) carrying contextual anchors.
    """

    def __init__(
        self,
        embedding_model: Optional[Any] = None,
        parent_chunk_size: int = 2000,
        parent_chunk_overlap: int = 200,
        child_chunk_size: int = 500,
        child_chunk_overlap: int = 80
    ):
        self.embedding_model = embedding_model
        legal_separators = [
            "\n\nSection ", "\n\nArticle ", "\n\nRule ", "\n\nOrder ",
            "\n\nRegulation ", "\n\nSchedule ", "\nSection ", "\nArticle ",
            "\nRule ", "\n\n(", "\n(", "\n\n", "\n", ". ", " "
        ]
        self.parent_splitter = RecursiveCharacterTextSplitter(
            chunk_size=parent_chunk_size,
            chunk_overlap=parent_chunk_overlap,
            separators=legal_separators
        )
        self.semantic_child_chunker = SemanticChunker(
            embedding_model=embedding_model,
            target_chunk_size=child_chunk_size,
            min_chunk_size=180,
            max_chunk_size=650
        )

    def chunk_blocks(
        self,
        blocks: List[Dict[str, Any]],
        embedding_model: Optional[Any] = None
    ) -> Tuple[List[Document], List[Document]]:
        """Generates hierarchically linked Parent (Macro) and Child (Micro Semantic) Documents."""
        active_semantic_chunker = self.semantic_child_chunker
        if embedding_model is not None:
            active_semantic_chunker = SemanticChunker(
                embedding_model=embedding_model,
                target_chunk_size=self.semantic_child_chunker.target_chunk_size
            )

        parents: List[Document] = []
        children: List[Document] = []

        for b in blocks:
            meta = dict(b.get("metadata", {}))
            body = b.get("body", "").strip()
            if not body:
                continue

            pid = meta.get("legal_reference") or f"LEGAL-{uuid.uuid4().hex[:8]}"
            meta["parent_id"] = pid
            act_name = meta.get("act_name") or meta.get("document_name") or "Statute"
            hierarchy_path = meta.get("hierarchy_path") or ""

            # 1. Parent Macro Chunks (Full Legal Section / Scope)
            parent_splits = self.parent_splitter.split_text(body)
            for p_idx, p_text in enumerate(parent_splits):
                p_meta = dict(meta)
                p_meta["chunk_type"] = "parent"
                p_meta["parent_split_index"] = p_idx
                p_meta["is_semantic"] = False
                parents.append(Document(page_content=p_text, metadata=sanitize_metadata(p_meta)))

            # 2. Child Micro Chunks via Semantic Chunking
            child_splits = active_semantic_chunker.split_text_semantically(body)
            total_children = len(child_splits)

            for c_idx, c_text in enumerate(child_splits):
                c_meta = dict(meta)
                c_meta["chunk_type"] = "child"
                c_meta["child_index"] = c_idx
                c_meta["total_child_splits"] = total_children
                c_meta["is_semantic"] = True

                # Contextual breadcrumb tag
                context_tag = f"[Act: {act_name} | Ref: {pid}"
                if hierarchy_path:
                    context_tag += f" | Scope: {hierarchy_path}"
                context_tag += "]"

                chunk_content = f"{context_tag}\n{c_text}"
                children.append(Document(page_content=chunk_content, metadata=sanitize_metadata(c_meta)))

        return parents, children


# Alias for explicit import
HierarchicalSemanticChunker = HierarchicalChunker
