import torch
import numpy as np
import pandas as pd
from torch.utils.data import Dataset
from sklearn.preprocessing import MinMaxScaler
from ..utils.indicators import add_indicators

class CryptoDataset(Dataset):
    def __init__(self, df: pd.DataFrame, sequence_length: int = 60, is_training: bool = True):
        self.sequence_length = sequence_length
        
        # 1. Thêm chỉ báo kỹ thuật (Đã bao gồm EMA, Bollinger Bands)
        self.data = add_indicators(df)
        
        # --- CẬP NHẬT DANH SÁCH CỘT MỚI TẠI ĐÂY ---
        feature_cols = [
            'close', 'open', 'high', 'low', 'volume',  # Dữ liệu gốc (5)
            'rsi', 'macd', 'sma_20',                   # Chỉ báo cũ (3)
            'ema_50', 'bb_upper', 'bb_lower'           # Chỉ báo MỚI (3)
        ]
        # Tổng cộng bây giờ chúng ta có 11 đặc trưng (Features)
        
        self.features = self.data[feature_cols].values
        
        # 2. Chuẩn hóa dữ liệu (Scaling) về khoảng [0, 1]
        self.scaler = MinMaxScaler(feature_range=(0, 1))
        
        if is_training:
            # Nếu đang train: Học cách scale từ dữ liệu này
            self.scaled_data = self.scaler.fit_transform(self.features)
        else:
            # Nếu đang predict: Dùng cách scale đã học (Logic này sẽ xử lý kỹ hơn ở phần Predictor)
            self.scaled_data = self.scaler.fit_transform(self.features)

        # 3. Tạo Sequences (Cửa sổ trượt)
        self.X, self.y = self._create_sequences(self.scaled_data)

    def _create_sequences(self, data):
        X, y = [], []
        # Chạy cửa sổ trượt
        # Ví dụ: data có 100 dòng, seq_len = 60
        # i chạy từ 60 đến 100
        for i in range(self.sequence_length, len(data)):
            # Lấy 60 dòng quá khứ (từ i-60 đến i)
            X.append(data[i-self.sequence_length:i])
            
            # Lấy giá trị tương lai cần dự đoán (Chính là giá Close tại thời điểm i)
            # Cột 0 là 'close'
            y.append(data[i, 0]) 
            
        return torch.tensor(np.array(X), dtype=torch.float32), torch.tensor(np.array(y), dtype=torch.float32)

    def __len__(self):
        return len(self.X)

    def __getitem__(self, idx):
        return self.X[idx], self.y[idx]
    
    def get_scaler(self):
        return self.scaler