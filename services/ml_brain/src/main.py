import os 
import yaml
import torch
import numpy as np
import pandas as pd  # <--- THÊM: Cần để xử lý dữ liệu cho Backtest

from fastapi import FastAPI, Depends, Body
from sqlalchemy.ext.asyncio import AsyncSession

from .config import settings
from .database import get_db
from .core.data_loader import DataLoader
from .core.dataset import CryptoDataset

from .core.model import ModelFactory
from .core.trainer import CryptoTrainer

from .core.predictor import CryptoPredictor
from .core.backtester import Backtester # <--- THÊM: Import module Backtester

app = FastAPI(title=settings.PROJECT_NAME)

def load_config():
    config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.yaml")
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

@app.get("/")
async def root():
    """Health check endpoint for the ML Brain service."""
    return {
        "service": "ML Brain",
        "status": "Healthy 🧠",
        "pytorch_version": torch.__version__,
        "cuda_available": torch.cuda.is_available()
    }

# --- CÁC API DEBUG (Giữ nguyên) ---
@app.get("/debug/load-data/{symbol}")
async def debug_load_data(symbol: str, db: AsyncSession = Depends(get_db)):
    formatted_symbol = symbol.replace("-", "/").upper()
    loader = DataLoader(db)
    df = await loader.get_historical_data(formatted_symbol, timeframe="1h", limit=5)
    if df.empty:
        return {"status": "empty", "message": "Chưa tìm thấy dữ liệu. Hãy chạy Data Engine sync trước!"}
    return {"status": "success", "rows_loaded": len(df), "preview": df.to_dict(orient="index")}

@app.get("/debug/process-data/{symbol}")
async def debug_process_data(symbol: str, db: AsyncSession = Depends(get_db)):
    formatted_symbol = symbol.replace("-", "/").upper()
    loader = DataLoader(db)
    df = await loader.get_historical_data(formatted_symbol, timeframe="1h", limit=500)
    if df.empty or len(df) < 100:
        return {"status": "error", "message": "Cần ít nhất 100 nến để test"}
    dataset = CryptoDataset(df, sequence_length=60)
    sample_X, sample_y = dataset[0]
    return {
        "status": "success", 
        "original_count": len(df), 
        "processed_count": len(dataset), 
        "feature_shape": str(sample_X.shape), 
        "target_shape": str(sample_y.shape)
    }

@app.post("/debug/build-model/{model_type}")
async def debug_build_model(model_type: str, custom_config: dict = Body(None)):
    full_config = load_config()
    if custom_config and model_type in full_config:
        full_config[model_type].update(custom_config)
    data_cfg = full_config['data']
    input_size = data_cfg['input_size']
    seq_len = data_cfg['sequence_length']
    try:
        model = ModelFactory.create_model(model_type, full_config, input_size)
        dummy_input = torch.randn(4, seq_len, input_size)
        output = model(dummy_input)
        return {"status": "success", "model_type": model_type, "test_output_shape": str(output.shape)}
    except Exception as e:
        return {"status": "error", "message": str(e)}

# --- API TRAIN MODEL ---
@app.post("/api/v1/train/{symbol}")
async def train_model(
    symbol: str, 
    model_type: str = "lstm",
    epochs: int = 10,
    batch_size: int = 32,
    db: AsyncSession = Depends(get_db)
):
    formatted_symbol = symbol.replace("-", "/").upper()
    full_config = load_config()
    
    # Cập nhật config nóng từ request parameters nếu cần (Optimizer, LR...)
    # Ở đây dùng mặc định từ file YAML, nhưng override learning rate cho chắc
    full_config['training']['learning_rate'] = 0.001 

    try:
        trainer = CryptoTrainer(db, formatted_symbol, model_type, full_config)
        result = await trainer.train(epochs=epochs, batch_size=batch_size)
        return result
    except Exception as e:
        return {"status": "error", "message": str(e)}

# --- API DỰ ĐOÁN & BACKTEST (ĐÃ SỬA CHỮA) ---
@app.post("/api/v1/evaluate/{symbol}")
async def evaluate_model(
    symbol: str, 
    model_type: str = "lstm",
    initial_capital: float = 1000, # <--- THÊM: Nhận vốn từ Dashboard
    db: AsyncSession = Depends(get_db)
):
    formatted_symbol = symbol.replace("-", "/").upper()
    
    try:
        # 1. Dự đoán (Predict)
        predictor = CryptoPredictor(formatted_symbol, model_type)
        loader = DataLoader(db)
        
        # Lấy 1000 nến gần nhất để test
        df_raw = await loader.get_historical_data(formatted_symbol, timeframe="1h", limit=1000)
        
        if df_raw.empty:
            return {"status": "error", "message": "Không đủ dữ liệu để backtest (Hãy tải thêm dữ liệu)"}

        eval_result = predictor.evaluate(df_raw)
        
        # 2. Backtest (Chạy mô phỏng kiếm tiền)
        # Tạo DataFrame tạm để Backtester xử lý
        df_backtest = pd.DataFrame({
            'timestamps': eval_result['timestamps'],
            'actual': eval_result['actual'],
            'predicted': eval_result['predicted']
        })
        
        # Khởi tạo Backtester với vốn user nhập và phí 0.1%
        backtester = Backtester(initial_capital=initial_capital, fee=0.001)
        bt_result = backtester.run(df_backtest, threshold=0.005) # Ngưỡng 0.5%
        
        # 3. Vẽ biểu đồ & Trả kết quả
        # Lưu vào thư mục saved_models để Dashboard map volume đọc được
        save_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "saved_models")
        os.makedirs(save_dir, exist_ok=True)
        
        plot_path = predictor.plot_comparison(eval_result, save_dir)
        
        # Tính sai số RMSE
        rmse = np.sqrt(np.mean((np.array(eval_result['actual']) - np.array(eval_result['predicted']))**2))

        # --- TRẢ VỀ JSON CHUẨN FORM MỚI (Khớp với Dashboard) ---
        return {
            "status": "success",
            "model_info": {
                "symbol": formatted_symbol,
                "type": model_type,
                "rmse": f"{rmse:.2f} USD"
            },
            "backtest_result": {
                "initial_capital": f"${bt_result['initial_capital']}",
                "final_equity": f"${bt_result['final_equity']}",
                "roi": f"{bt_result['roi_percent']}%",
                "total_trades": bt_result['total_trades']
            },
            "plot_url": plot_path
        }

    except Exception as e:
        print(f"Lỗi Evaluate: {str(e)}") # In ra log Docker để debug
        return {"status": "error", "message": str(e)}