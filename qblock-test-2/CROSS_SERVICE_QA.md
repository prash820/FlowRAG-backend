# FlowRAG Cross-Service Q&A for QBlock Platform

This document contains questions and answers that specifically demonstrate **cross-service retrieval** - where FlowRAG searches across multiple connected namespaces to provide comprehensive answers about how different QBlock services work together.

**All queries use `include_cross_service: true`**

---

## Q1: Complete Order Fetch Flow (Mobile → ShopDataProvider → Shopify)

**Question:** Trace the complete flow from when a user requests orders in the mobile app to when data is fetched from Shopify API

**Starting Namespace:** `qblock-mobile`
**Services Searched:** qblock-mobile, qblock-shop-data, qblock-label-service, qblock-auth-service

### Answer

To trace the complete flow from when a user requests orders in the mobile app to when data is fetched from the Shopify API, we'll follow the sequence of operations as described by the provided context. This flow involves multiple services and components working together to fulfill the request.

1. **User Requests Orders in Mobile App**: The user initiates a request to view all pending orders through the mobile application.

2. **Mobile App Contacts Order Service**: The mobile app, specifically through its `OrderService` class located in `order_service.dart`, handles the request. The `getAllPendingOrders` method is invoked to fetch all pending orders. This method constructs a GET request to the `$_baseUrl/api/getAllPendingOrders` endpoint, which is part of the `qblock-shop-data` service.

3. **Shop Data Provider Service Receives Request**: The request is received by the `qblock-shop-data` service, specifically at the `/api/getAllPendingOrders` route defined in `route.ts`. This route handler begins by authenticating the request. Upon successful authentication, it proceeds to fetch all pending orders.

4. **Fetching Orders from Shopify**: The route handler iterates over all shop IDs obtained from the `shopKeyProviderService`. For each shop, it checks the platform associated with the shop ID. If the platform is "shopify", it invokes the `getPendingOrders` method from the `shopifyService`.

5. **Shopify Service**: The `shopifyService`'s `getOrders` method is called with parameters such as `shopId`, `status`, `limit`, and `page`. This method creates an API client configured for the Shopify API, constructs a request URL using the shop's ID, and sends a GET request to Shopify's `/admin/api/${apiVersion}/orders.json` endpoint. The response from Shopify contains order data in Shopify's format.

6. **Data Transformation**: The Shopify order data is then transformed into a common order format by the `getOrders` method. This transformation includes mapping fields from Shopify's order format to the application's order format, such as order ID, status, total price, currency code, and line items.

7. **Response to Mobile App**: Once all orders have been fetched and transformed, the `GET` function in `route.ts` compiles this data into a single response object. This object includes data for all shops and platforms, including Shopify. The response is then sent back to the mobile app's `OrderService`.

8. **Mobile App Processes Response**: Upon receiving the response, the `OrderService` in the mobile app parses the JSON data to extract and construct order objects. These order objects are then made available to the user interface for display to the user.

### Flow Diagram
```
┌─────────────────┐      ┌─────────────────────┐      ┌─────────────────┐
│  qblock-mobile  │      │  qblock-shop-data   │      │   Shopify API   │
│  (Flutter App)  │      │ (ShopDataProvider)  │      │   (External)    │
└────────┬────────┘      └──────────┬──────────┘      └────────┬────────┘
         │                          │                          │
         │  GET /api/getAllPending  │                          │
         │─────────────────────────>│                          │
         │                          │                          │
         │                          │  GET /admin/api/orders   │
         │                          │─────────────────────────>│
         │                          │                          │
         │                          │<─────────────────────────│
         │                          │   Shopify Order Data     │
         │                          │                          │
         │                          │  Transform to Common     │
         │                          │  Order Format            │
         │                          │                          │
         │<─────────────────────────│                          │
         │   Unified Order Response │                          │
         │                          │                          │
```

---

## Q2: Label Creation Across Services (Mobile → ShopDataProvider → LabelCreationOrchestrator)

**Question:** How do the mobile app, ShopDataProvider, and LabelCreationOrchestrator work together to create shipping labels?

**Starting Namespace:** `qblock-mobile`
**Services Searched:** qblock-mobile, qblock-shop-data, qblock-label-service, qblock-auth-service

### Answer

The process of creating shipping labels in the described system involves multiple components: the mobile app, ShopDataProvider, LabelCreationOrchestrator, and various services and APIs. Here's how these components work together:

1. **Mobile App (qblock-mobile)**: The mobile app acts as the front-end interface for users (likely merchants or shipping managers) to initiate the creation of shipping labels for pending orders. It interacts with various services to fetch order details, authenticate users, and trigger the label creation process.

2. **OrderService**: Within the mobile app, the `OrderService` is responsible for fetching all pending orders from the ShopDataProvider via the `$_baseUrl/api/getAllPendingOrders` and `SHOP_DATA_PROVIDER_URL` endpoints. This service acts as a bridge between the mobile app and the backend services, fetching necessary order data to prepare for shipping label creation.

3. **ShopDataProvider (qblock-shop-data)**: This backend service provides detailed information about orders, including shipping details required for label creation. It is queried by the mobile app's `OrderService` to retrieve pending orders that need shipping labels.

4. **LabelCreationService**: Also within the mobile app, this service is tasked with the actual creation of shipping labels. It takes the order details, including shipping information, and sends them to the LabelCreationOrchestrator via the `LABEL_CREATION_ORCHESTRATOR_URL`. This service prepares the data and handles the communication with the LabelCreationOrchestrator.

5. **LabelCreationOrchestrator (qblock-label-service)**: This component is a backend service that orchestrates the creation of shipping labels. It receives requests from the LabelCreationService, processes the shipping details, and interacts with external shipping services (like ShipStation) to generate shipping labels. It handles the complexities of communicating with shipping carriers, generating labels, and possibly scheduling pickups.

6. **GatekeeperService**: This service is involved in the authentication process and possibly in the final steps of the label creation process, such as storing information about created labels in a database. It ensures that only authenticated requests are processed and might be responsible for logging or tracking label creation events.

7. **Database Interaction**: After a label is successfully created, details about the label (such as tracking numbers and shipment costs) might be stored in a database for record-keeping and future reference. This step is crucial for order fulfillment and tracking.

8. **ShippingLabelRequest and Response Handling**: The `ShippingLabelRequest` class defines the structure of the request needed for creating a label, including order ID, weight, dimensions, and other optional parameters like `testLabel` and `pickupNotes`. The LabelCreationOrchestrator uses this request format to process and generate labels. Upon successful label creation, the orchestrator returns a response which is then handled by the mobile app.

### Flow Diagram
```
┌─────────────────┐      ┌─────────────────────┐      ┌─────────────────────┐
│  qblock-mobile  │      │  qblock-shop-data   │      │qblock-label-service │
│  (Flutter App)  │      │ (ShopDataProvider)  │      │(LabelCreationOrch.) │
└────────┬────────┘      └──────────┬──────────┘      └──────────┬──────────┘
         │                          │                            │
         │  1. GET pending orders   │                            │
         │─────────────────────────>│                            │
         │<─────────────────────────│                            │
         │    Order data with       │                            │
         │    shipping details      │                            │
         │                          │                            │
         │  2. POST create label    │                            │
         │──────────────────────────────────────────────────────>│
         │                          │                            │
         │                          │                            │  3. Create
         │                          │                            │     label via
         │                          │                            │     ShipStation
         │                          │                            │
         │<──────────────────────────────────────────────────────│
         │    Label data (tracking, │                            │
         │    PDF URL, cost)        │                            │
```

---

## Q3: Authentication Flow Across All Services

**Question:** What is the authentication flow between all QBlock services? How does ShopKeyProvider provide credentials to other services?

**Starting Namespace:** `qblock-auth-service`
**Services Searched:** qblock-auth-service, qblock-mobile, qblock-shop-data, qblock-label-service

### Answer

The authentication flow between all QBlock services involves multiple components, including the AuthService, GatekeeperService, and the use of API keys or JWT tokens for securing communication between services. Here's a detailed breakdown:

1. **AuthService**:
   - Located in `auth_service.dart`, AuthService is responsible for validating login credentials against expected values stored in the environment variables. It uses SHA-256 hashing for password validation.
   - It provides functionality to check if a user is authenticated and to log in or log out a user. The login process involves validating the email and hashed password against stored values.

2. **GatekeeperService**:
   - Found in `gatekeeper_service.dart`, GatekeeperService interacts with the QBlock's Gatekeeper authentication service. It fetches JWT tokens from the Gatekeeper by sending a service ID and permissions request. This token is then used for authenticating requests to other services within the QBlock ecosystem.
   - The service checks for a valid configuration, including the Gatekeeper URL and whether authentication is enabled, before attempting to fetch a token.

3. **ShopKeyProvider**:
   - ShopKeyProvider plays a role in managing and providing shop-specific authentication tokens, as indicated by the `initializeDatabase` function in `db.ts`. This function sets up a database table for storing shop authentication tokens, including access tokens, refresh tokens, and other metadata.
   - These tokens are essential for accessing shop-specific data and services, ensuring that each shop's data is accessed securely and only by authorized services or users.

4. **OrderService and LabelCreationService**:
   - Both services demonstrate how authentication headers are constructed for outgoing requests. Depending on the configuration (`_useJwtAuth`), they either use an API key or a JWT token (fetched from GatekeeperService) as part of the request headers to authenticate against other services or data providers.
   - The API key or JWT token is included in the headers of each request to ensure that the request is authenticated. For JWT, the header is `Authorization: Bearer <token>`, and for API key authentication, it's `x-api-key: <api_key>`.

5. **Authentication Flow**:
   - The flow starts with the AuthService validating user credentials. Upon successful login, the GatekeeperService may be invoked to fetch a JWT token for service-to-service communication.
   - Services like OrderService use either JWT tokens or API keys, based on the environment configuration, to authenticate requests to external services or internal APIs.
   - ShopKeyProvider, through its database initialization for storing auth tokens, suggests a mechanism for managing and providing these credentials for shop-specific operations.

### Flow Diagram
```
┌─────────────────┐      ┌─────────────────────┐      ┌─────────────────────┐
│  qblock-mobile  │      │ qblock-auth-service │      │  qblock-shop-data   │
│  (Flutter App)  │      │  (ShopKeyProvider)  │      │ (ShopDataProvider)  │
└────────┬────────┘      └──────────┬──────────┘      └──────────┬──────────┘
         │                          │                            │
         │  1. User Login           │                            │
         │  (AuthService validates) │                            │
         │                          │                            │
         │  2. GET shop-credentials │                            │
         │─────────────────────────>│                            │
         │<─────────────────────────│                            │
         │   JWT Token / API Keys   │                            │
         │                          │                            │
         │  3. Request with Bearer  │                            │
         │     token or x-api-key   │                            │
         │──────────────────────────────────────────────────────>│
         │                          │                            │
         │                          │  4. Validates token        │
         │                          │     via middleware         │
         │                          │                            │
```

---

## Q4: Etsy Orders + Label Service Collaboration

**Question:** When fetching Etsy orders, how do ShopDataProvider and LabelCreationOrchestrator collaborate to get shipping destination information?

**Starting Namespace:** `qblock-shop-data`
**Services Searched:** qblock-shop-data, qblock-mobile, qblock-label-service, qblock-auth-service

### Answer

The collaboration between `ShopDataProvider` and `LabelCreationOrchestrator` to get shipping destination information for Etsy orders involves several steps and components across different services:

1. **Fetching Orders from Etsy**: Initially, orders are fetched from Etsy. This is done through the `OrderService` in the `qblock-mobile` service, which calls an API endpoint to get all pending orders.

2. **ShopDataProvider Middleware**: After orders are fetched, the `ShopDataProvider` acts as a middleware. The `OrderService` makes a GET request to the `SHOP_DATA_PROVIDER_URL`. The `ShopDataProvider` is responsible for processing or enriching order data fetched from Etsy. This might include consolidating order details, preparing them for label creation, and possibly fetching additional information required for shipping.

3. **Shipping Destination Information**: The `Order` class in the `ShopDataProvider` includes a `destination` field, which contains shipping destination information such as name, company, address, and phone number. This information is crucial for creating shipping labels and is populated from the data fetched from Etsy or through additional processing done by the `ShopDataProvider`.

4. **LabelCreationOrchestrator Service**: The `LabelCreationOrchestrator` service, specifically through its `createLabel` function, takes the order information, including shipping destination details, and creates a shipping label. This process involves:
   - Validating the shipping address
   - Creating a payload that includes the order ID, shipping date, weight, dimensions, and other relevant shipping information
   - Making an API call to an external service (like ShipStation) to create the shipping label
   - Handling the response, which includes the shipping label information, and possibly scheduling a pickup

5. **API Calls and Data Flow**: The collaboration involves API calls where the `ShopDataProvider` makes a POST request to the `LabelCreationOrchestrator` service to initiate the shipping label creation process. This request includes the shipping destination information along with other order details.

6. **ShippingLabelRequest**: The `ShippingLabelRequest` interface defines the structure of the request expected by the `LabelCreationOrchestrator`. This includes the order ID, weight, dimensions, and optionally, test label flag, pickup notes, ship date, and warehouse ID.

### Flow Diagram
```
┌─────────────────────┐      ┌─────────────────────┐      ┌─────────────────┐
│  qblock-shop-data   │      │qblock-label-service │      │   ShipStation   │
│ (ShopDataProvider)  │      │(LabelCreationOrch.) │      │   (External)    │
└──────────┬──────────┘      └──────────┬──────────┘      └────────┬────────┘
           │                            │                          │
           │  Fetch Etsy Orders         │                          │
           │  (includes destinations)   │                          │
           │                            │                          │
           │  POST /api/shipping/       │                          │
           │       shipments            │                          │
           │───────────────────────────>│                          │
           │  (receipt_ids,             │                          │
           │   shipment_status)         │                          │
           │                            │                          │
           │                            │  Create Label Request    │
           │                            │─────────────────────────>│
           │                            │<─────────────────────────│
           │                            │  Label + Tracking        │
           │                            │                          │
           │<───────────────────────────│                          │
           │  Destination + Label Info  │                          │
```

---

## Q5: End-to-End Order Fulfillment Flow

**Question:** Describe the end-to-end data flow when a merchant views and fulfills an order - from mobile app through all backend services

**Starting Namespace:** `qblock-mobile`
**Services Searched:** qblock-mobile, qblock-shop-data, qblock-label-service, qblock-auth-service

### Answer

The end-to-end data flow when a merchant views and fulfills an order through the mobile app involves several backend services and steps:

1. **Merchant Views Orders:**
   - The merchant uses the `qblock-mobile` app to view orders. The app's `OrderService` makes a `GET` request to `$_baseUrl/api/getAllPendingOrders` to fetch all pending orders.
   - This request is handled by the `qblock-shop-data` service, which aggregates order data from various platforms like Shopify or Etsy. This aggregation involves fetching order data tailored to the shop's platform and then mapping this data to a unified order format.

2. **Merchant Selects an Order for Fulfillment:**
   - Upon selecting an order from the list in the mobile app, the `_navigateToFulfillment` method is called, setting the selected order in the provider and navigating to the fulfillment screen.

3. **Order Fulfillment Screen:**
   - The `OrderFulfillmentScreen` is displayed, where the app fetches detailed order information, possibly involving additional calls to backend services for up-to-date data.
   - The screen allows the merchant to select products from the order and choose a fulfillment method. This process involves various providers to manage state within the app.

4. **Submitting the Order for Fulfillment:**
   - Once the merchant finalizes the products to fulfill and selects a fulfillment method, they submit the order for fulfillment by calling `_submitOrder`.
   - This process involves the `orderService` making a call to a backend service responsible for handling order fulfillment, updating the order status in the database, and possibly integrating with third-party services for shipping and logistics.
   - The backend service might need to interact with external APIs, such as ShipStation, to create shipping labels or track shipments.

5. **Order Fulfillment Confirmation:**
   - Upon successful submission, the app updates the UI to reflect the submission status.
   - If successful, the merchant might be presented with options to print shipping labels or view shipment tracking information.

6. **Authentication and Authorization:**
   - Throughout this process, authentication and authorization are managed by the `qblock-auth-service`, ensuring that only authorized users can view and manage orders.

7. **Label Creation:**
   - For shipping, the `LabelCreationService` in the mobile app interacts with the `qblock-label-service` to generate or fetch shipping labels for the selected order.

### Complete Flow Diagram
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  qblock-mobile  │    │qblock-auth-svc  │    │qblock-shop-data │    │qblock-label-svc │
│  (Flutter App)  │    │(ShopKeyProvider)│    │(ShopDataProvider│    │(LabelCreation)  │
└────────┬────────┘    └────────┬────────┘    └────────┬────────┘    └────────┬────────┘
         │                      │                      │                      │
         │  1. Login/Auth       │                      │                      │
         │─────────────────────>│                      │                      │
         │<─────────────────────│                      │                      │
         │     JWT Token        │                      │                      │
         │                      │                      │                      │
         │  2. GET orders       │                      │                      │
         │─────────────────────────────────────────────>                      │
         │                      │                      │                      │
         │                      │                      │  Fetch from          │
         │                      │                      │  Shopify/Etsy        │
         │                      │                      │                      │
         │<─────────────────────────────────────────────                      │
         │     Order List       │                      │                      │
         │                      │                      │                      │
         │  3. Select Order     │                      │                      │
         │  → Fulfillment Screen│                      │                      │
         │                      │                      │                      │
         │  4. Submit Order     │                      │                      │
         │─────────────────────────────────────────────>                      │
         │                      │                      │  Update status       │
         │                      │                      │                      │
         │  5. Create Label     │                      │                      │
         │────────────────────────────────────────────────────────────────────>
         │                      │                      │                      │
         │<────────────────────────────────────────────────────────────────────
         │  Label + Tracking    │                      │                      │
         │                      │                      │                      │
         │  6. Show confirmation│                      │                      │
         │     to merchant      │                      │                      │
```

---

## Summary

| # | Question | Starting NS | Services Involved | Key Integration Points |
|---|----------|-------------|-------------------|----------------------|
| Q1 | Order fetch flow | qblock-mobile | mobile → shop-data → Shopify | OrderService → ShopifyService → Shopify API |
| Q2 | Label creation | qblock-mobile | mobile → shop-data → label-service | LabelCreationService → LabelCreationOrchestrator → ShipStation |
| Q3 | Authentication flow | qblock-auth-service | auth → mobile → shop-data | GatekeeperService → JWT tokens → All services |
| Q4 | Etsy + Label collaboration | qblock-shop-data | shop-data → label-service | POST /api/shipping/shipments for destination info |
| Q5 | End-to-end fulfillment | qblock-mobile | All 4 services | Complete merchant workflow |

---

## How Cross-Service Retrieval Works

When `include_cross_service: true` is set:

1. **Namespace Discovery**: FlowRAG queries Neo4j for all `CALLS_API` relationships connected to the starting namespace
2. **Multi-Namespace Search**: Vector search runs across ALL connected namespaces
3. **Graph Context**: Cross-service API call information is included in the response context
4. **Combined Results**: Results from all namespaces are merged and ranked by relevance

This enables FlowRAG to answer questions that span multiple services, tracing data flows and understanding how components interact across the entire QBlock platform.

---

*Generated by FlowRAG on December 2, 2024*
*All queries used `include_cross_service: true` for comprehensive cross-service retrieval*
