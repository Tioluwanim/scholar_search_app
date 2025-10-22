import streamlit as st
import requests
import pandas as pd
from io import BytesIO

st.set_page_config(page_title="Scholar Downloader", page_icon="📚", layout="wide")

BACKEND_BASE = "https://scholar-search-app-backend.onrender.com"

st.title("📘 Scholar Downloader")
st.markdown("Fetch and download research papers from **Semantic Scholar**, **OpenAlex**, and **Google Scholar**.")

names_input = st.text_area("Enter researcher names (one per line):")
uploaded = st.file_uploader("📤 Upload names file (CSV, TXT, XLSX):", type=["csv", "txt", "xlsx"])

def extract_names(file):
    try:
        if file.name.endswith(".csv"):
            return pd.read_csv(file).iloc[:, 0].dropna().tolist()
        if file.name.endswith(".xlsx"):
            return pd.read_excel(file).iloc[:, 0].dropna().tolist()
        if file.name.endswith(".txt"):
            return [n.strip() for n in file.read().decode().splitlines() if n.strip()]
    except Exception as e:
        st.error(f"Error reading file: {e}")
        return []
    return []

file_names = extract_names(uploaded) if uploaded else []
all_names = list(dict.fromkeys([n.strip() for n in names_input.split("\n") if n.strip()] + file_names))

if "results" not in st.session_state:
    st.session_state.results = None

if st.button("🔍 Search Papers") and all_names:
    with st.spinner("Searching papers across multiple sources..."):
        try:
            resp = requests.post(f"{BACKEND_BASE}/search", json={"names": all_names}, timeout=600)
            if resp.status_code == 200:
                st.session_state.results = resp.json().get("data", [])
            else:
                st.error(f"Error: {resp.text}")
        except Exception as e:
            st.error(f"⚠️ Failed to connect: {e}")

if st.session_state.results:
    for author_data in st.session_state.results:
        st.subheader(f"👤 {author_data['Researcher']}")
        if "Error" in author_data:
            st.warning(author_data["Error"])
            continue
        df = pd.DataFrame(author_data["papers"])
        if df.empty:
            st.info("No papers found.")
            continue
        st.dataframe(df[["index", "title", "year", "doi", "pdf_url"]], hide_index=True)
        valid_pdfs = [p["pdf_url"] for p in author_data["papers"] if p.get("pdf_url")]
        if valid_pdfs and st.button(f"⬇️ Download All for {author_data['Researcher']}", key=author_data["Researcher"]):
            try:
                r = requests.post(f"{BACKEND_BASE}/download", json={"pdf_urls": valid_pdfs, "author_name": author_data["Researcher"]}, timeout=300)
                if r.status_code == 200:
                    st.download_button(f"💾 Save {author_data['Researcher']}.zip", data=BytesIO(r.content),
                                       file_name=f"{author_data['Researcher']}.zip", mime="application/zip")
                else:
                    st.error("Download failed.")
            except Exception as e:
                st.error(f"Error downloading: {e}")
        st.divider()

st.markdown("<hr><center style='color:gray'>Made with ❤️ by Scholar Downloader AI</center>", unsafe_allow_html=True)
