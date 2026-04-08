import streamlit as st
import xml.etree.ElementTree as ET
import pandas as pd
from src.data import fetch_all_jobs, fetch_selected_jobs
import streamlit as st
import json
# @st.cache_resource
# def preload_system():
#     # preload backend
#     from src.backend import match_employees_production
#     from src.backend import generate_enterprise_explanation

#     # preload embedding model
#     from sentence_transformers import SentenceTransformer
#     SentenceTransformer("BAAI/bge-small-en-v1.5")

#     return True

# preload_system()

import threading

def warmup():
    from src.backend import match_employees_production
    from src.backend import generate_enterprise_explanation

    # preload embedding model
    from sentence_transformers import SentenceTransformer
    SentenceTransformer("BAAI/bge-small-en-v1.5")

threading.Thread(target=warmup).start()

st.set_page_config(page_title="Candidate Skills", layout="wide")

CONFIG_FILE = "/home/labuser/Desktop/Project/Instructions/MaaS/projects/Skillcloudtesttry/config.json"

def load_config():
    try:
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_config(data):
    with open(CONFIG_FILE, "w") as f:
        json.dump(data, f)

config = load_config()

if "ALL_JOB_URL" not in st.session_state:
    st.session_state.ALL_JOB_URL = config.get("ALL_JOB_URL")

if "SELECTED_URL" not in st.session_state:
    st.session_state.SELECTED_URL = config.get("SELECTED_URL")

if "username" not in st.session_state:
    st.session_state.username=config.get("username")

if "password" not in st.session_state:
    st.session_state.password = config.get("password")

# -------------------------
# CSS (FULL RESTORED)
# -------------------------
# LOADER_GIF = "https://media1.giphy.com/media/v1.Y2lkPTc5MGI3NjExdjJramcyZ3pkamZybDYxOGoyNDh6YXU0MWF2eWhiODdhMXI0ZTN0bCZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9cw/KnJnh0KmNodNJ1aoUI/giphy.gif"  
LOADER_GIF = "https://media4.giphy.com/media/v1.Y2lkPTc5MGI3NjExOTFnMnl3c2Nya2g4eXh2MWJlYmg0MGE5bnJpdHRid2Vubjc0cTdpeiZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9cw/LLd6Ma5vQtXyw/giphy.gif"  

def show_loader():
    loader = st.empty()
    loader.markdown(f"""
    <div class="loader-overlay">
        <img src="{LOADER_GIF}">
    </div>
    """, unsafe_allow_html=True)
    return loader

def hide_loader(loader):
    loader.empty()
st.markdown(f"""
<style>
.loader-overlay {{
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    background: rgba(255,255,255,0.7);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 9999;
}}

.loader-overlay img {{
    width: 500px;
    height: 500px;
}}
</style>
""", unsafe_allow_html=True)
st.markdown("""
<style>

#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

.stApp {
    background: radial-gradient(circle at 20% 20%, #f3f6ff, #eef2ff 40%, #f8fafc 100%);
}

.stApp:before{
    content:"";
    position:fixed;
    width:100%;
    height:100%;
    top:0;
    left:0;
    background-image:
      linear-gradient(rgba(0,0,0,0.03) 1px, transparent 1px),
      linear-gradient(90deg, rgba(0,0,0,0.03) 1px, transparent 1px);
    background-size:40px 40px;
    pointer-events:none;
}

.block-container{
  padding-top:10px;
  padding-bottom:2rem;
}

/* HERO */
.hero {
  padding: 20px 25px 2px 25px;
  border-radius:20px;
  background:linear-gradient(to right, #512DA8, #512DA8);
  color:white;
  box-shadow:0 20px 60px rgba(0,0,0,0.15);
  margin-bottom:20px;
}

/* KPI */
.kpi-card{
    background:rgba(255,255,255,0.7);
    backdrop-filter: blur(12px);
    padding:14px 18px;
    border-radius:14px;
    border:1px solid rgba(255,255,255,0.5);
    box-shadow:0 8px 20px rgba(0,0,0,0.08);
    text-align:center;
}

/* BUTTON */
.stButton>button{
    border-radius:14px;
    background: linear-gradient(135deg, #512DA8, #512DA8);
    color:white;
    font-weight:600;
    border:none;
}

/* TABLE */
.section-title{
    font-size:28px;
    font-weight:700;
    margin-top:10px;
}

.job-cell{
    font-size:18px;
    display:flex;
    align-items:center;
    height:70px;
}

.job-cell-strong{
    font-size:20px;
    font-weight:600;
    display:flex;
    align-items:center;
    height:70px;
}
.btn-center {       
    height:10px;
    display: flex;
    align-items: center;
    
}

.st-key-modal {
            position: fixed;
            top: 10%;
            left: 20%;
            width: 60%;
            height: fit-content;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            padding: 30px;
            overflow-y: auto;
            z-index: 9999;
        }
</style>
""", unsafe_allow_html=True)

# Hide sidebar
st.markdown("""<style>[data-testid="stSidebar"] {display:none;}</style>""", unsafe_allow_html=True)

# -------------------------
# PATHS
# -------------------------
BASE_PATH = r"/home/labuser/Desktop/Project/Instructions/MaaS/projects/Skillcloudtesttry/"
JOB_XML = f"{BASE_PATH}/all_jobs.xml"
JOBID_FILE = f"{BASE_PATH}/jobid.xml"

ns = {"wd": "urn:com.workday.report/CR_All_Job_Applications"}
WD = "urn:com.workday.report/CR_All_Job_Applications"

# -------------------------
# LOAD JOBS
# -------------------------

def load_positions():
    if os.path.exists(JOB_XML):
        tree = ET.parse(JOB_XML)
        root = tree.getroot()

        jobs_dict = {}
        candidate_counts = {}

        for entry in root.findall("wd:Report_Entry", ns):

            job = entry.find("wd:Job_Requisition", ns)
            if job is None:
                continue

            job_id = ""
            for i in job.findall("wd:ID", ns):
                if i.attrib.get(f"{{{WD}}}type") == "Job_Requisition_ID":
                    job_id = i.text

            if not job_id:
                continue

            # Count candidate if present
            candidate_node = entry.find("wd:Candidate", ns)
            if candidate_node is not None:
                candidate_counts[job_id] = candidate_counts.get(job_id, 0) + 1

        for entry in root.findall("wd:Report_Entry", ns):

            group = entry.find("wd:Job_Requisition_group", ns)

            if group is None:
                continue

            # 👉 Read openings FIRST
            openings_node = group.find("wd:Number_of_Openings_Available", ns)

            if openings_node is None or not openings_node.text:
                continue

            try:
                openings = int(openings_node.text.strip())
            except:
                openings = 0

            # 👉 Skip if no openings
            if openings <= 0:
                continue

            # 👉 Only now read other fields
            job = entry.find("wd:Job_Requisition", ns)
            if job is None:
                continue

            job_id = ""
            for i in job.findall("wd:ID", ns):
                if i.attrib.get(f"{{{WD}}}type") == "Job_Requisition_ID":
                    job_id = i.text

            if not job_id or job_id in jobs_dict:
                continue

            title = job.attrib.get(f"{{{WD}}}Descriptor", "")
            if title.startswith(job_id):
                title = title[len(job_id):].strip()

            manager_node = group.find("wd:Hiring_Manager", ns)
            manager = manager_node.attrib.get(f"{{{WD}}}Descriptor", "") if manager_node else ""

            jobs_dict[job_id] = {
                "Job ID": job_id,
                "Title": title,
                "Hiring Manager": manager,
                "Openings": openings,
                "Candidates":candidate_counts.get(job_id, 0)
            }

        return pd.DataFrame(list(jobs_dict.values()))
    else:
        jobs_dict1 = {
                "Job ID": "None",
                "Title": "None",
                "Hiring Manager": "None",
                "Openings": "None",
                "Candidates": "None"
            }
        
        return pd.DataFrame(list(jobs_dict1.values()))
loader = show_loader()
import os
if not os.path.exists(JOB_XML):
    fetch_all_jobs()
df = load_positions()
hide_loader(loader)
if os.path.exists(JOB_XML):
    df = df.sort_values(by="Job ID", ascending=True).reset_index(drop=True)
else:
    print()

# -------------------------
# HERO
# -------------------------
st.markdown("""
<div class="hero">
<h1>🚀 Candidate Skills Evaluator</h1>
<p>AI-assisted hiring dashboard to review open roles and evaluate candidates efficiently.</p>
</div>
""", unsafe_allow_html=True)

if "show_settings" not in st.session_state:
    st.session_state.show_settings = False

col1, col2 = st.columns([8,1])
with col2:
    if st.button("⚙️"):
        st.session_state.show_settings = True

if st.session_state.show_settings:
    with st.container(key="modal"):
        top1, top2 = st.columns([9,1])
        with top1:
            st.markdown("### ⚙️ API Confguration")
        with top2:
            if st.button("❌ Close"):
                st.session_state.show_settings = False
                st.rerun()
        current_url = st.session_state.get(
            "ALL_JOB_URL",
            "https://impl-services1.wd12.myworkday.com/ccx/service/customreport2/tcs_dpt2/ISU+Job+Requisition/CR_All_Job_Applications"
        )
        cur_user = st.session_state.get("username")
        cur_pass = st.session_state.get("password")
        new_url = st.text_input("Enter API Endpoint", value = current_url, help="Please enter the RAAS endpoint from the Workday tenant")
        username = st.text_input("Enter Username", value=cur_user, width=300)
        password = st.text_input("Enter Password", value = cur_pass, type="password", width=300)
        if st.button("💾 Save"):
            config["ALL_JOB_URL"] = new_url
            config["SELECTED_URL"] = new_url
            config["username"] = username
            config["password"] = password
            save_config(config)

            st.session_state.ALL_JOB_URL = new_url
            st.session_state.SELECTED_URL = new_url
            st.session_state.username = username
            st.session_state.password = password

            loader = show_loader()
            fetch_all_jobs()
            hide_loader(loader)
            st.session_state.show_settings = False
            st.rerun()

# -------------------------
# KPI CARDS
# -------------------------
k1,k2,k3 = st.columns(3)

k1.markdown(f"""
<div class="kpi-card">
<h2>📋 {len(df) if os.path.exists(JOB_XML) else 0}</h2>
<p>Active Requisitions</p>
</div>
""", unsafe_allow_html=True)

k2.markdown(f"""
<div class="kpi-card">
<h2>👨‍💼 {df["Hiring Manager"].nunique() if os.path.exists(JOB_XML) else 0}</h2>
<p>Hiring Managers</p>
</div>
""", unsafe_allow_html=True)

k3.markdown(f"""
<div class="kpi-card">
<h2>🔢 {df["Openings"].astype(int).sum() if os.path.exists(JOB_XML) else 0}</h2>
<p>Total Openings</p>
</div>
""", unsafe_allow_html=True)

st.divider()

# -------------------------
# TABLE
# -------------------------
st.markdown('<div class="section-title">📂 Open Job Requisitions</div>', unsafe_allow_html=True)

header = st.columns([1.5,3,3,2,2,2])
header[0].markdown("#### Job ID")
header[1].markdown("#### 💼 Role")
header[2].markdown("#### 👤 Hiring Manager")
header[3].markdown("#### 🔢 Openings")
header[4].markdown("#### Candidates")
header[5].markdown("#### Action")

st.divider()
if os.path.exists(JOB_XML):
    for i,row in df.iterrows():

        c1,c2,c3,c4,c5, c6 = st.columns([1.5,4,3,2,2,2])

        c1.markdown(f'<div class="job-cell-strong">{row["Job ID"]}</div>', unsafe_allow_html=True)
        c2.markdown(f'<div class="job-cell-strong">{row["Title"]}</div>', unsafe_allow_html=True)
        c3.markdown(f'<div class="job-cell">{row["Hiring Manager"]}</div>', unsafe_allow_html=True)
        c4.markdown(f'<div class="job-cell">{row["Openings"]}</div>', unsafe_allow_html=True)
        c5.markdown(f'<div class="job-cell">{row["Candidates"]}</div>', unsafe_allow_html=True)
        c6.markdown(f'<div class="btn-center">', unsafe_allow_html=True)
        if c6.button("🔎 Review Candidates", key=f"job_{i}", use_container_width=True):

            loader = show_loader()
            st.session_state.selected_job_id = row["Job ID"]

            root = ET.Element("Selected_Job")
            ET.SubElement(root, "Job_ID").text = row["Job ID"]
            ET.ElementTree(root).write(JOBID_FILE)        
            fetch_selected_jobs(row["Job ID"])
            hide_loader(loader)
            
            st.switch_page("pages/skillcloud.py")

        st.divider()
