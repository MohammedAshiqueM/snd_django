

# 📡 SND (Send) — Django Backend

Welcome to the backend of SND ("Send") — a peer-to-peer developer collaboration platform designed to foster knowledge-sharing, mentorship, and real-time learning through virtual sessions, blogs, tech discussions, and more.

This repository contains the Dockerized Django REST + WebSocket backend, handling everything from API communication to real-time WebSocket interactions, background task management with Celery, and secure infrastructure setup with Nginx.


---

## 📖 Story Behind `SND`

The idea for SND was inspired by the movie `In Time`, where time acts as currency. I adapted this into a knowledge-sharing economy — developers earn time by mentoring and spend it to learn new skills, ensuring balanced, mutual growth within a thriving developer community.

❌ Existing solutions like Stack Overflow lack real-time interactive learning.

❌ Mentorship programs are expensive and often inaccessible.

❌ Self-paced learning lacks mentorship and accountability.


SND bridges this gap:

✅ Schedule skill-sharing sessions

✅ Post tech doubts, blogs, and webinars

✅ Track sessions using a time-banking system

✅ Chat with media support via Cloudinary

✅ Conduct video calls using WebRTC

✅ Collaborate via a real-time code editor

✅ Rate, review, and report users

✅ Moderation and admin management

✅ (Premium) Exchange time for money via Razorpay


Designed by a developer, for developers, SND emphasizes real-time collaboration, fair knowledge exchange, and community building.




---

## 📦 Project Structure


```
snd_backend/
│   ├── .env                        # Environment variables
│   ├── asgi.py                     # ASGI config (for Django Channels/WebSockets,using gunicorn)
│   ├── celery.py                   # Celery configuration
│   ├── JwtAuthMiddleWareWs.py      # JWT Auth Middleware for WebSockets
│   ├── settings.py                 # Django settings file
│   ├── setting.py                  # settings
│   ├── urls.py                     # URL routes
│   └── worker.py                   # Celery worker loader
│
├── admin_side/                     # Django app: Admin-side management (users, reports, etc.)
├── user_side/                      # Django app: User operations (sessions, blogs, questions, etc.)
│
├── docker/
├── Dockerfile                      # Backend Dockerfile
├── docker-entrypoint.sh            # Docker container entrypoint script
├── nginx.conf                      # Nginx configuration for reverse proxy
│
├── docker-compose.yml              # Multi-container orchestration (Backend, DB, Nginx)
├── manage.py                       # Django management utility
└── README.md                       # (this file!)

---
```

🌐 Tech Stack

Django REST Framework — API development

Django Channels — WebSockets & real-time features

Celery + Redis — Asynchronous tasks & scheduling

PostgreSQL — Relational database

Docker + Docker Compose — Containerized environment

Nginx — Reverse proxy & static/media handling

Cloudinary — Media storage and CDN

JWT & Google Authentication — Secure token-based access

Razorpay API  — Payment integration

Uvicorn — ASGI


## 📂 Running the Project (Local Docker Setup)

### 📌 1️⃣ Clone the Repository

```bash
git clone https://github.com/MohammedAshiqueM/snd_django
cd snd_django
```

---

### 📌 2️⃣ Create a `.env` File

Add this in the project root:

```bash
# Email Configuration
EMAIL_HOST_USER=your-email
EMAIL_HOST_PASSWORD=your-email-password

# Google OAuth Credentials
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret

# Razorpay Payment Gateway
RAZORPAY_KEY=your-razorpay-key
RAZORPAY_SECRET=your-razorpay-secret-key

# Cloudinary (for image uploads)
CLOUD_NAME=your-cloudinary-name
CLOUD_API=your-cloudinary-api
CLOUD_SECRET=your-cloudinary-secret-key

# App URLs
# NB: Use either 'localhost' or '127.0.0.1' consistently for both URLs in development
FRONTEND_URL=http://127.0.0.1:3000
BACKEND_URL=ws://127.0.0.1:8000

# Django Secret Key
SECRET_KEY=your-django-secret-key

# PostgreSQL Database
POSTGRES_DB=snd
POSTGRES_USER=postgres
POSTGRES_PASSWORD=12345
POSTGRES_HOST=db
POSTGRES_PORT=5432
```

---

### 📌 3️⃣ Build and Run with Docker Compose

```bash
docker-compose up --build
```

- Backend runs at: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- WebSocket runs at: `ws://127.0.0.1:8000/`
- Nginx  at: [http://127.0.0.1](http://127.0.0.1)

---

## 🐳 Docker Images

- 📦 **Docker Hub**: [mohammedashique/snd-backend-web](https://hub.docker.com/u/mohammedashique)

```bash
docker pull mohammedashique/snd-backend-web
docker run --env-file .env -d -p 8000:8000 mohammedashique/snd-backend-web
```

---

## 🔄 Real-Time WebSockets with JWT(HttpOnly Cookie Based)

SND uses **Django Channels** with a custom **JWTAuthMiddlewareWs** to authenticate WebSocket connections securely.
Instead of passing JWTs via query strings (which can be insecure), SND leverages **HttpOnly cookies** for token storage and authentication.
Clients connect via:

```ws
ws://127.0.0.1:8000/ws/room-name/
```
---

## 🎛️ Background Tasks with Celery

Celery is integrated for handling asynchronous tasks — email notifications, session follow-ups.

To run the worker:

```bash
docker-compose exec backend celery -A snd_backend worker --loglevel=info
```

---

# 🛡️ Creating a Django Superuser (Without Docker)
If you're running the project locally (without Docker) and need to create a Django superuser to access the admin panel:

📌 Steps:
Activate your virtual environment (if using one)
```
source venv/bin/activate    # Mac/Linux
.\venv\Scripts\activate     # Windows
```

Run Django’s createsuperuser command

```
python manage.py createsuperuser
```

Follow the prompts:

Enter a Username

Enter an Email address

Enter a Password

✅ Once created, you can log into the Django admin panel at:

- http://127.0.0.1:8000/admin/ (default Django admin)

- http://127.0.0.1:3000/dashboard/ (custom admin if you're using the [snd_react frontend](https://github.com/MohammedAshiqueM/snd_react))

📌 For Docker Users:
If you're using Docker Compose, you need to run the command inside the running backend container:

```
docker-compose exec backend python manage.py createsuperuser
```
Then follow the same prompts in your terminal.

## 📎 Related Repositories

- 🎨 **Frontend (React)**: [snd_react](https://github.com/MohammedAshiqueM/snd_react)
- 🐳 **Docker Hub Repo**: [mohammedashique/snd-backend-web](https://hub.docker.com/u/mohammedashique)

---

## 📖 Future Plans

- ✅ Social media-style friend recommendations
Implementing graph-based link prediction algorithms for developer connections, inspired by Social Network Analysis (SNA) techniques. This will allow the system to suggest potential collaborators and mentors based on mutual connections, shared interests, and activity patterns.


---

## 🙌 Credits & Thanks

Built with ❤️ by Mohammed Ashique

Tested and reviewed by industrial experts and Brocamp peers.

---

## 📑 License

This project is licensed under the [MIT License](LICENSE).

## 📧 Contact

For queries, feedback, or collaboration:  
📬 [Connect on LinkedIn](https://www.linkedin.com/in/mohammad-ashique/)

---
