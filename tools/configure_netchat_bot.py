"""Configure NetChat bot token for QUAN AI BRAIN.

Usage:
    python tools/configure_netchat_bot.py <access_token>

This script:
1. Validates the bot access token
2. Saves it to .env file in netMind Desktop
3. Tests the connection
4. Returns bot identity
"""
import os
import sys
from pathlib import Path

sys.path.insert(0, "src")


def main() -> int:
    """Configure bot token."""
    if len(sys.argv) < 2:
        print("❌ Missing access token")
        print("\nUsage: python tools/configure_netchat_bot.py <access_token>")
        print("\nGet your bot access token from:")
        print("  https://bot-netchat.viettel.vn/")
        print("  → Bot Management → Your bot → Access Token")
        return 1

    access_token = sys.argv[1]

    if not access_token or len(access_token) < 10:
        print("❌ Invalid access token (too short)")
        return 1

    print("=" * 70)
    print("CONFIGURING NETCHAT BOT")
    print("=" * 70)

    # Find HERMES_HOME
    hermes_home = Path(os.environ.get("HERMES_HOME", Path.home() / ".netmind_desktop"))
    env_file = hermes_home / ".env"

    print(f"\n📁 Target: {env_file}")

    # Create .env if not exists
    if not env_file.exists():
        print("   Creating .env file...")
        env_file.parent.mkdir(parents=True, exist_ok=True)
        env_file.write_text("# netMind Desktop environment variables\n", encoding="utf-8")

    # Read existing content
    content = env_file.read_text(encoding="utf-8")

    # Check if token already exists
    if "MATTERMOST_TOKEN" in content:
        print("   ⚠️  Token already exists. Overwriting...")
        lines = content.split("\n")
        new_lines = []
        for line in lines:
            if line.startswith("MATTERMOST_TOKEN="):
                new_lines.append(f"MATTERMOST_TOKEN={access_token}")
            else:
                new_lines.append(line)
        content = "\n".join(new_lines)
    else:
        # Add new token
        content = content.rstrip() + f"\nMATTERMOST_TOKEN={access_token}\n"

    # Save
    env_file.write_text(content, encoding="utf-8")
    print("   ✅ Token saved!")

    # Test connection
    print("\n🔍 Testing connection...")
    try:
        # Try to import and test
        from hermes_tools import terminal
        
        result = terminal("python -m bot_netchat whoami", timeout=30)
        if result.get("exit_code") == 0:
            print("   ✅ Bot connected successfully!")
            print(f"   Output: {result.get('output', '')[:200]}")
        else:
            print("   ⚠️  Connection test failed, but token is saved")
            print(f"   Error: {result.get('output', '')[:200]}")
    except Exception as e:
        print(f"   ⚠️  Could not test: {e}")

    print("\n" + "=" * 70)
    print("✅ CONFIGURATION COMPLETE")
    print("=" * 70)
    print("\nNext steps:")
    print("1. Test bot: python -m bot_netchat whoami")
    print("2. List channels: python -m bot_netchat list")
    print("3. Send test message: python -m bot_netchat send <channel_id> 'Hello' --to-channel")
    print("\nBot will now be able to:")
    print("  • Receive messages from NetChat channels")
    print("  • Send responses back")
    print("  • Upload/download files")
    print("  • Act as 'Tony Pham Assistant'")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())