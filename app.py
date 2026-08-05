import streamlit as st
import pandas as pd
import random
import uuid
import json
from streamlit_gsheets import GSheetsConnection

# 1. Page Config 
st.set_page_config(page_title="UniCompanion Evaluation", page_icon="🤖", layout="centered")

# --- GLOBAL COUNTER FUNCTION ---
def get_and_increment_participant_counter():
    conn = st.connection("gsheets", type=GSheetsConnection)
    try:
        counter_data = conn.read(worksheet="Counter", ttl=0)
        if counter_data is not None and not counter_data.empty and "count" in counter_data.columns:
            val = counter_data["count"].iloc[0]
            count = int(val) if pd.notna(val) else 0
        else:
            count = 0
    except Exception as e:
        print(f"Counter read error: {e}")
        count = 0
        
    new_data = pd.DataFrame([{"count": count + 1}])
    conn.update(worksheet="Counter", data=new_data)
    return count

# --- INITIALIZE STATE ---
if 'initialized' not in st.session_state:
    st.session_state.initialized = True
    st.session_state.participant_id = str(uuid.uuid4())[:8]
    st.session_state.participant_index = get_and_increment_participant_counter()
    
    # State tracking for the block loops
    st.session_state.current_run = 1                        
    st.session_state.current_q_index = 0                    
    
    # Load JSON
    try:
        with open("questions_data.json", "r", encoding="utf-8") as f:
            raw_data = json.load(f)
            active_blocks = [
                "Semantic_Low_Explainable", 
                "Semantic_High_Explainable",
                "Graph_Low_Explainable",
                "Graph_High_Explainable"
            ]
            st.session_state.question_pools = {
                k: v for k, v in raw_data.items() if k in active_blocks
            }
    except FileNotFoundError:
        st.error("Error: 'questions_data.json' not found.")
        st.stop()
    
    st.session_state.block_order = random.sample(list(st.session_state.question_pools.keys()), len(st.session_state.question_pools))
    st.session_state.active_pipeline = None
    st.session_state.active_questions = [] 
    
    st.session_state.responses = {
        "participant_id": st.session_state.participant_id,
        "global_participant_sequence": st.session_state.participant_index,
        "consent_given": False,
        "demographics": {},
        "block_presentation_order": st.session_state.block_order,
        "block_evaluations": {
            block_name: [] for block_name in st.session_state.block_order
        }
    }

# --- DEFINE PAGES & NAVIGATION ---
# These point directly to the files inside your 'pages' folder
pages = [
    st.Page("pages/1_consent.py", title="Consent Form"),
    st.Page("pages/2_demographics.py", title="Demographics"),
    st.Page("pages/3_instructions.py", title="Instructions"),
    st.Page("pages/4_role_reminder.py", title="Role Reminder"),
    st.Page("pages/5_question_eval.py", title="System Evaluation"),
    st.Page("pages/5b_bounce.py", title="Loading..."),
    st.Page("pages/6_pipeline_survey.py", title="Survey"),
    st.Page("pages/7_final.py", title="Finish")
]

# Position="hidden" ensures users cannot click around the sidebar to skip pages
pg = st.navigation(pages, position="hidden")
pg.run()
