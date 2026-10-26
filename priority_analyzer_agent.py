import os
import re
from typing import TypedDict
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.memory import MemorySaver
from langchain_core.messages import HumanMessage
from langchain_ollama import ChatOllama, OllamaEmbeddings
from langchain_chroma import Chroma

# 1. Define Patient State Schema
class PatientState(TypedDict):
    patient_name: str
    sickness: str
    priority: int
    doctor_name: str
    status: str
    appointment_time: str
    confidence: int
    reasoning: str
    guideline: str

# 2. Load the local Chroma vector store and Mistral model
embeddings = OllamaEmbeddings(model="nomic-embed-text:latest")
vector_store = Chroma(
    persist_directory="./chroma_triage_db",
    embedding_function=embeddings
)
llm = ChatOllama(model="mistral:latest")

# 3. Define the AI Node with Precise RAG and Regex Parsing
def analyze_priority(state: PatientState):
    """Searches the PDF triage rules using RAG, then extracts the P-level,
    confidence, matched guideline and a short clinical justification."""
    print(f"\n[AI Agent] Searching triage rules for: {state['sickness']}...")

    # RAG search for matching rules in your PDF
    docs = vector_store.similarity_search(state['sickness'], k=2)
    retrieved_rules = "\n".join([doc.page_content for doc in docs])

    # Fallback guideline name taken from the matched document's metadata.
    fallback_guideline = "Triage guide"
    if docs:
        source = (docs[0].metadata or {}).get("source")
        if source:
            fallback_guideline = os.path.basename(str(source))

    prompt = f"""
    You are a strict clinical triage assistant. Match the patient's symptoms to the correct rule in the Triage Guide below.

    --- TRIAGE GUIDE RULES ---
    {retrieved_rules}
    --------------------------

    Patient Name: {state['patient_name']}
    Symptoms: {state['sickness']}

    Instructions:
    1. Find the exact matching discriminator row in the rules.
    2. Identify its Priority Level (P1, P2, P3, P4, or P5).
    3. Respond with EXACTLY these four lines and nothing else:
    PRIORITY: P1-P5
    CONFIDENCE: <integer between 0 and 100>
    GUIDELINE: <short name of the matched rule>
    REASON: <one short clinical sentence>
    """

    response = llm.invoke([HumanMessage(content=prompt)])
    raw_text = response.content.strip()
    print(f"[AI Agent] Raw LLM Response: {raw_text}")

    # PRECISE PARSING: prefer the labelled PRIORITY line, then look for 'P' + digit.
    match = re.search(r'PRIORITY:\s*P?([1-5])', raw_text, re.IGNORECASE) \
        or re.search(r'P([1-5])', raw_text, re.IGNORECASE)

    if match:
        suggested_priority = int(match.group(1))
    else:
        # Fallback if 'P' was missed, search for any standalone digit 1-5
        fallback_match = re.search(r'[1-5]', raw_text)
        suggested_priority = int(fallback_match.group()) if fallback_match else 3

    conf_match = re.search(r'CONFIDENCE:\s*(\d{1,3})', raw_text, re.IGNORECASE)
    confidence = int(conf_match.group(1)) if conf_match else 80
    confidence = max(0, min(100, confidence))

    guide_match = re.search(r'GUIDELINE:\s*(.+)', raw_text, re.IGNORECASE)
    guideline = guide_match.group(1).strip() if guide_match else fallback_guideline

    reason_match = re.search(r'REASON:\s*(.+)', raw_text, re.IGNORECASE)
    reasoning = reason_match.group(1).strip() if reason_match else ""

    print(f"[AI Agent] Correctly Assigned Priority: P{suggested_priority} "
          f"(confidence {confidence} %, guideline: {guideline})")

    return {
        "priority": suggested_priority,
        "status": "pending_approval",
        "confidence": confidence,
        "reasoning": reasoning,
        "guideline": guideline
    }

# 4. Define the Database Save Node
def save_to_database(state: PatientState):
    print(f"\n[Database] Saving patient {state['patient_name']} (Priority P{state['priority']}) to database!")
    return {"status": "approved_and_saved"}

# 5. Build the Workflow Graph with HITL Interrupt
workflow = StateGraph(PatientState)
workflow.add_node("analyze_priority", analyze_priority)
workflow.add_node("save_to_database", save_to_database)

workflow.add_edge(START, "analyze_priority")
workflow.add_edge("analyze_priority", "save_to_database")
workflow.add_edge("save_to_database", END)

memory = MemorySaver()
graph = workflow.compile(
    checkpointer=memory, 
    interrupt_before=["save_to_database"]
)
