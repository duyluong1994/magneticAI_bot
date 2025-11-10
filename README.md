# MagneticAI Telegram Bot

Telegram bot để quản lý payments cho hệ thống MagneticAI. Bot được xây dựng bằng Python với khả năng scale và mở rộng dễ dàng.

## Tính năng

- ✅ Quản lý admin (sysadmin + sub-admins)
- ✅ Complete payments qua Telegram command
- ✅ Kết nối database PostgreSQL
- ✅ Cấu trúc code có thể scale

## Cài đặt

### 1. Cài đặt dependencies

```bash
pip install -r requirements.txt
```

### 2. Cấu hình môi trường

Tạo file `.env` từ `.env.example`:

```bash
cp .env.example .env
```

Điền thông tin vào `.env`:

```env
# Telegram Bot Token
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here

# Database Configuration
DB_HOST=localhost
DB_PORT=5432
DB_NAME=your_database_name
DB_USER=your_database_user
DB_PASSWORD=your_database_password
```

### 3. Lấy Telegram Bot Token

1. Mở Telegram và tìm [@BotFather](https://t.me/botfather)
2. Gửi `/newbot` và làm theo hướng dẫn
3. Copy token và paste vào `.env`

### 4. Chạy bot

```bash
python bot.py
```

## Cấu trúc dự án

```
supporter_bot/
├── bot.py              # Main bot application
├── config.py           # Configuration và environment variables
├── database.py         # Database models và connection
├── admin_manager.py    # Admin management system
├── payment_service.py  # Payment business logic
├── requirements.txt    # Python dependencies
├── .env.example        # Environment variables template
└── README.md          # Documentation
```

## Quyền truy cập

### System Admin (Hardcoded)
- User ID: `588014415`
- Quyền: Tất cả quyền, bao gồm thêm/xóa sub-admins

### Sub-Admins
- Được thêm bởi sysadmin qua command `/add_admin`
- Lưu trong memory (bot state), không lưu vào database
- Có quyền complete payments nhưng không thể quản lý admins

## Commands

### Commands cho tất cả users

#### `/start`
Khởi động bot và hiển thị thông tin user

#### `/help`
Hiển thị danh sách commands

### Commands cho Admin (sysadmin + sub-admins)

#### `/complete_payment <paymentIds>`
Complete một hoặc nhiều payments.

**Usage:**
```
/complete_payment payment-id-1 payment-id-2 payment-id-3
```

**Example:**
```
/complete_payment abc123-def456-ghi789 xyz789-uvw012-rst345
```

**Logic:**
- Tìm payment theo ID trong database
- Update status thành `completed`
- Set `processedAt` = current time
- Update `user.totalPaidOut` nếu payment chưa được complete trước đó

**Response:**
- Summary: tổng số, completed, not found, errors
- Chi tiết từng payment: status và thông tin

### Commands cho Sysadmin only

#### `/add_admin <user_id>`
Thêm một sub-admin.

**Usage:**
```
/add_admin 123456789
```

#### `/remove_admin <user_id>`
Xóa một sub-admin.

**Usage:**
```
/remove_admin 123456789
```

#### `/list_admins`
Liệt kê tất cả admins (sysadmin + sub-admins).

## Database Models

Bot sử dụng các models sau từ database:

### Payment
- `id` (UUID): Primary key
- `userId` (UUID): Foreign key to Users
- `amount` (Decimal): Total amount
- `status` (Enum): pending, processing, completed, failed, etc.
- `processedAt` (DateTime): Thời gian processed
- Các fields khác...

### User
- `id` (UUID): Primary key
- `totalPaidOut` (Decimal): Tổng số tiền đã trả
- Các fields khác...

## Logic Complete Payment

Logic trong `/complete_payment` giống hệt với endpoint `/api/payment/complete-payout`:

1. Validate payment IDs (phải là UUID format)
2. Với mỗi payment ID:
   - Tìm payment trong database
   - Nếu tìm thấy:
     - Check nếu đã completed trước đó
     - Update `status` = `completed`
     - Update `processedAt` = current time
     - Nếu chưa completed trước đó: update `user.totalPaidOut`
   - Nếu không tìm thấy: báo lỗi
3. Return summary và details

## Mở rộng

Bot được thiết kế để dễ dàng mở rộng:

1. **Thêm commands mới**: Thêm handler trong `bot.py`
2. **Thêm services**: Tạo file service mới trong thư mục
3. **Thêm models**: Thêm vào `database.py`
4. **Thêm decorators**: Tạo decorator mới cho permissions

## Troubleshooting

### Bot không start
- Kiểm tra `TELEGRAM_BOT_TOKEN` trong `.env`
- Kiểm tra log để xem lỗi cụ thể

### Không kết nối được database
- Kiểm tra thông tin DB trong `.env`
- Kiểm tra database đang chạy
- Kiểm tra firewall/network

### Payment không complete được
- Kiểm tra payment ID có đúng format UUID không
- Kiểm tra payment có tồn tại trong database không
- Kiểm tra log để xem lỗi cụ thể

## License

Internal use only.
