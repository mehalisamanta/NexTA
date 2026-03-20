# NexTA
 
**AI-Powered Resume Screening System** — Automated Intelligent Recruitment
 
NexTA is an end-to-end recruitment screening platform that leverages OpenAI to parse, analyze, score, and format candidate resumes. It integrates with Microsoft SSO for authentication and SharePoint for cloud-based document retrieval and storage.
 
---
 
## Overview
 
| Service      | Technology          | Description                                                                                          |
|--------------|---------------------|------------------------------------------------------------------------------------------------------|
| **Backend**  | Python 3.11         | Resume parsing, OpenAI-powered analysis & scoring, Word/PPT report generation, SharePoint integration |
| **Frontend** | Streamlit 1.43      | Interactive web UI with tabs for upload, candidate review & scoring, candidate pool, and analytics     |
 
Both services are containerised with Docker and orchestrated via Docker Compose.
 
---
 
## Repository Structure
 
```
NexTA/
├── backend/                      # Backend service
│   ├── Dockerfile.backend        # Backend Docker image definition
│   ├── dockerignore.txt          # Backend Docker ignore rules
│   ├── nexta-backend.tar         # Prebuilt backend Docker image
│   ├── __init__.py
│   ├── check.py                  # Health-check utility
│   ├── openai_client.py          # OpenAI API client initialisation
│   ├── resume_analysis.py        # AI resume analysis logic
│   ├── resume_formatter.py       # Word document resume formatting
│   ├── ppt_generator.py          # PowerPoint report generation
│   ├── ppt_template_mapper.py    # PPT template field mapping
│   ├── preprocessing.py          # Resume text preprocessing & PII masking
│   ├── scoring.py                # Candidate scoring engine
│   ├── file_handlers.py          # File upload & parsing utilities
│   └── sharepoint.py             # SharePoint file operations
├── frontend/                     # Frontend service
│   ├── Dockerfile.frontend       # Frontend Docker image definition
│   ├── dockerignore.txt          # Frontend Docker ignore rules
│   ├── nexta-frontend.tar        # Prebuilt frontend Docker image
│   ├── __init__.py
│   ├── app.py                    # Streamlit application entry point
│   ├── tabs.py                   # Upload & analytics tab components
│   ├── analysis_tab.py           # Candidate review & scoring tab
│   ├── candidate_pool_tab.py     # Candidate pool management tab
│   └── sso.py                    # Microsoft SSO authentication & login rendering
├── config/                       # Application configuration
│   ├── __init__.py
│   ├── settings.py               # Page config, CSS, JD templates, column mappings
│   └── config.toml               # Streamlit server configuration
├── inputs/                       # Document templates
│   ├── word_template.docx        # Word resume output template
│   └── sample_ppt_template.pptx  # PowerPoint report template
├── testcases/                    # Test suite
│   ├── app_test_ui.py            # UI integration tests
│   ├── test_ppt_generator.py     # PPT generator unit tests
│   └── test_resume_analysis.py   # Resume analysis unit tests
├── .env                          # Environment variables (not committed to Git)
├── .gitignore
├── docker-compose.yml            # Docker Compose orchestration
├── exceptions.py                 # Compatibility shim for legacy packages
├── logo.png                      # Application logo
└── requirements.txt              # Python dependencies
```
 
---
 
## Prerequisites
 
- [Docker](https://docs.docker.com/get-docker/) (v20.10+)
- [Docker Compose](https://docs.docker.com/compose/install/) (v2.0+ or the `docker compose` plugin)
 
---
 
## Getting Started
 
### 1. Clone the Repository
 
```bash
git clone -b docker https://github.com/mehalisamanta/NexTA.git
cd NexTA
```
 
### 2. Configure Environment Variables
 
Copy the example `.env` file (or create one) and fill in your credentials:
 
| Variable                | Description                          |
|-------------------------|--------------------------------------|
| `OPENAI_API_KEY`        | OpenAI API key                       |
| `AZURE_TENANT_ID`       | Azure AD tenant ID (SSO)             |
| `AZURE_CLIENT_ID`       | Azure AD application client ID (SSO) |
| `AZURE_CLIENT_SECRET`   | Azure AD client secret (SSO)         |
| `AZURE_REDIRECT_URI`    | OAuth redirect URI                   |
| `TENANT_ID`             | SharePoint service-account tenant ID |
| `CLIENT_ID`             | SharePoint service-account client ID |
| `CLIENT_SECRET`         | SharePoint service-account secret    |
| `SHAREPOINT_SITE_ID`    | SharePoint site ID                   |
| `SHAREPOINT_DRIVE_ID`   | SharePoint drive ID                  |
| `INPUT_FOLDER_PATH`     | SharePoint input folder path         |
| `OUTPUT_FOLDER_PATH`    | SharePoint output folder path        |
| `JD_FOLDER_PATH`        | SharePoint job-descriptions folder   |
 
### 3. Load Prebuilt Docker Images
 
Prebuilt image tarballs are included in the repository. Load them into your local Docker daemon:
 
```bash
docker load -i backend/nexta-backend.tar
docker load -i frontend/nexta-frontend.tar
```
 
### 4. Start the Application
 
```bash
docker-compose up -d
```
 
### 5. Access the Application
 
| Service  | URL                          |
|----------|------------------------------|
| Frontend | http://localhost:8501         |
| Backend  | http://localhost:8000         |
 
---
 
## Stopping the Application
 
```bash
docker-compose down
```
 
To also remove the associated Docker volumes:
 
```bash
docker-compose down -v
```
 
---
 
## Building Images from Source (Optional)
 
If you prefer to build the Docker images yourself instead of loading the prebuilt tarballs:
 
```bash
docker build -f backend/Dockerfile.backend  -t nexta-backend  .
docker build -f frontend/Dockerfile.frontend -t nexta-frontend .
```
 
Then start the application as usual:
 
```bash
docker-compose up -d
```
 
---
 
## Troubleshooting
 
| Issue | Solution |
|-------|----------|
| **Port already in use** | Stop any service occupying port `8000` or `8501`, or change the host port mapping in `docker-compose.yml` (e.g. `"9000:8000"`). |
| **`docker load` fails** | Ensure the `.tar` files are not corrupted and that Docker Desktop is running. Re-download the repository if needed. |
| **Containers exit immediately** | Run `docker-compose logs -f` to inspect startup errors. Verify that all required environment variables in `.env` are set correctly. |
| **OpenAI / SharePoint errors** | Double-check your API keys and Azure AD credentials in the `.env` file. Ensure the OpenAI key has sufficient quota. |
| **Frontend cannot reach backend** | Both containers must be on the same Docker Compose network. Run `docker-compose ps` to verify both services are running. |
| **Permission denied on `.tar`** | On Linux/macOS, prefix the `docker load` command with `sudo`. |
 
---
 
## Folder Notes
 
- **`inputs/`** — Contains the Word (`.docx`) and PowerPoint (`.pptx`) templates used to generate formatted candidate reports. You can replace these with your own branded templates.
- **`config/`** — Holds application settings (`settings.py`) and Streamlit server configuration (`config.toml`).
- **`testcases/`** — Unit and integration tests. Run them locally with `pytest testcases/`.
- **`.env`** — Must be created manually with your credentials. This file is git-ignored and **should never be committed**.
 
---
 
## License
 
© 2026 NEXTURN. All rights reserved.