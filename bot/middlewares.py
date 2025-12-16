from functools import wraps
from telegram import Update
from telegram.ext import CallbackContext
from core.config import settings

def super_admin_only(func):

    @wraps(func)
    def wrapped(update: Update, context: CallbackContext, *args, **kwargs):
        user_id = update.effective_user.id
        if user_id != settings.SUPER_ADMIN_ID:
            update.message.reply_text("⛔️ Sizda bu buyruqni bajarish huquqi yo'q!")
            return
        return func(update, context, *args, **kwargs)
    return wrapped