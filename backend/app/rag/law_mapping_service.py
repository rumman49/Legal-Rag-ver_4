"""Statutory Law Mapping Service (Old Laws vs New Criminal Laws 2023).

Loads transition_mappings.csv (IPC <-> BNS, CrPC <-> BNSS, IEA <-> BSA)
and provides accurate bidirectional cross-referencing between old and new laws.
"""
import csv
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from langchain_core.documents import Document

logger = logging.getLogger(__name__)

# Base path to mapping file
PROJECT_ROOT = Path(__file__).resolve().parents[3]
CSV_CANDIDATE_PATHS = [
    PROJECT_ROOT / "data" / "mappings" / "transition_mappings.csv",
    PROJECT_ROOT / "data" / "mappings" / "mapping.csv",
    PROJECT_ROOT / "data" / "mapping.csv",
    Path("F:/Legal RAG V3/data/mappings/transition_mappings.csv"),
]

# Common Criminal Offenses Keyword Dictionary
OFFENSE_KEYWORDS_CATALOG = [
    {
        "name": "Murder / Hatya",
        "keywords": [r"\b(hatya|murder|maar\s+diya|jaan\s+se\s+maar|katl|qatl)\b"],
        "new_act": "The Bharatiya Nyaya Sanhita, 2023",
        "new_sections": ["103", "101", "105"],
        "old_act": "The Indian Penal Code, 1860",
        "old_sections": ["302", "300", "304"],
        "summary": "Murder: Defined under BNS Section 101 (formerly IPC 300), punishable under BNS Section 103 (formerly IPC 302) with Death or Imprisonment for Life and Fine. Culpable homicide not amounting to murder is BNS Section 105 (formerly IPC 304)."
    },
    {
        "name": "Attempt to Murder / Half Murder",
        "keywords": [r"\b(attempt\s+to\s+murder|half\s+murder|jaanleva\s+hamla|marne\s+ki\s+koshish)\b"],
        "new_act": "The Bharatiya Nyaya Sanhita, 2023",
        "new_sections": ["109"],
        "old_act": "The Indian Penal Code, 1860",
        "old_sections": ["307"],
        "summary": "Attempt to murder is now covered under BNS Section 109 (formerly IPC Section 307)."
    },
    {
        "name": "Theft / Chori / Unauthorized Taking of Property or Vehicle",
        "keywords": [
            r"\b(chori|theft|stolen|chura\s+liya|churaya|chori\s+ki)\b",
            r"\b(bina\s+puche|bina\s+ijazat|bina\s+permission|bina\s+bataye)\b",
            r"\b(gaadi|gadi|car|bike|motorcycle|scooter|vehicle|vahan|vaahan)\s+(?:le\s+gaya|chura|chori|le\s+li|uthaya|chala\s+li)\b",
            r"\b(temporary\s+deprivation|wapas\s+kar\s+di|le\s+kar\s+wapas)\b"
        ],
        "new_act": "The Bharatiya Nyaya Sanhita, 2023",
        "new_sections": ["303", "305"],
        "old_act": "The Indian Penal Code, 1860",
        "old_sections": ["378", "379", "380"],
        "summary": (
            "Theft is defined under BNS Section 303(1) (formerly IPC Section 378) and punishable under BNS Section 303(2) (formerly IPC Section 379). "
            "Theft of any means of transport (vehicle) is specifically aggravated under BNS Section 305(b) with up to 7 years imprisonment and fine. "
            "TEMPORARY DEPRIVATION JURISPRUDENCE: Under established Indian criminal jurisprudence (Pyare Lal Bhargava v. State of Rajasthan), "
            "even temporary deprivation of movable property taken dishonestly without the owner's consent constitutes theft the moment the property is moved. "
            "Returning the property later does not wipe out the completed criminal offense."
        )
    },
    {
        "name": "Dishonest Misappropriation of Property (Section 314 BNS / Section 403 IPC)",
        "keywords": [
            r"\b(misappropriation|dishonest\s+misappropriation|amanat\s+mein\s+khayanat|viniyog)\b",
            r"\b(section\s+314|dhara\s+314|bns\s+314|ipc\s+403)\b"
        ],
        "new_act": "The Bharatiya Nyaya Sanhita, 2023",
        "new_sections": ["314"],
        "old_act": "The Indian Penal Code, 1860",
        "old_sections": ["403"],
        "summary": (
            "BNS Section 314 (formerly IPC Section 403) covers 'Dishonest misappropriation of property'. "
            "CRITICAL STATUTORY DISTINCTION: Section 314 is NOT for 'unauthorized use of vehicle'. "
            "It penalizes dishonestly misappropriating or converting movable property to one's own use (punishable with imprisonment up to 2 years, or fine, or both)."
        )
    },
    {
        "name": "Cheating / Dhokhadhadi / 420",
        "keywords": [r"\b(cheating|fraud|dhokha|dhokhadhadi|420|thagi|fraudulent)\b"],
        "new_act": "The Bharatiya Nyaya Sanhita, 2023",
        "new_sections": ["318", "316"],
        "old_act": "The Indian Penal Code, 1860",
        "old_sections": ["420", "415"],
        "summary": "Cheating is defined under BNS Section 316 (formerly IPC 415) and punishable under BNS Section 318 (formerly IPC 420)."
    },
    {
        "name": "Rape / Balaatkaar",
        "keywords": [r"\b(rape|balaatkaar|balatkar|gang\s*rape)\b"],
        "new_act": "The Bharatiya Nyaya Sanhita, 2023",
        "new_sections": ["63", "64", "70"],
        "old_act": "The Indian Penal Code, 1860",
        "old_sections": ["375", "376", "376d"],
        "summary": "Rape is defined under BNS Section 63 (formerly IPC 375), punishable under BNS Section 64 (formerly IPC 376). Gang rape is BNS Section 70 (formerly IPC 376D)."
    },
    {
        "name": "Kidnapping / Apharan",
        "keywords": [r"\b(kidnap|kidnapping|apharan|agva|kidnapped)\b"],
        "new_act": "The Bharatiya Nyaya Sanhita, 2023",
        "new_sections": ["137", "140"],
        "old_act": "The Indian Penal Code, 1860",
        "old_sections": ["359", "363", "364"],
        "summary": "Kidnapping and abduction are covered under BNS Section 137 (formerly IPC 359/363)."
    },
    {
        "name": "Voluntarily Causing Hurt / Marpeet",
        "keywords": [r"\b(marpeet|maarpeet|chot|assault|grievous\s+hurt|peeta|haathapaai)\b"],
        "new_act": "The Bharatiya Nyaya Sanhita, 2023",
        "new_sections": ["115", "118"],
        "old_act": "The Indian Penal Code, 1860",
        "old_sections": ["323", "325", "326"],
        "summary": "Voluntarily causing hurt is BNS Section 115 (formerly IPC 323); grievous hurt is BNS Section 118 (formerly IPC 325/326)."
    },
    {
        "name": "Dowry Death & Cruelty / Dahej",
        "keywords": [r"\b(dahej|dowry|dowry\s+death|patni\s+ko\s+satana)\b"],
        "new_act": "The Bharatiya Nyaya Sanhita, 2023",
        "new_sections": ["80", "85"],
        "old_act": "The Indian Penal Code, 1860",
        "old_sections": ["304b", "498a"],
        "summary": "Dowry death is BNS Section 80 (formerly IPC 304B); cruelty by husband or relatives is BNS Section 85 (formerly IPC 498A)."
    },
    {
        "name": "Defamation / Maan-Haani",
        "keywords": [r"\b(defamation|maan\s*haani|badnami|manhani)\b"],
        "new_act": "The Bharatiya Nyaya Sanhita, 2023",
        "new_sections": ["356"],
        "old_act": "The Indian Penal Code, 1860",
        "old_sections": ["499", "500"],
        "summary": "Defamation is covered under BNS Section 356 (formerly IPC Section 499 & 500)."
    },
    {
        "name": "Anticipatory Bail / Agrim Zamanat",
        "keywords": [r"\b(anticipatory\s+bail|agrim\s+zamanat|bail\s+before\s+arrest)\b"],
        "new_act": "The Bharatiya Nagarik Suraksha Sanhita, 2023",
        "new_sections": ["482"],
        "old_act": "The Code of Criminal Procedure, 1973",
        "old_sections": ["438"],
        "summary": "Anticipatory bail is governed under BNSS Section 482 (formerly CrPC Section 438)."
    },
    {
        "name": "FIR / Zero FIR",
        "keywords": [r"\b(fir|zero\s+fir|first\s+information\s+report|police\s+complaint)\b"],
        "new_act": "The Bharatiya Nagarik Suraksha Sanhita, 2023",
        "new_sections": ["173"],
        "old_act": "The Code of Criminal Procedure, 1973",
        "old_sections": ["154"],
        "summary": "FIR and Zero FIR provisions are governed under BNSS Section 173 (formerly CrPC Section 154)."
    },
    {
        "name": "Arrest and Police Powers / Giraftari",
        "keywords": [r"\b(arrest|giraftari|police\s+custody|remand)\b"],
        "new_act": "The Bharatiya Nagarik Suraksha Sanhita, 2023",
        "new_sections": ["35", "187"],
        "old_act": "The Code of Criminal Procedure, 1973",
        "old_sections": ["41", "167"],
        "summary": "Arrest procedures are governed under BNSS Section 35 (formerly CrPC Section 41); police remand is BNSS Section 187 (formerly CrPC 167)."
    },
    {
        "name": "Uncontrollable Rage / Provocation / Anger Issues / Gussa",
        "keywords": [r"\b(rage|uncontrollable\s+rage|anger|anger\s+issues|gussa|aakrosh|provocation|sudden\s+fight|heat\s+of\s+passion)\b"],
        "new_act": "The Bharatiya Nyaya Sanhita, 2023",
        "new_sections": ["122", "101"],
        "old_act": "The Indian Penal Code, 1860",
        "old_sections": ["334", "335", "300"],
        "summary": "Acts committed under sudden provocation or uncontrollable rage are governed under BNS Section 122 (formerly IPC 334 & 335 for hurt on provocation) and BNS Section 101 Exception 1 & 4 (formerly IPC 300 Exception 1 & 4 for grave and sudden provocation)."
    },
    {
        "name": "Offenses Committed Outside India / Extraterritorial Jurisdiction",
        "keywords": [r"\b(bahr\s+jakr|bharat\s+se\s+bahar|outside\s+india|crime\s+outside|abroad|foreign\s+crime|extradition)\b"],
        "new_act": "The Bharatiya Nyaya Sanhita, 2023",
        "new_sections": ["1", "47", "48"],
        "old_act": "The Code of Criminal Procedure, 1973",
        "old_sections": ["188", "189"],
        "summary": "Offenses committed outside India by Indian citizens are governed under BNS Section 1(5) (formerly IPC Section 3 and 4) and CrPC Section 188 / BNSS Section 208."
    },
    {
        "name": "Facts Judicially Noticeable / Bare Facts for Laws",
        "keywords": [r"\b(bare\s+facts|judicial\s+notice|facts\s+need\s+not\s+be\s+proved|facts\s+for\s+laws)\b"],
        "new_act": "The Bharatiya Sakshya Adhiniyam, 2023",
        "new_sections": ["51", "52"],
        "old_act": "The Indian Evidence Act, 1872",
        "old_sections": ["56", "57"],
        "summary": "Facts that need not be proved and of which courts must take judicial notice are governed under BSA Section 51 and 52 (formerly IEA Section 56 and 57)."
    },
    {
        "name": "Rash Driving / Hit and Run / Drink and Drive",
        "keywords": [r"\b(drunk\s+driving|rash\s+driving|hit\s+and\s+run|drink\s+and\s+drive|gaadi\s+thok\s+di)\b"],
        "new_act": "The Bharatiya Nyaya Sanhita, 2023",
        "new_sections": ["281", "106"],
        "old_act": "The Indian Penal Code, 1860",
        "old_sections": ["279", "304a"],
        "summary": "Rash driving is BNS Section 281 (formerly IPC 279); causing death by rash/negligent driving (hit and run) is BNS Section 106 (formerly IPC 304A)."
    }
]


class LawMappingService:
    """Singleton service to query statutory transition mappings between Old and New Indian Laws."""

    def __init__(self):
        self._loaded = False
        self.ipc_to_bns: Dict[str, Dict[str, Any]] = {}
        self.bns_to_ipc: Dict[str, Dict[str, Any]] = {}
        self.crpc_to_bnss: Dict[str, Dict[str, Any]] = {}
        self.bnss_to_crpc: Dict[str, Dict[str, Any]] = {}
        self.iea_to_bsa: Dict[str, Dict[str, Any]] = {}
        self.bsa_to_iea: Dict[str, Dict[str, Any]] = {}
        self._load_csv()

    def _load_csv(self):
        """Loads transition mappings from available CSV file."""
        csv_file = None
        for path in CSV_CANDIDATE_PATHS:
            if path.exists():
                csv_file = path
                break

        if not csv_file:
            logger.warning("No transition_mappings.csv found. Law mapping running in catalog fallback mode.")
            return

        try:
            with open(csv_file, mode="r", encoding="utf-8", errors="ignore") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    pair = (row.get("pair") or "").lower().strip()
                    from_sec = (row.get("from_section") or "").strip()
                    to_sec = (row.get("to_section") or "").strip()

                    if not from_sec or not to_sec:
                        continue

                    entry = {
                        "from_act": row.get("from_act", "").upper(),
                        "from_section": from_sec,
                        "from_heading": row.get("from_heading", ""),
                        "to_act": row.get("to_act", "").upper(),
                        "to_section": to_sec,
                        "to_heading": row.get("to_heading", ""),
                        "relation": row.get("relation", ""),
                        "confidence_score": row.get("confidence_score", "1.0")
                    }

                    if pair == "ipc-bns":
                        self.ipc_to_bns[from_sec.lower()] = entry
                        self.bns_to_ipc[to_sec.lower()] = entry
                    elif pair == "crpc-bnss":
                        self.crpc_to_bnss[from_sec.lower()] = entry
                        self.bnss_to_crpc[to_sec.lower()] = entry
                    elif pair == "iea-bsa":
                        self.iea_to_bsa[from_sec.lower()] = entry
                        self.bsa_to_iea[to_sec.lower()] = entry

            self._loaded = True
            logger.info(
                f"LawMappingService initialized: {len(self.ipc_to_bns)} IPC->BNS, "
                f"{len(self.crpc_to_bnss)} CrPC->BNSS, {len(self.iea_to_bsa)} IEA->BSA mappings."
            )
        except Exception as e:
            logger.warning(f"Error loading law mapping CSV: {e}")

    def lookup_section(self, act: str, section: str) -> Optional[Dict[str, Any]]:
        """Finds corresponding section between Old and New law."""
        act_clean = act.lower()
        sec_clean = str(section).strip().lower()

        # Order matters: "bns" is a substring of "bnss", so BNSS must be tested first.
        if "ipc" in act_clean or "indian penal" in act_clean:
            return self.ipc_to_bns.get(sec_clean)
        elif "bnss" in act_clean or "suraksha" in act_clean:
            return self.bnss_to_crpc.get(sec_clean)
        elif "bns" in act_clean or "nyaya" in act_clean:
            return self.bns_to_ipc.get(sec_clean)
        elif "crpc" in act_clean or "criminal procedure" in act_clean:
            return self.crpc_to_bnss.get(sec_clean)
        elif "iea" in act_clean or "evidence" in act_clean:
            return self.iea_to_bsa.get(sec_clean)
        elif "bsa" in act_clean or "sakshya" in act_clean:
            return self.bsa_to_iea.get(sec_clean)

        return None

    def match_offense_catalog(self, query: str) -> List[Dict[str, Any]]:
        """Detects if query matches common criminal offenses."""
        q_low = query.lower()
        matches = []
        for item in OFFENSE_KEYWORDS_CATALOG:
            for pattern in item["keywords"]:
                if re.search(pattern, q_low):
                    matches.append(item)
                    break
        return matches

    def get_transition_guidance(self, query: str, retrieved_docs: List[Document]) -> Optional[str]:
        """
        Builds authoritative transition context comparing Old Law vs New Law
        based on query terms, offense catalog, and retrieved document metadata.
        """
        catalog_matches = self.match_offense_catalog(query)
        transitions_found = []

        # 1. Matches from offense catalog
        for match in catalog_matches:
            transitions_found.append(
                f"- **{match['name']}**:\n"
                f"  * **Current Law in Force (from 1 July 2024)**: {match['new_act']} — Section(s) {', '.join(match['new_sections'])}\n"
                f"  * **Replaced Old Law (before 1 July 2024)**: {match['old_act']} — Section(s) {', '.join(match['old_sections'])}\n"
                f"  * **Key Provisions**: {match['summary']}"
            )

        # 2. Check for explicit section references in query or retrieved docs
        sec_match = re.search(r"\b(?:section|sec|dhara|धारा)\s*(\d+[a-z]?)\b", query, re.IGNORECASE)
        if sec_match:
            sec_num = sec_match.group(1).lower()
            if "ipc" in query.lower() and sec_num in self.ipc_to_bns:
                t = self.ipc_to_bns[sec_num]
                transitions_found.append(
                    f"- **Section Transition**: IPC Section {t['from_section']} ('{t['from_heading']}') "
                    f"is replaced by **BNS Section {t['to_section']}** ('{t['to_heading']}')."
                )
            elif "bns" in query.lower() and sec_num in self.bns_to_ipc:
                t = self.bns_to_ipc[sec_num]
                transitions_found.append(
                    f"- **Section Transition**: BNS Section {t['to_section']} ('{t['to_heading']}') "
                    f"corresponds to former **IPC Section {t['from_section']}** ('{t['from_heading']}')."
                )

        if not transitions_found:
            return None

        guidance = (
            "=== STATUTORY TRANSITION MAPPING (CURRENT LAW VS REPLACED LAW) ===\n"
            "IMPORTANT LEGAL NOTICE ON APPLICABLE LAW:\n"
            "India replaced IPC 1860, CrPC 1973, and IEA 1872 with Bharatiya Nyaya Sanhita 2023 (BNS), "
            "Bharatiya Nagarik Suraksha Sanhita 2023 (BNSS), and Bharatiya Sakshya Adhiniyam 2023 (BSA), "
            "which came into full force on July 1, 2024.\n"
            "- Offenses committed ON OR AFTER July 1, 2024 MUST be charged under the NEW LAWS (BNS/BNSS/BSA).\n"
            "- Offenses committed PRIOR TO July 1, 2024 continue under the OLD LAWS (IPC/CrPC/IEA).\n\n"
            "Applicable Mappings for this Query:\n"
            + "\n".join(transitions_found)
            + "\n\nWhen providing the legal explanation, explain BOTH the Current Law (BNS/BNSS) and the former law (IPC/CrPC) so the user has complete legal clarity."
        )
        return guidance


# Global Singleton
_law_mapping_service: Optional[LawMappingService] = None

def get_law_mapping_service() -> LawMappingService:
    global _law_mapping_service
    if _law_mapping_service is None:
        _law_mapping_service = LawMappingService()
    return _law_mapping_service
