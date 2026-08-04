import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# --- STRICT SESSION GUARD ---
# Check if the question list is missing or empty
if "active_questions" not in st.session_state or len(st.session_state.active_questions) == 0:
    st.switch_page("pages/1_consent.py")

# 2. Add the visual title to the actual page
st.title("🤖 UniCompanion")

st.progress(1.0)
col_meta1, col_meta2 = st.columns([1, 1])
with col_meta1:
    st.caption(f"🆔 **Participant:** ID-{st.session_state.participant_id}")
st.markdown("---")

def save_email_to_server(email_address):
    conn = st.connection("gsheets", type=GSheetsConnection)
    existing_data = conn.read(worksheet="Emails", ttl=0)
    
    if existing_data is not None and "email_address" in existing_data.columns and email_address in existing_data["email_address"].values:
        return
        
    new_df = pd.DataFrame([{"email_address": email_address}])
    updated_df = pd.concat([existing_data, new_df], ignore_index=True) if existing_data is not None else new_df
    conn.update(worksheet="Emails", data=updated_df)

if "study_completed" not in st.session_state:
    st.session_state.study_completed = False

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
else:
    st.success("🎉 Evaluation Session Completed Successfully!")
    
    with st.container(border=True):
        st.subheader("ℹ️ Study Debriefing")
        st.write("Thank you for taking part in this study.")
        st.write("The purpose of this experiment was to examine how varying levels of explainability and different background architectures influence a user's perception of transparency and trustworthiness in educational AI assistants.")
        st.write("By evaluating these distinct system behaviors, your responses will directly contribute to designing more reliable and comprehensible digital tools for university environments.")
        st.write("Your responses remain strictly anonymous and will be used solely for research purposes. If you have any questions regarding the study or your data, you may contact the primary researcher at **mamini@uni-osnabrueck.de**.")
        
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