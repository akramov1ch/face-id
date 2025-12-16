from telegram import ReplyKeyboardMarkup

def get_admin_keyboard():
    keyboard = [
        ["➕ Filial qo'shish", "➕ Qurilma qo'shish"],
        ["🔔 Bildirishnoma ulash", "🔄 Google Sheets Sync"], 
        ["📋 Ma'lumotlar"],
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

def get_device_type_keyboard():
    keyboard = [
        ["Kirish (Entry)", "Chiqish (Exit)"],
        ["Universal (Kirish/Chiqish)"],
        ["⬅️ Bekor qilish"]
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

def get_cancel_keyboard():
    return ReplyKeyboardMarkup([["⬅️ Bekor qilish"]], resize_keyboard=True)