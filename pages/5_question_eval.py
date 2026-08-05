

import streamlit as st
import time

# --- STRICT SESSION GUARD ---
# Check if the question list is missing or empty
if "active_questions" not in st.session_state or len(st.session_state.active_questions) == 0:
    st.switch_page("pages/1_consent.py")

# 2. Add the visual title to the actual page
st.title("🤖 UniCompanion")

# Inject modern, native HTML/JS with a 150ms delay
# This forces our scroll to execute AFTER Streamlit's internal engine finishes restoring state
st.html(f"""
    <div style="display:none">{time.time()}</div>
    <script>
        setTimeout(function() {{
            // Look for the scroll container in both the parent and current window
            const doc = window.parent ? window.parent.document : document;
            const container = doc.querySelector('[data-testid="stAppViewContainer"]') || doc.querySelector('.main');
            
            if (container) {{
                container.scrollTo({{ top: 0, behavior: 'smooth' }});
            }}
            // Fallback for native window scrolling
            window.scrollTo({{ top: 0, behavior: 'smooth' }});
        }}, 150);
    </script>
""")

# Dynamic progress calculation based on the current block
adjusted_progress = 0.4 + ((st.session_state.current_run - 1) * 0.15)
st.progress(min(adjusted_progress, 1.0))

col_meta1, col_meta2 = st.columns([1, 1])
with col_meta1:
    st.caption(f"🆔 **Participant:** ID-{st.session_state.participant_id}")
with col_meta2:
    st.caption(f"🧱 **Progress:** Block {st.session_state.current_run} / {len(st.session_state.block_order)}")

def next_question(faith_score, rel_score, recall_score, prec_score):
    q_item = st.session_state.active_questions[st.session_state.current_q_index]
    block_name = st.session_state.active_pipeline
    q_id = q_item.get("question_id", st.session_state.current_q_index)
    
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
    
    if block_name in st.session_state.responses["block_evaluations"]:
        st.session_state.responses["block_evaluations"][block_name].append(interaction_record)
    
    # Route to the bounce page to trigger a native scroll-to-top, OR move to survey
    if st.session_state.current_q_index < len(st.session_state.active_questions) - 1:
        st.session_state.current_q_index += 1
        st.switch_page("pages/5b_bounce.py")  # <--- USE THE NATIVE ROUTER HERE
    else:
        st.switch_page("pages/6_pipeline_survey.py")

st.markdown("""
    <style>
    .appview-container .main .block-container { max-width: 95% !important; padding-left: 2rem !important; padding-right: 2rem !important; }
    div[data-testid="stMarkdownContainer"] pre code { white-space: pre-wrap !important; word-break: break-word !important; }
    </style>
""", unsafe_allow_html=True)

q_idx = st.session_state.current_q_index
q_item = st.session_state.active_questions[q_idx]
active_pipeline = st.session_state.active_pipeline

student_question = q_item.get("question", "Question missing")
context_text = q_item.get("context_original", "Context missing")
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

ordinal_map = {1: "First", 2: "Second", 3: "Third", 4: "Fourth"}
bot_ordinal = ordinal_map.get(st.session_state.current_run, f"{st.session_state.current_run}th")

st.subheader(f"🔍 {bot_ordinal} Chatbot Evaluation | Question {q_idx + 1} of {len(st.session_state.active_questions)}")

# Display the image using the relative path to the assets folder
st.markdown("---")

col1, col2, col3 = st.columns([1, 2, 1])

with col2:
    st.markdown("<h5 style='text-align: center;'><b>The chatbot first finds the context, then uses it to generate a response to the student's question.</b></h5>", unsafe_allow_html=True)
    st.image("assets/rag_flow.png", width=500)
    st.markdown("<p style='text-align: center; color: gray;'><small>Generated by Google Gemini</small></p>", unsafe_allow_html=True)

st.markdown("---")
st.markdown("### 📊 Performance Assessment")
st.write("Please review the Student Question and the three Reference Panels below, then select the most appropriate option for each of the following evaluation questions.")

# --- ADDED EXPLANATION HERE ---
st.warning("💡 **Note:** Sometimes the chatbot may retrieve incorrect *Context*, which can cause it to differ from the *Expected Response*. If you notice this, please evaluate the chatbot's responses objectively based **only on current information**. Please do not use assumptions about university rules.")

st.markdown("<br>", unsafe_allow_html=True)

# Question 1
st.markdown("###### To what extent does the `Chatbot Response` align with the content of `Context`?")
s_faith = st.selectbox("faith_label", options=["100%", "75%", "50%", "25%", "0%", "I do not know"], index=None, placeholder="Select an option...", label_visibility="collapsed", key=f"faith_q_{q_idx}_r_{st.session_state.current_run}")

# Question 2
st.markdown("###### To what extent is the `Chatbot Response` relevant to the `Student Question`?")
s_relevancy = st.selectbox("rel_label", options=["100%", "75%", "50%", "25%", "0%", "I do not know"], index=None, placeholder="Select an option...", label_visibility="collapsed", key=f"rel_q_{q_idx}_r_{st.session_state.current_run}")

# Question 3
st.markdown("###### To what extent does the `Context` align with the `Expected Response`?")
s_recall = st.selectbox("rec_label", options=["100%", "75%", "50%", "25%", "0%", "I do not know"], index=None, placeholder="Select an option...", label_visibility="collapsed", key=f"rec_q_{q_idx}_r_{st.session_state.current_run}")

# Question 4
st.markdown("###### To what extent is the `Context` relevant to the `Student Question`?")
s_precision = st.selectbox("prec_label", options=["100%", "75%", "50%", "25%", "0%", "I do not know"], index=None, placeholder="Select an option...", label_visibility="collapsed", key=f"prec_q_{q_idx}_r_{st.session_state.current_run}")


st.markdown("<br>", unsafe_allow_html=True)

st.markdown("---")

with st.container(border=True):
    st.markdown("##### ❓ Student Question")
    st.info(student_question)
    
st.markdown("<br>", unsafe_allow_html=True)
col_context, col_response = st.columns([1, 1], gap="medium")

with col_context:
    with st.container(border=True):
        st.markdown("##### 📄 Context")
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
with st.container(border=True):
    st.markdown("##### 🎯 Expected Response")
    st.success(ground_truth)

# --- DYNAMIC BUTTON TEXT LOGIC ---
# Check if this is the final question in the block
is_last_question = st.session_state.current_q_index >= len(st.session_state.active_questions) - 1

if is_last_question:
    button_text = "Proceed to Post-Block Survey →"
else:
    button_text = "Next Question →"

# Check if all four evaluation questions have a selected value
all_answered = (
    s_faith is not None and 
    s_relevancy is not None and 
    s_recall is not None and 
    s_precision is not None
)

# Show a warning if the user hasn't finished evaluating
if not all_answered:
    st.warning("⚠️ Please select an option for all evaluation questions to proceed.")

# The button is disabled if 'all_answered' is False
if st.button(button_text, use_container_width=True, disabled=not all_answered):
    # Pass the selectbox values directly into the function
    next_question(s_faith, s_relevancy, s_recall, s_precision)















