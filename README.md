#  Megasus - Autonomous Industrial Supply Network



[Megasus - Autonomous Industrial Supply Network Frontend, Field Service Management and Digital Twin](https://aisn-frontend-prod-80514976508.us-central1.run.app)

[Megasus - Autonomous Industrial Supply Network Frontend Source Code](https://github.com/mikoaro/f-megasus)

![Megasus - Autonomous Industrial Supply Network - 1](./screenshots/0.png)

![Megasus - Autonomous Industrial Supply Network - 2](./screenshots/1.png)

![Megasus - Autonomous Industrial Supply Network - 3](./screenshots/2.png)

![Megasus - Autonomous Industrial Supply Network - 4](./screenshots/3.png)


---

# A.I.S.N. - Autonomous Industrial Self-Healing Network

## 🚀 Overview

**A.I.S.N.** (Autonomous Industrial Self-Healing Network) represents the next generation of industrial operations: moving from **Human Oversight (Mode A)** to **Autonomous Swarm Intelligence (Mode B)**.

This platform demonstrates a "Self-Healing Enterprise" where critical assets—like the **heavy Duty Mining Excavator**—are not just monitored but actively managed by a swarm of AI agents. When a critical fault (e.g., Thermal Runaway) occurs, the system autonomously:

1. **Analyzes Real-Time Telemetry** via WebSocket streams.
2. **Verifies Physical Safety** using Computer Vision simulations.
3. **Executes IoT Safety Protocols** (e.g., Derating engines).
4. **Orchestrates Logistics** by negotiating with Vendor Agents for parts.
5. **Updates Systems of Record** (CRM, ERP, FSM) without human intervention.

---

## 🏗️ Architecture

### 1. High-Level Architecture 

```mermaid
graph TD
    %% Styling - Colorful Boxes
    classDef frontend fill:#2563eb,stroke:#1e40af,stroke-width:2px,color:#fff;
    classDef backend fill:#7c3aed,stroke:#5b21b6,stroke-width:2px,color:#fff;
    classDef db fill:#059669,stroke:#047857,stroke-width:2px,color:#fff;
    classDef ai fill:#db2777,stroke:#be185d,stroke-width:2px,color:#fff;
    classDef ext fill:#d97706,stroke:#b45309,stroke-width:2px,color:#fff;

    subgraph "Client Layer"
        UI[Next.js Frontend / Dashboard]:::frontend
    end

    subgraph "Application Layer (Google Cloud Run)"
        API[FastAPI Backend]:::backend
        Sim[Physics Simulator]:::backend
        AgentCore[Marathon Agent Core]:::ai
        VendorBot[Vendor Agent Swarm]:::ai
    end

    subgraph "Data Layer (Google Cloud SQL)"
        DB[(PostgreSQL)]:::db
        ERP[Inventory Table]:::db
        CRM[Tickets Table]:::db
        FSM[Dispatches Table]:::db
    end

    subgraph "AI Services"
        Gemini[Google Gemini 3 Pro Preview]:::ext
        TTS[Browser Speech API]:::frontend
    end

    %% Connections
    UI -- "WebSocket (Real-Time Data)" --> API
    UI -- "REST (System of Records)" --> API
    API -- "Updates State" --> Sim
    Sim -- "Telemetry Stream" --> API
    API -- "Orchestrates" --> AgentCore
    AgentCore -- "Consults" --> Gemini
    AgentCore -- "Negotiates" --> VendorBot
    AgentCore -- "Persists Data" --> DB
    DB --> ERP
    DB --> CRM
    DB --> FSM
    AgentCore -- "Status Stream" --> UI
    UI -- "Synthesizes Audio" --> TTS

```

### 2. Component Flow 

```text
[ 🖥️ CLIENT: Next.js Dashboard (Blue) ]
       │   ▲
       │   │ (WebSocket: Telemetry & Agent Chat)
       ▼   │
[ ☁️ SERVER: FastAPI Backend (Purple) ]
   │
   ├── [ ⚙️ Physics Engine (Purple) ] <--- (Simulates Thermal Runaway)
   │
   ├── [ 🤖 Marathon Agent (Pink) ] ---> [ 🧠 Google Gemini 3 Pro (Orange) ]
   │       │
   │       └── (Mode B: Auto) ---> [ 🤖 Vendor Agent (Pink) ]
   │
   └── [ 🗄️ Database Layer - Cloud SQL (Green) ]
           ├── 📦 ERP: Inventory
           ├── 🎫 CRM: Tickets
           └── 🚚 FSM: Dispatches

```

---

## ✨ Key Features

* **Dual Operation Modes:**
* **Mode A (Human):** Standard monitoring where operators manually review alerts and tickets.
* **Mode B (Auto):** Autonomous agent swarm that negotiates prices, orders parts, and dispatches technicians in seconds.


* **Real-Time Physics Simulation:** Generates dynamic telemetry (RPM, Torque, Temp) and simulates faults like Thermal Runaway.
* **Multi-Agent Negotiation:** A primary safety agent converses with a secondary vendor agent to procure out-of-stock parts autonomously.
* **System of Record Integration:** Automatically populates Postgres tables for Inventory, Incident Tickets, and Field Service Work Orders.
* **Live Vision HUD:** Simulates computer vision feeds switching between "Clean" and "Hazard" states based on telemetry.
* **Voice-Enabled Ops:** Uses Text-to-Speech to vocalize the negotiation between agents for a transparent "Glass Box" AI experience.

---

## 🛠️ Tech Stack

* **Frontend:** Next.js 16, React, Tailwind CSS, Three.js (Fiber/Drei) for 3D visualization.
* **Backend:** Python 3.14, FastAPI, Uvicorn, WebSockets.
* **Database:** PostgreSQL (Google Cloud SQL), `asyncpg` for async pooling.
* **AI Model:** Google Gemini 3 Pro Preview (via Google GenAI SDK).
* **Infrastructure:** Google Cloud Run, Cloud Build, Docker.

---

## 📋 Prerequisites

1. **Google Cloud Project:** Active project with billing enabled.
2. **APIs Enabled:** Cloud Run Admin API, Cloud Build API, Cloud SQL Admin API.
3. **Google Gemini API Key:** Obtain from [Google AI Studio](https://aistudio.google.com/).
4. **Local Tools:** Python 3.14+, Node.js 18+, Docker (optional).

---

## ⚙️ Configuration & Installation

### 1. Repository Setup

```bash
git clone <your-repo-url>
cd aisn-platform

```

### 2. Backend Setup

Create a `.env.local` file in the `backend` folder:

```env
GEMINI_API_KEY="your_actual_api_key_here"
# Local DB for testing or Cloud SQL Proxy connection string
DB_URL="postgresql://user:password@localhost:5432/megasus_db"

```

Install dependencies:

```bash
cd backend
pip install -r requirements.txt

```

Run locally:

```bash
uvicorn app.main:app --reload --port 8080

```

### 3. Frontend Setup

Create a `.env.local` file in the `frontend` folder:

```env
NEXT_PUBLIC_API_URL="http://localhost:8080"

```

Install dependencies & run:

```bash
cd frontend
npm install
npm run dev

```

*Access the dashboard at `http://localhost:3000*`

---

## 🚀 Deployment Guide (Google Cloud)

This guide assumes you are using **Cloud Build** for CI/CD.

### Step 1: Prepare `cloudbuild.yaml`

Ensure your `cloudbuild.yaml` in the root directory contains the following (replace variables with your project details):

```yaml
steps:
  # Build Docker Image
  - name: 'gcr.io/cloud-builders/docker'
    args: ['build', '-t', 'gcr.io/$PROJECT_ID/aisn-backend:$COMMIT_SHA', '.']
  
  # Push to Container Registry
  - name: 'gcr.io/cloud-builders/docker'
    args: ['push', 'gcr.io/$PROJECT_ID/aisn-backend:$COMMIT_SHA']
  
  # Deploy to Cloud Run
  - name: 'gcr.io/google.com/cloudsdktool/cloud-sdk'
    entrypoint: gcloud
    args:
      - 'run'
      - 'deploy'
      - 'aisn-backend-prod'
      - '--image'
      - 'gcr.io/$PROJECT_ID/aisn-backend:$COMMIT_SHA'
      - '--region'
      - 'us-central1'
      - '--allow-unauthenticated'
      - '--add-cloudsql-instances'
      - 'PROJECT_ID:REGION:INSTANCE_NAME' # Update this!

options:
  logging: CLOUD_LOGGING_ONLY

```

### Step 2: Configure Secrets

1. Go to **Cloud Run** -> Select Service -> **Edit & Deploy New Revision**.
2. **Variables & Secrets** Tab.
3. Add Environment Variable: `GEMINI_API_KEY`.
4. Add Environment Variable: `DB_URL`.
* *Format for Cloud Run:* `postgresql://user:pass@/dbname?host=/cloudsql/PROJECT:REGION:INSTANCE`



### Step 3: Trigger Build

Commit and push your changes to the `main` branch. Cloud Build will automatically pick up the `cloudbuild.yaml` and deploy the application.

---

## 🧪 Usage Instructions

1. **Launch the Dashboard:** Open the deployed URL or localhost.
2. **Observe Normal Ops:** The excavator rotates; telemetry is green.
3. **Trigger Incident:**
* Click **"! TRIGGER FAULT !"**.
* Observe the "Field View" turn red (Thermal Runaway).


4. **Mode A (Human):** The system waits. You see the critical alerts, but no action is taken automatically.
5. **Mode B (Auto):**
* Click **"RESET"**.
* Click **"Mode B: Auto"** in the navbar.
* Click **"! TRIGGER FAULT !"** again.
* **Listen:** The Agents will verbally negotiate the fix.
* **Watch:** The System of Record tables (CRM, ERP, FSM) at the bottom will populate automatically in real-time.



---

## 📜 License

[MIT License](https://www.google.com/search?q=LICENSE)