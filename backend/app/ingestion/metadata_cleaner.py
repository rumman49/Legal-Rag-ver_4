"""Legal Reference Utilities, Comprehensive Statutory Metadata Schema, and ChromaDB Metadata Sanitizer."""
from __future__ import annotations
import re
import uuid
from typing import List, Dict, Optional, Any, Union
from pydantic import BaseModel, ConfigDict, Field


class LegalMetadata(BaseModel):
    """
    Comprehensive Legal Metadata Schema for Indian Law Statutes, Scraped Provisions & Crosswalks.
    Fully compatible with IndiaCode scrapers, BNS/IPC/BNSS/CrPC crosswalks, and ChromaDB primitives.
    """
    model_config = ConfigDict(extra="ignore")

    # DOCUMENT
    document_id: Optional[str] = None
    file_name: Optional[str] = None
    document_name: Optional[str] = None
    document_type: Optional[str] = "statute"
    title: Optional[str] = None
    short_title: Optional[str] = None
    act_name: Optional[str] = None
    act_year: Optional[Union[str, int]] = None
    jurisdiction: Optional[str] = "India"
    language: Optional[str] = "English"
    source: Optional[str] = None
    source_type: Optional[str] = "official"

    # LEGAL HIERARCHY
    part_number: Optional[str] = None
    part_no: Optional[str] = None
    part_title: Optional[str] = None
    chapter_number: Optional[str] = None
    chapter_no: Optional[str] = None
    chapter_title: Optional[str] = None
    division_number: Optional[str] = None
    division_title: Optional[str] = None

    # PROVISION
    section_number: Optional[str] = None
    section_no: Optional[str] = None
    section_title: Optional[str] = None
    subsection_number: Optional[str] = None
    subsection_no: Optional[str] = None
    clause: Optional[str] = None
    clause_no: Optional[str] = None
    subclause: Optional[str] = None
    subclause_no: Optional[str] = None
    article_no: Optional[str] = None
    article_title: Optional[str] = None
    rule_no: Optional[str] = None
    rule_title: Optional[str] = None
    order_no: Optional[str] = None
    order_title: Optional[str] = None
    regulation_no: Optional[str] = None
    regulation_title: Optional[str] = None
    schedule_no: Optional[str] = None
    schedule_title: Optional[str] = None

    # STRUCTURE
    chunk_type: Optional[str] = "child"
    parent_section: Optional[str] = None
    parent_section_title: Optional[str] = None
    explanation_number: Optional[str] = None
    illustration_number: Optional[str] = None
    proviso: Optional[Union[str, bool]] = None

    # CLASSIFICATION
    legal_topic: Optional[str] = None
    legal_topics: Optional[Union[List[str], str]] = None
    offence_category: Optional[str] = None
    section_type: Optional[str] = None

    # PUNISHMENT
    punishment: Optional[Dict[str, Any]] = None
    punishment_imprisonment: Optional[bool] = None
    punishment_maximum_years: Optional[Union[int, float]] = None
    punishment_life_imprisonment: Optional[bool] = None
    punishment_death_penalty: Optional[bool] = None
    punishment_fine: Optional[bool] = None
    punishment_summary: Optional[str] = None

    # PROCEDURE
    cognizable: Optional[bool] = None
    bailable: Optional[bool] = None
    compoundable: Optional[bool] = None
    triable_by: Optional[str] = None

    # CROSSWALK (BNS <-> IPC, BNSS <-> CrPC, BSA <-> IEA)
    previous_law: Optional[str] = None
    previous_section: Optional[str] = None
    cross_reference_type: Optional[str] = "corresponding_provision"

    # REFERENCES
    referenced_sections: Optional[Union[List[str], str]] = None
    referenced_acts: Optional[Union[List[str], str]] = None
    referenced_cases: Optional[Union[List[str], str]] = None

    # TEMPORAL
    enactment_date: Optional[str] = None
    commencement_date: Optional[str] = None
    effective_date: Optional[str] = None
    amended: Optional[bool] = False
    repealed: Optional[bool] = False
    current_status: Optional[str] = "in_force"

    # LOCATION
    page_number: Optional[int] = None
    paragraph_number: Optional[int] = None

    # RETRIEVAL
    keywords: Optional[Union[List[str], str]] = None
    entities: Optional[Union[List[str], str]] = None
    concepts: Optional[Union[List[str], str]] = None
    answer_types: Optional[Union[List[str], str]] = None

    # CHUNK NAVIGATION & HIERARCHY
    chunk_id: Optional[str] = None
    chunk_index: Optional[int] = None
    previous_chunk_id: Optional[str] = None
    next_chunk_id: Optional[str] = None
    parent_id: Optional[str] = None
    child_index: Optional[int] = None
    total_child_splits: Optional[int] = None
    parent_split_index: Optional[int] = None
    hierarchy_path: Optional[str] = None
    heading: Optional[str] = None
    file_type: Optional[str] = None
    is_semantic: Optional[bool] = None


def sanitize_metadata(meta: Dict[str, Any]) -> Dict[str, str | int | float | bool]:
    """
    Filters out None values, flattens nested dicts (e.g. punishment), serializes lists,
    harmonizes statutory aliases, and strictly guarantees ChromaDB primitive compliance.
    """
    clean_meta: Dict[str, str | int | float | bool] = {}

    # 1. Alias harmonization
    # section_number <-> section_no
    sec = meta.get("section_number") or meta.get("section_no")
    if sec:
        clean_meta["section_number"] = str(sec)
        clean_meta["section_no"] = str(sec)

    # subsection_number <-> subsection_no
    sub = meta.get("subsection_number") or meta.get("subsection_no")
    if sub:
        clean_meta["subsection_number"] = str(sub)
        clean_meta["subsection_no"] = str(sub)

    # clause <-> clause_no
    cl = meta.get("clause") or meta.get("clause_no")
    if cl:
        clean_meta["clause"] = str(cl)
        clean_meta["clause_no"] = str(cl)

    # subclause <-> subclause_no
    subcl = meta.get("subclause") or meta.get("subclause_no")
    if subcl:
        clean_meta["subclause"] = str(subcl)
        clean_meta["subclause_no"] = str(subcl)

    # chapter_number <-> chapter_no
    chap = meta.get("chapter_number") or meta.get("chapter_no")
    if chap:
        clean_meta["chapter_number"] = str(chap)
        clean_meta["chapter_no"] = str(chap)

    # part_number <-> part_no
    part = meta.get("part_number") or meta.get("part_no")
    if part:
        clean_meta["part_number"] = str(part)
        clean_meta["part_no"] = str(part)

    # file_name <-> document_name
    doc_n = meta.get("file_name") or meta.get("document_name")
    if doc_n:
        clean_meta["file_name"] = str(doc_n)
        clean_meta["document_name"] = str(doc_n)

    # chunk_id <-> parent_id
    if meta.get("chunk_id"):
        clean_meta["chunk_id"] = str(meta["chunk_id"])

    # 2. Flatten nested punishment dictionary if present
    punishment = meta.get("punishment")
    if isinstance(punishment, dict):
        if "imprisonment" in punishment and punishment["imprisonment"] is not None:
            clean_meta["punishment_imprisonment"] = bool(punishment["imprisonment"])
        if "maximum_years" in punishment and punishment["maximum_years"] is not None:
            clean_meta["punishment_maximum_years"] = (
                int(punishment["maximum_years"]) if isinstance(punishment["maximum_years"], (int, float)) else str(punishment["maximum_years"])
            )
        if "life_imprisonment" in punishment and punishment["life_imprisonment"] is not None:
            clean_meta["punishment_life_imprisonment"] = bool(punishment["life_imprisonment"])
        if "death_penalty" in punishment and punishment["death_penalty"] is not None:
            clean_meta["punishment_death_penalty"] = bool(punishment["death_penalty"])
        if "fine" in punishment and punishment["fine"] is not None:
            clean_meta["punishment_fine"] = bool(punishment["fine"])

        # Build readable punishment summary string
        summary_parts = []
        if punishment.get("death_penalty"):
            summary_parts.append("Death penalty")
        elif punishment.get("life_imprisonment"):
            summary_parts.append("Imprisonment for life")
        elif punishment.get("imprisonment") and punishment.get("maximum_years"):
            summary_parts.append(f"Imprisonment up to {punishment['maximum_years']} years")
        elif punishment.get("imprisonment"):
            summary_parts.append("Imprisonment")
        if punishment.get("fine"):
            summary_parts.append("Fine")

        if summary_parts and "punishment_summary" not in clean_meta:
            clean_meta["punishment_summary"] = ", ".join(summary_parts)

    # 3. Process all remaining fields
    for key, val in meta.items():
        if val is None or key in ["punishment"]:
            continue

        if isinstance(val, (bool, int, float)):
            clean_meta[key] = val
        elif isinstance(val, str):
            clean_meta[key] = val.strip()
        elif isinstance(val, list):
            # Serialize lists into comma-delimited strings for ChromaDB filtering & keyword search
            clean_meta[key] = ", ".join(str(item).strip() for item in val if item is not None)
        elif isinstance(val, dict):
            # Flatten any other nested dict by prefixing key
            for sub_k, sub_v in val.items():
                if sub_v is not None:
                    flat_k = f"{key}_{sub_k}"
                    if isinstance(sub_v, (bool, int, float, str)):
                        clean_meta[flat_k] = sub_v
                    else:
                        clean_meta[flat_k] = str(sub_v)
        else:
            clean_meta[key] = str(val)

    return clean_meta


def make_legal_reference(metadata: dict) -> str:
    """Constructs canonical identifier string from document metadata."""
    # If explicit chunk_id is already provided (e.g. BNS-318-4)
    if metadata.get("chunk_id"):
        return str(metadata["chunk_id"]).upper()

    document_name = (
        metadata.get("act_name")
        or metadata.get("short_title")
        or metadata.get("title")
        or metadata.get("document_name")
        or metadata.get("file_name")
        or "LEGAL-DOCUMENT"
    )

    prefix = re.sub(r"[^A-Za-z0-9]+", "-", str(document_name).upper()).strip("-")
    year = metadata.get("act_year")
    if year:
        prefix = f"{prefix}-{year}"

    article_no = metadata.get("article_no")
    if article_no:
        return f"{prefix}-ARTICLE-{article_no}"

    section_no = metadata.get("section_number") or metadata.get("section_no")
    if section_no:
        result = f"{prefix}-SECTION-{section_no}"
        subsection = metadata.get("subsection_number") or metadata.get("subsection_no")
        if subsection:
            result += f"-SUBSECTION-{subsection}"
        clause = metadata.get("clause") or metadata.get("clause_no")
        if clause:
            result += f"-CLAUSE-{clause.upper()}"
        subclause = metadata.get("subclause") or metadata.get("subclause_no")
        if subclause:
            result += f"-SUBCLAUSE-{subclause}"
        return result

    rule_no = metadata.get("rule_no")
    if rule_no:
        return f"{prefix}-RULE-{rule_no}"

    regulation_no = metadata.get("regulation_no")
    if regulation_no:
        return f"{prefix}-REGULATION-{regulation_no}"

    order_no = metadata.get("order_no")
    if order_no:
        return f"{prefix}-ORDER-{order_no}"

    schedule_no = metadata.get("schedule_no")
    if schedule_no:
        return f"{prefix}-SCHEDULE-{schedule_no}"

    heading = metadata.get("heading") or metadata.get("section_title")
    if heading:
        slug = re.sub(r"[^A-Za-z0-9]+", "-", str(heading).upper()).strip("-")[:40]
        if slug:
            return f"{prefix}-{slug}"

    return f"{prefix}-{uuid.uuid4().hex[:8]}"


def format_human_legal_reference(metadata: dict) -> str:
    """Constructs clean human-readable reference title string for citations with crosswalk info."""
    if not metadata:
        return "Indian Law Statute"

    raw_act = metadata.get("act_name") or metadata.get("short_title") or metadata.get("title") or metadata.get("document_name") or ""
    raw_ref = metadata.get("legal_reference") or metadata.get("chunk_id") or ""
    raw_act = re.sub(r"^(ACT:\s*|Act:\s*)", "", str(raw_act)).strip()

    sec = metadata.get("section_number") or metadata.get("section_no") or metadata.get("article_no")
    if not sec and raw_ref:
        m = re.search(r"-(SECTION|ARTICLE|RULE)-([0-9A-Z]+)", str(raw_ref), re.IGNORECASE)
        if m:
            sec = m.group(2)

    year = metadata.get("act_year")
    if not year and raw_ref:
        m = re.search(r"\b(19\d\d|20\d\d)\b", str(raw_ref))
        if m:
            year = m.group(1)

    title = ""
    if raw_act:
        words = str(raw_act).split()
        cleaned_words = []
        for w in words:
            if w.upper() in ["THE", "OF", "FOR", "AND", "IN", "TO", "ON"]:
                cleaned_words.append(w.lower() if cleaned_words else w.capitalize())
            else:
                cleaned_words.append(w.capitalize())
        title = " ".join(cleaned_words)
        if year and str(year) not in title:
            title = f"{title}, {year}"
        prov = f"Section {sec}" if sec else ""
        sub = metadata.get("subsection_number") or metadata.get("subsection_no")
        if sub:
            prov += f"({sub})"
        clause = metadata.get("clause") or metadata.get("clause_no")
        if clause:
            prov += f"({clause})"
        full_ref = f"{title} — {prov}" if prov else title
    else:
        full_ref = str(raw_ref)

    # Append provision title if available
    sec_title = metadata.get("section_title") or metadata.get("parent_section_title")
    if sec_title and sec_title.lower() not in full_ref.lower():
        full_ref += f": {sec_title}"

    # Append Historical Crosswalk note (e.g. [Corresponds to IPC Section 420])
    prev_law = metadata.get("previous_law")
    prev_sec = metadata.get("previous_section")
    if prev_law and prev_sec:
        full_ref += f" [Corresponds to: {prev_law} Section {prev_sec}]"

    return full_ref


build_legal_reference = make_legal_reference
