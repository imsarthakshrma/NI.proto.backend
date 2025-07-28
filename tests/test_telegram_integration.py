"""
Full Telegram Integration Test for DELA Bot
"""

import asyncio
import os
from dotenv import load_dotenv
from telegram import Bot
from src.integration.telegram.telegram_bot import DelaBot

load_dotenv()

async def test_full_telegram_integration():
    print("\n🔹 Starting Telegram Integration Test 🔹\n")

    bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
    test_chat_id = os.getenv("TELEGRAM_TEST_CHAT_ID")  # Optional for sending message

    if not bot_token:
        print("❌ TELEGRAM_BOT_TOKEN is missing in your .env file.")
        return

    # ✅ 1. Test Telegram API connection
    tg_bot = Bot(token=bot_token)
    me = await tg_bot.get_me()
    print(f"✅ Telegram API reachable. Bot username: @{me.username}")

    # ✅ 2. Test DELA Bot initialization
    dela_bot = DelaBot()
    print(f"✅ DELA Bot created. Observer Agent ID: {dela_bot.observer_agent.agent_id}")

    # ✅ 3. Test Observer Agent logic
    result = await dela_bot.observer_agent.process(
        {"message": "Integration test message"},
        {"message_type": "telegram", "sender": "test_user"}
    )
    print(f"✅ Observer Agent processed test message. Beliefs generated: {result.get('beliefs_count', 0)}")

    # ✅ 4. (Optional) Send a test message to a Telegram chat
    if test_chat_id:
        await tg_bot.send_message(chat_id=test_chat_id, text="🚀 DELA Bot integration test successful!")
        print(f"✅ Test message sent to chat ID {test_chat_id}")

    print("\n🎉 Telegram Integration Test Completed Successfully!\n")

if __name__ == "__main__":
    asyncio.run(test_full_telegram_integration())
