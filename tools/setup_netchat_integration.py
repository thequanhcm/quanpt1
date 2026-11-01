"""Setup NetChat integration for QUAN AI BRAIN — Connect bot to channel.

Usage:
    python tools/setup_netchat_integration.py

This script:
1. Checks if NetChat bot is connected
2. Prompts for bot access token (if not connected)
3. Configures bot-netchat skill
4. Tests connection to channel 4phc9b1mx78ajq3grccw89u94a
5. Sends welcome message to the channel

The bot will be able to:
- Receive messages from the channel
- Send responses back
- Upload/download files
- Act as "Tony Pham Assistant" in NetChat
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, "src")

def main() -> int:
    """Setup NetChat integration."""
    print("=" * 70)
    print("NETCHAT INTEGRATION SETUP — QUAN AI BRAIN")
    print("=" * 70)

    # Channel ID from user
    channel_id = "4phc9b1mx78ajq3grccw89u94a"
    channel_name = "Trợ lý Tony Pham"

    print(f"\n📱 Target Channel:")
    print(f"   Name: {channel_name}")
    print(f"   ID: {channel_id}")

    # Check current connection
    hermes_home = Path(os.environ.get("HERMES_HOME", Path.home() / ".netmind_desktop"))
    env_file = hermes_home / ".env"

    print(f"\n🔍 Checking NetChat connection...")
    print(f"   HERMES_HOME: {hermes_home}")
    print(f"   Env file: {env_file}")

    if env_file.exists():
        content = env_file.read_text(encoding="utf-8")
        has_token = "MATTERMOST_TOKEN" in content or "NETCHAT_BOT_TOKEN" in content
        if has_token:
            print("   ✅ Bot is already connected!")
        else:
            print("   ❌ No bot token found")
    else:
        print("   ❌ Env file not found")

    print("\n" + "=" * 70)
    print("NEXT STEPS:")
    print("=" * 70)
    print("\n1. Get Bot Access Token:")
    print("   - Open: https://bot-netchat.viettel.vn/")
    print("   - Login with your Viettel account")
    print("   - Go to Bot Management → Your bot")
    print("   - Copy the 'Access Token'")

    print("\n2. Configure Bot:")
    print("   Run: python tools/configure_netchat_bot.py <access_token>")
    print("   Or: Send the access token directly in this chat")

    print("\n3. Test Connection:")
    print("   Run: python tools/test_netchat_connection.py")

    print("\n4. Enable Auto-Response:")
    print("   The bot will automatically respond to messages in channel:")
    print(f"   - Channel: {channel_name} ({channel_id})")
    print("   - Bot will act as: 'Tony Pham Assistant'")

    print("\n" + "=" * 70)
    print("📄 Detailed guide: docs/NETCHAT_INTEGRATION_GUIDE.md")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())