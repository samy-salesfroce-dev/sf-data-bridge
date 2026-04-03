import streamlit as st
import os, sys

from database.db_handler import init_db

# Page Configuration for Premium Feel
st.set_page_config(
    page_title="SF-Data-Bridge",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Premium Design
def load_css():
    st.markdown("""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
        
        html, body, [class*="css"] {
            font-family: 'Inter', sans-serif;
        }

        /* Gradient header */
        .premium-header {
            background: linear-gradient(90deg, #11998e 0%, #38ef7d 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            font-size: 3rem;
            font-weight: 700;
            padding-bottom: 20px;
        }

        /* Glassmorphism sidebar */
        [data-testid="stSidebar"] {
            background-color: rgba(240, 242, 246, 0.4);
            backdrop-filter: blur(10px);
        }

        /* Animated buttons */
        .stButton>button {
            transition: all 0.3s ease;
            border-radius: 8px;
            font-weight: 600;
        }
        .stButton>button:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        }
        </style>
    """, unsafe_allow_html=True)

def main():
    load_css()
    
    # ---------------------------------------------
    # APPLICATION LOGIN GATE
    # ---------------------------------------------
    if 'app_authenticated' not in st.session_state:
        st.session_state.app_authenticated = False
        
    if not st.session_state.app_authenticated:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.markdown('<div class="premium-header" style="text-align: center; margin-top: 100px;">SF-Data-Bridge ⚡</div>', unsafe_allow_html=True)
            st.markdown("### 🔒 Secure Admin Portal")
            
            with st.form("login_form"):
                password = st.text_input("Enter Application Password", type="password")
                if st.form_submit_button("Unlock Tools"):
                    if password == os.environ.get("APP_PASSWORD", "admin123"):
                        st.session_state.app_authenticated = True
                        st.rerun()
                    else:
                        st.error("Access Denied: Incorrect Password.")
        return # Block execution of the rest of the app

    # ---------------------------------------------
    # SECURE APPLICATION RENDERING
    # ---------------------------------------------
    init_db() # Ensure DB is initialized
    
    st.markdown('<div class="premium-header">SF-Data-Bridge ⚡</div>', unsafe_allow_html=True)
    st.markdown("### Professional Salesforce-to-Salesforce Migration Engine (Cloud Version)")
    
    # Initialize session states
    if 'current_project_id' not in st.session_state:
        st.session_state.current_project_id = None
    if 'source_sf' not in st.session_state:
        st.session_state.source_sf = None
    if 'target_sf' not in st.session_state:
        st.session_state.target_sf = None

    # Custom Navigation
    st.sidebar.title("Navigation")
    pages = ["Project Setup & Auth", "Metadata & Schema Diff", "Transformation & Mapping", "Execution & Audit"]
    
    selection = st.sidebar.radio("Go to phase:", pages)
    
    st.sidebar.markdown("---")
    if st.session_state.source_sf and st.session_state.target_sf:
        st.sidebar.success("✅ Orgs Authenticated")
    else:
        st.sidebar.error("❌ Orgs Not Authenticated")

    # Routing
    if selection == "Project Setup & Auth":
        from ui.pages.project_setup import render_page
        render_page()
    elif selection == "Metadata & Schema Diff":
        from ui.pages.metadata_diff import render_page
        render_page()
    elif selection == "Transformation & Mapping":
        from ui.pages.mapping_ui import render_page
        render_page()
    elif selection == "Execution & Audit":
        from ui.pages.execution import render_page
        render_page()

if __name__ == "__main__":
    main()
