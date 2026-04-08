import random
import re
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import json
import os
import unicodedata, re
import xml.etree.ElementTree as ET
import base64
import tempfile
from sentence_transformers import SentenceTransformer

import streamlit as st

@st.cache_resource
def get_embedder():
    return SentenceTransformer("BAAI/bge-small-en-v1.5")

embedder = get_embedder()

DATA_FILE = "employees.json"

employees = []
employee_embeddings = None
skill_embeddings_cache = None
domain_embeddings_cache = None

def clean_name(text):
    if not text:
        return ""
    parts = re.split(r'[\u200e\u200f]', text)

    name = parts[0].strip()
    return name

def parse_workday_xml(xml_path):

    tree = ET.parse(xml_path)
    root = tree.getroot()

    namespace = {"wd": "urn:com.workday.report/CR_All_Job_Applications"}

    records = []
    no_attachment=[]
    job_description=None
    candidate_count=0
    for entry in root.findall("wd:Report_Entry", namespace):
        if not job_description:
            job_desc = entry.find(".//wd:Job_Description_Summary", namespace)
            job_description = job_desc.text if job_desc is not None else ""
            print("Found JD",job_description)

        # Candidate Name
        WD_NS = "urn:com.workday.report/CR_All_Job_Applications"
        candidate = entry.find("wd:Candidate", namespace)
        # print(candidate.attrib)
        candidate_name = candidate.attrib.get(f"{{{namespace.get("wd")}}}Descriptor", "") if candidate is not None else ""
        candidate_name=clean_name(candidate_name)
        if candidate:
            candidate_count+=1
        # Job Description (Requirement)
        job_desc = entry.find(".//wd:Job_Description_Summary", namespace)
        job_description = job_desc.text if job_desc is not None else ""

        # File Info
        attachment = entry.find("wd:attachments_group", namespace)

        if attachment is not None:
            filename = attachment.find("wd:fileName", namespace).text
            base64_data = attachment.find("wd:Base64", namespace).text #do Base64 for base64 attachmentContent

            records.append({
                "candidate_name": candidate_name,
                "job_description": job_description,
                "filename": filename,
                "base64": base64_data
            })
        else:
            no_attachment.append(candidate_name)

    print("Found candidates : ", len(records))
    return job_description,records, candidate_count, no_attachment

def save_base64_file(base64_string, filename):

    file_bytes = base64.b64decode(base64_string)

    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=f"_{filename}")
    temp_file.write(file_bytes)
    temp_file.close()

    return temp_file.name

def reset_state():
    global employees, employee_embeddings, skill_embeddings_cache

    employees.clear()
    employee_embeddings = None
    skill_embeddings_cache = None

def load_employees():
    global employees
    employees = []
    rebuild_embeddings()

# def save_employees():
#     with open(DATA_FILE, "w") as f:
#         json.dump(employees, f, indent=4)

def add_employee(full_name, current_project, availability, resume_skills, domains, extra_data=None):

    if any(emp["full_name"] == full_name for emp in employees):
        return
    employee = {
        "full_name": full_name,
        "current_project": current_project,
        "availability": availability,
        "resume_skills": resume_skills,
        "domains": domains
    }

    if extra_data:
        employee.update(extra_data)

    employees.append(employee)
    rebuild_embeddings()


def rebuild_embeddings():
    global employee_embeddings
    employee_embeddings = build_employee_embeddings(employees)
    initialize_skill_embeddings()
    initialize_domain_embeddings()


def build_employee_profile_text(employee):

    skills_text = ", ".join(
        [f"{skill} ({years} years)"
         for skill, years in employee["resume_skills"].items()]
    )

    domain_text = ", ".join(employee["domains"])

    profile = f"""
    Employee Skills: {skills_text}.
    Employee Domains: {domain_text}.
    """

    return profile.strip()

def build_employee_embeddings(employees):

    profiles = [build_employee_profile_text(emp) for emp in employees]

    embeddings = embedder.encode(
        profiles,
        normalize_embeddings=True
    )

    return embeddings


def initialize_skill_embeddings():
    global skill_embeddings_cache

    all_skills = list({
        skill
        for emp in employees
        for skill in emp["resume_skills"].keys()
    })

    skill_embeddings = embedder.encode(
        all_skills,
        normalize_embeddings=True
    )

    skill_embeddings_cache = {
        "skills": all_skills,
        "embeddings": skill_embeddings
    }

def initialize_domain_embeddings():
    global domain_embeddings_cache

    all_domains = list({
        domain
        for emp in employees
        for domain in emp["domains"]
    })

    domain_embeddings = embedder.encode(
        all_domains,
        normalize_embeddings=True,
    )

    domain_embeddings_cache = {
        "domains" : all_domains,
        "embeddings" : domain_embeddings
    }

def detect_required_skills(requirement_text, similarity_threshold=0.63):

    global skill_embeddings_cache

    req_embedding = embedder.encode(
        requirement_text,
        normalize_embeddings=True
    )

    required = []

    for skill, skill_emb in zip(
        skill_embeddings_cache["skills"],
        skill_embeddings_cache["embeddings"]
    ):

        sim = cosine_similarity(
            [req_embedding],
            [skill_emb]
        )[0][0]

        if sim >= similarity_threshold:
            required.append(skill)

    year_match = re.findall(r"(\d+)\+?\s+years?", requirement_text)
    min_years = int(year_match[0]) if year_match else 1

    return required, min_years

def compute_structured_score(employee, required_skills, min_years):

    if not required_skills:
        return 0

    matched = 0

    for skill in required_skills:
        if skill in employee["resume_skills"]:
            years = employee["resume_skills"][skill]

            if years >= min_years:
                matched += 1
            else:
                matched += years / min_years

    return matched / len(required_skills)

def detect_required_domains(requirement_text, similarity_threshold = 0.55):
    global domain_embeddings_cache

    req_embedding = embedder.encode(
        requirement_text,
        normalize_embeddings=True
    )

    req_domain=[]

    for domain, domain_emb in zip(
        domain_embeddings_cache["domains"],
        domain_embeddings_cache["embeddings"]
        ):
        sim = cosine_similarity(
            [req_embedding],
            [domain_emb]
        )[0][0]

        if sim>=similarity_threshold:
            req_domain.append(domain)
    
    return req_domain

    # global employees

    # domain_vocab = set()
    # for emp in employees:
    #     domain_vocab.update(emp["domains"])

    # required_domains = []

    # for domain in domain_vocab:
    #     if domain.lower() in requirement_text.lower():
    #         required_domains.append(domain)

    # return required_domains

def compute_domain_score(employee, required_domains):

    if not required_domains:
        return 0
    
    matched= 0

    for domain in required_domains:
        if domain in employee["domains"]:
            matched+=1

    return matched/len(required_domains)

    # return len(matches) / len(required_domains)

def match_employees_production(empl, requirement_text, top_k=20):
    
    # 1️⃣ Detect required skills
    required_skills, min_years = detect_required_skills(requirement_text)
    required_domains = detect_required_domains(requirement_text)

    print("Required skills:", required_skills)
    print("Required domains:", required_domains)

    if not required_skills:
        print("No required skills detected.")
        return []

    req_embedding = embedder.encode(
        requirement_text,
        normalize_embeddings=True
    )

    candidates = []

    # 2️⃣ First pass: compute structured matches + semantic
    for idx, emp in enumerate(empl):
        print("Employee : ", len(emp))
        structured_score = compute_structured_score(
            emp,
            required_skills,
            min_years
        )

        domain_score = compute_domain_score(emp, required_domains)

        # Count matched skills (for relative filtering)
        matched_count = 0
        for skill in required_skills:
            if skill in emp["resume_skills"]:
                matched_count += 1

        semantic_sim = cosine_similarity(
            [req_embedding],
            [employee_embeddings[idx]]
        )[0][0]

        candidates.append({
            "employee": emp,
            "matched_count": matched_count,
            "structured_score": structured_score,
            "domain_score": domain_score,
            "semantic_similarity": semantic_sim,
            "availability": emp["availability"],
            "filename" : emp["filename"],
            "base64":emp["base64"],
        })

    # 3️⃣ Relative Filtering Logic
    max_matched = max(c["matched_count"] for c in candidates)

    # Adaptive threshold (70% of best performer)
    threshold = max_matched * 0.1

    filtered = [
        c for c in candidates
        if c["matched_count"] >= threshold
    ]

    # If filtering removes everyone, fallback to top 10 structured
    if not filtered:
        filtered = sorted(
            candidates,
            key=lambda x: x["structured_score"],
            reverse=True
        )[:10]

    # 4️⃣ Final weighted scoring
    results = []

    for c in filtered:

        final_score = (
            0.45 * c["structured_score"] +
            0.20 * c["domain_score"] +
            0.25 * c["semantic_similarity"] +
            0.10 * c["availability"]
        )

        matched_skill_names = [
          skill for skill in required_skills
          if skill in c["employee"]["resume_skills"]
        ]

        matched_domains = list(
            set(c["employee"]["domains"]).intersection(required_domains)
        )

        results.append({
            "full_name": c["employee"]["full_name"],
            "matched_skills": matched_skill_names,
            "matched_domains": matched_domains,
            "structured_score": round(c["structured_score"], 3),      #structure is skill
            "domain_score": round(c["domain_score"], 3),
            "semantic_similarity": round(c["semantic_similarity"], 3),
            "availability_score": round(c["availability"], 3),
            "final_score": round(float(final_score), 3),
            "filename":c["filename"],
            "base64":c["base64"],
        })

    ranked = sorted(results, key=lambda x: x["final_score"], reverse=True)

    return ranked[:top_k]

# ------Loading & Initializing-----
load_employees()

# ------- Explanation Part --------
def build_evaluation_evidence(employee, required_skills, min_years):

    matched = []
    partial = []
    extra = []

    for skill in required_skills:

        if skill in employee["resume_skills"]:
            years = employee["resume_skills"][skill]

            if years >= min_years:
                matched.append({
                    "skill": skill,
                    "years": years,
                    "status": "meets_requirement"
                })
            else:
                partial.append({
                    "skill": skill,
                    "years": years,
                    "required": min_years,
                    "status": "below_requirement"
                })


    for skill in employee["resume_skills"]:
      if skill not in required_skills:
        extra.append({
            "skill": skill,
            "status": "extra"
        })
    return {
        "matched": matched,
        "partial": partial,
        "extra": extra
    }


def classify_fit(structured_score):

    if structured_score >= 0.75:
        return "Strong Fit", "Low Risk"
    elif structured_score >= 0.5:
        return "Moderate Fit", "Medium Risk"
    else:
        return "Weak Fit", "High Risk"

def generate_enterprise_explanation(employee, requirement_text):

    # Detect skills and domains
    required_skills, min_years = detect_required_skills(requirement_text)
    required_domains = detect_required_domains(requirement_text)

    # Skill evidence
    evidence = build_evaluation_evidence(
        employee,
        required_skills,
        min_years
    )

    structured_score = compute_structured_score(
        employee,
        required_skills,
        min_years
    )

    # Domain scoring
    domain_score = compute_domain_score(employee, required_domains)
    matched_domains = list(
        set(employee["domains"]).intersection(required_domains)
    )

    fit_level, risk_level = classify_fit(structured_score)

    explanation = {
        "full_name": employee["full_name"],
        "overall_fit": fit_level,
        "risk_level": risk_level,
        "availability": employee["availability"],
        "structured_score": round(structured_score, 3),

        # Skill Details
        "required_skills": required_skills,
        "matched_skills": evidence["matched"],
        "partially_matched_skills": evidence["partial"],
        "extra_skills": evidence["extra"],

        # Domain Details
        "required_domains": required_domains,
        "matched_domains": matched_domains,
        "domain_score": round(domain_score, 3),

        # Raw employee domains
        "employee_domains": employee["domains"]
    }

    return explanation


# -------------------------------
# ORGANIZATION GAP ANALYSIS
# -------------------------------

def organization_gap_analysis(requirement_text):

    required_skills, min_years = detect_required_skills(requirement_text)
    required_domains = detect_required_domains(requirement_text)

    skill_analysis = []
    domain_analysis = []

    for skill in required_skills:

        total_available = sum(
            1 for emp in employees
            if skill in emp["resume_skills"]
        )

        strong_match = sum(
            1 for emp in employees
            if skill in emp["resume_skills"] and emp["resume_skills"][skill] >= min_years
        )

        avg_experience = np.mean([
            emp["resume_skills"][skill]
            for emp in employees
            if skill in emp["resume_skills"]
        ]) if total_available > 0 else 0

        risk_level = (
            "High Risk"
            if total_available < 3
            else "Moderate Risk"
            if total_available < 6
            else "Low Risk"
        )

        skill_analysis.append({
            "skill": skill,
            "required_years": min_years,
            "available_employees": total_available,
            "strong_match_count": strong_match,
            "avg_experience": round(float(avg_experience), 2),
            "risk_level": risk_level
        })

    for domain in required_domains:

        domain_count = sum(
            1 for emp in employees
            if domain in emp["domains"]
        )

        risk_level = (
            "High Risk"
            if domain_count < 3
            else "Moderate Risk"
            if domain_count < 6
            else "Low Risk"
        )

        domain_analysis.append({
            "domain": domain,
            "available_employees": domain_count,
            "risk_level": risk_level
        })

    return {
        "skills": skill_analysis,
        "domains": domain_analysis
    }


# -------------------------------
# WHY NOT COMPARATOR
# -------------------------------

def compare_candidates(name1, name2, requirement_text):

    emp1 = next(e for e in employees if e["full_name"] == name1)
    emp2 = next(e for e in employees if e["full_name"] == name2)

    required_skills, min_years = detect_required_skills(requirement_text)
    required_domains = detect_required_domains(requirement_text)

    def evaluate(emp):

        structured_score = compute_structured_score(emp, required_skills, min_years)
        domain_score = compute_domain_score(emp, required_domains)
        # required_skills, min_years = detect_required_skills(requirement_text)

        required_skill_experience = {
            skill: emp["resume_skills"][skill]
            for skill in required_skills
            if skill in emp["resume_skills"]
        }

        return {
            "structured_score": round(structured_score, 3),
            "domain_score": round(domain_score, 3),
            "availability": emp["availability"],
            "required_skill_experience": required_skill_experience
        }

    return {
        name1: evaluate(emp1),
        name2: evaluate(emp2)
    }


# -------------------------------
# WHAT-IF SIMULATOR VERSION
# -------------------------------

def match_employees_simulator(requirement_text,
                              skill_weight=0.45,
                              domain_weight=0.20,
                              semantic_weight=0.25,
                              availability_weight=0.10,
                              top_k=20):

    required_skills, min_years = detect_required_skills(requirement_text)
    required_domains = detect_required_domains(requirement_text)

    if not required_skills:
        return []

    req_embedding = embedder.encode(
        requirement_text,
        normalize_embeddings=True
    )

    results = []

    for idx, emp in enumerate(employees):

        structured_score = compute_structured_score(emp, required_skills, min_years)
        domain_score = compute_domain_score(emp, required_domains)

        semantic_sim = cosine_similarity(
            [req_embedding],
            [employee_embeddings[idx]]
        )[0][0]

        final_score = (
            skill_weight * structured_score +
            domain_weight * domain_score +
            semantic_weight * semantic_sim +
            availability_weight * emp["availability"]
        )

        results.append({
            "full_name": emp["full_name"],
            "final_score": round(float(final_score), 3)
        })

    ranked = sorted(results, key=lambda x: x["final_score"], reverse=True)

    return ranked[:top_k]

