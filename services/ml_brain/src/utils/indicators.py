import pandas as pd
import numpy as np

def add_indicators(df: pd.DataFrame, config: dict = None) -> pd.DataFrame:
    """
    Thêm các chỉ báo kỹ thuật vào DataFrame dựa trên config.
    
    Args:
        df: DataFrame chứa các cột ['close', 'open', 'high', 'low', 'volume']
        config: Dictionary chứa cấu hình (load từ config.yaml). 
                Nếu None, dùng giá trị mặc định.
    """
    # 1. Lấy tham số từ Config (hoặc dùng mặc định nếu thiếu)
    if config and 'indicators' in config:
        ind_cfg = config['indicators']
        sma_win = ind_cfg.get('sma_window', 20)
        ema_win = ind_cfg.get('ema_window', 50)
        rsi_win = ind_cfg.get('rsi_window', 14)
        bb_win = ind_cfg.get('bb_window', 20)
        bb_std = ind_cfg.get('bb_std_dev', 2.0)
        macd_fast = ind_cfg.get('macd_fast', 12)
        macd_slow = ind_cfg.get('macd_slow', 26)
        macd_signal = ind_cfg.get('macd_signal', 9)
    else:
        # Fallback defaults (để code không bị crash nếu quên file config)
        sma_win, ema_win, rsi_win = 20, 50, 14
        bb_win, bb_std = 20, 2.0
        macd_fast, macd_slow, macd_signal = 12, 26, 9

    df = df.copy()
    
    # Đảm bảo dữ liệu là số thực
    close = df['close'].astype(float)
    
    # --------------------------------------------------------
    # 1. RSI (Relative Strength Index)
    # --------------------------------------------------------
    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=rsi_win).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=rsi_win).mean()
    rs = gain / loss
    df['rsi'] = 100 - (100 / (1 + rs))
    
    # --------------------------------------------------------
    # 2. MACD (Moving Average Convergence Divergence)
    # --------------------------------------------------------
    exp1 = close.ewm(span=macd_fast, adjust=False).mean()
    exp2 = close.ewm(span=macd_slow, adjust=False).mean()
    df['macd'] = exp1 - exp2
    # Signal line (không nhất thiết phải thêm vào feature nếu muốn tiết kiệm)
    # df['macd_signal'] = df['macd'].ewm(span=macd_signal, adjust=False).mean()
    
    # --------------------------------------------------------
    # 3. Moving Averages (SMA & EMA)
    # --------------------------------------------------------
    df[f'sma_{sma_win}'] = close.rolling(window=sma_win).mean()
    df[f'ema_{ema_win}'] = close.ewm(span=ema_win, adjust=False).mean()
    
    # --------------------------------------------------------
    # 4. Bollinger Bands
    # --------------------------------------------------------
    sma_bb = close.rolling(window=bb_win).mean()
    std_bb = close.rolling(window=bb_win).std()
    df['bb_upper'] = sma_bb + (std_bb * bb_std)
    df['bb_lower'] = sma_bb - (std_bb * bb_std)
    
    # --------------------------------------------------------
    # 5. Xử lý NaN (Do Rolling tạo ra)
    # --------------------------------------------------------
    # Thay thế NaN bằng giá trị đầu tiên hợp lệ (Backfill) hoặc 0
    df.fillna(method='bfill', inplace=True)
    df.fillna(0, inplace=True) # Phòng trường hợp bfill vẫn còn NaN

    return df