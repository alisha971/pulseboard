# 🌩️ PulseBoard

### **A Distributed Team Productivity & Analytics Platform**

PulseBoard is a full-stack, event-driven analytics system that tracks team productivity in real time.
It demonstrates how modern systems decouple **event ingestion** from **analytics processing** using queues, background workers, caching, and microservices.

---

# 🚀 Features

### ✔ Instant Event Ingestion

Events are accepted immediately without waiting for analytics.

### ✔ Asynchronous Background Processing

A Python worker consumes queued events and updates aggregated metrics.

### ✔ Real-Time Dashboard

A React + Chart.js dashboard visualizes team activity trends.

### ✔ Redis Caching Layer

Ensures fast dashboard response times with cached analytics.

### ✔ Full Microservice Architecture

4 custom services + 3 infrastructure services orchestrated via Docker Compose.

### ✔ Cloud-Deployable

Easily deployable on a single EC2 instance using Docker.

---

# 🏗️ Architecture Overview

PulseBoard uses **7 total containers**:

```
+---------------------------+        +-------------------------+
|  pulse-frontend (React)   |<------>|  pulse-dashboard-api    |
|     Port 3000             |        |  (FastAPI + Redis)      |
+---------------------------+        +-------------------------+
                                              |
                                              v
                                     +-----------------+
                                     |   Redis Cache   |
                                     +-----------------+

     +------------------------------+
     |     pulse-activity-svc       |
     |   Node.js Event Ingestion    |
     |         Port 3001            |
     +------------------------------+
                  |
                  v
       +-----------------------+
       |   RabbitMQ Queue     |
       +-----------------------+
                  |
                  v
     +------------------------------+
     |   pulse-analytics-svc       |
     |  Python Background Worker   |
     +------------------------------+
                  |
                  v
            +-------------+
            |  Postgres   |
            +-------------+
```

---

# 🔄 Event Flow

## **1️⃣ Write Path (Submitting a New Event)**

1. Client sends an event to the Activity API.
2. The service:

   * Stores the event in Postgres
   * Publishes the event to RabbitMQ
3. Returns success instantly → **non-blocking**

---

## **2️⃣ Read Path (Dashboard Rendering)**

1. React dashboard fetches analytics from the Dashboard API.
2. API checks Redis cache:

   * HIT → returns cached results
   * MISS → queries Postgres → stores to cache

---

# 🛠️ Technology Stack

| Layer         | Tech                                 |
| ------------- | ------------------------------------ |
| Frontend      | React (Vite), Chart.js, Tailwind CSS |
| APIs          | Node.js (Express), Python (FastAPI)  |
| Worker        | Python                               |
| Queue         | RabbitMQ                             |
| Database      | PostgreSQL                           |
| Cache         | Redis                                |
| Web Server    | Nginx                                |
| Orchestration | Docker & Docker Compose              |
| Cloud         | AWS EC2 (optional deployment)        |

---

# 📦 Service Overview

### **Frontend (React + Nginx)**

* Port: 3000
* Serves UI & proxies API requests

### **Activity Service (Node.js)**

* Event ingestion API
* Publishes to RabbitMQ

### **Analytics Worker (Python)**

* Background message consumer
* Updates aggregated metrics

### **Dashboard API (FastAPI)**

* Reads analytics
* Uses Redis for caching

### **Infrastructure Services**

| Service    | Purpose                           |
| ---------- | --------------------------------- |
| PostgreSQL | Stores raw events + daily metrics |
| Redis      | High-speed cache                  |
| RabbitMQ   | Asynchronous messaging            |

---

# ▶️ Local Development

### **Requirements**

* Docker Desktop
* Git

### Clone the repository

```bash
git clone https://github.com/alisha971/pulseboard.git
cd pulseboard
```

### Start all services

```bash
cd infra
docker compose up --build
```

### Access the system

| Component     | URL                                                                                    |
| ------------- | -------------------------------------------------------------------------------------- |
| Frontend      | [http://localhost:3000](http://localhost:3000)                                         |
| Activity API  | [http://localhost:3001/api/activity](http://localhost:3001/api/activity)               |
| Dashboard API | [http://localhost:8000/api/metrics/summary](http://localhost:8000/api/metrics/summary) |
| RabbitMQ UI   | [http://localhost:15672](http://localhost:15672)                                       |
| Postgres      | localhost:5555                                                                         |

⚠️ Default credentials are NOT included here.
Use your own `.env` or environment variables.

---

# 🧪 Test an Event (Postman)

POST →

```
http://localhost:3001/api/activity
```

Body:

```json
{
  "user": "alex@example.com",
  "type": "task_created"
}
```

---

# 🌐 EC2 Deployment (Optional)

PulseBoard can be deployed on a single EC2 instance using Docker.

### Steps Summary

1. Launch EC2 instance
2. Install Docker & Docker Compose
3. Clone repo
4. Run:

```
docker compose up -d
```

### Access:

```
http://<EC2-PUBLIC-IP>:3000
```

---

# 🔁 Updating the Deployed Version

When you improve the project locally and want to push changes to EC2:

```bash
ssh -i <your-key.pem> ec2-user@<your-ip>
cd ~/pulseboard
git pull
cd infra
docker compose down
docker compose up --build -d
```

New features go live instantly.

---

# 📁 Project Structure

```
pulseboard/
│
├── frontend/                   # React + Nginx
├── services/
│   ├── activity-service        # Node.js
│   ├── analytics-service       # Python worker
│   └── dashboard-api           # FastAPI backend
│
├── db/
│   └── schema.sql              # DB schema
│
└── infra/
    └── docker-compose.yml      # Entire environment
```
