import streamlit as st

# --- BASIC SESSION GUARD ---
# Check if they passed the consent page
if "responses" not in st.session_state or "consent_given" not in st.session_state.responses:
    st.switch_page("pages/1_consent.py")

# 2. Add the visual title to the actual page
st.title("🤖 UniCompanion")


st.progress(0.3)
col_meta1, col_meta2 = st.columns([1, 1])
with col_meta1:
    st.caption(f"🆔 **Participant:** ID-{st.session_state.participant_id}")
st.markdown("---")

def initialize_next_block():
    current_block_name = st.session_state.block_order[st.session_state.current_run - 1]
    st.session_state.active_pipeline = current_block_name
    
    pool = st.session_state.question_pools[current_block_name]
    pool_size = len(pool) 
    
    questions_per_block = 3
    total_active_blocks = len(st.session_state.block_order)
    questions_per_participant = total_active_blocks * questions_per_block
    
    participant_base_offset = (st.session_state.participant_index * questions_per_participant) % pool_size
    run_offset = (st.session_state.current_run - 1) * questions_per_block
    
    active_qs = []
    for i in range(questions_per_block):
        target_index = (participant_base_offset + run_offset + i) % pool_size
        active_qs.append(pool[target_index])
    
    st.session_state.active_questions = active_qs
    st.session_state.current_q_index = 0
    st.switch_page("pages/5_question_eval.py")

st.subheader("🎯 Scenario & Role")
with st.container(border=True):
    st.markdown("""
Imagine you are an Osnabrück University student trying to figure out your study regulations. The **Examination Office** has built *UniCompanion*, a new AI chatbot, to help answer your questions. 

Your critical task is to evaluate **4 different versions** of the AI chatbot and assess their responses for accuracy against official university regulations before the system goes live.

<br>
<div style="text-align: center;">
    <h4><strong>Please pay close attention to the details and evaluate each output carefully.</strong></h4>
</div>
""", unsafe_allow_html=True)
    
st.markdown("<br>", unsafe_allow_html=True)
if st.button(f"Begin Block {st.session_state.current_run}", use_container_width=True):
    initialize_next_block()