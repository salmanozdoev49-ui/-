import os
import tempfile

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

BOT_TOKEN = os.getenv("BOT_TOKEN")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привет!\n\n"
        "Отправь мне видео, и я попробую скачать его "
        "и отправить тебе обратно."
    )


async def video_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message

    if not message or not message.video:
        return

    video = message.video

    if video.file_size and video.file_size > 20 * 1024 * 1024:
        await message.reply_text(
            "❌ Это видео больше 20 МБ.\n"
            "Пока тестируем обычную версию бота."
        )
        return

    status = await message.reply_text(
        "⏳ Скачиваю видео..."
    )

    file = await context.bot.get_file(video.file_id)

    temp_file = tempfile.NamedTemporaryFile(
        delete=False,
        suffix=".mp4"
    )

    temp_path = temp_file.name
    temp_file.close()

    try:
        await file.download_to_drive(temp_path)

        await status.edit_text(
            "📤 Видео скачано!\n"
            "Отправляю обратно..."
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
            f"❌ Ошибка:\n{error}"
        )

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def main():
    if not BOT_TOKEN:
        raise RuntimeError(
            "Не найден BOT_TOKEN в переменных окружения."
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

    print("🤖 Бот запущен!")

    application.run_polling()


if __name__ == "__main__":
    main()
