import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, random_split
import os
import time
import matplotlib.pyplot as plt
from sqlalchemy.ext.asyncio import AsyncSession

from .dataset import CryptoDataset
from .data_loader import DataLoader as DbLoader
from .model import ModelFactory
from .callbacks import EarlyStopping  # <--- Import class mới
from ..config import settings

# Cấu hình Matplotlib để chạy không cần màn hình (Headless mode cho Docker)
plt.switch_backend('Agg')

class CryptoTrainer:
    def __init__(self, db_session: AsyncSession, symbol: str, model_type: str = "lstm", config: dict = None):
        self.db = db_session
        self.symbol = symbol
        self.model_type = model_type
        self.config = config if config else {} 
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        
        # Lấy config training
        self.train_cfg = self.config.get('training', {})

    def _get_optimizer(self, model_params):
        """Factory chọn Optimizer dựa trên Config"""
        opt_name = self.train_cfg.get('optimizer', 'adam').lower()
        lr = float(self.train_cfg.get('learning_rate', 0.001))
        wd = float(self.train_cfg.get('weight_decay', 1e-5))

        print(f"🔧 Optimizer: {opt_name.upper()} | LR: {lr}")

        if opt_name == 'sgd':
            return optim.SGD(model_params, lr=lr, weight_decay=wd, momentum=0.9)
        elif opt_name == 'rmsprop':
            return optim.RMSprop(model_params, lr=lr, weight_decay=wd)
        else:
            return optim.Adam(model_params, lr=lr, weight_decay=wd)

    def _get_scheduler(self, optimizer):
        """Factory chọn Scheduler"""
        sch_cfg = self.train_cfg.get('scheduler', {})
        sch_type = sch_cfg.get('type', 'none').lower()
        
        if sch_type == 'steplr':
            step_size = sch_cfg.get('step_size', 10)
            gamma = sch_cfg.get('gamma', 0.5)
            print(f"📉 Scheduler: StepLR (Step: {step_size}, Gamma: {gamma})")
            return optim.lr_scheduler.StepLR(optimizer, step_size=step_size, gamma=gamma)
        
        elif sch_type == 'plateau':
            patience = sch_cfg.get('patience', 3)
            print(f"📉 Scheduler: ReduceLROnPlateau (Patience: {patience})")
            return optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='min', patience=patience, factor=0.5)
            
        return None

    def _plot_loss(self, history, save_dir):
        """Vẽ biểu đồ Loss và lưu ra file ảnh"""
        plt.figure(figsize=(10, 6))
        plt.plot(history['train_loss'], label='Train Loss', color='blue')
        plt.plot(history['val_loss'], label='Validation Loss', color='orange')
        plt.title(f'Training Process: {self.symbol} ({self.model_type})')
        plt.xlabel('Epochs')
        plt.ylabel('Loss')
        plt.legend()
        plt.grid(True)
        
        plot_path = os.path.join(save_dir, f"{self.symbol.replace('/','-')}_loss.png")
        plt.savefig(plot_path)
        plt.close() # Giải phóng bộ nhớ
        return plot_path

    async def train(self, epochs: int = 20, batch_size: int = 32):
        print(f"📥 Đang tải dữ liệu cho {self.symbol}...")
        db_loader = DbLoader(self.db)
        # Tăng limit lên để tận dụng sức mạnh training
        df = await db_loader.get_historical_data(self.symbol, timeframe="1h", limit=50000)
        
        if df.empty:
            raise ValueError("Không có dữ liệu!")

        # Chuẩn bị Data
        seq_len = self.config.get("data", {}).get("sequence_length", 60)
        full_dataset = CryptoDataset(df, sequence_length=seq_len, is_training=True)
        train_size = int(0.8 * len(full_dataset))
        test_size = len(full_dataset) - train_size
        train_dataset, test_dataset = random_split(full_dataset, [train_size, test_size])
        
        train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
        test_loader = DataLoader(test_dataset, batch_size=batch_size, shuffle=False)
        
        # Khởi tạo Model, Loss, Optimizer, Scheduler
        input_size = full_dataset.features.shape[1]
        model = ModelFactory.create_model(self.model_type, self.config, input_size)
        model.to(self.device)

        criterion = nn.MSELoss()
        optimizer = self._get_optimizer(model.parameters())
        scheduler = self._get_scheduler(optimizer)

        # Khởi tạo Early Stopping
        es_cfg = self.train_cfg.get('early_stopping', {})
        early_stopping = EarlyStopping(
            patience=es_cfg.get('patience', 5),
            min_delta=es_cfg.get('min_delta', 0.0001),
            verbose=True
        )

        print(f"🚀 Bắt đầu Training trên {self.device}...")
        history = {'train_loss': [], 'val_loss': []}
        start_time = time.time()

        for epoch in range(epochs):
            # --- TRAIN ---
            model.train()
            train_loss = 0.0
            for X_batch, y_batch in train_loader:
                X_batch, y_batch = X_batch.to(self.device), y_batch.to(self.device)
                
                outputs = model(X_batch)
                loss = criterion(outputs.squeeze(), y_batch)
                
                optimizer.zero_grad()
                loss.backward()
                optimizer.step()
                train_loss += loss.item()
            
            # --- VALIDATE ---
            model.eval()
            val_loss = 0.0
            with torch.no_grad():
                for X_batch, y_batch in test_loader:
                    X_batch, y_batch = X_batch.to(self.device), y_batch.to(self.device)
                    outputs = model(X_batch)
                    loss = criterion(outputs.squeeze(), y_batch)
                    val_loss += loss.item()

            avg_train_loss = train_loss / len(train_loader)
            avg_val_loss = val_loss / len(test_loader)
            
            # Cập nhật Scheduler (nếu có)
            if scheduler:
                if isinstance(scheduler, optim.lr_scheduler.ReduceLROnPlateau):
                    scheduler.step(avg_val_loss)
                else:
                    scheduler.step()
                
                # In ra Learning Rate hiện tại
                current_lr = optimizer.param_groups[0]['lr']
            
            history['train_loss'].append(avg_train_loss)
            history['val_loss'].append(avg_val_loss)

            print(f"Epoch [{epoch+1}/{epochs}] | LR: {optimizer.param_groups[0]['lr']:.6f} | Train: {avg_train_loss:.6f} | Val: {avg_val_loss:.6f}")

            # --- CHECK EARLY STOPPING ---
            early_stopping(avg_val_loss, model)
            if early_stopping.early_stop:
                print("🛑 Early stopping triggered!")
                break

        # Load lại model tốt nhất trước khi lưu
        if early_stopping.best_model_state:
             model.load_state_dict(early_stopping.best_model_state)

        # --- LƯU KẾT QUẢ ---
        save_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "saved_models")
        os.makedirs(save_dir, exist_ok=True)
        
        # 1. Lưu Model (.pth)
        save_path = self._save_model(model, full_dataset.get_scaler(), save_dir)
        
        # 2. Vẽ biểu đồ Loss (.png)
        plot_path = self._plot_loss(history, save_dir)
        
        duration = time.time() - start_time
        return {
            "status": "success",
            "model_type": self.model_type,
            "duration": f"{duration:.2f}s",
            "epochs_run": len(history['train_loss']),
            "best_val_loss": early_stopping.best_loss,
            "paths": {
                "model": save_path,
                "plot": plot_path
            }
        }

    def _save_model(self, model, scaler, save_dir):
        filename = f"{self.symbol.replace('/','-')}_{self.model_type}.pth"
        filepath = os.path.join(save_dir, filename)
        checkpoint = {
            'model_state_dict': model.state_dict(),
            'config': self.config,
            'scaler': scaler,
            'input_size': model.lstm.input_size if hasattr(model, 'lstm') else 11
        }
        torch.save(checkpoint, filepath)
        return filepath