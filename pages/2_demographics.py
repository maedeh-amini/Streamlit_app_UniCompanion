import streamlit as st


# --- BASIC SESSION GUARD ---
# Check if they passed the consent page
if "responses" not in st.session_state or "consent_given" not in st.session_state.responses:
    st.switch_page("pages/1_consent.py")

# Add the visual title to the actual page
st.title("🤖 UniCompanion")

st.progress(0.1)
col_meta1, col_meta2 = st.columns([1, 1])
with col_meta1:
    # Adding a quick check in case participant_id isn't set yet during testing
    if "participant_id" in st.session_state:
        st.caption(f"🆔 **Participant:** ID-{st.session_state.participant_id}")
st.markdown("---")

def start_experiment():
    st.session_state.responses["demographics"] = {
        "age": st.session_state.age_input,
        "gender": st.session_state.gender_input,
        "highest_education": st.session_state.education_level_input,
        "english_proficiency": st.session_state.english_proficiency_input,
        "german_proficiency": st.session_state.german_proficiency_input,
        "chatbot_usage_frequency": st.session_state.chatbot_frequency_input,
        "info_seeking_habit": st.session_state.info_seeking_habit
    }
    st.switch_page("pages/3_instructions.py")

st.subheader("📋 Demographic Information")
st.write("Please provide your background details to start the evaluation pipeline.")

with st.form("demographics_form", border=True):
    st.session_state.age_input = st.number_input("Age *", min_value=18, value=None, placeholder="Enter your age", step=1)
    st.session_state.gender_input = st.selectbox("What is your gender? *", options=["Female", "Male", "Other", "Prefer not to say"], index=None, placeholder="Select gender")
    st.session_state.education_level_input = st.selectbox("What is your current academic status? *", options=["Student (cognitive science at Osnabrück University)", "Student (Other discipline or university)", "Non-student (With prior university experience/graduated)", "Non-student (No prior university experience)"], index=None, placeholder="Select academic status")
    lang_levels = ["Beginner", "Intermediate", "Advanced", "Native"]
    st.session_state.english_proficiency_input = st.selectbox("How would you rate your English proficiency? *", options=lang_levels, index=None, placeholder="Select English level")
    st.session_state.german_proficiency_input = st.selectbox("How would you rate your German proficiency? *", options=lang_levels, index=None, placeholder="Select German level")
    st.session_state.chatbot_frequency_input = st.selectbox("How often do you use AI chatbot tools? *", options=["Never", "Rarely / Less than once a week", "Around once a week", "Multiple times a week", "Daily"], index=None, placeholder="Select your usage frequency")
    st.session_state.info_seeking_habit = st.selectbox("How do you typically learn about university study regulations? *", options=["Reviewing official university resources", "Asking AI tools (e.g., ChatGPT, Claude)","Asking the Examination Office, academic advisors, or informed peers","Other"], index=None)

    st.markdown("<br>", unsafe_allow_html=True)
    submit_demographics = st.form_submit_button("Continue to Instructions →", use_container_width=True)
    
    if submit_demographics:
    
        if not all([
            st.session_state.age_input, 
            st.session_state.gender_input, 
            st.session_state.education_level_input, 
            st.session_state.english_proficiency_input, 
            st.session_state.german_proficiency_input, 
            st.session_state.chatbot_frequency_input,
            st.session_state.info_seeking_habit
        ]):
            st.error("Please fill in all options marked with * before proceeding.")
        else:
            start_experiment()






