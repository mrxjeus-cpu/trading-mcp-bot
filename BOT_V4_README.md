# Trading Bot v4 - EMA Alignment Strategy

## 🎯 Overview

Bot v4 sử dụng **EMA Alignment Strategy** với 4 đường EMA (20, 50, 100, 200) để phát hiện các setup theo xu hướng trên khung 4H.

---

## 📋 Features

### 🔄 Trend Modes
- **UPTREND**: Chỉ LONG khi Price > EMA200 và EMA20 > EMA50 > EMA100 > EMA200
- **DOWNTREND**: Chỉ SHORT khi Price < EMA200 và EMA20 < EMA50 < EMA100 < EMA200
- **AUTO**: Tự động detect trend và trade theo đó

### 📊 EMA Setups

#### UPTREND Setups:
1. **Long #1**: Pullback về EMA20 (Rủi ro cao, lợi nhuận cao)
2. **Long #2**: Pullback về EMA50 (An toàn hơn)
3. **Long #3**: EMA20 Golden Cross (cắt lên EMA50)
4. **Long #4**: EMA Ribbon Expansion (Xu hướng mạnh)

#### DOWNTREND Setups:
1. **Short #1**: Pullback lên EMA20
2. **Short #2**: Pullback lên EMA50
3. **Short #3**: EMA20 Death Cross (cắt xuống EMA50)
4. **Short #4**: EMA Ribbon Expansion (Xu hướng giảm mạnh)

---

## 🚀 Installation

### Local Testing:

```bash
# Make script executable
chmod +x run_bot_v4_local.sh

# Run bot
./run_bot_v4_local.sh
```

### VPS Deployment:

#### Option 1: Fresh Install
```bash
chmod +x deploy-vps-v4.sh
./deploy-vps-v4.sh
```

#### Option 2: Switch from v2 to v4
```bash
chmod +x switch-to-v4.sh
./switch-to-v4.sh
```

---

## 💡 Usage

### Telegram Commands:

| Command | Description |
|---------|-------------|
| `/trend` | Chọn trend mode (UPTREND/DOWNTREND/AUTO) |
| `/check` | Check current conditions immediately |
| `/status` | Show bot status and current trend mode |
| `/start` | Start automatic monitoring (30min interval) |
| `/stop` | Stop automatic monitoring |
| `/help` | Show all available commands |

### VPS Management:

```bash
# View logs
pm2 logs tradingview-bot-v4 --lines 50

# Restart bot
pm2 restart tradingview-bot-v4

# Stop bot
pm2 stop tradingview-bot-v4

# Delete bot
pm2 delete tradingview-bot-v4

# View status
pm2 status
```

---

## ⚙️ Configuration

### Bot Config (ecosystem.config.v4.js):

```javascript
{
  TREND_MODE: 'auto',           // 'uptrend', 'downtrend', 'auto'
  EMA_PROXIMITY_PCT: '0.8',     // EMA touch threshold (%)
  BOT_TIMEFRAME: '4h',          // 4H timeframe
  BOT_CHECK_INTERVAL: '1800'    // 30 minutes
}
```

### Timeframe Selection:
- **4H**: Khuyên dùng cho EMA analysis (balance giữa noise và trend)
- **1D**: Cho trend dài hạn (ít signals hơn nhưng chất lượng hơn)
- **1H**: Cho scalping (nhiều noise hơn)

---

## 📈 Trading Strategy

### Entry Conditions:

**For LONG:**
1. Price > EMA200
2. EMA20 > EMA50 > EMA100 > EMA200
3. Price pulls back to EMA20 hoặc EMA50
4. RSI healthy (40-70)
5. Enter tại pullback zone

**For SHORT:**
1. Price < EMA200
2. EMA20 < EMA50 < EMA100 < EMA200
3. Price pulls up to EMA20 hoặc EMA50
4. RSI not overbought (30-60)
5. Enter tại pullback zone

### Risk Management:

- **Stop Loss**: 1.5% từ entry (thích hợp 4H timeframe)
- **Take Profit**: 2.5x risk (1:2.5 R:R)
- **Position Size**: 1% account risk

---

## 🔍 V2 vs V4 Comparison

| Feature | v2 | v4 |
|---------|-----|-----|
| Strategy | RSI Breakout + Confluence | EMA Alignment |
| Timeframe | 1H | 4H |
| Check Interval | 5 minutes | 30 minutes |
| Signals | More frequent | Higher quality |
| Trend Following | Partial | Full |
| Indicators | RSI + EMA + Fib + Volume | EMA-focused |

---

## 🛠️ Troubleshooting

### Bot không start:
```bash
# Check logs
pm2 logs tradingview-bot-v4 --lines 100

# Check Python path
pm2 show tradingview-bot-v4
```

### Không có signals:
- Kiểm tra trend mode: `/status`
- Market có thể đang sideways (không có trend rõ ràng)
- AUTO mode sẽ skip khi không có trend

### EMA setup không detect:
- Tăng EMA_PROXIMITY_PCT (mặc định 0.8%)
- Kiểm tra timeframe settings
- Verify EMA alignment conditions

---

## 📝 Notes

- Bot v4 tập trung **quality over quantity** - ít signals nhưng chất lượng hơn
- 30-minute interval phù hợp cho 4H timeframe
- AUTO mode khuyến nghị cho大多数 traders
- UPTREND/DOWNTREND mode khi market có trend rõ ràng

---

## ⚠️ Disclaimer

Bot này chỉ cung cấp signals, không phải financial advice. Always:
- Manage risk properly
- Use stop loss
- Don't over-leverage
- Do your own research
