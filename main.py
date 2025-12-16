import logging
import threading
import uvicorn
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler

from core.config import settings
from core.database import engine
from core.models import Base
from core.hik_server import app as fastapi_app

from bot import states
from bot.handlers import admin, employee, common

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

Base.metadata.create_all(bind=engine)

def run_fastapi():
    uvicorn.run(fastapi_app, host="0.0.0.0", port=settings.SERVER_PORT, log_level="warning")

def main():
    logger.info("🚀 FaceID Tizimi ishga tushmoqda...")

    server_thread = threading.Thread(target=run_fastapi, daemon=True)
    server_thread.start()
    logger.info(f"📡 Hikvision Server {settings.SERVER_PORT}-portda tinglamoqda...")

    updater = Updater(settings.BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    branch_conv = ConversationHandler(
        entry_points=[MessageHandler(Filters.regex('^➕ Filial'), admin.add_branch_start)],
        states={
            states.BRANCH_NAME: [MessageHandler(Filters.text & ~Filters.regex('^⬅️'), admin.get_branch_name)],
            states.BRANCH_SHEET_ID: [MessageHandler(Filters.text & ~Filters.regex('^⬅️'), admin.get_branch_sheet)],
        },
        fallbacks=[MessageHandler(Filters.regex('^⬅️'), common.cancel)]
    )

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

    notif_conv = ConversationHandler(
        entry_points=[MessageHandler(Filters.regex('^🔔 Bildirishnoma'), admin.set_notification_start)],
        states={
            states.NOTIF_EMP_ID: [MessageHandler(Filters.text & ~Filters.regex('^⬅️'), admin.get_notif_emp_id)],
            states.NOTIF_CHAT_ID: [MessageHandler(Filters.text & ~Filters.regex('^⬅️'), admin.get_notif_chat_id)],
        },
        fallbacks=[MessageHandler(Filters.regex('^⬅️'), common.cancel)]
    )

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

    dp.add_handler(CommandHandler("start", common.start))
    dp.add_handler(MessageHandler(Filters.regex('^🔄 Google'), admin.sync_sheets))
    dp.add_handler(MessageHandler(Filters.regex('^📋 Ma\'lumotlar'), admin.list_info))
    
    dp.add_handler(branch_conv)
    dp.add_handler(device_conv)
    dp.add_handler(notif_conv)
    dp.add_handler(emp_conv)

    logger.info("🤖 Telegram Bot ishga tushdi va xabarlarni kutmoqda...")
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()