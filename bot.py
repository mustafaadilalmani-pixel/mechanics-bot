import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, CallbackQueryHandler, filters

TOKEN = "866400496:AAFikQUu7sj8EiuUwbTnqnWxmUTCpse8NGY"
ADMIN_ID = 7066058422
CHANNEL_ID = -1003936687336

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    welcome_msg = (
        "مرحباً بك في منصة ميكانيك الهندسي (المرحلة الأولى) 🎓\n\n"
        "💰 سعر الاشتراك الشهري: 15 دولار (أو ما يعادلها بالدينار العراقي).\n\n"
        "💳 طرق الدفع المتاحة:\n"
        "- حساب ماستر كي: `7111439357`\n\n"
        "📸 بعد إتمام التحويل، يرجى إرسال صورة (إيصال الدفع / السكرين) هنا مباشرة، وسيتم مراجعته وتفعيل اشتراكك في القناة فوراً."
    )
    await update.message.reply_text(welcome_msg, parse_mode="Markdown")

async def handle_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    if update.message.photo:
        photo_file = update.message.photo[-1].file_id
        
        keyboard = [
            [
                InlineKeyboardButton("✅ قبول وتفعيل", callback_data=f"accept_{user.id}"),
                InlineKeyboardButton("❌ رفض", callback_data=f"reject_{user.id}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        caption = (
            f"📥 طلب اشتراك جديد:\n"
            f"👤 اسم الطالب: {user.first_name}\n"
            f"🔗 المعرف: @{user.username if user.username else 'لا يوجد'}\n"
            f"🆔 الآدي: `{user.id}`"
        )
        
        await context.bot.send_photo(
            chat_id=ADMIN_ID,
            photo=photo_file,
            caption=caption,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        
        await update.message.reply_text("⏳ تم استلام السكرين بنجاح، جاري التحقق من الحوالة وتفعيل اشتراكك...")
    else:
        await update.message.reply_text("يرجى إرسال صورة إيصال التحويل (سكرين) حصراً.")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    action, student_id = data.split("_")
    student_id = int(student_id)
    
    if action == "accept":
        try:
            expire_date = datetime.datetime.now() + datetime.timedelta(days=1)
            invite_link = await context.bot.create_chat_invite_link(
                chat_id=CHANNEL_ID,
                member_limit=1,
                expire_date=expire_date
            )
            
            await context.bot.send_message(
                chat_id=student_id,
                text=(
                    f"🎉 تم قبول اشتراكك بنجاح!\n\n"
                    f"🔗 إليك رابط الدخول الخاص بك للقناة (مخصص لك وحدك وصالح لمرة واحدة):\n"
                    f"{invite_link.invite_link}\n\n"
                    f"⏱️ ملاحظة: اشتراكك مفعل لمدة 30 يوماً من الآن."
                )
            )
            
            context.job_queue.run_once(kick_student, when=datetime.timedelta(days=30), data=student_id)
            
            await query.edit_message_caption(caption=query.message.caption + "\n\n✅ **تم القبول وإرسال الرابط وجدولة الطرد بعد 30 يوماً.**", parse_mode="Markdown")
        
        except Exception as e:
            await query.edit_message_caption(caption=query.message.caption + f"\n\n⚠️ خطأ: {str(e)}")
            
    elif action == "reject":
        await context.bot.send_message(
            chat_id=student_id,
            text="❌ عذراً، تم رفض إيصال الدفع لعدم صحته أو عدم وضوحه. يرجى التأكد من الحوالة والمحاولة مرة أخرى."
        )
        await query.edit_message_caption(caption=query.message.caption + "\n\n❌ **تم رفض الطلب.**", parse_mode="Markdown")

async def kick_student(context: ContextTypes.DEFAULT_TYPE):
    student_id = context.job.data
    try:
        await context.bot.ban_chat_member(chat_id=CHANNEL_ID, user_id=student_id)
        await context.bot.unban_chat_member(chat_id=CHANNEL_ID, user_id=student_id)
        
        await context.bot.send_message(
            chat_id=student_id,
            text="⏳ انتهت مدة اشتراكك الشهرية (30 يوماً). تم إزالتك من القناة، ولتجديد الاشتراك يرجى التواصل مع الأستاذ وإرسال إيصال جديد."
        )
    except Exception as e:
        print(f"Error kicking student: {e}")

def main():
    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.PHOTO & ~filters.COMMAND, handle_receipt))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
