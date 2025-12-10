from telegram import Update, ReplyKeyboardRemove
from telegram.ext import CallbackContext, ConversationHandler
from core.database import SessionLocal
from core.models import Employee, Device
from core.hik_device import upload_to_branch_devices
from bot import states
import io

def handle_id(update: Update, context: CallbackContext):
    text = update.message.text.strip()
    
    # Admin buyruqlarini o'tkazib yuborish
    if text.startswith("➕") or text.startswith("🔄"): return

    db = SessionLocal()
    employee = db.query(Employee).filter(Employee.account_id == text).first()
    
    if not employee:
        db.close()
        update.message.reply_text("❌ Bunday ID topilmadi. Qaytadan urinib ko'ring.")
        return ConversationHandler.END
    
    # Xodim ma'lumotlarini saqlab olamiz
    context.user_data['emp_id'] = employee.account_id
    context.user_data['emp_name'] = employee.full_name
    context.user_data['branch_id'] = employee.branch_id
    
    # Filial nomini olish uchun
    branch_name = employee.branch.name
    db.close()

    update.message.reply_text(
        f"👋 Salom, *{context.user_data['emp_name']}*!\n"
        f"Filial: *{branch_name}*\n\n"
        "📸 Iltimos, Face ID uchun **selfi tushib yuboring**.",
        parse_mode='Markdown',
        reply_markup=ReplyKeyboardRemove()
    )
    return states.WAITING_PHOTO

def handle_photo(update: Update, context: CallbackContext):
    user_id = context.user_data.get('emp_id')
    branch_id = context.user_data.get('branch_id')
    
    if not user_id:
        update.message.reply_text("Sessiya eskirgan. ID ni qayta yuboring.")
        return ConversationHandler.END

    msg = update.message.reply_text("⏳ Rasm qabul qilindi. Filialdagi barcha qurilmalarga yuklanmoqda...")

    # 1. Rasmni yuklab olish
    photo_file = update.message.photo[-1].get_file()
    f = io.BytesIO()
    photo_file.download(out=f)
    image_bytes = f.getvalue()

    # 2. Filialdagi barcha qurilmalarni olish
    db = SessionLocal()
    devices = db.query(Device).filter(Device.branch_id == branch_id).all()
    
    if not devices:
        msg.edit_text("❌ Sizning filialingizda qurilmalar topilmadi. Adminga murojaat qiling.")
        db.close()
        return ConversationHandler.END

    # Qurilmalar ro'yxatini tayyorlash
    dev_list = [{'ip': d.ip_address, 'user': d.username, 'pass': d.password} for d in devices]
    db.close()

    # 3. Yuklash (Core Logic)
    results = upload_to_branch_devices(dev_list, user_id, image_bytes)

    # 4. Natijani ko'rsatish
    report = "📊 **Yuklash natijalari:**\n\n"
    success_count = 0
    
    for res in results:
        status = "✅ OK" if res['success'] else f"❌ Xato ({res['msg']})"
        report += f"🖥 IP {res['ip']}: {status}\n"
        if res['success']: success_count += 1
    
    if success_count == len(devices):
        final_text = f"✅ **Muvaffaqiyatli!**\nRasm barcha {success_count} ta qurilmaga yuklandi."
    else:
        final_text = f"⚠️ **Qisman yuklandi.**\n\n{report}"

    msg.edit_text(final_text, parse_mode='Markdown')
    context.user_data.clear()
    return ConversationHandler.END