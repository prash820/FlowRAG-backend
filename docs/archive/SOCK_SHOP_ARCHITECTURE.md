# Sock Shop Microservices Architecture

**Project:** Weaveworks Sock Shop Demo Application
**Purpose:** Cloud-native microservices reference architecture
**Source:** https://microservices-demo.github.io/

---

## Overview

Sock Shop is a demonstration microservices application that simulates an e-commerce site selling socks. It showcases cloud-native architecture patterns, polyglot microservices, and modern DevOps practices.

---

## Services Architecture

### 7 Core Microservices

#### 1. **Front-End Service** (JavaScript/Node.js)
- **Language:** JavaScript (Node.js)
- **Files:** ~33 JavaScript files
- **Purpose:** Web UI and API gateway
- **Responsibilities:**
  - Serves the web interface
  - Aggregates API calls to backend services
  - Handles user sessions
  - Routes requests to appropriate microservices
- **Key Components:**
  - `server.js` - Express server setup
  - `api/endpoints.js` - API endpoint configuration
  - `api/cart/index.js` - Shopping cart API
  - `api/catalogue/index.js` - Product catalog API
  - `api/orders/index.js` - Order management API
  - `api/user/index.js` - User authentication API
- **Dependencies:**
  - Calls: catalogue, carts, orders, user, payment services
  - Uses: Express.js, React (or similar frontend framework)

#### 2. **Payment Service** (Go)
- **Language:** Go
- **Files:** ~6 Go files
- **Purpose:** Process payments and authorize transactions
- **Responsibilities:**
  - Authorize payment transactions
  - Validate payment amounts
  - Handle payment decline scenarios
  - Health check endpoint
- **Key Components:**
  - `service.go` - Core payment logic
  - `endpoints.go` - HTTP endpoint handlers
  - `transport.go` - HTTP transport layer (go-kit)
  - `logging.go` - Logging middleware
  - `wiring.go` - Dependency injection setup
- **Architecture:** Built with go-kit microservices framework
- **Patterns:** Hexagonal architecture, middleware chain

#### 3. **User Service** (Go)
- **Language:** Go
- **Files:** ~11 Go files
- **Purpose:** User account management and authentication
- **Responsibilities:**
  - User registration
  - User authentication
  - Address management
  - Credit card information storage
  - User profile management
- **Key Components:**
  - `users/users.go` - User domain logic
  - `main.go` - Service entry point
  - Database integration for user data persistence
- **Database:** MongoDB (typically)

#### 4. **Catalogue Service** (Go)
- **Language:** Go
- **Files:** ~5 Go files
- **Purpose:** Product catalog management
- **Responsibilities:**
  - List available products (socks)
  - Product search and filtering
  - Product details retrieval
  - Inventory information
- **Key Components:**
  - `transport.go` - HTTP handlers (11 functions)
  - `endpoints.go` - Business logic endpoints (6 functions, 11 structs)
  - `logging.go` - Request/response logging (6 functions)
- **Database:** MySQL (typically)
- **Features:** Product images, tags, prices, descriptions

#### 5. **Shipping Service** (Java/Spring Boot)
- **Language:** Java
- **Files:** ~20 Java files
- **Purpose:** Handle shipping and fulfillment
- **Responsibilities:**
  - Create shipping requests
  - Track shipments
  - Calculate shipping costs
  - Manage shipment status
- **Key Components:**
  - `ShippingServiceApplication.java` - Spring Boot main class
  - `ShippingController.java` - REST controller
  - `entities/Shipment.java` - Shipment entity
  - `configuration/RabbitMqConfiguration.java` - Message queue setup
  - `middleware/HTTPMonitoringInterceptor.java` - Request monitoring
- **Architecture:** Spring Boot with RabbitMQ integration
- **Database:** MySQL (typically)
- **Messaging:** Uses RabbitMQ for async communication

#### 6. **Carts Service** (Java/Spring Boot)
- **Language:** Java
- **Files:** ~20 Java files
- **Purpose:** Shopping cart management
- **Responsibilities:**
  - Add items to cart
  - Remove items from cart
  - Update cart quantities
  - Retrieve cart contents
  - Merge carts (for logged-in users)
- **Key Components:**
  - Cart entity models
  - CartController for REST endpoints
  - Cart repository for persistence
- **Database:** MongoDB (typically)
- **Patterns:** RESTful API design

#### 7. **Orders Service** (Java/Spring Boot)
- **Language:** Java
- **Files:** ~17 Java files
- **Purpose:** Order processing and management
- **Responsibilities:**
  - Create new orders
  - Retrieve order history
  - Process order workflow
  - Integrate with payment and shipping services
- **Key Components:**
  - Order entity models
  - OrdersController for REST endpoints
  - Order repository for persistence
- **Architecture:** Spring Boot microservice
- **Database:** MongoDB (typically)
- **Integration:** Calls payment and shipping services

---

## Technology Stack by Service

| Service | Language | Framework | Database | Message Queue |
|---------|----------|-----------|----------|---------------|
| front-end | JavaScript | Node.js/Express | - | - |
| payment | Go | go-kit | - | - |
| user | Go | go-kit | MongoDB | - |
| catalogue | Go | go-kit | MySQL | - |
| shipping | Java | Spring Boot | MySQL | RabbitMQ |
| carts | Java | Spring Boot | MongoDB | - |
| orders | Java | Spring Boot | MongoDB | - |

---

## Service Dependencies & Communication

### Call Graph (High-Level)

```
┌─────────────┐
│  front-end  │ (JavaScript/Node.js)
│   Web UI    │
└─────┬───────┘
      │
      ├─────────────┬─────────────┬─────────────┬─────────────┐
      │             │             │             │             │
      v             v             v             v             v
  ┌───────┐    ┌──────────┐  ┌───────┐    ┌────────┐   ┌─────────┐
  │ user  │    │catalogue │  │ carts │    │ orders │   │ payment │
  │  (Go) │    │   (Go)   │  │(Java) │    │ (Java) │   │  (Go)   │
  └───────┘    └──────────┘  └───────┘    └────┬───┘   └─────────┘
                                                │
                                                v
                                          ┌──────────┐
                                          │ shipping │
                                          │  (Java)  │
                                          └──────────┘
```

### API Communication Patterns

1. **Synchronous HTTP REST:**
   - front-end → user: User authentication, profile
   - front-end → catalogue: Product listing, search
   - front-end → carts: Cart operations
   - front-end → orders: Order creation, history
   - orders → payment: Payment authorization
   - orders → shipping: Shipment creation

2. **Asynchronous Messaging:**
   - shipping service uses RabbitMQ for event-driven updates

---

## Code Statistics (Extracted by FlowRAG)

### Total Coverage
- **Total Files:** 148 source files
- **Total Code Units:** 837 (functions, methods, classes)
- **Languages:** 4 (Python, JavaScript, Go, Java)

### By Language

#### Python (Test Utilities)
- **Files:** 36
- **Code Units:** 144
- **Breakdown:**
  - Classes: 31 (Docker, Api, Container test helpers)
  - Methods: 69
  - Functions: ~10
- **Purpose:** Integration test infrastructure

#### JavaScript (Front-End)
- **Files:** 33
- **Code Units:** 52
- **Breakdown:**
  - Functions: 52
  - Classes: 0
- **Imports:** 55
- **Calls:** 551

#### Go (Payment, User, Catalogue)
- **Files:** 22
- **Code Units:** 230
- **Breakdown:**
  - Functions: 101
  - Methods: 68
  - Structs: 61
- **Imports:** 159
- **Calls:** 1024

#### Java (Shipping, Carts, Orders)
- **Files:** 57
- **Code Units:** 411
- **Breakdown:**
  - Methods: 289
  - Constructors: 57
  - Classes: 52
  - Interfaces: 8
  - Enums: 5
- **Imports:** 354
- **Calls:** 500

---

## Key Design Patterns

### 1. Microservices Pattern
- **Separation of Concerns:** Each service handles a specific business capability
- **Independent Deployment:** Services can be deployed and scaled independently
- **Polyglot Persistence:** Different databases for different needs

### 2. API Gateway Pattern
- **front-end service** acts as the API gateway
- Aggregates calls to multiple backend services
- Single entry point for clients

### 3. Database per Service
- **user, carts, orders:** MongoDB (document-oriented for flexible schemas)
- **catalogue, shipping:** MySQL (relational for structured product data)
- **payment:** In-memory or external payment gateway

### 4. Go-kit Microservices Framework (Go services)
- **Endpoint layer:** Business logic
- **Transport layer:** HTTP/gRPC
- **Service layer:** Core domain logic
- **Middleware:** Logging, monitoring, circuit breaking

### 5. Spring Boot REST APIs (Java services)
- **Controller layer:** REST endpoints
- **Service layer:** Business logic
- **Repository layer:** Data access
- **Configuration:** Java-based configuration

### 6. Circuit Breaker Pattern
- **Go services:** Use go-kit circuit breaker
- **Purpose:** Prevent cascading failures

---

## Expected Queries FlowRAG Should Answer

### Architecture Questions

1. **"What services are in the Sock Shop architecture?"**
   - Expected: 7 services (front-end, payment, user, catalogue, shipping, carts, orders)

2. **"What language is the payment service written in?"**
   - Expected: Go

3. **"Which services use Java?"**
   - Expected: shipping, carts, orders

4. **"What database does the user service use?"**
   - Expected: MongoDB (from code analysis and typical deployment)

### Code Structure Questions

5. **"How many functions are in the payment service?"**
   - Expected: ~42 code units (8 functions in transport.go, 3 in logging.go, etc.)

6. **"What classes exist in the catalogue service?"**
   - Expected: Structs from endpoints.go (11 structs extracted)

7. **"What methods does the ShippingController have?"**
   - Expected: Methods extracted from ShippingController.java

8. **"What imports does the front-end service use?"**
   - Expected: 55 imports (Express, HTTP libraries, etc.)

### Dependency Questions

9. **"Which services does the front-end call?"**
   - Expected: user, catalogue, carts, orders, payment

10. **"What services does the orders service depend on?"**
    - Expected: payment, shipping

### Implementation Questions

11. **"What framework does the shipping service use?"**
    - Expected: Spring Boot (from imports like org.springframework.*)

12. **"How many API endpoints does the catalogue service have?"**
    - Expected: Based on functions in transport.go (11 functions)

13. **"What is the signature of the Authorise method in payment service?"**
    - Expected: Should extract from service.go

14. **"What functions call fmt.Println in the Go services?"**
    - Expected: Based on call graph analysis

### Cross-Service Questions

15. **"Show me the flow from order creation to shipment"**
    - Expected: orders service → payment service → shipping service (from call graph)

---

## Testing Strategy

### Test Questions
We'll query FlowRAG with these questions and verify:
1. **Accuracy:** Does the answer match the documentation?
2. **Completeness:** Does it include all relevant services/components?
3. **Source Attribution:** Does it cite specific files/line numbers?
4. **Call Graph:** Can it trace dependencies between services?

### Success Criteria
- ✅ Correctly identifies all 7 services
- ✅ Correctly identifies programming languages
- ✅ Retrieves accurate function/class counts
- ✅ Shows correct service dependencies
- ✅ Provides file paths and line numbers for code references

---

## Notes for FlowRAG Ingestion

### What Was Ingested
- ✅ All source code files (Python, JavaScript, Go, Java)
- ✅ Functions, methods, constructors
- ✅ Classes, structs, interfaces, enums
- ✅ Import relationships
- ✅ Function call graphs

### What Was NOT Ingested
- ❌ Test files (excluded from main ingestion)
- ❌ Configuration files (YAML, JSON)
- ❌ Documentation files (README.md)
- ❌ Vendor dependencies
- ❌ Build artifacts

### Graph Structure in Neo4j
```
(File)-[:CONTAINS]->(Class)-[:CONTAINS]->(Method)
(Function)-[:CALLS]->(Function)
(File)-[:IMPORTS]->(Module)
```

All nodes tagged with:
- `namespace: "sock_shop"`
- `language: "python" | "javascript" | "go" | "java"`
- `file_path: "<absolute path>"`

---

## Summary

Sock Shop is a **7-service polyglot microservices application** demonstrating:
- **4 programming languages:** JavaScript, Go, Java, Python
- **3 architectural patterns:** Microservices, API Gateway, Database per Service
- **2 frameworks:** go-kit (Go), Spring Boot (Java)
- **Real-world complexity:** ~148 files, 837 code units

FlowRAG should be able to answer questions about service architecture, code structure, dependencies, and implementation details by querying the ingested knowledge graph.
