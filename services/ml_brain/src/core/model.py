import torch
import torch.nn as nn

class LSTMModel(nn.Module):
    def __init__(self, input_size, hidden_size=64, num_layers=2, dropout=0.2):
        super(LSTMModel, self).__init__()
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True, dropout=dropout)
        self.fc = nn.Linear(hidden_size, 1)

    def forward(self, x):
        # x shape: (batch_size, seq_len, input_size)
        out, _ = self.lstm(x)
        # Lấy output tại bước thời gian cuối cùng
        out = out[:, -1, :] 
        out = self.fc(out)
        return out

class HybridModel(nn.Module):
    """
    Kết hợp LSTM và GRU chạy song song.
    """
    def __init__(self, input_size, hidden_size=64, num_layers=2, dropout=0.2):
        super(HybridModel, self).__init__()
        
        # Nhánh 1: LSTM
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True, dropout=dropout)
        
        # Nhánh 2: GRU
        self.gru = nn.GRU(input_size, hidden_size, num_layers, batch_first=True, dropout=dropout)
        
        # Lớp tổng hợp: Input của Linear sẽ gấp đôi hidden_size (do nối 2 vector lại)
        self.fc = nn.Linear(hidden_size * 2, 1)

    def forward(self, x):
        # 1. Chạy qua LSTM
        lstm_out, _ = self.lstm(x)
        lstm_last = lstm_out[:, -1, :] # Lấy trạng thái cuối
        
        # 2. Chạy qua GRU
        gru_out, _ = self.gru(x)
        gru_last = gru_out[:, -1, :]   # Lấy trạng thái cuối
        
        # 3. Nối 2 kết quả lại (Concatenate)
        # Ví dụ: LSTM ra vector 64, GRU ra vector 64 -> Nối thành 128
        combined = torch.cat((lstm_last, gru_last), dim=1)
        
        # 4. Đưa qua lớp Linear cuối cùng
        out = self.fc(combined)
        return out

class AttentionModel(nn.Module):
    """Mô hình LSTM với cơ chế Attention (Nâng cao)"""
    def __init__(self, input_size, hidden_size=64, num_layers=2, dropout=0.2):
        super(AttentionModel, self).__init__()
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True, dropout=dropout)
        self.attention = nn.Linear(hidden_size, 1)
        self.fc = nn.Linear(hidden_size, 1)
        
    def forward(self, x):
        lstm_out, _ = self.lstm(x) # (Batch, Seq, Hidden)
        
        # Tính trọng số Attention
        attn_weights = torch.softmax(self.attention(lstm_out), dim=1)
        
        # Nhân trọng số với output
        context = torch.sum(attn_weights * lstm_out, dim=1)
        
        out = self.fc(context)
        return out

class ModelFactory:
    @staticmethod
    def create_model(model_type, config, input_size):
        # Lấy tham số từ config, nếu không có thì dùng mặc định
        # Lưu ý: config có thể là dict to (full config) hoặc dict nhỏ (model config)
        if model_type in config:
            model_cfg = config[model_type]
        else:
            # Fallback nếu config đưa vào không chia theo model_type
            model_cfg = config 

        hidden_size = int(model_cfg.get('hidden_size', 64))
        num_layers = int(model_cfg.get('num_layers', 2))
        dropout = float(model_cfg.get('dropout', 0.2))
        
        print(f"🏗️ Building {model_type.upper()} Model: Input={input_size}, Hidden={hidden_size}, Layers={num_layers}")

        if model_type == "lstm":
            return LSTMModel(input_size, hidden_size, num_layers, dropout)
        elif model_type == "hybrid":
            return HybridModel(input_size, hidden_size, num_layers, dropout)
        elif model_type == "attention":
            return AttentionModel(input_size, hidden_size, num_layers, dropout)
        else:
            raise ValueError(f"Unknown model type: {model_type}")