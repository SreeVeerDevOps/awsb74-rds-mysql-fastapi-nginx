# 🎬 MyFlixDB — FastAPI Movie Management API

Hosted on **AWS EC2** | Backed by **AWS RDS MySQL** | Fronted by **nginx**

---

## Project Structure

```
myflixdb/
├── app/
│   ├── __init__.py
│   ├── main.py          # FastAPI routes
│   ├── database.py      # RDS connection (Secrets Manager + SSM)
│   ├── models.py        # SQLAlchemy ORM model
│   ├── schemas.py       # Pydantic request/response schemas
│   └── crud.py          # DB operations + Faker bulk generator
├── scripts/
│   ├── deploy.sh        # One-shot EC2 deployment
│   ├── myflixdb.service # systemd unit
│   └── nginx.conf       # nginx reverse-proxy config
├── requirements.txt
├── .env.example
└── README.md
```

---

## API Endpoints

| Method | Route | Description |
|--------|-------|-------------|
| `GET` | `/health` | DB connectivity & stats |
| `GET` | `/movies` | List movies (pagination + filters) |
| `GET` | `/movies/{id}` | Get single movie |
| `POST` | `/movies` | Add one movie |
| `POST` | `/movies/bulk` | Add 10/20/30/50/100 movies (Faker or manual) |
| `PUT` | `/movies/{id}` | Update movie fields |
| `DELETE` | `/movies/{id}` | Delete one movie |
| `DELETE` | `/movies?above_id=N` | Delete all movies with ID > N |

Interactive docs available at `/docs` (Swagger UI) and `/redoc`.

---

## Bulk Insert — Increment Options

```bash
# Auto-generate 10 Faker movies
curl -X POST http://your-ec2-ip/movies/bulk \
  -H "Content-Type: application/json" \
  -d '{"count": 10}'

# Available counts: 10, 20, 30, 50, 100

# Insert specific movies manually
curl -X POST http://your-ec2-ip/movies/bulk \
  -H "Content-Type: application/json" \
  -d '{
    "movies": [
      {"title": "Inception", "director": "Nolan", "year_released": 2010, "genre": "Sci-Fi"},
      {"title": "Interstellar", "director": "Nolan", "year_released": 2014, "genre": "Sci-Fi"}
    ]
  }'
```

---

## Local Development

```bash
# 1. Clone and enter directory
cd myflixdb

# 2. Create virtual environment
python3 -m venv venv && source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env — set DB_HOST, DB_USER, DB_PASSWORD for local MySQL
# OR set DATABASE_URL=mysql+pymysql://user:pass@localhost/myflixdb

# 5. Run development server
uvicorn app.main:app --reload --port 8000

# 6. Open Swagger UI
open http://localhost:8000/docs
```

---

## EC2 Deployment

### Prerequisites
- EC2 instance (Amazon Linux 2023 or Ubuntu 22.04)
- IAM role attached with:
  - `secretsmanager:GetSecretValue` on `awsb74-rds-creds`
  - `ssm:GetParameters` on `/b74/db_host` and `/b74/db_port`
- RDS MySQL instance in same VPC
- Security Group: EC2 inbound port 80 open; RDS inbound port 3306 from EC2 SG

### One-Command Deploy

```bash
# SSH into EC2
ssh -i key.pem ec2-user@your-ec2-ip

# Clone repo
git clone https://github.com/yourrepo/myflixdb.git
cd myflixdb

# Deploy
bash scripts/deploy.sh
```

### Manual Steps (if not using deploy.sh)

```bash
# 1. Virtual environment
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Environment (EC2 uses AWS — leave DB_HOST blank)
cp .env.example .env
# Set only: AWS_REGION, SECRET_NAME, SSM_HOST_KEY, SSM_PORT_KEY, DB_NAME

# 3. Systemd service
sudo cp scripts/myflixdb.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable myflixdb
sudo systemctl start myflixdb

# 4. nginx
sudo cp scripts/nginx.conf /etc/nginx/sites-available/myflixdb
sudo ln -s /etc/nginx/sites-available/myflixdb /etc/nginx/sites-enabled/
sudo systemctl restart nginx

# 5. Check
sudo systemctl status myflixdb
curl http://localhost/health
```

---

## AWS Setup Checklist

```
AWS Secrets Manager
  └─ Secret name: awsb74-rds-creds
     └─ {"db_user": "admin", "db_password": "yourpass"}

AWS SSM Parameter Store
  ├─ /b72/db_host  → your-rds.rds.amazonaws.com
  └─ /b72/db_port  → 3306

RDS MySQL
  └─ Database: myflixdb  (tables auto-created on first start)

EC2 IAM Role — inline policy:
  {
    "Version": "2012-10-17",
    "Statement": [
      {"Effect":"Allow","Action":"secretsmanager:GetSecretValue","Resource":"arn:aws:secretsmanager:us-east-1:*:secret:awsb74-rds-creds*"},
      {"Effect":"Allow","Action":"ssm:GetParameters","Resource":["arn:aws:ssm:us-east-1:*:parameter/b72/*"]}
    ]
  }
```

---

## Example API Calls

```bash
BASE="http://ec2-44-193-8-252.compute-1.amazonaws.com"

# Health
curl $BASE/health

# List movies
curl "$BASE/movies?limit=10&director=Nolan"

# Add one movie
curl -X POST $BASE/movies \
  -H "Content-Type: application/json" \
  -d '{"title":"Dune","director":"Denis Villeneuve","year_released":2021,"genre":"Sci-Fi","rating":"PG-13"}'

# Bulk add 50 Faker movies
curl -X POST $BASE/movies/bulk \
  -H "Content-Type: application/json" \
  -d '{"count": 50}'

# Update a movie
curl -X PUT $BASE/movies/1 \
  -H "Content-Type: application/json" \
  -d '{"rating":"R","genre":"Drama"}'

# Delete one movie
curl -X DELETE $BASE/movies/1

# Delete all movies with ID > 200
curl -X DELETE "$BASE/movies?above_id=200"
```
