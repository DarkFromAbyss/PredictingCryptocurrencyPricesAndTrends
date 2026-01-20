import httpx
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from .config import settings

app = FastAPI(title=settings.PROJECT_NAME)

# Tạo Client dùng chung để tiết kiệm tài nguyên
timeout_config = httpx.Timeout(300.0, connect=60.0)
http_client = httpx.AsyncClient(timeout=timeout_config)

@app.on_event("shutdown")
async def shutdown_event():
    await http_client.aclose()

@app.get("/")
async def root():
    return {
        "message": "Welcome to Crypto System Gateway 🚪",
        "routes": {
            "data": "/api/v1/data/...",
            "ml": "/api/v1/ml/..."
        }
    }

# --- HÀM PROXY TỔNG QUÁT ---
async def forward_request(service_url: str, path: str, request: Request):
    """
    Chuyển tiếp request tới Microservice đích.
    """
    # 1. Xây dựng URL đích
    # service_url: http://data_engine:8000
    # path: sync/BTC-USDT
    url = f"{service_url}/api/v1/{path}"
    
    try:
        # 2. Forward method, headers, params, body
        response = await http_client.request(
            method=request.method,
            url=url,
            headers=request.headers, # Giữ nguyên Auth token nếu có
            params=request.query_params,
            content=await request.body()
        )
        
        # 3. Trả về kết quả y hệt service gốc
        return JSONResponse(content=response.json(), status_code=response.status_code)
        
    except httpx.RequestError as exc:
        return JSONResponse(
            status_code=503,
            content={"status": "error", "message": f"Service unavailable: {exc}"}
        )

# --- ĐỊNH TUYẾN (ROUTING) ---

# 1. Route cho Data Engine (Bắt đầu bằng /api/v1/data/...)
# Ví dụ: GET /api/v1/data/sync/BTC-USDT
@app.api_route("/api/v1/data/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def data_proxy(path: str, request: Request):
    return await forward_request(settings.DATA_ENGINE_URL, path, request)

# 2. Route cho ML Brain (Bắt đầu bằng /api/v1/ml/...)
# Ví dụ: POST /api/v1/ml/train/BTC-USDT
@app.api_route("/api/v1/ml/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def ml_proxy(path: str, request: Request):
    return await forward_request(settings.ML_BRAIN_URL, path, request)