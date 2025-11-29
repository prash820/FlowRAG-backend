# FlowRAG API Route Detection Strategy

**Purpose:** Document how we detect and extract API routes/endpoints from code

**Date:** 2025-11-19

---

## Overview

FlowRAG automatically detects API endpoints in source code and creates a graph connecting endpoints to their handler functions.

**Supported Frameworks:**
1. **Go:** gorilla/mux, go-kit HTTP transport, http.HandleFunc
2. **JavaScript/Node.js:** Express.js
3. **Java:** Spring Boot (@RestController, @RequestMapping annotations)
4. **PHP:** Laravel (Route::get/post/resource patterns)
5. **Python:** FastAPI (@app.get decorators), Flask (@app.route decorators)
6. **Ruby:** Ruby on Rails (resources, get/post/put/patch/delete)

---

## API Route Patterns Detected

### Go Patterns

#### 1. **gorilla/mux Router**

```go
r := mux.NewRouter()

// Pattern 1: Methods().Path().Handler()
r.Methods("GET").Path("/login").Handler(httptransport.NewServer(
    e.LoginEndpoint,
    decodeLoginRequest,
    encodeResponse,
))

// Pattern 2: Methods().PathPrefix().Handler()
r.Methods("GET").PathPrefix("/customers").Handler(httptransport.NewServer(
    e.UserGetEndpoint,
    decodeGetRequest,
    encodeResponse,
))

// Pattern 3: HandleFunc
r.HandleFunc("/health", healthHandler).Methods("GET")

// Pattern 4: Handle
r.Handle("/metrics", promhttp.Handler())
```

**Detection Strategy:**
- Look for `mux.NewRouter()` calls
- Track calls on router variable: `.Methods()`, `.Path()`, `.PathPrefix()`, `.Handler()`
- Extract HTTP method and path from call chain
- Link to handler function (first argument to `.Handler()`)

#### 2. **Standard http.HandleFunc**

```go
http.HandleFunc("/", indexHandler)
http.HandleFunc("/api/users", usersHandler)
```

**Detection Strategy:**
- Look for `http.HandleFunc()` calls
- First argument: path pattern
- Second argument: handler function name

---

### JavaScript/Express Patterns

#### 1. **Express app.METHOD()**

```javascript
const app = express();

// Pattern 1: Basic routes
app.get("/customers/:id", function(req, res, next) {
    // handler code
});

// Pattern 2: Named functions
app.post("/register", registerHandler);

// Pattern 3: Multiple handlers (middleware)
app.post("/customers", auth, validation, function(req, res) {
    // handler code
});
```

**Detection Strategy:**
- Look for `app.get()`, `app.post()`, `app.put()`, `app.delete()`, `app.patch()`
- First argument: route pattern
- Last argument: handler function (may be anonymous or named)
- Track middleware chain

#### 2. **Express router.METHOD()**

```javascript
const router = express.Router();

router.get("/users", getUsersHandler);
router.post("/users", createUserHandler);

module.exports = router;
```

**Detection Strategy:**
- Look for `express.Router()` calls
- Track calls on router variable
- Extract method, path, and handler

---

### Java/Spring Boot Patterns

#### 1. **@RequestMapping Annotations**

```java
@RestController
@RequestMapping("/api")
public class UserController {

    @GetMapping("/users")
    public List<User> getUsers() {
        // ...
    }

    @PostMapping("/users")
    public User createUser(@RequestBody User user) {
        // ...
    }

    @RequestMapping(value = "/customers", method = RequestMethod.GET)
    public List<Customer> getCustomers() {
        // ...
    }
}
```

**Detection Strategy:**
- Look for `@RestController`, `@Controller` class annotations
- Track `@RequestMapping`, `@GetMapping`, `@PostMapping`, etc. on methods
- Extract HTTP method and path
- Combine class-level and method-level paths

---

### PHP/Laravel Patterns

#### 1. **Route Facade Methods**

```php
use Illuminate\Support\Facades\Route;

// Pattern 1: Basic routes
Route::get('/users', [UserController::class, 'index']);
Route::post('/users', [UserController::class, 'store']);

// Pattern 2: String notation
Route::put('/users/{id}', 'UserController@update');

// Pattern 3: Resource routes
Route::resource('/posts', PostController::class);

// Pattern 4: API Resource routes (no create/edit views)
Route::apiResource('/api/users', UserController::class);
```

**Detection Strategy:**
- Look for `Route::` static method calls
- Extract HTTP method from method name (get, post, put, patch, delete)
- First argument: route path
- Second argument: controller and method
- Expand resource routes into 7 individual routes
- Expand apiResource routes into 5 individual routes

---

### Python/FastAPI Patterns

#### 1. **FastAPI Route Decorators**

```python
from fastapi import FastAPI

app = FastAPI()

# Pattern 1: Basic routes
@app.get("/users")
async def get_users():
    return {"users": []}

# Pattern 2: Path parameters
@app.get("/users/{user_id}")
async def get_user(user_id: int):
    return {"user_id": user_id}

# Pattern 3: Router
from fastapi import APIRouter
router = APIRouter()

@router.post("/items")
async def create_item(item: Item):
    return item

# Pattern 4: Multiple methods
@app.api_route("/multi", methods=["GET", "POST"])
async def multi_method():
    return {}
```

**Detection Strategy:**
- Look for `@app.get`, `@app.post`, `@router.get`, etc. decorators
- Extract HTTP method from decorator name
- First argument of decorator: route path
- Function name: handler name
- Support for `@app.api_route` with methods parameter

---

### Python/Flask Patterns

#### 1. **Flask Route Decorators**

```python
from flask import Flask

app = Flask(__name__)

# Pattern 1: Single method
@app.route("/users", methods=["GET"])
def get_users():
    return {"users": []}

# Pattern 2: Multiple methods
@app.route("/users", methods=["GET", "POST"])
def users():
    if request.method == "GET":
        return get_all_users()
    else:
        return create_user()

# Pattern 3: Blueprint
from flask import Blueprint
api = Blueprint('api', __name__)

@api.route("/items/<int:item_id>")
def get_item(item_id):
    return {"item_id": item_id}
```

**Detection Strategy:**
- Look for `@app.route`, `@blueprint.route` decorators
- Extract path from first argument
- Extract methods from `methods` keyword argument
- Default to GET if no methods specified
- Create separate route for each HTTP method

---

### Ruby/Rails Patterns

#### 1. **Rails Routes DSL**

```ruby
Rails.application.routes.draw do
  # Pattern 1: Basic routes
  get '/users', to: 'users#index'
  post '/users', to: 'users#create'

  # Pattern 2: Resource routes
  resources :posts  # Creates 7 RESTful routes

  # Pattern 3: Singular resource
  resource :profile  # Creates 6 RESTful routes (no index)

  # Pattern 4: Namespace
  namespace :api do
    namespace :v1 do
      resources :users
    end
  end

  # Pattern 5: Member/collection routes
  resources :articles do
    member do
      post :publish
    end
    collection do
      get :archived
    end
  end
end
```

**Detection Strategy:**
- Look for route DSL methods: get, post, put, patch, delete
- Extract path and controller#action from arguments
- Expand `resources` into 7 individual routes
- Expand `resource` into 6 individual routes
- Track namespace prefixes for nested routes

---

## Graph Schema

### APIEndpoint Node

```python
class APIEndpointNode(BaseNode):
    """API endpoint node."""

    label: str = NodeLabel.ENDPOINT

    # HTTP details
    http_method: str                    # GET, POST, PUT, DELETE, PATCH
    path: str                           # /api/users/:id

    # Handler details
    handler_function: str               # Function name
    handler_file: str                   # File containing handler

    # Metadata
    service: str                        # Service name (e.g., "user")
    framework: str                      # Framework (e.g., "express", "gorilla/mux")
    middleware: List[str] = []          # Middleware functions

    # Documentation
    description: Optional[str] = None   # Endpoint description
    parameters: List[str] = []          # Path/query parameters
    request_body: Optional[str] = None  # Request body schema
    response_body: Optional[str] = None # Response body schema
```

### HANDLES Relationship

```python
class HandlesRelationship(BaseRelationship):
    """Endpoint handles relationship."""

    type: RelationType = RelationType.HANDLES

    # From: APIEndpoint
    # To: Function (handler)

    # Metadata
    is_direct: bool = True              # Direct handler vs middleware
    handler_order: int = 1              # Order in handler chain
```

---

## Implementation

### Enhanced Go Parser

**Location:** `ingestion/parsers/go_parser.py`

**New Method:** `_extract_api_routes()`

```python
def _extract_api_routes(self, root_node: Node, code: str) -> List[APIRoute]:
    """Extract API routes from Go code."""
    routes = []

    def visit_node(node: Node):
        # Pattern 1: r.Methods("GET").Path("/login").Handler(...)
        if node.type == "call_expression":
            call_chain = self._get_call_chain(node, code)

            # Check if this is a router call chain
            if self._is_router_call_chain(call_chain):
                route = self._parse_router_call_chain(call_chain, code)
                if route:
                    routes.append(route)

        # Pattern 2: http.HandleFunc("/path", handler)
        elif node.type == "call_expression":
            callee = self._get_callee_name(node, code)
            if callee in ["http.HandleFunc", "HandleFunc"]:
                route = self._parse_handle_func(node, code)
                if route:
                    routes.append(route)

        # Recursively visit children
        for child in node.children:
            visit_node(child)

    visit_node(root_node)
    return routes
```

**Call Chain Parsing:**

```python
def _get_call_chain(self, node: Node, code: str) -> List[Dict]:
    """Get chain of method calls like r.Methods("GET").Path("/login")."""
    chain = []
    current = node

    while current:
        if current.type == "call_expression":
            # Get method name
            method = self._get_method_name(current, code)

            # Get arguments
            args = self._get_call_arguments(current, code)

            chain.insert(0, {
                'method': method,
                'args': args
            })

            # Move to next in chain (object of current call)
            current = self._get_call_object(current)
        else:
            break

    return chain
```

**Route Extraction:**

```python
def _parse_router_call_chain(self, call_chain: List[Dict], code: str) -> Optional[APIRoute]:
    """Parse route from gorilla/mux call chain."""
    http_method = None
    path = None
    handler = None

    for call in call_chain:
        method = call['method']
        args = call['args']

        # Extract HTTP method
        if method == 'Methods' and args:
            http_method = args[0].strip('"')

        # Extract path
        elif method in ['Path', 'PathPrefix'] and args:
            path = args[0].strip('"')

        # Extract handler
        elif method == 'Handler' and args:
            handler = self._extract_handler_from_server(args[0])

    if http_method and path and handler:
        return APIRoute(
            method=http_method,
            path=path,
            handler=handler,
            framework='gorilla/mux'
        )

    return None
```

---

### Enhanced JavaScript Parser

**Location:** `ingestion/parsers/javascript_parser.py`

**New Method:** `_extract_api_routes()`

```python
def _extract_api_routes(self, tree: Any) -> List[APIRoute]:
    """Extract API routes from Express.js code."""
    routes = []

    def visit_node(node):
        if hasattr(node, 'type') and node.type == 'CallExpression':
            # Get callee (e.g., "app.get", "router.post")
            callee = self._get_callee_name(node.callee)

            # Check if it's an Express route definition
            if callee and self._is_express_route(callee):
                route = self._parse_express_route(node, callee)
                if route:
                    routes.append(route)

        # Recursively visit children
        for key in ['body', 'declarations', 'expression', 'arguments']:
            if hasattr(node, key):
                attr = getattr(node, key)
                if attr is None:
                    continue
                if hasattr(attr, 'type'):
                    visit_node(attr)
                elif isinstance(attr, list):
                    for item in attr:
                        if item and hasattr(item, 'type'):
                            visit_node(item)

    if hasattr(tree, 'body'):
        for stmt in tree.body:
            visit_node(stmt)

    return routes
```

**Express Route Detection:**

```python
def _is_express_route(self, callee: str) -> bool:
    """Check if callee is an Express route method."""
    # app.get, app.post, router.get, etc.
    parts = callee.split('.')
    if len(parts) == 2:
        obj, method = parts
        return method in ['get', 'post', 'put', 'delete', 'patch', 'all']
    return False

def _parse_express_route(self, node: Any, callee: str) -> Optional[APIRoute]:
    """Parse Express route from CallExpression."""
    if not hasattr(node, 'arguments') or len(node.arguments) < 2:
        return None

    # First argument: path
    path_arg = node.arguments[0]
    path = None
    if hasattr(path_arg, 'value'):
        path = path_arg.value

    # Last argument: handler function
    handler_arg = node.arguments[-1]
    handler = None

    if handler_arg.type == 'FunctionExpression':
        handler = '<anonymous>'
        # Could extract line number for linking
        handler_line = handler_arg.loc.start.line if hasattr(handler_arg, 'loc') else None
    elif handler_arg.type == 'Identifier':
        handler = handler_arg.name if hasattr(handler_arg, 'name') else None
    elif handler_arg.type == 'ArrowFunctionExpression':
        handler = '<arrow-function>'
        handler_line = handler_arg.loc.start.line if hasattr(handler_arg, 'loc') else None

    # Extract HTTP method from callee (e.g., "app.get" -> "GET")
    http_method = callee.split('.')[-1].upper()

    # Extract middleware (arguments between path and handler)
    middleware = []
    for i in range(1, len(node.arguments) - 1):
        arg = node.arguments[i]
        if hasattr(arg, 'name'):
            middleware.append(arg.name)

    if path and handler and http_method:
        return APIRoute(
            method=http_method,
            path=path,
            handler=handler,
            handler_line=handler_line,
            middleware=middleware,
            framework='express'
        )

    return None
```

---

## API Route Data Model

```python
@dataclass
class APIRoute:
    """Represents an extracted API route."""

    # Required
    method: str          # GET, POST, PUT, DELETE, PATCH
    path: str            # /api/users/:id
    handler: str         # Handler function name
    framework: str       # express, gorilla/mux, spring

    # Optional
    file_path: str = None
    handler_line: int = None
    middleware: List[str] = field(default_factory=list)
    parameters: List[str] = field(default_factory=list)
    description: str = None

    def to_endpoint_node(self, namespace: str) -> dict:
        """Convert to Neo4j APIEndpoint node."""
        return {
            'id': self.generate_id(),
            'name': f"{self.method} {self.path}",
            'label': 'Endpoint',
            'http_method': self.method,
            'path': self.path,
            'handler_function': self.handler,
            'framework': self.framework,
            'middleware': self.middleware,
            'namespace': namespace,
            'file_path': self.file_path or ''
        }

    def generate_id(self) -> str:
        """Generate unique ID for endpoint."""
        import hashlib
        key = f"{self.method}:{self.path}:{self.framework}"
        return hashlib.sha256(key.encode()).hexdigest()[:16]
```

---

## Integration with Neo4j

### Store APIEndpoint Nodes

```python
# In neo4j_loader.py

def load_api_routes(self, routes: List[APIRoute], namespace: str):
    """Load API routes into Neo4j."""
    with self.driver.session() as session:
        for route in routes:
            # Create APIEndpoint node
            endpoint_data = route.to_endpoint_node(namespace)

            query = """
            MERGE (e:Endpoint {id: $id})
            SET e.name = $name,
                e.http_method = $http_method,
                e.path = $path,
                e.handler_function = $handler_function,
                e.framework = $framework,
                e.middleware = $middleware,
                e.namespace = $namespace,
                e.file_path = $file_path
            RETURN e
            """

            session.run(query, **endpoint_data)

            # Create HANDLES relationship to handler function
            if route.handler != '<anonymous>':
                self._link_endpoint_to_handler(
                    endpoint_data['id'],
                    route.handler,
                    namespace
                )
```

### Create HANDLES Relationships

```python
def _link_endpoint_to_handler(self, endpoint_id: str, handler_name: str, namespace: str):
    """Create HANDLES relationship between endpoint and handler function."""
    with self.driver.session() as session:
        query = """
        MATCH (e:Endpoint {id: $endpoint_id})
        MATCH (f:Function {name: $handler_name, namespace: $namespace})
        MERGE (e)-[r:HANDLES]->(f)
        SET r.created_at = datetime()
        RETURN r
        """

        session.run(query,
                   endpoint_id=endpoint_id,
                   handler_name=handler_name,
                   namespace=namespace)
```

---

## Query Examples

### Find All API Endpoints

```cypher
MATCH (e:Endpoint {namespace: 'sock_shop'})
RETURN e.http_method, e.path, e.handler_function
ORDER BY e.path
```

### Find Handler for Endpoint

```cypher
MATCH (e:Endpoint {path: '/register', http_method: 'POST'})-[:HANDLES]->(f:Function)
RETURN f.name, f.file_path, f.line_start
```

### Find All Endpoints Handled by a Function

```cypher
MATCH (e:Endpoint)-[:HANDLES]->(f:Function {name: 'registerHandler'})
RETURN e.http_method, e.path
```

### API Call Graph

```cypher
// Find what an endpoint calls
MATCH (e:Endpoint {path: '/register'})-[:HANDLES]->(f:Function)-[:CALLS*]->(called:Function)
RETURN e.path, f.name, called.name
```

---

## Expected Results (Sock Shop)

### Front-End Service (Express.js)

| Method | Path | Handler | File |
|--------|------|---------|------|
| GET | /customers/:id | anonymous | api/user/index.js:7 |
| GET | /customers | anonymous | api/user/index.js:14 |
| GET | /addresses | anonymous | api/user/index.js:17 |
| GET | /cards | anonymous | api/user/index.js:20 |
| POST | /customers | anonymous | api/user/index.js:25 |
| POST | /addresses | anonymous | api/user/index.js:45 |
| POST | /cards | anonymous | api/user/index.js:109 |
| DELETE | /customers/:id | anonymous | api/user/index.js:130 |
| POST | /register | anonymous | api/user/index.js:180 |
| GET | /login | anonymous | api/user/index.js:250 |
| GET | /cart | anonymous | api/cart/index.js:12 |
| POST | /cart | anonymous | api/cart/index.js:65 |
| DELETE | /cart/:id | anonymous | api/cart/index.js:42 |

**Expected:** ~30-40 endpoints from front-end

### User Service (Go + gorilla/mux)

| Method | Path | Handler | File |
|--------|------|---------|------|
| GET | /login | LoginEndpoint | api/transport.go:38 |
| POST | /register | RegisterEndpoint | api/transport.go:44 |
| GET | /customers | UserGetEndpoint | api/transport.go:50 |
| GET | /cards | CardGetEndpoint | api/transport.go:56 |
| GET | /addresses | AddressGetEndpoint | api/transport.go:62 |
| POST | /customers | UserPostEndpoint | api/transport.go:68 |
| POST | /addresses | AddressPostEndpoint | api/transport.go:74 |
| POST | /cards | CardPostEndpoint | api/transport.go:80 |
| DELETE | / | DeleteEndpoint | api/transport.go:86 |
| GET | /health | HealthEndpoint | api/transport.go:92 |

**Expected:** ~10-15 endpoints from user service

### Total Expected

**All Sock Shop Services:** ~50-70 API endpoints

---

## Testing Strategy

### Unit Tests

```python
def test_extract_go_routes():
    """Test Go route extraction."""
    code = '''
    r.Methods("GET").Path("/users").Handler(getUsersHandler)
    r.Methods("POST").Path("/users").Handler(createUserHandler)
    '''

    parser = GoParser()
    routes = parser._extract_api_routes(parse(code))

    assert len(routes) == 2
    assert routes[0].method == "GET"
    assert routes[0].path == "/users"

def test_extract_express_routes():
    """Test Express route extraction."""
    code = '''
    app.get("/users", function(req, res) {
        res.json(users);
    });
    app.post("/users", createUser);
    '''

    parser = JavaScriptParser()
    routes = parser._extract_api_routes(parse(code))

    assert len(routes) == 2
    assert routes[0].method == "GET"
    assert routes[1].handler == "createUser"
```

### Integration Tests

```python
def test_api_route_ingestion():
    """Test full API route ingestion pipeline."""
    # Ingest front-end service
    result = ingest_service("front-end", "sock_shop")

    # Query Neo4j for endpoints
    with neo4j_client.driver.session() as session:
        result = session.run("""
            MATCH (e:Endpoint {namespace: 'sock_shop'})
            RETURN count(e) as endpoint_count
        """)
        count = result.single()['endpoint_count']

        assert count > 0
        print(f"Found {count} API endpoints")
```

---

## Benefits

1. **API Discovery** - Automatically map all API endpoints
2. **Handler Tracking** - Know which function handles each endpoint
3. **Impact Analysis** - Find all endpoints affected by function changes
4. **Documentation** - Auto-generate API documentation
5. **Testing** - Generate test cases for all endpoints
6. **Monitoring** - Track which endpoints are used

---

## Future Enhancements

1. **Parameter Extraction** - Extract path/query/body parameters
2. **Response Schema** - Infer response types from handler
3. **Authentication** - Detect auth middleware
4. **Rate Limiting** - Detect rate limit middleware
5. **OpenAPI Generation** - Generate OpenAPI/Swagger specs
6. **Request Validation** - Detect validation middleware

---

## Implementation Status

**Status:** ✅ COMPLETED - All major frameworks implemented

**Languages Implemented:**
- ✅ Go (gorilla/mux, http.HandleFunc)
- ✅ JavaScript (Express.js)
- ✅ Java (Spring Boot) - TESTED AND WORKING
- ✅ PHP (Laravel)
- ✅ Python (FastAPI, Flask)
- ✅ Ruby (Rails)

**Implementation Files:**
- `ingestion/parsers/go_parser.py` - Go route detection
- `ingestion/parsers/javascript_parser.py` - Express route detection
- `ingestion/parsers/java_parser.py` - Spring Boot route detection
- `ingestion/parsers/php_parser.py` - Laravel route detection
- `ingestion/parsers/python_parser.py` - FastAPI/Flask route detection
- `ingestion/parsers/ruby_parser.py` - Rails route detection
- `ingestion/parsers/api_routes.py` - Shared APIRoute model
- `databases/neo4j/schema.py` - APIEndpoint node and HANDLES relationship

**Testing:**
- Java parser: ✅ WORKING (3 routes detected from test file)
- Go parser: ⚠️ Implemented, needs debugging
- JavaScript parser: ⚠️ Implemented, needs debugging
- PHP parser: ⏳ Not yet tested
- Python parser: ⏳ Not yet tested
- Ruby parser: ⏳ Not yet tested

**Priority:** HIGH (core MVP feature)

---

**Last Updated:** 2025-11-20
**Next Step:** Test parsers with real code and integrate into ingestion pipeline
