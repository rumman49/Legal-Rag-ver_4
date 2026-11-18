"""Statutory reference parsing: act aliases (old and new Indian codes) and section/article/rule/regulation references.

One alias table and one set of patterns serve both query routing (rag/hybrid_retriever.py) and
follow-up contextualisation (rag/rag_pipeline.py), so the two cannot disagree about what a query names.
"""
import re
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


@dataclass(frozen=True)
class Act:
    code: str
    needle: str  # case-insensitive substring of the act_name stored in ChromaDB metadata


ACTS: Dict[str, Act] = {a.code: a for a in (
    Act("BNS", "Bharatiya Nyaya Sanhita"),
    Act("BNSS", "Bharatiya Nagarik Suraksha"),
    Act("BSA", "Bharatiya Sakshya"),
    Act("IPC", "Indian Penal Code"),
    Act("CRPC", "Code of Criminal Procedure"),
    Act("CPC", "Code of Civil Procedure"),
    Act("IEA", "Indian Evidence Act"),
    Act("NI", "Negotiable Instruments Act"),
    Act("IT", "Information Technology Act"),
    Act("CONTRACT", "Indian Contract Act"),
    Act("COMPANIES", "Companies Act"),
    Act("ARBITRATION", "Arbitration and Conciliation"),
    Act("PMLA", "Prevention of Money-Laundering"),
    Act("MV", "Motor Vehicles Act"),
    Act("INCOMETAX", "Income-tax Act"),
    Act("CONSUMER", "Consumer Protection"),
    Act("HMA", "Hindu Marriage Act"),
    Act("CONST", "Constitution of India"),
)}

# Lowercase aliases per act. Hindi/Devanagari spellings are included because queries arrive in Hindi too.
ALIASES: Dict[str, Tuple[str, ...]] = {
    "BNS": ("bns", "bharatiya nyaya sanhita", "nyaya sanhita", "बीएनएस", "भारतीय न्याय संहिता"),
    "BNSS": ("bnss", "bharatiya nagarik suraksha sanhita", "bharatiya nagarik suraksha",
             "nagarik suraksha sanhita", "बीएनएसएस", "भारतीय नागरिक सुरक्षा संहिता"),
    "BSA": ("bsa", "bharatiya sakshya adhiniyam", "bharatiya sakshya", "बीएसए", "भारतीय साक्ष्य अधिनियम"),
    "IPC": ("ipc", "indian penal code", "penal code", "आईपीसी", "भारतीय दंड संहिता"),
    "CRPC": ("crpc", "cr.p.c", "code of criminal procedure", "criminal procedure code", "सीआरपीसी",
             "दंड प्रक्रिया संहिता"),
    "CPC": ("cpc", "c.p.c", "code of civil procedure", "civil procedure code"),
    "IEA": ("iea", "indian evidence act", "evidence act"),
    "NI": ("ni act", "negotiable instruments act"),
    "IT": ("it act", "information technology act"),
    "CONTRACT": ("indian contract act", "contract act"),
    "COMPANIES": ("companies act", "company act"),
    "ARBITRATION": ("arbitration and conciliation act", "arbitration act"),
    "PMLA": ("pmla",),
    "MV": ("motor vehicles act", "mv act"),
    "INCOMETAX": ("income-tax act", "income tax act"),
    "CONSUMER": ("consumer protection act",),
    "HMA": ("hindu marriage act",),
    "CONST": ("constitution of india", "constitution", "samvidhan", "संविधान"),
}

# Generic words that name an act only in a specific context. They may attach to a section/article
# number ("Article 21 of the Constitution") but never filter retrieval on their own.
WEAK_ALIASES = {"constitution", "contract act", "it act", "evidence act"}

_ALIAS_TO_CODE = {alias: code for code, aliases in ALIASES.items() for alias in aliases}
_ALT = "|".join(re.escape(a) for a in sorted(_ALIAS_TO_CODE, key=len, reverse=True))
# ASCII boundaries only: Devanagari aliases are not preceded or followed by Latin letters in practice.
ACT_ALT = rf"(?<![A-Za-z0-9])(?:{_ALT})(?![A-Za-z0-9])"

NUM = r"\d{1,4}[A-Za-z]{0,2}(?![A-Za-z0-9])"
NUMLIST = rf"{NUM}(?:\s*(?:,|&|\band\b|\bor\b|\bto\b|-|–)\s*{NUM})*"
SUBS_G = r"(?P<subs>(?:\s*\(\s*[0-9A-Za-z]{1,4}\s*\))*)"
KW_SEC = r"(?:sections?|secs?|s|धारा|धाराएं|धारायें)"
KW_ART = r"(?:articles?|arts?|अनुच्छेद)"
TAIL = rf"(?:\s*,?\s*(?:(?:of|under|in|from)\s+)?(?:the\s+)?(?P<act>{ACT_ALT}))?"

_P_SECTION = re.compile(rf"(?<![A-Za-z0-9]){KW_SEC}\.?\s*(?P<nums>{NUMLIST}){SUBS_G}{TAIL}", re.IGNORECASE)
_P_ARTICLE = re.compile(rf"(?<![A-Za-z0-9]){KW_ART}\.?\s*(?P<nums>{NUMLIST}){SUBS_G}{TAIL}", re.IGNORECASE)
_P_RULE = re.compile(
    rf"(?<![A-Za-z0-9])(?:order\s+(?P<order>{NUM})\s*,?\s*)?rules?\s*(?P<nums>{NUMLIST}){SUBS_G}{TAIL}",
    re.IGNORECASE,
)
_P_REGULATION = re.compile(rf"(?<![A-Za-z0-9])(?:regulations?|reg\.?)\s*(?P<nums>{NUMLIST}){SUBS_G}{TAIL}", re.IGNORECASE)
# "BNS 103", "BNSS section 173", "Constitution article 21"
_P_ACT_FIRST = re.compile(
    rf"(?P<act>{ACT_ALT})\s*,?\s*(?P<kw>{KW_SEC}|{KW_ART})?\.?\s*(?P<nums>{NUMLIST}){SUBS_G}",
    re.IGNORECASE,
)
# "103 of the BNS", "302 IPC"
_P_NUM_FIRST = re.compile(
    rf"(?<![A-Za-z0-9])(?P<nums>{NUMLIST}){SUBS_G}\s*(?:of\s+the\s+|of\s+|under\s+the\s+|under\s+)?(?P<act>{ACT_ALT})(?![A-Za-z0-9])",
    re.IGNORECASE,
)

_NUM_TOKEN = re.compile(r"\d{1,4}[A-Za-z]{0,2}")
_RANGE = re.compile(r"^\s*(\d+)\s*(?:-|–|to)\s*(\d+)\s*$")


def _expand_numbers(nums: str) -> List[str]:
    """'103' -> ['103']; '103 and 104' -> both; '103-105' -> 103, 104, 105 (ranges capped at 10)."""
    rng = _RANGE.match(nums)
    if rng:
        a, b = int(rng.group(1)), int(rng.group(2))
        if 0 < a <= b and b - a <= 10:
            return [str(i) for i in range(a, b + 1)]
    return _NUM_TOKEN.findall(nums)


def _looks_like_year(number: str) -> bool:
    digits = re.match(r"\d+", number)
    return bool(digits) and 1800 <= int(digits.group(0)) <= 2099


def _split_subs(subs: str) -> Tuple[Optional[str], Optional[str]]:
    """'(2)(a)' -> ('2', 'a')."""
    parts = re.findall(r"\(\s*([0-9A-Za-z]+)\s*\)", subs or "")
    sub = next((p for p in parts if p.isdigit()), None)
    clause = next((p for p in parts if p.isalpha()), None)
    return sub, clause


def _act_from_alias(text: Optional[str]) -> Optional[Act]:
    if not text:
        return None
    code = _ALIAS_TO_CODE.get(text.strip().lower())
    return ACTS.get(code) if code else None


def _make_ref(kind: str, number: str, subs: str, act: Optional[Act], start: int, end: int,
              text: str, order: Optional[str] = None) -> Dict:
    sub, clause = _split_subs(subs)
    ref = {
        "type": kind,
        "section_no": None, "subsection_no": None, "clause_no": None,
        "article_no": None, "rule_no": None, "regulation_no": None, "order_no": order,
        "act_code": act.code if act else None,
        "act_needle": act.needle if act else None,
        "text": text, "raw": text, "start": start, "end": end,
    }
    if kind == "section":
        ref.update(section_no=number, subsection_no=sub, clause_no=clause)
    elif kind == "article":
        ref.update(article_no=number)
    elif kind == "rule":
        ref.update(rule_no=number)
    elif kind == "regulation":
        ref.update(regulation_no=number)
    return ref


def find_acts(text: str) -> List[Act]:
    """Distinct acts named in the text, in order of appearance (weak aliases included)."""
    seen: List[Act] = []
    for m in re.finditer(ACT_ALT, text, re.IGNORECASE):
        act = _act_from_alias(m.group(0))
        if act and act not in seen:
            seen.append(act)
    return seen


def strong_acts(text: str) -> List[Act]:
    """Acts named by a non-generic alias. Only these may filter retrieval."""
    seen: List[Act] = []
    for m in re.finditer(ACT_ALT, text, re.IGNORECASE):
        alias = m.group(0).lower()
        act = _act_from_alias(alias)
        if act and alias not in WEAK_ALIASES and act not in seen:
            seen.append(act)
    return seen


def extract_act_filter(text: str) -> Optional[str]:
    """Stored-name needle of the first strongly named act, or None. Kept for callers that want one act."""
    acts = strong_acts(text)
    return acts[0].needle if acts else None


def extract_references(text: str) -> List[Dict]:
    """Statutory references in text: sections, articles, rules, regulations, each with its act if one is attached.

    References without an attached act inherit the act only when the text names exactly one act.
    Each dict keeps the keys the rest of the pipeline reads (section_no, article_no, ..., raw, start, end).
    """
    found: List[Dict] = []
    taken: List[Tuple[int, int]] = []

    def overlaps(span: Tuple[int, int]) -> bool:
        return any(span[0] < e and s < span[1] for s, e in taken)

    def add(kind: str, m: re.Match, nums: str, act: Optional[Act], subs: str = "", order: Optional[str] = None):
        span = m.span()
        if overlaps(span):
            return
        taken.append(span)
        for number in _expand_numbers(nums):
            found.append(_make_ref(kind, number, subs, act, span[0], span[1], m.group(0), order))

    for m in _P_SECTION.finditer(text):
        add("section", m, m.group("nums"), _act_from_alias(m.group("act")), m.group("subs"))
    for m in _P_ARTICLE.finditer(text):
        add("article", m, m.group("nums"), _act_from_alias(m.group("act")), m.group("subs"))
    for m in _P_RULE.finditer(text):
        add("rule", m, m.group("nums"), _act_from_alias(m.group("act")), m.group("subs"), m.group("order"))
    for m in _P_REGULATION.finditer(text):
        add("regulation", m, m.group("nums"), _act_from_alias(m.group("act")), m.group("subs"))
    for m in _P_ACT_FIRST.finditer(text):
        kw = (m.group("kw") or "").lower()
        if not kw and any(_looks_like_year(n) for n in _expand_numbers(m.group("nums"))):
            continue
        kind = "article" if re.fullmatch(KW_ART, kw or "x", re.IGNORECASE) else "section"
        add(kind, m, m.group("nums"), _act_from_alias(m.group("act")), m.group("subs"))
    for m in _P_NUM_FIRST.finditer(text):
        if any(_looks_like_year(n) for n in _expand_numbers(m.group("nums"))):
            continue
        add("section", m, m.group("nums"), _act_from_alias(m.group("act")), m.group("subs"))

    # A reference with no attached act takes the query's only named act, if there is exactly one.
    acts = find_acts(text)
    if len(acts) == 1:
        for ref in found:
            if ref["act_code"] is None and ref["type"] in ("section", "article"):
                ref["act_code"] = acts[0].code
                ref["act_needle"] = acts[0].needle

    found.sort(key=lambda r: r["start"])
    return found
