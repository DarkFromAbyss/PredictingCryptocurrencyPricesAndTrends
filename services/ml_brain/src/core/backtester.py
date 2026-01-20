import pandas as pd
import numpy as np

class Backtester:
    def __init__(self, initial_capital: float = 1000.0, fee: float = 0.001):
        """
        Khởi tạo bộ Backtest.
        Args:
            initial_capital: Số vốn ban đầu (ví dụ: 1000 USD).
            fee: Phí giao dịch sàn (0.001 tương ứng 0.1% của Binance).
        """
        self.initial_capital = initial_capital
        self.fee = fee

    def run(self, df: pd.DataFrame, threshold: float = 0.005):
        """
        Chạy mô phỏng giao dịch trên dữ liệu lịch sử.
        
        Args:
            df (pd.DataFrame): DataFrame chứa 3 cột bắt buộc:
                               - 'timestamps': Thời gian
                               - 'actual': Giá thực tế
                               - 'predicted': Giá AI dự đoán
            threshold (float): Ngưỡng ra quyết định (0.005 = 0.5%).
                               Nếu (Giá Dự đoán - Giá Hiện tại) > 0.5% -> MUA.
                               Nếu (Giá Dự đoán - Giá Hiện tại) < -0.5% -> BÁN.
        
        Returns:
            dict: Kết quả thống kê (ROI, Tổng tài sản, Số lệnh...).
        """
        capital = self.initial_capital # Tiền mặt hiện có
        position = 0.0                 # Số lượng Coin đang giữ
        trades = []                    # Nhật ký giao dịch
        equity_curve = [capital]       # Biểu đồ tài sản theo thời gian

        # Duyệt qua từng cây nến trong dữ liệu (bỏ qua cây đầu tiên vì không có quá khứ để so sánh)
        for i in range(1, len(df)):
            timestamp = df['timestamps'].iloc[i]
            current_price = df['actual'].iloc[i-1]    # Giá đóng cửa cây nến trước (Giá hiện tại để vào lệnh)
            predicted_price = df['predicted'].iloc[i-1] # Giá AI dự đoán cho cây nến tiếp theo
            next_real_price = df['actual'].iloc[i]    # Giá thực tế diễn ra sau đó (dùng để tính NAV)

            # Tính phần trăm thay đổi dự kiến (AI đoán tăng hay giảm bao nhiêu %)
            predicted_change = (predicted_price - current_price) / current_price

            # --- LOGIC RA QUYẾT ĐỊNH (STRATEGY) ---

            # 1. Tín hiệu MUA (Long)
            # Điều kiện: Chưa có hàng (position == 0) VÀ AI đoán tăng mạnh hơn ngưỡng threshold
            if position == 0 and predicted_change > threshold:
                # Mua hết tiền (All-in)
                amount_to_buy = capital / current_price
                cost = amount_to_buy * current_price
                fee_val = cost * self.fee # Trừ phí sàn
                
                if capital > fee_val:
                    position = amount_to_buy * (1 - self.fee) # Số coin thực nhận
                    capital = 0 # Tiền mặt về 0
                    
                    trades.append({
                        "type": "BUY 🟢",
                        "time": str(timestamp),
                        "price": current_price,
                        "value": cost,
                        "fee": fee_val
                    })

            # 2. Tín hiệu BÁN (Sell)
            # Điều kiện: Đang giữ hàng (position > 0) VÀ (AI đoán giảm HOẶC tăng yếu hơn ngưỡng)
            elif position > 0 and predicted_change < -threshold:
                # Bán sạch coin (Close position)
                revenue = position * current_price
                fee_val = revenue * self.fee
                
                capital = revenue - fee_val # Tiền mặt thu về
                position = 0 # Hết coin
                
                trades.append({
                    "type": "SELL 🔴",
                    "time": str(timestamp),
                    "price": current_price,
                    "value": revenue,
                    "fee": fee_val
                })

            # 3. Cập nhật giá trị tài sản ròng (NAV - Net Asset Value)
            # Nếu đang giữ coin, tài sản = giá trị coin hiện tại. Nếu giữ tiền, tài sản = tiền mặt.
            current_equity = capital + (position * next_real_price)
            equity_curve.append(current_equity)

        # --- TỔNG KẾT ---
        final_equity = equity_curve[-1]
        roi_percent = ((final_equity - self.initial_capital) / self.initial_capital) * 100
        
        return {
            "initial_capital": self.initial_capital,
            "final_equity": round(final_equity, 2),
            "roi_percent": round(roi_percent, 2),
            "total_trades": len(trades),
            "trades_log": trades[-5:], # Chỉ trả về 5 giao dịch cuối cùng để xem mẫu
            "equity_curve": equity_curve
        }