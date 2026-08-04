import streamlit as st


# --- BASIC SESSION GUARD ---
# Check if they passed the consent page
if "responses" not in st.session_state or "consent_given" not in st.session_state.responses:
    st.switch_page("pages/1_consent.py")

# 2. Add the visual title to the actual page
st.title("🤖 UniCompanion")


st.progress(0.1)
col_meta1, col_meta2 = st.columns([1, 1])
with col_meta1:
    st.caption(f"🆔 **Participant:** ID-{st.session_state.participant_id}")
st.markdown("---")

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
    st.switch_page("pages/3_instructions.py")

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
    st.session_state.info_seeking_habit = st.selectbox("How do you typically learn about university study regulations? *", options=["Searching the official university website", "Asking AI tools (e.g., ChatGPT, Claude)","Asking the Examination Office, academic advisors, or informed peers","Other"], index=None)


    st.markdown("<br>", unsafe_allow_html=True)
    submit_demographics = st.form_submit_button("Continue to Instructions →", use_container_width=True)
    
    if submit_demographics:
        if not all([st.session_state.age_group_input, st.session_state.gender_input, st.session_state.education_level_input, st.session_state.english_proficiency_input, st.session_state.german_proficiency_input, st.session_state.chatbot_frequency_input]):
            st.error("Please fill in all options marked with * before proceeding.")
        else:
            start_experiment()