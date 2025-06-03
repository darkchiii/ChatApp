# Chat Backend Project with Redis, JWT, Throttling, Celery & Django REST

## Purpose

This project aims to deliver a fully working 1:1 chat backend using modern web development tools and principles. The goal is to become comfortable with:
- Deepening Django REST Framework (DRF) knowledge through **custom scalable features**
- Using **Redis** for caching and request throttling
- Implementing **JWT-based authentication**
- Gaining hands-on experience with **asynchronous processing and queuing (Celery)**
- Writing comprehensive **tests** for logic-heavy API flows
- Understanding architectural decisions around **synchronous vs. asynchronous flows**
- Eventually deploying the application using **Docker**
- Write clean, well-tested backend code for APIs

What I want to deeply understand during the process:
1. **How to break down an app** into backend, database, API, queue, and caching layers
2. **How data flows** through a system: `request → controller → DB → response`
3. **synchronous vs. asynchronous flow**
   - When and where queues (e.g., Celery + RabbitMQ) come in
4. When to **scale horizontally vs. vertically**

## Tools & Concepts to explore

| Concept                    |                                                      |
|---------------------------|----------------------------------------------------------------------|
| **Redis**                 | Fast in-memory caching and custom rate limiting                      |
| **RabbitMQ / Kafka**      | Queue systems for background processing (e.g., async email jobs)      |
| **Load balancers / Nginx**| Routing and distributing traffic (planned for future)                |
| **Throughput & Latency**  | Performance metrics for backend efficiency                          |
| **Rate Limiting**         | Protects from abuse, preserves performance                          |
| **Connection Pools**      | Efficient DB connections under load                                  |
| **Read Replicas**         | Scaling reads separately from writes (optional for later)            |

---

## Completed Features

- **JWT Authentication**
  Implemented using `rest_framework_simplejwt`. Users are authenticated via token-based login.

- **Chat Room Logic (1:1 only)**
  Users can create or retrieve private chat rooms with each other. Duplicate rooms are avoided automatically.

- **Messaging System**
    Messages are stored and served per room. Serializer and logic ensure valid sender and receiver.

- **Message Caching (last 50)**
  Redis stores the 50 most recent messages per room. On cache miss, the data is fetched from the database and stored in Redis.

### Redis-based Throttling

- Implemented a **sliding window rate limiting algorithm** via a custom `BaseThrottle` class
- Users are limited to **3 messages every 5 seconds**
- Redis sorted sets (`zadd`, `zremrangebyscore`, `zcard`) are used to manage per-user rate data

### Testing

- Basic test coverage for chat room creation, message sending, and throttling logic
- Includes edge cases like unauthenticated users and invalid room access

## Planned Features

- RabbitMQ or Redis Queue (via Celery) for processing async jobs like notifications (currently working on it)
- Admin panel for monitoring chat activity and system health
- Logging message delivery latency and user behavior
- Swagger or Redoc documentation
- Dockerized deployment with Compose

Feel free to check out the `throttling`, `views`, and `tests` modules inside chat directory for more implementation details.

README will be updated as the project progresses.
