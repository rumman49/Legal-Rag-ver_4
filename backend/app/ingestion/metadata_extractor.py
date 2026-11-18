"""Comprehensive Legal Hierarchy Parser for Indian Law Statutes, Markdown files, Scraped Datasets & Crosswalks."""
import re
from typing import Dict, Any, List, Optional
from app.ingestion.metadata_cleaner import LegalMetadata, make_legal_reference, sanitize_metadata


class LegalHierarchyParser:
    """Extracts exhaustive statutory metadata fields across Indian legal structures, Markdown documents, and IndiaCode schemas."""

    PART_RE = re.compile(r"(?:PART)\s+([IVXLCDM\d]+)[\s:\-–—]*(.*?)(?=\n|$)", re.IGNORECASE)
    CHAPTER_RE = re.compile(r"(?:CHAPTER)\s+([IVXLCDM\d]+)[\s:\-–—]*(.*?)(?=\n|$)", re.IGNORECASE)
    ORDER_RE = re.compile(r"(?:ORDER)\s+([IVXLCDM\d]+)[\s:\-–—]*(.*?)(?=\n|$)", re.IGNORECASE)
    SECTION_RE = re.compile(r"(?:SECTION|SEC\.?)\s+(\d+[A-Z]*)[\s:\.\-–—]*(.*?)(?=\n|$)", re.IGNORECASE)
    ARTICLE_RE = re.compile(r"(?:ARTICLE|ART\.?)\s+(\d+[A-Z]*)[\s:\.\-–—]*(.*?)(?=\n|$)", re.IGNORECASE)
    RULE_RE = re.compile(r"(?:RULE)\s+(\d+[A-Z]*)[\s:\.\-–—]*(.*?)(?=\n|$)", re.IGNORECASE)
    REGULATION_RE = re.compile(r"(?:REGULATION|REG\.?)\s+(\d+[A-Z]*)[\s:\.\-–—]*(.*?)(?=\n|$)", re.IGNORECASE)
    SCHEDULE_RE = re.compile(r"(?:SCHEDULE)\s+([IVXLCDM\d]+)[\s:\-–—]*(.*?)(?=\n|$)", re.IGNORECASE)

    SUBSECTION_RE = re.compile(r"\(\s*(\d+[A-Z]?)\s*\)")
    CLAUSE_RE = re.compile(r"\(\s*([a-z])\s*\)")
    SUBCLAUSE_RE = re.compile(r"\(\s*([ivx]+|\d+)\s*\)")

    MD_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)(?:\s+#*)?$", re.MULTILINE)
    MD_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)

    # Crosswalk & Legal Attribute Extractors
    CROSSWALK_RE = re.compile(
        r"(?:corresponds?\s+to|corresponding\s+to|earlier\s+law|old\s+law|previously|repealed)\s*(?:section|sec\.?)?\s*(\d+[A-Z]*)\s*(?:of\s+)?(IPC|CrPC|IEA|Indian\s+Penal\s+Code|Code\s+of\s+Criminal\s+Procedure|Indian\s+Evidence\s+Act)?",
        re.IGNORECASE
    )
    BRACKET_CROSSWALK_RE = re.compile(
        r"\[(?:corresponds?\s+to\s+)?(IPC|CrPC|IEA)\s*(?:sec\.?|section)?\s*(\d+[A-Z]*)\]",
        re.IGNORECASE
    )
    PUNISHMENT_IMPRISON_RE = re.compile(
        r"imprisonment\s+(?:for\s+a\s+term\s+which\s+may\s+extend\s+to\s+)?(\d+)\s+years?",
        re.IGNORECASE
    )
    PUNISHMENT_LIFE_RE = re.compile(r"imprisonment\s+for\s+life", re.IGNORECASE)
    PUNISHMENT_DEATH_RE = re.compile(r"\b(?:death\s+penalty|sentence\s+of\s+death)\b", re.IGNORECASE)
    PUNISHMENT_FINE_RE = re.compile(r"\b(?:with\s+fine|and\s+fine|or\s+fine|liable\s+to\s+fine)\b", re.IGNORECASE)
    EXPLANATION_RE = re.compile(r"Explanation(?:\s+(\d+))?[\s\.\—\-:]*", re.IGNORECASE)
    ILLUSTRATION_RE = re.compile(r"Illustration(?:\s*\(?([a-z\d]+)\)?)?[\s\.\—\-:]*", re.IGNORECASE)
    PROVISO_RE = re.compile(r"Provided\s+(?:that|further)", re.IGNORECASE)

    @classmethod
    def extract_act_info(cls, text: str, document_name: str) -> tuple[str, str | None]:
        """Detects Act/Statute Name and Act Year from headers or document name."""
        lines = [line.strip() for line in text[:2500].splitlines() if line.strip()]
        clean_doc = document_name.rsplit(".", 1)[0].replace("_", " ").title()
        act_name = clean_doc
        act_year = None

        for line in lines:
            if re.search(r"\b(ACT|SANHITA|CONSTITUTION|CODE|RULES|REGULATIONS|ORDINANCE|ADHINIYAM)\b", line, re.IGNORECASE):
                cleaned = re.sub(r"^[#\s\*_]+|[^\w\s\(\),]+$", "", line)
                if len(cleaned) < 130 and len(cleaned) > 3:
                    act_name = cleaned
                year_match = re.search(r"\b(18\d{2}|19\d{2}|20\d{2})\b", line)
                if year_match:
                    act_year = year_match.group(1)
                break

        if not act_year:
            year_match = re.search(r"\b(18\d{2}|19\d{2}|20\d{2})\b", text[:2000])
            if year_match:
                act_year = year_match.group(1)

        return act_name, act_year

    @classmethod
    def parse_frontmatter(cls, text: str) -> tuple[dict, str]:
        """Extracts YAML/JSON frontmatter from markdown files if present."""
        fm_match = cls.MD_FRONTMATTER_RE.match(text)
        metadata = {}
        content = text
        if fm_match:
            fm_text = fm_match.group(1)
            content = text[fm_match.end():]
            for line in fm_text.splitlines():
                if ":" in line:
                    key, val = line.split(":", 1)
                    k = key.strip().lower()
                    v = val.strip().strip("\"'")
                    if v.lower() == "true": metadata[k] = True
                    elif v.lower() == "false": metadata[k] = False
                    elif v.lower() == "none" or v.lower() == "null": metadata[k] = None
                    elif v.isdigit(): metadata[k] = int(v)
                    else: metadata[k] = v
        return metadata, content

    @classmethod
    def enrich_statutory_metadata(cls, meta: LegalMetadata, body: str, fm_meta: Optional[Dict[str, Any]] = None):
        """Enriches metadata with crosswalk (old law), punishment, explanations, and scraper fields."""
        # Transfer any fields passed from frontmatter / scraper dataset
        if fm_meta:
            for k, v in fm_meta.items():
                if hasattr(meta, k) and getattr(meta, k) is None and v is not None:
                    setattr(meta, k, v)

        # Crosswalk detection (e.g. BNS Section corresponds to IPC Section)
        if not meta.previous_section:
            cw_bracket = cls.BRACKET_CROSSWALK_RE.search(body)
            if cw_bracket:
                meta.previous_law = cw_bracket.group(1).upper()
                meta.previous_section = cw_bracket.group(2)
            else:
                cw_match = cls.CROSSWALK_RE.search(body)
                if cw_match:
                    meta.previous_section = cw_match.group(1)
                    if cw_match.group(2):
                        law_str = cw_match.group(2).upper()
                        if "PENAL" in law_str or "IPC" in law_str: meta.previous_law = "IPC"
                        elif "PROCEDURE" in law_str or "CRPC" in law_str: meta.previous_law = "CrPC"
                        elif "EVIDENCE" in law_str or "IEA" in law_str: meta.previous_law = "IEA"
                        else: meta.previous_law = law_str

        # Punishment extraction
        if meta.punishment_imprisonment is None:
            imp_m = cls.PUNISHMENT_IMPRISON_RE.search(body)
            if imp_m:
                meta.punishment_imprisonment = True
                meta.punishment_maximum_years = int(imp_m.group(1))

        if meta.punishment_life_imprisonment is None and cls.PUNISHMENT_LIFE_RE.search(body):
            meta.punishment_imprisonment = True
            meta.punishment_life_imprisonment = True

        if meta.punishment_death_penalty is None and cls.PUNISHMENT_DEATH_RE.search(body):
            meta.punishment_death_penalty = True

        if meta.punishment_fine is None and cls.PUNISHMENT_FINE_RE.search(body):
            meta.punishment_fine = True

        # Explanation / Illustration / Proviso
        if not meta.explanation_number:
            exp_m = cls.EXPLANATION_RE.search(body)
            if exp_m and exp_m.group(1):
                meta.explanation_number = exp_m.group(1)

        if not meta.illustration_number:
            ill_m = cls.ILLUSTRATION_RE.search(body)
            if ill_m and ill_m.group(1):
                meta.illustration_number = ill_m.group(1)

        if meta.proviso is None and cls.PROVISO_RE.search(body):
            meta.proviso = True

    @classmethod
    def parse_markdown_content(cls, text: str, document_name: str) -> List[Dict[str, Any]]:
        """
        Parses Markdown documents into structural parent blocks preserving:
        - Heading hierarchy levels (# to ######)
        - Breadcrumb path (e.g. Act > Chapter > Section)
        - Markdown tables and lists as atomic units
        - Statutory markers in headers (Section, Article, Rule, etc.)
        - Comprehensive scraper metadata (Crosswalk, Punishment, Procedure)
        """
        fm_meta, clean_text = cls.parse_frontmatter(text)
        act_name, act_year = cls.extract_act_info(clean_text, document_name)
        if "title" in fm_meta: act_name = fm_meta["title"]
        if "act_name" in fm_meta: act_name = fm_meta["act_name"]
        if "act_year" in fm_meta or "year" in fm_meta:
            act_year = fm_meta.get("act_year") or fm_meta.get("year")

        matches = list(cls.MD_HEADING_RE.finditer(clean_text))
        if not matches:
            return cls.parse_standard_content(clean_text, document_name, fm_meta=fm_meta)

        blocks = []
        heading_stack: Dict[int, str] = {}
        current_part_no, current_part_title = None, None
        current_chap_no, current_chap_title = None, None

        first_pos = matches[0].start()
        if first_pos > 0 and clean_text[:first_pos].strip():
            preamble_text = clean_text[:first_pos].strip()
            preamble_meta = LegalMetadata(
                act_name=act_name,
                act_year=act_year,
                document_name=document_name,
                section_title="Preamble / Preliminary",
                hierarchy_path=f"{act_name} > Preamble",
                file_type="markdown",
                chunk_type="parent"
            )
            cls.enrich_statutory_metadata(preamble_meta, preamble_text, fm_meta)
            p_dict = preamble_meta.model_dump()
            p_dict["legal_reference"] = make_legal_reference(p_dict)
            blocks.append({"metadata": sanitize_metadata(p_dict), "body": preamble_text})

        for i, match in enumerate(matches):
            level = len(match.group(1))
            heading_text = match.group(2).strip()
            start_pos = match.start()
            end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(clean_text)
            body = clean_text[start_pos:end_pos].strip()

            heading_stack = {l: h for l, h in heading_stack.items() if l < level}
            heading_stack[level] = heading_text

            breadcrumb_items = [heading_stack[l] for l in sorted(heading_stack.keys())]
            hierarchy_path = " > ".join(breadcrumb_items) if breadcrumb_items else heading_text

            if level == 1 and len(heading_text) > 4:
                act_name = heading_text
                ym = re.search(r"\b(18\d{2}|19\d{2}|20\d{2})\b", heading_text)
                if ym: act_year = ym.group(1)

            check_header = f"{heading_text}\n{body[:250]}"
            part_m = cls.PART_RE.search(check_header)
            if part_m:
                current_part_no, current_part_title = part_m.group(1), part_m.group(2).strip()

            chap_m = cls.CHAPTER_RE.search(check_header)
            if chap_m:
                current_chap_no, current_chap_title = chap_m.group(1), chap_m.group(2).strip()

            meta = LegalMetadata(
                act_name=act_name,
                act_year=act_year,
                document_name=document_name,
                part_no=current_part_no,
                part_title=current_part_title,
                chapter_no=current_chap_no,
                chapter_title=current_chap_title,
                hierarchy_path=f"{act_name} > {hierarchy_path}" if act_name not in hierarchy_path else hierarchy_path,
                heading=heading_text,
                file_type="markdown",
                chunk_type="parent"
            )

            sec_m = cls.SECTION_RE.search(heading_text) or cls.SECTION_RE.search(body[:300])
            art_m = cls.ARTICLE_RE.search(heading_text) or cls.ARTICLE_RE.search(body[:300])
            rule_m = cls.RULE_RE.search(heading_text) or cls.RULE_RE.search(body[:300])
            ord_m = cls.ORDER_RE.search(heading_text) or cls.ORDER_RE.search(body[:300])
            reg_m = cls.REGULATION_RE.search(heading_text) or cls.REGULATION_RE.search(body[:300])
            sch_m = cls.SCHEDULE_RE.search(heading_text) or cls.SCHEDULE_RE.search(body[:300])

            if sec_m:
                meta.section_no = sec_m.group(1)
                meta.section_number = sec_m.group(1)
                meta.section_title = sec_m.group(2).strip() or heading_text
            elif art_m:
                meta.article_no = art_m.group(1)
                meta.article_title = art_m.group(2).strip() or heading_text
            elif rule_m:
                meta.rule_no = rule_m.group(1)
                meta.rule_title = rule_m.group(2).strip() or heading_text
            elif ord_m:
                meta.order_no = ord_m.group(1)
                meta.order_title = ord_m.group(2).strip() or heading_text
            elif reg_m:
                meta.regulation_no = reg_m.group(1)
                meta.regulation_title = reg_m.group(2).strip() or heading_text
            elif sch_m:
                meta.schedule_no = sch_m.group(1)
                meta.schedule_title = sch_m.group(2).strip() or heading_text
            else:
                meta.section_title = heading_text

            header_snippet = body[:200]
            sub_m = cls.SUBSECTION_RE.search(header_snippet)
            if sub_m:
                meta.subsection_no = sub_m.group(1)
                meta.subsection_number = sub_m.group(1)
            cls_m = cls.CLAUSE_RE.search(header_snippet)
            if cls_m:
                meta.clause_no = cls_m.group(1)
                meta.clause = cls_m.group(1)
            subcls_m = cls.SUBCLAUSE_RE.search(header_snippet)
            if subcls_m and meta.clause_no and subcls_m.group(1) != meta.subsection_no:
                meta.subclause_no = subcls_m.group(1)
                meta.subclause = subcls_m.group(1)

            # Enrich with crosswalk, punishment, explanations & frontmatter
            cls.enrich_statutory_metadata(meta, body, fm_meta)

            dict_meta = meta.model_dump()
            dict_meta["legal_reference"] = make_legal_reference(dict_meta)
            blocks.append({"metadata": sanitize_metadata(dict_meta), "body": body})

        return blocks

    @classmethod
    def parse_standard_content(cls, text: str, document_name: str, fm_meta: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Scans standard legal text (PDF, DOCX, TXT) with statutory regexes."""
        act_name, act_year = cls.extract_act_info(text, document_name)
        if fm_meta:
            if "act_name" in fm_meta: act_name = fm_meta["act_name"]
            if "act_year" in fm_meta or "year" in fm_meta:
                act_year = fm_meta.get("act_year") or fm_meta.get("year")

        markers = []
        for m in cls.PART_RE.finditer(text): markers.append((m.start(), "part", m.group(1), m.group(2).strip()))
        for m in cls.CHAPTER_RE.finditer(text): markers.append((m.start(), "chapter", m.group(1), m.group(2).strip()))
        for m in cls.ORDER_RE.finditer(text): markers.append((m.start(), "order", m.group(1), m.group(2).strip()))
        for m in cls.SECTION_RE.finditer(text): markers.append((m.start(), "section", m.group(1), m.group(2).strip()))
        for m in cls.ARTICLE_RE.finditer(text): markers.append((m.start(), "article", m.group(1), m.group(2).strip()))
        for m in cls.RULE_RE.finditer(text): markers.append((m.start(), "rule", m.group(1), m.group(2).strip()))
        for m in cls.REGULATION_RE.finditer(text): markers.append((m.start(), "regulation", m.group(1), m.group(2).strip()))
        for m in cls.SCHEDULE_RE.finditer(text): markers.append((m.start(), "schedule", m.group(1), m.group(2).strip()))

        markers.sort(key=lambda x: x[0])

        if not markers:
            meta = LegalMetadata(
                act_name=act_name,
                act_year=act_year,
                document_name=document_name,
                chunk_type="parent"
            )
            cls.enrich_statutory_metadata(meta, text, fm_meta)
            d_meta = meta.model_dump()
            d_meta["legal_reference"] = make_legal_reference(d_meta)
            return [{"metadata": sanitize_metadata(d_meta), "body": text.strip()}]

        current_part_no, current_part_title = None, None
        current_chap_no, current_chap_title = None, None
        blocks = []

        for idx, item in enumerate(markers):
            pos, kind, no, title = item
            end_pos = markers[idx + 1][0] if idx + 1 < len(markers) else len(text)
            content = text[pos:end_pos].strip()

            if kind == "part":
                current_part_no, current_part_title = no, title
            elif kind == "chapter":
                current_chap_no, current_chap_title = no, title
            else:
                meta = LegalMetadata(
                    act_name=act_name,
                    act_year=act_year,
                    document_name=document_name,
                    part_no=current_part_no,
                    part_title=current_part_title,
                    chapter_no=current_chap_no,
                    chapter_title=current_chap_title,
                    chunk_type="parent"
                )

                if kind == "section":
                    meta.section_no = no
                    meta.section_number = no
                    meta.section_title = title
                elif kind == "article":
                    meta.article_no = no
                    meta.article_title = title
                elif kind == "rule":
                    meta.rule_no = no
                    meta.rule_title = title
                elif kind == "order":
                    meta.order_no = no
                    meta.order_title = title
                elif kind == "regulation":
                    meta.regulation_no = no
                    meta.regulation_title = title
                elif kind == "schedule":
                    meta.schedule_no = no
                    meta.schedule_title = title

                path_parts = [act_name]
                if current_chap_no: path_parts.append(f"Chapter {current_chap_no}")
                if meta.section_no: path_parts.append(f"Section {meta.section_no}")
                elif meta.article_no: path_parts.append(f"Article {meta.article_no}")
                elif meta.rule_no: path_parts.append(f"Rule {meta.rule_no}")
                meta.hierarchy_path = " > ".join(path_parts)

                header_snippet = content[:200]
                sub_match = cls.SUBSECTION_RE.search(header_snippet)
                if sub_match:
                    meta.subsection_no = sub_match.group(1)
                    meta.subsection_number = sub_match.group(1)

                cls_match = cls.CLAUSE_RE.search(header_snippet)
                if cls_match:
                    meta.clause_no = cls_match.group(1)
                    meta.clause = cls_match.group(1)

                subcls_match = cls.SUBCLAUSE_RE.search(header_snippet)
                if subcls_match and meta.clause_no and subcls_match.group(1) != meta.subsection_no:
                    meta.subclause_no = subcls_match.group(1)
                    meta.subclause = subcls_match.group(1)

                # Enrich with crosswalk, punishment, explanations & frontmatter
                cls.enrich_statutory_metadata(meta, content, fm_meta)

                dict_meta = meta.model_dump()
                dict_meta["legal_reference"] = make_legal_reference(dict_meta)
                blocks.append({"metadata": sanitize_metadata(dict_meta), "body": content})

        return blocks

    @classmethod
    def parse_document_content(cls, text: str, document_name: str) -> List[Dict[str, Any]]:
        """Intelligently routes Markdown vs standard text parsing."""
        is_md = (
            document_name.lower().endswith(".md")
            or bool(cls.MD_HEADING_RE.search(text[:1500]))
            or bool(cls.MD_FRONTMATTER_RE.match(text))
        )
        if is_md:
            return cls.parse_markdown_content(text, document_name)
        return cls.parse_standard_content(text, document_name)
