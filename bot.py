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
        "Отправь мне видео, и я скачаю его "
        "и отправлю тебе обратно.\n\n"
        "📥 Максимальный размер сейчас — 20 МБ."
    )


async def video_handler(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):
    message = update.message

    if not message or not message.video:
        return

    video = message.video

    # Ограничение обычного Telegram Bot API
    if video.file_size and video.file_size > 20 * 1024 * 1024:
        await message.reply_text(
            "❌ Видео слишком большое.\n\n"
            f"Размер: {video.file_size / 1024 / 1024:.1f} МБ\n"
            "Максимум сейчас: 20 МБ."
        )
        return

    status = await message.reply_text(
        "⏳ Скачиваю видео..."
    )

    temp_path = None

    try:
        # Получаем файл Telegram
        telegram_file = await context.bot.get_file(
            video.file_id
        )

        # Создаём временный файл
        temp_file = tempfile.NamedTemporaryFile(
            delete=False,
            suffix=".mp4"
        )

        temp_path = temp_file.name
        temp_file.close()

        # Скачиваем видео на Render
        await telegram_file.download_to_drive(
            temp_path
        )

        await status.edit_text(
            "✅ Видео полностью скачано!\n\n"
            "📤 Отправляю обратно..."
        )

        # Отправляем видео обратно как VIDEO,
        # а не как DOCUMENT
        with open(temp_path, "rb") as video_file:
            await context.bot.send_video(
                chat_id=message.chat_id,
                video=video_file,
                caption="✅ Готово!",
                supports_streaming=True
            )

        # Удаляем сообщение со статусом
        await status.delete()

    except Exception as error:
        print(f"Ошибка: {error}")

        try:
            await status.edit_text(
                f"❌ Ошибка при обработке видео:\n\n"
                f"{error}"
            )
        except Exception:
            pass

    finally:
        # Удаляем временный файл с Render
        if temp_path and os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except Exception:
                pass


def run_web_server():
    app.run(
        host="0.0.0.0",
        port=PORT
    )


def main():
    if not BOT_TOKEN:
        raise RuntimeError(
            "BOT_TOKEN не найден в Environment Variables!"
        )

    # Создаём Telegram-приложение
    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .build()
    )

    # Команда /start
    application.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    # Получение видео
    application.add_handler(
        MessageHandler(
            filters.VIDEO,
            video_handler
        )
    )

    # Запускаем веб-сервер для Render
    web_thread = threading.Thread(
        target=run_web_server,
        daemon=True
    )

    web_thread.start()

    print("🤖 Telegram Video Bot запущен!")
    print(f"🌐 Render PORT: {PORT}")

    # Запускаем Telegram-бота
    application.run_polling()


if __name__ == "__main__":
    main()
