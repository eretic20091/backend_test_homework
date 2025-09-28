import os
import logging
import json
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import speech_recognition as sr
from pydub import AudioSegment
import tempfile
import requests
import aiohttp
import asyncio
from PyPDF2 import PdfReader
import io

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Токен бота (получите у @BotFather)
BOT_TOKEN = "8358463402:AAHHxoPcuGbwD4JkSeBcW72vun2XATWNJkU"

# Настройки OpenRouter.ai
OPENROUTER_API_KEY = "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"
OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODEL = "openai/gpt-3.5-turbo"

async def call_openrouter_api(prompt: str) -> str:
    """Асинхронный вызов OpenRouter API"""
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/your-username/telegram-bot",
        "X-Title": "Telegram Transcription Bot"
    }
    
    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {
                "role": "system",
                "content": "Ты помощник для обработки и улучшения текста. Отвечай только на русском языке."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "temperature": 0.7,
        "max_tokens": 1000
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                OPENROUTER_API_URL,
                headers=headers,
                json=payload,
                timeout=30
            ) as response:
                
                if response.status == 200:
                    data = await response.json()
                    return data['choices'][0]['message']['content'].strip()
                else:
                    error_text = await response.text()
                    logger.error(f"OpenRouter API error: {response.status} - {error_text}")
                    return f"Ошибка API: {response.status}"
                    
    except asyncio.TimeoutError:
        logger.error("OpenRouter API timeout")
        return "Таймаут при обращении к API"
    except Exception as e:
        logger.error(f"OpenRouter API exception: {e}")
        return f"Ошибка: {str(e)}"

async def improve_text_with_ai(text: str, text_type: str = "general") -> str:
    """Улучшение текста с помощью AI"""
    if len(text.strip()) < 10:
        return text
    
    if text_type == "audio":
        prompt = f"""
        Пожалуйста, обработай следующий текст, полученный из аудиозаписи:
        
        1. Исправь орфографические и пунктуационные ошибки
        2. Добавь недостающие знаки препинания
        3. Сделай текст более читаемым и структурированным
        4. Сохрани оригинальный смысл и стиль
        5. Если текст несвязный - попробуй восстановить логику
        
        Текст для обработки: "{text}"
        
        Верни только исправленный текст без дополнительных комментариев.
        """
    else:
        prompt = f"""
        Пожалуйста, улучши следующий текст:
        
        1. Исправь грамматические, орфографические и пунктуационные ошибки
        2. Улучши стиль и читаемость текста
        3. Сделай текст более структурированным и логичным
        4. Сохрани оригинальный смысл и основную идею
        5. Если нужно - разбей на абзацы для лучшего восприятия
        
        Текст для улучшения: "{text}"
        
        Верни только улучшенный текст без дополнительных комментариев.
        """
    
    return await call_openrouter_api(prompt)

async def summarize_text_with_ai(text: str) -> str:
    """Суммаризация текста с помощью AI"""
    if len(text.split()) < 20:
        return "Текст слишком короткий для суммаризации"
    
    prompt = f"""
    Сделай краткое содержание следующего текста. Выдели основные идеи и ключевые моменты.
    Верни ответ на русском языке в формате маркированного списка.
    
    Текст: "{text}"
    """
    
    return await call_openrouter_api(prompt)

async def process_pdf_with_ai(text: str) -> str:
    """Обработка PDF текста с помощью AI"""
    if len(text.strip()) < 50:
        return "Текст из PDF слишком короткий для обработки"
    
    prompt = f"""
    Проанализируй следующий текст, извлеченный из PDF документа:
    
    1. Сделай структурированное описание содержания
    2. Выдели основные разделы и темы
    3. Представь информацию в удобочитаемом формате
    4. Сохрани ключевые моменты
    
    Текст из PDF: "{text[:3000]}"  # Ограничиваем длину для API
    
    Верни структурированный анализ на русском языке.
    """
    
    return await call_openrouter_api(prompt)

async def correct_text_with_ai(text: str) -> str:
    """Корректура текста с помощью AI"""
    if len(text.strip()) < 10:
        return text
    
    prompt = f"""
    Проведи профессиональную корректуру следующего текста:
    
    1. Исправь все орфографические ошибки
    2. Исправь пунктуационные ошибки (запятые, точки, тире и т.д.)
    3. Проверь грамматику и синтаксис
    4. Убери повторяющиеся слова и фразы
    5. Сохрани оригинальный смысл и стиль
    
    Текст для корректуры: "{text}"
    
    Верни только исправленный текст без комментариев.
    """
    
    return await call_openrouter_api(prompt)

async def format_text_with_ai(text: str) -> str:
    """Форматирование текста с помощью AI"""
    if len(text.strip()) < 10:
        return text
    
    prompt = f"""
    Отформатируй и отредактируй следующий текст для лучшей читаемости:
    
    1. Разбей на логические абзацы
    2. Добавь подзаголовки где это уместно
    3. Исправь структуру предложений
    4. Сделай текст более профессиональным и понятным
    5. Сохрани все важные детали и смысл
    
    Текст для форматирования: "{text}"
    
    Верни только отформатированный текст.
    """
    
    return await call_openrouter_api(prompt)

def download_file(file_url, file_path):
    """Скачивание файла"""
    response = requests.get(file_url)
    with open(file_path, 'wb') as f:
        f.write(response.content)

def convert_audio(input_path, output_path):
    """Конвертация аудио в WAV формат"""
    try:
        audio = AudioSegment.from_file(input_path)
        audio = audio.set_frame_rate(16000).set_channels(1)
        audio.export(output_path, format="wav")
        return True
    except Exception as e:
        logger.error(f"Audio conversion error: {e}")
        return False

def transcribe_audio(audio_path):
    """Транскрибация аудио с помощью SpeechRecognition"""
    recognizer = sr.Recognizer()
    
    try:
        with sr.AudioFile(audio_path) as source:
            audio_data = recognizer.record(source)
        
        text = recognizer.recognize_google(audio_data, language='ru-RU')
        return text
    except sr.UnknownValueError:
        return "Не удалось распознать речь"
    except sr.RequestError as e:
        return f"Ошибка сервиса распознавания: {e}"
    except Exception as e:
        return f"Ошибка обработки аудио: {e}"

def extract_text_from_pdf(pdf_path):
    """Извлечение текста из PDF файла"""
    try:
        with open(pdf_path, 'rb') as file:
            pdf_reader = PdfReader(file)
            text = ""
            
            for page_num in range(len(pdf_reader.pages)):
                page = pdf_reader.pages[page_num]
                text += page.extract_text() + "\n\n"
            
            return text.strip()
    except Exception as e:
        logger.error(f"PDF extraction error: {e}")
        return f"Ошибка чтения PDF: {e}"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    welcome_text = (
        "🎙️ Добро пожаловать в AI бот для обработки текста!\n\n"
        "📁 Что я умею:\n"
        "• Голосовые сообщения → текст с улучшением\n"
        "• Аудиофайлы → расшифровка и корректура\n"
        "• PDF файлы → анализ содержания\n"
        "• Любой текст → улучшение и форматирование\n\n"
        "✨ Просто отправьте мне текст, и я его улучшу!\n\n"
        "Доступные команды:\n"
        "/start - начать работу\n"
        "/help - помощь\n"
        "/improve - улучшить текст (ответьте на сообщение)"
    )
    await update.message.reply_text(welcome_text)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help"""
    help_text = (
        "🤖 Как пользоваться ботом:\n\n"
        "🎤 Голосовые сообщения:\n"
        "• Отправьте голосовое → получите текст с AI-обработкой\n\n"
        "📁 Аудиофайлы:\n"
        "• MP3, WAV, OGG → расшифровка с улучшением\n\n"
        "📄 PDF файлы:\n"
        "• Отправьте PDF → анализ содержания с AI\n\n"
        "📝 Любой текст:\n"
        "• Отправьте текст → улучшение, корректура, форматирование\n"
        "• Ответьте /improve на сообщение с текстом\n\n"
        "⚙️ Максимальный размер файла: 20MB\n"
        "⏱️ Максимальная длительность аудио: 5 минут\n\n"
        "🧠 Используемые AI-модели: GPT-3.5 Turbo через OpenRouter"
    )
    await update.message.reply_text(help_text)

async def improve_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /improve"""
    if not update.message.reply_to_message:
        await update.message.reply_text("❌ Ответьте командой /improve на сообщение с текстом, который нужно улучшить")
        return
    
    original_message = update.message.reply_to_message
    text_to_improve = ""
    
    # Получаем текст из разных типов сообщений
    if original_message.text:
        text_to_improve = original_message.text
    elif original_message.caption:
        text_to_improve = original_message.caption
    else:
        await update.message.reply_text("❌ В ответном сообщении нет текста для улучшения")
        return
    
    if len(text_to_improve.strip()) < 5:
        await update.message.reply_text("❌ Текст слишком короткий для улучшения")
        return
    
    await update.message.reply_text("✨ Улучшаю текст...")
    
    # Предлагаем варианты улучшения
    keyboard = [
        [{"text": "🔄 Баланс", "callback_data": f"improve:balance:{text_to_improve[:500]}"}],
        [{"text": "🎯 Корректура", "callback_data": f"improve:correct:{text_to_improve[:500]}"}],
        [{"text": "📋 Форматирование", "callback_data": f"improve:format:{text_to_improve[:500]}"}]
    ]
    reply_markup = {"inline_keyboard": keyboard}
    
    await update.message.reply_text(
        "Выберите тип улучшения:",
        reply_markup=json.dumps(reply_markup)
    )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик текстовых сообщений"""
    text = update.message.text
    
    # Игнорируем команды
    if text.startswith('/'):
        return
    
    if len(text.strip()) < 10:
        await update.message.reply_text("📝 Отправьте более длинный текст для улучшения или используйте /improve")
        return
    
    # Предлагаем улучшить текст
    keyboard = [
        [{"text": "✨ Улучшить этот текст", "callback_data": f"improve:balance:{text[:500]}"}]
    ]
    reply_markup = {"inline_keyboard": keyboard}
    
    await update.message.reply_text(
        "Хотите улучшить этот текст с помощью AI?",
        reply_markup=json.dumps(reply_markup)
    )

async def handle_voice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик голосовых сообщений"""
    try:
        await update.message.reply_text("🔍 Обрабатываю голосовое сообщение...")
        
        voice = update.message.voice
        file = await voice.get_file()
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.ogg') as temp_ogg:
            temp_ogg_path = temp_ogg.name
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_wav:
            temp_wav_path = temp_wav.name
        
        # Скачивание файла
        download_file(file.file_path, temp_ogg_path)
        
        # Конвертация в WAV
        if not convert_audio(temp_ogg_path, temp_wav_path):
            await update.message.reply_text("❌ Ошибка конвертации аудио")
            return
        
        # Транскрибация
        raw_text = transcribe_audio(temp_wav_path)
        
        if "Не удалось распознать речь" in raw_text or "Ошибка" in raw_text:
            await update.message.reply_text(f"❌ {raw_text}")
            return
        
        # Отправка сырого текста
        await update.message.reply_text(f"📝 Сырая расшифровка:\n\n{raw_text}")
        
        # Улучшение текста с помощью AI
        await update.message.reply_text("🧠 Улучшаю текст с помощью AI...")
        improved_text = await improve_text_with_ai(raw_text, "audio")
        
        # Отправка улучшенного текста
        if improved_text.startswith("Ошибка"):
            await update.message.reply_text(f"❌ {improved_text}")
        else:
            if len(improved_text) > 4000:
                for i in range(0, len(improved_text), 4000):
                    await update.message.reply_text(f"✨ Улучшенный текст (часть {i//4000 + 1}):\n\n{improved_text[i:i+4000]}")
            else:
                await update.message.reply_text(f"✨ Улучшенный текст:\n\n{improved_text}")
        
        # Очистка временных файлов
        os.unlink(temp_ogg_path)
        os.unlink(temp_wav_path)
        
    except Exception as e:
        logger.error(f"Error processing voice: {e}")
        await update.message.reply_text("❌ Произошла ошибка при обработке аудио")

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик документов (PDF)"""
    try:
        document = update.message.document
        file_name = document.file_name or "file"
        file_extension = os.path.splitext(file_name)[1].lower()
        
        if file_extension != '.pdf':
            await update.message.reply_text("❌ Поддерживаются только PDF файлы")
            return
        
        await update.message.reply_text("📄 Обрабатываю PDF файл...")
        
        # Скачивание файла
        file = await document.get_file()
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_pdf:
            temp_pdf_path = temp_pdf.name
        
        download_file(file.file_path, temp_pdf_path)
        
        # Извлечение текста из PDF
        extracted_text = extract_text_from_pdf(temp_pdf_path)
        
        if extracted_text.startswith("Ошибка"):
            await update.message.reply_text(f"❌ {extracted_text}")
            return
        
        if not extracted_text.strip():
            await update.message.reply_text("❌ Не удалось извлечь текст из PDF файла")
            return
        
        # Отправка извлеченного текста (первые 2000 символов)
        preview_text = extracted_text[:2000] + ("..." if len(extracted_text) > 2000 else "")
        await update.message.reply_text(f"📖 Извлеченный текст (фрагмент):\n\n{preview_text}")
        
        # Обработка с помощью AI
        await update.message.reply_text("🧠 Анализирую содержание с помощью AI...")
        analyzed_text = await process_pdf_with_ai(extracted_text)
        
        # Отправка анализа
        if analyzed_text.startswith("Ошибка"):
            await update.message.reply_text(f"❌ {analyzed_text}")
        else:
            await update.message.reply_text(f"📊 Анализ PDF:\n\n{analyzed_text}")
        
        # Очистка временного файла
        os.unlink(temp_pdf_path)
        
    except Exception as e:
        logger.error(f"Error processing PDF: {e}")
        await update.message.reply_text("❌ Произошла ошибка при обработке PDF файла")

async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик callback запросов"""
    query = update.callback_query
    await query.answer()
    
    if query.data.startswith('improve:'):
        parts = query.data.split(':', 2)
        if len(parts) == 3:
            improve_type = parts[1]
            text_to_improve = parts[2]
            
            await query.edit_message_text("✨ Улучшаю текст...")
            
            if improve_type == "balance":
                result = await improve_text_with_ai(text_to_improve, "general")
            elif improve_type == "correct":
                result = await correct_text_with_ai(text_to_improve)
            elif improve_type == "format":
                result = await format_text_with_ai(text_to_improve)
            else:
                result = await improve_text_with_ai(text_to_improve, "general")
            
            if result.startswith("Ошибка"):
                await query.message.reply_text(f"❌ {result}")
            else:
                await query.message.reply_text(f"✨ Улучшенный текст:\n\n{result}")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ошибок"""
    logger.error(f"Update {update} caused error {context.error}")
    if update and update.message:
        await update.message.reply_text("❌ Произошла непредвиденная ошибка")

def main():
    """Основная функция"""
    # Создание приложения
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Добавление обработчиков
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("improve", improve_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    application.add_handler(MessageHandler(filters.VOICE, handle_voice))
    application.add_handler(MessageHandler(filters.AUDIO, handle_voice))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    
    # Обработчик callback запросов
    from telegram.ext import CallbackQueryHandler
    application.add_handler(CallbackQueryHandler(handle_callback_query))
    
    # Обработчик ошибок
    application.add_error_handler(error_handler)
    
    # Запуск бота
    print("🤖 AI бот запущен...")
    print("📁 Поддерживаемые форматы: текст, голосовые, аудио, PDF")
    application.run_polling()

if __name__ == "__main__":
    main()