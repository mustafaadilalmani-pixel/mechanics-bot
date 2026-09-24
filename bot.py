import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# إعداد السجلات لمتابعة عمل البوت
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# إعدادات البوت الأساسية
TOKEN = os.getenv("BOT_TOKEN", "7718978253:AAGr_...أضف التوكن هنا...")
ADMIN_ID = int(os.getenv("ADMIN_ID", "7066058422"))
CHANNEL_ID = int(os.getenv("CHANNEL_ID", "-1003936687336"))

# سعر الاشتراك وطريقة الدفع
SUBSCRIPTION_PRICE = "25 دولار"
PAYMENT_INFO = "يرجى التحويل على زين كاش أو الحساب التالي: \n`07800000000`\n\nبعد اكتمال الدفع، قم بإرسال **صورة (سكرين) الإيصال** هنا في البوت ليتم التحقق منه وإرسال الرابط لك فوراً."

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """الرد على أمر البدء وإرسال تفاصيل السعر وطريقة الدفع"""
    welcome_text = (
        f"مرحباً بك يا بطل في بوت الاشتراك الخاص بالقناة 🏗️\n\n"
        f"💰 **سعر الاشتراك الشهري:** {SUBSCRIPTION_PRICE}\n\n"
        f"📌 **طريقة الدفع:**\n{PAYMENT_INFO}"
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """استلام صورة إيصال الدفع من الطالب وتحويلها للآدمي مع أزرار القبول والرفض"""
    user = update.message.from_user
    
    if not update.message.photo:
        return

    photo_file_id = update.message.photo[-1].file_id

    # رسالة تنبيه للطالب
    await update.message.reply_text("⏳ تم استلام إيصال الدفع بنجاح! جاري مراجعته من قبل الإدارة وسيتم إرسال رابط القناة خلال لحظات.")

    # تجهيز الأزرار للآدمي
    keyboard = [
        [
            InlineKeyboardButton("✅ قبول وإرسال الرابط", callback_data=f"accept_{user.id}"),
            InlineKeyboardButton("❌ رفض", callback_data=f"reject_{user.id}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # إرسال تفاصيل الطالب والإيصال للآدمي
    caption = (
        f"🔔 **طلب اشتراك جديد معلق!**\n\n"
        f"👤 **اسم الطالب:** {user.full_name}\n"
        f"🆔 **معرف الحساب:** @{user.username if user.username else 'لا يوجد'}\n"
        f"🔢 **الـ ID:** `{user.id}`"
    )
    
    await context.bot.send_photo(
        chat_id=ADMIN_ID,
        photo=photo_file_id,
        caption=caption,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """التعامل مع ضغطات أزرار القبول أو الرفض من قبل الآدمي"""
    query = update.callback_query
    await query.answer()

    data = query.data
    action, student_id_str = data.split("_")
    student_id = int(student_id_str)

    if action == "accept":
        try:
            # إنشاء رابط دعوة صالح للاستخدام مرة واحدة فقط
            invite_link = await context.bot.create_chat_invite_link(
                chat_id=CHANNEL_ID,
                member_limit=1
            )

            # إرسال الرابط للطالب
            success_msg = (
                f"🎉 **مبروك! تم قبول اشتراكك بنجاح.**\n\n"
                f"🔗 إليك رابط الدخول الخاص بك للقناة (صالح للاستخدام مرة واحدة فقط):\n{invite_link.invite_link}\n\n"
                f"⏳ اشتراكك فعال لمدة **30 يوماً**."
            )
            await context.bot.send_message(chat_id=student_id, text=success_msg, parse_mode="Markdown")

            # جدولة إزالة المستخدم بعد 30 يوماً
            context.job_queue.run_once(kick_user_from_channel, when=30 * 86400, data={"user_id": student_id, "chat_id": CHANNEL_ID})

            # تحديث رسالة الآدمي
            await query.edit_message_caption(caption=query.message.caption + "\n\n✅ **[تم قبول الطلب وإرسال الرابط للطالب]**", reply_markup=None)

        except Exception as e:
            await query.message.reply_text(f"⚠️ حدث خطأ أثناء إنشاء الرابط (تأكد أن البوت مشرف في القناة): {e}")

    elif action == "reject":
        try:
            await context.bot.send_message(
                chat_id=student_id,
                text="❌ عذراً، تم رفض إيصال الدفع المرسل. يرجى التأكد من السجل أو مراسلة الدعم الفني."
            )
        except:
            pass

        await query.edit_message_caption(caption=query.message.caption + "\n\n❌ **[تم رفض الطلب]**", reply_markup=None)

async def kick_user_from_channel(context: ContextTypes.DEFAULT_TYPE):
    """طرد الطالب من القناة تلقائياً بعد انتهاء الـ 30 يوم"""
    job_data = context.job.data
    user_id = job_data["user_id"]
    chat_id = job_data["chat_id"]

    try:
        await context.bot.ban_chat_member(chat_id=chat_id, user_id=user_id)
        await context.bot.unban_chat_member(chat_id=chat_id, user_id=user_id)
        
        await context.bot.send_message(
            chat_id=user_id,
            text="⚠️ انتهت مدة اشتراكك الـ 30 يوماً وتم إخراجك من القناة تلقائياً. لتجديد الاشتراك يرجى إرسال /start من جديد."
        )
    except Exception as e:
        logger.error(f"Failed to kick user {user_id}: {e}")

def main():
    bot_token = os.getenv("BOT_TOKEN", "7718978253:AAGr_...ضع التوكن هنا...")
    
    application = Application.builder().token(bot_token).build()

    # المعالجات والأوامر (تم تصحيح فلتر المستخدم هنا)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.PHOTO & ~filters.User(ADMIN_ID), handle_photo))
    application.add_handler(CallbackQueryHandler(button_callback))

    print("Bot is running...")
    application.run_polling()

if __name__ == "__main__":
    main()
