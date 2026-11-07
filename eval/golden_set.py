"""Golden evaluation set for DringlichAI's triage pipeline.

WHY THIS EXISTS: to measure triage accuracy honestly against a fixed, human-derived set of
cases instead of eyeballing single examples. Every case is derived from a real discriminator in
`DringlichAI_Mock_Triage_Guide.pdf` and carries the priority a clinician would expect, which is
what makes the numbers reproducible and defensible.

INTERVIEW TALKING POINT: the set is deliberately weighted toward P1 so the zero-tolerance
under-triage check has enough urgent cases to be meaningful, and it includes a couple of
on-purpose ambiguous cases (e.g. CP-06a) plus a no-match case so the harness measures a hard
question, not a softball.

The data below is fixed — do not regenerate or re-derive it. It is the ground truth the harness
scores against.
"""

# Scored set: every case has a known expected_priority taken from the guideline.
GOLDEN_SET = [
    # --- Chest pain (CP) ---
    {"id": "CP-01a", "symptoms": "68-year-old, severe chest pain, collapsed on the waiting room floor, hard to rouse.",
     "expected_priority": 1, "guideline": "CP-01", "note": "classic unambiguous P1 — collapse + chest pain"},
    {"id": "CP-02a", "symptoms": "Chest pain, gasping for air, can't get a full sentence out between breaths.",
     "expected_priority": 1, "guideline": "CP-02", "note": "P1 — severe breathing difficulty with chest pain"},
    {"id": "CP-03a", "symptoms": "Crushing pressure in the chest spreading into the left arm and jaw, sweating heavily, looks pale.",
     "expected_priority": 2, "guideline": "CP-03", "note": "classic cardiac-pattern P2"},
    {"id": "CP-04a", "symptoms": "Sudden severe chest pain that started about 20 minutes ago, patient rates it 8 out of 10.",
     "expected_priority": 2, "guideline": "CP-04", "note": "sudden onset within the hour, high severity"},
    {"id": "CP-05a", "symptoms": "Chest pain that gets worse when breathing in deeply or moving, otherwise stable and talking normally.",
     "expected_priority": 3, "guideline": "CP-05", "note": "pain only on movement/breathing, stable otherwise"},
    {"id": "CP-06a", "symptoms": "Mild chest ache on and off for the past four days, nothing else going on.",
     "expected_priority": 4, "guideline": "CP-06", "note": "AMBIGUOUS by design — tests whether duration gets confused with CP-04's sudden-onset case"},
    # --- Shortness of breath (SB) ---
    {"id": "SB-01a", "symptoms": "Can't speak at all, lips look blue-grey, looks completely exhausted from trying to breathe.",
     "expected_priority": 1, "guideline": "SB-01", "note": "classic P1 respiratory failure pattern"},
    {"id": "SB-02a", "symptoms": "Can only manage two or three words before needing to catch her breath.",
     "expected_priority": 2, "guideline": "SB-02", "note": "few-words-at-a-time breathlessness"},
    {"id": "SB-03a", "symptoms": "Known asthmatic, wheezing, but can speak in full sentences and the usual inhaler hasn't helped much yet.",
     "expected_priority": 3, "guideline": "SB-03", "note": "known condition, still verbally fluent"},
    {"id": "SB-05a", "symptoms": "Mild cough with a cold, breathing feels completely normal at rest.",
     "expected_priority": 5, "guideline": "SB-05", "note": "classic non-urgent"},
    # --- Headache (HA) ---
    {"id": "HA-01a", "symptoms": "Severe headache, very drowsy, hard to keep awake, family says he had a brief fit earlier.",
     "expected_priority": 1, "guideline": "HA-01", "note": "reduced consciousness + seizure, highest-urgency headache"},
    {"id": "HA-02a", "symptoms": "Sudden headache an hour ago, says it's the worst headache of her life, came on like a thunderclap.",
     "expected_priority": 2, "guideline": "HA-02", "note": "classic thunderclap / worst-ever headache red flag"},
    {"id": "HA-03a", "symptoms": "Headache with a fever and a stiff neck, seems a bit confused compared to normal.",
     "expected_priority": 2, "guideline": "HA-03", "note": "meningitic red flags"},
    {"id": "HA-04a", "symptoms": "Moderate headache with some vomiting, says it feels like her usual migraines.",
     "expected_priority": 3, "guideline": "HA-04", "note": "known migraine pattern"},
    # --- Abdominal pain (AB) ---
    {"id": "AB-01a", "symptoms": "Severe stomach pain, patient collapsed and is very hard to wake up.",
     "expected_priority": 1, "guideline": "AB-01", "note": "collapse + abdominal pain"},
    {"id": "AB-02a", "symptoms": "Severe abdominal pain, around 9 out of 10, and there was some blood when he vomited.",
     "expected_priority": 2, "guideline": "AB-02", "note": "severe pain with blood in vomit"},
    {"id": "AB-04a", "symptoms": "Stomach pain with diarrhoea, still able to drink fluids normally.",
     "expected_priority": 4, "guideline": "AB-04", "note": "can tolerate fluids, lower urgency"},
    # --- Wounds / minor injury (WI) ---
    {"id": "WI-01a", "symptoms": "Deep cut on the forearm, still bleeding heavily even after ten minutes of firm pressure.",
     "expected_priority": 1, "guideline": "WI-01", "note": "uncontrolled bleeding"},
    {"id": "WI-02a", "symptoms": "Nasty cut on the shin, you can actually see the bone, and the foot looks like it's at a strange angle.",
     "expected_priority": 2, "guideline": "WI-02", "note": "visible bone / deformity"},
    {"id": "WI-05a", "symptoms": "Small graze on the knee from a fall, nothing else bothering her.",
     "expected_priority": 5, "guideline": "WI-05", "note": "classic minor/non-urgent"},
]

# Separate from the scored set above: this case has NO clean guideline match on purpose.
# It isn't scored as right/wrong against one number — it's there to observe and document
# what the system actually does (today: falls through to the priority-3 default) when the
# input doesn't cleanly match any rule, which is a real, everyday intake scenario.
NO_MATCH_CASE = {
    "id": "NOMATCH-01", "symptoms": "Patient says they feel 'kind of off' today, nothing specific.",
    "expected_priority": None, "guideline": None,
    "note": "deliberately vague — documents current fallback behavior on a no-match input"
}
