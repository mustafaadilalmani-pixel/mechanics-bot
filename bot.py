import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes

# إعداد السجلات لمتابعة عمل البوت
logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# إعدادات البوت الأساسية (تأكد من وضعها كمتغيرات بيئة في منصة Koyeb أو ضعها هنا مباشرة)
TOKEN = os.getenv("BOT_TOKEN", "7718978253:AAGr_...أضف التوكن الخاص بك هنا...")
ADMIN_ID = int(os.getenv("ADMIN_ID", "7066058422"))
CHANNEL_ID = int(os.getenv("CHANNEL_ID", "-1003936687336"))

# سعر الاشتراك وطريقة الدفع (يمكنك تعديلها حسب رغبتك)
SUBSCRIPTION_PRICE = "25 دولار"  # أو المبلغ بالدينار حسب رغبتك
PAYMENT_INFO = "يرجى التحويل على زين كاش أو الحساب التالي: \n`07800000000`\n\nبعد اكتمال الدفع، قم بإرسال **صورة (سكرين) الإيصال** هنا في الهوت ليتم التحويل وإرسال الرابط لك فوراً."

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """الرد على أمر البدء وإرسال تفاصيل السعر وطريقة الدفع"""
    welcome_text = (
        f"مرحباً بك يا بطل في بوت الاشتراك الخاص بالقناة الهندسية 🏗️\n\n"
        f"💰 **سعر الاشتراك الشهري:** {SUBSCRIPTION_PRICE}\n\n"
        f"📌 **طريقة الدفع:**\n{PAYMENT_INFO}"
    )
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """استلام صورة إيصال الدفع من الطالب وتحويلها للآدمي مع أزرار القبول والرفض"""
    user = update.message.from_user
    
    # التحقق من أن الرسالة مرفقة بصورة
    if not update.message.photo:
        return

    photo_file_id = update.message.photo[-1].file_id

    # رسالة تنبيه للطالب بأن السكرين وصل وجاري المراجعة
    await update.message.reply_text("⏳ تم استلام إيصال الدفع بنجاح! جاري مراجعته من قبل الإدارة وسيتم إرسال رابط القناة خلال لحظات.")

    # تجهيز الأزرار للآدمي (قبول أو رفض)
    keyboard = [
        [
            InlineKeyboardButton("✅ قبول وإرسال الرابط", callback_data=f"accept_{user.id}"),
            InlineKeyboardButton("❌ رفض", callback_data=f"reject_{user.id}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # إرسال تفاصيل الطالب وإيصال الدفع إلى الآدمي حصراً
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
            # 1. إنشاء رابط دعوة صالح للاستخدام مرة واحدة فقط وينتهي خلال 24 ساعة
            invite_link = await context.bot.create_chat_invite_link(
                chat_id=CHANNEL_ID,
                member_limit=1
            )

            # 2. إرسال الرابط للطالب وتأكيد تفعيل الاشتراك
            success_msg = (
                f"🎉 **مبروك! تم قبول اشتراكك بنجاح.**\n\n"
                f"🔗 إليك رابط الدخول الخاص بك للقناة (صالح للاستخدام مرة واحدة فقط):\n{invite_link.invite_link}\n\n"
                f"⏳ اشتراكك فعال لمدة **30 يوماً**."
            )
            await context.bot.send_message(chat_id=student_id, text=success_msg, parse_mode="Markdown")

            # 3. جدولة إزالة المستخدم تلقائياً بعد 30 يوماً (30 * 24 * 60 * 60 ثانية)
            # ملاحظة: لضمان عمل الجدولة بشكل دائم يفضل استخدام قاعدة بيانات، لكن سنستخدم الجدولة المؤقتة بالذاكرة هنا
            context.job_queue.run_once(kick_user_from_channel, when=30 * 86400, data={"user_id": student_id, "chat_id": CHANNEL_ID})

            # تحديث رسالة الآدمي لتوضيح أنه تم القبول
            await query.edit_message_caption(caption=query.message.caption + "\n\n✅ **[تم قبول الطلب وإرسال الرابط للطالب]**", reply_markup=None)

        except Exception as e:
            await query.message.reply_text(f"⚠️ حدث خطأ أثناء إنشاء الرابط (تأكد أن البوت مشرف في القناة وله صلاحية إضافة أعضاء): {e}")

    elif action == "reject":
        # إبلاغ الطالب برفض الإيصال
        try:
            await context.bot.send_message(
                chat_id=student_id,
                text="❌ عذراً، تم رفض إيصال الدفع المرسل. يرجى التأكد من السجل أو مراسلة الدعم الفني."
            )
        except:
            pass

        # تحديث رسالة الآدمي لتوضيح أنه تم الرفض
        await query.edit_message_caption(caption=query.message.caption + "\n\n❌ **[تم رفض الطلب]**", reply_markup=None)

async def kick_user_from_channel(context: ContextTypes.DEFAULT_TYPE):
    """وظيفة طرد الطالب من القناة تلقائياً بعد انتهاء الـ 30 يوم"""
    job_data = context.job.data
    user_id = job_data["user_id"]
    chat_id = job_data["chat_id"]

    try:
        # حظر المؤقت ثم فك الحظر عنه (هذه هي الطريقة البرمجية الرسمية لطرد العضو من القناة في تليجرام)
        await context.bot.ban_chat_member(chat_id=chat_id, user_id=user_id)
        await context.bot.unban_chat_member(chat_id=chat_id, user_id=user_id)
        
        # إعلام الطالب بانتهاء اشتراكه
        await context.bot.send_message(
            chat_id=user_id,
            text="⚠️ انتهت مدة اشتراكاتك الـ 30 يوماً وتم إخراجك من القناة تلقائياً. لتجديد الاشتراك يرجى إرسال /start من جديد."
        )
    except Exception as e:
        logger.error(f"Failed to kick user {user_id}: {e}")

def main():
    """تشغيل وبدء تشغيل البوت"""
    # احصل على التوكن من متغيرات البيئة أو ضعه مباشرة هنا للاختبار
    bot_token = os.getenv("BOT_TOKEN", "7718978253:AAGr_...ضع التوكن هنا إذا لم تضعه في Variables...")
    
    application = Application.builder().token(bot_token).build()

    # الأوامر والمعالجات
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.PHOTO & ~filters.USER(ADMIN_ID), handle_photo))
    application.add_handler(CallbackQueryHandler(button_callback))

    # بدء التشغيل
    print("Bot is running...")
    application.run_polling()

if __name__ == "__main__":
    main()
