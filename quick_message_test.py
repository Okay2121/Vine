#!/usr/bin/env python
"""Quick test for message safety"""

message = """ADJUST USER BALANCE

Enter the Telegram ID or username of the user whose balance you want to adjust.

Examples:
- 1234567890 for Telegram ID
- @username
- username

Type cancel to go back."""

problematic_chars = ['*', '_', '`', '[', ']', '(', ')', '~', '>', '#', '+', '=', '|', '{', '}', '!']
found_issues = [char for char in problematic_chars if char in message]

print(f"Message length: {len(message)} characters")
print(f"Byte length: {len(message.encode('utf-8'))} bytes")

if found_issues:
    print(f"Found problematic characters: {found_issues}")
else:
    print("Message is safe from parsing errors")
    print("No problematic characters detected")