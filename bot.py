import os
import threading
import tempfile

from flask import Flask
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
PORT = int(os.getenv("PORT", "10000"))

app = Flask(__name__)


@app.route("/")
def home():
    return "Telegram Video Bot is running!"


@app.route("/health")
def health():
    return "OK"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привет!\n\n"
        "Отправь мне видео, и я попробую скачать "
        "его и отправить обратно."
    )


async def video_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    message = update.message

    if not message or not message.video:
        return

    video = message.video

    if video.file_size and video.file_size > 20 * 1024 * 1024:
        await message.reply_text(
            "❌ Видео больше 20 МБ.\n"
            "Пока поддерживается максимум 20 МБ."
        )
        return

    status = await message.reply_text(
        "⏳ Скачиваю видео..."
    )

    temp_path = None

    try:
        telegram_file = await context.bot.get_file(
            video.file_id
        )

        temp_file = tempfile.NamedTemporaryFile(
            delete=False,
            suffix=".mp4"
        )

        temp_path = temp_file.name
        temp_file.close()

        await telegram_file.download_to_drive(
            temp_path
        )

        await status.edit_text(
            "📤 Скачивание завершено!\n"
            "Отправляю видео обратно..."
        )

        with open(temp_path, "rb") as video_file:
            await context.bot.send_video(
                chat_id=message.chat_id,
                video=video_file,
                caption="✅ Готово!"
            )

        await status.delete()

    except Exception as error:
        await status.edit_text(
            f"❌ Произошла ошибка:\n{error}"
        )

    finally:
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)


def run_web_server():
    app.run(
        host="0.0.0.0",
        port=PORT
    )


def main():
    if not BOT_TOKEN:
        raise RuntimeError(
            "BOT_TOKEN не найден!"
        )

    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )

    application.add_handler(
        CommandHandler("start", start)
    )

    application.add_handler(
        MessageHandler(
            filters.VIDEO,
            video_handler
        )
    )

    web_thread = threading.Thread(
        target=run_web_server,
        daemon=True
    )

    web_thread.start()

    print("🤖 Telegram-бот запущен!")
    print(f"🌐 Web server port: {PORT}")

    application.run_polling()


if __name__ == "__main__":
    main()
