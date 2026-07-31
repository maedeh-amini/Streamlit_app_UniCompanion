import streamlit as st
import pandas as pd
import numpy as np
import random
import uuid
import json
import os
import time
import streamlit.components.v1 as components
from streamlit_gsheets import GSheetsConnection

# 1. Keep the global layout centered by default to maintain thin text-heavy pages
st.set_page_config(page_title="UniCompanion Evaluation", page_icon="🤖", layout="centered")

def scroll_to_top():
    """Forces the Streamlit container to scroll to the top using a zero-height iframe."""
    components.html(
        """
        <script>
            const parent = window.parent.document;
            const main = parent.querySelector('.main') || parent.querySelector('[data-testid="stAppViewContainer"]');
            if (main) {
                main.scrollTo({ top: 0, behavior: 'instant' });
            }
        </script>
        """,
        height=0
    )

# --- GLOBAL COUNTER FUNCTION ---
def get_and_increment_participant_counter():
    """Reads a global counter from Google Sheets to assign sequential question blocks."""
    # Establish the connection
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # 1. Fetch current counter (ttl=0 ensures we don't get a cached old value)
    try:
        counter_data = conn.read(worksheet="Counter", ttl=0)
        
        # Check if the dataframe is properly formatted
        if counter_data is not None and not counter_data.empty and "count" in counter_data.columns:
            val = counter_data["count"].iloc[0]
            # Handle potential NaN or missing values
            count = int(val) if pd.notna(val) else 0
        else:
            count = 0
            
    except Exception as e:
        # Fallback if the sheet isn't set up or encounters a read error
        print(f"Counter read error: {e}")
        count = 0
        
    # 2. Increment and save for the next participant
    new_data = pd.DataFrame([{"count": count + 1}])
    
    # Write the updated dataframe back to the 'Counter' worksheet
    conn.update(worksheet="Counter", data=new_data)
    
    return count

# --- 2. INITIALIZE DATA & SESSION STATE ---
if 'initialized' not in st.session_state:
    st.session_state.initialized = True
    st.session_state.participant_id = str(uuid.uuid4())[:8]
    
    # Get this participant's global sequence number (0 for the 1st person, 1 for the 2nd, etc.)
    st.session_state.participant_index = get_and_increment_participant_counter()
    
    # Flow: consent -> demographics -> instructions -> role_reminder -> question_eval -> pipeline_survey -> final
    st.session_state.current_page = "consent"  
    st.session_state.current_run = 1                        
    st.session_state.current_q_index = 0                    
    
    # Load Embedded Question Pools from a local JSON file
    try:
        with open("questions_data_2.json", "r", encoding="utf-8") as f:
            raw_data = json.load(f)
            
            # --- BLOCK CONTROLLER ---
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
        st.error("Error: 'questions_data_2.json' not found in the project directory. Please ensure the file exists.")
        st.stop()
    
    # Randomize the order of the blocks for this specific participant
    st.session_state.block_order = random.sample(list(st.session_state.question_pools.keys()), len(st.session_state.question_pools))
    
    st.session_state.active_pipeline = None
    st.session_state.active_questions = [] 
    
    # UPDATED: Store evaluations as lists of dictionaries per block
    st.session_state.responses = {
        "participant_id": st.session_state.participant_id,
        "global_participant_sequence": st.session_state.participant_index,
        "consent_given": False,
        "demographics": {},
        "block_presentation_order": st.session_state.block_order,
        # Initialize an empty list for each block to hold the interaction dictionaries
        "block_evaluations": {
            block_name: [] for block_name in st.session_state.block_order
        }
    }

# --- 3. HELPER FUNCTIONS TO MANAGE TRANSITIONS ---
def accept_consent():
    st.session_state.responses["consent_given"] = True
    st.session_state.current_page = "demographics"

def start_experiment():
    st.session_state.responses["demographics"] = {
        "age_group": st.session_state.age_group_input,
        "gender": st.session_state.gender_input,
        "highest_education": st.session_state.education_level_input,
        "university": st.session_state.university_input,
        "english_proficiency": st.session_state.english_proficiency_input,
        "german_proficiency": st.session_state.german_proficiency_input,
        "chatbot_usage_frequency": st.session_state.chatbot_frequency_input
    }
    st.session_state.current_page = "instructions"

def go_to_role_reminder():
    st.session_state.current_page = "role_reminder"

def initialize_next_block():
    current_block_name = st.session_state.block_order[st.session_state.current_run - 1]
    st.session_state.active_pipeline = current_block_name
    
    pool = st.session_state.question_pools[current_block_name]
    pool_size = len(pool) # Should be 50
    
    # --- NEW OFFSET LOGIC ---
    questions_per_block = 3
    total_active_blocks = len(st.session_state.block_order)
    questions_per_participant = total_active_blocks * questions_per_block
    
    # Base offset for the whole participant
    participant_base_offset = (st.session_state.participant_index * questions_per_participant) % pool_size
    
    # Specific offset for the current block
    run_offset = (st.session_state.current_run - 1) * questions_per_block
    
    # Collect exactly 3 questions
    active_qs = []
    for i in range(questions_per_block):
        target_index = (participant_base_offset + run_offset + i) % pool_size
        active_qs.append(pool[target_index])
    
    st.session_state.active_questions = active_qs
    st.session_state.current_q_index = 0
    st.session_state.current_page = "question_eval"

# UPDATED: Construct and append a dictionary for each question rated
def next_question(faith_score, rel_score, recall_score, prec_score):
    q_item = st.session_state.active_questions[st.session_state.current_q_index]
    block_name = st.session_state.active_pipeline
    
    # Attempt to fetch a question_id, default to the index if it doesn't exist in the JSON
    q_id = q_item.get("question_id", st.session_state.current_q_index)
    
    # Build the dictionary exactly as requested
    interaction_record = {
        "block_sequence_position": st.session_state.current_run,
        "assigned_pipeline": block_name,
        "question_id": q_id,
        "scores": {
            "faithfulness": faith_score,
            "answer_relevancy": rel_score,
            "contextual_recall": recall_score,
            "contextual_precision": prec_score
        }
    }
    
    # Append to the list for this specific pipeline
    if block_name in st.session_state.responses["block_evaluations"]:
        st.session_state.responses["block_evaluations"][block_name].append(interaction_record)
    
    if st.session_state.current_q_index < len(st.session_state.active_questions) - 1:
        st.session_state.current_q_index += 1
    else:
        st.session_state.current_page = "pipeline_survey"

# UPDATED: Format the survey dictionary as requested
def submit_pipeline_survey(survey_scores):
    survey_data = {
        "block_sequence_position": st.session_state.current_run,
        "assigned_pipeline": st.session_state.active_pipeline,
        "survey_responses": survey_scores
    }
    
    if "block_surveys" not in st.session_state.responses:
        st.session_state.responses["block_surveys"] = {}
        
    st.session_state.responses["block_surveys"][st.session_state.active_pipeline] = survey_data
    
    if st.session_state.current_run < len(st.session_state.block_order):
        st.session_state.current_run += 1
        initialize_next_block()
    else:
        save_responses_to_server()
        st.session_state.current_page = "final"

# UPDATED: Save JSON formatted strings mapping directly to the requested columns
def save_responses_to_server():
    """Pushes the aggregated experiment data into the Google Sheet with one row per participant."""
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # 1. Fetch existing data (ttl=0 ensures we get the latest state and don't overwrite)
    existing_data = conn.read(worksheet="ExperimentData", ttl=0)
    
    chatbot_types = [
        "Semantic_Low_Explainable",
        "Semantic_High_Explainable",
        "Graph_Low_Explainable",
        "Graph_High_Explainable"
    ]
    
    row_data = {
        "participant_id": st.session_state.responses["participant_id"],
        "global_participant_sequence": st.session_state.responses["global_participant_sequence"],
        "demographics": json.dumps(st.session_state.responses["demographics"], ensure_ascii=False),
        "block_presentation_order": json.dumps(st.session_state.responses["block_presentation_order"], ensure_ascii=False),
        "consent_given": st.session_state.responses["consent_given"]
    }
    
    # 2. Iterate through each chatbot type and populate the respective single question and survey columns
    for chatbot in chatbot_types:
        # Extract and dump the list of single question interactions to JSON
        if chatbot in st.session_state.responses["block_evaluations"]:
            eval_list = st.session_state.responses["block_evaluations"][chatbot]
            row_data[f"single_question_rating_{chatbot}"] = json.dumps(eval_list, ensure_ascii=False) if eval_list else "[]"
        else:
            row_data[f"single_question_rating_{chatbot}"] = "[]"
            
        # Extract and dump the survey data to JSON
        if "block_surveys" in st.session_state.responses and chatbot in st.session_state.responses["block_surveys"]:
            survey_dict = st.session_state.responses["block_surveys"][chatbot]
            row_data[f"block_survey_{chatbot}"] = json.dumps(survey_dict, ensure_ascii=False)
        else:
            row_data[f"block_survey_{chatbot}"] = "{}"
    
    # 3. Transform to DataFrame
    new_data_row = pd.DataFrame([row_data])
    
    # 4. Concatenate and update connection object
    updated_df = pd.concat([existing_data, new_data_row], ignore_index=True) if existing_data is not None else new_data_row
    conn.update(worksheet="ExperimentData", data=updated_df)

def save_email_to_server(email_address):
    """Pushes the VP-Stunden email into a separate Google Sheet for anonymity."""
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # 1. Fetch existing data
    existing_data = conn.read(worksheet="Emails", ttl=0)
    
    # Check to prevent duplicates if data exists
    if existing_data is not None and "email_address" in existing_data.columns and email_address in existing_data["email_address"].values:
        return
        
    # 2. Transform to DataFrame
    new_df = pd.DataFrame([{"email_address": email_address}])
    
    # 3. Concatenate and update connection object
    updated_df = pd.concat([existing_data, new_df], ignore_index=True) if existing_data is not None else new_df
    conn.update(worksheet="Emails", data=updated_df)

# --- 4. PAGE ROUTING & RENDERING ---
st.title("🤖 UniCompanion")

# Force scroll to top on every page render
scroll_to_top()

# Added 'role_reminder' to the mapping
progress_mapping = {"consent": 0.0, "demographics": 0.1, "instructions": 0.2, "role_reminder": 0.3, "question_eval": 0.4, "pipeline_survey": 0.8, "final": 1.0}
base_progress = progress_mapping.get(st.session_state.current_page, 0.0)
adjusted_progress = base_progress if base_progress in [0.0, 0.1, 0.2, 0.3, 1.0] else base_progress + ((st.session_state.current_run - 1) * 0.15)
st.progress(min(adjusted_progress, 1.0))

col_meta1, col_meta2 = st.columns([1, 1])
with col_meta1:
    st.caption(f"🆔 **Participant:** ID-{st.session_state.participant_id}")
with col_meta2:
    if st.session_state.current_page not in ["consent", "demographics", "instructions", "role_reminder", "final"]:
        st.caption(f"🧱 **Progress:** Block {st.session_state.current_run} / {len(st.session_state.block_order)}")

st.markdown("---")

# PAGE: CONSENT FORM
if st.session_state.current_page == "consent":
    st.subheader("📄 Consent Form")
    with st.container(border=True):
        st.markdown("### Purpose of the Study")
        st.write("The purpose of this study is to evaluate and compare different types of Retrieval-Augmented Generation (RAG) chatbot systems designed to assist students with administrative and study regulation queries.")
        st.markdown("### Procedure")
        st.write("You will be asked to review question-and-response pairs generated by four different chatbots. For each chatbot, you will evaluate a series of interactions based on specific quality metrics. After completing each chatbot's evaluation block, you will fill out a short survey regarding your perception of the agent's trustworthiness and transparency.\n\nThe entire study is conducted online, must be completed on a computer or laptop (mobile devices are not suitable), and is estimated to take approximately 15–20 minutes.")
        st.markdown("### Possible Risks and Discomforts")
        st.write("There are no physical or psychological risks associated with this study. The tasks involve reading text and completing standard questionnaires. You may experience mild cognitive fatigue due to the evaluative nature of the task. Participation is entirely **voluntary**, and you are free to withdraw from the experiment at any time without giving a reason and without any penalty. In case of incomplete participation, the collected data will not be recorded.")
        st.markdown("### Possible Benefits")
        st.write("This study may not provide direct personal benefits. However, the findings will contribute to research on Human-Computer Interaction (HCI), Explainable AI (XAI), and the development of more reliable, transparent conversational agents for educational institutions. Additionally, students who are studying cognitive science and psychology can receive 0.5 VP hours to compensate for their participation.")
        st.markdown("### Privacy and Data Protection")
        st.write("All data collected during this experiment including your evaluation ratings, survey responses, and basic demographic questions will be recorded anonymously. No personal identifying information will be collected. The anonymized data will be stored securely on Google infrastructure (which includes servers located in the US) and will be accessed exclusively by the authorized research team for academic purposes.")
        st.write("If you have any questions, concerns, or complaints about this study, please contact:\n\n**Researcher:** mamini@uni-osnabrueck.de")
        st.markdown("---")
        st.markdown("#### Declaration of Consent")
        st.markdown("By clicking the **'I Agree and Start'** button below, you declare that:\n* You have read and understood the information above.\n* You are at least 18 years of age.\n* You are currently registered at a higher education institution.\n* You have a level of English proficiency sufficient to complete the tasks.\n")
        st.markdown("<br>", unsafe_allow_html=True)
        st.button("I Agree and Start", on_click=accept_consent, use_container_width=True)

# PAGE: DEMOGRAPHICS
elif st.session_state.current_page == "demographics":
    st.subheader("📋 Demographic Information")
    st.write("Please provide your background details to start the evaluation pipeline.")
    
    with st.form("demographics_form", border=True):
        st.session_state.age_group_input = st.selectbox("What is your age group? *", options=["18-24", "25-34", "35 and above"], index=None, placeholder="Select your age group")
        st.session_state.gender_input = st.selectbox("What is your gender? *", options=["Female", "Male", "Other", "Prefer not to say"], index=None, placeholder="Select gender")
        st.session_state.education_level_input = st.selectbox("What is your current academic status? *", options=["Bachelor's student of Cognitive Science / Psychology", "Master's student of Cognitive Science / Psychology", "PhD student of Cognitive Science / Psychology", "Student (Other discipline or university)", "Non-student (With prior university experience/graduated)", "Non-student (No prior university experience)"], index=None, placeholder="Select academic status")
        st.session_state.university_input = st.selectbox("Which university do you currently attend? *", options=["Osnabrück University", "Other", "Not Applicable (Not a student)"], index=None, placeholder="Select your university")
        lang_levels = ["Beginner", "Intermediate", "Advanced", "Native"]
        st.session_state.english_proficiency_input = st.selectbox("How would you rate your English proficiency? *", options=lang_levels, index=None, placeholder="Select English level")
        st.session_state.german_proficiency_input = st.selectbox("How would you rate your German proficiency? *", options=lang_levels, index=None, placeholder="Select German level")
        st.session_state.chatbot_frequency_input = st.selectbox("How often do you use AI or chatbot tools? *", options=["Never", "Rarely / Less than once a week", "Around once a week", "Multiple times a week", "Daily"], index=None, placeholder="Select your usage frequency")
        
        st.markdown("<br>", unsafe_allow_html=True)
        submit_demographics = st.form_submit_button("Continue to Instructions →", use_container_width=True)
        
        if submit_demographics:
            if not all([st.session_state.age_group_input, st.session_state.gender_input, st.session_state.education_level_input, st.session_state.english_proficiency_input, st.session_state.german_proficiency_input, st.session_state.chatbot_frequency_input]):
                st.error("Please fill in all options marked with * before proceeding.")
            else:
                start_experiment()
                st.rerun()

# PAGE: STUDY INSTRUCTIONS
elif st.session_state.current_page == "instructions":
    st.subheader("📖 Experiment Instructions")
    st.write("Welcome! Thank you for participating in our study. Please read the following guidelines carefully before starting the evaluation.")
    
    with st.container(border=True):
        st.markdown("### Your Task")
        st.write(f"You will evaluate {len(st.session_state.block_order)} different chatbots sequentially. Each chatbot represents a different approach designed to answer student queries about Cognitive Science administration and study regulations at Osnabrück University.\n\nFor each chatbot, the evaluation is split into two phases:")
        st.markdown("#### Phase 1: System Evaluation")
        st.write("You will be presented with a series of interactions. For each interaction, you will see:\n* **The Student's Question:** The query submitted to the chatbot.\n* **The Ground Truth Response:** The verified, correct administrative answer.\n* **The Context:** The source documentation/regulations retrieved by the system.\n* **The Agent Output:** The response generated by the chatbot based on the context.\n\nFor each interaction, you must evaluate the chatbot's output using the provided sliding scales/metrics.\n\n💡 *Tip: If you are unsure about the definition of any evaluation metric, hover over or click the help sign [?] located next to the metric name for a detailed explanation.*")
        st.markdown("#### Phase 2: Post-Block Survey")
        st.write("After you finish evaluating the set of questions for a specific chatbot, you will complete a brief survey. In this survey, you will rate how trustworthy and transparent you found that specific conversational agent based on your experience.")
        st.markdown("### Important Rules for Participation")
        st.write("* **Do not refresh or close the browser tab** during the experiment, as your progress will be lost.\n* Please complete the study in a quiet environment where you can focus.\n* Please evaluate the responses objectively based on the provided context and ground truth, rather than personal assumptions about university rules.")
        
        st.markdown("<br>", unsafe_allow_html=True)
        # Changed button to route to the new role_reminder page
        st.button("Proceed to Scenario →", on_click=go_to_role_reminder, use_container_width=True)

# PAGE: ROLE REMINDER (NEW)
elif st.session_state.current_page == "role_reminder":
    st.subheader("🎯 Scenario & Role")
    
    with st.container(border=True):
        st.markdown("""
Imagine you are working for the **Examination Office** at Osnabrück University. The university is testing *UniCompanion*, a new AI assistant designed to answer student queries about study regulations. 

Your critical task is to evaluate **4 different versions** of the AI chatbot and assess their responses for accuracy against official university regulations before the system is released to the student body.

<br>
<div style="text-align: center;">
    <h4><strong>Please pay close attention to the details and evaluate each output carefully.</strong></h4>
</div>
""", unsafe_allow_html=True)
        
    st.markdown("<br>", unsafe_allow_html=True)
    st.button(f"Begin Block {st.session_state.current_run}", on_click=initialize_next_block, use_container_width=True)

# PAGE: QUESTION EVALUATION LOOP
elif st.session_state.get('current_page') == "question_eval":
    st.markdown("""
        <style>
        .appview-container .main .block-container { max-width: 95% !important; padding-left: 2rem !important; padding-right: 2rem !important; }
        div[data-testid="stMarkdownContainer"] pre code { white-space: pre-wrap !important; word-break: break-word !important; }
        </style>
    """, unsafe_allow_html=True)

    q_idx = st.session_state.current_q_index
    q_item = st.session_state.active_questions[q_idx]
    active_pipeline = st.session_state.active_pipeline
    
    # --- DYNAMIC ANSWER SELECTION BASED ON JSON KEYS ---
    student_question = q_item.get("question", "Question missing")
    context_text = q_item.get("context_original", "Context missing")
    
    # Extract translation safely
    context_translation = q_item.get("context_translation", None)
    has_translation = isinstance(context_translation, str) and context_translation.strip() != ""
    
    if active_pipeline == "Semantic_Low_Explainable":
        chatbot_response = q_item.get("chatbot_low_explainable_response", q_item.get("low_explainable_response", "Answer missing."))
        ground_truth = q_item.get("ground_truth_low_explainable_answer", "Ground truth missing.")
    elif active_pipeline == "Semantic_High_Explainable":
        chatbot_response = q_item.get("chatbot_high_explainable_response", "Answer missing.")
        ground_truth = q_item.get("ground_truth_high_explainable_answer", "Ground truth missing.")
    elif active_pipeline == "Graph_Low_Explainable":
        chatbot_response = q_item.get("chatbot_low_explainable_response", "Answer missing.")
        ground_truth = q_item.get("ground_truth_low_explainable_answer", "Ground truth missing.")
    elif active_pipeline == "Graph_High_Explainable":
        chatbot_response = q_item.get("chatbot_high_explainable_response", "Answer missing.")
        ground_truth = q_item.get("ground_truth_high_explainable_answer", "Ground truth missing.")
    else:
        chatbot_response = "Unknown pipeline."
        ground_truth = "Unknown pipeline."

    
    # --- UPDATED: Chatbot Tracker Logic (Formatted inline as requested) ---
    ordinal_map = {1: "First", 2: "Second", 3: "Third", 4: "Fourth"}
    bot_ordinal = ordinal_map.get(st.session_state.current_run, f"{st.session_state.current_run}th")
    
    st.subheader(f"🔍 System Evaluation  |  {bot_ordinal} Chatbot  |  Question {q_idx + 1} of {len(st.session_state.active_questions)}")
    
    st.markdown(
        "Please evaluate the chatbot's performance using the sliding scales below.\n\n"
        "##### **Note: The chatbot generates its response based on the retrieved context.**"
    )
    st.markdown("---")
    
    # ==========================
    # --- RESTRUCTURED LAYOUT ---
    # ==========================
    
    # ROW 1: Student Question (Full width)
    with st.container(border=True):
        st.markdown("##### ❓ Student Question")
        st.info(student_question)
        
    st.markdown("<br>", unsafe_allow_html=True)
    
    # ROW 2: Retrieved Context (Left) and Chatbot Response (Right)
    col_context, col_response = st.columns([1, 1], gap="medium")
    
    with col_context:
        with st.container(border=True):
            st.markdown("##### 📄 Retrieved Context Sources")
            # Display translation alongside original if it exists
            if has_translation:
                st.markdown("**Original (German):**")
                st.markdown(f"```text\n{context_text}\n```")
                st.markdown("**English Translation:**")
                st.markdown(f"```text\n{context_translation}\n```")
            else:
                st.markdown(f"```text\n{context_text}\n```")
                
    with col_response:
        with st.container(border=True):
            st.markdown(f"##### 🤖 Chatbot Response")
            st.write(chatbot_response)
            
    st.markdown("<br>", unsafe_allow_html=True)
    
    # ROW 3: Ground Truth (Full width)
    with st.container(border=True):
        st.markdown("##### 🎯 Ground Truth (Expected Output)")
        st.success(ground_truth)
    
    # ==========================
    
    st.markdown("---")
    
    st.markdown("### 📊 Performance Assessment")
    st.write("Please adjust the sliders below (**0 = Complete Failure**, **100 = Perfect Alignment**):")

    st.warning("💡 **Important:** Click the **[?]** next to each metric to see what to compare before assigning your score.")

    s_faith = st.slider("Rate Faithfulness (Factuality / Truthfulness):", min_value=0, max_value=100, value=50, step=1, key=f"faith_q_{q_idx}_r_{st.session_state.current_run}", help="👉 COMPARE: Chatbot Response vs. Retrieved Context\n\n100 = Every claim made in the Chatbot Response can be directly inferred from the Retrieved Context.")
    s_relevancy = st.slider("Rate Answer Relevancy:", min_value=0, max_value=100, value=50, step=1, key=f"rel_q_{q_idx}_r_{st.session_state.current_run}", help="👉 COMPARE: Chatbot Response vs. Student Question\n\n100 = Every statement in the Chatbot Response directly answers the Student Question without any unrelated text.")
    s_recall = st.slider("Rate Contextual Recall:", min_value=0, max_value=100, value=50, step=1, key=f"rec_q_{q_idx}_r_{st.session_state.current_run}", help="👉 COMPARE: Retrieved Context vs. Ground Truth (Expected Output)\n\n100 = The Retrieved Context successfully verifies every factual statement in the Ground Truth.")
    s_precision = st.slider("Rate Contextual Precision:", min_value=0, max_value=100, value=50, step=1, key=f"prec_q_{q_idx}_r_{st.session_state.current_run}", help="👉 COMPARE: Retrieved Context vs. Student Question\n\n100 = The Retrieved Context is highly relevant and perfectly aligns with the Question asked.")
    
    st.markdown("<br>", unsafe_allow_html=True)
    st.button("Next Phase →", on_click=next_question, args=(s_faith, s_relevancy, s_recall, s_precision), use_container_width=True)

# PAGE: BLOCK PIPELINE SURVEY
elif st.session_state.current_page == "pipeline_survey":
    st.subheader(f"📝 End of Block {st.session_state.current_run} Review")
    st.write("Please indicate your level of agreement with the descriptions regarding the system you just evaluated:")
    st.markdown("---")
    
    st.markdown("""
        <style>
        .survey-row-even { background-color: #f7f7f7; padding: 15px; border-radius: 4px; margin-bottom: 5px; }
        .survey-row-odd { background-color: #ffffff; padding: 15px; border-radius: 4px; margin-bottom: 5px; }
        div[data-testid="stHorizontalBlock"] { align-items: center !important; }
        </style>
    """, unsafe_allow_html=True)
    
    items = [
        {"text": "I trust the chatbot's responses.", "key": "trust_responses"},
        {"text": "The chatbot's response seemed reliable.", "key": "responses_reliable"},
        {"text": "I felt confident making a decision based on the chatbot's response.", "key": "confident_decision"},
        {"text": "I would use this chatbot to make a similar academic or study-related decision.", "key": "use_future_decisions"},
        {"text": "The explanation helped me understand the answer provided.", "key": "helped_understanding"},
        {"text": "The explanation made me trust the chatbot more.", "key": "explanation_increased_trust"},
        {"text": "I prefer getting a contextual explanation over just a direct quote from the study regulations.", "key": "prefer_contextual"}
    ]
    
    likert_options = ["Strongly Disagree", "Disagree", "Neutral", "Agree", "Strongly Agree"]
    current_survey_answers = {}
    
    for idx, item in enumerate(items):
        st.markdown(f"**Item {idx+1}:** {item['text']}")
        # Ensure the keys are collected as 'item1', 'item2' based on loop index to exactly match your requested dictionary format
        dict_key = f"item{idx+1}"
        choice = st.radio(label=f"label_{item['key']}", options=likert_options, index=2, key=f"grid_radio_{item['key']}_run_{st.session_state.current_run}", horizontal=True, label_visibility="collapsed")
        current_survey_answers[dict_key] = likert_options.index(choice) + 1
        st.markdown("<hr style='margin: 8px 0px; border-top: 1px dashed #ccc;'>", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.button("Submit Survey & Proceed to Final Step →", on_click=submit_pipeline_survey, args=(current_survey_answers,), use_container_width=True)

# PAGE: FINAL SUBMISSION / DEBRIEFING
elif st.session_state.current_page == "final":
    
    if "study_completed" not in st.session_state:
        st.session_state.study_completed = False

    # TERMINAL STATE: Safe to close
    if st.session_state.study_completed:
        st.balloons()
        st.markdown("<br><br>", unsafe_allow_html=True)
        st.success("✅ **All data saved successfully.**")
        st.markdown(
            """
            <div style='text-align: center; padding: 20px;'>
                <h2>Experiment Complete</h2>
                <p>Thank you for contributing to this HCI research!</p>
                <p><strong>You may now safely close this browser tab/window.</strong></p>
            </div>
            """, 
            unsafe_allow_html=True
        )
        
    # DEBRIEFING & VP-STUNDEN FORM
    else:
        st.success("🎉 Evaluation Session Completed Successfully!")
        
        # --- NEW DEBRIEFING SECTION ---
        with st.container(border=True):
            st.subheader("ℹ️ Study Debriefing")
            st.write("Thank you for taking part in this study.")
            st.write("The purpose of this experiment was to examine how varying levels of explainability and different background architectures influence a user's perception of transparency and trustworthiness in educational AI assistants.")
            st.write("By evaluating these distinct system behaviors, your responses will directly contribute to designing more reliable and comprehensible digital tools for university environments.")
            st.write("Your responses remain strictly anonymous and will be used solely for research purposes. If you have any questions regarding the study or your data, you may contact the primary researcher at **mamini@uni-osnabrueck.de**.")
        # ------------------------------
        
        st.markdown("---")
        st.subheader("📋 Experimental Course Credits (VP-Stunden)")
        st.write("If you require **0.5 VP hours** for your participation, please submit your university email address below.")
        st.info("🛡️ **Data Privacy Protection Notice:** To ensure absolute anonymity, your email address is logged completely independently into a separate, unlinked server storage file. There is no cryptographic reference, participant ID, or one-to-one mapping connecting your identity back to the experimental evaluation values you assigned.")
        
        with st.form("vp_email_form", border=True):
            email_input = st.text_input("Enter your university email address:", placeholder="username@uni-osnabrueck.de")
            
            col1, col2 = st.columns(2)
            with col1:
                submit_email = st.form_submit_button("Submit Email for Credits", use_container_width=True)
            with col2:
                skip_email = st.form_submit_button("I don't need credits (Finish Study)", use_container_width=True)
            
            if submit_email:
                if email_input.strip() == "" or "@" not in email_input:
                    st.error("Please enter a valid university email address.")
                else:
                    save_email_to_server(email_input.strip())
                    st.session_state.study_completed = True
                    st.rerun()
                    
            if skip_email:
                st.session_state.study_completed = True
                st.rerun()





