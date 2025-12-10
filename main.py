import logging
import threading
import uvicorn
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler

# Loyiha modullari
from core.config import settings
from core.database import engine
from core.models import Base
from core.hik_server import app as fastapi_app

# Bot handlerlari
from bot import states
from bot.handlers import admin, employee, common

# Loglarni sozlash
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# 1. Baza jadvallarini yaratish (agar yo'q bo'lsa)
Base.metadata.create_all(bind=engine)

def run_fastapi():
    """
    Hikvision qurilmalaridan keladigan signallarni qabul qiluvchi
    FastAPI serverini ishga tushirish.
    """
    uvicorn.run(fastapi_app, host="0.0.0.0", port=settings.SERVER_PORT, log_level="warning")

def main():
    """
    Loyihaning asosiy kirish nuqtasi.
    """
    logger.info("🚀 FaceID Tizimi ishga tushmoqda...")

    # 2. FastAPI Serverni alohida oqimda (Thread) ishga tushiramiz
    # daemon=True degani - asosiy dastur o'chsa, bu server ham o'chadi
    server_thread = threading.Thread(target=run_fastapi, daemon=True)
    server_thread.start()
    logger.info(f"📡 Hikvision Server {settings.SERVER_PORT}-portda tinglamoqda...")

    # 3. Telegram Botni sozlash
    updater = Updater(settings.BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    # --- HANDLERLARNI ULASH ---

    # A) Admin: Filial qo'shish jarayoni
    branch_conv = ConversationHandler(
        entry_points=[MessageHandler(Filters.regex('^➕ Filial'), admin.add_branch_start)],
        states={
            states.BRANCH_NAME: [MessageHandler(Filters.text & ~Filters.regex('^⬅️'), admin.get_branch_name)],
            states.BRANCH_SHEET_ID: [MessageHandler(Filters.text & ~Filters.regex('^⬅️'), admin.get_branch_sheet)],
        },
        fallbacks=[MessageHandler(Filters.regex('^⬅️'), common.cancel)]
    )

    # B) Admin: Qurilma qo'shish jarayoni
    device_conv = ConversationHandler(
        entry_points=[MessageHandler(Filters.regex('^➕ Qurilma'), admin.add_device_start)],
        states={
            states.DEV_SELECT_BRANCH: [MessageHandler(Filters.text & ~Filters.regex('^⬅️'), admin.get_dev_branch)],
            states.DEV_IP: [MessageHandler(Filters.text & ~Filters.regex('^⬅️'), admin.get_dev_ip)],
            states.DEV_USER: [MessageHandler(Filters.text & ~Filters.regex('^⬅️'), admin.get_dev_user)],
            states.DEV_PASS: [MessageHandler(Filters.text & ~Filters.regex('^⬅️'), admin.get_dev_pass)],
            states.DEV_TYPE: [MessageHandler(Filters.text & ~Filters.regex('^⬅️'), admin.get_dev_type)],
        },
        fallbacks=[MessageHandler(Filters.regex('^⬅️'), common.cancel)]
    )

    # C) Admin: Bildirishnoma sozlash (YANGI QO'SHILDI)
    notif_conv = ConversationHandler(
        entry_points=[MessageHandler(Filters.regex('^🔔 Bildirishnoma'), admin.set_notification_start)],
        states={
            states.NOTIF_EMP_ID: [MessageHandler(Filters.text & ~Filters.regex('^⬅️'), admin.get_notif_emp_id)],
            states.NOTIF_CHAT_ID: [MessageHandler(Filters.text & ~Filters.regex('^⬅️'), admin.get_notif_chat_id)],
        },
        fallbacks=[MessageHandler(Filters.regex('^⬅️'), common.cancel)]
    )

    # D) Xodim: Rasm yuklash jarayoni
    # Bu yerda ID raqam yuborilganda ishga tushadi (Buyruq va tugmalardan tashqari matnlar)
    emp_conv = ConversationHandler(
        entry_points=[
            MessageHandler(
                Filters.text & ~Filters.command & ~Filters.regex('^(➕|🔄|📋|🔔|⬅️)'), 
                employee.handle_id
            )
        ],
        states={
            states.WAITING_PHOTO: [MessageHandler(Filters.photo, employee.handle_photo)]
        },
        fallbacks=[
            CommandHandler('cancel', common.cancel),
            MessageHandler(Filters.regex('^⬅️'), common.cancel)
        ]
    )

    # E) Umumiy va Admin buyruqlari
    dp.add_handler(CommandHandler("start", common.start))
    dp.add_handler(MessageHandler(Filters.regex('^🔄 Google'), admin.sync_sheets))
    dp.add_handler(MessageHandler(Filters.regex('^📋 Ma\'lumotlar'), admin.list_info))
    
    # Conversation handlerlarni qo'shish
    dp.add_handler(branch_conv)
    dp.add_handler(device_conv)
    dp.add_handler(notif_conv) # <-- Yangi handler qo'shildi
    dp.add_handler(emp_conv)

    # 4. Botni ishga tushirish
    logger.info("🤖 Telegram Bot ishga tushdi va xabarlarni kutmoqda...")
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()