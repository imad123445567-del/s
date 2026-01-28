#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎮 PUBG Mobile Account Analyzer Bot (Userbot)
نظام ذكي لمراقبة وتحليل وتسعير حسابات PUBG Mobile
"""

import asyncio
import logging
from datetime import datetime
from pyrogram import Client, filters, idle
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.handlers import MessageHandler, CallbackQueryHandler
import config
from modules.database import Database
from modules.detector import ItemDetector
from modules.pricing import PricingEngine
from modules.monitor import MessageMonitor
from modules.learning import LearningSystem
from modules.notifications import NotificationManager
from utils.safety import SafetyManager
from utils.image_processor import ImageProcessor

# إعداد Logging
logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(config.DATA_DIR / 'bot.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class PUBGAnalyzerBot:
    """البوت الرئيسي"""
    
    def __init__(self):
        # تهيئة Pyrogram Client (Userbot)
        self.app = Client(
            name=config.SESSION_NAME,
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            phone_number=config.PHONE_NUMBER,
            workdir=str(config.DATA_DIR)
        )
        
        # تهيئة المكونات
        self.db = Database()
        self.detector = ItemDetector(self.db)
        self.pricing = PricingEngine(self.db)
        self.monitor = MessageMonitor(self.db, self.detector, self.pricing)
        self.learning = LearningSystem(self.db, self.detector)
        self.notifications = NotificationManager(self.app)
        self.safety = SafetyManager()
        self.image_processor = ImageProcessor()
        
        # حالة البوت
        self.is_monitoring = False
        self.monitoring_task = None
        
        logger.info("✅ تم تهيئة البوت بنجاح")
    
    def setup_handlers(self):
        """تسجيل معالجات الأوامر"""
        
        # الأمر الرئيسي - فتح لوحة التحكم
        @self.app.on_message(filters.me & filters.command("start", prefixes="/"))
        async def start_command(client, message: Message):
            await self.show_main_menu(message)
        
        # معالج الأزرار
        @self.app.on_callback_query()
        async def callback_handler(client, callback):
            await self.handle_callback(callback)
        
        # معالج الرسائل في المحادثات المراقبة
        @self.app.on_message(filters.chat([]))
        async def monitor_handler(client, message: Message):
            if self.is_monitoring:
                await self.monitor.process_message(message)
        
        logger.info("✅ تم تسجيل معالجات الأوامر")
    
    async def show_main_menu(self, message: Message):
        """عرض القائمة الرئيسية"""
        stats = self.db.get_market_stats()
        
        text = f"""
🎮 **PUBG Account Analyzer**

📊 **الإحصائيات:**
• العناصر النادرة: {stats['total_items']}
• الحسابات المكتشفة: {stats['total_accounts']}
• الحسابات المبيوعة: {stats['sold_accounts']}

⚙️ **الحالة:** {'🟢 يعمل' if self.is_monitoring else '🔴 متوقف'}
"""
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📥 إدارة المصادر", callback_data="sources"),
                InlineKeyboardButton("🔍 فحص حساب", callback_data="analyze")
            ],
            [
                InlineKeyboardButton("➕ إضافة نوادر", callback_data="add_items"),
                InlineKeyboardButton("📊 تقارير السوق", callback_data="reports")
            ],
            [
                InlineKeyboardButton("💰 تسعير حساب", callback_data="price_account"),
                InlineKeyboardButton("⚙️ الإعدادات", callback_data="settings")
            ],
            [
                InlineKeyboardButton(
                    "⏸️ إيقاف المراقبة" if self.is_monitoring else "▶️ تشغيل المراقبة",
                    callback_data="toggle_monitoring"
                )
            ]
        ])
        
        await message.reply_text(text, reply_markup=keyboard)
    
    async def handle_callback(self, callback):
        """معالج النقرات على الأزرار"""
        data = callback.data
        
        if data == "sources":
            await self.show_sources_menu(callback)
        
        elif data == "add_source":
            await callback.message.reply_text(
                "📥 **إضافة مصدر جديد**\n\n"
                "قم بإرسال رابط أو username الكروب/القناة:\n"
                "مثال: @pubg_accounts أو https://t.me/pubg_store"
            )
        
        elif data == "add_items":
            await self.show_add_items_menu(callback)
        
        elif data == "add_items_batch":
            await callback.message.reply_text(
                "🖼️ **إضافة مجموعة نوادر**\n\n"
                "أرسل صورة واحدة تحتوي على عدة عناصر نادرة\n"
                "سيتم تقسيمها وتحليل كل عنصر على حدة"
            )
        
        elif data == "analyze":
            await callback.message.reply_text(
                "🔍 **فحص حساب**\n\n"
                "أرسل صورة أو فيديو للحساب المراد تحليله"
            )
        
        elif data == "reports":
            await self.show_market_reports(callback)
        
        elif data == "price_account":
            await callback.message.reply_text(
                "💰 **تسعير حساب**\n\n"
                "أرسل صورة أو فيديو الحساب لتقدير سعره السوقي"
            )
        
        elif data == "toggle_monitoring":
            await self.toggle_monitoring(callback)
        
        elif data == "settings":
            await self.show_settings(callback)
        
        elif data == "back_main":
            await self.show_main_menu(callback.message)
        
        elif data.startswith("remove_source_"):
            chat_id = int(data.replace("remove_source_", ""))
            await self.remove_source(callback, chat_id)
        
        await callback.answer()
    
    async def show_sources_menu(self, callback):
        """عرض قائمة المصادر"""
        sources = self.db.get_all_sources()
        
        text = f"📥 **المصادر المراقبة** ({len(sources)})\n\n"
        
        keyboard = []
        for source in sources[:10]:  # أول 10
            emoji = "📢" if source['chat_type'] == 'channel' else "👥"
            trust = "✅" if source['is_trusted'] else ""
            
            text += f"{emoji} {source['chat_title']} {trust}\n"
            text += f"   └ الرسائل: {source['total_messages_processed']}\n\n"
            
            keyboard.append([
                InlineKeyboardButton(
                    f"❌ {source['chat_title'][:20]}",
                    callback_data=f"remove_source_{source['chat_id']}"
                )
            ])
        
        keyboard.append([
            InlineKeyboardButton("➕ إضافة مصدر", callback_data="add_source")
        ])
        keyboard.append([
            InlineKeyboardButton("🔙 رجوع", callback_data="back_main")
        ])
        
        await callback.message.edit_text(
            text,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def show_add_items_menu(self, callback):
        """قائمة إضافة العناصر"""
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton(
                    "🖼️ صورة مجموعة نوادر (30-50 عنصر)",
                    callback_data="add_items_batch"
                )
            ],
            [
                InlineKeyboardButton(
                    "📷 إضافة عنصر واحد",
                    callback_data="add_single_item"
                )
            ],
            [
                InlineKeyboardButton("🔙 رجوع", callback_data="back_main")
            ]
        ])
        
        await callback.message.edit_text(
            "➕ **إضافة عناصر نادرة**\n\n"
            "اختر الطريقة المناسبة:",
            reply_markup=keyboard
        )
    
    async def show_market_reports(self, callback):
        """عرض تقارير السوق"""
        stats = self.db.get_market_stats()
        
        text = "📊 **تقارير السوق**\n\n"
        text += f"📦 إجمالي العناصر: {stats['total_items']}\n"
        text += f"🏪 الحسابات المكتشفة: {stats['total_accounts']}\n"
        text += f"✅ الحسابات المبيوعة: {stats['sold_accounts']}\n\n"
        
        text += "🔥 **أكثر العناصر ظهوراً:**\n"
        for item in stats['top_items'][:5]:
            text += f"• {item['name']}: {item['detection_count']} مرة\n"
        
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("📈 اتجاهات الأسعار", callback_data="price_trends"),
                InlineKeyboardButton("🎯 الطلب والعرض", callback_data="supply_demand")
            ],
            [
                InlineKeyboardButton("🔙 رجوع", callback_data="back_main")
            ]
        ])
        
        await callback.message.edit_text(text, reply_markup=keyboard)
    
    async def toggle_monitoring(self, callback):
        """تشغيل/إيقاف المراقبة"""
        self.is_monitoring = not self.is_monitoring
        
        if self.is_monitoring:
            # تشغيل المراقبة
            self.monitoring_task = asyncio.create_task(self.monitor.start_monitoring(self.app))
            await callback.answer("✅ تم تشغيل المراقبة", show_alert=True)
        else:
            # إيقاف المراقبة
            if self.monitoring_task:
                self.monitoring_task.cancel()
            await callback.answer("⏸️ تم إيقاف المراقبة", show_alert=True)
        
        await self.show_main_menu(callback.message)
    
    async def remove_source(self, callback, chat_id: int):
        """حذف مصدر"""
        success = self.db.remove_source(chat_id)
        
        if success:
            await callback.answer("✅ تم حذف المصدر", show_alert=True)
        else:
            await callback.answer("❌ فشل الحذف", show_alert=True)
        
        await self.show_sources_menu(callback)
    
    async def show_settings(self, callback):
        """عرض الإعدادات"""
        text = f"""
⚙️ **الإعدادات**

📊 **المراقبة:**
• الفاصل الزمني: {config.MONITOR_INTERVAL}s
• معالجة الوسائط فقط: {'نعم' if config.PROCESS_MEDIA_ONLY else 'لا'}

🎯 **الكشف:**
• حد الثقة: {config.CONFIDENCE_THRESHOLD * 100}%
• حد التشابه: {config.SIMILARITY_THRESHOLD * 100}%

🔔 **الإشعارات:**
• عند النوادر: {'نعم' if config.NOTIFY_ON_RARE else 'لا'}
• عند السعر الجيد: {'نعم' if config.NOTIFY_ON_GOOD_PRICE else 'لا'}

💾 **التخزين:**
• النسخ الاحتياطي: كل {config.BACKUP_INTERVAL_HOURS} ساعة
"""
        
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🔙 رجوع", callback_data="back_main")]
        ])
        
        await callback.message.edit_text(text, reply_markup=keyboard)
    
    async def run(self):
        """تشغيل البوت"""
        logger.info("🚀 بدء تشغيل البوت...")
        
        # تسجيل المعالجات
        self.setup_handlers()
        
        # بدء البوت
        await self.app.start()
        logger.info("✅ البوت يعمل الآن!")
        
        # إرسال رسالة للحساب الشخصي
        me = await self.app.get_me()
        await self.app.send_message(
            "me",
            f"🎮 **PUBG Analyzer Bot**\n\n"
            f"✅ البوت يعمل الآن!\n"
            f"📱 الحساب: {me.first_name}\n"
            f"🕐 الوقت: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            f"اكتب /start لفتح لوحة التحكم"
        )
        
        # الانتظار
        await idle()
        
        # إيقاف البوت
        await self.app.stop()
        logger.info("👋 تم إيقاف البوت")

async def main():
    """النقطة الرئيسية للبرنامج"""
    bot = PUBGAnalyzerBot()
    await bot.run()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("⚠️ تم إيقاف البوت بواسطة المستخدم")
    except Exception as e:
        logger.error(f"❌ خطأ: {e}", exc_info=True)