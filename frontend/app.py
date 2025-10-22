import streamlit as st
import requests
import pandas as pd
import time
from io import BytesIO

# ---------------- CONFIG ----------------
st.set_page_config(
    page_title="Scholar Downloader",
    page_icon="📚",
    layout="wide"
)

BACKEND_BASE = "https://scholar-search-app-backend.onrender.com"

# ---------------- HEADER ----------------
st.title("📘 Scholar Downloader")
st.markdown(
    """
    #### Find and Download Research Papers Effortlessly  
    Upload a file **or** enter researcher names below to fetch papers from Semantic Scholar, OpenAlex, and Google Scholar.
    """
)

# ---------------- INPUT SECTION ----------------
col1, col2 = st.columns([2, 1])

with col1:
    names = st.text_area(
        "Enter researcher names (one per line):",
        placeholder="Example:\nAndrew Ng\nYann LeCun\nFei-Fei Li"
    )

with col2:
    uploaded_file = st.file_uploader(
        "📤 Upload file (CSV, TXT, XLSX)",
        type=["csv", "txt", "xlsx"]
    )

# ---------------- PARSE FILE ----------------
file_names = []
if uploaded_file:
    try:
        if uploaded_file.name.endswith(".csv"):
            df = pd.read_csv(uploaded_file)
        elif uploaded_file.name.endswith(".xlsx"):
            df = pd.read_excel(uploaded_file)
        elif uploaded_file.name.endswith(".txt"):
            content = uploaded_file.read().decode("utf-8")
            df = pd.DataFrame({"names": [n.strip() for n in content.splitlines() if n.strip()]})
        else:
            df = pd.DataFrame()

        name_col = df.columns[0]
        file_names = df[name_col].dropna().astype(str).tolist()
        st.success(f"✅ Loaded {len(file_names)} names from file.")
    except Exception as e:
        st.error(f"⚠️ Error reading file: {e}")

# ---------------- MERGE NAMES ----------------
combined_names = []
if names.strip():
    combined_names += [n.strip() for n in names.split("\n") if n.strip()]
if file_names:
    combined_names += file_names
combined_names = list(dict.fromkeys(combined_names))  # remove duplicates

# ---------------- SESSION STATE ----------------
if "results" not in st.session_state:
    st.session_state.results = None
if "attempt" not in st.session_state:
    st.session_state.attempt = 0

# ---------------- SEARCH & RETRY ----------------
colA, colB = st.columns([1, 1])
with colA:
    search_button = st.button("🔍 Search Papers", type="primary")
with colB:
    retry_button = st.button("🔁 Retry Search", type="secondary")

if (search_button or retry_button) and combined_names:
    # Reset previous results
    st.session_state.results = None
    st.session_state.attempt += 1
    st.session_state.last_search_time = time.strftime("%H:%M:%S")

    attempt_label = f"Attempt #{st.session_state.attempt}"
    with st.spinner(f"{attempt_label} — Searching fresh... Please wait ⏳"):
        try:
            resp = requests.post(
                f"{BACKEND_BASE}/search",
                json={"names": combined_names},
                timeout=600
            )
            if resp.status_code == 200:
                new_results = resp.json().get("data", [])
                st.session_state.results = new_results

                if not new_results:
                    st.warning("⚠️ No papers found — try again later or check the names.")
                else:
                    st.success(f"✅ Search completed successfully at {st.session_state.last_search_time}")

            else:
                st.error(f"❌ Error {resp.status_code}: {resp.text}")

        except Exception as e:
            st.error(f"⚠️ Unable to connect to backend: {e}")

# ---------------- DISPLAY RESULTS ----------------
if st.session_state.results:
    st.markdown(f"## 🧾 Search Results (Attempt {st.session_state.attempt})")
    for author_data in st.session_state.results:
        st.markdown(f"### 👤 {author_data['Researcher']}")
        if "Error" in author_data:
            st.warning(author_data["Error"])
            continue

        papers = author_data["papers"]
        if not papers:
            st.info("No papers found for this researcher.")
            continue

        df = pd.DataFrame(papers)
        df_display = df[["index", "title", "year", "doi", "pdf_url"]].rename(columns={
            "index": "S/N",
            "title": "Title",
            "year": "Year",
            "doi": "DOI",
            "pdf_url": "PDF URL"
        })

        st.dataframe(df_display, use_container_width=True, hide_index=True)

        # PDF download option
        valid_pdfs = [p["pdf_url"] for p in papers if p.get("pdf_url")]
        if valid_pdfs:
            if st.button(f"⬇️ Download All Papers for {author_data['Researcher']}", key=f"btn_{author_data['Researcher']}"):
                try:
                    resp = requests.post(
                        f"{BACKEND_BASE}/download",
                        json={
                            "pdf_urls": valid_pdfs,
                            "author_name": author_data["Researcher"]
                        },
                        timeout=180
                    )
                    if resp.status_code == 200:
                        zip_bytes = resp.content
                        st.download_button(
                            label=f"💾 Save {author_data['Researcher']}.zip",
                            data=BytesIO(zip_bytes),
                            file_name=f"{author_data['Researcher']}.zip",
                            mime="application/zip"
                        )
                    else:
                        st.error(f"❌ Failed to prepare zip: {resp.text}")
                except Exception as e:
                    st.error(f"⚠️ Download error: {e}")
        st.markdown("---")

# ---------------- FOOTER ----------------
st.markdown("""
<div style='text-align:center; color:gray; font-size:0.9em; margin-top:20px;'>
Made with ❤️ by Scholar Downloader AI | Powered by FastAPI + Streamlit
</div>
""", unsafe_allow_html=True)
