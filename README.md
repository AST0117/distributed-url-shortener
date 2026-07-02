# Distributed URL Shortener

A horizontally-scalable URL shortening service deployed on AWS, built with Flask, Redis, and MySQL. Features Base62 key generation, Redis-backed caching, token bucket rate limiting, and load-balanced deployment across multiple EC2 instances.

---

## Architecture

```
Client
  │
  ▼
Application Load Balancer (AWS ALB)
  │              │
  ▼              ▼
EC2 Instance 1  EC2 Instance 2
(Flask + Redis) (Flask + Redis)
  │
  ▼
AWS RDS MySQL (shared persistent store)
```

| Component       | Technology                          |
|----------------|--------------------------------------|
| API             | Flask + Gunicorn (4 workers)        |
| ID Generation   | Base62 encoding on auto-increment ID |
| Cache           | Redis (LRU, TTL = 1 hour)           |
| Rate Limiter    | Token bucket via Redis               |
| Database        | AWS RDS MySQL 8.0 (ap-south-1)      |
| Compute         | 2× EC2 t3.micro, Dockerized         |
| Load Balancer   | AWS Application Load Balancer        |

---

## API Endpoints

### POST `/shorten`
Shorten a long URL.

**Request:**
```bash
curl -X POST http://<host>/shorten \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'
```

**Response:**
```json
{
  "short_code": "1",
  "short_url": "/1"
}
```

---

### GET `/<short_code>`
Redirects to the original URL (302).

```bash
curl -v http://<host>/1
# HTTP/1.1 302 FOUND
# Location: https://example.com
```

---

### GET `/stats/<short_code>`
Returns metadata for a shortened URL.

```bash
curl http://<host>/stats/1
```

**Response:**
```json
{
  "short_code": "1",
  "long_url": "https://example.com",
  "created_at": "2026-07-02T07:28:58",
  "click_count": 5
}
```

---

## Rate Limiting

All `/shorten` requests are rate-limited per IP (or `X-API-Key` header) using a **token bucket algorithm**:
- Bucket capacity: 10 requests
- Refill rate: 1 token/second
- Exceeding the limit returns `HTTP 429 Too Many Requests`

---

## Project Structure

```
distributed-url-shortener/
├── app/
│   ├── __init__.py          # App factory, DB init
│   ├── main.py              # Entry point
│   ├── api/
│   │   ├── __init__.py
│   │   └── routes.py        # API endpoints + rate limiter decorator
│   ├── models/
│   │   ├── __init__.py
│   │   └── url.py           # SQLAlchemy URL model
│   └── services/
│       ├── __init__.py
│       ├── encoder.py       # Base62 encode/decode
│       ├── cache.py         # Redis cache wrapper
│       └── rate_limiter.py  # Token bucket implementation
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

---

## Running Locally (Docker Compose)

### Prerequisites
- Docker + Docker Compose
- Git

### Steps

**1. Clone the repo:**
```bash
git clone https://github.com/AST0117/distributed-url-shortener.git
cd distributed-url-shortener
```

**2. Set up environment variables:**
```bash
cp .env.example .env
```

Edit `.env`:
```
MYSQL_HOST=mysql           # use 'mysql' for local Docker, or RDS endpoint for AWS
MYSQL_USER=root
MYSQL_PASSWORD=rootpass
MYSQL_DB=urlshortener
REDIS_HOST=redis
REDIS_PORT=6379
```

**3. Start all services:**
```bash
docker compose up --build
```

This starts:
- Flask app on port `5000`
- MySQL on port `3306`
- Redis on port `6379`

**4. Test it:**
```bash
# Shorten a URL
curl -X POST http://localhost:5000/shorten \
  -H "Content-Type: application/json" \
  -d '{"url": "https://example.com"}'

# Follow the redirect
curl -v http://localhost:5000/1

# Check stats
curl http://localhost:5000/stats/1
```

---

## Live AWS Deployment

The service is deployed on AWS in `ap-south-1` (Mumbai):

**Live ALB endpoint:**
```
http://url-shortener-alb-492026041.ap-south-1.elb.amazonaws.com
```

**Test the live deployment:**

```bash
# Shorten a URL
curl -X POST http://url-shortener-alb-492026041.ap-south-1.elb.amazonaws.com/shorten \
  -H "Content-Type: application/json" \
  -d '{"url": "https://your-long-url.com"}'

# Follow the redirect (use the short_code from above)
curl -v http://url-shortener-alb-492026041.ap-south-1.elb.amazonaws.com/<short_code>

# Check click stats
curl http://url-shortener-alb-492026041.ap-south-1.elb.amazonaws.com/stats/<short_code>
```

---

## AWS Infrastructure Setup (Reference)

### Prerequisites
- AWS account + IAM user with `AdministratorAccess`
- AWS CLI configured (`aws configure`)

### RDS MySQL
```bash
aws rds create-db-instance \
  --db-instance-identifier url-shortener-db \
  --db-instance-class db.t3.micro \
  --engine mysql --engine-version 8.0 \
  --master-username admin \
  --master-user-password <password> \
  --allocated-storage 20 \
  --db-name urlshortener \
  --publicly-accessible \
  --no-multi-az --no-deletion-protection \
  --region ap-south-1
```

### EC2 Instances
```bash
aws ec2 run-instances \
  --image-id ami-040875d8447f6c9c0 \
  --instance-type t3.micro \
  --key-name url-shortener-key \
  --security-group-ids <ec2-sg-id> \
  --count 1 --region ap-south-1
```

On each EC2 instance:
```bash
sudo yum install -y docker git
sudo service docker start
# Install Docker Compose v2 + buildx (see README setup section)
git clone https://github.com/AST0117/distributed-url-shortener.git
cd distributed-url-shortener
# Create .env with RDS endpoint
docker compose up --build -d
```

### Application Load Balancer
```bash
aws elbv2 create-load-balancer \
  --name url-shortener-alb \
  --subnets <subnet-1> <subnet-2> <subnet-3> \
  --security-groups <alb-sg-id> \
  --region ap-south-1
```

---

## Design Decisions

**Why Base62 over MD5/SHA hash?**
Base62 encoding of the auto-increment DB ID guarantees zero collisions by construction. Hash-based approaches require collision detection and retry logic, adding latency and complexity.

**Why token bucket over fixed window rate limiting?**
Token bucket allows short bursts (up to bucket capacity) while enforcing a long-term average rate. Fixed window counting resets abruptly and allows 2× burst at window boundaries.

**Why Redis for both cache and rate limiter?**
Redis atomic operations (`HSET`, `INCR`, `EXPIRE`) make it safe for concurrent rate limit checks across multiple Gunicorn workers without race conditions. Using one Redis instance for both concerns reduces infrastructure complexity.

**Why RDS over containerized MySQL?**
RDS provides automated backups, point-in-time recovery, and managed failover — critical for a persistent URL store where data loss means broken links. It also decouples the database lifecycle from the application container.

---

## Load Testing

```bash
# Install Apache Bench
sudo apt-get install apache2-utils

# Benchmark the shorten endpoint (100 requests, 10 concurrent)
ab -n 100 -c 10 -p post.json -T application/json \
  http://url-shortener-alb-492026041.ap-south-1.elb.amazonaws.com/shorten
```

Where `post.json` contains:
```json
{"url": "https://example.com"}
```

---

## Tech Stack

- **Backend:** Python 3.11, Flask, Flask-SQLAlchemy, Gunicorn
- **Cache / Rate Limiter:** Redis 7
- **Database:** MySQL 8.0 (AWS RDS)
- **Containerization:** Docker, Docker Compose
- **Cloud:** AWS EC2, RDS, ALB (ap-south-1)
- **Version Control:** Git, GitHub