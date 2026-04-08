import streamlit as st
import json
import pandas as pd
from src.backend import generate_enterprise_explanation, parse_workday_xml, save_base64_file
import src.backend as backend
from pathlib import Path
import tempfile
from langchain_openai import ChatOpenAI
import os
import httpx
import xml.etree.ElementTree as ET
import base64


st.set_page_config(layout="wide")

current_job = st.session_state.get("selected_job_id")
print("Current Job is : ",current_job)

if "loaded_job_id" not in st.session_state:
    st.session_state.loaded_job_id = None


print("loaded job is : ", st.session_state.loaded_job_id)
# If new job selected → clear everything
if st.session_state.loaded_job_id != current_job:
    # employees=[]
    backend.reset_state()
    st.session_state.clear()
    # mark this job as loaded
    st.session_state.loaded_job_id = current_job

if "show_warning" not in st.session_state:
    st.session_state.show_warning = False
    
client = httpx.Client(verify=False)
llm = ChatOpenAI(
    base_url="https://genailab.tcs.in", # set openai_api_base to the LiteLLMProxy
    model = "azure_ai/genailab-maas-DeepSeek-V3-0324",
    api_key="sk-K8gYKJNpPOSISHb9p08fjA",
    http_client = client
)
# -------------------------------
# SESSION STATE INITIALIZATION
# -------------------------------

if "top_candidates" not in st.session_state:
    print("Addidng top candidates as None")
    st.session_state.top_candidates = None


if "show_download_modal" not in st.session_state:
    st.session_state.show_download_modal = False

# -------------------------------
# HEADER
# -------------------------------
st.markdown("""
<style>

/* ----------- GLOBAL BACKGROUND ----------- */

#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
header {visibility: hidden;}

.stApp {
    background: radial-gradient(circle at 20% 20%, #f3f6ff, #eef2ff 40%, #f8fafc 100%);
}

/* floating subtle grid */
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

/* ----------- HERO PANEL ----------- */

.hero {
  padding: 10px 20px;
  border-radius:20px;
  background:linear-gradient(to right, #512DA8, #512DA8);
  color:white;
  box-shadow:0 20px 60px rgba(0,0,0,0.15);
}

# .hero:after{
#     content:"";
#     position:absolute;
#     width:400px;
#     height:400px;
#     background:radial-gradient(circle, rgba(255,255,255,0.2), transparent);
#     top:-120px;
#     right:-100px;
# }

.block-container{
  padding-top:2rem;
  padding-bottom:4rem;
}

/* ----------- KPI CARDS ----------- */

.kpi-card{

    background:rgba(255,255,255,0.7);
    backdrop-filter: blur(12px);

    padding:28px;

    border-radius:16px;

    border:1px solid rgba(255,255,255,0.5);

    box-shadow:
        0 10px 30px rgba(0,0,0,0.08);

    transition:all .25s ease;

}

.kpi-card:hover{
    transform:translateY(-8px) scale(1.02);
    box-shadow:0 25px 50px rgba(0,0,0,0.15);
}

/* ----------- BUTTONS ----------- */

.stButton>button{

    border-radius:14px;

    background: linear-gradient(135deg,#512DA8,#512DA8);

    color:white;

    font-weight:600;

    border:none;
    margin-top:20px;
    transition:all .2s ease;

    box-shadow:
        0 8px 25px rgba(79,70,229,.35);

}

.stButton>button:hover{

    transform:translateY(-2px);

    box-shadow:
        0 14px 35px rgba(79,70,229,.45);

}

/* ----------- DATAFRAME ----------- */

[data-testid="stDataFrame"]{

    border-radius:18px;

    overflow:hidden;

    box-shadow:
        0 15px 40px rgba(0,0,0,.12);

}

/* ----------- SECTION HEADERS ----------- */

.section-title{

    font-size:28px;

    font-weight:700;

    margin-top:40px;

    margin-bottom:10px;

}

/* ----------- CARD PANELS ----------- */

.section{
margin-top:40px;
margin-bottom:40px;
}

.st-key-panel{
background:rgba(255,255,255,0.85);
backdrop-filter: blur(10px);
padding:28px;
border-radius:16px;
border:1px solid rgba(0,0,0,0.05);
box-shadow:0 10px 30px rgba(0,0,0,0.08);
}

.st-key-panela{
background:rgba(245,245,245,0.85);
backdrop-filter: blur(10px);
padding:10px;
border-radius:16px;
border:1px solid rgba(0,0,0,0.05);
# box-shadow:0 10px 30px rgba(0,0,0,0.08);
text-align: center;
margin-bottom: 20px;
}

.st-key-panel1{
background:rgba(255,255,255,0.85);
backdrop-filter: blur(10px);
padding:28px;
border-radius:16px;
border:1px solid rgba(0,0,0,0.05);
box-shadow:0 10px 30px rgba(0,0,0,0.08);
}

.st-key-panel2{
background:rgba(255,255,255,0.85);
backdrop-filter: blur(10px);
padding:28px;
border-radius:16px;
border:1px solid rgba(0,0,0,0.05);
box-shadow:0 10px 30px rgba(0,0,0,0.08);
}

.st-key-panel3{
background:rgba(255,255,255,0.85);
backdrop-filter: blur(10px);
padding:28px;
border-radius:16px;
border:1px solid rgba(0,0,0,0.05);
box-shadow:0 10px 30px rgba(0,0,0,0.08);
}
/* ----------- SUCCESS BANNER ----------- */

.success-banner{

    border-radius:14px;
    padding:18px;
    margin-bottom:20px;
    background:linear-gradient(135deg, rgba(22, 163, 74, 0.7), rgba(34, 197, 94, 0.5));
    text-color:white;
    color:white;
    opacity: 0.5
    font-weight:600;

}

/* ----------- RISK CARDS ----------- */

.skill-card{

    padding:18px;

    border-radius:14px;

    background:linear-gradient(135deg,#F8F8F8,#FFFFFF);

    color:#0f172a;

    margin-bottom:12px;

    # border:1px solid rgba(0,0,0,0.5);

    box-shadow: inset 2px 5px 5px rgba(0,0,0,0.15);

}

/* ----------- ANIMATED AI LOADER ----------- */
.st-key-modal {
            position: fixed;
            top: 5%;
            left: 10%;
            width: 80%;
            height: 85%;
            background: white;
            border-radius: 20px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            padding: 30px;
            overflow-y: auto;
            z-index: 9999;
        }
            

.ai-loader{

    height:4px;

    width:100%;

    background:
        linear-gradient(90deg,#4f46e5,#ec4899,#4f46e5);

    background-size:200%;

    border-radius:6px;

    animation:load 1.5s linear infinite;

}

@keyframes load{

    0%{background-position:0%}

    100%{background-position:200%}

}

/* ----------- SMOOTH SCROLL ----------- */

html{
    scroll-behavior:smooth;
}

</style>
""", unsafe_allow_html=True)


xml_path = "/home/labuser/Desktop/Project/Instructions/MaaS/projects/Skillcloudtesttry/data.xml"


job_description_s, records, candidate_count, no_attachment = parse_workday_xml(xml_path)
for x in records:
    print("Candidates :",x.get("candidate_name"))
print("Resume not found: ",no_attachment)

st.markdown("""
<div class="hero">

<h1>🤖 AI Talent Intelligence Platform</h1>

<h3>Intelligent Internal Talent Matching</h3>

<p style="opacity:.9;font-size:17px;margin-top:10px">
AI-driven workforce analysis that identifies the best internal talent
for projects using skill intelligence, domain expertise, and availability signals.
</p>

</div>
""", unsafe_allow_html=True)

if "requirement_input" not in st.session_state:
    print("There was no requirement so adding current")
    st.session_state.requirement_input = job_description_s

if st.session_state.requirement_input:
  st.markdown("### 📄 Job Requirement")
  st.markdown(f"""
  <div class="st-key-panela">
  <p style="font-size:18px; font-weight: bold; margin-bottom: 0px; ">
  <i>{st.session_state.requirement_input}</i>
  </p>
  </div>
  """, unsafe_allow_html=True)

col1, col2, col3, col4 = st.columns(4)

col1.markdown(f"""
<div class="kpi-card">
<h3>Total Candidates</h3>
<h1>{candidate_count}</h1>
</div>
""", unsafe_allow_html=True)

# col2.markdown("""
# <div class="kpi-card">
# <h3>AI Matching Engine</h3>
# <h1 style="color:#22c55e;">Active</h1>
# </div>
# """, unsafe_allow_html=True)

# col3.markdown("""
# <div class="kpi-card">
# <h3>Decision Time</h3>
# <h1>< 5 Minutes</h1>
# </div>
# """, unsafe_allow_html=True)

# col4.markdown("""
# <div class="kpi-card">
# <h3>Cost Reduction</h3>
# <h1>30–50%</h1>
# </div>
# """, unsafe_allow_html=True)

st.divider()
if st.button("Process Resumes"):
    if len(no_attachment)>0:
        st.session_state.show_warning = True
    
    from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend
    from docling.document_converter import (DocumentConverter, PdfFormatOption, WordFormatOption,)
    from docling.datamodel.base_models import InputFormat
    from docling.pipeline.simple_pipeline import SimplePipeline
    from docling.pipeline.standard_pdf_pipeline import StandardPdfPipeline
    from docling_core.types.doc.document import ContentLayer
    progress_container = st.empty()
    progress_bar = st.progress(0)
    total = len(records)
    converter = DocumentConverter(  # all of the below is optional, has internal defaults.
        allowed_formats=[
            InputFormat.PDF,
            InputFormat.IMAGE,
            InputFormat.DOCX,
            InputFormat.HTML,
            InputFormat.PPTX,
            InputFormat.ASCIIDOC,
            InputFormat.CSV,
            InputFormat.MD,
        ],  # whitelist formats, non-matching files are ignored.
        format_options={
            InputFormat.PDF: PdfFormatOption(
                pipeline_cls=StandardPdfPipeline, backend=PyPdfiumDocumentBackend
            ),
            InputFormat.DOCX: WordFormatOption(
                pipeline_cls=SimplePipeline  # or set a backend, e.g., MsWordDocumentBackend
                # If you change the backend, remember to import it, e.g.:
                #   from docling.backend.msword_backend import MsWordDocumentBackend
            ),
        },
    )
    added_count = 0
    
    for i,record in enumerate(records):
      print("Inside for loop")
      if len(no_attachment)>0:
          progress_container.markdown(
            f"🤖 AI processing (**{i+1}/{total}** candidates) | **{len(no_attachment)}** resumes not found"
        )
      else:
          progress_container.markdown(
            f"🤖 AI processing **({i+1}/{total}** candidates)"
        )
      progress_bar.progress((i + 1) / total)


      try:
            file_path = save_base64_file(
                record["base64"],
                record["filename"]
            )
            print('File is',file_path)
            result = list(converter.convert_all([Path(file_path)]))
            resume_text = result[0].document.export_to_markdown(included_content_layers={ContentLayer.FURNITURE,ContentLayer.BODY})
            prompt=f"""_text
            You are an expert resume-to-structured-data converter.

            Your job is to extract information from the resume and return STRICTLY valid JSON
            that matches the required employee schema.

            Return ONLY valid JSON in this exact structure:

            {{
              "full_name": "",
              "current_project": "",
              "availability": 0.0,
              "resume_skills": {{
                  "Skill Name": 0
              }},
              "domains": []
            }}

            STRICT RULES:

            1. employee_id:
              - Leave empty string "" (it will be assigned later).

            2. current_project:
              - If current project mentioned, extract it.
              - Otherwise figure out based on latest experience.

            3. availability:
              - Based on the experience date, see if the employee is available for immediate joining, let the notice period be 90 days, see how far he is from it
              - Estimate availability as a float between 0.0 and 1.0
              - 1.0 = immediately available
              - 0.5 = partially allocated
              - 0.2 = fully allocated
              - If unknown, return 0.8

            4. resume_skills:
              - Must be a dictionary.
              - Keys = main proven skills only.
              - Values = years of experience for that skill as INTEGER.
              - If exact years not mentioned, estimate from total experience proportionally.

              - Do NOT include vague terms like "pressure handle" or "hard-working".

            5. domains:
              - Only business domains 
              - These should be the functional / technical domains or sector which can tell how this employee contributes to business(refer these example : Software Development, Data Science & Analytics, Cybersecurity, DevOps, IT Infrastructure & Support, Marketing & Sales, UI/UX Design, Human Resources & Administration, Sales & Business Development, Operations & Logistics,Legal & Compliance, Finance & Investment, etc and many others)
              - Do NOT include technical stack names as domains.
              - Do NOT include skills as domain.
              - If none found, return empty list [].

            6. DO NOT:
              - Add explanations.
              - Add comments.
              - Wrap in markdown.
              - Add extra fields.
              - Return anything other than JSON.

            Resume:
            ----------------
            {resume_text}
            ----------------
            """
            response = llm.invoke(prompt).content
            response = response.strip().replace("```json", "").replace("```", "")

            data = json.loads(response)

            backend.add_employee(
                data["full_name"],
                data["current_project"],
                data["availability"],
                data["resume_skills"],
                data["domains"],
                extra_data={
                    "filename":record["filename"],
                    "base64":record["base64"],
                },
            )

            st.toast(f"✅ {data['full_name']} added successfully!", icon="🎉")
      except Exception as e:
              st.error(f'Parsing failed for candidate: {record["candidate_name"]}. **Try Again**')
              # st.write(response)


    st.divider()

# -------------------------------
# KPI SECTION
# -------------------------------



# -------------------------------
# REQUIREMENT INPUT
# -------------------------------



    if not st.session_state.requirement_input.strip():
        st.warning("There is no requirement found!")
    else:
        with st.spinner("🤖 AI analyzing workforce data..."):
            if len(backend.employees)!=0:
                st.session_state.top_candidates = backend.match_employees_production(
                    backend.employees, st.session_state.requirement_input
                )

# -------------------------------
# RESULTS SECTION
# -------------------------------
if st.session_state.show_warning:
    print("Yes")
    name = ", ".join(no_attachment)
    st.warning(f"Resume not found for : **{name}**")

if st.session_state.top_candidates:
    
    st.markdown("""
    <div class="success-banner">
    Top Matching Talent Identified
    </div>
    """, unsafe_allow_html=True)
    
    df = pd.DataFrame(st.session_state.top_candidates)

    # Format for executives
    df_display = df.copy()
    df_display = df.drop(columns=["base64","filename"])
    df_display["structured_score"] *= 100
    df_display["domain_score"] *= 100
    df_display["semantic_similarity"] *= 100
    df_display["availability_score"] *= 100
    df_display["final_score"] *= 100

    df_display.rename(columns={
        "full_name": "Name",
        "structured_score": "Skill Match %",
        "domain_score": "Domain Match %",
        "semantic_similarity": "Context Match %",
        "availability_score": "Availability %",
        "final_score": "Overall Fit %",
        "matched_skills": "Matched Skills",
        "matched_domains": "Matched Domains"
    }, inplace=True)
    print(df["filename"])
    st.dataframe(df_display, use_container_width=True, hide_index=True)

    if st.button("📥 Download Resumes"):
        st.session_state.show_download_modal = True

    st.divider()

    # -------------------------------
    # VISUAL INSIGHTS
    # -------------------------------
    if st.session_state.show_download_modal:
        with st.container(key="modal"):
            top1, top2 = st.columns([9,1])
            with top1:
                st.markdown("## 📥 Download Candidate Resumes")
            with top2:
                if st.button("❌ Close"):
                    st.session_state.show_download_modal = False
                    st.rerun()
            st.divider()
            for i, row in df.iterrows():
                c1, c2, c3 = st.columns([4,3,2])
                c1.markdown(f"**{row['full_name']}**")
                c2.markdown(f"Overall Fit: {round(row['final_score']*100)}%")
                file_bytes = base64.b64decode(row["base64"])
                c3.download_button(
                    label="⬇️ Download",
                    data=file_bytes,
                    file_name=row["filename"],
                    mime="application/octet-stream",
                    key=f"download_modal_{i}"
                )

    st.divider()
    st.markdown('<div class="section-title">📊 Match Breakdown</div>', unsafe_allow_html=True)

    chart_df = df_display.set_index("Name")[
        ["Skill Match %", "Domain Match %", "Availability %"]
    ]

    st.bar_chart(chart_df)

    st.divider()

    # -------------------------------
    # DETAILED VIEW
    # -------------------------------

    # st.subheader("🔎 Candidate Deep Dive")

    # selected_emp_id = st.selectbox(
    #     "Select Candidate for Detailed Evaluation",
    #     df_display["Name"],
    #     key="employee_selector"
    # )

    # selected_employee = next(
    #     e for e in backend.employees
    #     if e["full_name"] == selected_emp_id
    # )

    # explanation = generate_enterprise_explanation(
    #     selected_employee,
    #     st.session_state.requirement_input
    # )

    # colA, colB = st.columns(2)

    # # -------------------------------
    # # LEFT SIDE – FIT & DOMAIN
    # # -------------------------------

    # with colA:
    #   with st.container(key = "panel"):
    #     st.markdown("### 🧠 Fit Assessment")
    #     st.write("**Overall Fit:**", explanation["overall_fit"])
    #     st.write("**Risk Level:**", explanation["risk_level"])
    #     st.write("**Availability:**", explanation["availability"])
    #     st.write("**Skill Match Score:**", f"{explanation['structured_score'] * 100:.0f}%")

    #     st.markdown("### 🌍 Domain Alignment")

    #     if explanation["required_domains"]:
    #         st.write("**Required Domain(s):**", ", ".join(explanation["required_domains"]))
    #     else:
    #         st.write("**Required Domain(s):** None specified")

    #     if explanation["matched_domains"]:
    #         st.success("Matched Domain(s): " + ", ".join(explanation["matched_domains"]))
    #     else:
    #         st.error("No Required Domain Match")

    #     st.write("**Domain Match Score:**", f"{explanation['domain_score'] * 100:.0f}%")

    # # -------------------------------
    # # RIGHT SIDE – SKILL DETAILS
    # # -------------------------------

    # with colB:
    #     with st.container(key = "panel1"):
    #         if explanation["matched_skills"]:
    #             st.markdown("### ✅ Matched Skills")
    #             for skill in explanation["matched_skills"]:
    #                 st.write(f"✔ {skill['skill']} ({skill['years']} years)")

    #         if explanation["partially_matched_skills"]:
    #             st.markdown("### ⚠️ Partial Skills")
    #             for skill in explanation["partially_matched_skills"]:
    #                 st.write(f"⚠ {skill['skill']} ({skill['years']} yrs, required {skill['required']})")

    #         if explanation["extra_skills"]:
    #             st.markdown("### ➕ Additional Skills")
    #             for skill in explanation["extra_skills"]:
    #                 st.write(f"✚ {skill['skill']}")

    # st.divider()

    # # -------------------------------
    # # BUSINESS IMPACT SECTION
    # # -------------------------------

    # st.subheader("💰 Business Impact Estimation")

    # st.info("""
    # • Reduces manual resume screening
    # • Minimizes hiring bias
    # • Improves internal workforce utilization
    # • Accelerates project staffing decisions
    # • Reduces dependency on external consultants
    # """)




    # # ============================================================
    # # 🔥 EXECUTIVE WORKFORCE RISK PANEL
    # # ============================================================

    # from src.backend import organization_gap_analysis, compare_candidates, match_employees_simulator

    # st.divider()
    # st.subheader("📉 Workforce Risk & Gap Analysis")

    # gap_report = organization_gap_analysis(st.session_state.requirement_input)

    # col_low, col_mod, col_high = st.columns(3)

    # col_low.markdown("### 🟢 Low Risk")
    # col_mod.markdown("### 🟡 Moderate Risk")
    # col_high.markdown("### 🔴 High Risk")


    # def render_scroll_container(content):
    #     st.markdown(f"""
    #     <div style="
    #         max-height: 500px;
    #         overflow-y: auto;
    #         padding-right: 6px;
    #     ">
    #         {content}
    #     </div>
    #     """, unsafe_allow_html=True)


    # def build_card(skill):
    #   return f"""
    #   <div class="skill-card">
    #       <h4>{skill['skill']}</h4>
    #       <p><b>Available:</b> {skill['available_employees']}</p>
    #       <p><b>Strong Matches:</b> {skill['strong_match_count']}</p>
    #       <p><b>Avg Experience:</b> {skill['avg_experience']} yrs</p>
    #   </div>
    #   """


    # low_cards = ""
    # mod_cards = ""
    # high_cards = ""

    # for skill in gap_report["skills"]:
    #     card_html = build_card(skill)

    #     if skill["risk_level"] == "Low Risk":
    #         low_cards += card_html
    #     elif skill["risk_level"] == "Moderate Risk":
    #         mod_cards += card_html
    #     else:
    #         high_cards += card_html


    # with col_low:
    #     render_scroll_container(low_cards)

    # with col_mod:
    #     render_scroll_container(mod_cards)

    # with col_high:
    #     render_scroll_container(high_cards)




    # # ============================================================
    # # 🔍 WHY NOT COMPARATOR
    # # ============================================================

    # st.divider()
    # st.subheader("🔍 Why Not Candidate Comparator")

    # with st.container(key = "panel3"):
    #   colX1, colX2 = st.columns(2)

    #   emp_a = colX1.selectbox("Candidate A", df_display["Name"], key="cmpA")
    #   emp_b = colX2.selectbox("Candidate B", df_display["Name"], key="cmpB")

    #   if emp_a and emp_b:

    #     comparison = compare_candidates(
    #         emp_a,
    #         emp_b,
    #         st.session_state.requirement_input
    #     )

    #     data_a = comparison[emp_a]
    #     data_b = comparison[emp_b]

    #     st.markdown("### 📊 Side-by-Side Comparison")

    #     colA, colB = st.columns(2)

    #     with colA:
    #       # with st.container(key = "panel2"):
    #         st.markdown(f"#### 🅰 Candidate {emp_a}")
    #         st.metric("Skill Match", f"{data_a['structured_score']*100:.0f}%")
    #         st.metric("Domain Match", f"{data_a['domain_score']*100:.0f}%")
    #         st.metric("Availability", f"{data_a['availability']*100:.0f}%")
    #         for skill, years in comparison[emp_a]["required_skill_experience"].items():
    #           st.write(f"{skill}: {years} years")

    #         # st.metric("Total Experience (Years)", data_a["total_experience_years"])

    #     with colB:
    #       # with st.container(key = "panel3"):
    #         st.markdown(f"#### 🅱 Candidate {emp_b}")
    #         st.metric("Skill Match", f"{data_b['structured_score']*100:.0f}%")
    #         st.metric("Domain Match", f"{data_b['domain_score']*100:.0f}%")
    #         st.metric("Availability", f"{data_b['availability']*100:.0f}%")
    #         for skill, years in comparison[emp_b]["required_skill_experience"].items():
    #           st.write(f"{skill}: {years} years")
    #         # st.metric("Total Experience (Years)", data_b["total_experience_years"])

    #   # ------------------------
    #   # AI Decision Insight
    #   # ------------------------

    #   st.divider()
    #   st.markdown("### 🧠 Why One Candidate Ranks Higher")

    #   if data_a["structured_score"] > data_b["structured_score"]:
    #       st.success(f"{emp_a} ranks higher due to stronger required skill alignment.")
    #   elif data_b["structured_score"] > data_a["structured_score"]:
    #       st.success(f"{emp_b} ranks higher due to stronger required skill alignment.")
    #   else:
    #       st.info("Both candidates have similar skill alignment.")

    #   if data_a["domain_score"] != data_b["domain_score"]:
    #       stronger = emp_a if data_a["domain_score"] > data_b["domain_score"] else emp_b
    #       st.write(f"• {stronger} has stronger domain relevance.")

    #   if data_a["availability"] != data_b["availability"]:
    #       more_available = emp_a if data_a["availability"] > data_b["availability"] else emp_b
    #       st.write(f"• {more_available} is more immediately available.")


    #   expr_a = sum(data_a["required_skill_experience"].values())
    #   expr_b = sum(data_b["required_skill_experience"].values())
    #   if expr_a != expr_b:
    #       more_exp = emp_a if expr_a > expr_b else emp_b
    #       st.write(f"• {more_exp} has greater experience in the required skills.")



    # # ============================================================
    # # ⚙ WHAT-IF SIMULATOR
    # # ============================================================

    # st.divider()
    # st.subheader("⚙ What-If Strategic Simulator")

    # colW1, colW2, colW3, colW4 = st.columns(4)

    # skill_weight = colW1.slider("Skill Weight", 0.0, 1.0, 0.45)
    # domain_weight = colW2.slider("Domain Weight", 0.0, 1.0, 0.20)
    # semantic_weight = colW3.slider("Semantic Weight", 0.0, 1.0, 0.25)
    # availability_weight = colW4.slider("Availability Weight", 0.0, 1.0, 0.10)

    # if st.button("Run Simulation"):

    #     simulation_results = match_employees_simulator(
    #         st.session_state.requirement_input,
    #         skill_weight,
    #         domain_weight,
    #         semantic_weight,
    #         availability_weight
    #     )

    #     st.write("### Simulation Results (Adjusted Rankings)")
    #     st.dataframe(pd.DataFrame(simulation_results))
