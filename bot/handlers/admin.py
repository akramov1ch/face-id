import random
import string
from telegram import Update, ReplyKeyboardRemove, ReplyKeyboardMarkup
from telegram.ext import CallbackContext, ConversationHandler
from sqlalchemy.orm import Session

# Loyiha modullari
from bot import states, keyboards
from core.database import SessionLocal
from core.models import Branch, Device, Employee, DeviceType
from core.sheets import GoogleSheetManager
from core.config import settings

# --- YORDAMCHI FUNKSIYALAR ---

def get_db():
    """Baza sessiyasini yaratish"""
    return SessionLocal()

def cancel(update: Update, context: CallbackContext):
    """Jarayonni bekor qilish"""
    update.message.reply_text("🚫 Jarayon bekor qilindi.", reply_markup=keyboards.get_admin_keyboard())
    return ConversationHandler.END

def generate_new_id():
    """6 xonali tasodifiy raqamli ID yaratadi (masalan: 102938)"""
    return ''.join(random.choices(string.digits, k=6))

def normalize_text(text):
    """Matnni solishtirish uchun tozalash (kichik harf, bo'sh joylarsiz)"""
    if not text: return ""
    return text.lower().replace(" ", "")

# ============================================================================
# 1. FILIAL QO'SHISH (ADD BRANCH)
# ============================================================================

def add_branch_start(update: Update, context: CallbackContext):
    if update.effective_user.id != settings.SUPER_ADMIN_ID:
        return ConversationHandler.END
    
    update.message.reply_text(
        "🏢 **Yangi filial nomini kiriting:**\n"
        "(Diqqat: Bu nom Google Sheet dagi 'Filial' ustuni bilan bir xil bo'lishi shart!)",
        reply_markup=keyboards.get_cancel_keyboard(),
        parse_mode='Markdown'
    )
    return states.BRANCH_NAME

def get_branch_name(update: Update, context: CallbackContext):
    text = update.message.text
    if text == "⬅️ Bekor qilish": return cancel(update, context)
    
    context.user_data['b_name'] = text
    update.message.reply_text(
        "📄 **Google Sheet ID sini kiriting:**\n"
        "Bu filialning davomati (Kirish/Chiqish tarixi) qaysi Sheetga yozilsin?\n"
        "(ID yoki to'liq URL yuborishingiz mumkin)",
        reply_markup=keyboards.get_cancel_keyboard(),
        parse_mode='Markdown'
    )
    return states.BRANCH_SHEET_ID

def get_branch_sheet(update: Update, context: CallbackContext):
    text = update.message.text
    if text == "⬅️ Bekor qilish": return cancel(update, context)
    
    # Sheet ID ni tozalash (agar to'liq URL tashlansa)
    sheet_id = text
    if "/d/" in text:
        try:
            sheet_id = text.split("/d/")[1].split("/")[0]
        except:
            pass 

    db: Session = get_db()
    try:
        new_branch = Branch(name=context.user_data['b_name'], attendance_sheet_id=sheet_id)
        db.add(new_branch)
        db.commit()
        update.message.reply_text(
            f"✅ **Filial muvaffaqiyatli qo'shildi!**\n\n"
            f"🏢 Nomi: `{new_branch.name}`\n"
            f"📄 Sheet ID: `{sheet_id}`",
            reply_markup=keyboards.get_admin_keyboard(),
            parse_mode='Markdown'
        )
    except Exception as e:
        update.message.reply_text(
            f"❌ **Xatolik yuz berdi:**\n{e}\n"
            "(Ehtimol bu nomdagi filial allaqachon mavjud)",
            reply_markup=keyboards.get_admin_keyboard(),
            parse_mode='Markdown'
        )
    finally:
        db.close()
    
    return ConversationHandler.END

# ============================================================================
# 2. QURILMA QO'SHISH (ADD DEVICE)
# ============================================================================

def add_device_start(update: Update, context: CallbackContext):
    if update.effective_user.id != settings.SUPER_ADMIN_ID: return ConversationHandler.END
    
    db = get_db()
    branches = db.query(Branch).all()
    db.close()

    if not branches:
        update.message.reply_text("❌ Tizimda filiallar yo'q. Avval filial qo'shing!")
        return ConversationHandler.END

    # Filiallar ro'yxatini tugma qilamiz
    buttons = [[b.name] for b in branches]
    buttons.append(["⬅️ Bekor qilish"])
    
    update.message.reply_text(
        "🖥 **Qaysi filialga qurilma qo'shmoqchisiz?**", 
        reply_markup=ReplyKeyboardMarkup(buttons, resize_keyboard=True, one_time_keyboard=True),
        parse_mode='Markdown'
    )
    return states.DEV_SELECT_BRANCH

def get_dev_branch(update: Update, context: CallbackContext):
    text = update.message.text
    if text == "⬅️ Bekor qilish": return cancel(update, context)

    db = get_db()
    branch = db.query(Branch).filter(Branch.name == text).first()
    db.close()

    if not branch:
        update.message.reply_text("❌ Filial topilmadi. Ro'yxatdan tanlang.")
        return states.DEV_SELECT_BRANCH

    context.user_data['d_branch_id'] = branch.id
    update.message.reply_text(
        "🌐 **Qurilma IP manzilini kiriting:**\n(Masalan: 192.168.1.64)", 
        reply_markup=keyboards.get_cancel_keyboard(),
        parse_mode='Markdown'
    )
    return states.DEV_IP

def get_dev_ip(update: Update, context: CallbackContext):
    if update.message.text == "⬅️ Bekor qilish": return cancel(update, context)
    context.user_data['d_ip'] = update.message.text
    update.message.reply_text("👤 **Qurilma Logini** (odatda 'admin'):", parse_mode='Markdown')
    return states.DEV_USER

def get_dev_user(update: Update, context: CallbackContext):
    if update.message.text == "⬅️ Bekor qilish": return cancel(update, context)
    context.user_data['d_user'] = update.message.text
    update.message.reply_text("🔑 **Qurilma Paroli:**", parse_mode='Markdown')
    return states.DEV_PASS

def get_dev_pass(update: Update, context: CallbackContext):
    if update.message.text == "⬅️ Bekor qilish": return cancel(update, context)
    context.user_data['d_pass'] = update.message.text
    update.message.reply_text(
        "⚙️ **Qurilma turini tanlang:**\n"
        "- Kirish: Faqat kirishni qayd qiladi\n"
        "- Chiqish: Faqat chiqishni qayd qiladi\n"
        "- Universal: Ikkalasini ham (yoki tugmaga qarab)",
        reply_markup=keyboards.get_device_type_keyboard(),
        parse_mode='Markdown'
    )
    return states.DEV_TYPE

def get_dev_type(update: Update, context: CallbackContext):
    text = update.message.text
    if text == "⬅️ Bekor qilish": return cancel(update, context)

    d_type = DeviceType.UNIVERSAL
    if "Entry" in text: d_type = DeviceType.ENTRY
    if "Exit" in text: d_type = DeviceType.EXIT

    db = get_db()
    try:
        new_device = Device(
            branch_id=context.user_data['d_branch_id'],
            ip_address=context.user_data['d_ip'],
            username=context.user_data['d_user'],
            password=context.user_data['d_pass'],
            device_type=d_type
        )
        db.add(new_device)
        db.commit()
        update.message.reply_text(
            f"✅ **Qurilma muvaffaqiyatli qo'shildi!**\n\n"
            f"🌐 IP: `{context.user_data['d_ip']}`\n"
            f"⚙️ Turi: {d_type.value}",
            reply_markup=keyboards.get_admin_keyboard(),
            parse_mode='Markdown'
        )
    except Exception as e:
        update.message.reply_text(f"❌ Xatolik: {e}")
    finally:
        db.close()
    return ConversationHandler.END

# ============================================================================
# 3. GOOGLE SHEETS SINXRONIZATSIYA (SYNC & ID GENERATION) - YANGILANGAN
# ============================================================================

def sync_sheets(update: Update, context: CallbackContext):
    if update.effective_user.id != settings.SUPER_ADMIN_ID: return

    msg = update.message.reply_text("⏳ **Sinxronizatsiya va ID yaratish boshlanmoqda...**\nBu biroz vaqt olishi mumkin.", parse_mode='Markdown')
    
    db = SessionLocal()
    manager = GoogleSheetManager()
    
    try:
        # 1. Sheetdan ma'lumotlarni "xom" holatda olamiz (worksheet va qator raqami bilan)
        raw_data = manager.get_all_employees_raw()
        
        if not raw_data:
            msg.edit_text("❌ Sheet bo'sh yoki o'qib bo'lmadi (Loglarni tekshiring).")
            return

        # 2. Bazadagi barcha xodimlarni xotiraga olamiz (tezkor qidirish uchun)
        all_employees = db.query(Employee).all()
        
        # ID bo'yicha qidirish uchun lug'at
        db_emp_by_id = {e.account_id: e for e in all_employees}
        
        # Ism va Filial bo'yicha qidirish uchun lug'at (ID yo'q bo'lganda ishlatiladi)
        # Kalit: (branch_id, normalized_full_name)
        db_emp_by_name = {(e.branch_id, normalize_text(e.full_name)): e for e in all_employees}

        count_new = 0
        count_updated = 0
        count_generated = 0
        count_recovered = 0 # Bazadan topib Sheetga yozilganlar
        not_found_branches = set()

        # 3. Har bir qatorni aylanamiz
        for worksheet, row_num, data in raw_data:
            sheet_acc_id = data['account_id'] # Sheetdagi ID
            full_name = data['full_name']
            b_name = data['branch_name']

            # Filialni tekshirish
            branch = db.query(Branch).filter(Branch.name == b_name).first()
            if not branch:
                not_found_branches.add(b_name)
                continue 

            # --- ALGORITM BOSHLANDI ---

            # 1-HOLAT: Sheetda ID bor
            if sheet_acc_id:
                if sheet_acc_id in db_emp_by_id:
                    # Bazada bor -> Update
                    existing_emp = db_emp_by_id[sheet_acc_id]
                    if existing_emp.full_name != full_name or existing_emp.branch_id != branch.id:
                        existing_emp.full_name = full_name
                        existing_emp.branch_id = branch.id
                        count_updated += 1
                else:
                    # Bazada yo'q -> Create (Sheetdagi ID bilan)
                    new_emp = Employee(
                        account_id=sheet_acc_id, 
                        full_name=full_name, 
                        branch_id=branch.id
                    )
                    db.add(new_emp)
                    # Yangi qo'shilganini lug'atga ham qo'shamiz (keyingi qatorlar uchun)
                    db_emp_by_id[sheet_acc_id] = new_emp
                    count_new += 1

            # 2-HOLAT: Sheetda ID YO'Q
            else:
                # Bazada shu filial va ism bilan xodim bormi?
                key = (branch.id, normalize_text(full_name))
                
                if key in db_emp_by_name:
                    # HA, BOR -> Bazadagi ID ni Sheetga yozish
                    existing_emp = db_emp_by_name[key]
                    
                    # Sheetga yozib qo'yamiz
                    success = manager.write_id_to_cell(worksheet, row_num, existing_emp.account_id)
                    if success:
                        count_recovered += 1
                    
                    # Ma'lumotlarni yangilash (agar kerak bo'lsa)
                    if existing_emp.full_name != full_name:
                        existing_emp.full_name = full_name
                        count_updated += 1
                else:
                    # YO'Q -> Yangi ID generatsiya qilish (Create)
                    new_id = generate_new_id()
                    
                    # Unikallikni tekshirish
                    while db.query(Employee).filter(Employee.account_id == new_id).first():
                        new_id = generate_new_id()
                    
                    # Sheetga yozish
                    success = manager.write_id_to_cell(worksheet, row_num, new_id)
                    if success:
                        count_generated += 1
                    
                    # Bazaga qo'shish
                    new_emp = Employee(
                        account_id=new_id, 
                        full_name=full_name, 
                        branch_id=branch.id
                    )
                    db.add(new_emp)
                    
                    # Lug'atlarni yangilash
                    db_emp_by_id[new_id] = new_emp
                    db_emp_by_name[(branch.id, normalize_text(full_name))] = new_emp
                    count_new += 1
        
        db.commit()
        
        result_text = (
            f"✅ **Jarayon yakunlandi!**\n\n"
            f"🆕 Bazaga yangi qo'shildi: {count_new}\n"
            f"🔄 Yangilandi: {count_updated}\n"
            f"🆔 **Yangi ID berildi (Sheetga yozildi): {count_generated}**\n"
            f"♻️ **Eski ID tiklandi (Sheetga yozildi): {count_recovered}**"
        )
        
        if not_found_branches:
            result_text += "\n\n⚠️ **Topilmagan filiallar:**\n" + ", ".join(not_found_branches)
            result_text += "\n(Avval '➕ Filial qo'shish' orqali ularni yarating)"

        msg.edit_text(result_text, parse_mode='Markdown')

    except Exception as e:
        msg.edit_text(f"❌ Xatolik yuz berdi: {e}")
    finally:
        db.close()

# ============================================================================
# 4. MA'LUMOTLARNI KO'RISH (LIST INFO)
# ============================================================================

def list_info(update: Update, context: CallbackContext):
    if update.effective_user.id != settings.SUPER_ADMIN_ID: return

    db = get_db()
    branches = db.query(Branch).all()
    
    if not branches:
        update.message.reply_text("📭 Tizimda ma'lumotlar yo'q.")
        db.close()
        return

    text = "📊 **Tizim ma'lumotlari:**\n\n"
    for b in branches:
        dev_count = len(b.devices)
        emp_count = len(b.employees)
        text += (
            f"🏢 **{b.name}**\n"
            f"   - 🖥 Qurilmalar: {dev_count} ta\n"
            f"   - 👥 Xodimlar: {emp_count} ta\n"
            f"   - 📄 Sheet ID: `{b.attendance_sheet_id}`\n\n"
        )
    
    db.close()
    update.message.reply_text(text, parse_mode='Markdown')

# ============================================================================
# 5. BILDIRISHNOMA SOZLASH (NOTIFICATION LINK)
# ============================================================================

def set_notification_start(update: Update, context: CallbackContext):
    if update.effective_user.id != settings.SUPER_ADMIN_ID: return ConversationHandler.END
    
    update.message.reply_text(
        "🔔 **Bildirishnoma sozlash**\n\n"
        "Qaysi xodimning davomatini kuzatmoqchisiz?\n"
        "Iltimos, xodimning **ID raqamini** kiriting (masalan: 101):",
        reply_markup=keyboards.get_cancel_keyboard(),
        parse_mode='Markdown'
    )
    return states.NOTIF_EMP_ID

def get_notif_emp_id(update: Update, context: CallbackContext):
    text = update.message.text
    if text == "⬅️ Bekor qilish": return cancel(update, context)
    
    db = get_db()
    employee = db.query(Employee).filter(Employee.account_id == text).first()
    db.close()
    
    if not employee:
        update.message.reply_text("❌ Bunday ID li xodim topilmadi. Qayta kiriting:")
        return states.NOTIF_EMP_ID
    
    context.user_data['notif_emp_db_id'] = employee.id
    context.user_data['notif_emp_name'] = employee.full_name
    
    update.message.reply_text(
        f"👤 Xodim: **{employee.full_name}**\n\n"
        "Endi xabarlar qaysi **Telegram ID** ga borishini yozing.\n"
        "(Masalan: 9988776655)",
        reply_markup=keyboards.get_cancel_keyboard(),
        parse_mode='Markdown'
    )
    return states.NOTIF_CHAT_ID

def get_notif_chat_id(update: Update, context: CallbackContext):
    text = update.message.text
    if text == "⬅️ Bekor qilish": return cancel(update, context)
    
    if not text.isdigit():
        update.message.reply_text("❌ Iltimos, faqat raqamlardan iborat Telegram ID kiriting.")
        return states.NOTIF_CHAT_ID
        
    chat_id = int(text)
    emp_db_id = context.user_data['notif_emp_db_id']
    
    db = get_db()
    try:
        employee = db.query(Employee).filter(Employee.id == emp_db_id).first()
        employee.notification_chat_id = chat_id
        db.commit()
        
        update.message.reply_text(
            f"✅ **Muvaffaqiyatli bog'landi!**\n\n"
            f"👤 Xodim: {context.user_data['notif_emp_name']}\n"
            f"📲 Xabar boradigan ID: `{chat_id}`",
            reply_markup=keyboards.get_admin_keyboard(),
            parse_mode='Markdown'
        )
    except Exception as e:
        update.message.reply_text(f"❌ Xatolik: {e}")
    finally:
        db.close()
        
    return ConversationHandler.END