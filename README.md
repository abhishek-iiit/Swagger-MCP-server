# Swagger-MCP-server

**Swagger-MCP-server** is a lightweight Model Context Protocol (MCP) server that interacts with the [Swagger Petstore API](https://petstore.swagger.io/) using an OpenAPI 3.0 specification. The server dynamically loads API tools defined in `openapi.json` and exposes endpoints that mimic those of the Petstore API using the `mcp.server.fastmcp` module.

---

## 📦 Features

- ✅ Dynamic loading of OpenAPI 3.0 spec (Petstore).
- 🐾 Full support for Petstore operations: Pets, Stores, Users.
- ⚡ Built using FastAPI.
- 🛠️ Utilizes the `mcp` server CLI and dynamic tool registration.

---

## 🚀 Installation Guide

1. **Clone the repository**

```bash
git clone https://github.com/abhishek-iiit/Swagger-MCP-server.git
cd Swagger-MCP-server
```

2. **Create and activate a virtual environment**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

3. **Install dependencies**

```bash
pip install -r requirements.txt
```

# 🧪 Running the Server

To start the server:

```bash
python main.py
```

This will start an MCP server that registers endpoints as defined in the openapi.json file and serves them via the Petstore API interface.

# 📚 API Endpoints

The server mirrors the Swagger Petstore API. It includes operations for:

## Pets

- Add a new pet
- Update an existing pet
- Find pets by status or tags
- Get pet by ID
- Delete a pet
- Stores
- Place an order
- Get order by ID
- Check inventory
- Users
- Create users
- Login/logout
- Get user by username
- Update/delete user

# 📦 Dependencies

Dependencies are listed in requirements.txt and include:

- fastapi: High-performance API framework.
- httpx: Async-compatible HTTP client.
- mcp[cli]: Model Context Protocol server framework.
- jsonschema: JSON Schema validation.

Install them via:

```bash
pip install -r requirements.txt
```
