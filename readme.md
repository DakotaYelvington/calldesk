# CallDesk 📞
> Automatic call logging and job dispatch for trade businesses.

Built for garage door, plumbing, HVAC, and electrical businesses 
that are tired of managing 30+ calls a day on sticky notes.

---

## The Problem
Small trade businesses get flooded with calls daily. Most owners are:
- Writing call details on paper or in their notes app
- Manually texting employees job details
- Missing calls because they're already on a job
- Wasting time on spam and sales calls

## The Solution
CallDesk automatically logs every incoming call, filters out spam, 
and lets you assign jobs to employees in one tap — all from your phone.

---

## Features
- 📋 Automatic call logging via Twilio
- 🚫 Spam filtering — known spam numbers auto blocked
- 👤 Contact recognition — personal and employee calls handled separately
- 👷 One tap dispatch — assign jobs to employees from the dashboard
- 📱 SMS notifications — employees get job details automatically
- 📊 Live dashboard — see all calls and statuses in real time
- 🔐 JWT authentication — secure login system

---

## Tech Stack
| Layer | Technology |
|-------|-----------|
| Backend | Python, FastAPI |
| Database | PostgreSQL |
| Phone/SMS | Twilio |
| Frontend | HTML, CSS, JavaScript |
| Auth | JWT tokens, bcrypt |
| Hosting | Railway + Netlify |

---

## Project Structure
calldesk/
├── main.py          # FastAPI backend
├── dashboard.html   # Owner dashboard
├── login.html       # Login page
├── style.css        # Dashboard styles
├── login.css        # Login styles
├── .env             # Environment variables
└── README.md        # You are here

---

## Getting Started

### Prerequisites
- Python 3.10+
- PostgreSQL
- Twilio account
- OpenAI API account

### Installation

1. Clone the repository
```bash
git clone https://github.com/DakotaYelvington/calldesk.git
cd calldesk
```

2. Install dependencies
```bash
pip install fastapi uvicorn sqlalchemy psycopg2-binary python-dotenv twilio python-jose passlib bcrypt slowapi
```

3. Set up your .env file

DATABASE_URL=postgresql://user:password@localhost/calldesk
TWILIO_ACCOUNT_SID=your_sid
TWILIO_AUTH_TOKEN=your_token
TWILIO_PHONE_NUMBER=your_number
FORWARD_TO=your_phone
SECRET_KEY=your_secret_key
API_KEY=your_api_key

4. Run the app
```bash
python -m uvicorn main:app --reload
```

---

## API Endpoints

### Auth
| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/register` | Create a new account |
| POST | `/login` | Login and get token |

### Calls
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/calls` | Get all calls |
| GET | `/calls/summary` | Get stat counts |
| POST | `/calls` | Create a call manually |
| PUT | `/calls/{id}/assign` | Assign to employee |
| PUT | `/calls/{id}/mark-spam` | Mark as spam |
| POST | `/incoming-call` | Twilio webhook |

### Filtered Numbers
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/filtered-numbers` | Get all filtered numbers |
| POST | `/filtered-numbers` | Add a number rule |
| DELETE | `/filtered-numbers/{id}` | Remove a number |

### Employees
| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/employees` | Get all employees |
| POST | `/employees` | Add an employee |

---

## Roadmap
- [x] Automatic call logging
- [x] Spam filtering
- [x] Employee dispatch
- [x] SMS notifications
- [x] JWT authentication
- [x] Styled dashboard
- [ ] Deploy to production
- [ ] PWA support
- [ ] Multi business support
- [ ] Stripe billing
- [ ] Mobile app

---

## Why I Built This
My buddy runs a garage door repair business and was getting 
30+ calls a day with no system to manage them. I built CallDesk 
to solve that specific problem — and realized every trade business 
in the country has the exact same pain.

---

## Author
Built by Dakota Yelvington
- GitHub: [@DakotaYelvington](https://github.com/DakotaYelvington)

---

## License
All Rights Reserved - Dakota Yelvington 2026