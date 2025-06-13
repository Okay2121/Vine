#!/usr/bin/env python
"""
Nice Referral Link Formatter
----------------------------
Creates attractive and user-friendly referral links and messages
"""

def format_nice_referral_link(user_id, user_name=None):
    """
    Create a nice, branded referral link
    
    Args:
        user_id (str): Telegram user ID
        user_name (str): Optional username for personalization
        
    Returns:
        str: Formatted referral link
    """
    base_link = f"https://t.me/ThriveQuantbot?start=ref_{user_id}"
    return base_link

def create_shareable_message(user_name, referral_link):
    """
    Create a nice shareable message for referrals
    
    Args:
        user_name (str): Name of the person sharing
        referral_link (str): The referral link
        
    Returns:
        str: Formatted shareable message
    """
    message = f"""🚀 *Join me on THRIVE!*

I've been using this amazing crypto trading bot that's helping me grow my portfolio automatically.

💰 *What THRIVE does:*
• Trades live Solana memecoins 24/7
• Tracks all profits transparently  
• Lets you withdraw anytime with proof

🎁 *Special offer:* Use my link and we both get referral bonuses when you start trading!

👇 *Start here:*
{referral_link}

No subscriptions, no empty promises - just real trading results."""

    return message

def create_copy_paste_referral(user_id, first_name=None):
    """
    Create a copy-paste friendly referral message
    
    Args:
        user_id (str): Telegram user ID  
        first_name (str): Optional first name
        
    Returns:
        str: Copy-paste ready message
    """
    link = format_nice_referral_link(user_id)
    
    name_part = f" from {first_name}" if first_name else ""
    
    message = f"""🎯 THRIVE Crypto Bot Invitation{name_part}

Get started with automated Solana trading:
{link}

✅ Live trading results
✅ Transparent profit tracking  
✅ Withdraw anytime
✅ Referral bonuses for both of us

Join the future of crypto trading!"""

    return message

def get_social_share_links(referral_link, user_name=None):
    """
    Generate social media sharing links
    
    Args:
        referral_link (str): The referral link
        user_name (str): Optional username
        
    Returns:
        dict: Social media sharing URLs
    """
    import urllib.parse
    
    base_text = "🚀 Join me on THRIVE - the automated crypto trading bot! Get started:"
    encoded_text = urllib.parse.quote(f"{base_text} {referral_link}")
    
    return {
        'telegram': f"https://t.me/share/url?url={urllib.parse.quote(referral_link)}&text={urllib.parse.quote(base_text)}",
        'twitter': f"https://twitter.com/intent/tweet?text={encoded_text}",
        'whatsapp': f"https://wa.me/?text={encoded_text}",
        'copy_text': f"{base_text} {referral_link}"
    }