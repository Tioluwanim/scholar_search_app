# Scholar Search App

**Scholar Search App** is a web application that allows users to search for multiple authors or researchers and retrieve their research papers from Google Scholar. The app is intended to simplify literature retrieval for students, researchers, and anyone conducting academic reviews.

> ⚠️ Note: Due to Google Scholar's anti-bot measures, automatic PDF downloads of paywalled papers are **not guaranteed**. Currently, the app provides paper titles and links where available.

---

## 💡 Overview

Performing literature searches for multiple authors manually is time-consuming. Scholar Search App aims to automate this process: you provide a list of author names, and the app searches Google Scholar, returning publications and links for download where possible.

The app is ideal for **researchers, students, and educators** needing quick access to papers, with the added benefit of being open-source for contributions and improvements.

---

## 🛠️ Features

- Accept multiple researcher/author names as input  
- Search Google Scholar automatically (via Python libraries)  
- Aggregate results: list of papers per author  
- Provide links to papers (PDFs or source pages)  
- Simple UI for input and result display  
- Modular backend and frontend structure  

---

## 🧑‍💻 Tech Stack

- **Backend:** Python (FastAPI or Flask)  
- **Frontend:** streamlit
- **Data Handling:** Python libraries (`scholarly`, `requests`, `BeautifulSoup`)  
- **Version Control:** Git / GitHub  

---

## 📁 Repository Structure

```

scholar_search_app/
│
├── backend/            # Backend server code (search logic, data parsing)
├── frontend/           # Frontend code (UI for input and displaying results)
├── data/               # Optional: store example input files or results
├── tests/              # Unit tests or sample scripts
├── requirements.txt    # Python dependencies
└── README.md           # ← this file

````

---

## 🚀 Installation & Running Locally

1. **Clone the repository**
```bash
git clone https://github.com/Tioluwanim/scholar_search_app.git
cd scholar_search_app
````

2. **Set up a Python virtual environment**

```bash
python -m venv venv
source venv/bin/activate  # Mac/Linux
venv\Scripts\activate     # Windows
```

3. **Install dependencies**

```bash
pip install -r backend/requirements.txt
```

4. **Run the backend server**

```bash
cd backend
python app.py   # Or your backend entry-point
```

5. **Open the frontend**

* If static: open `frontend/index.html` in a browser
* If served via backend: visit the URL shown in terminal (`http://localhost:8000` or similar)

---

## ✅ Usage

1. Enter a list of researcher or author names (comma-separated or newline-separated).
2. Submit the search request.
3. View aggregated paper titles and links.
4. Download available PDFs manually or follow the provided links.

> Note: Automatic PDF downloads of paywalled papers are **not guaranteed**.

---

## 🐛 Current Limitation / Problem

* Google Scholar **blocks automated downloads** for many papers.
* Some PDFs may be behind paywalls and cannot be accessed directly.

---

## 📚 How to Contribute / Help Fix

We welcome contributions to improve the app. Here are ways you can help:

* Fix or improve PDF download functionality
* Integrate alternative sources like **arXiv, PubMed, or CORE** for open-access papers
* Improve search accuracy for authors with common names
* Add caching or a local database to avoid repeated queries
* Enhance frontend UI/UX for better usability
* Add unit tests or error handling for failed searches

**Steps to Contribute:**

1. Fork the repository
2. Create a new branch:

```bash
git checkout -b feature/YourFeature
```

3. Make your changes and commit with descriptive messages
4. Push to your fork and submit a **Pull Request**

Please open issues for bug reports or feature requests.

---

## 📄 License

This project is licensed under the **MIT License**. See the `LICENSE` file for details.

---

## 🎯 Author / Maintainer

* **Tioluwanimi Adeagbo** – maintainer of this project
* Feel free to contact via GitHub issues or Pull Requests for questions or suggestions

---

```

---

✅ **What’s different in this README:**  
- Clearly explains the **current limitation** (Google Scholar blocking downloads)  
- Encourages contributors to **help fix the problem or enhance the app**  
- Provides **installation, usage, and contribution instructions**  
- Sets expectations for users about automatic PDF downloads  

---

If you want, I can **also rewrite it with a “How to fix the Scholar blocking” section** with starter code for using `scholarly` and open-access APIs, so contributors can jump in and implement fixes quickly.  

Do you want me to do that?
```
