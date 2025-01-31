import aiohttp
import asyncio
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
import time
import logging

# Konfigurasi logging
logging.basicConfig(level=logging.INFO)

# Konfigurasi API Telegram
TELEGRAM_TOKEN = "6837750868:AAFjibD5ajw-yA-xpSxh7Rm45Jcjo-8i7bI"
TELEGRAM_CHAT_IDS = ["-1001651360411", "-1001460863353", "-1002108809012", "-1002220890884"]

# Link API dan Pendaftaran
API_URL = "https://didihub20.com/api/main/lottery/rounds?page=1&count=20&type=2"
REGISTER_URL = "https://didihub20.com/register?spreadCode=MCYET"

# Daftar kompensasi taruhan
BET_SEQUENCE = [1000, 3000, 6000, 16000, 32000, 80000, 160000, 350000]

# Pola prediksi dari data yang ada di web
PREDICTION_PATTERN = []
pattern_index = 0
consecutive_losses = 0

# Fungsi untuk menentukan win/lose berdasarkan angka
def get_win_lose(number):
    if number in [0, 1, 2, 3, 4]:
        return "K"
    elif number in [5, 6, 7, 8, 9]:
        return "B"
    else:
        return "Invalid"

# Fungsi untuk mengambil data dari API
async def fetch_data(api_url):
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(api_url, timeout=10) as response:  # Perpanjang timeout menjadi 10 detik
                if response.status == 200:
                    return await response.json()
                else:
                    logging.error(f"Error fetching data: {response.status}")
                    return None
        except aiohttp.ClientError as e:
            logging.error(f"Network error: {e}")
            return None
        except asyncio.TimeoutError:
            logging.error("Request timeout")
            return None

# Fungsi untuk merekam pola dari data yang ada di web
def record_pattern(data_items):
    global PREDICTION_PATTERN
    PREDICTION_PATTERN = []
    for item in data_items:
        result = get_win_lose(item["number"])
        PREDICTION_PATTERN.append(result)
    PREDICTION_PATTERN = PREDICTION_PATTERN[:30]  # Batasi pola hingga 30 hasil terbaru

# Fungsi untuk mengirim pesan ke Telegram ke banyak grup
async def send_to_telegram(bot_token, chat_ids, message, button_url):
    bot = Bot(token=bot_token)
    keyboard = [[InlineKeyboardButton("Daftar", url=button_url)]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    for chat_id in chat_ids:
        try:
            await bot.send_message(chat_id=chat_id, text=message, reply_markup=reply_markup, parse_mode="HTML")
            logging.info(f"Pesan berhasil dikirim ke grup Telegram dengan ID: {chat_id}")
        except Exception as e:
            logging.error(f"Error sending message to chat ID {chat_id}: {e}")

# Saldo awal
modal_balance = 1000000  # Saldo modal awal
current_balance = modal_balance  # Saldo saat ini

# Fungsi utama untuk memonitor API
async def monitor_api():
    global current_balance, pattern_index, consecutive_losses, PREDICTION_PATTERN
    last_period = None
    bet_index = 0
    history = []
    total_bets = 0
    total_wins = 0

    while True:
        data = await fetch_data(API_URL)
        if data:
            items = data.get("items", [])
            if items:
                if not PREDICTION_PATTERN:
                    # Rekam pola dari data yang ada di web
                    record_pattern(items)

                latest_item = items[0]
                current_period = latest_item.get("period")
                number = latest_item.get("number")

                # Pastikan hanya memproses periode baru
                if current_period and number is not None and current_period != last_period:
                    result_actual = get_win_lose(number)
                    current_bet = BET_SEQUENCE[bet_index]

                    # Prediksi berdasarkan pola
                    prediction = PREDICTION_PATTERN[pattern_index]

                    # Update hasil taruhan berdasarkan prediksi periode sebelumnya dengan hasil periode saat ini
                    if prediction == result_actual:
                        result = "WIN ✅"
                        total_wins += 1
                        bet_index = 0
                        current_balance += current_bet  # Tambah saldo dengan taruhan
                        consecutive_losses = 0  # Reset kekalahan berturut-turut
                    else:
                        result = "LOSE ❌"
                        bet_index = min(bet_index + 1, len(BET_SEQUENCE) - 1)
                        current_balance -= current_bet  # Kurangi saldo sesuai taruhan
                        consecutive_losses += 1

                    # Jika kekalahan berturut-turut mencapai 5, reset pola
                    if consecutive_losses >= 5:
                        pattern_index = 0
                        consecutive_losses = 0
                    else:
                        pattern_index = (pattern_index + 1) % len(PREDICTION_PATTERN)

                    total_bets += 1
                    accuracy = (total_wins / total_bets) * 100
                    profit_balance = current_balance - modal_balance  # Hitung profit

                    # Tampilkan hanya 4 digit terakhir periode
                    formatted_period = str(current_period)[-4:]
                    next_period = str(int(current_period) + 1)[-4:]

                    history.append(
                        f"{formatted_period} | {number} ({result_actual}) {current_bet} {result}"
                    )
                    if len(history) > 20:
                        history.pop(0)

                    next_bet = BET_SEQUENCE[bet_index]
                    message = (
                        "<b>Riwayat DIDIHUB WINGO CEPAT:</b>\n"
                        + "\n".join(history)
                        + f"\n\n<b>Prediksi Periode {next_period}:</b>\n"
                        f"<b>Taruhan:</b> {prediction} {next_bet}\n"
                        f"<b>Akurasi:</b> {accuracy:.2f}%\n"
                        f"<b>Saldo Modal:</b> {modal_balance:,}\n"
                        f"<b>Saldo Saat Ini:</b> {current_balance:,}\n"
                        f"<b>Saldo Profit:</b> {profit_balance:,}\n"
                    )

                    # Kirim ke Telegram
                    await send_to_telegram(TELEGRAM_TOKEN, TELEGRAM_CHAT_IDS, message, REGISTER_URL)
                    last_period = current_period  # Update last_period
                else:
                    logging.info("Data tidak lengkap atau periode sama dengan sebelumnya.")
            else:
                logging.info("Tidak ada data item dalam response API.")
        else:
            logging.error("Gagal mengambil data dari API.")

        time.sleep(10)

# Jalankan fungsi monitor
if __name__ == "__main__":
    asyncio.run(monitor_api())
