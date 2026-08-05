import streamlit as st

# --- STRICT SESSION GUARD ---
# Check if the question list is missing or empty
if "active_questions" not in st.session_state or len(st.session_state.active_questions) == 0:
    st.switch_page("pages/1_consent.py")


# 2. Add the visual title to the actual page
st.title("🤖 UniCompanion")


# Immediately bounce back to the question page. 
# Because it's a new page load, Streamlit natively scrolls to the top.
st.switch_page("pages/5_question_eval.py")