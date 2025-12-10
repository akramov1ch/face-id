from telegram import Update, ReplyKeyboardRemove
from telegram.ext import CallbackContext, ConversationHandler
from bot import keyboards
from core.config import settings

def start(update: Update, context: CallbackContext):
    """
    /start bosilganda ishlaydi.
    Admin bo'lsa -> Admin panelni ochadi.
    Xodim bo'lsa -> ID so'raydi.
    """
    user_id = update.effective_user.id
    
    if user_id == settings.SUPER_ADMIN_ID:
        update.message.reply_text(
            "👑 <b>Admin Panelga xush kelibsiz!</b>\n\nQuyidagi menyudan foydalaning:", 
            reply_markup=keyboards.get_admin_keyboard(),
            parse_mode='HTML'
        )
    else:
        update.message.reply_text(
            "👋 <b>Assalomu alaykum!</b>\n\n"
            "Tizimga kirish uchun 🆔 <b>ID raqamingizni</b> yozib yuboring.\n"
            "<i>(Masalan: 101 yoki YM2024)</i>",
            reply_markup=ReplyKeyboardRemove(),
            parse_mode='HTML'
        )

def cancel(update: Update, context: CallbackContext):
    """
    Jarayonni bekor qilish (ConversationHandler uchun).
    """
    user_id = update.effective_user.id
    
    # Agar admin bo'lsa, menyuni qaytaramiz
    if user_id == settings.SUPER_ADMIN_ID:
        markup = keyboards.get_admin_keyboard()
    else:
        markup = ReplyKeyboardRemove()
        
    update.message.reply_text("🚫 Jarayon bekor qilindi.", reply_markup=markup)
    context.user_data.clear()
    return ConversationHandler.END