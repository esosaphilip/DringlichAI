from priority_analyzer_agent import graph

def run_triage_system():
    print("=== AI HOSPITAL FRONT-DESK TRIAGE SYSTEM ===")
    
    name = input("Enter patient name: ")
    sickness = input("Enter patient sickness/symptoms: ")
    doctor = input("Enter assigned doctor: ")
    appt_time = input("Enter appointment time (HH:MM): ")

    initial_state = {
        "patient_name": name,
        "sickness": sickness,
        "priority": 0,
        "doctor_name": doctor,
        "status": "new",
        "appointment_time": appt_time
    }

    config = {"configurable": {"thread_id": "triage_session_001"}}

    # 1. Run graph (Executes AI analysis and stops before saving)
    print("\n--- Running AI Triage Analysis ---")
    graph.invoke(initial_state, config)

    # 2. Retrieve paused state for the human nurse check
    current_state = graph.get_state(config)
    ai_priority = current_state.values.get("priority")
    
    print(f"\n[HUMAN-IN-THE-LOOP CHECKPOINT]")
    print(f"Patient: {name}")
    print(f"AI Suggested Priority: P{ai_priority}")
    
    # 3. Nurse approval gate
    decision = input("Do you approve this priority? (y/n): ").strip().lower()

    if decision == 'y':
        print("\nNurse Approved! Resuming graph to save to database...")
        graph.invoke(None, config)
        print("Process complete. Patient successfully queued.")
    else:
        print("\nNurse Rejected. Triage aborted.")

if __name__ == "__main__":
    run_triage_system()