# Sock Shop Services - Complete Memory Bank

## Overview

Sock Shop is a cloud-native microservices reference architecture demonstrating modern e-commerce patterns. It consists of 7 services written in 3 languages (Go, JavaScript, Java), showcasing polyglot microservices, distributed tracing, and observability.

---

## Service Architecture

### 1. Front-End Service (JavaScript/Node.js)

**Purpose:** Web UI and API Gateway

**Technology Stack:**
- Language: JavaScript (Node.js)
- Framework: Express.js
- Files: 24 JavaScript files, 126 functions total

**Key Responsibilities:**
- Serves the e-commerce web interface
- Acts as API gateway aggregating backend calls
- Manages user sessions and cookies
- Routes requests to appropriate microservices
- Handles static asset serving

**Key Components:**
- `server.js` - Express server initialization
- `api/endpoints.js` - API route definitions
- `api/cart/index.js` - Shopping cart API proxy
- `api/catalogue/index.js` - Product catalog API proxy
- `api/orders/index.js` - Order management API proxy
- `api/user/index.js` - User authentication API proxy
- `public/js/client.js` - Client-side JavaScript with cart operations

**API Endpoints:**
- GET /catalogue - List products
- GET /catalogue/:id - Get product details
- POST /cart - Add item to cart
- GET /cart - Get cart contents
- DELETE /cart/:id - Remove cart item
- POST /orders - Create order
- POST /register - User registration
- POST /login - User authentication

**Service Calls:**
Front-end calls all backend services:
- Catalogue service (Go) - Product data
- Carts service (Java) - Shopping cart
- Orders service (Java) - Order processing
- User service (Go) - Authentication
- Payment service (Go) - Payment authorization

**Flow Example - Add to Cart:**
```
1. User clicks "Add to Cart" button
2. client.js sends POST /cart with item_id
3. Front-end proxies to Carts service (Java)
4. Carts service validates and stores cart item
5. Response sent back to browser
6. UI updates cart icon with item count
```

---

### 2. Payment Service (Go)

**Purpose:** Payment authorization and transaction processing

**Technology Stack:**
- Language: Go
- Framework: Go-Kit microservices framework
- Files: 6 Go files, 96 functions total
- Architecture: 3-layer (Transport, Endpoint, Service)

**Key Responsibilities:**
- Authorize payment transactions
- Validate payment amounts against limits
- Handle payment decline scenarios
- Provide health check endpoint
- Expose Prometheus metrics

**Key Components:**
- `service.go` - Core payment business logic (8 functions)
  - `Authorise(amount float32) Authorisation` - Main authorization logic
  - `Health() []Health` - Health check implementation
- `endpoints.go` - HTTP endpoint wrappers (6 functions)
  - `MakeAuthoriseEndpoint(s Service)` - Creates authorization endpoint
  - `MakeHealthEndpoint(s Service)` - Creates health endpoint
- `transport.go` - HTTP transport layer (16 functions)
  - `MakeHTTPHandler()` - Routes HTTP requests
  - `decodeAuthoriseRequest()` - Parses authorization requests
  - `encodeAuthoriseResponse()` - Formats responses
- `logging.go` - Logging middleware (8 functions)
  - Wraps service methods with logging
- `wiring.go` - Dependency injection setup (4 functions)
  - `WireUp()` - Initializes service with all components

**Business Logic:**
```go
type Authorisation struct {
    Authorised bool   `json:"authorised"`
}

func (s *service) Authorise(amount float32) (Authorisation, error) {
    if amount > s.declineOverAmount {
        return Authorisation{Authorised: false}, nil
    }
    return Authorisation{Authorised: true}, nil
}
```

**API Endpoints:**
- POST /paymentAuth - Authorize payment
  - Request: `{"amount": 100.00}`
  - Response: `{"authorised": true/false}`
- GET /health - Health check

**Request Flow - Payment Authorization:**
```
1. HTTP POST /paymentAuth arrives
2. MakeHTTPHandler routes to handler chain
3. decodeAuthoriseRequest parses JSON body
4. MakeAuthoriseEndpoint applies middleware
5. Authorise checks amount > threshold
   - If amount > declineOverAmount: decline
   - Else: authorize
6. encodeAuthoriseResponse formats JSON
7. HTTP 200 OK with {"authorised": true/false}
```

**Architecture Pattern:**
```
Transport Layer (transport.go)
  ↓ HTTP handling
Endpoint Layer (endpoints.go)
  ↓ Circuit breaker, middleware
Service Layer (service.go)
  ↓ Business logic
Response
```

**Monitoring:**
- OpenTracing distributed tracing
- Prometheus metrics exposed
- Health check endpoint

---

### 3. User Service (Go)

**Purpose:** User account management and authentication

**Technology Stack:**
- Language: Go
- Framework: Go-Kit microservices framework
- Files: 11 Go files, 444 functions total (largest service)
- Database: MongoDB

**Key Responsibilities:**
- User registration and account creation
- User authentication (login)
- Address management (shipping/billing)
- Credit card information storage
- User profile management
- Session management

**Key Components:**
- `users/users.go` - User domain models
- `service.go` - Business logic (62 functions)
  - `Register(username, password, email, firstName, lastName)`
  - `Login(username, password)` - Authentication
  - `GetUsers()` - List users
  - `GetUser(id)` - Get user details
- `db.go` - Database interface (75 functions)
  - `CreateUser()` - Persist user
  - `CreateAddress()` - Store address
  - `CreateCard()` - Store payment card
- `mongodb.go` - MongoDB implementation (109 functions)
- `transport.go` - HTTP handlers (129 functions)
- `endpoints.go` - Endpoint wrappers (62 functions)
- `middlewares.go` - Logging and instrumentation (39+186 functions)

**Database Schema:**
```
User {
    username: string
    password: string (hashed)
    email: string
    firstName: string
    lastName: string
    addresses: [Address]
    cards: [Card]
}

Address {
    street: string
    city: string
    postcode: string
    country: string
}

Card {
    longNum: string
    expires: string
    ccv: string
}
```

**API Endpoints:**
- POST /register - Create new user account
- POST /login - Authenticate user
- GET /customers - List all customers (admin)
- GET /customers/:id - Get customer details
- GET /cards - Get user's payment cards
- GET /addresses - Get user's addresses
- POST /cards - Add new payment card
- POST /addresses - Add new address
- GET /health - Health check

**Registration Flow:**
```
1. POST /register with user data
2. decodeRegisterRequest validates input
3. MakeRegisterEndpoint applies middleware
4. Register service method:
   a. Hash password
   b. CreateUser in database
   c. CreateAddress if provided
   d. CreateCard if provided
5. Return created user with ID
```

**Authentication Flow:**
```
1. POST /login with {username, password}
2. decodeLoginRequest parses credentials
3. Login service method:
   a. Fetch user from database
   b. Compare password hashes
   c. Generate session token if valid
4. Return user object + session cookie
```

**Data Access Pattern:**
```
Transport → Endpoint → Service → DB Interface → MongoDB Implementation
```

---

### 4. Catalogue Service (Go)

**Purpose:** Product catalog and inventory management

**Technology Stack:**
- Language: Go
- Framework: Go-Kit microservices framework
- Files: 5 Go files, 150 functions total
- Database: MySQL (typically)

**Key Responsibilities:**
- List available products (socks)
- Product search and filtering
- Product detail retrieval
- Tag-based categorization
- Inventory information

**Key Components:**
- `service.go` - Business logic
  - `List(tags, order, pageNum, pageSize)` - Paginated product listing
  - `Get(id)` - Single product retrieval
  - `Tags()` - Get all product tags
  - `Count(tags)` - Count products matching tags
- `transport.go` - HTTP handlers (11 functions)
  - Routes for /catalogue, /catalogue/:id, /tags
- `endpoints.go` - Endpoint wrappers (6 functions, 11 structs)
- `logging.go` - Request/response logging (6 functions)

**Product Model:**
```
Sock {
    id: string
    name: string
    description: string
    imageUrl: [string]
    price: float
    count: int
    tag: [string]
}
```

**API Endpoints:**
- GET /catalogue - List products with pagination
  - Query params: tags, order, page, size
  - Example: /catalogue?tags=blue&order=price&page=1&size=10
- GET /catalogue/:id - Get product by ID
- GET /tags - Get all available tags
- GET /catalogue/size - Count products
- GET /health - Health check

**Product Listing Flow:**
```
1. GET /catalogue?tags=blue&page=1&size=10
2. decodeListRequest parses query parameters
3. MakeListEndpoint applies caching middleware
4. List service method:
   a. Parse tags filter
   b. Apply sorting (price/name)
   c. Calculate pagination offset
   d. Query database with filters
   e. Return page of products
5. encodeListResponse formats JSON array
```

**Features:**
- Product images stored as URL arrays
- Tag-based filtering (color, material, pattern)
- Price-based sorting
- Pagination support
- Product count API

---

### 5. Carts Service (Java/Spring Boot)

**Purpose:** Shopping cart management

**Technology Stack:**
- Language: Java
- Framework: Spring Boot
- Files: 24 Java files, 137 functions total
- Database: MongoDB

**Key Responsibilities:**
- Create and manage shopping carts
- Add items to cart
- Update item quantities
- Remove items from cart
- Merge carts (anonymous → logged in)
- Calculate cart totals

**Key Components:**
- `CartController.java` - REST endpoints
- `CartService.java` - Business logic
- `CartRepository.java` - Data access
- `Cart.java` - Domain model
- `Item.java` - Cart item model

**Cart Model:**
```java
Cart {
    customerId: String
    items: List<Item>
}

Item {
    itemId: String
    quantity: int
    unitPrice: float
}
```

**API Endpoints:**
- GET /carts/:customerId - Get customer's cart
- POST /carts/:customerId/items - Add item to cart
- PATCH /carts/:customerId/items - Update item quantity
- DELETE /carts/:customerId/items/:itemId - Remove item
- POST /carts/:customerId/merge - Merge carts
- GET /health - Health check

**Add to Cart Flow:**
```
1. POST /carts/{customerId}/items
   Body: {itemId: "sock123", quantity: 2}
2. CartController receives request
3. CartService.addItem():
   a. Fetch or create cart for customer
   b. Check if item already in cart
      - If yes: increment quantity
      - If no: add new item
   c. Save updated cart
4. Return updated cart with all items
```

**Spring Boot Configuration:**
- Uses MongoDB for persistence
- REST controller annotations
- Dependency injection
- Health check actuator

---

### 6. Orders Service (Java/Spring Boot)

**Purpose:** Order creation and management

**Technology Stack:**
- Language: Java
- Framework: Spring Boot
- Files: 25 Java files, 225 functions total (largest Java service)
- Database: MongoDB
- Messaging: RabbitMQ

**Key Responsibilities:**
- Create customer orders
- Orchestrate order fulfillment
- Coordinate with payment, shipping services
- Track order status
- Manage order history

**Key Components:**
- `OrdersController.java` - REST endpoints
- `OrdersService.java` - Business logic
- `Order.java` - Domain model
- `PaymentClient.java` - Payment service integration
- `ShippingClient.java` - Shipping service integration

**Order Model:**
```java
Order {
    id: String
    customerId: String
    customer: Customer
    address: Address
    card: Card
    items: List<Item>
    shipment: Shipment
    date: Date
    total: float
}
```

**API Endpoints:**
- POST /orders - Create new order
- GET /orders - List customer orders
- GET /orders/:id - Get order details
- GET /health - Health check

**Order Creation Flow:**
```
1. POST /orders
   Body: {customerId, addressId, cardId, items}
2. OrdersController receives request
3. OrdersService.createOrder():
   a. Validate customer exists
   b. Get address and card details
   c. Calculate order total
   d. Call Payment service for authorization
   e. If authorized:
      - Call Shipping service to create shipment
      - Create order record
      - Clear customer's cart
      - Publish order event to RabbitMQ
   f. If declined:
      - Return payment declined error
4. Return created order with ID
```

**Integration Points:**
- Payment Service - Authorization check
- Shipping Service - Shipment creation
- User Service - Customer validation
- Carts Service - Cart clearing
- RabbitMQ - Order events

---

### 7. Shipping Service (Java/Spring Boot)

**Purpose:** Shipping calculation and fulfillment

**Technology Stack:**
- Language: Java
- Framework: Spring Boot
- Files: 8 Java files, 49 functions total (smallest service)
- Queue: RabbitMQ for async processing

**Key Responsibilities:**
- Create shipping requests
- Calculate shipping costs
- Track shipment status
- Manage delivery information

**Key Components:**
- `ShippingController.java` - REST endpoints (6 functions)
- `Shipment.java` - Domain model (11 functions)
- `ShippingServiceApplication.java` - Spring Boot main (6 functions)
- `RabbitMqConfiguration.java` - Message queue setup (8 functions)

**Shipment Model:**
```java
Shipment {
    id: String
    name: String
    carrier: String
    trackingNumber: String
    deliveryDate: Date
}
```

**API Endpoints:**
- POST /shipping - Create shipment
  - Request: `{itemId, itemCount, address}`
  - Response: Shipment with tracking number
- GET /shipping/:id - Get shipment status
- GET /health - Health check

**Shipping Creation Flow:**
```
1. POST /shipping (usually called by Orders service)
   Body: {itemId, itemCount, address}
2. ShippingController receives request
3. Create Shipment:
   a. Generate unique tracking number
   b. Assign carrier (e.g., "USPS", "FedEx")
   c. Calculate estimated delivery date
   d. Store shipment record
4. Return shipment details
```

**RabbitMQ Integration:**
- Listens for order events
- Processes shipments asynchronously
- Updates shipment status

---

## Cross-Service Communication

### Service Dependencies

```
Front-End (JS)
  ├─→ Catalogue (Go) - Product data
  ├─→ Carts (Java) - Cart management
  ├─→ Orders (Java) - Order creation
  ├─→ User (Go) - Authentication
  └─→ Payment (Go) - Implicit via Orders

Orders (Java)
  ├─→ Payment (Go) - Authorization
  ├─→ Shipping (Java) - Shipment creation
  ├─→ User (Go) - Customer validation
  └─→ Carts (Java) - Cart clearing

Carts (Java)
  └─→ Catalogue (Go) - Price lookup

User (Go)
  └─→ MongoDB - User data

Payment (Go)
  └─→ (No external service dependencies)

Shipping (Java)
  └─→ RabbitMQ - Event processing

Catalogue (Go)
  └─→ MySQL - Product data
```

### Communication Patterns

**Synchronous HTTP:**
- Front-end → All backend services
- Orders → Payment (authorization)
- Orders → Shipping (creation)
- Carts → Catalogue (price validation)

**Asynchronous Messaging:**
- Orders → RabbitMQ → Shipping (order events)

---

## Complete User Flows

### Flow 1: User Registration

```
1. User fills registration form on front-end
2. Front-end POST /register to User service
3. User service:
   a. Validates input (email format, password strength)
   b. Hashes password with bcrypt
   c. Creates user record in MongoDB
   d. Creates default address if provided
   e. Creates payment card if provided
4. Returns user object with generated ID
5. Front-end auto-logs in user
6. Session cookie set for authentication
```

**Services Involved:** Front-end (JS), User (Go)

### Flow 2: Browse Products

```
1. User lands on homepage
2. Front-end GET /catalogue from Catalogue service
3. Catalogue service:
   a. Queries MySQL for products
   b. Applies default sorting (featured)
   c. Returns first page (10 items)
4. Front-end renders product grid
5. User applies filters (e.g., tag=blue)
6. Front-end GET /catalogue?tags=blue
7. Catalogue returns filtered results
8. Front-end updates display
```

**Services Involved:** Front-end (JS), Catalogue (Go)

### Flow 3: Add to Cart

```
1. User clicks "Add to Cart" on product
2. Front-end POST /cart with itemId
3. Front-end proxies to Carts service (Java)
4. Carts service:
   a. Fetches current cart for customer
   b. Checks if product already in cart
      - If yes: quantity++
      - If no: adds new item
   c. Optionally validates price with Catalogue
   d. Saves updated cart to MongoDB
5. Returns full cart contents
6. Front-end updates cart icon (item count)
```

**Services Involved:** Front-end (JS), Carts (Java), [Catalogue (Go)]

### Flow 4: Complete Purchase (Full E-commerce Flow)

```
1. User clicks "Checkout"
2. Front-end displays order summary
3. User confirms order
4. Front-end POST /orders to Orders service
   Body: {customerId, addressId, cardId, items}

5. Orders service orchestration:
   a. Validate customer exists (User service)
   b. Get address details from User service
   c. Get card details from User service
   d. Calculate order total from cart items

   e. Call Payment service POST /paymentAuth
      - Payment checks amount < threshold
      - Returns {authorised: true/false}

   f. If payment authorized:
      - Call Shipping POST /shipping
      - Shipping creates shipment record
      - Shipping returns tracking number

      - Orders creates order record in MongoDB
      - Orders publishes order event to RabbitMQ
      - Orders calls Carts DELETE /cart to clear

   g. If payment declined:
      - Return error to front-end
      - No order created

6. Return order confirmation to front-end
7. Front-end displays success page with order ID

8. Asynchronously:
   - Shipping service picks up RabbitMQ event
   - Updates shipment status
   - Could trigger email notification
```

**Services Involved:**
- Front-end (JS)
- Orders (Java) - Orchestrator
- User (Go) - Customer data
- Payment (Go) - Authorization
- Shipping (Java) - Fulfillment
- Carts (Java) - Cart clearing

**Data Flow:**
```
Front-end → Orders
Orders → User (get customer, address, card)
Orders → Payment (authorize)
Payment → Orders (authorization result)
Orders → Shipping (create shipment)
Shipping → Orders (tracking number)
Orders → Carts (clear cart)
Orders → RabbitMQ (order event)
Orders → Front-end (order confirmation)
RabbitMQ → Shipping (async processing)
```

---

## Technical Architecture Patterns

### Go-Kit Microservices (Payment, User, Catalogue)

**3-Layer Architecture:**

1. **Transport Layer** (`transport.go`)
   - HTTP request/response handling
   - Request decoding (JSON → structs)
   - Response encoding (structs → JSON)
   - Error handling and formatting

2. **Endpoint Layer** (`endpoints.go`)
   - Business logic wrappers
   - Middleware application:
     - Circuit breakers
     - Rate limiting
     - Request/response logging
     - Distributed tracing

3. **Service Layer** (`service.go`)
   - Pure business logic
   - No HTTP knowledge
   - Testable in isolation
   - Interface-based design

**Dependency Injection:**
```go
// Wiring pattern
func WireUp() http.Handler {
    // 1. Create service
    service := NewService()

    // 2. Add logging middleware
    service = LoggingMiddleware(service)

    // 3. Create endpoints
    endpoints := MakeEndpoints(service)

    // 4. Create HTTP handler
    handler := MakeHTTPHandler(endpoints)

    return handler
}
```

**Benefits:**
- Separation of concerns
- Easy to add middleware
- Testable layers
- Framework-agnostic business logic

### Spring Boot Services (Carts, Orders, Shipping)

**Controller → Service → Repository Pattern:**

1. **Controller** (`*Controller.java`)
   - REST endpoint definitions
   - Request validation
   - HTTP response mapping
   - Annotations: `@RestController`, `@RequestMapping`

2. **Service** (`*Service.java`)
   - Business logic implementation
   - Transaction management
   - Service orchestration
   - Annotations: `@Service`, `@Transactional`

3. **Repository** (`*Repository.java`)
   - Data access abstraction
   - MongoDB operations
   - Query methods
   - Annotations: `@Repository`, Spring Data

**Dependency Injection:**
```java
@RestController
public class OrdersController {
    @Autowired
    private OrdersService ordersService;

    @PostMapping("/orders")
    public Order createOrder(@RequestBody OrderRequest req) {
        return ordersService.createOrder(req);
    }
}
```

**Benefits:**
- Convention over configuration
- Auto-configuration
- Rich ecosystem (Spring Data, Spring Cloud)
- Built-in monitoring (Actuator)

---

## Observability & Monitoring

### Distributed Tracing

**OpenTracing Integration:**
- All services instrumented
- Trace IDs propagated across services
- Spans created for each operation
- Visualize complete request flows

**Example Trace:**
```
Trace ID: abc123
├─ Front-end: GET /
│  └─ Span: render homepage (50ms)
├─ Catalogue: GET /catalogue
│  ├─ Span: decode request (1ms)
│  ├─ Span: query database (15ms)
│  └─ Span: encode response (2ms)
└─ Total: 68ms
```

### Metrics

**Prometheus Metrics Exposed:**
- Request count by endpoint
- Response time histograms
- Error rates
- Active connections
- Database query times
- Queue depths (RabbitMQ)

**Example Metrics:**
```
http_requests_total{service="payment",endpoint="/paymentAuth"} 1543
http_request_duration_seconds{service="payment"} 0.045
```

### Health Checks

**All services expose `/health` endpoint:**
- Returns 200 OK when healthy
- Includes dependency status
- Used by load balancers
- Kubernetes readiness/liveness probes

---

## Database Architecture

### MongoDB (User, Carts, Orders)

**Why MongoDB:**
- Flexible schema for user profiles
- Nested documents (addresses, cards)
- Good for cart operations (frequent updates)
- JSON-like documents match REST API

**Collections:**
- `users` - User accounts
- `carts` - Shopping carts
- `orders` - Order history
- `shipments` - Shipping records

### MySQL (Catalogue)

**Why MySQL:**
- Relational data (products, tags)
- ACID transactions
- Good for product catalog
- SQL query capabilities

**Tables:**
- `socks` - Product catalog
- `tags` - Product categorization
- `sock_tag` - Many-to-many relationship

---

## Message Queue (RabbitMQ)

**Purpose:** Asynchronous event processing

**Queues:**
- `orders` - Order creation events
- `shipments` - Shipping status updates

**Flow:**
```
Orders Service → RabbitMQ → Shipping Service
(publishes)        (queue)     (consumes)
```

**Benefits:**
- Decoupling services
- Resilience (retry on failure)
- Load leveling
- Event-driven architecture

---

## Deployment Architecture

### Containerization

**All services are containerized:**
- Docker images for each service
- Multi-stage builds (compile → runtime)
- Minimal base images (Alpine Linux)
- Health checks in Dockerfile

### Orchestration

**Kubernetes Deployment:**
- Each service as Deployment
- Service discovery via K8s Services
- ConfigMaps for configuration
- Secrets for credentials
- HorizontalPodAutoscaler for scaling

### Service Mesh

**Linkerd/Istio compatible:**
- Automatic retry and timeout
- Load balancing
- Traffic splitting (canary deployments)
- Mutual TLS

---

## Security Considerations

### Authentication

**User Service:**
- Password hashing with bcrypt
- Session-based authentication
- Secure cookie flags (HttpOnly, Secure)

### Authorization

**API Gateway (Front-end):**
- Session validation
- Customer ID verification
- Rate limiting

### Network Security

**Service-to-Service:**
- mTLS in service mesh
- Internal network isolation
- API keys for service auth

### Data Protection

**Sensitive Data:**
- Credit card info (encrypted at rest)
- Passwords (hashed, never stored plain)
- PII (compliant with regulations)

---

## Performance Characteristics

### Response Times (typical)

- Catalogue list: 50-100ms
- Payment authorization: 20-50ms
- User login: 100-200ms (bcrypt overhead)
- Cart operations: 30-80ms
- Order creation: 200-500ms (orchestration)

### Scalability

**Stateless Services:**
- Payment, Catalogue - Horizontally scalable
- Multiple instances behind load balancer

**Stateful Services:**
- User, Carts, Orders - Scale with database
- Session affinity not required (DB-backed)

### Bottlenecks

**Common:**
- Database queries (catalogue filtering)
- Password hashing (user login)
- Order orchestration (multiple service calls)

**Mitigation:**
- Database indexing
- Caching (Redis for catalogue)
- Async processing (RabbitMQ for orders)

---

## Error Handling Patterns

### Go Services

```go
func (s *service) Authorise(amount float32) (Authorisation, error) {
    if amount < 0 {
        return Authorisation{}, ErrInvalidAmount
    }
    // ... business logic
    return auth, nil
}
```

**Error Response:**
```json
{
    "error": "Invalid amount",
    "status": 400
}
```

### Java Services

```java
@ExceptionHandler(InvalidOrderException.class)
public ResponseEntity<ErrorResponse> handleInvalidOrder(InvalidOrderException e) {
    return ResponseEntity.badRequest()
        .body(new ErrorResponse(e.getMessage()));
}
```

### Circuit Breakers

**Go-Kit Middleware:**
- Fails fast when service unavailable
- Returns cached response or default
- Prevents cascade failures

---

## Testing Strategy

### Unit Tests

**Go Services:**
- Test service layer in isolation
- Mock dependencies
- Table-driven tests

**Java Services:**
- JUnit + Mockito
- Mock repositories
- Test business logic

### Integration Tests

- Test with real databases (Docker)
- Test service-to-service calls
- Verify error scenarios

### E2E Tests

- Complete user flows
- Selenium for front-end
- API tests for backend
- Chaos engineering (random failures)

---

## Key Insights for Developers

### Understanding Payment Authorization

**Location:** `payment/service.go:41`

The payment service uses a simple threshold-based authorization:
```go
func (s *service) Authorise(amount float32) (Authorisation, error) {
    if amount > s.declineOverAmount {
        return Authorisation{Authorised: false}, nil
    }
    return Authorisation{Authorised: true}, nil
}
```

**Key Point:** This is a demo - real payment would call external gateway (Stripe, PayPal)

### Understanding User Registration

**Location:** `user/service.go:62`

Registration creates user + optional address + card:
```go
func (s *service) Register(username, password, email, first, last string) (User, error) {
    u := NewUser(username, password, email, first, last)
    err := s.users.CreateUser(u)
    // ... create address and card if provided
    return u, err
}
```

**Security:** Password hashed before storage, never logged

### Understanding Cart Management

**Location:** `carts/CartService.java`

Cart operations are idempotent:
- Adding same item twice → increments quantity
- Removing non-existent item → no error
- Merging empty carts → safe operation

### Understanding Order Orchestration

**Location:** `orders/OrdersService.java`

Order creation is transactional:
1. All validations pass, OR
2. No order created (rollback)

**Failure Scenarios:**
- Payment declined → No order, cart unchanged
- Shipping failed → Compensating transaction
- Database error → Rollback all changes

---

## Common Development Tasks

### Adding New Product to Catalogue

```
1. Insert into MySQL socks table
2. Add tags in sock_tag table
3. No code changes needed
4. Catalogue service auto-picks up
```

### Changing Payment Threshold

```
1. Edit payment/service.go
2. Change declineOverAmount constant
3. Rebuild + redeploy payment service
4. No other services affected
```

### Adding New Order Status

```
1. Add status to Order.java enum
2. Update OrdersService state machine
3. Add RabbitMQ handler for new status
4. Update front-end UI
```

---

## Debugging Tips

### Tracing Request Flow

1. Check distributed trace for request ID
2. Follow spans across services
3. Identify slow component
4. Check logs for that span

### Database Issues

**MongoDB slow queries:**
```
db.currentOp({"active": true, "secs_running": {$gt: 5}})
```

**MySQL slow queries:**
```
SHOW FULL PROCESSLIST;
```

### Network Issues

**Check service connectivity:**
```bash
kubectl exec -it pod-name -- curl http://catalogue:8080/health
```

### Memory Leaks

**Check Go service metrics:**
```
http://payment:8080/debug/pprof/heap
```

**Check Java heap:**
```
jmap -heap <pid>
```

---

## Summary

Sock Shop demonstrates modern microservices architecture with:

- **7 services** across **3 languages** (Go, JavaScript, Java)
- **Multiple databases** (MongoDB, MySQL)
- **Message queue** (RabbitMQ) for async processing
- **Distributed tracing** (OpenTracing) for observability
- **Cloud-native** deployment (Docker, Kubernetes)

**Key Architectural Patterns:**
- Go-Kit 3-layer architecture (Transport, Endpoint, Service)
- Spring Boot MVC (Controller, Service, Repository)
- API Gateway pattern (Front-end)
- Service orchestration (Orders)
- Event-driven (RabbitMQ)

**Production-Ready Features:**
- Health checks
- Metrics (Prometheus)
- Tracing (OpenTracing)
- Circuit breakers
- Graceful shutdown
- Configuration management

This is a reference architecture showcasing best practices for building, deploying, and operating microservices at scale.
