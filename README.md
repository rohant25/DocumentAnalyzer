# Insurance Document Analyzer (LLM-Powered) - Technical Documentation

## Overview

This application is a **Streamlit-based web tool** that accepts `.pdf`, `.docx`, and `.txt` insurance-related documents, analyzes them using **Google Gemini (Generative AI)**, and detects:

* Typographical errors
* Name and date inconsistencies
* Domain-specific policy issues

It produces an Excel report listing all identified issues per document. The app is fully containerized and deployed to **Google Cloud Run** with CI/CD configured via **Cloud Build**.

---

## Project Structure

```
insurance-document-analyzer/
├── app.py                    # Main Streamlit app
├── requirements.txt         # Python dependencies
├── Dockerfile               # Build instructions for container
├── cloudbuild.yaml          # CI/CD pipeline definition
├── .gitignore               # Git exclusions
└── .streamlit/
    └── secrets.toml         # (Used locally, not committed)
```

---

## Features

* Upload and analyze multiple insurance documents
* Uses Gemini 1.5 Flash via `google.generativeai`
* Results downloadable as `.xlsx`
* Secure API key access via **Secret Manager**
* CI/CD pipeline for automated build and deploy

---

## Streamlit App (`app.py`)

### Major Components

#### File Handling

```python
uploaded_files = st.file_uploader("Upload Documents", type=["pdf", "docx", "txt"], accept_multiple_files=True)
```

* Extracts text using PyMuPDF (`fitz`), `docx`, or native read depending on file type.

#### LLM Integration

```python
model = genai.GenerativeModel("gemini-1.5-flash")
response = model.generate_content(prompt)
```

* Uses Google Generative AI with dynamic prompt injection.

#### Error Parsing

* Gemini output is parsed for structured error attributes: `Line Number`, `Error Type`, `Error Description`, `Suggested Change`.

#### Output

* DataFrame shown in-app
* Downloadable Excel report using `st.download_button`

---

## Prompt Engineering

Prompt is structured with:

* Specific error types
* Required output format
* Full document text

This ensures consistent and parseable output from Gemini.

---

## Security & Secrets

### Secret Manager

* Secret Name: `gemini-api-key`
* Accessed in code:

```python
from google.auth import default
_, project_id = default()
```

```python
name = f"projects/{project_id}/secrets/gemini-api-key/versions/latest"
```

* Uses default Cloud Run service account (or custom) with IAM role `Secret Manager Secret Accessor`

---

## Dockerfile

```dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install -r requirements.txt
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

---

## Cloud Build (CI/CD)

`cloudbuild.yaml` deploys on code push:

```yaml
options:
  logging: CLOUD_LOGGING_ONLY
steps:
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'us-central1-docker.pkg.dev/$PROJECT_ID/streamlit-repo/insurance-analyzer', '.']

  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'us-central1-docker.pkg.dev/$PROJECT_ID/streamlit-repo/insurance-analyzer']

  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    entrypoint: gcloud
    args:
      [
        'run', 'deploy', 'insurance-analyzer',
        '--image', 'us-central1-docker.pkg.dev/$PROJECT_ID/streamlit-repo/insurance-analyzer',
        '--region', 'us-central1',
        '--platform', 'managed',
        '--allow-unauthenticated',
        '--port', '8501'
      ]
```

---

## IAM Permissions

To allow secret access and deployment:

```bash
gcloud projects add-iam-policy-binding [PROJECT_ID] \
  --member="serviceAccount:[PROJECT_NUMBER]@cloudbuild.gserviceaccount.com" \
  --role="roles/iam.serviceAccountUser"

gcloud projects add-iam-policy-binding [PROJECT_ID] \
  --member="serviceAccount:[PROJECT_NUMBER]-compute@developer.gserviceaccount.com" \
  --role="roles/secretmanager.secretAccessor"
```

---

## Deployment Summary

1. Push to GitHub
2. Cloud Build triggers
3. Builds Docker image
4. Pushes to Artifact Registry
5. Deploys to Cloud Run

---

## Future Enhancements

* Add authentication (OAuth / Firebase Auth)
* Add retry/fallback logic for LLM failures
* Add user-uploaded templates or form validations
* Enable monitoring via Cloud Logging dashboards

---

## Contact / Owner

* Developer: Rohan
* Platform: Google Cloud Platform (Cloud Run, Secret Manager, Cloud Build)
* LLM: Gemini 1.5 Flash (via google.generativeai)
