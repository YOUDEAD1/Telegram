#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import logging
import time
import os
import sys
from bot import Bot
from keep_alive_http import keep_alive
import threading

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# تشغيل خادم الويب للحفاظ على البوت نشطاً 24/7
keep_alive()

def watchdog(bot_instance):
    """مراقبة حالة البوت وإعادة تشغيله إذا توقف"""
    restart_count = 0
    max_restarts = 5
    restart_interval = 60  # ثانية
    
    while True:
        try:
            # التحقق من حالة البوت كل دقيقة
            time.sleep(60)
            
            if not bot_instance.is_running:
                restart_count += 1
                logger.warning(f"تم اكتشاف توقف البوت. محاولة إعادة التشغيل {restart_count}/{max_restarts}...")
                
                # إعادة تشغيل البوت
                bot_instance.run()
                
                # إذا نجحت إعادة التشغيل، أعد تعيين العداد
                if bot_instance.is_running:
                    logger.info("تمت إعادة تشغيل البوت بنجاح")
                    restart_count = 0
                else:
                    logger.error("فشلت محاولة إعادة تشغيل البوت")
                    
                    # إذا وصلنا للحد الأقصى من المحاولات، انتظر فترة أطول
                    if restart_count >= max_restarts:
                        logger.error(f"تم الوصول للحد الأقصى من محاولات إعادة التشغيل ({max_restarts}). انتظار {restart_interval} ثانية...")
                        time.sleep(restart_interval)
                        restart_count = 0
                        restart_interval = min(restart_interval * 2, 3600)  # زيادة فترة الانتظار حتى ساعة كحد أقصى
        except Exception as e:
            logger.error(f"خطأ في مراقبة البوت: {str(e)}", exc_info=True)
            time.sleep(30)  # انتظار في حالة حدوث خطأ

def main():
    """Start the bot."""
    # إنشاء مجلد البيانات إذا لم يكن موجوداً
    os.makedirs('data', exist_ok=True)
    
    # Create and run the bot
    print("Starting Telegram Bot...")
    bot = Bot()
    
    # تشغيل مراقب البوت في خيط منفصل
    watchdog_thread = threading.Thread(target=watchdog, args=(bot,), daemon=True)
    watchdog_thread.start()
    
    # تشغيل البوت
    bot.run()
    
    # حلقة لا نهائية لمنع البرنامج من الإغلاق
    try:
        while True:
            time.sleep(60)  # انتظار دقيقة واحدة ثم التكرار
            
            # إذا توقف البوت، دع watchdog يتعامل مع إعادة التشغيل
            if not bot.is_running:
                logger.info("البوت متوقف، watchdog سيقوم بإعادة التشغيل...")
            else:
                logger.debug("البوت يعمل بشكل طبيعي")
    except KeyboardInterrupt:
        print("Bot stopped manually")

if __name__ == '__main__':
    main()
