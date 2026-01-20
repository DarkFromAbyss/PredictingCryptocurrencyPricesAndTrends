import torch
import numpy as np
import pandas as pd
import os
import matplotlib.pyplot as plt
from torch.utils.data import DataLoader

from .model import ModelFactory
from .dataset import CryptoDataset
from ..utils.indicators import add_indicators

# Cấu hình Matplotlib (Headless)
plt.switch_backend('Agg')

class CryptoPredictor:
    def __init__(self, symbol: str, model_type: str = "lstm"):
        self.symbol = symbol
        self.model_type = model_type
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model = None
        self.scaler = None
        self.config = None
        
        # Tự động load checkpoint khi khởi tạo
        self._load_checkpoint()

    def _load_checkpoint(self):
        # Tìm đường dẫn file model
        save_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "saved_models")
        filename = f"{self.symbol.replace('/','-')}_{self.model_type}.pth"
        filepath = os.path.join(save_dir, filename)

        if not os.path.exists(filepath):
            raise FileNotFoundError(f"❌ Chưa tìm thấy model tại: {filepath}. Hãy chạy Training trước!")

        print(f"🔄 Đang tải model từ: {filename}...")
        checkpoint = torch.load(filepath, map_location=self.device, weights_only=False)

        self.config = checkpoint['config']
        self.scaler = checkpoint['scaler'] # Quan trọng: Dùng lại thước đo cũ
        input_size = checkpoint['input_size']

        # Tái tạo kiến trúc Model
        self.model = ModelFactory.create_model(self.model_type, self.config, input_size)
        self.model.load_state_dict(checkpoint['model_state_dict'])
        self.model.to(self.device)
        self.model.eval() # Chế độ dự đoán (Tắt Dropout)

    def evaluate(self, df: pd.DataFrame):
        """
        Chạy dự đoán trên toàn bộ DataFrame để kiểm thử.
        """
        seq_len = self.config.get('data', {}).get('sequence_length', 60)
        
        # 1. Chuẩn bị dữ liệu (Feature Engineering)
        df_processed = add_indicators(df.copy(), self.config)
        
        # Hardcode thứ tự cột (Phải khớp 100% với lúc train trong dataset.py)
        feature_cols = [
            'close', 'open', 'high', 'low', 'volume', 
            'rsi', 'macd', 'sma_20', 'ema_50', 'bb_upper', 'bb_lower'
        ]
        
        data_values = df_processed[feature_cols].values
        
        # 2. Scale dữ liệu bằng Scaler đã load (Không fit mới!)
        scaled_data = self.scaler.transform(data_values)
        
        # 3. Tạo Sliding Window thủ công
        X, y_actual = [], []
        timestamps = []
        
        # Bắt đầu từ seq_len đến hết
        for i in range(seq_len, len(scaled_data)):
            X.append(scaled_data[i-seq_len:i])
            # y thực tế (lấy cột 0 là Close)
            y_actual.append(data_values[i, 0]) 
            timestamps.append(df_processed.index[i])

        X_tensor = torch.tensor(np.array(X), dtype=torch.float32).to(self.device)
        
        # 4. Dự đoán hàng loạt (Batch Prediction)
        batch_size = 64
        predictions = []
        
        with torch.no_grad():
            for i in range(0, len(X_tensor), batch_size):
                batch_X = X_tensor[i : i+batch_size]
                batch_out = self.model(batch_X) # Kết quả [Batch, 1] (đã scale)
                predictions.extend(batch_out.cpu().numpy().flatten())

        # 5. Inverse Scale (Đổi về giá USD)
        # Trick: Tạo dummy matrix để inverse transform
        pred_array = np.array(predictions).reshape(-1, 1)
        
        # Chúng ta cần một ma trận có 11 cột để inverse, nhưng chỉ quan tâm cột 0 (Close)
        dummy_matrix = np.zeros((len(predictions), len(feature_cols)))
        dummy_matrix[:, 0] = pred_array.flatten()
        
        # Inverse toàn bộ và chỉ lấy cột đầu tiên
        inv_matrix = self.scaler.inverse_transform(dummy_matrix)
        y_pred = inv_matrix[:, 0]

        return {
            "timestamps": timestamps,
            "actual": y_actual,
            "predicted": y_pred
        }

    def plot_comparison(self, eval_result, save_dir):
        """Vẽ biểu đồ Actual vs Predicted"""
        timestamps = eval_result['timestamps']
        actual = eval_result['actual']
        predicted = eval_result['predicted']
        
        # Chỉ lấy 200 điểm cuối cùng để vẽ cho rõ (Zoom in)
        zoom_range = 200
        if len(actual) > zoom_range:
            timestamps = timestamps[-zoom_range:]
            actual = actual[-zoom_range:]
            predicted = predicted[-zoom_range:]

        plt.figure(figsize=(12, 6))
        plt.plot(timestamps, actual, label='Thực tế (Actual)', color='blue', linewidth=2)
        plt.plot(timestamps, predicted, label='Dự đoán (Predicted)', color='red', linestyle='--', linewidth=2)
        
        plt.title(f'Evaluation: {self.symbol} - Real vs Predicted (Last {zoom_range} hours)')
        plt.xlabel('Time')
        plt.ylabel('Price (USDT)')
        plt.legend()
        plt.grid(True)
        plt.xticks(rotation=45)
        plt.tight_layout()

        filename = f"{self.symbol.replace('/','-')}_evaluation.png"
        filepath = os.path.join(save_dir, filename)
        plt.savefig(filepath)
        plt.close()
        return filepath