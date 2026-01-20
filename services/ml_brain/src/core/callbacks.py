import numpy as np
import torch

class EarlyStopping:
    def __init__(self, patience=5, min_delta=0, verbose=False):
        """
        Args:
            patience (int): Số epoch chấp nhận chờ đợi khi loss không giảm.
            min_delta (float): Ngưỡng thay đổi tối thiểu để được coi là cải thiện.
            verbose (bool): In thông báo ra màn hình.
        """
        self.patience = patience
        self.min_delta = min_delta
        self.verbose = verbose
        self.counter = 0
        self.best_loss = None
        self.early_stop = False
        self.best_model_state = None

    def __call__(self, val_loss, model):
        # Lần đầu chạy
        if self.best_loss is None:
            self.best_loss = val_loss
            self.best_model_state = model.state_dict()
        
        # Nếu Loss tăng hoặc giảm không đáng kể
        elif val_loss > self.best_loss - self.min_delta:
            self.counter += 1
            if self.verbose:
                print(f'   ⏳ EarlyStopping counter: {self.counter} out of {self.patience}')
            if self.counter >= self.patience:
                self.early_stop = True
        
        # Nếu tìm được Loss tốt hơn hẳn
        else:
            self.best_loss = val_loss
            self.best_model_state = model.state_dict() # Lưu lại trạng thái tốt nhất này
            self.counter = 0 # Reset bộ đếm