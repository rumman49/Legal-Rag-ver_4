"""Strict Legal Grounding Prompt & LangChain RAG Execution Chain with LangSmith Tracing."""
import os
from typing import Dict, Any, List
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.documents import Document
from app.core.config import settings
from app.llm.provider import get_llm


# Configure LangSmith environment variables if enabled
if settings.LANGCHAIN_TRACING_V2.lower() == "true":
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = settings.LANGCHAIN_API_KEY
    os.environ["LANGCHAIN_PROJECT"] = settings.LANGCHAIN_PROJECT


import re
import logging
from app.ingestion.metadata_cleaner import format_human_legal_reference
from app.rag.legal_refs import extract_references

logger = logging.getLogger(__name__)

GREETING_PATTERN = re.compile(
    r"^\s*(hi|hello|hey|greetings|namaste|ssup|good morning|good evening|thanks|thank you|oh acha|acha|ok|okay|bye)\s*[!.]*\s*$",
    re.IGNORECASE
)

IDENTITY_PATTERN = re.compile(
    r"\b(who\s+are\s+you|kya\s+tum|tum\s+kaun|kaun\s+ho|what\s+are\s+you|your\s+name|tum\s+kya\s+ho|are\s+you\s+a\s+bot|legal\s+ai\s+bot|who\s+made\s+you)\b",
    re.IGNORECASE
)

def detect_query_language(query: str) -> str:
    """
    Detects whether the query language is:
    - 'hindi': Explicit Hindi request ('hindi mai', 'hindi me') OR contains Devanagari script.
    - 'hinglish': Roman script with Hindi/Urdu conversational words.
    - 'english': Standard English query.
    """
    q_stripped = query.strip()
    q_low = q_stripped.lower()

    # 1. Devanagari script characters
    if bool(re.search(r"[\u0900-\u097F]", q_stripped)):
        return "hindi"

    # 2. Explicit Hindi request in prompt
    if bool(re.search(r"\b(hindi\s+(?:mai|me|mein|me\s+batao|mai\s+btao)|in\s+hindi)\b", q_low)):
        return "hindi"

    # 3. Hinglish vocabulary match
    hinglish_words = {
        "kya", "hai", "hain", "kare", "kru", "karu", "karein", "kaise", "mera", "meri", "mere",
        "maine", "humne", "mujhe", "apne", "apna", "apni", "hota", "hoti", "hote", "hoga", "hogi",
        "nahi", "kyu", "kyun", "btao", "batao", "samjhao", "insaan", "hatya", "saza", "kanoon",
        "kanun", "police", "thana", "wajah", "baare", "bare", "mein", "mai", "pe", "se", "ko",
        "par", "aur", "bhi", "toh", "kab", "kahan", "kiski", "kisko", "kisi", "kisne", "kar",
        "diya", "di", "raha", "rahi", "rahe", "gaya", "gayi", "chori", "dhokha", "marpeet",
        "zamanat", "vakil", "faisla", "adalat", "mukadma", "dahez", "dahej", "kuch", "iska", "iski",
        "isme", "usme", "bhai", "sir", "madam", "boliye", "bolo", "bataiye", "bache", "bachne"
    }
    tokens = set(re.findall(r"[a-z]+", q_low))
    if bool(tokens.intersection(hinglish_words)):
        return "hinglish"

    return "english"


def build_dynamic_system_prompt(
    query: str,
    retrieved_documents: List[Document]
) -> str:
    """Builds a strictly targeted system prompt with exact language directives and Old vs New law mappings."""
    lang = detect_query_language(query)

    if lang == "hinglish":
        language_directive = """MANDATORY LANGUAGE DIRECTIVE: HINGLISH (ROMAN SCRIPT)
- The user asked in Hinglish (Hindi/Urdu words written in the Roman/English alphabet, e.g. "maine ek insaan ki hatya krdi ab mai kya kru").
- YOU MUST RESPOND 100% IN NATURAL, FLUENT HINGLISH using the Roman/English alphabet (e.g. "Yeh ek bahut gambhir mamla hai. Bharatiya Nyaya Sanhita (BNS) 2023 ke antargat...").
- STRICT PROHIBITION: DO NOT USE DEVANAGARI HINDI SCRIPT (जैसे यह लिपि). Output ONLY in Roman script Hinglish!
- Structure your response with clear Hinglish headings:
  ### Kanooni Sthiti aur Dharaayein (Legal Provisions)
  ### Saza aur Jurmana (Penalties & Provisions)
  ### Turant Kya Kadam Uthane Chahiye (Crucial Practical Steps)
  ### Saral Sankshep (Summary)"""
    elif lang == "hindi":
        language_directive = """MANDATORY LANGUAGE DIRECTIVE: PURE HINDI (DEVANAGARI SCRIPT)
- The user asked in Hindi or requested Hindi ("hindi mai" / "hindi me").
- YOU MUST RESPOND 100% IN SHUDDH AUR SARAL DEVANAGARI HINDI (हिंदी लिपि).
- Do NOT output English paragraphs.
- Structure your response with clear Devanagari headings:
  ### कानूनी स्थिति और धाराएं (Legal Provisions)
  ### सजा और प्रावधान (Penalties & Provisions)
  ### तुरंत क्या कदम उठाने चाहिए (Actionable Steps)
  ### सरल संक्षेप (Summary)"""
    else:
        language_directive = """MANDATORY LANGUAGE DIRECTIVE: ENGLISH
- The user asked in English.
- YOU MUST RESPOND 100% IN CLEAR, PROFESSIONAL ENGLISH.
- STRICT PROHIBITION: DO NOT output any Hinglish or Hindi summary section (such as 'संक्षेप (Hinglish Summary)') when the user query is in English. Keep the entire response in English."""

    # Retrieve transition guidance from LawMappingService
    try:
        from app.rag.law_mapping_service import get_law_mapping_service
        mapping_svc = get_law_mapping_service()
        transition_guidance = mapping_svc.get_transition_guidance(query, retrieved_documents)
    except Exception as e:
        logger.warning(f"Error fetching transition guidance: {e}")
        transition_guidance = None

    transition_block = f"\n\n{transition_guidance}\n" if transition_guidance else ""

    return f"""You are an expert Multilingual Indian Legal AI Assistant. Your objective is to provide strictly grounded, clear legal explanations based on the RETRIEVED STATUTORY CONTEXT and TRANSITION MAPPINGS below.

{language_directive}

CRITICAL LEGAL & GROUNDING RULES:
1. STRICT GROUNDING, REFUSAL & PARTIAL FULFILLMENT:
   - If the RETRIEVED STATUTORY CONTEXT is entirely empty or completely irrelevant to the user's query, YOU MUST CLEARLY STATE: "I do not have any laws or provisions related to [topic] in my statutory database."
   - IF THE CONTEXT PARTIALLY ANSWERS THE QUERY (e.g., contains the requested statute but lacks requested case laws, interpretations, or specific sub-rules), you MUST answer the part that is supported by the text.
   - For the missing portion, explicitly state: "The retrieved documents do not contain information regarding [missing subject]." DO NOT issue a blanket refusal if relevant partial context is present.
   - ABSOLUTELY DO NOT try to answer from memory, fabricate general legal explanations, or bring in external knowledge (like state laws or unretrieved labor codes) if the specific statute is absent from the context.

2. SOURCE HONESTY & ZERO HALLUCINATION:
   - You must answer ONLY using the exact facts and provisions found in the RETRIEVED STATUTORY CONTEXT below.
   - Name a section/article number ONLY if it appears in the context, and cite it as "<Act> Section <no>" using the Act and number shown in that source's header. Never describe a neighbouring or "related" section from memory.
   - If the user asked for a specific section and that section is NOT in the context, say so in one sentence (e.g. "Section 173 of the BNSS is not in the retrieved context") and stop. Do not paraphrase what that section probably says.
   - When quoting the law, copy the operative wording from the context. Do not add penalties, fines, time limits, or conditions that the context does not state.
   - You must not inject specific case laws (e.g., Supreme Court rulings), historical statutes (like the IPC/CrPC), or external legal precedents into your answer UNLESS they are physically written in the provided retrieved text or the transition mappings.
   - NEVER claim your own internal knowledge is part of the retrieved context.

3. CURRENT LAW VS OLD LAW (TRANSITION FRAMEWORK):
   - Always clarify that since 1 July 2024, the new criminal laws (BNS, BNSS, BSA) are in effect.
   - If the retrieved context contains the OLD law (e.g., IPC/CrPC) but NOT the exact text of the NEW law (e.g., BNS/BNSS), you may state the new section number IF provided by the transition mappings.
   - HOWEVER, YOU MUST NOT invent, guess, or explain the detailed provisions, timelines, or sub-sections of the new law from your memory. You must state: "The specific text of the new BNSS/BNS provision is not in the retrieved context, but it corresponds to [Old Law] which states..."

4. RESPONSIBLE PRACTICAL & PROCEDURAL GUIDANCE:
   - If the user asks about an alleged crime or urgent situation:
     * Explain the applicable offense and penalties objectively based strictly on the retrieved law.
     * Emphasize the vital necessity of immediately contacting a qualified criminal defense advocate (vakil).
     * Warn against destroying or tampering with evidence.
     * Explain lawful, peaceful surrender before a police officer or Judicial Magistrate as the legally mandated path.
     * Include a clear reminder that this is educational legal information and does not constitute formal attorney-client representation.

{transition_block}

FINAL AND MOST IMPORTANT RULE:
{language_directive}

RETRIEVED STATUTORY CONTEXT:
{{context}}
"""

def format_context(documents: List[Document]) -> str:
    """Formats retrieved Documents into grounded context string with citations."""
    if not documents:
        return "No relevant statutory context retrieved."

    formatted = []
    for idx, doc in enumerate(documents, 1):
        meta = doc.metadata
        ref = format_human_legal_reference(meta)
        act = meta.get("act_name") or meta.get("document_name") or "Bare Act"
        sec = meta.get("section_no") or meta.get("article_no") or meta.get("rule_no") or "Provision"
        title = meta.get("section_title") or meta.get("article_title") or meta.get("rule_title") or ""
        path = meta.get("hierarchy_path") or ""
        path_str = f" | Scope: {path}" if path else ""

        # Additional statutory metadata tags
        tags = []
        if meta.get("previous_law") and meta.get("previous_section"):
            tags.append(f"Old Law: {meta['previous_law']} Section {meta['previous_section']}")
        if meta.get("punishment_summary"):
            tags.append(f"Punishment: {meta['punishment_summary']}")
        elif meta.get("punishment_maximum_years"):
            tags.append(f"Punishment: Up to {meta['punishment_maximum_years']} yrs")
        if meta.get("bailable") is not None:
            tags.append("Bailable" if meta.get("bailable") else "Non-Bailable")
        if meta.get("cognizable") is not None:
            tags.append("Cognizable" if meta.get("cognizable") else "Non-Cognizable")

        tag_str = f" | [{', '.join(tags)}]" if tags else ""

        # Clean snippet header text
        clean_body = re.sub(r"^\[Act:[^\]]+\]\s*-*\s*", "", doc.page_content, flags=re.IGNORECASE).strip()

        header = f"--- Source [{idx}]: {ref} | Act: {act} | Provision: {sec} {title}{path_str}{tag_str} ---"
        formatted.append(f"{header}\n{clean_body}")

    return "\n\n".join(formatted)


def contextualize_query(
    query: str,
    chat_history: List[Dict[str, Any]] | None = None,
    provider: str = "groq"
) -> str:
    """Reformulates conversational follow-up queries (e.g. 'kya hota hai isme') into standalone legal search queries using conversation context."""
    if not chat_history:
        return query

    clean_q = query.strip()
    if not clean_q:
        return query

    # Check if query is referential or a brief follow-up
    referential_patterns = [
        r"\b(isme|ispe|iska|iski|ismein|iske|usme|uska|uski|ye|yeh|wo|woh)\b",
        r"\b(it|this|that|these|those|they|them)\b",
        r"\b(punishment|saza|fine|details|kya hota hai|kya hai|kya matlab|samjhao|explain|clarify)\b",
        r"\b(what about|what is|how much|and what)\b"
    ]
    query_lower = clean_q.lower()
    is_referential = any(re.search(pat, query_lower) for pat in referential_patterns)
    has_explicit_ref = bool(extract_references(clean_q))

    # If the user already asked a standalone query with a specific section/article, no need to rewrite
    if has_explicit_ref and not is_referential:
        return clean_q

    # Extract last user and assistant messages
    recent = chat_history[-4:]
    history_lines = []
    prev_user_ref = ""
    for m in recent:
        role = (m.get("role") or "user").lower()
        content = (m.get("content") or m.get("text") or "").strip()
        if content:
            history_lines.append(f"{role.capitalize()}: {content[:250]}")
            if role in ["user", "human"] and not prev_user_ref:
                prev_refs = extract_references(content)
                if prev_refs:
                    prev_user_ref = prev_refs[0].get("raw") or ""

    if not history_lines:
        return clean_q

    history_text = "\n".join(history_lines)
    prompt_text = (
        "Given the following conversation history and a follow-up question from the user, "
        "rephrase the follow-up question into a complete, standalone Indian legal search query. "
        "Preserve the exact statute, section, article, or legal subject mentioned previously. "
        "Return ONLY the reformulated search query without explanation.\n\n"
        f"Chat History:\n{history_text}\n\n"
        f"Follow-up Question: {clean_q}\n"
        "Standalone Query:"
    )

    try:
        llm = get_llm(provider=provider)
        rephrased = llm.invoke(prompt_text).content.strip()
        rephrased = re.sub(r'^["\']|["\']$', '', rephrased).strip()
        if rephrased and len(rephrased) > 3:
            return rephrased
    except Exception as e:
        logger.warning(f"Query contextualization fallback: {e}")
        if prev_user_ref:
            return f"{prev_user_ref} {clean_q}"

    return clean_q


def run_legal_rag_chain(
    query: str,
    retrieved_documents: List[Document],
    provider: str | None = None,
    model_name: str | None = None,
    chat_history: List[Dict[str, Any]] | None = None
) -> Dict[str, Any]:
    """Executes the grounded RAG chain using the requested LLM provider with fallback handling."""
    clean_q = query.strip()
    detected_lang = detect_query_language(clean_q)

    # Small Talk / Greetings Interceptor (returns polite natural response without statutory warning)
    if GREETING_PATTERN.match(clean_q):
        if detected_lang == "hindi":
            reply = "नमस्ते! मैं आपका बहुभाषी कानूनी AI सहायक हूँ। आप भारतीय न्याय संहिता (BNS), BNSS, BSA, संविधान या किसी भी भारतीय कानून के बारे में सवाल पूछ सकते हैं। मैं आज आपकी क्या सहायता करूँ?"
        elif detected_lang == "hinglish":
            reply = "Namaste! Main aapka Multilingual Legal AI Assistant hoon. Aap Bharatiya Nyaya Sanhita (BNS), BNSS, BSA, Constitution ya kisi bhi Indian Bare Act ke baare mein sawal pooch sakte hain. Main aaj aapki kya madad karoon?"
        else:
            reply = "Hello! I am your Multilingual Indian Legal AI Assistant. You can ask me questions about Indian Bare Acts (BNS, BNSS, BSA, Constitution, etc.) in English, Hindi, or Hinglish. How can I assist you today?"
        
        return {
            "query": query,
            "answer": reply,
            "citations": [],
            "provider": provider or settings.DEFAULT_LLM_PROVIDER,
            "documents_count": 0
        }

    # Bot Identity Interceptor (answers identity questions naturally without fetching unrelated legal documents)
    if IDENTITY_PATTERN.search(clean_q):
        if detected_lang == "hindi":
            reply = "हाँ, मैं आपका बहुभाषी कानूनी AI सहायक हूँ। मैं भारतीय न्याय संहिता (BNS 2023), BNSS 2023, BSA 2023, भारत का संविधान और सभी 900+ भारतीय कानूनों (Bare Acts) के आधार पर आपके प्रश्नों के उत्तर पूरी प्रामाणिकता के साथ दे सकता हूँ।"
        elif detected_lang == "hinglish":
            reply = "Haan, main aapka Multilingual Legal AI Assistant hoon! Main Bharatiya Nyaya Sanhita (BNS 2023), BNSS 2023, BSA 2023, Constitution of India, aur sabhi Indian Bare Acts ke baare mein aapke kanooni sawalon ke jawab strictly grounded tarike se de sakta hoon. Aap kisi bhi Act ya Section ke baare mein sawal pooch sakte hain."
        else:
            reply = "Yes, I am your Multilingual Indian Legal AI Assistant. I provide strictly grounded legal answers based on BNS 2023, BNSS 2023, BSA 2023, the Constitution of India, and all Indian Bare Acts."

        return {
            "query": query,
            "answer": reply,
            "citations": [],
            "provider": provider or settings.DEFAULT_LLM_PROVIDER,
            "documents_count": 0
        }

    # If no relevant statutory context was retrieved from the database, decline directly without hallucinating
    if not retrieved_documents:
        if detected_lang == "hindi":
            reply = (
                "मेरे वैधानिक डेटाबेस (Statutory Database) में आपके इस प्रश्न से संबंधित कोई कानून या धाराएं उपलब्ध नहीं हैं।\n\n"
                "मेरा नॉलेज बेस मुख्य रूप से भारत के केंद्रीय कानूनों (Central Bare Acts), भारतीय न्याय संहिता (BNS 2023), "
                "BNSS 2023, BSA 2023 और भारत के संविधान पर आधारित है। यदि आपका प्रश्न किसी स्थानीय या राज्य-स्तरीय कानून "
                "के बारे में है जो यहाँ अनुक्रमित नहीं है, तो कृपया संबंधित विभाग या स्थानीय अधिवक्ता से परामर्श लें।"
            )
        elif detected_lang == "hinglish":
            reply = (
                "Mere statutory database mein aapke is sawaal se sambandhit koi kanoon ya statutory provisions uplabdh nahi hain.\n\n"
                "Mera knowledge base mukhya roop se Indian Central Bare Acts, Bharatiya Nyaya Sanhita (BNS 2023), BNSS 2023, "
                "BSA 2023 aur Constitution of India par aadharit hai. Agar aapka sawal kisi local ya state-specific kanoon "
                "ke baare mein hai jo yahan indexed nahi hai, toh kripya sambhandhit department ya local advocate se consult karein."
            )
        else:
            reply = (
                "I do not have any laws, bare acts, or statutory provisions related to this topic in my statutory database.\n\n"
                "My knowledge base covers Indian Central Bare Acts (including the Bharatiya Nyaya Sanhita 2023, "
                "BNSS 2023, BSA 2023, and the Constitution of India). If your inquiry pertains to unindexed state legislation, "
                "local municipal rules, or topics outside Indian statutory law, these are not present in this central repository."
            )

        return {
            "query": query,
            "answer": reply,
            "citations": [],
            "provider": provider or settings.DEFAULT_LLM_PROVIDER,
            "documents_count": 0
        }

    context_str = format_context(retrieved_documents)
    dynamic_system_prompt = build_dynamic_system_prompt(clean_q, retrieved_documents)
    
    message_templates = [
        ("system", dynamic_system_prompt)
    ]
    if chat_history:
        for m in chat_history[-6:]:
            role = (m.get("role") or "user").lower()
            content = (m.get("content") or m.get("text") or "").strip()
            if not content:
                continue
            if role in ["user", "human"]:
                message_templates.append(("human", content))
            elif role in ["assistant", "bot", "ai"]:
                message_templates.append(("ai", content[:800]))

    message_templates.append(("human", "{query}"))
    prompt = ChatPromptTemplate.from_messages(message_templates)

    primary_provider = provider or settings.DEFAULT_LLM_PROVIDER
    providers_to_try = [primary_provider]
    for p in (settings.LLM_FALLBACK_PROVIDERS or "").split(","):
        p = p.strip()
        if p and p not in providers_to_try:
            providers_to_try.append(p)

    answer = None
    used_provider = primary_provider
    last_error = None

    for p in providers_to_try:
        try:
            m_name = model_name if p == primary_provider else None
            llm = get_llm(provider=p, model_name=m_name)
            chain = prompt | llm | StrOutputParser()
            answer = chain.invoke({
                "context": context_str,
                "query": query
            })
            used_provider = p
            break
        except Exception as e:
            logger.warning(f"LLM Provider '{p}' failed: {e}. Trying fallback if available.")
            last_error = e
            continue

    if answer is None:
        answer = f"⚠️ Unable to generate response from LLM provider ({primary_provider}). Error details: {str(last_error)}. Please verify your API key and model settings in `.env`."

    # Prepare enriched structured citations for frontend drawer & relevance score
    citations = []
    for idx, d in enumerate(retrieved_documents):
        meta = d.metadata
        human_ref = format_human_legal_reference(meta)
        raw_score = meta.get("rerank_score") or meta.get("similarity_score")
        
        # Format dynamic relevance percentage score
        if meta.get("is_exact_match"):
            score_pct = 98
        elif isinstance(raw_score, (float, int)) and raw_score > 0:
            if raw_score >= 0.5:
                score_pct = max(80, min(98, int(round(raw_score * 100))))
            elif raw_score >= 0.005:
                score_pct = max(65, min(85, int(round(65 + raw_score * 400))))
            else:
                score_pct = max(45, min(65, int(round(45 + raw_score * 3000))))
        else:
            score_pct = 60

        # Clean snippet header text
        clean_snippet = d.page_content.strip()
        clean_snippet = re.sub(r"^\[Act:[^\]]+\]\s*-*\s*", "", clean_snippet, flags=re.IGNORECASE).strip()

        citations.append({
            "legal_reference": human_ref,
            "doc_name": human_ref or meta.get("act_name") or meta.get("document_name") or "Indian Statute",
            "document_name": meta.get("document_name") or meta.get("act_name") or human_ref,
            "act_name": meta.get("act_name") or human_ref.split(" — ")[0],
            "section_no": meta.get("section_no") or meta.get("article_no") or "",
            "article_no": meta.get("article_no") or "",
            "section_title": meta.get("section_title") or meta.get("article_title") or "",
            "score": f"{score_pct}%",
            "score_val": score_pct,
            "snippet": clean_snippet,
            "text": clean_snippet
        })

    return {
        "query": query,
        "answer": answer,
        "citations": citations,
        "provider": used_provider,
        "documents_count": len(retrieved_documents)
    }



