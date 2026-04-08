import requests
from requests.auth import HTTPBasicAuth
import xml.etree.ElementTree as ET
import xml.dom.minidom
import re
import urllib3
import time
import streamlit as st

DEFAULT_URL = "https://impl-services1.wd12.myworkday.com/ccx/service/customreport2/tcs_dpt2/ISU+Job+Requisition/CR_All_Job_Applications"

def get_all_jobs_url():
    return st.session_state.get("ALL_JOB_URL") 

# =========================================================
# 🔐 INTERNAL CONFIG (HIDDEN FROM USER)
# =========================================================



USE_SSL_VERIFY = False
CERT_PATH = None
def _configure_ssl():
    if not USE_SSL_VERIFY:
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        return False
    return CERT_PATH if CERT_PATH else True
def _clean_text(text):
    if text is None:
        return None
    return re.sub(r'[^\w\s\.\,\-\@\&\/]', '', text).strip()
def _clean_xml(element):
    # Extract tag name without namespace
    tag_name = element.tag.split('}')[-1]

    # 🚫 Skip cleaning for Base64 tag
    if tag_name == "Base64" or tag_name=="attachmentContent":
        return
    

    # ✅ Clean normal text
    if element.text:
        element.text = _clean_text(element.text)

    if element.tail:
        element.tail = _clean_text(element.tail)

    # Recurse into children
    for child in element:
        _clean_xml(child)
def _fetch_xml(url, verify_ssl):
    try:
        response = requests.get(
            url,
            auth=HTTPBasicAuth(st.session_state.username, st.session_state.password),
            headers={"Accept": "application/xml"},
            verify=verify_ssl
        )
        if response.status_code == 200:
            print(f"✅ Success: {url}")
            st.toast("API Response recieved", icon="✅")
            time.sleep(2)
            return response.content
        else:
            print(f"❌ Failed ({response.status_code})")
            return None
    except Exception as e:
        print(f"❌ Error: {e}")
        return None


# =========================================================
# ---------------- PROCESS ----------------
# =========================================================
def _process_xml(xml_data):
    try:
        root = ET.fromstring(xml_data)

        _clean_xml(root)

        if "}" in root.tag:
            namespace = root.tag.split('}')[0].strip('{')
            ET.register_namespace('wd', namespace)

        xml_bytes = ET.tostring(root, encoding="utf-8")

        dom = xml.dom.minidom.parseString(xml_bytes)
        pretty_xml = dom.toprettyxml(indent="  ")

        return "\n".join([line for line in pretty_xml.split("\n") if line.strip()])

    except Exception as e:
        print(f"❌ Processing error: {e}")
        return None
def _save_xml(data, filename):
    try:
        with open(filename, "w", encoding="utf-8") as f:
            f.write(data)
        print(f"💾 Saved: {filename}")
    except Exception as e:
        print(f"❌ Save error: {e}")


# =========================================================
# ✅ PUBLIC FUNCTION 1: FETCH ALL JOBS
# =========================================================
def fetch_all_jobs(output_file="all_jobs.xml"):
    """
    Fetch all jobs and save into one file
    """
    verify_ssl = _configure_ssl()

    print("📥 Fetching ALL jobs...")

    xml_data = _fetch_xml(get_all_jobs_url(), verify_ssl)

    if xml_data:
        pretty_xml = _process_xml(xml_data)
        if pretty_xml:
            _save_xml(pretty_xml, output_file)
    


# =========================================================
# ✅ PUBLIC FUNCTION 2: FETCH SELECTED JOBS
# =========================================================
def fetch_selected_jobs(job_ids):
    """
    Fetch selected job(s) using job_id(s)
    Only input required from user
    """

    verify_ssl = _configure_ssl()

    if isinstance(job_ids, str):
        job_ids = [job_ids]

    for job_id in job_ids:
        print(f"\n📥 Fetching Job ID: {job_id}")
        time.sleep(2)
        url = f"{get_all_jobs_url()}?Job_Requisition_ID={job_id}"
        print(url)
        xml_data = _fetch_xml(url, verify_ssl)

        if xml_data:
            pretty_xml = _process_xml(xml_data)
            if pretty_xml:
                filename = f"data.xml"
                _save_xml(pretty_xml, filename)
