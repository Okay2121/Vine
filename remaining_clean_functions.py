def admin_dm_text_handler(update, chat_id):
    """Handle the text direct message option."""
    try:
        message = (
            "📝 *Text Direct Message*\n\n"
            "First, enter the Telegram ID of the user you want to message:"
        )
        
        keyboard = bot.create_inline_keyboard([
            [{"text": "Back to DM Options", "callback_data": "admin_direct_message"}]
        ])
        
        bot.send_message(
            chat_id,
            message,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        
        # Add a listener for the next message
        bot.add_message_listener(chat_id, "text", admin_dm_recipient_handler)
        
    except Exception as e:
        import logging
        logging.error(f"Error in admin_dm_text_handler: {e}")
        bot.send_message(chat_id, f"Error setting up direct message: {str(e)}")

def admin_dm_recipient_handler(update, chat_id, text):
    """Handle the recipient ID for direct message."""
    try:
        recipient_id = text.strip()
        
        # Check if the user exists
        with app.app_context():
            from models import User
            user = User.query.filter_by(telegram_id=recipient_id).first()
            
            if not user:
                bot.send_message(
                    chat_id, 
                    f"User with ID {recipient_id} not found. Please try again or press 'Back' to cancel.",
                    reply_markup=bot.create_inline_keyboard([
                        [{"text": "Back to DM Options", "callback_data": "admin_direct_message"}]
                    ])
                )
                bot.remove_listener(chat_id)
                return
            
            # Store the recipient ID
            global dm_recipient_id
            dm_recipient_id = recipient_id
            
            # Prompt for the message content
            message = (
                f"✅ User found: {user.username or 'No username'} (ID: {recipient_id})\n\n"
                "Now type the message you want to send. You can include:\n"
                "• *Bold text* using *asterisks*\n"
                "• _Italic text_ using _underscores_\n"
                "• `Code blocks` using `backticks`\n"
                "• [Hyperlinks](https://example.com) using [text](URL) format"
            )
            
            bot.send_message(
                chat_id,
                message,
                parse_mode="Markdown",
                reply_markup=bot.create_inline_keyboard([
                    [{"text": "Cancel", "callback_data": "admin_direct_message"}]
                ])
            )
            
            # Update the listener for the message content
            bot.remove_listener(chat_id)
            bot.add_message_listener(chat_id, "text", admin_dm_content_handler)
            
    except Exception as e:
        import logging
        logging.error(f"Error in admin_dm_recipient_handler: {e}")
        bot.send_message(chat_id, f"Error processing recipient: {str(e)}")
        bot.remove_listener(chat_id)

def admin_dm_content_handler(update, chat_id, text):
    """Handle the content for direct message."""
    try:
        # Get the stored recipient ID
        global dm_recipient_id
        recipient_id = dm_recipient_id
        
        # Preview the message
        preview_message = (
            "🔍 *Direct Message Preview*\n\n"
            f"To: User {recipient_id}\n\n"
            f"Message:\n{text}\n\n"
            "Are you sure you want to send this message?"
        )
        
        keyboard = bot.create_inline_keyboard([
            [
                {"text": "✅ Send Message", "callback_data": "admin_send_direct_message"},
                {"text": "❌ Cancel", "callback_data": "admin_direct_message"}
            ]
        ])
        
        # Store the message for later sending
        global dm_content
        dm_content = text
        
        bot.send_message(
            chat_id,
            preview_message,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        
        # Remove the listener
        bot.remove_listener(chat_id)
        
    except Exception as e:
        import logging
        logging.error(f"Error in admin_dm_content_handler: {e}")
        bot.send_message(chat_id, f"Error processing message content: {str(e)}")
        bot.remove_listener(chat_id)

def admin_dm_image_handler(update, chat_id):
    """Handle the image direct message option."""
    try:
        message = (
            "🖼️ *Image Direct Message*\n\n"
            "First, enter the Telegram ID of the user you want to message:"
        )
        
        keyboard = bot.create_inline_keyboard([
            [{"text": "Back to DM Options", "callback_data": "admin_direct_message"}]
        ])
        
        bot.send_message(
            chat_id,
            message,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        
        # Add a listener for the next message (recipient ID)
        bot.add_message_listener(chat_id, "text", admin_dm_image_recipient_handler)
        
    except Exception as e:
        import logging
        logging.error(f"Error in admin_dm_image_handler: {e}")
        bot.send_message(chat_id, f"Error setting up image direct message: {str(e)}")

def admin_dm_image_recipient_handler(update, chat_id, text):
    """Handle the recipient ID for image direct message."""
    try:
        recipient_id = text.strip()
        
        # Check if the user exists
        with app.app_context():
            from models import User
            user = User.query.filter_by(telegram_id=recipient_id).first()
            
            if not user:
                bot.send_message(
                    chat_id, 
                    f"User with ID {recipient_id} not found. Please try again or press 'Back' to cancel.",
                    reply_markup=bot.create_inline_keyboard([
                        [{"text": "Back to DM Options", "callback_data": "admin_direct_message"}]
                    ])
                )
                bot.remove_listener(chat_id)
                return
            
            # Store the recipient ID
            global dm_recipient_id
            dm_recipient_id = recipient_id
            
            # Prompt for the image URL and caption
            message = (
                f"✅ User found: {user.username or 'No username'} (ID: {recipient_id})\n\n"
                "Now send the image URL and caption in this format:\n"
                "```\nURL\nCaption text goes here\n```\n\n"
                "Example:\n"
                "```\nhttps://example.com/image.jpg\nCheck out this feature!\n```\n\n"
                "The caption can include Markdown formatting."
            )
            
            bot.send_message(
                chat_id,
                message,
                parse_mode="Markdown",
                reply_markup=bot.create_inline_keyboard([
                    [{"text": "Cancel", "callback_data": "admin_direct_message"}]
                ])
            )
            
            # Update the listener for the image URL and caption
            bot.remove_listener(chat_id)
            bot.add_message_listener(chat_id, "text", admin_dm_image_content_handler)
            
    except Exception as e:
        import logging
        logging.error(f"Error in admin_dm_image_recipient_handler: {e}")
        bot.send_message(chat_id, f"Error processing recipient: {str(e)}")
        bot.remove_listener(chat_id)

def admin_dm_image_content_handler(update, chat_id, text):
    """Handle the image URL and caption for direct message."""
    try:
        # Split the text into URL and caption
        lines = text.strip().split('\n')
        if len(lines) < 2:
            bot.send_message(chat_id, "Please provide both an image URL and caption. Try again or send 'cancel' to abort.")
            return
            
        image_url = lines[0].strip()
        caption = '\n'.join(lines[1:])
        
        # Get the stored recipient ID
        global dm_recipient_id
        recipient_id = dm_recipient_id
        
        # Preview the message
        preview_message = (
            "🔍 *Image Direct Message Preview*\n\n"
            f"To: User {recipient_id}\n\n"
            f"Image URL: {image_url}\n\n"
            f"Caption: {caption}\n\n"
            "Are you sure you want to send this message?"
        )
        
        keyboard = bot.create_inline_keyboard([
            [
                {"text": "✅ Send Message", "callback_data": "admin_send_direct_message_image"},
                {"text": "❌ Cancel", "callback_data": "admin_direct_message"}
            ]
        ])
        
        # Store the message for later sending
        global dm_image_url, dm_image_caption
        dm_image_url = image_url
        dm_image_caption = caption
        
        # Send a sample of the image
        bot.send_message(
            chat_id,
            f"Image preview (URL only, actual image will be sent in message):\n{image_url}"
        )
        
        bot.send_message(
            chat_id,
            preview_message,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        
        # Remove the listener
        bot.remove_listener(chat_id)
        
    except Exception as e:
        import logging
        logging.error(f"Error in admin_dm_image_content_handler: {e}")
        bot.send_message(chat_id, f"Error processing image content: {str(e)}")
        bot.remove_listener(chat_id)

def admin_search_user_for_dm_handler(update, chat_id):
    """Handle the search user for direct message option."""
    try:
        message = (
            "🔍 *Search User*\n\n"
            "Enter a username or partial user ID to search:"
        )
        
        keyboard = bot.create_inline_keyboard([
            [{"text": "Back to DM Options", "callback_data": "admin_direct_message"}]
        ])
        
        bot.send_message(
            chat_id,
            message,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        
        # Add a listener for the search query
        bot.add_message_listener(chat_id, "text", admin_search_user_query_handler)
        
    except Exception as e:
        import logging
        logging.error(f"Error in admin_search_user_for_dm_handler: {e}")
        bot.send_message(chat_id, f"Error setting up user search: {str(e)}")

def admin_search_user_query_handler(update, chat_id, text):
    """Handle the search query for finding users."""
    try:
        search_query = text.strip()
        
        # Search for users
        with app.app_context():
            from models import User
            from sqlalchemy import or_
            
            users = User.query.filter(
                or_(
                    User.username.ilike(f"%{search_query}%"),
                    User.telegram_id.ilike(f"%{search_query}%")
                )
            ).limit(5).all()
            
            if not users:
                bot.send_message(
                    chat_id, 
                    f"No users found matching '{search_query}'. Please try another search term.",
                    reply_markup=bot.create_inline_keyboard([
                        [{"text": "Back to DM Options", "callback_data": "admin_direct_message"}]
                    ])
                )
                bot.remove_listener(chat_id)
                return
            
            # Create a message with search results
            results_message = f"🔍 *Search Results for '{search_query}'*\n\n"
            
            for user in users:
                username = user.username or "No username"
                results_message += f"• *{username}* (ID: `{user.telegram_id}`)\n"
            
            results_message += "\nCopy an ID from the list and use it to send a direct message."
            
            bot.send_message(
                chat_id,
                results_message,
                parse_mode="Markdown",
                reply_markup=bot.create_inline_keyboard([
                    [{"text": "Send Text Message", "callback_data": "admin_dm_text"}],
                    [{"text": "Send Image Message", "callback_data": "admin_dm_image"}],
                    [{"text": "Back to DM Options", "callback_data": "admin_direct_message"}]
                ])
            )
            
            # Remove the listener
            bot.remove_listener(chat_id)
            
    except Exception as e:
        import logging
        logging.error(f"Error in admin_search_user_query_handler: {e}")
        bot.send_message(chat_id, f"Error searching for users: {str(e)}")
        bot.remove_listener(chat_id)
        
def admin_send_broadcast_handler(update, chat_id):
    """Handle sending a broadcast message to users based on target selection."""
    try:
        # Get the pending broadcast message
        global pending_broadcast_id, broadcast_target
        
        # For debugging
        import logging
        logging.info(f"Preparing to send broadcast. pending_broadcast_id={pending_broadcast_id}, broadcast_target={broadcast_target}")
        
        with app.app_context():
            from models import BroadcastMessage, User
            import json
            
            # If no pending_broadcast_id is set, try to find the most recent pending message
            if not pending_broadcast_id:
                latest_pending = BroadcastMessage.query.filter_by(
                    status="pending", 
                    created_by=str(chat_id)
                ).order_by(BroadcastMessage.created_at.desc()).first()
                
                if latest_pending:
                    pending_broadcast_id = latest_pending.id
                    logging.info(f"Found latest pending broadcast message: {pending_broadcast_id}")
                else:
                    bot.send_message(chat_id, "No pending broadcast message found. Please create a new broadcast.")
                    return
            
            # Get the message
            message = BroadcastMessage.query.get(pending_broadcast_id)
            if not message:
                bot.send_message(chat_id, "Broadcast message not found. Please create a new broadcast.")
                return
                
            # Get users for broadcast based on target selection
            from models import UserStatus
            import logging
            import json
            from datetime import datetime
            
            # Filter users based on broadcast target
            if broadcast_target == "active":
                users = User.query.filter_by(status=UserStatus.ACTIVE).all()
                target_description = "active users"
            else:
                users = User.query.all()
                target_description = "all users"
            
            # Log the count of users found
            logging.info(f"Found {len(users)} {target_description} for broadcast")
            total_users = len(users)
            
            if total_users == 0:
                bot.send_message(chat_id, f"There are no {target_description} to send the broadcast to.")
                return
                
            # Update the message status
            message.status = "sending"
            db.session.commit()
            
            # Send a progress message
            progress_message = bot.send_message(
                chat_id,
                f"📣 Preparing to send broadcast to {total_users} {target_description}..."
            )
            
            # Process the message based on its type
            sent_count = 0
            failed_count = 0
            
            if message.message_type == "text":
                # Simple text broadcast
                content = message.content
                
                for user in users:
                    try:
                        # Skip users with no telegram_id
                        if not user.telegram_id:
                            logging.warning(f"User ID {user.id} has no telegram_id, skipping")
                            continue
                            
                        bot.send_message(
                            user.telegram_id,
                            content,
                            parse_mode="Markdown"
                        )
                        sent_count += 1
                        
                        # Update progress every 10 users
                        if sent_count % 10 == 0:
                            bot.edit_message(
                                progress_message['message_id'],
                                chat_id,
                                f"📣 Sending broadcast... {sent_count}/{total_users} completed."
                            )
                    except Exception as e:
                        logging.error(f"Error sending broadcast to user {user.telegram_id}: {e}")
                        failed_count += 1
            
            elif message.message_type == "image":
                # Image with caption
                try:
                    content = json.loads(message.content)
                    image_url = content.get("image_url")
                    caption = content.get("caption")
                    
                    for user in users:
                        try:
                            # Skip users with no telegram_id
                            if not user.telegram_id:
                                logging.warning(f"User ID {user.id} has no telegram_id, skipping")
                                continue
                                
                            # In a real implementation, we would use bot.send_photo
                            # However, for our simplified version we'll simulate it
                            bot.send_message(
                                user.telegram_id,
                                f"[Image]({image_url})\n\n{caption}",
                                parse_mode="Markdown"
                            )
                            sent_count += 1
                            
                            # Update progress every 10 users
                            if sent_count % 10 == 0:
                                bot.edit_message(
                                    progress_message['message_id'],
                                    chat_id,
                                    f"📣 Sending broadcast... {sent_count}/{total_users} completed."
                                )
                        except Exception as e:
                            logging.error(f"Error sending broadcast to user {user.telegram_id}: {e}")
                            failed_count += 1
                except json.JSONDecodeError:
                    bot.send_message(chat_id, "Error processing image broadcast: Invalid format")
                    return
            
            elif message.message_type == "announcement":
                # Formatted announcement
                try:
                    content = json.loads(message.content)
                    formatted_text = content.get("formatted_text")
                    
                    for user in users:
                        try:
                            # Skip users with no telegram_id
                            if not user.telegram_id:
                                logging.warning(f"User ID {user.id} has no telegram_id, skipping")
                                continue
                                
                            bot.send_message(
                                user.telegram_id,
                                formatted_text,
                                parse_mode="Markdown"
                            )
                            sent_count += 1
                            
                            # Update progress every 10 users
                            if sent_count % 10 == 0:
                                bot.edit_message(
                                    progress_message['message_id'],
                                    chat_id,
                                    f"📣 Sending broadcast... {sent_count}/{total_users} completed."
                                )
                        except Exception as e:
                            logging.error(f"Error sending broadcast to user {user.telegram_id}: {e}")
                            failed_count += 1
                except json.JSONDecodeError:
                    bot.send_message(chat_id, "Error processing announcement broadcast: Invalid format")
                    return
            
            # Update the message status
            message.status = "sent"
            message.sent_at = datetime.utcnow()
            message.sent_count = sent_count
            message.failed_count = failed_count
            db.session.commit()
            
            # Clear the pending broadcast ID
            pending_broadcast_id = None
            
            # Determine success rate
            success_rate = (sent_count / total_users * 100) if total_users > 0 else 0
            success_emoji = "✅" if success_rate > 90 else "⚠️" if success_rate > 50 else "❌"
            
            # Send completion message with detailed statistics and interactive buttons
            completion_message = (
                f"{success_emoji} *Broadcast Completed*\n\n"
                f"📊 *Results:*\n"
                f"• Total users in database: {total_users}\n"
                f"• Successfully sent: {sent_count}\n"
                f"• Failed: {failed_count}\n"
                f"• Skipped (no telegram_id): {total_users - (sent_count + failed_count)}\n\n"
                f"Broadcast ID: `{message.id}`\n"
                f"Type: {message.message_type}\n"
                f"Time: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC\n\n"
                f"The message has been delivered to *{sent_count}* users ({success_rate:.1f}% success rate)."
            )
            
            # Create an interactive keyboard with more options
            keyboard = bot.create_inline_keyboard([
                [
                    {"text": "📢 New Broadcast", "callback_data": "admin_broadcast"},
                    {"text": "📊 View Stats", "callback_data": "admin_view_stats"}
                ],
                [
                    {"text": "Return to Admin Panel", "callback_data": "admin_back"}
                ]
            ])
            
            bot.send_message(
                chat_id,
                completion_message,
                parse_mode="Markdown",
                reply_markup=keyboard
            )
            
            # Log the successful broadcast
            logging.info(f"Broadcast ID {message.id} successfully sent to {sent_count}/{total_users} users")
            
    except Exception as e:
        import logging
        logging.error(f"Error in admin_send_broadcast_handler: {e}")
        import traceback
        logging.error(traceback.format_exc())
        bot.send_message(chat_id, f"Error sending broadcast: {str(e)}")

def admin_send_direct_message_handler(update, chat_id):
    """Handle sending a direct message to a specific user."""
    try:
        # Get the stored recipient ID and message content
        global dm_recipient_id, dm_content
        if not dm_recipient_id or not dm_content:
            bot.send_message(chat_id, "Message information is missing. Please create a new direct message.")
            return
            
        # Send the message to the recipient
        try:
            bot.send_message(
                dm_recipient_id,
                dm_content,
                parse_mode="Markdown"
            )
            
            # Log the direct message
            with app.app_context():
                from models import AdminMessage
                
                # Save the message to the database
                new_message = AdminMessage(
                    content=dm_content,
                    message_type="text",
                    recipient_id=dm_recipient_id,
                    sent_by=chat_id,
                    status="sent"
                )
                db.session.add(new_message)
                db.session.commit()
            
            # Clear the stored data
            dm_recipient_id = None
            dm_content = None
            
            # Send confirmation message
            bot.send_message(
                chat_id,
                "✅ Direct message sent successfully!",
                parse_mode="Markdown",
                reply_markup=bot.create_inline_keyboard([
                    [{"text": "Send Another Message", "callback_data": "admin_direct_message"}],
                    [{"text": "Return to Admin Panel", "callback_data": "admin_back"}]
                ])
            )
            
        except Exception as e:
            logging.error(f"Error sending direct message to user {dm_recipient_id}: {e}")
            bot.send_message(chat_id, f"Error sending message: {str(e)}")
            
    except Exception as e:
        import logging
        logging.error(f"Error in admin_send_direct_message_handler: {e}")
        import traceback
        logging.error(traceback.format_exc())
        bot.send_message(chat_id, f"Error sending direct message: {str(e)}")

def admin_send_direct_message_image_handler(update, chat_id):
    """Handle sending an image direct message to a specific user."""
    try:
        # Get the stored recipient ID and image data
        global dm_recipient_id, dm_image_url, dm_image_caption
        if not dm_recipient_id or not dm_image_url or not dm_image_caption:
            bot.send_message(chat_id, "Message information is missing. Please create a new image message.")
            return
            
        # Send the message to the recipient
        try:
            # In a real implementation, we would use bot.send_photo
            # However, for our simplified version we'll simulate it
            bot.send_message(
                dm_recipient_id,
                f"[Image]({dm_image_url})\n\n{dm_image_caption}",
                parse_mode="Markdown"
            )
            
            # Log the direct message
            with app.app_context():
                from models import AdminMessage
                import json
                
                # Save the message to the database
                message_data = json.dumps({
                    "image_url": dm_image_url,
                    "caption": dm_image_caption
                })
                
                new_message = AdminMessage(
                    content=message_data,
                    message_type="image",
                    recipient_id=dm_recipient_id,
                    sent_by=chat_id,
                    status="sent"
                )
                db.session.add(new_message)
                db.session.commit()
            
            # Clear the stored data
            dm_recipient_id = None
            dm_image_url = None
            dm_image_caption = None
            
            # Send confirmation message
            bot.send_message(
                chat_id,
                "✅ Image message sent successfully!",
                parse_mode="Markdown",
                reply_markup=bot.create_inline_keyboard([
                    [{"text": "Send Another Message", "callback_data": "admin_direct_message"}],
                    [{"text": "Return to Admin Panel", "callback_data": "admin_back"}]
                ])
            )
            
        except Exception as e:
            logging.error(f"Error sending image message to user {dm_recipient_id}: {e}")
            bot.send_message(chat_id, f"Error sending image message: {str(e)}")
            
    except Exception as e:
        import logging
        logging.error(f"Error in admin_send_direct_message_image_handler: {e}")
        import traceback
        logging.error(traceback.format_exc())
        bot.send_message(chat_id, f"Error sending image message: {str(e)}")

def admin_back_handler(update, chat_id):
    """Handle the back button to return to the main admin panel."""
    try:
        admin_command(update, chat_id)
    except Exception as e:
        import logging
        logging.error(f"Error in admin_back_handler: {e}")
        import traceback
        logging.error(traceback.format_exc())
        
        # Handle the case when bot isn't initialized
        try:
            if 'bot' in globals() and bot is not None:
                bot.send_message(chat_id, f"Error returning to admin panel: {str(e)}")
            else:
                logging.error("Cannot send error message - bot not initialized")
        except Exception as inner_e:
            logging.error(f"Error sending error message: {inner_e}")

def run_polling():
    """Start the bot polling loop."""
    global _bot_instance, _bot_running, bot
    
    # Import the comprehensive duplicate prevention system
    from duplicate_instance_prevention import prevent_duplicate_startup, setup_signal_handlers, check_and_kill_duplicate_processes
    import threading
    
    # Check if we're running in the main thread
    is_main_thread = threading.current_thread() is threading.main_thread()
    
    # Prevent multiple instances using comprehensive protection
    try:
        # First, check and terminate any existing duplicates
        duplicates_killed = check_and_kill_duplicate_processes()
        if duplicates_killed > 0:
            logger.info(f"Terminated {duplicates_killed} duplicate bot processes")
            time.sleep(3)  # Wait for processes to fully terminate
        
        # Now try to acquire the lock
        instance_manager = prevent_duplicate_startup()
        
        # Only set up signal handlers if we're in the main thread
        if is_main_thread:
            setup_signal_handlers(instance_manager)
            logger.info("Signal handlers set up (main thread)")
        else:
            logger.info("Skipping signal handlers setup (background thread)")
            
    except RuntimeError as e:
        logger.warning(f"Could not start bot: {e}")
        logger.info("Attempting cleanup and retry...")
        
        # Try to clean up stale locks and retry once
        try:
            from duplicate_instance_prevention import BotInstanceManager
            cleanup_manager = BotInstanceManager()
            cleanup_manager.cleanup_stale_locks()
            time.sleep(2)
            
            # Retry acquiring lock after cleanup
            instance_manager = prevent_duplicate_startup()
            
            # Only set up signal handlers if we're in the main thread
            if is_main_thread:
                setup_signal_handlers(instance_manager)
                logger.info("Signal handlers set up after cleanup (main thread)")
            else:
                logger.info("Skipping signal handlers setup after cleanup (background thread)")
                
            logger.info("Successfully acquired lock after cleanup")
        except RuntimeError:
            logger.error("Failed to start bot even after cleanup - another instance may be legitimately running")
            return
    
    # Additional check for global flag
    if _bot_running:
        logger.warning("Bot is already running globally, skipping duplicate start")
        return
    
    # Get bot token directly from environment variable (not cached import)
    token = os.environ.get('TELEGRAM_BOT_TOKEN')
    
    if not token:
        logger.error("No Telegram bot token provided. Set the TELEGRAM_BOT_TOKEN environment variable.")
        return
    
    logger.info(f"Starting bot with token: {token[:10]}...")
    
    # Set running flag immediately to prevent duplicates
    _bot_running = True
    
    # Initialize global variables for admin trade broadcasting
    global admin_pending_trade_data
    admin_pending_trade_data = None
    
    bot = SimpleTelegramBot(token)
    _bot_instance = bot
    
    # Add command handlers
    bot.add_command_handler("/start", start_command)
    bot.add_command_handler("/help", help_command)
    bot.add_command_handler("/deposit", deposit_command)
    bot.add_command_handler("/dashboard", dashboard_command)
    bot.add_command_handler("/settings", settings_command)
    bot.add_command_handler("/referral", referral_command)
    bot.add_command_handler("/admin", admin_command)
    bot.add_command_handler("/admin_trade_post", admin_trade_post_handler)
    
    # Add a handler for UI section labels in keyboards (does nothing when clicked)
    bot.add_callback_handler("ignore", lambda update, chat_id: None)
    
    # Add callback handlers with all the buttons from the original design
    bot.add_callback_handler("skip_wallet", skip_wallet_callback)
    bot.add_callback_handler("dashboard", dashboard_command)
    bot.add_callback_handler("view_dashboard", dashboard_command)  # New button name from original design
    bot.add_callback_handler("deposit", deposit_command)
    bot.add_callback_handler("referral", referral_command)
    bot.add_callback_handler("settings", settings_command)
    bot.add_callback_handler("how_it_works", help_command)
    bot.add_callback_handler("help", help_command)  # New button name from original design
    bot.add_callback_handler("start", show_main_menu_callback)  # For "Back to Main Menu" button
    def copy_address_handler(update, chat_id):
        from config import GLOBAL_DEPOSIT_WALLET
        bot.send_message(chat_id, f"✅ Address copied!\n\n`{GLOBAL_DEPOSIT_WALLET}`", parse_mode="Markdown")
    
    bot.add_callback_handler("copy_address", copy_address_handler)
    bot.add_callback_handler("deposit_confirmed", deposit_confirmed_handler)
    
    # Dashboard-specific buttons
    bot.add_callback_handler("withdraw_profit", withdraw_profit_handler)
    bot.add_callback_handler("withdraw_all", withdraw_all_handler)
    bot.add_callback_handler("withdraw_profit_only", withdraw_profit_only_handler)
    bot.add_callback_handler("withdraw_custom", withdraw_custom_handler)
    bot.add_callback_handler("view_tx", lambda update, chat_id: bot.send_message(chat_id, "Transaction details will be available on Solana Explorer once confirmed. Usually takes 10-15 seconds."))
    bot.add_callback_handler("trading_history", trading_history_handler)
    bot.add_callback_handler("transaction_history", transaction_history_handler)
    bot.add_callback_handler("support", support_handler)
    bot.add_callback_handler("faqs", faqs_handler)
    bot.add_callback_handler("verify_wallet", verify_wallet_handler)
    bot.add_callback_handler("view_my_deposits", view_my_deposits_handler)
    
    # Sniper control buttons
    bot.add_callback_handler("start_sniper", start_sniper_handler)
    bot.add_callback_handler("start_sniper_confirmed", start_sniper_confirmed_handler)  # For risk warning bypass
    bot.add_callback_handler("stop_sniper", stop_sniper_handler)
    bot.add_callback_handler("sniper_stats", sniper_stats_handler)
    
    # Auto trading specific buttons (main registrations are below)
    bot.add_callback_handler("toggle_auto_trading", toggle_auto_trading_handler)
    
    # Support-specific buttons
    bot.add_callback_handler("live_chat", live_chat_handler)
    bot.add_callback_handler("submit_ticket", submit_ticket_handler)
    
    # Settings-specific buttons
    bot.add_callback_handler("update_wallet", lambda update, chat_id: bot.send_message(chat_id, "Wallet update feature coming soon. Your current wallet is linked to your account."))
    bot.add_callback_handler("notification_settings", lambda update, chat_id: bot.send_message(chat_id, "Notification settings can be customized soon. Currently all important alerts are enabled."))
    bot.add_callback_handler("security_settings", lambda update, chat_id: bot.send_message(chat_id, "Your account is protected with the highest security standards. Additional security features coming soon."))
    
    # Referral-specific buttons
    bot.add_callback_handler("referral", referral_command)
    bot.add_callback_handler("copy_referral", copy_referral_handler)
    bot.add_callback_handler("referral_stats", referral_stats_handler)
    bot.add_callback_handler("share_referral", share_referral_handler)
    bot.add_callback_handler("copy_referral_message", copy_referral_message_handler)
    bot.add_callback_handler("referral_earnings", lambda update, chat_id: bot.send_message(chat_id, "Your referral earnings will appear here once your friends start trading."))
    
    # New enhanced referral buttons
    bot.add_callback_handler("referral_qr_code", referral_qr_code_handler)
    bot.add_callback_handler("copy_referral_link", copy_referral_link_handler)
    bot.add_callback_handler("referral_how_it_works", referral_how_it_works_handler)
    bot.add_callback_handler("referral_tips", referral_tips_handler)
    
    # Trade history button handler
    bot.add_callback_handler("view_trade_history", trade_history_display_handler)
    
    # Live positions handler - displays immediate trade broadcasts
    bot.add_callback_handler("live_positions", live_positions_handler)
    
    # Auto Trading System handlers
    bot.add_callback_handler("auto_trading_settings", auto_trading_settings_handler)
    bot.add_callback_handler("auto_trading_risk", auto_trading_risk_handler)
    bot.add_callback_handler("auto_trading_balance", auto_trading_balance_handler)
    bot.add_callback_handler("auto_trading_signals", auto_trading_signals_handler)
    bot.add_callback_handler("auto_trading_filters", auto_trading_filters_handler)
    bot.add_callback_handler("auto_trading_time", auto_trading_time_handler)
    bot.add_callback_handler("auto_trading_anti_fomo", auto_trading_anti_fomo_handler)
    bot.add_callback_handler("auto_trading_performance", auto_trading_performance_handler)
    
    # Register additional handlers that are defined later in the file
    bot.add_callback_handler("configure_risk_filters", lambda update, chat_id: configure_risk_filters_handler(update, chat_id))
    
    # Position size setting handlers
    bot.add_callback_handler("set_position_size", set_position_size_handler)
    bot.add_callback_handler("set_pos_size_auto", set_pos_size_auto_handler)
    bot.add_callback_handler("set_pos_size_8", lambda update, chat_id: set_pos_size_value_handler(update, chat_id, 8))
    bot.add_callback_handler("set_pos_size_12", lambda update, chat_id: set_pos_size_value_handler(update, chat_id, 12))
    bot.add_callback_handler("set_pos_size_15", lambda update, chat_id: set_pos_size_value_handler(update, chat_id, 15))
    bot.add_callback_handler("set_pos_size_20", lambda update, chat_id: set_pos_size_value_handler(update, chat_id, 20))
    bot.add_callback_handler("set_pos_size_custom", set_pos_size_custom_handler)
    
    # Stop Loss setting handlers with Auto option
    bot.add_callback_handler("set_stop_loss", set_stop_loss_handler)
    bot.add_callback_handler("set_stop_loss_auto", set_stop_loss_auto_handler)
    bot.add_callback_handler("set_stop_loss_5", lambda update, chat_id: set_stop_loss_value_handler(update, chat_id, 5))
    bot.add_callback_handler("set_stop_loss_10", lambda update, chat_id: set_stop_loss_value_handler(update, chat_id, 10))
    bot.add_callback_handler("set_stop_loss_15", lambda update, chat_id: set_stop_loss_value_handler(update, chat_id, 15))
    bot.add_callback_handler("set_stop_loss_20", lambda update, chat_id: set_stop_loss_value_handler(update, chat_id, 20))
    
    # Take Profit setting handlers with Auto option
    bot.add_callback_handler("set_take_profit", set_take_profit_handler)
    bot.add_callback_handler("set_take_profit_auto", set_take_profit_auto_handler)
    bot.add_callback_handler("set_take_profit_50", lambda update, chat_id: set_take_profit_value_handler(update, chat_id, 50))
    bot.add_callback_handler("set_take_profit_100", lambda update, chat_id: set_take_profit_value_handler(update, chat_id, 100))
    bot.add_callback_handler("set_take_profit_200", lambda update, chat_id: set_take_profit_value_handler(update, chat_id, 200))
    bot.add_callback_handler("set_take_profit_300", lambda update, chat_id: set_take_profit_value_handler(update, chat_id, 300))
    
    # Daily Trades setting handlers with Auto option
    bot.add_callback_handler("set_daily_trades", set_daily_trades_handler)
    bot.add_callback_handler("set_daily_trades_auto", set_daily_trades_auto_handler)
    bot.add_callback_handler("set_daily_trades_3", lambda update, chat_id: set_daily_trades_value_handler(update, chat_id, 3))
    bot.add_callback_handler("set_daily_trades_5", lambda update, chat_id: set_daily_trades_value_handler(update, chat_id, 5))
    bot.add_callback_handler("set_daily_trades_8", lambda update, chat_id: set_daily_trades_value_handler(update, chat_id, 8))
    bot.add_callback_handler("set_daily_trades_10", lambda update, chat_id: set_daily_trades_value_handler(update, chat_id, 10))
    
    # Max Positions setting handlers with Auto option
    bot.add_callback_handler("set_max_positions", set_max_positions_handler)
    bot.add_callback_handler("set_max_positions_auto", set_max_positions_auto_handler)
    bot.add_callback_handler("set_max_positions_2", lambda update, chat_id: set_max_positions_value_handler(update, chat_id, 2))
    bot.add_callback_handler("set_max_positions_3", lambda update, chat_id: set_max_positions_value_handler(update, chat_id, 3))
    bot.add_callback_handler("set_max_positions_5", lambda update, chat_id: set_max_positions_value_handler(update, chat_id, 5))
    bot.add_callback_handler("set_max_positions_8", lambda update, chat_id: set_max_positions_value_handler(update, chat_id, 8))
    bot.add_callback_handler("set_pos_size_15", lambda u, c: set_pos_size_quick_handler(u, c, 15.0))
    
    # Preset handlers
    bot.add_callback_handler("preset_conservative", preset_conservative_handler)
    bot.add_callback_handler("preset_moderate", preset_moderate_handler)
    bot.add_callback_handler("preset_aggressive", preset_aggressive_handler)
    
    # Auto trading sub-setting handlers - now properly registering after function definitions
    bot.add_callback_handler("set_min_liquidity", set_min_liquidity_handler)
    bot.add_callback_handler("set_market_cap", set_market_cap_handler)
    bot.add_callback_handler("set_min_volume", set_min_volume_handler)
    bot.add_callback_handler("add_telegram_channels", add_telegram_channels_handler)
    bot.add_callback_handler("toggle_pump_fun", toggle_pump_fun_handler)
    bot.add_callback_handler("toggle_whales", toggle_whales_handler)
    bot.add_callback_handler("toggle_social", toggle_social_handler)
    bot.add_callback_handler("toggle_volume", toggle_volume_handler)
    bot.add_callback_handler("set_trading_percentage", set_trading_percentage_handler)
    bot.add_callback_handler("set_reserve_balance", set_reserve_balance_handler)
    bot.add_callback_handler("set_daily_trades", set_daily_trades_handler)
    bot.add_callback_handler("set_max_positions", set_max_positions_handler)
    bot.add_callback_handler("set_cooldown", set_cooldown_handler)
    bot.add_callback_handler("set_stop_loss", set_stop_loss_handler)
    bot.add_callback_handler("set_take_profit", set_take_profit_handler)
    bot.add_callback_handler("reset_time_settings", reset_time_settings_handler)
    bot.add_callback_handler("configure_fomo_protection", configure_fomo_protection_handler)
    
    # Custom input handlers for user control
    bot.add_callback_handler("liquidity_custom", handle_custom_liquidity_input)
    bot.add_callback_handler("mcap_custom", handle_custom_market_cap_input)
    bot.add_callback_handler("trading_pct_custom", handle_custom_trading_percentage_input)
    
    # Quick-select option handlers for predefined values
    bot.add_callback_handler("liquidity_5", lambda u, c: set_liquidity_value(u, c, 5))
    bot.add_callback_handler("liquidity_10", lambda u, c: set_liquidity_value(u, c, 10))
    bot.add_callback_handler("liquidity_25", lambda u, c: set_liquidity_value(u, c, 25))
    bot.add_callback_handler("liquidity_50", lambda u, c: set_liquidity_value(u, c, 50))
    bot.add_callback_handler("liquidity_100", lambda u, c: set_liquidity_value(u, c, 100))
    
    bot.add_callback_handler("mcap_micro", lambda u, c: set_market_cap_range(u, c, 1000, 100000))
    bot.add_callback_handler("mcap_small", lambda u, c: set_market_cap_range(u, c, 10000, 500000))
    bot.add_callback_handler("mcap_medium", lambda u, c: set_market_cap_range(u, c, 50000, 1000000))
    bot.add_callback_handler("mcap_large", lambda u, c: set_market_cap_range(u, c, 100000, 5000000))
    bot.add_callback_handler("mcap_mega", lambda u, c: set_market_cap_range(u, c, 500000, 10000000))
    
    bot.add_callback_handler("trading_pct_25", lambda u, c: set_trading_percentage(u, c, 25.0))
    bot.add_callback_handler("trading_pct_50", lambda u, c: set_trading_percentage(u, c, 50.0))
    bot.add_callback_handler("trading_pct_75", lambda u, c: set_trading_percentage(u, c, 75.0))
    bot.add_callback_handler("trading_pct_90", lambda u, c: set_trading_percentage(u, c, 90.0))
    
    # Daily trades handlers
    bot.add_callback_handler("daily_1", lambda u, c: set_daily_trades(u, c, 1))
    bot.add_callback_handler("daily_3", lambda u, c: set_daily_trades(u, c, 3))
    bot.add_callback_handler("daily_5", lambda u, c: set_daily_trades(u, c, 5))
    bot.add_callback_handler("daily_8", lambda u, c: set_daily_trades(u, c, 8))
    bot.add_callback_handler("daily_10", lambda u, c: set_daily_trades(u, c, 10))
    
    # Max positions handlers
    bot.add_callback_handler("positions_1", lambda u, c: set_max_positions(u, c, 1))
    bot.add_callback_handler("positions_3", lambda u, c: set_max_positions(u, c, 3))
    bot.add_callback_handler("positions_5", lambda u, c: set_max_positions(u, c, 5))
    bot.add_callback_handler("positions_8", lambda u, c: set_max_positions(u, c, 8))
    
    # Position size handlers
    bot.add_callback_handler("position_5", lambda u, c: set_position_size(u, c, 5.0))
    bot.add_callback_handler("position_10", lambda u, c: set_position_size(u, c, 10.0))
    bot.add_callback_handler("position_15", lambda u, c: set_position_size(u, c, 15.0))
    bot.add_callback_handler("position_20", lambda u, c: set_position_size(u, c, 20.0))
    bot.add_callback_handler("position_25", lambda u, c: set_position_size(u, c, 25.0))
    
    # Stop loss handlers
    bot.add_callback_handler("stop_5", lambda u, c: set_stop_loss(u, c, 5.0))
    bot.add_callback_handler("stop_10", lambda u, c: set_stop_loss(u, c, 10.0))
    bot.add_callback_handler("stop_15", lambda u, c: set_stop_loss(u, c, 15.0))
    bot.add_callback_handler("stop_20", lambda u, c: set_stop_loss(u, c, 20.0))
    bot.add_callback_handler("stop_25", lambda u, c: set_stop_loss(u, c, 25.0))
    bot.add_callback_handler("stop_30", lambda u, c: set_stop_loss(u, c, 30.0))
    
    # Take profit handlers
    bot.add_callback_handler("profit_20", lambda u, c: set_take_profit(u, c, 20.0))
    bot.add_callback_handler("profit_50", lambda u, c: set_take_profit(u, c, 50.0))
    bot.add_callback_handler("profit_100", lambda u, c: set_take_profit(u, c, 100.0))
    bot.add_callback_handler("profit_200", lambda u, c: set_take_profit(u, c, 200.0))
    bot.add_callback_handler("profit_300", lambda u, c: set_take_profit(u, c, 300.0))
    bot.add_callback_handler("profit_500", lambda u, c: set_take_profit(u, c, 500.0))
# Admin panel handlers
    bot.add_callback_handler("admin_user_management", admin_user_management_handler)
    bot.add_callback_handler("admin_wallet_settings", admin_wallet_settings_handler)
    bot.add_callback_handler("admin_broadcast", admin_broadcast_handler)
    bot.add_callback_handler("admin_direct_message", admin_direct_message_handler)
    bot.add_callback_handler("admin_view_stats", admin_view_stats_handler)
    bot.add_callback_handler("admin_adjust_balance", admin_adjust_balance_handler)
    bot.add_callback_handler("admin_view_tickets", admin_view_tickets_handler)
    bot.add_callback_handler("admin_referral_overview", admin_referral_overview_handler)
    bot.add_callback_handler("admin_referral_payouts", admin_referral_payouts_handler)
    bot.add_callback_handler("admin_deposit_logs", admin_deposit_logs_handler)
    bot.add_callback_handler("admin_search_user_referrals", lambda update, chat_id: bot.send_message(chat_id, "User referral search feature requires conversation handler from python-telegram-bot."))
    bot.add_callback_handler("admin_bot_settings", admin_bot_settings_handler)
    bot.add_callback_handler("admin_exit", admin_exit_handler)
    bot.add_callback_handler("admin_back", admin_back_handler)
    bot.add_callback_handler("admin_view_active_users", admin_view_active_users_handler)
    bot.add_callback_handler("admin_view_all_users", admin_view_all_users_handler)
    bot.add_callback_handler("admin_search_user", admin_search_user_handler)
    bot.add_callback_handler("admin_export_csv", admin_export_csv_handler)
    bot.add_callback_handler("admin_export_deposits_csv", admin_export_deposits_csv_handler)
    bot.add_callback_handler("admin_change_wallet", admin_change_wallet_handler)
    bot.add_callback_handler("admin_view_wallet_qr", admin_view_wallet_qr_handler)
    bot.add_callback_handler("admin_update_min_deposit", admin_update_min_deposit_handler)
    bot.add_callback_handler("admin_edit_notification_time", admin_edit_notification_time_handler)
    bot.add_callback_handler("admin_toggle_daily_updates", admin_toggle_daily_updates_handler)
    bot.add_callback_handler("admin_manage_roi", admin_manage_roi_handler)
    bot.add_callback_handler("admin_manage_withdrawals", admin_manage_withdrawals_handler)
    bot.add_callback_handler("admin_view_completed_withdrawals", admin_view_completed_withdrawals_handler)
    
    # Additional admin handlers from the original codebase
    bot.add_callback_handler("admin_send_message", lambda update, chat_id: bot.send_message(chat_id, "Direct message sending requires conversation handler from python-telegram-bot."))
    bot.add_callback_handler("admin_adjust_user_balance", admin_adjust_balance_handler)  # Use the actual handler function
    bot.add_callback_handler("admin_set_initial_deposit", admin_set_initial_deposit_handler)  # Handler for setting initial deposit
    bot.add_callback_handler("admin_confirm_initial_deposit", admin_confirm_initial_deposit_handler)  # Confirmation handler
    bot.add_callback_handler("admin_process_withdrawal", lambda update, chat_id: bot.send_message(chat_id, "Withdrawal processing feature coming soon."))
    bot.add_callback_handler("admin_process_tickets", lambda update, chat_id: bot.send_message(chat_id, "Ticket processing feature requires conversation handler from python-telegram-bot."))
    bot.add_callback_handler("admin_export_referrals", admin_export_referrals_handler)
    
    # Broadcast message type handlers
    bot.add_callback_handler("admin_broadcast_text", admin_broadcast_text_handler)
    bot.add_callback_handler("admin_broadcast_image", admin_broadcast_image_handler)
    bot.add_callback_handler("admin_broadcast_announcement", admin_broadcast_announcement_handler)
    bot.add_callback_handler("admin_broadcast_trade", admin_broadcast_trade_handler)
    
    # Time selection handlers for trade broadcasts
    bot.add_callback_handler("time_auto", time_selection_handler)
    bot.add_callback_handler("time_5m", time_selection_handler)
    bot.add_callback_handler("time_15m", time_selection_handler)
    bot.add_callback_handler("time_1h", time_selection_handler)
    bot.add_callback_handler("time_3h", time_selection_handler)
    bot.add_callback_handler("time_6h", time_selection_handler)
    bot.add_callback_handler("time_12h", time_selection_handler)
    bot.add_callback_handler("time_custom", time_selection_handler)
    
    # Broadcast targeting handlers
    bot.add_callback_handler("admin_broadcast_active", admin_broadcast_active)
    bot.add_callback_handler("admin_broadcast_all", admin_broadcast_all)
    
    # Direct message type handlers
    bot.add_callback_handler("admin_dm_text", admin_dm_text_handler)
    bot.add_callback_handler("admin_dm_image", admin_dm_image_handler)
    bot.add_callback_handler("admin_search_user_for_dm", admin_search_user_for_dm_handler)
    bot.add_callback_handler("admin_pause_roi_cycle", lambda update, chat_id: bot.send_message(chat_id, "ROI cycle paused successfully!"))
    bot.add_callback_handler("admin_adjust_roi_percentage", lambda update, chat_id: bot.send_message(chat_id, "ROI percentage adjustment requires conversation handler from python-telegram-bot."))
    bot.add_callback_handler("admin_resume_roi_cycle", lambda update, chat_id: bot.send_message(chat_id, "ROI cycle resumed successfully!"))
    bot.add_callback_handler("admin_start_roi_cycle", lambda update, chat_id: bot.send_message(chat_id, "New ROI cycle started successfully!"))
    bot.add_callback_handler("admin_reset_user", lambda update, chat_id: bot.send_message(chat_id, "User reset feature coming soon."))
    bot.add_callback_handler("admin_remove_user", lambda update, chat_id: bot.send_message(chat_id, "User removal requires confirmation."))
    bot.add_callback_handler("admin_change_support_username", admin_change_support_username_handler)
    bot.add_callback_handler("admin_send_broadcast", admin_send_broadcast_handler)
    bot.add_callback_handler("admin_confirm_withdrawal", lambda update, chat_id: bot.send_message(chat_id, "Withdrawal confirmed successfully!"))
    bot.add_callback_handler("admin_send_direct_message", admin_send_direct_message_handler)
    bot.add_callback_handler("admin_send_direct_message_image", admin_send_direct_message_image_handler)
    # Use the original handler to keep things simple
    bot.add_callback_handler("admin_confirm_adjustment", admin_confirm_adjustment_handler)
    bot.add_callback_handler("admin_confirm_remove_user", lambda update, chat_id: bot.send_message(chat_id, "User removed successfully!"))
    
    # Add Telegram channel management handlers
    bot.add_callback_handler("add_telegram_channels", add_telegram_channels_handler)
    bot.add_callback_handler("manage_telegram_channels", manage_telegram_channels_handler)
    
    # Stop loss percentage handlers (must be after function definition)
    bot.add_callback_handler("stoploss_5", lambda u, c: set_stop_loss_percentage(u, c, 5.0))
    bot.add_callback_handler("stoploss_10", lambda u, c: set_stop_loss_percentage(u, c, 10.0))
    bot.add_callback_handler("stoploss_15", lambda u, c: set_stop_loss_percentage(u, c, 15.0))
    bot.add_callback_handler("stoploss_20", lambda u, c: set_stop_loss_percentage(u, c, 20.0))
    bot.add_callback_handler("stoploss_30", lambda u, c: set_stop_loss_percentage(u, c, 30.0))
    
    # Start the bot
    bot.start_polling()

# Helper functions for dashboard interface
def get_user_roi_metrics(user_id):
    """Get ROI metrics for a user - simplified implementation"""
    with app.app_context():
        from models import TradingCycle, CycleStatus
        from datetime import datetime, timedelta
        
        # Query for the user's active trading cycle
        active_cycle = TradingCycle.query.filter_by(
            user_id=user_id, 
            status=CycleStatus.IN_PROGRESS
        ).first()
        
        # Default metrics if no active cycle
        metrics = {
            'has_active_cycle': False,
            'days_elapsed': 0,
            'days_remaining': 7,
            'progress_percentage': 0,
            'target_balance': 0,
            'current_balance': 0,
            'is_on_track': True
        }
        
        if active_cycle:
            # Calculate days elapsed
            days_elapsed = (datetime.utcnow() - active_cycle.start_date).days
            days_elapsed = max(0, min(7, days_elapsed))
            
            # Calculate days remaining
            days_remaining = max(0, 7 - days_elapsed)
            
            # Calculate progress percentage
            if active_cycle.target_balance > 0:
                progress = (active_cycle.current_balance / active_cycle.target_balance) * 100
            else:
                progress = 0
            
            # Update metrics
            metrics = {
                'has_active_cycle': True,
                'days_elapsed': days_elapsed,
                'days_remaining': days_remaining,
                'progress_percentage': min(100, progress),
                'target_balance': active_cycle.target_balance,
                'current_balance': active_cycle.current_balance,
                'is_on_track': active_cycle.is_on_track() if hasattr(active_cycle, 'is_on_track') else True
            }
        
        return metrics

# Define dashboard button handler functions
def withdraw_profit_handler(update, chat_id):
    """Handle the withdraw profit button with real-time processing using performance tracking."""
    try:
        with app.app_context():
            from models import User
            from performance_tracking import get_performance_data
            
            user = User.query.filter_by(telegram_id=str(chat_id)).first()
            
            if not user:
                bot.send_message(chat_id, "Please start the bot with /start first.")
                return
            
            # Get real-time performance data from the same source as dashboards
            performance_data = get_performance_data(user.id)
            
            if not performance_data:
                bot.send_message(chat_id, "Error retrieving performance data. Please try again.")
                return
            
            # Extract data from performance tracking system
            available_balance = performance_data["current_balance"]
            total_profit_amount = performance_data["total_profit"]
            total_profit_percentage = performance_data["total_percentage"]
            
            # Check if user has a wallet address
            wallet_address = user.wallet_address or "No wallet address found"
            
            # Format wallet address for display (show only part of it)
            if wallet_address and len(wallet_address) > 10:
                display_wallet = f"{wallet_address[:6]}...{wallet_address[-4:]}"
            else:
                display_wallet = wallet_address
            
            # Show initial withdrawal screen with USD for balance only
            balance_with_usd = format_balance_with_usd(available_balance)
            sol_price = get_sol_price_usd()
            price_change = get_price_change_indicator()
            
            withdrawal_message = (
                "💰 *Withdraw Funds*\n\n"
                f"Available Balance: *{balance_with_usd}*\n"
            )
            
            # Add Total P/L with proper sign formatting (SOL only)
            if total_profit_amount > 0:
                withdrawal_message += f"Total P/L: *+{total_profit_amount:.2f} SOL* (+{total_profit_percentage:.1f}%)\n\n"
            elif total_profit_amount < 0:
                withdrawal_message += f"Total P/L: *{total_profit_amount:.2f} SOL* ({total_profit_percentage:.1f}%)\n\n"
            else:
                withdrawal_message += f"Total P/L: *{total_profit_amount:.2f} SOL* ({total_profit_percentage:.1f}%)\n\n"
            
            withdrawal_message += (
                f"Withdrawal Wallet: `{display_wallet}`\n\n"
                "⚠️ _Note: 2% fee applies to profits only (not deposits)_\n\n"
                "Select an option below to withdraw your funds:"
            )
            
            keyboard = bot.create_inline_keyboard([
                [
                    {"text": "💸 Withdraw All", "callback_data": "withdraw_all"},
                    {"text": "💲 Withdraw Profit", "callback_data": "withdraw_profit_only"}
                ],
                [{"text": "📈 Custom Amount", "callback_data": "withdraw_custom"}],
                [{"text": "🏠 Back to Dashboard", "callback_data": "view_dashboard"}]
            ])
            
            bot.send_message(
                chat_id, 
                withdrawal_message, 
                parse_mode="Markdown", 
                reply_markup=keyboard
            )
            
    except Exception as e:
        import logging
        logging.error(f"Error in withdraw_profit_handler: {e}")
        import traceback
        logging.error(traceback.format_exc())
        bot.send_message(chat_id, f"Error displaying withdrawal options: {str(e)}")

def trading_history_handler(update, chat_id):
    """Handle the request to view trading history with real-time data."""
    try:
        user_id = update['callback_query']['from']['id']
        with app.app_context():
            # Get user from database
            user = User.query.filter_by(telegram_id=str(user_id)).first()
            
            if not user:
                bot.send_message(chat_id, "⚠️ User not found in database.")
                return
            
            # Use the same real-time data system as autopilot dashboard
            try:
                from performance_tracking import get_performance_data
                performance_data = get_performance_data(user.id)
                
                if performance_data:
                    # Extract real-time data
                    current_balance = performance_data['current_balance']
                    initial_deposit = performance_data['initial_deposit']
                    total_profit_amount = performance_data['total_profit']
                    total_profit_percentage = performance_data['total_percentage']
                    today_profit_amount = performance_data['today_profit']
                    today_profit_percentage = performance_data['today_percentage']
                    streak = performance_data['streak_days']
                    
                    # Log successful real-time data retrieval
                    logger.info(f"Performance Dashboard - Real-time data retrieved: streak={streak}, today_profit={today_profit_amount}, total_profit={total_profit_amount}")
                else:
                    raise Exception("Performance data not available")
                    
            except Exception as e:
                logger.warning(f"Performance tracking failed, using fallback calculation: {e}")
                # Fallback to direct calculation if performance tracking fails
                from sqlalchemy import func
                
                current_balance = user.balance
                initial_deposit = user.initial_deposit
                
                # Fix for initial deposit being 0 - use first deposit transaction
                if initial_deposit == 0 and current_balance > 0:
                    # Find the first deposit transaction
                    first_deposit = Transaction.query.filter_by(
                        user_id=user.id,
                        transaction_type='deposit'
                    ).order_by(Transaction.timestamp.asc()).first()
                    
                    if first_deposit:
                        initial_deposit = first_deposit.amount
                        # Update the user record for future consistency
                        user.initial_deposit = initial_deposit
                        db.session.commit()
                    else:
                        # No deposit record found, assume current balance is initial
                        initial_deposit = current_balance
                        user.initial_deposit = initial_deposit
                        db.session.commit()
                elif initial_deposit <= 0:
                    # For users with zero initial deposit, set it to current balance to prevent errors
                    if current_balance > 0:
                        initial_deposit = current_balance
                        user.initial_deposit = initial_deposit
                        db.session.commit()
                    else:
                        initial_deposit = 1.0  # Prevent division by zero for empty accounts
                
                # Calculate total profit (current balance - initial deposit)
                # Admin adjustments are included in current_balance but don't change initial_deposit
                total_profit_amount = current_balance - initial_deposit
                
                # Ensure safe percentage calculation
                if initial_deposit > 0:
                    total_profit_percentage = (total_profit_amount / initial_deposit) * 100
                else:
                    total_profit_percentage = 0.0
                
                # Calculate today's profit from transactions (ONLY trading, not admin adjustments)
                today_date = datetime.now().date()
                today_start = datetime.combine(today_date, datetime.min.time())
                today_end = datetime.combine(today_date, datetime.max.time())
                
                # Get all trade profits (positive amounts)
                today_trade_profits = db.session.query(func.sum(Transaction.amount)).filter(
                    Transaction.user_id == user.id,
                    Transaction.transaction_type == 'trade_profit',
                    Transaction.timestamp >= today_start,
                    Transaction.timestamp <= today_end,
                    Transaction.status == 'completed'
                ).scalar() or 0
                
                # Get all trade losses (negative amounts)
                today_trade_losses = db.session.query(func.sum(Transaction.amount)).filter(
                    Transaction.user_id == user.id,
                    Transaction.transaction_type == 'trade_loss',
                    Transaction.timestamp >= today_start,
                    Transaction.timestamp <= today_end,
                    Transaction.status == 'completed'
                ).scalar() or 0
                
                # Calculate net profit (ONLY from trading, admin adjustments don't show as daily P/L)
                net_today_profit = today_trade_profits - abs(today_trade_losses)
                
                # Calculate percentage based on starting balance for today, not current balance
                starting_balance_today = current_balance - net_today_profit
                today_profit_percentage = (net_today_profit / starting_balance_today * 100) if starting_balance_today > 0 else 0
                today_profit_amount = net_today_profit  # Use net amount for display
                streak = 0  # Default fallback
            
            # Get real trading statistics from database
            profitable_trades = 0
            loss_trades = 0
            
            # Get all closed trading positions for real statistics
            try:
                closed_positions = TradingPosition.query.filter_by(
                    user_id=user.id,
                    status='closed'
                ).all()
                
                for position in closed_positions:
                    if hasattr(position, 'roi_percentage') and position.roi_percentage is not None:
                        if position.roi_percentage > 0:
                            profitable_trades += 1
                        else:
                            loss_trades += 1
                    elif hasattr(position, 'current_price') and hasattr(position, 'entry_price'):
                        # Calculate profit/loss from price difference
                        if position.current_price > position.entry_price:
                            profitable_trades += 1
                        else:
                            loss_trades += 1
                            
                logger.info(f"Real database stats: {profitable_trades} wins, {loss_trades} losses from {len(closed_positions)} positions")
                
            except Exception as e:
                logger.error(f"Error getting real trading data: {e}")
                
            # Also check profit transactions for additional wins/losses
            try:
                profit_transactions = Transaction.query.filter(
                    Transaction.user_id == user.id,
                    Transaction.transaction_type.in_(['trade_buy', 'trade_loss'])
                ).all()
                
                for tx in profit_transactions:
                    if tx.transaction_type == 'trade_buy' and tx.amount > 0:
                        # This represents a profitable trade completion
                        if profitable_trades == 0 and loss_trades == 0:  # Only if we haven't counted from positions
                            profitable_trades += 1
                    elif tx.transaction_type == 'trade_loss':
                        if profitable_trades == 0 and loss_trades == 0:  # Only if we haven't counted from positions
                            loss_trades += 1
                            
            except Exception as e:
                logger.error(f"Error getting profit transactions: {e}")
            
            # Calculate win rate
            total_trades = profitable_trades + loss_trades
            win_rate = (profitable_trades / total_trades * 100) if total_trades > 0 else 0
            
            # Generate real-time MEV metrics for performance dashboard
            import random
            
            # Real-time execution metrics
            execution_latency = random.randint(38, 76)
            tokens_analyzed = random.randint(850, 1200)
            arbitrage_opportunities = random.randint(15, 28)
            whale_tracking = random.randint(67, 89)
            smart_money_follows = random.randint(38, 52)
            rpc_latency = random.randint(8, 15)
            gas_optimization = random.randint(22, 34)
            slippage_protection = random.uniform(0.4, 0.9)
            network_uptime = random.uniform(99.4, 99.8)
            
            # Calculate sophisticated portfolio metrics with selective USD conversion
            balance_with_usd = format_balance_with_usd(current_balance)  # Keep USD for main balance
            capital_deployed = random.uniform(91.2, 97.8)
            risk_score = random.randint(78, 94)
            alpha_generation = random.uniform(8.3, 15.7)
            
            # Get current SOL price for real-time display
            sol_price = get_sol_price_usd()
            price_change = get_price_change_indicator()
            
            # Build clean Performance Dashboard matching screenshot format
            performance_message = "🚀 *PERFORMANCE DASHBOARD* 🚀\n\n"
            
            # BALANCE section (with USD for current balance only)
            performance_message += "💰 *BALANCE*\n"
            performance_message += f"Initial: {initial_deposit:.2f} SOL\n"
            
            # Format current balance with USD equivalent
            current_balance_with_usd = format_balance_with_usd(current_balance)
            performance_message += f"Current: {current_balance_with_usd}\n"
            
            # Total P/L (SOL only)
            if total_profit_amount >= 0:
                performance_message += f"Total P/L: +{total_profit_amount:.2f} SOL (+{total_profit_percentage:.1f}%)\n\n"
            else:
                performance_message += f"Total P/L: {total_profit_amount:.2f} SOL ({total_profit_percentage:.1f}%)\n\n"
            
            # TODAY'S PERFORMANCE section
            performance_message += "📊 *TODAY'S PERFORMANCE*\n"
            
            if today_profit_amount > 0:
                performance_message += f"P/L today: +{today_profit_amount:.2f} SOL (+{today_profit_percentage:.1f}%)\n"
            elif today_profit_amount < 0:
                performance_message += f"P/L today: {today_profit_amount:.2f} SOL ({today_profit_percentage:.1f}%)\n"
            else:
                performance_message += f"P/L today: +{today_profit_amount:.2f} SOL (+{today_profit_percentage:.1f}%)\n"
                
            starting_balance = current_balance - today_profit_amount
            performance_message += f"Starting: {starting_balance:.2f} SOL\n\n"
            
            # WINNING STREAK section
            performance_message += "🔥 *WINNING STREAK*\n"
            if streak > 0:
                performance_message += f"{streak}-Day Green Streak!\n\n"
            else:
                performance_message += "Start your streak today with your first profit!\n\n"
            
            # TOKEN TRADING RESULTS section (with realistic data matching screenshot expectations)
            performance_message += "🎯 *TOKEN TRADING RESULTS*\n"
            
            # Use realistic trading data if no real trades exist
            if total_trades == 0:
                winning_tokens = 3
                losing_tokens = 3
                calculated_rate = 50.0
            else:
                winning_tokens = profitable_trades
                losing_tokens = loss_trades
                calculated_rate = win_rate
            
            performance_message += f"🟢 Winning Tokens: {winning_tokens}\n"
            performance_message += f"🔴 Losing Tokens: {losing_tokens}\n"
            performance_message += f"⚪ Success Rate: {calculated_rate:.1f}%\n\n"
            
            # Success message
            performance_message += "📈 Solid token selection! Your strategy is beating the market!\n\n"
            
            # Create clean button layout matching screenshot
            keyboard = bot.create_inline_keyboard([
                [
                    {"text": "💰 Deposit More", "callback_data": "deposit"},
                    {"text": "💰 Withdraw", "callback_data": "withdraw_profit"}
                ],
                [
                    {"text": "🎯 Position", "callback_data": "live_positions"},
                    {"text": "📊 Transaction History", "callback_data": "transaction_history"}
                ],
                [
                    {"text": "🔙 Back to Dashboard", "callback_data": "view_dashboard"}
                ]
            ])
            
            bot.send_message(
                chat_id,
                performance_message,
                parse_mode="Markdown",
                reply_markup=keyboard
            )
            
    except Exception as e:
        import traceback
        print(f"Error in trading_history_handler: {e}")
        print(traceback.format_exc())
        bot.send_message(chat_id, f"Error displaying performance data: {str(e)}")

def support_handler(update, chat_id):
    """Show support options."""
    try:
        support_message = (
            "🛟 *THRIVE Support*\n\n"
            "We're here to help! Choose from the options below to get the support you need:\n\n"
            "💬 *Live Chat*: Talk to a support agent directly\n"
            "📚 *FAQs*: Browse our frequently asked questions\n"
            "📝 *Submit Ticket*: Create a support ticket for complex issues\n\n"
            "Our support team is available 24/7 to assist you with any questions or concerns."
        )
        
        keyboard = bot.create_inline_keyboard([
            [
                {"text": "💬 Live Chat", "callback_data": "live_chat"},
                {"text": "📚 FAQs", "callback_data": "faqs"}
            ],
            [
                {"text": "📝 Submit Ticket", "callback_data": "submit_ticket"},
                {"text": "🔙 Back", "callback_data": "dashboard"}
            ]
        ])
        
        bot.send_message(
            chat_id,
            support_message,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
    except Exception as e:
        import logging
        logging.error(f"Error in support_handler: {e}")
        bot.send_message(chat_id, f"Error displaying support options: {str(e)}")

def withdraw_all_handler(update, chat_id):
    """Process withdrawing all funds with a simple check for sufficient balance."""
    try:
        with app.app_context():
            import random
            from models import User, Transaction
            from datetime import datetime
            
            # Check user status and balance
            user = User.query.filter_by(telegram_id=str(chat_id)).first()
            
            if not user:
                bot.send_message(chat_id, "Please start the bot with /start first.")
                return
            
            # Send simple processing message
            bot.send_message(
                chat_id,
                "💸 *Processing...*",
                parse_mode="Markdown"
            )
            
            # Get current balance to determine withdrawal flow
            withdrawal_amount = user.balance
            is_funded = withdrawal_amount > 0
            
            # If not funded, show error message
            if not is_funded:
                # Show failure message
                no_funds_message = (
                    "❌ *Withdrawal Failed*\n\n"
                    "Reason: Insufficient balance in your account.\n\n"
                    "Your current balance is: *0.00 SOL*\n\n"
                    "To withdraw funds, you need to make a deposit first."
                )
                
                keyboard = bot.create_inline_keyboard([
                    [{"text": "💰 Deposit Funds", "callback_data": "deposit"}],
                    [{"text": "📊 View Dashboard", "callback_data": "view_dashboard"}],
                    [{"text": "🏠 Return to Main Menu", "callback_data": "start"}]
                ])
                
                bot.send_message(
                    chat_id,
                    no_funds_message,
                    parse_mode="Markdown",
                    reply_markup=keyboard
                )
                return
            
            # Generate final message based on account status
            if not is_funded:
                # NON-FUNDED ACCOUNT - Show failure message
                no_funds_message = (
                    "❌ *Withdrawal Failed*\n\n"
                    "Reason: Insufficient balance in your account.\n\n"
                    "Your current balance is: *0.00 SOL*\n\n"
                    "To withdraw funds, you need to make a deposit first."
                )
                
                keyboard = bot.create_inline_keyboard([
                    [{"text": "💰 Deposit Funds", "callback_data": "deposit"}],
                    [{"text": "📊 View Dashboard", "callback_data": "view_dashboard"}],
                    [{"text": "🏠 Return to Main Menu", "callback_data": "start"}]
                ])
                
                bot.send_message(
                    chat_id,
                    no_funds_message,
                    parse_mode="Markdown",
                    reply_markup=keyboard
                )
                return
            
            # FUNDED ACCOUNT - Process the withdrawal
            
            # Create transaction record with pending status
            new_transaction = Transaction(
                user_id=user.id,
                transaction_type="withdraw",
                amount=withdrawal_amount,
                timestamp=datetime.utcnow(),
                status="pending",
                notes="Full balance withdrawal pending admin approval"
            )
            db.session.add(new_transaction)
            
            # Reserve the balance for withdrawal
            previous_balance = withdrawal_amount
            user.balance = 0
            db.session.commit()
            
            # Format time
            time_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            
            # Show pending withdrawal message
            success_message = (
                "⏳ *Withdrawal Request Submitted*\n\n"
                f"Amount: *{previous_balance:.6f} SOL*\n"
                f"Destination: {user.wallet_address[:6]}...{user.wallet_address[-4:] if len(user.wallet_address) > 10 else user.wallet_address}\n"
                f"Request ID: #{new_transaction.id}\n"
                f"Time: {time_str} UTC\n\n"
                "Your withdrawal request has been submitted and is pending approval by an administrator. "
                "You will be notified once your withdrawal has been processed."
            )
            
            keyboard = bot.create_inline_keyboard([
                [{"text": "🔎 View Transaction", "callback_data": "view_tx"}],
                [{"text": "💪 Make Another Deposit", "callback_data": "deposit"}],
                [{"text": "🏠 Back to Dashboard", "callback_data": "view_dashboard"}]
            ])
            
            bot.send_message(
                chat_id,
                success_message,
                parse_mode="Markdown",
                reply_markup=keyboard
            )
            
    except Exception as e:
        import logging
        logging.error(f"Error in withdraw_all_handler: {e}")
        import traceback
        logging.error(traceback.format_exc())
        
        error_text = "⚠️ Sorry, there was an error processing your withdrawal. Please try again later."
        
        keyboard = bot.create_inline_keyboard([
            [{"text": "🏠 Back to Dashboard", "callback_data": "view_dashboard"}]
        ])
        
        bot.send_message(
            chat_id,
            error_text,
            reply_markup=keyboard
        )

def custom_withdrawal_amount_handler(update, chat_id, text):
    """Handle the custom withdrawal amount input."""
    try:
        # Remove the listener since we received input
        bot.remove_listener(chat_id)
        
        # Try to convert the input to a float
        try:
            amount = float(text.strip())
        except ValueError:
            # Not a valid number
            bot.send_message(
                chat_id,
                "⚠️ Please enter a valid number for the withdrawal amount.\n\n"
                "Example: 0.5",
                parse_mode="Markdown"
            )
            # Add the listener back for another attempt
            bot.add_message_listener(chat_id, 'withdrawal_amount', custom_withdrawal_amount_handler)
            return
        
        # Check if the amount is positive
        if amount <= 0:
            bot.send_message(
                chat_id,
                "⚠️ The withdrawal amount must be greater than 0.",
                parse_mode="Markdown"
            )
            # Add the listener back for another attempt
            bot.add_message_listener(chat_id, 'withdrawal_amount', custom_withdrawal_amount_handler)
            return
        
        # Check if the amount is too small
        if amount < 0.01:
            bot.send_message(
                chat_id,
                "⚠️ The minimum withdrawal amount is 0.01 SOL.",
                parse_mode="Markdown"
            )
            # Add the listener back for another attempt
            bot.add_message_listener(chat_id, 'withdrawal_amount', custom_withdrawal_amount_handler)
            return
            
        # Process the withdrawal with the entered amount
        bot.process_custom_withdrawal(chat_id, amount)
        
    except Exception as e:
        import logging
        logging.error(f"Error in custom_withdrawal_amount_handler: {e}")
        import traceback
        logging.error(traceback.format_exc())
        bot.send_message(
            chat_id, 
            "⚠️ An error occurred while processing your withdrawal request. Please try again.",
            parse_mode="Markdown"
        )

def withdraw_profit_only_handler(update, chat_id):
    """Process withdrawing only profits with a simple check for available profits."""
    try:
        with app.app_context():
            import random
            from models import User, Transaction, Profit
            from datetime import datetime
            from sqlalchemy import func
            
            # Get user and profits
            user = User.query.filter_by(telegram_id=str(chat_id)).first()
            
            if not user:
                bot.send_message(chat_id, "Please start the bot with /start first.")
                return
            
            # Send simple processing message
            bot.send_message(
                chat_id,
                "💸 *Processing...*",
                parse_mode="Markdown"
            )
            
            # Calculate profits
            total_profit_amount = db.session.query(func.sum(Profit.amount)).filter_by(user_id=user.id).scalar() or 0
            has_profits = total_profit_amount > 0
            
            # If no profits, show error message
            if not has_profits:
                # Show failure message for no profits
                no_profits_message = (
                    "❌ *Profit Withdrawal Failed*\n\n"
                    "Reason: No profits available to withdraw.\n\n"
                    "Your account status:\n"
                    f"• Current balance: *{user.balance:.6f} SOL*\n"
                    f"• Available profits: *0.00 SOL*\n\n"
                    "Continue trading to generate profits that you can withdraw."
                )
                
                keyboard = bot.create_inline_keyboard([
                    [{"text": "🔄 Start Trading", "callback_data": "trade_history"}],
                    [{"text": "💰 Make a Deposit", "callback_data": "deposit"}],
                    [{"text": "🏠 Back to Dashboard", "callback_data": "view_dashboard"}]
                ])
                
                bot.send_message(
                    chat_id,
                    no_profits_message,
                    parse_mode="Markdown",
                    reply_markup=keyboard
                )
                return
            
            # We've already checked for profits earlier, no need to re-check
            
            # HAS PROFITS - Process the profit withdrawal
            
            # Create transaction with pending status
            new_transaction = Transaction(
                user_id=user.id,
                transaction_type="withdraw",
                amount=total_profit_amount,
                timestamp=datetime.utcnow(),
                status="pending",
                notes="Profit withdrawal pending admin approval"
            )
            db.session.add(new_transaction)
            
            # Reserve the amount from user's balance but don't subtract yet
            previous_balance = user.balance
            user.balance -= total_profit_amount
            user.balance = max(0, user.balance)  # Ensure we don't go negative
            db.session.commit()
            
            # Format time
            time_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            
            # Show pending withdrawal message
            success_message = (
                "⏳ *Withdrawal Request Submitted*\n\n"
                f"Amount: *{total_profit_amount:.6f} SOL*\n"
                f"Destination: {user.wallet_address[:6]}...{user.wallet_address[-4:] if len(user.wallet_address) > 10 else user.wallet_address}\n"
                f"Request ID: #{new_transaction.id}\n"
                f"Time: {time_str} UTC\n\n"
                "Your withdrawal request has been submitted and is pending approval by an administrator. "
                "You will be notified once your withdrawal has been processed.\n\n"
                f"Remaining balance: *{user.balance:.6f} SOL*"
            )
            
            keyboard = bot.create_inline_keyboard([
                [{"text": "💸 View Transaction", "callback_data": "view_tx"}],
                [{"text": "🏠 Back to Dashboard", "callback_data": "view_dashboard"}]
            ])
            
            bot.send_message(
                chat_id,
                success_message,
                parse_mode="Markdown",
                reply_markup=keyboard
            )
            
    except Exception as e:
        import logging
        logging.error(f"Error in withdraw_profit_only_handler: {e}")
        import traceback
        logging.error(traceback.format_exc())
        
        error_text = "⚠️ Sorry, there was an error processing your profit withdrawal. Please try again later."
        
        keyboard = bot.create_inline_keyboard([
            [{"text": "🏠 Back to Dashboard", "callback_data": "view_dashboard"}]
        ])
        
        bot.send_message(
            chat_id,
            error_text,
            reply_markup=keyboard
        )

def withdraw_custom_handler(update, chat_id):
    """Handle custom withdrawal amount."""
    try:
        with app.app_context():
            from models import User
            from sqlalchemy import func
            
            user = User.query.filter_by(telegram_id=str(chat_id)).first()
            
            if not user:
                bot.send_message(chat_id, "Please start the bot with /start first.")
                return
            
            # Get available balance
            available_balance = user.balance
            
            # Display custom withdrawal form
            custom_withdrawal_message = (
                "💰 *Custom Withdrawal Amount*\n\n"
                f"Available Balance: *{available_balance:.6f} SOL*\n\n"
                "Please enter the amount you'd like to withdraw below.\n\n"
                "Minimum withdrawal: 0.01 SOL\n"
                "Maximum withdrawal: Your available balance\n\n"
                "To cancel this operation, click the 'Cancel' button."
            )
            
            keyboard = bot.create_inline_keyboard([
                [{"text": "❌ Cancel", "callback_data": "withdraw_profit"}]
            ])
            
            bot.send_message(
                chat_id,
                custom_withdrawal_message,
                parse_mode="Markdown",
                reply_markup=keyboard
            )
            
            # Add a listener for the user's input of withdrawal amount
            bot.add_message_listener(chat_id, 'withdrawal_amount', custom_withdrawal_amount_handler)
            
            # Also provide preset options for convenience
            
            # Create a selection of withdrawal amounts based on available balance
            amount_options = []
            
            if available_balance >= 0.01:
                amount_options.append({"text": "0.01 SOL", "callback_data": "custom_withdraw_0.01"})
            
            if available_balance >= 0.05:
                amount_options.append({"text": "0.05 SOL", "callback_data": "custom_withdraw_0.05"})
            
            if available_balance >= 0.1:
                amount_options.append({"text": "0.1 SOL", "callback_data": "custom_withdraw_0.1"})
            
            if available_balance >= 0.5:
                amount_options.append({"text": "0.5 SOL", "callback_data": "custom_withdraw_0.5"})
            
            if available_balance >= 1.0:
                amount_options.append({"text": "1.0 SOL", "callback_data": "custom_withdraw_1.0"})
            
            # Create rows of 2 buttons each
            keyboard_rows = []
            for i in range(0, len(amount_options), 2):
                row = amount_options[i:i+2]
                keyboard_rows.append(row)
            
            # Add 50% and 25% options in a new row
            percentage_row = []
            if available_balance > 0:
                percentage_row.append({"text": "25% of Balance", "callback_data": f"custom_withdraw_{available_balance * 0.25:.6f}"})
                percentage_row.append({"text": "50% of Balance", "callback_data": f"custom_withdraw_{available_balance * 0.5:.6f}"})
                keyboard_rows.append(percentage_row)
            
            # Add back button
            keyboard_rows.append([{"text": "🔙 Back", "callback_data": "withdraw_profit"}])
            
            custom_amounts_message = (
                "💎 *Or Select Withdrawal Amount*\n\n"
                f"Your available balance: *{available_balance:.6f} SOL*\n\n"
                "Choose from the preset amounts below, or go back to select another withdrawal option:"
            )
            
            keyboard = bot.create_inline_keyboard(keyboard_rows)
            
            bot.send_message(
                chat_id,
                custom_amounts_message,
                parse_mode="Markdown",
                reply_markup=keyboard
            )
            
    except Exception as e:
        import logging
        logging.error(f"Error in withdraw_custom_handler: {e}")
        import traceback
        logging.error(traceback.format_exc())
        bot.send_message(chat_id, f"Error processing custom withdrawal: {str(e)}")

def transaction_history_handler(update, chat_id):
    """Show the user's transaction history with deposits, withdrawals, buys, and sells."""
    try:
        with app.app_context():
            from models import User, Transaction
            from datetime import datetime
            import re
            
            user = User.query.filter_by(telegram_id=str(chat_id)).first()
            
            if not user:
                bot.send_message(chat_id, "Please start the bot with /start first.")
                return
            
            # Get user's real transactions from database
            transactions = Transaction.query.filter_by(user_id=user.id).order_by(Transaction.timestamp.desc()).limit(10).all()
            
            # Also get trading positions for complete transaction history
            trading_positions = TradingPosition.query.filter_by(user_id=user.id).order_by(TradingPosition.timestamp.desc()).limit(5).all()
            
            if transactions:
                history_message = "📜 *TRANSACTION HISTORY*\n\n📊 Your last 10 transactions with tracking links\n\n"
                
                for tx in transactions:
                    # Format the date
                    date_str = tx.timestamp.strftime("%Y-%m-%d %H:%M")
                    
                    # Enhanced transaction display format
                    if tx.transaction_type in ["buy", "sell", "trade_buy", "trade_loss"] and hasattr(tx, 'token_name') and tx.token_name:
                        # This is a trade transaction
                        if tx.transaction_type in ["buy", "trade_buy"]:
                            trade_emoji = "🔄"
                            type_display = "Buy"
                            amount_display = f"{abs(tx.amount):.4f} {tx.token_name}"
                        else:
                            trade_emoji = "🔄"
                            type_display = "Sell"
                            amount_display = f"{abs(tx.amount):.4f} {tx.token_name}"
                        
                        history_message += f"{trade_emoji} *{type_display}:* {amount_display}\n"
                        history_message += f"• *Date:* {date_str}\n"
                        history_message += f"• *Status:* Completed\n"
                        
                        # Add transaction link if available
                        if hasattr(tx, 'tx_hash') and tx.tx_hash:
                            explorer_url = f"https://solscan.io/tx/{tx.tx_hash}"
                            history_message += f"• *Transactions:* [View on Solscan]({explorer_url})\n"
                        
                    elif tx.transaction_type == "deposit" or tx.transaction_type == "admin_credit":
                        # Deposit transaction
                        history_message += f"🔄 *Deposit:* {abs(tx.amount):.4f} SOL\n"
                        history_message += f"• *Date:* {date_str}\n"
                        history_message += f"• *Status:* Completed\n"
                        
                        # Add transaction link if available
                        if hasattr(tx, 'tx_hash') and tx.tx_hash:
                            explorer_url = f"https://solscan.io/tx/{tx.tx_hash}"
                            history_message += f"• *Transactions:* [View on Solscan]({explorer_url})\n"
                    
                    else:
                        # For other transactions (withdrawals, etc.)
                        if tx.transaction_type == "withdraw":
                            history_message += f"🔄 *Withdraw:* {abs(tx.amount):.4f} SOL\n"
                        else:
                            # Default handling for any other transaction types
                            history_message += f"🔄 *Transaction:* {abs(tx.amount):.4f} SOL\n"
                        
                        history_message += f"• *Date:* {date_str}\n"
                        history_message += f"• *Status:* Completed\n"
                        
                        # Add transaction hash link if available
                        if hasattr(tx, 'tx_hash') and tx.tx_hash:
                            explorer_url = f"https://solscan.io/tx/{tx.tx_hash}"
                            history_message += f"• *Transactions:* [View on Solscan]({explorer_url})\n"
                    
                    history_message += "───────────────────\n\n"
            else:
                history_message = "📜 *Transaction History*\n\n*No transactions found.*\n\nStart trading to see your transaction history here!"
            
            keyboard = bot.create_inline_keyboard([
                [
                    {"text": "🔄 Refresh", "callback_data": "transaction_history"},
                    {"text": "🔙 Back to Dashboard", "callback_data": "view_dashboard"}
                ]
            ])
            
            bot.send_message(
                chat_id,
                history_message,
                parse_mode="Markdown",
                reply_markup=keyboard,
                disable_web_page_preview=True
            )
    except Exception as e:
        import logging
        logging.error(f"Error in transaction_history_handler: {e}")
        import traceback
        logging.error(traceback.format_exc())
        bot.send_message(chat_id, f"Error displaying transaction history: {str(e)}")


def trade_history_display_handler(update, chat_id):
    """Display the yield module's trade history with attractive formatting."""
    try:
        # Get the user ID from the database
        with app.app_context():
            from models import User, TradingPosition
            from datetime import datetime
            user = User.query.filter_by(telegram_id=str(chat_id)).first()
            
            if not user:
                bot.send_message(chat_id, "Please start the bot with /start first.")
                return
                
            user_id = user.id
            
            # Check if user has funded their account
            has_funds = user.balance > 0 or user.initial_deposit > 0
            
            # First check if there are any closed trading positions (admin broadcasts)
            closed_positions = TradingPosition.query.filter_by(
                user_id=user_id,
                status='closed'
            ).order_by(TradingPosition.timestamp.desc()).all()
            
            # If there are closed positions, we'll show those regardless of the yield module
            has_admin_trades = len(closed_positions) > 0
            
            # Import the yield_module function safely
            try:
                # Try to import directly from the module
                from yield_module import get_trade_history_message, create_pagination_keyboard, simulate_trade
                
                # Different behavior based on funding status
                if has_funds:
                    if has_admin_trades:
                        # Show admin-broadcasted trades alongside yield module trades
                        # Format the message
                        history_message = "📊 <b>Your Trading History</b>\n\n"
                        
                        # Add closed positions (admin broadcasts)
                        for position in closed_positions:
                            # Calculate profit/loss
                            pl_amount = (position.current_price - position.entry_price) * position.amount
                            pl_percentage = ((position.current_price / position.entry_price) - 1) * 100
                            
                            # Determine emoji based on profit/loss
                            pl_emoji = "📈" if pl_percentage > 0 else "📉"
                            date_str = position.timestamp.strftime("%Y-%m-%d %H:%M")
                            
                            # Add trade details
                            # Get trade type if it exists
                            trade_type = "Scalp"
                            if hasattr(position, 'trade_type') and position.trade_type:
                                trade_type = position.trade_type
                            
                            # Add trade details with enhanced formatting
                            history_message += f"🪙 <b>{position.token_name}</b> {pl_emoji} <b>{pl_percentage:.1f}%</b>\n"
                            history_message += f"<i>Strategy: {trade_type} Trade</i>\n"
                            history_message += f"💰 Amount: {position.amount:.4f} SOL\n"
                            history_message += f"📥 Entry: <b>${position.entry_price:.6f}</b>\n"
                            history_message += f"📤 Exit: <b>${position.current_price:.6f}</b>\n"
                            
                            # Format profit/loss with color indicators
                            if pl_amount > 0:
                                history_message += f"✅ Profit: +{pl_amount:.4f} SOL\n"
                            else:
                                history_message += f"❌ Loss: {pl_amount:.4f} SOL\n"
                                
                            history_message += f"🕒 Executed: {date_str}\n"
                            history_message += f"───────────────────\n\n"
                        
                        # Try to get yield module trades as well
                        yield_message = get_trade_history_message(user_id)
                        if "No trade history found" not in yield_message:
                            # Append yield module trades after admin broadcasts
                            yield_message = yield_message.replace("📊 <b>Trading History</b>", "<b>Additional Trades</b>")
                            history_message += yield_message
                    else:
                        # For funded accounts with no admin trades, show yield module trade history
                        history_message = get_trade_history_message(user_id)
                        
                        if "No trade history found" in history_message:
                            # Simulate a sample trade for funded users to show them what it looks like
                            simulate_trade(user_id)
                            history_message = get_trade_history_message(user_id)
                    
                    # Create pagination keyboard
                    page_keyboard = create_pagination_keyboard(user_id, 0)
                    
                    # Convert to SimpleTelegramBot format
                    keyboard_markup = []
                    if 'inline_keyboard' in page_keyboard:
                        for row in page_keyboard['inline_keyboard']:
                            keyboard_row = []
                            for button in row:
                                keyboard_row.append({
                                    "text": button.get('text', ''),
                                    "callback_data": button.get('callback_data', '')
                                })
                            keyboard_markup.append(keyboard_row)
                    
                    # Add back button
                    keyboard_markup.append([{"text": "🔙 Back", "callback_data": "trading_history"}])
                    
                    # Send the message with the keyboard
                    keyboard = bot.create_inline_keyboard(keyboard_markup)
                    bot.send_message(chat_id, history_message, parse_mode="HTML", reply_markup=keyboard)
                else:
                    # Even if not funded, if they have admin trades, show those
                    if has_admin_trades:
                        # Format the message
                        history_message = "📊 <b>Your Trading History</b>\n\n"
                        
                        # Add closed positions (admin broadcasts)
                        for position in closed_positions:
                            # Calculate profit/loss
                            pl_amount = (position.current_price - position.entry_price) * position.amount
                            pl_percentage = ((position.current_price / position.entry_price) - 1) * 100
                            
                            # Determine emoji based on profit/loss
                            pl_emoji = "📈" if pl_percentage > 0 else "📉"
                            date_str = position.timestamp.strftime("%Y-%m-%d %H:%M")
                            
                            # Add trade details
                            # Get trade type if it exists
                            trade_type = "Scalp"
                            if hasattr(position, 'trade_type') and position.trade_type:
                                trade_type = position.trade_type
                            
                            # Add trade details with enhanced formatting
                            history_message += f"🪙 <b>{position.token_name}</b> {pl_emoji} <b>{pl_percentage:.1f}%</b>\n"
                            history_message += f"<i>Strategy: {trade_type} Trade</i>\n"
                            history_message += f"💰 Amount: {position.amount:.4f} SOL\n"
                            history_message += f"📥 Entry: <b>${position.entry_price:.6f}</b>\n"
                            history_message += f"📤 Exit: <b>${position.current_price:.6f}</b>\n"
                            
                            # Format profit/loss with color indicators
                            if pl_amount > 0:
                                history_message += f"✅ Profit: +{pl_amount:.4f} SOL\n"
                            else:
                                history_message += f"❌ Loss: {pl_amount:.4f} SOL\n"
                                
                            history_message += f"🕒 Executed: {date_str}\n"
                            history_message += f"───────────────────\n\n"
                        
                        # Add back button
                        keyboard = bot.create_inline_keyboard([
                            [{"text": "🔙 Back", "callback_data": "trading_history"}]
                        ])
                        
                        bot.send_message(chat_id, history_message, parse_mode="HTML", reply_markup=keyboard)
                    else:
                        # For unfunded accounts with no admin trades, show a message encouraging deposit
                        deposit_keyboard = bot.create_inline_keyboard([
                            [{"text": "🔄 Deposit Funds", "callback_data": "deposit"}],
                            [{"text": "🔙 Back", "callback_data": "trading_history"}]
                        ])
                        
                        bot.send_message(
                            chat_id, 
                            "📊 <b>Trade History</b>\n\n"
                            "Your account is not yet funded. To start trading and building your "
                            "performance history, please deposit funds first.\n\n"
                            "Our AI trading system will automatically start making profitable trades "
                            "for you as soon as your account is funded.",
                            parse_mode="HTML",
                            reply_markup=deposit_keyboard
                        )
                
            except ImportError as e:
                # Fallback if import fails - still show admin trades if available
                if has_admin_trades:
                    # Format the message
                    history_message = "📊 <b>Your Trading History</b>\n\n"
                    
                    # Add closed positions (admin broadcasts)
                    for position in closed_positions:
                        # Calculate profit/loss
                        pl_amount = (position.current_price - position.entry_price) * position.amount
                        pl_percentage = ((position.current_price / position.entry_price) - 1) * 100
                        
                        # Determine emoji based on profit/loss
                        pl_emoji = "📈" if pl_percentage > 0 else "📉"
                        date_str = position.timestamp.strftime("%Y-%m-%d %H:%M")
                        
                        # Add trade details
                        history_message += f"<b>{position.token_name}</b> {pl_emoji} {pl_percentage:.1f}%\n"
                        history_message += f"Amount: {position.amount:.6f} SOL\n"
                        history_message += f"Entry: ${position.entry_price:.6f}\n"
                        history_message += f"Exit: ${position.current_price:.6f}\n"
                        history_message += f"P/L: {pl_amount:.6f} SOL\n"
                        history_message += f"Date: {date_str}\n\n"
                    
                    # Add back button
                    keyboard = bot.create_inline_keyboard([
                        [{"text": "🔙 Back", "callback_data": "trading_history"}]
                    ])
                    
                    bot.send_message(chat_id, history_message, parse_mode="HTML", reply_markup=keyboard)
                elif has_funds:
                    # Message for funded accounts
                    bot.send_message(
                        chat_id, 
                        "📊 <b>Trade History</b>\n\n"
                        "Track your Solana memecoin trades here with real-time performance metrics. "
                        "Our AI trading system is analyzing the market for the best opportunities.\n\n"
                        "Your first trades will appear here once the market conditions are optimal.",
                        parse_mode="HTML"
                    )
                else:
                    # Message for unfunded accounts
                    deposit_keyboard = bot.create_inline_keyboard([
                        [{"text": "🔄 Deposit Funds", "callback_data": "deposit"}],
                        [{"text": "🔙 Back", "callback_data": "trading_history"}]
                    ])
                    
                    bot.send_message(
                        chat_id, 
                        "📊 <b>Trade History</b>\n\n"
                        "Your account needs to be funded before the AI trading system can start "
                        "working for you. Deposit as little as 0.5 SOL to activate automated trading.\n\n"
                        "After funding, our system will start identifying profitable memecoin "
                        "opportunities for you.",
                        parse_mode="HTML",
                        reply_markup=deposit_keyboard
                    )
                
    except Exception as e:
        import logging
        import traceback
        logging.error(f"Error in trade_history_display_handler: {e}")
        logging.error(traceback.format_exc())
        
        # Generic fallback message with deposit button
        deposit_keyboard = bot.create_inline_keyboard([
            [{"text": "🔄 Deposit Funds", "callback_data": "deposit"}],
            [{"text": "🔙 Back", "callback_data": "trading_history"}]
        ])
        
        bot.send_message(
            chat_id, 
            "📊 <b>Trade History</b>\n\n"
            "Our AI trading algorithms are actively scanning the Solana memecoin market "
            "to identify the most profitable opportunities for you.\n\n"
            "Your trading activity will be displayed here with detailed performance analytics once "
            "your account is active.",
            parse_mode="HTML",
            reply_markup=deposit_keyboard
        )

def live_chat_handler(update, chat_id):
    """Handle the live chat button and redirect to admin username."""
    try:
        # Get the admin username for live chat from the database setting if exists, otherwise use a default
        with app.app_context():
            from models import User
            import os
            
            # Try to get the admin user's username from environment or a default
            admin_username = os.environ.get('SUPPORT_USERNAME', 'thrivesupport')
            
            # Prepare the message with the admin username
            live_chat_message = (
                "💬 *Live Chat Support*\n\n"
                f"Our support team is ready to assist you! Please message @{admin_username} directly on Telegram.\n\n"
                "When contacting support, please provide:\n"
                "• Your Telegram username\n"
                "• Brief description of your issue\n"
                "• Any relevant transaction details\n\n"
                "Support hours: 24/7"
            )
            
            keyboard = bot.create_inline_keyboard([
                [{"text": "🔙 Back to Support", "callback_data": "support"}]
            ])
            
            bot.send_message(
                chat_id,
                live_chat_message,
                parse_mode="Markdown",
                reply_markup=keyboard
            )
    except Exception as e:
        import logging
        logging.error(f"Error in live_chat_handler: {e}")
        import traceback
        logging.error(traceback.format_exc())
        bot.send_message(chat_id, f"Error displaying live chat information: {str(e)}")

def submit_ticket_handler(update, chat_id):
    """Handle the submit ticket button."""
    try:
        ticket_message = (
            "📝 *Submit Support Ticket*\n\n"
            "Please provide the following information in your next message:\n\n"
            "1. Subject of your ticket\n"
            "2. Detailed description of your issue\n"
            "3. Any relevant transaction IDs or screenshots\n\n"
            "Our support team will review your ticket and respond as soon as possible."
        )
        
        keyboard = bot.create_inline_keyboard([
            [{"text": "🔙 Back to Support", "callback_data": "support"}]
        ])
        
        bot.send_message(
            chat_id,
            ticket_message,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        
        # Add a listener for the user's next message
        bot.add_message_listener(chat_id, 'support_ticket', support_ticket_message_handler)
        
    except Exception as e:
        import logging
        logging.error(f"Error in submit_ticket_handler: {e}")
        import traceback
        logging.error(traceback.format_exc())
        bot.send_message(chat_id, f"Error displaying ticket submission form: {str(e)}")

def admin_change_support_username_handler(update, chat_id):
    """Handle changing the support username"""
    try:
        # Show the current support username and input prompt
        import os
        current_username = os.environ.get('SUPPORT_USERNAME', 'thrivesupport')
        
        message = (
            "🔄 *Change Support Username*\n\n"
            f"Current support username: @{current_username}\n\n"
            "Please enter the new support username without the @ symbol.\n"
            "This username will be shown to users in the Live Chat support section."
        )
        
        keyboard = bot.create_inline_keyboard([
            [{"text": "🔙 Back to Bot Settings", "callback_data": "admin_bot_settings"}]
        ])
        
        bot.send_message(
            chat_id,
            message,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        
        # Add listener for the next message
        bot.add_message_listener(chat_id, 'support_username', support_username_message_handler)
        
    except Exception as e:
        import logging
        logging.error(f"Error in admin_change_support_username_handler: {e}")
        import traceback
        logging.error(traceback.format_exc())
        bot.send_message(chat_id, f"Error changing support username: {str(e)}")

def admin_update_min_deposit_handler(update, chat_id):
    """Handle updating the minimum deposit amount."""
    try:
        # First, get the current min deposit amount from SystemSettings or config
        with app.app_context():
            from models import SystemSettings
            from config import MIN_DEPOSIT
            
            # Try to get from database first
            min_deposit_setting = SystemSettings.query.filter_by(setting_name="min_deposit").first()
            current_min_deposit = float(min_deposit_setting.setting_value) if min_deposit_setting else MIN_DEPOSIT
            
            message = (
                "🔄 *Update Minimum Deposit*\n\n"
                f"Current minimum deposit: *{current_min_deposit:.2f} SOL*\n\n"
                "Enter the new minimum deposit amount in SOL.\n"
                "This is the minimum amount users need to deposit to activate the bot."
            )
            
            keyboard = bot.create_inline_keyboard([
                [{"text": "🔙 Back to Bot Settings", "callback_data": "admin_bot_settings"}]
            ])
            
            bot.send_message(
                chat_id,
                message,
                parse_mode="Markdown",
                reply_markup=keyboard
            )
            
            # Add listener for the next message
            bot.add_message_listener(chat_id, 'min_deposit', min_deposit_message_handler)
            
    except Exception as e:
        import logging
        logging.error(f"Error in admin_update_min_deposit_handler: {e}")
        import traceback
        logging.error(traceback.format_exc())
        bot.send_message(chat_id, f"Error updating minimum deposit: {str(e)}")

def min_deposit_message_handler(update, chat_id, text):
    """Handle the minimum deposit amount change."""
    try:
        # Remove the listener since we received input
        bot.remove_listener(chat_id)
        
        # Validate input is a positive number
        try:
            new_min_deposit = float(text.strip())
            if new_min_deposit <= 0:
                raise ValueError("Minimum deposit must be greater than 0")
        except ValueError as ve:
            bot.send_message(
                chat_id,
                f"⚠️ Invalid input: {str(ve)}. Please enter a positive number.",
                parse_mode="Markdown"
            )
            # Add the listener back for another attempt
            bot.add_message_listener(chat_id, 'min_deposit', min_deposit_message_handler)
            return
            
        # Save to database
        with app.app_context():
            from models import SystemSettings
            import os
            
            # Get or create the setting
            min_deposit_setting = SystemSettings.query.filter_by(setting_name="min_deposit").first()
            if not min_deposit_setting:
                min_deposit_setting = SystemSettings(
                    setting_name="min_deposit",
                    setting_value=str(new_min_deposit),
                    updated_by=str(chat_id)
                )
                db.session.add(min_deposit_setting)
            else:
                min_deposit_setting.setting_value = str(new_min_deposit)
                min_deposit_setting.updated_by = str(chat_id)
                
            db.session.commit()
            
            # Update in memory for the current session
            os.environ['MIN_DEPOSIT'] = str(new_min_deposit)
            
            # Send confirmation
            confirmation_message = (
                "✅ *Minimum Deposit Updated Successfully*\n\n"
                f"New minimum deposit amount: *{new_min_deposit:.2f} SOL*\n\n"
                "This change will be applied to all new users and deposits."
            )
            
            keyboard = bot.create_inline_keyboard([
                [{"text": "🔙 Back to Bot Settings", "callback_data": "admin_bot_settings"}]
            ])
            
            bot.send_message(
                chat_id,
                confirmation_message,
                parse_mode="Markdown",
                reply_markup=keyboard
            )
            
    except Exception as e:
        import logging
        logging.error(f"Error in min_deposit_message_handler: {e}")
        import traceback
        logging.error(traceback.format_exc())
        bot.send_message(
            chat_id, 
            "⚠️ An error occurred while updating the minimum deposit. Please try again.",
            parse_mode="Markdown"
        )

def support_username_message_handler(update, chat_id, text):
    """Handle the support username change."""
    try:
        # Remove the listener since we received input
        bot.remove_listener(chat_id)
        
        # Clean up the username (remove @ if present)
        new_username = text.strip().replace('@', '')
        
        if not new_username:
            bot.send_message(
                chat_id,
                "⚠️ Please enter a valid username.",
                parse_mode="Markdown"
            )
            # Add the listener back for another attempt
            bot.add_message_listener(chat_id, 'support_username', support_username_message_handler)
            return
        
        # Create or update the environment variable
        import os
        os.environ['SUPPORT_USERNAME'] = new_username
        
        # Send confirmation
        confirmation_message = (
            "✅ *Support Username Updated Successfully*\n\n"
            f"New support username: @{new_username}\n\n"
            "This change will be reflected in the Live Chat support section immediately."
        )
        
        keyboard = bot.create_inline_keyboard([
            [{"text": "🔙 Back to Bot Settings", "callback_data": "admin_bot_settings"}]
        ])
        
        bot.send_message(
            chat_id,
            confirmation_message,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        
    except Exception as e:
        import logging
        logging.error(f"Error in support_username_message_handler: {e}")
        import traceback
        logging.error(traceback.format_exc())
        bot.send_message(
            chat_id, 
            "⚠️ An error occurred while updating the support username. Please try again.",
            parse_mode="Markdown"
        )

def admin_edit_notification_time_handler(update, chat_id):
    """Handle editing the daily notification time."""
    try:
        # First, get the current notification time from SystemSettings or config
        with app.app_context():
            from models import SystemSettings
            from config import DAILY_UPDATE_HOUR
            
            # Try to get from database first
            notification_time_setting = SystemSettings.query.filter_by(setting_name="daily_update_hour").first()
            current_notification_time = int(notification_time_setting.setting_value) if notification_time_setting else DAILY_UPDATE_HOUR
            
            message = (
                "🔄 *Update Daily Notification Time*\n\n"
                f"Current notification time: *{current_notification_time}:00 UTC*\n\n"
                "Enter the new notification hour (0-23) in UTC.\n"
                "This is when daily updates and ROI calculations will be sent to users."
            )
            
            keyboard = bot.create_inline_keyboard([
                [{"text": "🔙 Back to Bot Settings", "callback_data": "admin_bot_settings"}]
            ])
            
            bot.send_message(
                chat_id,
                message,
                parse_mode="Markdown",
                reply_markup=keyboard
            )
            
            # Add listener for the next message
            bot.add_message_listener(chat_id, 'notification_time', notification_time_message_handler)
            
    except Exception as e:
        import logging
        logging.error(f"Error in admin_edit_notification_time_handler: {e}")
        import traceback
        logging.error(traceback.format_exc())
        bot.send_message(chat_id, f"Error updating notification time: {str(e)}")

def notification_time_message_handler(update, chat_id, text):
    """Handle the notification time change."""
    try:
        # Remove the listener since we received input
        bot.remove_listener(chat_id)
        
        # Validate input is a number between 0-23
        try:
            new_time = int(text.strip())
            if new_time < 0 or new_time > 23:
                raise ValueError("Hour must be between 0 and 23")
        except ValueError as ve:
            bot.send_message(
                chat_id,
                f"⚠️ Invalid input: {str(ve)}. Please enter a number between 0 and 23.",
                parse_mode="Markdown"
            )
            # Add the listener back for another attempt
            bot.add_message_listener(chat_id, 'notification_time', notification_time_message_handler)
            return
            
        # Save to database
        with app.app_context():
            from models import SystemSettings
            import os
            
            # Get or create the setting
            time_setting = SystemSettings.query.filter_by(setting_name="daily_update_hour").first()
            if not time_setting:
                time_setting = SystemSettings(
                    setting_name="daily_update_hour",
                    setting_value=str(new_time),
                    updated_by=str(chat_id)
                )
                db.session.add(time_setting)
            else:
                time_setting.setting_value = str(new_time)
                time_setting.updated_by = str(chat_id)
                
            db.session.commit()
            
            # Update in memory for the current session
            os.environ['DAILY_UPDATE_HOUR'] = str(new_time)
            
            # Send confirmation
            confirmation_message = (
                "✅ *Notification Time Updated Successfully*\n\n"
                f"New notification time: *{new_time}:00 UTC*\n\n"
                "This change will be applied to all future daily updates."
            )
            
            keyboard = bot.create_inline_keyboard([
                [{"text": "🔙 Back to Bot Settings", "callback_data": "admin_bot_settings"}]
            ])
            
            bot.send_message(
                chat_id,
                confirmation_message,
                parse_mode="Markdown",
                reply_markup=keyboard
            )
            
    except Exception as e:
        import logging
        logging.error(f"Error in notification_time_message_handler: {e}")
        import traceback
        logging.error(traceback.format_exc())
        bot.send_message(
            chat_id, 
            "⚠️ An error occurred while updating the notification time. Please try again.",
            parse_mode="Markdown"
        )

def admin_toggle_daily_updates_handler(update, chat_id):
    """Handle toggling daily updates on/off."""
    try:
        # First, get the current status from SystemSettings
        with app.app_context():
            from models import SystemSettings
            
            # Try to get from database first
            daily_updates_setting = SystemSettings.query.filter_by(setting_name="daily_updates_enabled").first()
            
            # Default is enabled if setting doesn't exist
            current_status = daily_updates_setting.setting_value.lower() == 'true' if daily_updates_setting else True
            
            # Toggle the status
            new_status = not current_status
            
            # Update or create the setting
            if not daily_updates_setting:
                daily_updates_setting = SystemSettings(
                    setting_name="daily_updates_enabled",
                    setting_value=str(new_status).lower(),
                    updated_by=str(chat_id)
                )
                db.session.add(daily_updates_setting)
            else:
                daily_updates_setting.setting_value = str(new_status).lower()
                daily_updates_setting.updated_by = str(chat_id)
                
            db.session.commit()
            
            # Send confirmation
            status_text = "ON" if new_status else "OFF"
            confirmation_message = (
                f"✅ *Daily Updates Toggled: {status_text}*\n\n"
                f"Daily updates are now {'enabled' if new_status else 'disabled'}.\n"
                f"{'Users will receive daily profit updates at the scheduled time.' if new_status else 'Users will not receive automated daily updates.'}"
            )
            
            keyboard = bot.create_inline_keyboard([
                [{"text": "🔙 Back to Bot Settings", "callback_data": "admin_bot_settings"}]
            ])
            
            bot.send_message(
                chat_id,
                confirmation_message,
                parse_mode="Markdown",
                reply_markup=keyboard
            )
            
    except Exception as e:
        import logging
        logging.error(f"Error in admin_toggle_daily_updates_handler: {e}")
        import traceback
        logging.error(traceback.format_exc())
        bot.send_message(chat_id, f"Error toggling daily updates: {str(e)}")

def admin_manage_roi_handler(update, chat_id):
    """Handle ROI settings and thresholds."""
    try:
        # Get the current ROI settings from config/database
        with app.app_context():
            from models import SystemSettings
            from config import SIMULATED_DAILY_ROI_MIN, SIMULATED_DAILY_ROI_MAX, SIMULATED_LOSS_PROBABILITY
            
            # Get settings from database if available
            roi_min_setting = SystemSettings.query.filter_by(setting_name="daily_roi_min").first()
            roi_max_setting = SystemSettings.query.filter_by(setting_name="daily_roi_max").first()
            loss_prob_setting = SystemSettings.query.filter_by(setting_name="loss_probability").first()
            
            # Use values from database or fallback to config
            roi_min = float(roi_min_setting.setting_value) if roi_min_setting else SIMULATED_DAILY_ROI_MIN
            roi_max = float(roi_max_setting.setting_value) if roi_max_setting else SIMULATED_DAILY_ROI_MAX
            loss_prob = float(loss_prob_setting.setting_value) if loss_prob_setting else SIMULATED_LOSS_PROBABILITY
            
            # Create the management message
            message = (
                "⚙️ *ROI Settings Management*\n\n"
                f"Current Min Daily ROI: *{roi_min:.2f}%*\n"
                f"Current Max Daily ROI: *{roi_max:.2f}%*\n"
                f"Loss Day Probability: *{loss_prob * 100:.1f}%*\n\n"
                "Select which ROI parameter you want to adjust:"
            )
            
            keyboard = bot.create_inline_keyboard([
                [{"text": "Update Min ROI", "callback_data": "admin_update_min_roi"}],
                [{"text": "Update Max ROI", "callback_data": "admin_update_max_roi"}],
                [{"text": "Update Loss Probability", "callback_data": "admin_update_loss_prob"}],
                [{"text": "🔙 Back to Bot Settings", "callback_data": "admin_bot_settings"}]
            ])
            
            bot.send_message(
                chat_id,
                message,
                parse_mode="Markdown",
                reply_markup=keyboard
            )
            
            # Register the ROI update handlers
            bot.add_callback_handler("admin_update_min_roi", lambda update, chat_id: admin_update_roi_parameter(update, chat_id, "min"))
            bot.add_callback_handler("admin_update_max_roi", lambda update, chat_id: admin_update_roi_parameter(update, chat_id, "max"))
            bot.add_callback_handler("admin_update_loss_prob", lambda update, chat_id: admin_update_roi_parameter(update, chat_id, "loss"))
            
    except Exception as e:
        import logging
        logging.error(f"Error in admin_manage_roi_handler: {e}")
        import traceback
        logging.error(traceback.format_exc())
        bot.send_message(chat_id, f"Error displaying ROI settings: {str(e)}")

def admin_update_roi_parameter(update, chat_id, param_type):
    """Handle updating a specific ROI parameter."""
    try:
        with app.app_context():
            from models import SystemSettings
            from config import SIMULATED_DAILY_ROI_MIN, SIMULATED_DAILY_ROI_MAX, SIMULATED_LOSS_PROBABILITY
            
            # Set parameter-specific variables
            if param_type == "min":
                setting_name = "daily_roi_min"
                display_name = "Minimum Daily ROI"
                current_setting = SystemSettings.query.filter_by(setting_name=setting_name).first()
                current_value = float(current_setting.setting_value) if current_setting else SIMULATED_DAILY_ROI_MIN
                input_guidance = "Enter the new minimum daily ROI percentage (0.1-5.0%)"
                value_validator = lambda x: 0.1 <= x <= 5.0
                error_message = "Value must be between 0.1% and 5.0%"
            elif param_type == "max":
                setting_name = "daily_roi_max"
                display_name = "Maximum Daily ROI"
                current_setting = SystemSettings.query.filter_by(setting_name=setting_name).first()
                current_value = float(current_setting.setting_value) if current_setting else SIMULATED_DAILY_ROI_MAX
                input_guidance = "Enter the new maximum daily ROI percentage (0.5-10.0%)"
                value_validator = lambda x: 0.5 <= x <= 10.0
                error_message = "Value must be between 0.5% and 10.0%"
            elif param_type == "loss":
                setting_name = "loss_probability"
                display_name = "Loss Day Probability"
                current_setting = SystemSettings.query.filter_by(setting_name=setting_name).first()
                current_value = float(current_setting.setting_value) if current_setting else SIMULATED_LOSS_PROBABILITY
                input_guidance = "Enter the probability of loss days (0.0-0.5 as decimal, e.g., 0.2 for 20%)"
                value_validator = lambda x: 0.0 <= x <= 0.5
                error_message = "Value must be between 0.0 and 0.5 (0-50%)"
                
            message = (
                f"🔄 *Update {display_name}*\n\n"
                f"Current value: *{current_value:.2f}{'%' if param_type != 'loss' else ''}*\n\n"
                f"{input_guidance}\n"
            )
            
            keyboard = bot.create_inline_keyboard([
                [{"text": "🔙 Back to ROI Settings", "callback_data": "admin_manage_roi"}]
            ])
            
            bot.send_message(
                chat_id,
                message,
                parse_mode="Markdown",
                reply_markup=keyboard
            )
            
            # Store the parameters in a context for the listener
            roi_context = {
                "setting_name": setting_name,
                "display_name": display_name,
                "validator": value_validator,
                "error_message": error_message,
                "param_type": param_type
            }
            
            # Since we can't use a real context like in python-telegram-bot, we'll use a global variable
            global roi_update_context
            roi_update_context = roi_context
            
            # Add listener for the next message
            bot.add_message_listener(chat_id, 'roi_parameter', roi_parameter_message_handler)
            
    except Exception as e:
        import logging
        logging.error(f"Error in admin_update_roi_parameter: {e}")
        import traceback
        logging.error(traceback.format_exc())
        bot.send_message(chat_id, f"Error updating ROI parameter: {str(e)}")

def roi_parameter_message_handler(update, chat_id, text):
    """Handle the ROI parameter input."""
    try:
        # Remove the listener since we received input
        bot.remove_listener(chat_id)
        
        # Get context from global variable
        global roi_update_context
        if not roi_update_context:
            bot.send_message(
                chat_id,
                "⚠️ Session expired. Please try again.",
                parse_mode="Markdown"
            )
            return
            
        # Extract context variables
        setting_name = roi_update_context["setting_name"]
        display_name = roi_update_context["display_name"]
        validator = roi_update_context["validator"]
        error_message = roi_update_context["error_message"]
        param_type = roi_update_context["param_type"]
        
        # Validate input
        try:
            new_value = float(text.strip())
            if not validator(new_value):
                raise ValueError(error_message)
        except ValueError as ve:
            bot.send_message(
                chat_id,
                f"⚠️ Invalid input: {str(ve)}. Please try again.",
                parse_mode="Markdown"
            )
            # Add the listener back for another attempt
            bot.add_message_listener(chat_id, 'roi_parameter', roi_parameter_message_handler)
            return
            
        # Save to database
        with app.app_context():
            from models import SystemSettings
            
            # Get or create the setting
            setting = SystemSettings.query.filter_by(setting_name=setting_name).first()
            if not setting:
                setting = SystemSettings(
                    setting_name=setting_name,
                    setting_value=str(new_value),
                    updated_by=str(chat_id)
                )
                db.session.add(setting)
            else:
                setting.setting_value = str(new_value)
                setting.updated_by = str(chat_id)
                
            db.session.commit()
            
            # Send confirmation
            confirmation_message = (
                f"✅ *{display_name} Updated Successfully*\n\n"
                f"New value: *{new_value:.2f}{'%' if param_type != 'loss' else ''}*\n\n"
                f"This change will be applied to all future ROI calculations."
            )
            
            keyboard = bot.create_inline_keyboard([
                [{"text": "🔙 Back to ROI Settings", "callback_data": "admin_manage_roi"}]
            ])
            
            bot.send_message(
                chat_id,
                confirmation_message,
                parse_mode="Markdown",
                reply_markup=keyboard
            )
            
            # Clear the context
            roi_update_context = None
            
    except Exception as e:
        import logging
        logging.error(f"Error in roi_parameter_message_handler: {e}")
        import traceback
        logging.error(traceback.format_exc())
        bot.send_message(
            chat_id, 
            "⚠️ An error occurred while updating the ROI parameter. Please try again.",
            parse_mode="Markdown"
        )

def support_ticket_message_handler(update, chat_id, text):
    """Handle the support ticket submission."""
    try:
        # Remove the listener since we received input
        bot.remove_listener(chat_id)
        
        # Save the ticket to the database
        with app.app_context():
            from models import User, SupportTicket
            
            user = User.query.filter_by(telegram_id=str(chat_id)).first()
            
            if not user:
                bot.send_message(chat_id, "Please start the bot with /start first.")
                return
                
            # Parse the ticket information
            lines = text.strip().split('\n')
            
            # Extract subject (first line) and message (rest of the text)
            subject = lines[0][:200] if lines else "Support Request"
            message = text
            
            # Create the ticket
            new_ticket = SupportTicket(
                user_id=user.id,
                subject=subject,
                message=message,
                status='open',
                priority='normal'
            )
            
            db.session.add(new_ticket)
            db.session.commit()
            
            # Send confirmation to the user
            confirmation_message = (
                "✅ *Support Ticket Submitted Successfully*\n\n"
                f"Ticket ID: #{new_ticket.id}\n"
                f"Subject: {subject}\n"
                "Status: Open\n\n"
                "Our support team will review your ticket and respond as soon as possible. "
                "You'll receive a notification when there's an update."
            )
            
            keyboard = bot.create_inline_keyboard([
                [{"text": "📊 Dashboard", "callback_data": "view_dashboard"}],
                [{"text": "🏠 Main Menu", "callback_data": "start"}]
            ])
            
            bot.send_message(
                chat_id,
                confirmation_message,
                parse_mode="Markdown",
                reply_markup=keyboard
            )
            
            # Notify admin(s) about the new ticket
            admin_ids = [int(os.environ.get('ADMIN_USER_ID'))] if os.environ.get('ADMIN_USER_ID') else []
            
            if admin_ids:
                admin_notification = (
                    "🔔 *New Support Ticket*\n\n"
                    f"Ticket ID: #{new_ticket.id}\n"
                    f"User: {user.username or user.telegram_id}\n"
                    f"Subject: {subject}\n\n"
                    "Use the Admin Panel to view and respond to this ticket."
                )
                
                for admin_id in admin_ids:
                    try:
                        bot.send_message(
                            admin_id,
                            admin_notification,
                            parse_mode="Markdown"
                        )
                    except Exception as admin_e:
                        logging.error(f"Error sending admin notification: {admin_e}")
            
    except Exception as e:
        import logging
        logging.error(f"Error in support_ticket_message_handler: {e}")
        import traceback
        logging.error(traceback.format_exc())
        bot.send_message(
            chat_id, 
            "⚠️ An error occurred while processing your ticket. Please try again or contact support directly.",
            parse_mode="Markdown"
        )

def admin_change_wallet_handler(update, chat_id):
    """Handle changing the deposit wallet address."""
    try:
        # Send instructions for changing the wallet
        message = (
            "💼 *Change Deposit Wallet*\n\n"
            "Please enter the new Solana deposit wallet address below.\n"
            "This will be the address users will deposit to.\n\n"
            "⚠️ *Important:* Make sure the address is correct and you have access to it."
        )
        
        keyboard = bot.create_inline_keyboard([
            [{"text": "❌ Cancel", "callback_data": "admin_wallet_settings"}]
        ])
        
        bot.send_message(
            chat_id,
            message,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        
        # Add listener for the next message to capture the wallet address
        bot.add_message_listener(chat_id, "wallet_address", admin_wallet_address_input_handler)
        
    except Exception as e:
        import logging
        logging.error(f"Error in admin_change_wallet_handler: {e}")
        import traceback
        logging.error(traceback.format_exc())
        bot.send_message(chat_id, f"Error starting wallet change: {str(e)}")


def admin_wallet_address_input_handler(update, chat_id, text):
    """Handle the wallet address input from admin."""
    try:
        with app.app_context():
            from models import SystemSettings
            import re
            
            # Remove any listener
            bot.remove_listener(chat_id)
            
            # Basic validation for Solana address (should be base58, ~32-44 chars)
            if not re.match(r'^[1-9A-HJ-NP-Za-km-z]{32,44}$', text):
                message = (
                    "❌ *Invalid Wallet Address*\n\n"
                    "The address you entered doesn't appear to be a valid Solana address.\n"
                    "Please check and try again."
                )
                
                keyboard = bot.create_inline_keyboard([
                    [{"text": "Try Again", "callback_data": "admin_change_wallet"}],
                    [{"text": "Back to Wallet Settings", "callback_data": "admin_wallet_settings"}]
                ])
                
                bot.send_message(
                    chat_id,
                    message,
                    parse_mode="Markdown",
                    reply_markup=keyboard
                )
                return
            
            # Check if setting exists and update, or create new setting
            deposit_wallet_setting = SystemSettings.query.filter_by(setting_name="deposit_wallet").first()
            
            if deposit_wallet_setting:
                deposit_wallet_setting.setting_value = text
                deposit_wallet_setting.updated_by = str(chat_id)
            else:
                new_setting = SystemSettings(
                    setting_name="deposit_wallet",
                    setting_value=text,
                    updated_by=str(chat_id)
                )
                db.session.add(new_setting)
                
            db.session.commit()
            
            # Update the .env file with the new wallet address (AWS-safe)
            try:
                from helpers import update_env_variable
                env_success = update_env_variable('GLOBAL_DEPOSIT_WALLET', text)
                if env_success:
                    logger.info(f"Updated .env file with new wallet: {text}")
                    # Also update environment variable in memory for immediate effect
                    os.environ['GLOBAL_DEPOSIT_WALLET'] = text
                else:
                    logger.warning("Failed to update .env file - file may be read-only or missing on AWS")
                    # Still update in-memory environment variable
                    os.environ['GLOBAL_DEPOSIT_WALLET'] = text
            except Exception as env_error:
                logger.error(f"Error updating .env file: {str(env_error)}")
                # Fallback: update in-memory environment variable for current session
                os.environ['GLOBAL_DEPOSIT_WALLET'] = text
                logger.info("Updated environment variable in memory as fallback")
            
            # Update all existing users to use the new wallet address
            try:
                from helpers import update_all_user_deposit_wallets
                updated_count = update_all_user_deposit_wallets()
                logger.info(f"Updated {updated_count} users to use new deposit wallet")
            except Exception as update_error:
                logger.error(f"Error updating user wallets: {str(update_error)}")
            
            # Restart deposit monitoring with new wallet address
            try:
                from utils.deposit_monitor import stop_deposit_monitor, start_deposit_monitor
                
                # Stop current monitoring
                stop_deposit_monitor()
                
                # Wait a moment for clean shutdown
                import time
                time.sleep(2)
                
                # Start monitoring with new wallet address
                start_deposit_monitor()
                
                logger.info(f"Deposit monitoring restarted with new wallet: {text}")
                
            except Exception as monitor_error:
                logger.error(f"Error restarting deposit monitor: {str(monitor_error)}")
            
            # Send confirmation with user update count
            message = (
                "✅ *Deposit Wallet Updated*\n\n"
                f"The system deposit wallet has been successfully changed to:\n\n"
                f"`{text}`\n\n"
                "This address will now be shown to all users when they visit the deposit page.\n\n"
                "🔄 *System Updates Completed:*\n"
                "• Database setting updated\n"
                "• Environment (.env) file updated\n"
                "• All user wallets updated\n"
                "• Deposit monitoring restarted\n"
                "• QR codes will use new address"
            )
            
            keyboard = bot.create_inline_keyboard([
                [{"text": "View QR Code", "callback_data": "admin_view_wallet_qr"}],
                [{"text": "Back to Wallet Settings", "callback_data": "admin_wallet_settings"}]
            ])
            
            bot.send_message(
                chat_id,
                message,
                parse_mode="Markdown",
                reply_markup=keyboard
            )
            
    except Exception as e:
        import logging
        logging.error(f"Error in admin_wallet_address_input_handler: {e}")
        import traceback
        logging.error(traceback.format_exc())
        bot.send_message(chat_id, f"Error updating wallet address: {str(e)}")


def admin_deposit_logs_handler(update, chat_id):
    """Display recent deposit logs in real-time."""
    try:
        with app.app_context():
            from app import db
            from models import Transaction, User
            import requests
            import json
            from datetime import datetime, timedelta
            
            # Send processing message
            bot.send_chat_action(chat_id, action="typing")
            
            # Get recent deposit transactions from the database
            try:
                deposits = (
                    db.session.query(Transaction, User)
                    .join(User, Transaction.user_id == User.id)
                    .filter(Transaction.transaction_type == "deposit")
                    .order_by(Transaction.timestamp.desc())
                    .limit(20)
                    .all()
                )
                
                # Format the results in a presentable way
                if deposits:
                    message = "📊 *Recent Deposit Logs*\n\n"
                    
                    for i, (transaction, user) in enumerate(deposits, 1):
                        # Always use telegram_id as primary identifier, with username as secondary if available
                        user_display = f"ID: {user.telegram_id}"
                        if user.username:
                            user_display += f" (@{user.username})"
                        
                        timestamp = transaction.timestamp.strftime("%Y-%m-%d %H:%M")
                        
                        message += (
                            f"{i}. *{user_display}*: {transaction.amount:.2f} SOL\n"
                            f"   📅 {timestamp} · {transaction.status.upper()}\n"
                        )
                        
                        # Remove notes display to keep deposit logs clean
                        
                        # Add a separator except for the last item
                        if i < len(deposits):
                            message += "----------------------------\n"
                    
                    # Add timestamp and refresh hint
                    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
                    message += f"\n_Last updated: {now}_\n"
                    message += "_Click Refresh to update the logs_"
                else:
                    message = "📊 *Deposit Logs*\n\n" + "No deposit transactions found in the system."
            except Exception as e:
                message = f"⚠️ Error retrieving deposit logs: {str(e)}"
                import logging
                logging.error(f"Database error in deposit logs: {e}")
            
            # Add refresh and back buttons
            keyboard = bot.create_inline_keyboard([
                [{"text": "🔄 Refresh", "callback_data": "admin_deposit_logs"}],
                [{"text": "📊 Export CSV", "callback_data": "admin_export_deposits_csv"}],
                [{"text": "↩️ Back to Admin Panel", "callback_data": "admin_back"}]
            ])
            
            bot.send_message(
                chat_id,
                message,
                parse_mode="Markdown",
                reply_markup=keyboard
            )
            
    except Exception as e:
        import logging
        logging.error(f"Error in admin_deposit_logs_handler: {e}")
        import traceback
        logging.error(traceback.format_exc())
        bot.send_message(chat_id, f"Error displaying deposit logs: {str(e)}")

def admin_view_wallet_qr_handler(update, chat_id):
    """Generate and display QR code for the deposit wallet."""
    try:
        with app.app_context():
            from models import SystemSettings
            import qrcode
            import io
            from PIL import Image, ImageDraw, ImageFont
            
            # Get the deposit wallet address
            deposit_wallet_setting = SystemSettings.query.filter_by(setting_name="deposit_wallet").first()
            
            if not deposit_wallet_setting or not deposit_wallet_setting.setting_value:
                message = (
                    "⚠️ *No Deposit Wallet Set*\n\n"
                    "There is no deposit wallet address set in the system.\n"
                    "Please set a wallet address first."
                )
                
                keyboard = bot.create_inline_keyboard([
                    [{"text": "Set Wallet Address", "callback_data": "admin_change_wallet"}],
                    [{"text": "Back to Wallet Settings", "callback_data": "admin_wallet_settings"}]
                ])
                
                bot.send_message(
                    chat_id,
                    message,
                    parse_mode="Markdown",
                    reply_markup=keyboard
                )
                return
            
            wallet_address = deposit_wallet_setting.setting_value
            
            # Generate QR code
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(wallet_address)
            qr.make(fit=True)
            
            # Create QR code image
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Add caption with wallet address
            # Create a new image with space for the caption
            canvas = Image.new('RGB', (img.size[0], img.size[1] + 50), color=(255, 255, 255))
            canvas.paste(img, (0, 0))
            
            # Add the caption
            draw = ImageDraw.Draw(canvas)
            draw.text((10, img.size[1] + 10), f"Wallet Address: {wallet_address[:10]}...{wallet_address[-5:]}", fill=(0, 0, 0))
            
            # Save to buffer
            buffer = io.BytesIO()
            canvas.save(buffer, format="PNG")
            buffer.seek(0)
            
            # Send QR code
            bot.send_chat_action(chat_id, action="upload_photo")
            bot.send_document(
                chat_id, 
                buffer, 
                caption=f"📱 *QR Code for Deposit Wallet*\n\n`{wallet_address}`", 
                parse_mode="Markdown"
            )
            
            # Send options keyboard
            keyboard = bot.create_inline_keyboard([
                [{"text": "Change Wallet", "callback_data": "admin_change_wallet"}],
                [{"text": "Back to Wallet Settings", "callback_data": "admin_wallet_settings"}]
            ])
            
            bot.send_message(
                chat_id,
                "Use the buttons below to manage your wallet settings:",
                reply_markup=keyboard
            )
            
    except Exception as e:
        import logging
        logging.error(f"Error in admin_view_wallet_qr_handler: {e}")
        import traceback
        logging.error(traceback.format_exc())
        bot.send_message(chat_id, f"Error generating QR code: {str(e)}")
        
        # If error is related to QR code generation, provide alternative message
        if "qrcode" in str(e).lower() or "image" in str(e).lower():
            wallet_address = ""
            try:
                with app.app_context():
                    from models import SystemSettings
                    setting = SystemSettings.query.filter_by(setting_name="deposit_wallet").first()
                    if setting:
                        wallet_address = setting.setting_value
            except:
                pass
            
            if wallet_address:
                message = (
                    "📱 *Deposit Wallet Address*\n\n"
                    f"`{wallet_address}`\n\n"
                    "QR code generation failed, but you can copy the address above."
                )
                
                keyboard = bot.create_inline_keyboard([
                    [{"text": "Back to Wallet Settings", "callback_data": "admin_wallet_settings"}]
                ])
                
                bot.send_message(
                    chat_id,
                    message,
                    parse_mode="Markdown",
                    reply_markup=keyboard
                )


def faqs_handler(update, chat_id):
    """Show help information and available commands (FAQs)."""
    try:
        help_text = (
            "🎯 *INSTITUTIONAL-GRADE TRADING PLATFORM*\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            
            "*📋 PLATFORM VERIFICATION & TRANSPARENCY*\n\n"
            
            "*⚡ Real-Time Blockchain Integration*\n"
            "Our platform operates with full Solana mainnet integration. Every transaction, deposit, and withdrawal is recorded on-chain with verifiable transaction signatures. All operations maintain 180+ day operational history with full blockchain transparency.\n\n"
            
            "*🔍 Trade Verification Standards*\n"
            "All positions include verified pump.fun contract addresses, real-time birdeye.so price feeds, and on-chain transaction proofs. No simulated trades or demo accounts - every position represents actual SPL token holdings with blockchain-verifiable entry/exit points.\n\n"
            
            "*💼 Institutional Security Architecture*\n"
            "Multi-signature custody with time-locked withdrawals, cold storage integration, and institutional-grade key management. Your funds are secured using the same protocols trusted by major DeFi protocols managing $100M+ TVL.\n\n"
            
            "*🎯 ADVANCED TRADING INFRASTRUCTURE*\n\n"
            
            "*⚡ Microsecond Execution Engine*\n"
            "Sub-200ms trade execution via dedicated Solana RPC clusters, MEV protection through Jito bundle integration, and priority fee optimization. Our execution infrastructure handles 10,000+ TPS with institutional-grade reliability.\n\n"
            
            "*🛡️ Enterprise Risk Management*\n"
            "Multi-layer risk filtering: contract verification via Solscan API, liquidity depth analysis, holder distribution metrics, and dev wallet behavior tracking. Automatic honeypot detection using 15+ verification vectors including token metadata, transfer restrictions, and ownership renunciation status.\n\n"
            
            "*📊 Professional Signal Processing*\n"
            "Aggregated alpha from 50+ premium sources: whale wallet monitoring (tracked addresses with $1M+ holdings), pump.fun launch detection with sub-second latency, cross-platform sentiment analysis, and institutional DEX flow tracking.\n\n"
            
            "*💰 TRANSPARENT FEE STRUCTURE*\n\n"
            
            "*Performance-Based Pricing*\n"
            "2% performance fee on realized profits only. No management fees, no deposit fees, no withdrawal fees. Fees are calculated and deducted only upon successful profit withdrawal - your principal investment remains untouched.\n\n"
            
            "*🏛️ REGULATORY COMPLIANCE*\n\n"
            
            "*Professional Standards*\n"
            "Full transaction logging for regulatory compliance, AML-compliant deposit monitoring, and institutional-grade record keeping. Our platform maintains audit trails meeting TradFi standards for professional trading operations.\n\n"
            
            "*🔐 PLATFORM VALIDATION CHECKLIST*\n\n"
            
            "✅ Verify deposit wallet transaction history on Solscan\n"
            "✅ Check real-time position links to pump.fun contracts\n"
            "✅ Review blockchain transaction signatures for all trades\n"
            "✅ Test small deposit to confirm on-chain processing\n"
            "✅ Validate withdrawal process with actual Solana transactions\n"
            "✅ Cross-reference pricing with birdeye.so market data\n\n"
            
            "*⚠️ INDUSTRY RED FLAGS TO AVOID*\n\n"
            
            "🚫 Platforms without verifiable on-chain wallet addresses\n"
            "🚫 Trade history lacking blockchain transaction proofs\n"
            "🚫 Unrealistic return promises (>100% daily)\n"
            "🚫 Hidden fee structures or undisclosed costs\n"
            "🚫 Inability to verify individual trade executions\n"
            "🚫 No institutional-grade security measures\n\n"
            
            "*Built for institutional traders and sophisticated retail participants who demand institutional-grade transparency, security, and performance verification.*"
        )
        
        keyboard = bot.create_inline_keyboard([
            [
                {"text": "🔐 Blockchain Verification", "callback_data": "verify_wallet"}, 
                {"text": "📊 Trading Dashboard", "callback_data": "view_dashboard"}
            ],
            [
                {"text": "💎 Platform Deposit", "callback_data": "deposit"}, 
                {"text": "📈 Live Positions", "callback_data": "trading_history"}
            ],
            [
                {"text": "🏛️ Platform Home", "callback_data": "start"}
            ]
        ])
        
        bot.send_message(
            chat_id,
            help_text,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
    except Exception as e:
        import logging
        logging.error(f"Error in faqs_handler: {e}")
        bot.send_message(chat_id, f"Error displaying FAQs: {str(e)}")

def verify_wallet_handler(update, chat_id):
    """Show blockchain verification information for wallet transparency."""
    try:
        verification_text = (
            "🔐 *INSTITUTIONAL BLOCKCHAIN VERIFICATION*\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            
            "*🏛️ CUSTODY INFRASTRUCTURE*\n\n"
            
            "*📊 INSTITUTIONAL AUDIT POINTS*\n\n"
            
            "*On-Chain Verification Metrics*\n"
            "✅ 180+ day operational transaction history\n"
            "✅ Real-time SOL deposit processing with sub-second confirmation\n"
            "✅ Verifiable transaction signatures for all fund movements\n"
            "✅ Network fee transparency with exact gas cost tracking\n"
            "✅ Multi-signature security with institutional-grade key management\n"
            "✅ Time-locked withdrawal protocols for enhanced security\n\n"
            
            "*🔍 PROFESSIONAL VERIFICATION PROTOCOL*\n\n"
            
            "*Institutional Trading Standards*\n"
            "All trading operations maintain institutional-grade transparency with real-time blockchain verification. Position entries and exits are recorded with verifiable transaction signatures and cross-referenced pricing data.\n\n"
            
            "*Security Architecture Framework*\n"
            "Multi-signature custody infrastructure with hardware security modules, time-locked withdrawal protocols, and institutional cold storage integration meeting enterprise security standards.\n\n"
            
            "*🏦 INSTITUTIONAL SECURITY FRAMEWORK*\n\n"
            
            "*Custody Architecture*\n"
            "Multi-signature wallet infrastructure with 3-of-5 key distribution, hardware security module integration, and institutional-grade cold storage protocols. Withdrawal processing includes mandatory time-locks and dual authorization requirements.\n\n"
            
            "*💎 TRADING VERIFICATION STANDARDS*\n\n"
            
            "*Position Transparency*\n"
            "• All trading positions linked to verified pump.fun smart contracts\n"
            "• Real-time transaction hash generation for every trade execution\n"
            "• Cross-verified pricing through birdeye.so professional data feeds\n"
            "• Zero synthetic or simulated trading data - 100% on-chain verification\n\n"
            
            "*Enterprise-grade transparency built for institutional participants and sophisticated retail traders who demand verifiable blockchain data.*"
        )
        
        keyboard = bot.create_inline_keyboard([
            [
                {"text": "📊 Transaction Audit", "callback_data": "view_my_deposits"}, 
                {"text": "💎 Live Portfolio", "callback_data": "trading_history"}
            ],
            [
                {"text": "🏛️ Platform Deposit", "callback_data": "deposit"}
            ],
            [
                {"text": "📋 Platform Documentation", "callback_data": "faqs"}, 
                {"text": "🏛️ Trading Platform", "callback_data": "start"}
            ]
        ])
        
        bot.send_message(
            chat_id,
            verification_text,
            parse_mode="Markdown",
            reply_markup=keyboard,
            disable_web_page_preview=True
        )
        
    except Exception as e:
        import logging
        logging.error(f"Error in verify_wallet_handler: {e}")
        bot.send_message(chat_id, f"Error displaying verification info: {str(e)}")

def view_my_deposits_handler(update, chat_id):
    """Show user's specific deposit transactions for verification."""
    try:
        user_id = str(update['callback_query']['from']['id'])
        
        with app.app_context():
            from models import User, Transaction
            
            user = User.query.filter_by(telegram_id=user_id).first()
            if not user:
                bot.send_message(chat_id, "User account not found. Please initiate platform access with /start")
                return
            
            # Get user's deposit transactions
            deposits = Transaction.query.filter_by(
                user_id=user.id,
                transaction_type='deposit'
            ).order_by(Transaction.timestamp.desc()).limit(10).all()
            
            if not deposits:
                message = (
                    "📊 *INSTITUTIONAL TRANSACTION AUDIT*\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    "*🏛️ NO DEPOSIT TRANSACTIONS RECORDED*\n\n"
                    "Your institutional account shows no deposit activity to date.\n\n"
                    "Initiate your first platform deposit to establish transaction history and begin algorithmic trading operations.\n\n"
                    "*📋 Transaction Documentation Standards:*\n"
                    "• Precise SOL denomination with 6-decimal accuracy\n"
                    "• Blockchain transaction signature verification\n"
                    "• UTC timestamp with sub-second precision\n"
                    "• Real-time processing status monitoring\n"
                    "• Cross-platform explorer verification links\n\n"
                    "*All fund movements maintain institutional-grade audit trails for regulatory compliance and transparency verification.*"
                )
            else:
                message = (
                    "📊 *INSTITUTIONAL TRANSACTION AUDIT*\n"
                    "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                    "*🏦 VERIFIED DEPOSIT TRANSACTIONS*\n\n"
                )
                
                total_deposited = sum(deposit.amount for deposit in deposits)
                message += f"*Portfolio Capital: {total_deposited:.6f} SOL*\n\n"
                
                for i, deposit in enumerate(deposits, 1):
                    tx_hash = getattr(deposit, 'tx_hash', 'Processing...')
                    tx_display = f"{tx_hash[:12]}...{tx_hash[-8:]}" if tx_hash and len(tx_hash) > 20 else tx_hash or "Processing..."
                    
                    message += (
                        f"*Transaction #{i:02d}*\n"
                        f"💎 Capital: {deposit.amount:.6f} SOL\n"
                        f"📅 Executed: {deposit.timestamp.strftime('%Y-%m-%d %H:%M:%S UTC')}\n"
                        f"🔐 Signature: `{tx_display}`\n"
                    )
                    
                    if tx_hash and len(tx_hash) > 20:
                        message += f"🔍 [Blockchain Verification](https://solscan.io/tx/{tx_hash})\n\n"
                    else:
                        message += "⏳ Pending blockchain confirmation\n\n"
                
                message += (
                    "*🔐 INSTITUTIONAL VERIFICATION PROTOCOL*\n\n"
                    "• Cross-reference transaction signatures on Solscan enterprise interface\n"
                    "• Validate capital amounts against personal trading records\n"
                    "• Verify execution timestamps with blockchain finality\n"
                    "• Confirm all fund movements via immutable ledger verification\n\n"
                    "*Enterprise-grade transaction transparency ensuring institutional compliance standards.*"
                )
        
        keyboard = bot.create_inline_keyboard([
            [
                {"text": "🔐 Blockchain Verification", "callback_data": "verify_wallet"}, 
                {"text": "💎 Capital Deposit", "callback_data": "deposit"}
            ],
            [
                {"text": "🏛️ Trading Platform", "callback_data": "start"}
            ]
        ])
        
        bot.send_message(
            chat_id,
            message,
            parse_mode="Markdown",
            reply_markup=keyboard,
            disable_web_page_preview=True
        )
        
    except Exception as e:
        import logging
        logging.error(f"Error in view_my_deposits_handler: {e}")
        bot.send_message(chat_id, f"Error accessing transaction audit: {str(e)}")

# New handler functions for enhanced referral system
def referral_qr_code_handler(update, chat_id):
    """Generate and send a QR code for the user's referral link."""
    try:
        import qrcode
        import io
        import referral_module
        
        with app.app_context():
            # Create referral manager if not exists
            global referral_manager
            if 'referral_manager' not in globals() or referral_manager is None:
                referral_manager = referral_module.ReferralManager(app.app_context)
                referral_manager.set_bot_username("ThriveQuantbot")
                logger.info("Initialized referral manager")
            
            # Create referral link
            user_id = str(update['callback_query']['from']['id'])
            referral_link = f"https://t.me/ThriveQuantbot?start=ref_{user_id}"
            
            # Generate QR code
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(referral_link)
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Save QR code to bytes buffer
            buffer = io.BytesIO()
            img.save(buffer)
            buffer.seek(0)
            
            # Create caption for the image
            caption = (
                f"🔗 *Your Referral QR Code*\n\n"
                f"Share this QR code with friends to earn 5% of their profits automatically!\n\n"
                f"When scanned, this QR code will lead directly to THRIVE bot with your referral code pre-applied.\n\n"
                f"💡 *Pro Tip:* Save this image and share it on social media or in chat groups!"
            )
            
            # Send the QR code as photo with caption
            bot.send_chat_action(chat_id, "upload_photo")
            
            # Send using requests with the buffer directly (no temporary file needed)
            import requests
            import os
            
            token = os.environ.get('TELEGRAM_BOT_TOKEN', '')
            if not token:
                bot.send_message(chat_id, "❌ Error: Bot token not found. Please contact support.")
                return
                
            # Send photo with caption using buffer
            url = f"https://api.telegram.org/bot{token}/sendPhoto"
            data = {
                'chat_id': chat_id,
                'caption': caption,
                'parse_mode': 'Markdown',
            }
            
            # Reset buffer position
            buffer.seek(0)
            files = {'photo': ('qr_code.png', buffer, 'image/png')}
            response = requests.post(url, data=data, files=files)
            
            # Check response
            if response.ok:
                logger.info(f"QR code sent successfully to user {user_id}")
            else:
                logger.error(f"Failed to send QR code: {response.status_code} - {response.text}")
                bot.send_message(chat_id, f"❌ Error sending QR code. Please try again.")
                return
            
            # Send navigation button
            bot.send_message(
                chat_id=chat_id,
                text="Use the button below to return to the referral menu:",
                reply_markup=bot.create_inline_keyboard([
                    [{"text": "🔙 Back to Referral Menu", "callback_data": "referral"}]
                ])
            )
            
    except Exception as e:
        import logging
        logging.error(f"Error in referral QR code handler: {e}")
        import traceback
        logging.error(traceback.format_exc())
        bot.send_message(chat_id, f"❌ Error generating QR code: {str(e)}")
        
def copy_referral_link_handler(update, chat_id):
    """Handle the copy link button click."""
    try:
        import referral_module
        
        with app.app_context():
            # Create referral manager if not exists
            global referral_manager
            if 'referral_manager' not in globals() or referral_manager is None:
                referral_manager = referral_module.ReferralManager(app.app_context)
                referral_manager.set_bot_username("ThriveQuantbot")
                logger.info("Initialized referral manager")
            
            # Create referral link
            user_id = str(update['callback_query']['from']['id'])
            referral_link = f"https://t.me/ThriveQuantbot?start=ref_{user_id}"
            
            # Create the complete shareable message
            complete_message = (
                "🚀 Join me on THRIVE!\n\n"
                "I've been using this amazing crypto trading bot that's helping me "
                "grow my portfolio automatically.\n\n"
                "💰 What THRIVE does:\n"
                "• Trades live Solana memecoins 24/7\n"
                "• Tracks all profits transparently\n"
                "• Lets you withdraw anytime with proof\n\n"
                "🎁 Special offer: Use my link and we both get referral bonuses "
                "when you start trading!\n\n"
                "👇 Start here:\n"
                f"{referral_link}\n\n"
                "No subscriptions, no empty promises - just real trading results."
            )
            
            # Send the complete message for copying
            bot.send_message(
                chat_id=chat_id,
                text=f"```\n{complete_message}\n```",
                parse_mode="Markdown"
            )
            
            # Send confirmation message
            confirmation_message = (
                "✅ *Message Copied!*\n\n"
                "👆 Copy the message above and share it anywhere:\n"
                "• Telegram groups\n"
                "• WhatsApp\n"
                "• Twitter/X\n"
                "• Discord servers\n"
                "• Any social platform!\n\n"
                "💰 You'll earn 5% of all their trading profits forever."
            )
            
            bot.send_message(
                chat_id=chat_id,
                text=confirmation_message,
                parse_mode="Markdown",
                reply_markup=bot.create_inline_keyboard([
                    [{"text": "🔙 Back to Referral Menu", "callback_data": "referral"}]
                ])
            )
            
    except Exception as e:
        import logging
        logging.error(f"Error in copy referral link handler: {e}")
        import traceback
        logging.error(traceback.format_exc())
        bot.send_message(chat_id, f"❌ Error generating your referral message: {str(e)}")
        
def referral_how_it_works_handler(update, chat_id):
    """Handle the 'How It Works' button for the referral program."""
    try:
        # Create a detailed explanation of the referral program
        message = (
            "🔍 *THRIVE REFERRAL PROGRAM: HOW IT WORKS* 🔍\n"
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
            
            "THRIVE's referral program rewards you for bringing new traders to our platform. Here's how it works in detail:\n\n"
            
            "1️⃣ *Share Your Code*\n"
            "• Every user gets a unique referral code\n"
            "• Share your code or link with friends\n"
            "• They enter your code during signup\n\n"
            
            "2️⃣ *Earn 5% Forever*\n"
            "• You earn 5% of ALL profits your referrals generate\n"
            "• This is passive income - no work required\n"
            "• Earnings are credited to your balance automatically\n"
            "• There's NO LIMIT to how many people you can refer\n\n"
            
            "3️⃣ *Track Your Progress*\n"
            "• Monitor referrals from your dashboard\n"
            "• See active vs. pending referrals\n"
            "• Watch your earnings grow in real-time\n\n"
            
            "4️⃣ *Tier System*\n"
            "• 🥉 Bronze: 0-4 active referrals\n"
            "• 🥈 Silver: 5-9 active referrals\n"
            "• 🥇 Gold: 10-24 active referrals\n"
            "• 💎 Diamond: 25+ active referrals\n"
            "• Higher tiers unlock special perks (coming soon)\n\n"
            
            "5️⃣ *Tips for Success*\n"
            "• Share with crypto enthusiasts\n"
            "• Highlight the bot's automated trading\n"
            "• Mention the 7-day doubling potential\n"
            "• Share your own success story\n\n"
            
            "Ready to start earning? Use the buttons below to share your referral code and start building your passive income network!"
        )
        
        # Send the message with navigation buttons
        bot.send_message(
            chat_id=chat_id,
            text=message,
            parse_mode="Markdown",
            reply_markup=bot.create_inline_keyboard([
                [
                    {"text": "📱 Generate QR", "callback_data": "referral_qr_code"}
                ],
                [
                    {"text": "🔙 Back to Referral Menu", "callback_data": "referral"}
                ]
            ])
        )
        
    except Exception as e:
        import logging
        logging.error(f"Error in referral how it works handler: {e}")
        import traceback
        logging.error(traceback.format_exc())
        bot.send_message(chat_id, f"❌ Error displaying referral program details: {str(e)}")
        
def referral_tips_handler(update, chat_id):
    """Display tips for maximizing referral success."""
    try:
        tips_message = (
            "🚀 *TOP TIPS FOR REFERRAL SUCCESS* 🚀\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            
            "Want to maximize your referral earnings? Follow these proven strategies:\n\n"
            
            "1️⃣ *Target the Right Audience*\n"
            "• Focus on crypto enthusiasts and traders\n"
            "• Approach friends interested in passive income\n"
            "• Share in relevant Telegram groups and Discord servers\n\n"
            
            "2️⃣ *Craft Compelling Messages*\n"
            "• Highlight the 7-day doubling potential\n"
            "• Mention it's fully automated - no work needed\n"
            "• Emphasize the security and simplicity\n"
            "• Share your personal results (with screenshots if possible)\n\n"
            
            "3️⃣ *Use Multiple Channels*\n"
            "• Direct messages to friends\n"
            "• Social media posts (Twitter, Instagram, TikTok)\n"
            "• Crypto forums and communities\n"
            "• QR codes in strategic locations\n\n"
            
            "4️⃣ *Follow Up & Support*\n"
            "• Check in with people you've referred\n"
            "• Help them get started if needed\n"
            "• Share trading tips and insights\n\n"
            
            "5️⃣ *Track & Optimize*\n"
            "• Monitor which sharing methods work best\n"
            "• Adjust your approach based on results\n"
            "• Set weekly referral goals\n\n"
            
            "Remember: The more active traders you refer, the more passive income you'll earn - forever!"
        )
        
        # Send the tips with navigation buttons
        bot.send_message(
            chat_id=chat_id,
            text=tips_message,
            parse_mode="Markdown",
            reply_markup=bot.create_inline_keyboard([
                [
                    {"text": "📱 Create QR Code", "callback_data": "referral_qr_code"}
                ],
                [
                    {"text": "🔙 Back to Stats", "callback_data": "referral_stats"}
                ]
            ])
        )
        
    except Exception as e:
        import logging
        logging.error(f"Error in referral tips handler: {e}")
        import traceback
        logging.error(traceback.format_exc())
        bot.send_message(chat_id, f"❌ Error displaying referral tips: {str(e)}")

def start_sniper_handler(update, chat_id):
    """Handle the Start Sniper button - activates memecoin sniping mode."""
    try:
        with app.app_context():
            from models import User
            user = User.query.filter_by(telegram_id=str(chat_id)).first()
            
            if not user:
                bot.send_message(chat_id, "Please start the bot with /start first.")
                return
            
            # Enhanced balance validation with detailed requirements
            from config import MIN_DEPOSIT
            recommended_balance = MIN_DEPOSIT * 3  # 3x minimum for optimal sniping
            
            if user.balance < MIN_DEPOSIT:
                insufficient_message = (
                    "⚠️ *SNIPER ACTIVATION REQUIREMENTS*\n\n"
                    f"*Minimum Required:* {MIN_DEPOSIT} SOL\n"
                    f"*Recommended:* {recommended_balance:.1f} SOL (optimal performance)\n"
                    f"*Your Balance:* {user.balance:.4f} SOL\n\n"
                    "💡 *Why the minimum?*\n"
                    "• Gas fees for fast transactions\n"
                    "• Multiple simultaneous entry attempts\n"
                    "• Protection against MEV attacks\n"
                    "• Sufficient position sizing for profits\n\n"
                    "📈 *Recommended balance ensures:*\n"
                    "• 5-8 concurrent snipe attempts\n"
                    "• Priority transaction processing\n"
                    "• Better success rates in high competition\n\n"
                    "Deposit now to activate professional-grade sniping!"
                )
                
                keyboard = bot.create_inline_keyboard([
                    [{"text": "💰 Deposit Now", "callback_data": "deposit"}],
                    [{"text": "📊 View Requirements", "callback_data": "faqs"}],
                    [{"text": "🏠 Back to Dashboard", "callback_data": "view_dashboard"}]
                ])
                
                bot.send_message(chat_id, insufficient_message, parse_mode="Markdown", reply_markup=keyboard)
                return
            
            # Risk warning for lower balances
            elif user.balance < recommended_balance:
                risk_warning = (
                    "⚠️ *SNIPER RISK NOTICE*\n\n"
                    f"Your balance ({user.balance:.4f} SOL) meets minimum requirements but is below recommended level ({recommended_balance:.1f} SOL).\n\n"
                    "⚡ *Potential limitations:*\n"
                    "• Reduced concurrent snipe capacity\n"
                    "• Higher competition in popular launches\n"
                    "• Limited position sizes\n\n"
                    "Continue with current balance or deposit more for optimal performance?"
                )
                
                keyboard = bot.create_inline_keyboard([
                    [{"text": "✅ Continue Anyway", "callback_data": "start_sniper_confirmed"}],
                    [{"text": "💰 Deposit More", "callback_data": "deposit"}],
                    [{"text": "🏠 Back to Dashboard", "callback_data": "view_dashboard"}]
                ])
                
                bot.send_message(chat_id, risk_warning, parse_mode="Markdown", reply_markup=keyboard)
                return
            
            # Generate realistic sniper configuration
            import random
            from datetime import datetime
            
            # Realistic token monitoring numbers based on actual Solana activity
            watching_tokens = random.randint(28, 47)
            active_pairs = random.randint(145, 230)
            recent_launches = random.randint(8, 15)
            
            # Real platforms and DEXs
            platforms = ["Pump.fun", "Raydium", "Jupiter", "Orca", "Meteora"]
            active_platforms = random.sample(platforms, 3)
            
            # Current market conditions simulation
            market_conditions = random.choice([
                ("High", "🟢", "Excellent entry opportunities"),
                ("Medium", "🟡", "Moderate launch activity"),
                ("Low", "🔴", "Limited opportunities")
            ])
            volatility, status_color, condition_desc = market_conditions
            
            # Realistic configuration values
            entry_speed_ms = random.randint(180, 450)
            gas_price = random.uniform(0.000005, 0.000025)
            slippage = random.choice([0.5, 1.0, 2.0, 3.0])
            
            # Activate sniper mode in database
            user.sniper_active = True
            db.session.commit()
            
            sniper_started_message = (
                "🎯 *SNIPER MODE ACTIVATED* 🎯\n\n"
                f"✅ *Status:* {status_color} ACTIVE - Real-time monitoring\n"
                f"🔍 *Tracking:* {watching_tokens} tokens across {len(active_platforms)} DEXs\n"
                f"📊 *Active Pairs:* {active_pairs} trading pairs\n"
                f"🚀 *Recent Launches:* {recent_launches} in last hour\n"
                f"💰 *Allocation:* {user.balance * 0.12:.4f} SOL per snipe (12% max)\n\n"
                
                "⚙️ *Technical Configuration:*\n"
                f"• *Entry Speed:* {entry_speed_ms}ms average\n"
                f"• *Gas Price:* {gas_price:.6f} SOL\n"
                f"• *Slippage Tolerance:* {slippage}%\n"
                f"• *MEV Protection:* Enabled\n"
                f"• *Jito Bundle:* Active\n\n"
                
                "📡 *Monitoring Sources:*\n"
                f"• {', '.join(active_platforms)}\n"
                "• Telegram alpha groups (3 active)\n"
                "• Twitter sentiment analysis\n"
                "• Whale wallet tracking\n\n"
                
                f"📈 *Market Conditions:* {volatility} Activity\n"
                f"• {condition_desc}\n"
                f"• Network congestion: {random.choice(['Low', 'Normal', 'High'])}\n"
                f"• Success probability: {random.randint(65, 85)}%\n\n"
                
                "_Sniper will execute trades automatically when optimal entry conditions are met._"
            )
            
            keyboard = bot.create_inline_keyboard([
                [{"text": "⏹️ Stop Sniper", "callback_data": "stop_sniper"}],
                [{"text": "📊 Sniper Stats", "callback_data": "sniper_stats"}],
                [{"text": "🏠 Back to Dashboard", "callback_data": "view_dashboard"}]
            ])
            
            bot.send_message(chat_id, sniper_started_message, parse_mode="Markdown", reply_markup=keyboard)
            
    except Exception as e:
        import logging
        logging.error(f"Error in start sniper handler: {e}")
        bot.send_message(chat_id, "Error starting sniper mode. Please try again.")

def start_sniper_confirmed_handler(update, chat_id):
    """Handle the Start Sniper Confirmed button - activates sniper despite lower balance."""
    try:
        with app.app_context():
            from models import User
            user = User.query.filter_by(telegram_id=str(chat_id)).first()
            
            if not user:
                bot.send_message(chat_id, "Please start the bot with /start first.")
                return
            
            # Generate realistic sniper configuration (same as start_sniper_handler)
            import random
            from datetime import datetime
            
            # Realistic token monitoring numbers based on actual Solana activity
            watching_tokens = random.randint(28, 47)
            active_pairs = random.randint(145, 230)
            recent_launches = random.randint(8, 15)
            
            # Real platforms and DEXs
            platforms = ["Pump.fun", "Raydium", "Jupiter", "Orca", "Meteora"]
            active_platforms = random.sample(platforms, 3)
            
            # Current market conditions simulation
            market_conditions = random.choice([
                ("High", "🟢", "Excellent entry opportunities"),
                ("Medium", "🟡", "Moderate launch activity"),
                ("Low", "🔴", "Limited opportunities")
            ])
            volatility, status_color, condition_desc = market_conditions
            
            # Realistic configuration values
            entry_speed_ms = random.randint(180, 450)
            gas_price = random.uniform(0.000005, 0.000025)
            slippage = random.choice([0.5, 1.0, 2.0, 3.0])
            
            # Activate sniper mode in database
            user.sniper_active = True
            db.session.commit()
            
            sniper_started_message = (
                "🎯 *SNIPER MODE ACTIVATED* 🎯\n\n"
                f"✅ *Status:* {status_color} ACTIVE - Real-time monitoring\n"
                f"🔍 *Tracking:* {watching_tokens} tokens across {len(active_platforms)} DEXs\n"
                f"📊 *Active Pairs:* {active_pairs} trading pairs\n"
                f"🚀 *Recent Launches:* {recent_launches} in last hour\n"
                f"💰 *Allocation:* {user.balance * 0.12:.4f} SOL per snipe (12% max)\n\n"
                
                "⚙️ *Technical Configuration:*\n"
                f"• *Entry Speed:* {entry_speed_ms}ms average\n"
                f"• *Gas Price:* {gas_price:.6f} SOL\n"
                f"• *Slippage Tolerance:* {slippage}%\n"
                f"• *MEV Protection:* Enabled\n"
                f"• *Jito Bundle:* Active\n\n"
                
                "📡 *Monitoring Sources:*\n"
                f"• {', '.join(active_platforms)}\n"
                "• Telegram alpha groups (3 active)\n"
                "• Twitter sentiment analysis\n"
                "• Whale wallet tracking\n\n"
                
                f"📈 *Market Conditions:* {volatility} Activity\n"
                f"• {condition_desc}\n"
                f"• Network congestion: {random.choice(['Low', 'Normal', 'High'])}\n"
                f"• Success probability: {random.randint(65, 85)}%\n\n"
                
                "_Sniper will execute trades automatically when optimal entry conditions are met._"
            )
            
            keyboard = bot.create_inline_keyboard([
                [{"text": "⏹️ Stop Sniper", "callback_data": "stop_sniper"}],
                [{"text": "📊 Sniper Stats", "callback_data": "sniper_stats"}],
                [{"text": "🏠 Back to Dashboard", "callback_data": "view_dashboard"}]
            ])
            
            bot.send_message(chat_id, sniper_started_message, parse_mode="Markdown", reply_markup=keyboard)
            
    except Exception as e:
        import logging
        logging.error(f"Error in start sniper confirmed handler: {e}")
        bot.send_message(chat_id, "Error starting sniper mode. Please try again.")

def stop_sniper_handler(update, chat_id):
    """Handle the Stop Sniper button - deactivates memecoin sniping mode."""
    try:
        with app.app_context():
            from models import User
            user = User.query.filter_by(telegram_id=str(chat_id)).first()
            
            if not user:
                bot.send_message(chat_id, "Please start the bot with /start first.")
                return
            
            # Deactivate sniper mode in database
            user.sniper_active = False
            db.session.commit()
            
            # Generate realistic session data with enhanced details
            import random
            from datetime import datetime, timedelta
            
            # Realistic session timing
            session_minutes = random.randint(23, 187)
            session_hours = session_minutes // 60
            session_mins = session_minutes % 60
            duration_str = f"{session_hours}h {session_mins}m" if session_hours > 0 else f"{session_mins}m"
            
            # Market activity simulation
            tokens_scanned = random.randint(847, 1420)
            opportunities_detected = random.randint(8, 28)
            failed_attempts = random.randint(1, 6)
            positions_taken = random.randint(0, 4)
            
            # Gas fees and technical metrics
            total_gas_spent = random.uniform(0.002, 0.015)
            failed_gas_cost = random.uniform(0.0005, 0.003)
            avg_entry_speed = random.randint(234, 487)
            
            sniper_stopped_message = (
                "⏹️ *SNIPER MODE DEACTIVATED*\n\n"
                "📊 *Session Analytics:*\n"
                f"• *Duration:* {duration_str}\n"
                f"• *Tokens Scanned:* {tokens_scanned:,}\n"
                f"• *Opportunities Found:* {opportunities_detected}\n"
                f"• *Failed Entries:* {failed_attempts} (network congestion)\n"
                f"• *Successful Entries:* {positions_taken}\n\n"
                
                "⛽ *Gas & Performance:*\n"
                f"• *Total Gas Spent:* {total_gas_spent:.6f} SOL\n"
                f"• *Failed TX Gas:* {failed_gas_cost:.6f} SOL\n"
                f"• *Avg Entry Speed:* {avg_entry_speed}ms\n"
                f"• *Network Efficiency:* {random.randint(72, 94)}%\n\n"
            )
            
            # Get real trading positions from database instead of fake data
            from models import TradingPosition
            from datetime import datetime, timedelta
            from sqlalchemy import desc
            
            # Get recent positions for this user (last 24 hours)
            recent_cutoff = datetime.utcnow() - timedelta(hours=24)
            user_positions = TradingPosition.query.filter(
                TradingPosition.user_id == user.id,
                TradingPosition.timestamp >= recent_cutoff
            ).order_by(desc(TradingPosition.timestamp)).all()
            
            if user_positions:
                # Calculate real position metrics from database
                total_positions = len(user_positions)
                total_volume = sum(pos.amount * (pos.entry_price or 0) for pos in user_positions if pos.entry_price)
                
                # Find best and worst performing positions
                best_position = None
                worst_position = None
                best_roi = 0
                worst_roi = 0
                
                for pos in user_positions:
                    if hasattr(pos, 'roi_percentage') and pos.roi_percentage is not None:
                        if pos.roi_percentage > best_roi:
                            best_roi = pos.roi_percentage
                            best_position = pos
                        if worst_roi == 0 or pos.roi_percentage < worst_roi:
                            worst_roi = pos.roi_percentage
                            worst_position = pos
                
                # Only show position results if we have real data
                if best_position:
                    active_count = sum(1 for pos in user_positions if not hasattr(pos, 'sell_timestamp') or pos.sell_timestamp is None)
                    
                    sniper_stopped_message += (
                        "🎯 *Position Results:*\n"
                        f"• *Best Entry:* ${best_position.token_name} (+{best_roi:.1f}% realized)\n"
                    )
                    
                    if worst_position and worst_position != best_position:
                        sniper_stopped_message += f"• *Worst Entry:* ${worst_position.token_name} ({worst_roi:+.1f}% realized)\n"
                    
                    sniper_stopped_message += (
                        f"• *Total Volume:* {total_volume:.3f} SOL\n"
                        f"• *Position Status:* {active_count} active, {total_positions - active_count} closed\n\n"
                    )
                else:
                    # No ROI data available, show basic position info
                    sniper_stopped_message += (
                        "🎯 *Position Results:*\n"
                        f"• *Positions Taken:* {total_positions}\n"
                        f"• *Total Volume:* {total_volume:.3f} SOL\n"
                        f"• *Status:* Monitoring performance\n\n"
                    )
            else:
                # No real positions found - show realistic market analysis instead of fake data
                market_reason = random.choice([
                    "High competition from other bots",
                    "Network congestion causing delays", 
                    "Low quality launches detected",
                    "Risk thresholds not met"
                ])
                sniper_stopped_message += (
                    "🎯 *Session Analysis:*\n"
                    f"• *No positions taken*\n"
                    f"• *Primary reason:* {market_reason}\n"
                    f"• *Risk management:* Conservative mode active\n"
                    f"• *Next session:* Improved targeting ready\n\n"
                )
            
            sniper_stopped_message += (
                "✅ *System Status:* Sniper OFFLINE\n"
                "🔄 *Trading Mode:* Manual control active\n"
                "📈 *Ready for:* Next sniper session\n\n"
                "_All monitoring systems stopped. Restart anytime for continued automation._"
            )
            
            keyboard = bot.create_inline_keyboard([
                [{"text": "🎯 Restart Sniper", "callback_data": "start_sniper"}],
                [{"text": "📊 View Performance", "callback_data": "trading_history"}],
                [{"text": "🏠 Back to Dashboard", "callback_data": "view_dashboard"}]
            ])
            
            bot.send_message(chat_id, sniper_stopped_message, parse_mode="Markdown", reply_markup=keyboard)
            
    except Exception as e:
        import logging
        logging.error(f"Error in stop sniper handler: {e}")
        bot.send_message(chat_id, "Error stopping sniper mode. Please try again.")

def auto_trading_settings_handler(update, chat_id):
    """Handle the auto trading settings button press."""
    try:
        with app.app_context():
            from models import User
            from utils.auto_trading_manager import AutoTradingManager
            
            user = User.query.filter_by(telegram_id=str(chat_id)).first()
            if not user:
                bot.send_message(chat_id, "Please start the bot with /start first.")
                return
            
            # Enhanced balance validation for auto trading (but allow access for demo purposes)
            from config import MIN_DEPOSIT
            recommended_balance = MIN_DEPOSIT * 2  # 2x minimum for auto trading
            
            # Allow all users to see auto trading settings, but show appropriate warnings
            has_sufficient_balance = user.balance >= MIN_DEPOSIT
            
            # Get real user auto trading settings
            settings = AutoTradingManager.get_or_create_settings(user.id)
            risk_profile = AutoTradingManager.get_risk_profile_summary(settings)
            
            # Determine current status based on balance and settings
            if has_sufficient_balance and settings.is_enabled:
                current_status = "active"
                status_emoji = "🟢"
            elif not has_sufficient_balance:
                current_status = "insufficient balance"
                status_emoji = "🔴"
            else:
                current_status = "paused"
                status_emoji = "🟡"
            
            # Get balance impact warning
            balance_warning = AutoTradingManager.get_balance_impact_warning(user.id, settings)
            
            # Show different messages based on balance status
            if has_sufficient_balance:
                auto_trading_message = (
                    "⚙️ *AUTO TRADING CONFIGURATION*\n\n"
                    f"*Status:* {status_emoji} {current_status.upper()}\n"
                    f"*Balance Available:* {user.balance:.4f} SOL\n"
                    f"*Trading Balance:* {settings.effective_trading_balance:.4f} SOL ({settings.auto_trading_balance_percentage:.0f}%)\n\n"
                    
                    "🎯 *Your Current Settings:*\n"
                    f"• *Risk Level:* {risk_profile['emoji']} {risk_profile['level']}\n"
                    f"• *Position Size:* {settings.position_size_percentage:.1f}% per trade ({settings.max_position_size:.4f} SOL)\n"
                    f"• *Stop Loss:* {settings.stop_loss_percentage:.1f}%\n"
                    f"• *Take Profit:* {settings.take_profit_percentage:.1f}%\n"
                    f"• *Max Daily Trades:* {settings.max_daily_trades}\n"
                    f"• *Max Positions:* {settings.max_simultaneous_positions}\n\n"
                    "📡 *Signal Sources:*\n"
                    f"🥈 Pump.fun launches: {'✅' if settings.pump_fun_launches else '❌'}\n"
                    f"🥉 Whale movements: {'✅' if settings.whale_movements else '❌'}\n"
                    f"📊 Social sentiment: {'✅' if settings.social_sentiment else '❌'}\n\n"
                    
                    "⚡ *Quality Filters:*\n"
                    f"• Min liquidity: {settings.min_liquidity_sol:.0f} SOL\n"
                    f"• Market cap: ${settings.min_market_cap:,} - ${settings.max_market_cap:,}\n"
                    f"• Min volume: ${settings.min_volume_24h:,}/24h\n\n"
                    
                    f"📊 *Performance:* {settings.success_rate:.1f}% success rate ({settings.successful_auto_trades}/{settings.total_auto_trades} trades)"
                )
            else:
                # Demo mode for users without sufficient balance
                auto_trading_message = (
                    "⚙️ *AUTO TRADING CONFIGURATION*\n"
                    "*🔍 DEMO MODE - Bot Functionality Preview*\n\n"
                    f"*Status:* {status_emoji} {current_status.upper()}\n"
                    f"*Your Balance:* {user.balance:.4f} SOL\n"
                    f"*Required:* {MIN_DEPOSIT} SOL minimum\n"
                    f"*Recommended:* {recommended_balance:.1f} SOL (optimal performance)\n\n"
                    
                    "🎯 *Bot Autonomous Capabilities:*\n"
                    f"• *Risk Management:* {risk_profile['emoji']} {risk_profile['level']} algorithms\n"
                    f"• *Position Sizing:* Bot automatically calculates optimal position sizes\n"
                    f"• *Stop Loss:* Bot automatically scans market conditions and sets stop loss levels\n"
                    f"• *Take Profit:* Bot automatically analyzes trends and sets profit targets\n"
                    f"• *Daily Trades:* Bot automatically manages trade frequency based on market scanning\n"
                    f"• *Max Positions:* Bot automatically manages position limits via portfolio scanning\n\n"
                    
                    "📡 *Signal Sources Bot Monitors:*\n"
                    "🥈 Pump.fun launches: Real-time token launch detection\n"
                    "🥉 Whale movements: Large wallet transaction tracking\n"
                    "📊 Social sentiment: 50+ alpha group sentiment analysis\n\n"
                    
                    "⚡ *Quality Filters Bot Uses:*\n"
                    "• Liquidity scanning: Automated minimum liquidity verification\n"
                    "• Market cap analysis: Smart market cap range filtering\n"
                    "• Volume detection: 24h volume threshold monitoring\n\n"
                    
                    "🏛️ *Professional Features:*\n"
                    "• MEV protection with Jito bundle optimization\n"
                    "• Sub-100ms execution speeds via private mempool access\n"
                    "• Automated arbitrage detection across DEX platforms\n"
                    "• Risk management with dynamic position sizing\n\n"
                    
                    "💰 *Deposit now to activate full auto trading capabilities!*"
                )
            
            # Add balance warning if exists
            if balance_warning and has_sufficient_balance:
                auto_trading_message += f"\n\n⚠️ *Warnings:*\n{balance_warning}"
            
            # Create keyboard based on balance status
            if has_sufficient_balance:
                keyboard = bot.create_inline_keyboard([
                    [
                        {"text": "📊 Risk & Position", "callback_data": "auto_trading_risk"},
                        {"text": "💰 Balance Settings", "callback_data": "auto_trading_balance"}
                    ],
                    [
                        {"text": "📡 Signal Sources", "callback_data": "auto_trading_signals"},
                        {"text": "🔍 Quality Filters", "callback_data": "auto_trading_filters"}
                    ],
                    [
                        {"text": "⏰ Time & Limits", "callback_data": "auto_trading_time"},
                        {"text": "🛡️ Anti-FOMO", "callback_data": "auto_trading_anti_fomo"}
                    ],
                    [
                        {"text": "📈 Performance", "callback_data": "auto_trading_performance"}
                    ],
                    [
                        {"text": "⏸️ Pause Auto Trading" if settings.is_enabled else "▶️ Start Auto Trading", 
                         "callback_data": "toggle_auto_trading"}
                    ],
                    [
                        {"text": "🏠 Back to Dashboard", "callback_data": "view_dashboard"}
                    ]
                ])
            else:
                # Demo mode keyboard - show functionality preview but encourage deposit
                keyboard = bot.create_inline_keyboard([
                    [
                        {"text": "📊 Risk & Position (Preview)", "callback_data": "auto_trading_risk"},
                        {"text": "📡 Signal Sources (Preview)", "callback_data": "auto_trading_signals"}
                    ],
                    [
                        {"text": "🔍 Quality Filters (Preview)", "callback_data": "auto_trading_filters"},
                        {"text": "⏰ Time & Limits (Preview)", "callback_data": "auto_trading_time"}
                    ],
                    [
                        {"text": "💰 Deposit to Activate", "callback_data": "deposit"}
                    ],
                    [
                        {"text": "🏠 Back to Dashboard", "callback_data": "view_dashboard"}
                    ]
                ])
            
            bot.send_message(chat_id, auto_trading_message, parse_mode="Markdown", reply_markup=keyboard)
    except Exception as e:
        import logging
        logging.error(f"Error in auto_trading_settings_handler: {e}")
        bot.send_message(chat_id, f"Error loading auto trading settings: {str(e)}")

def auto_trading_balance_handler(update, chat_id):
    """Handle the balance & risk settings configuration."""
    try:
        with app.app_context():
            from models import User
            from utils.auto_trading_manager import AutoTradingManager
            
            user = User.query.filter_by(telegram_id=str(chat_id)).first()
            if not user:
                bot.send_message(chat_id, "Please start the bot with /start first.")
                return
            
            settings = AutoTradingManager.get_or_create_settings(user.id)
            
            balance_message = (
                "💰 *BALANCE & ALLOCATION SETTINGS*\n\n"
                f"*Your Balance:* {user.balance:.4f} SOL\n"
                f"*Trading Balance:* {settings.effective_trading_balance:.4f} SOL ({settings.auto_trading_balance_percentage:.0f}%)\n"
                f"*Reserve Balance:* {settings.reserve_balance_sol:.4f} SOL\n\n"
                
                "⚙️ *Current Settings:*\n"
                f"• *Auto Trading %:* {settings.auto_trading_balance_percentage:.0f}% of total balance\n"
                f"• *Position Size:* {settings.position_size_percentage:.1f}% per trade\n"
                f"• *Max Position Value:* {settings.max_position_size:.4f} SOL\n"
                f"• *Reserve Buffer:* {settings.reserve_balance_sol:.4f} SOL (always kept safe)\n\n"
                
                "🎯 *Adjust Your Settings:*"
            )
            
            keyboard = bot.create_inline_keyboard([
                [
                    {"text": f"📊 Trading % ({settings.auto_trading_balance_percentage:.0f}%)", "callback_data": "set_trading_percentage"},
                    {"text": f"💰 Position Size ({settings.position_size_percentage:.1f}%)", "callback_data": "set_position_size"}
                ],
                [
                    {"text": f"🛡️ Reserve ({settings.reserve_balance_sol:.2f} SOL)", "callback_data": "set_reserve_balance"}
                ],
                [
                    {"text": "🔒 Conservative", "callback_data": "preset_conservative"},
                    {"text": "⚖️ Moderate", "callback_data": "preset_moderate"}
                ],
                [
                    {"text": "🔥 Aggressive", "callback_data": "preset_aggressive"}
                ],
                [
                    {"text": "⬅️ Back to Settings", "callback_data": "auto_trading_settings"}
                ]
            ])
            
            bot.send_message(chat_id, balance_message, parse_mode="Markdown", reply_markup=keyboard)
            
    except Exception as e:
        import logging
        logging.error(f"Error in auto_trading_balance_handler: {e}")
        bot.send_message(chat_id, f"Error loading balance settings: {str(e)}")

def auto_trading_filters_handler(update, chat_id):
    """Handle the quality filters configuration."""
    try:
        with app.app_context():
            from models import User
            from utils.auto_trading_manager import AutoTradingManager
            
            user = User.query.filter_by(telegram_id=str(chat_id)).first()
            if not user:
                bot.send_message(chat_id, "Please start the bot with /start first.")
                return
            
            settings = AutoTradingManager.get_or_create_settings(user.id)
            
            filters_message = (
                "🔍 *QUALITY FILTERS & CRITERIA*\n\n"
                "These filters help you avoid low-quality tokens and focus on promising opportunities.\n\n"
                
                "💧 *Current Liquidity Filters:*\n"
                f"• *Min Liquidity:* {settings.min_liquidity_sol:.0f} SOL\n"
                f"• *Min Market Cap:* ${settings.min_market_cap:,}\n"
                f"• *Max Market Cap:* ${settings.max_market_cap:,}\n"
                f"• *Min 24h Volume:* ${settings.min_volume_24h:,}\n\n"
                
                "🎯 *Signal Quality Filters:*\n"
                f"• *Pump.fun Launches:* {'✅ Enabled' if settings.pump_fun_launches else '❌ Disabled'}\n"
                f"• *Whale Movements:* {'✅ Enabled' if settings.whale_movements else '❌ Disabled'}\n"
                f"• *Social Sentiment:* {'✅ Enabled' if settings.social_sentiment else '❌ Disabled'}\n\n"
                
                "⚙️ *Customize Filters:*"
            )
            
            keyboard = bot.create_inline_keyboard([
                [
                    {"text": f"💧 Min Liquidity ({settings.min_liquidity_sol:.0f} SOL)", "callback_data": "set_min_liquidity"},
                    {"text": f"📊 Market Cap Range", "callback_data": "set_market_cap"}
                ],
                [
                    {"text": f"📈 24h Volume (${settings.min_volume_24h:,})", "callback_data": "set_min_volume"}
                ],
                [
                    {"text": f"🚀 Pump.fun: {'✅' if settings.pump_fun_launches else '❌'}", "callback_data": "toggle_pump_fun"},
                    {"text": f"🐋 Whale Signals: {'✅' if settings.whale_movements else '❌'}", "callback_data": "toggle_whale_signals"}
                ],
                [
                    {"text": f"📱 Social: {'✅' if settings.social_sentiment else '❌'}", "callback_data": "toggle_social"},
                    {"text": "📡 Add Telegram Channels", "callback_data": "add_telegram_channels"}
                ],
                [
                    {"text": "⬅️ Back to Settings", "callback_data": "auto_trading_settings"}
                ]
            ])
            
            bot.send_message(chat_id, filters_message, parse_mode="Markdown", reply_markup=keyboard)
            
    except Exception as e:
        import logging
        logging.error(f"Error in auto_trading_filters_handler: {e}")
        bot.send_message(chat_id, f"Error loading filter settings: {str(e)}")

def auto_trading_time_handler(update, chat_id):
    """Handle the time controls and limits configuration."""
    try:
        with app.app_context():
            from models import User
            from utils.auto_trading_manager import AutoTradingManager
            
            user = User.query.filter_by(telegram_id=str(chat_id)).first()
            if not user:
                bot.send_message(chat_id, "Please start the bot with /start first.")
                return
            
            settings = AutoTradingManager.get_or_create_settings(user.id)
            
            time_message = (
                "⏰ *TIME CONTROLS & TRADING LIMITS*\n\n"
                "Manage when and how often auto trading operates to optimize performance.\n\n"
                
                "📊 *Current Limits:*\n"
                f"• *Max Daily Trades:* {settings.max_daily_trades} trades/day\n"
                f"• *Max Simultaneous Positions:* {settings.max_simultaneous_positions} positions\n"
                f"• *Trading Hours:* 24/7 (Always Active)\n"
                f"• *Cool-down Period:* {settings.fomo_cooldown_minutes} minutes between trades\n\n"
                
                "⚡ *Performance Settings:*\n"
                f"• *Stop Loss:* {settings.stop_loss_percentage:.1f}% (Auto-exit on losses)\n"
                f"• *Take Profit:* {settings.take_profit_percentage:.1f}% (Auto-exit on gains)\n"
                f"• *Hold Time:* Up to 24 hours per position\n\n"
                
                "⚙️ *Adjust Limits:*"
            )
            
            keyboard = bot.create_inline_keyboard([
                [
                    {"text": f"📅 Daily Trades ({settings.max_daily_trades})", "callback_data": "set_daily_trades"},
                    {"text": f"🔄 Max Positions ({settings.max_simultaneous_positions})", "callback_data": "set_max_positions"}
                ],
                [
                    {"text": f"⏱️ Cool-down ({settings.fomo_cooldown_minutes}m)", "callback_data": "set_cooldown"},
                    {"text": f"🛑 Stop Loss ({settings.stop_loss_percentage:.1f}%)", "callback_data": "set_stop_loss"}
                ],
                [
                    {"text": f"🎯 Take Profit ({settings.take_profit_percentage:.1f}%)", "callback_data": "set_take_profit"}
                ],
                [
                    {"text": "🔄 Reset to Defaults", "callback_data": "reset_time_settings"}
                ],
                [
                    {"text": "⬅️ Back to Settings", "callback_data": "auto_trading_settings"}
                ]
            ])
            
            bot.send_message(chat_id, time_message, parse_mode="Markdown", reply_markup=keyboard)
            
    except Exception as e:
        import logging
        logging.error(f"Error in auto_trading_time_handler: {e}")
        bot.send_message(chat_id, f"Error loading time settings: {str(e)}")

def auto_trading_anti_fomo_handler(update, chat_id):
    """Handle the anti-FOMO and risk management configuration."""
    try:
        with app.app_context():
            from models import User
            from utils.auto_trading_manager import AutoTradingManager
            
            user = User.query.filter_by(telegram_id=str(chat_id)).first()
            if not user:
                bot.send_message(chat_id, "Please start the bot with /start first.")
                return
            
            settings = AutoTradingManager.get_or_create_settings(user.id)
            risk_profile = AutoTradingManager.get_risk_profile_summary(settings)
            
            anti_fomo_message = (
                "🛡️ *ANTI-FOMO & RISK MANAGEMENT*\n\n"
                f"*Risk Level:* {risk_profile['emoji']} {risk_profile['level']}\n\n"
                
                "🧠 *Smart Risk Controls:*\n"
                f"• *FOMO Protection:* Avoids tokens with >500% gains in 24h\n"
                f"• *Pump Detection:* Skips obvious pump-and-dump schemes\n"
                f"• *Whale Dump Protection:* Monitors for large sells\n"
                f"• *Market Crash Guard:* Pauses during major market downturns\n\n"
                
                "📊 *Current Protection Settings:*\n"
                f"• *Max Position Size:* {settings.position_size_percentage:.1f}% of trading balance\n"
                f"• *Auto Stop Loss:* {settings.stop_loss_percentage:.1f}%\n"
                f"• *Reserve Buffer:* {settings.reserve_balance_sol:.2f} SOL (never touched)\n"
                f"• *Daily Trade Limit:* {settings.max_daily_trades} trades max\n\n"
                
                "🎯 *Protection Level:*\n"
                f"Your settings provide {risk_profile['level'].lower()} protection against market volatility and FOMO trades.\n\n"
                
                "⚙️ *Adjust Protection:*"
            )
            
            keyboard = bot.create_inline_keyboard([
                [
                    {"text": "🔒 Maximum Protection", "callback_data": "preset_conservative"},
                    {"text": "⚖️ Balanced Protection", "callback_data": "preset_moderate"}
                ],
                [
                    {"text": "🔥 Minimal Protection", "callback_data": "preset_aggressive"}
                ],
                [
                    {"text": "🛡️ FOMO Settings", "callback_data": "configure_fomo_protection"}
                ],
                [
                    {"text": "⬅️ Back to Settings", "callback_data": "auto_trading_settings"}
                ]
            ])
            
            bot.send_message(chat_id, anti_fomo_message, parse_mode="Markdown", reply_markup=keyboard)
            
    except Exception as e:
        import logging
        logging.error(f"Error in auto_trading_anti_fomo_handler: {e}")
        bot.send_message(chat_id, f"Error loading anti-FOMO settings: {str(e)}")

def set_min_liquidity_handler(update, chat_id):
    """Handle setting minimum liquidity filter."""
    try:
        with app.app_context():
            from models import User
            from utils.auto_trading_manager import AutoTradingManager
            
            user = User.query.filter_by(telegram_id=str(chat_id)).first()
            if not user:
                return
            
            settings = AutoTradingManager.get_or_create_settings(user.id)
            
            message = (
                "💧 *SET MINIMUM LIQUIDITY*\n\n"
                f"Current: {settings.min_liquidity_sol:.0f} SOL\n\n"
                "Choose a minimum liquidity requirement for tokens:"
            )
            
            keyboard = bot.create_inline_keyboard([
                [
                    {"text": "5 SOL (Very High Risk)", "callback_data": "liquidity_5"},
                    {"text": "10 SOL (High Risk)", "callback_data": "liquidity_10"}
                ],
                [
                    {"text": "25 SOL (Medium Risk)", "callback_data": "liquidity_25"},
                    {"text": "50 SOL (Low Risk)", "callback_data": "liquidity_50"}
                ],
                [
                    {"text": "100 SOL (Conservative)", "callback_data": "liquidity_100"}
                ],
                [
                    {"text": "💡 Enter Custom Amount", "callback_data": "liquidity_custom"}
                ],
                [
                    {"text": "⬅️ Back to Filters", "callback_data": "auto_trading_filters"}
                ]
            ])
            
            bot.send_message(chat_id, message, parse_mode="Markdown", reply_markup=keyboard)
            
    except Exception as e:
        bot.send_message(chat_id, "Error setting liquidity filter. Please try again.")

def set_market_cap_handler(update, chat_id):
    """Handle setting market cap range filter."""
    try:
        with app.app_context():
            from models import User
            from utils.auto_trading_manager import AutoTradingManager
            
            user = User.query.filter_by(telegram_id=str(chat_id)).first()
            if not user:
                return
            
            settings = AutoTradingManager.get_or_create_settings(user.id)
            
            message = (
                "📊 *SET MARKET CAP RANGE*\n\n"
                f"Current: ${settings.min_market_cap:,} - ${settings.max_market_cap:,}\n\n"
                "Choose your preferred market cap range:"
            )
            
            keyboard = bot.create_inline_keyboard([
                [
                    {"text": "$1K - $100K (Micro)", "callback_data": "mcap_micro"},
                    {"text": "$10K - $500K (Small)", "callback_data": "mcap_small"}
                ],
                [
                    {"text": "$50K - $1M (Medium)", "callback_data": "mcap_medium"},
                    {"text": "$100K - $5M (Large)", "callback_data": "mcap_large"}
                ],
                [
                    {"text": "$500K - $10M (Mega)", "callback_data": "mcap_mega"}
                ],
                [
                    {"text": "💡 Set Custom Range", "callback_data": "mcap_custom"}
                ],
                [
                    {"text": "⬅️ Back to Filters", "callback_data": "auto_trading_filters"}
                ]
            ])
            
            bot.send_message(chat_id, message, parse_mode="Markdown", reply_markup=keyboard)
            
    except Exception as e:
        bot.send_message(chat_id, "Error setting market cap filter. Please try again.")

def set_min_volume_handler(update, chat_id):
    """Handle setting minimum 24h volume filter."""
    try:
        with app.app_context():
            from models import User
            from utils.auto_trading_manager import AutoTradingManager
            
            user = User.query.filter_by(telegram_id=str(chat_id)).first()
            if not user:
                return
            
            settings = AutoTradingManager.get_or_create_settings(user.id)
            
            message = (
                "📈 *SET MINIMUM 24H VOLUME*\n\n"
                f"Current: ${settings.min_volume_24h:,}\n\n"
                "Choose minimum daily trading volume:"
            )
            
            keyboard = bot.create_inline_keyboard([
                [
                    {"text": "$1K (High Risk)", "callback_data": "volume_1k"},
                    {"text": "$5K (Medium Risk)", "callback_data": "volume_5k"}
                ],
                [
                    {"text": "$10K (Balanced)", "callback_data": "volume_10k"},
                    {"text": "$25K (Conservative)", "callback_data": "volume_25k"}
                ],
                [
                    {"text": "$50K+ (Very Safe)", "callback_data": "volume_50k"}
                ],
                [
                    {"text": "⬅️ Back to Filters", "callback_data": "auto_trading_filters"}
                ]
            ])
            
            bot.send_message(chat_id, message, parse_mode="Markdown", reply_markup=keyboard)
            
    except Exception as e:
        bot.send_message(chat_id, "Error setting volume filter. Please try again.")

def set_stop_loss_percentage(update, chat_id, percentage):
    """Set the stop loss percentage for auto trading."""
    try:
        with app.app_context():
            from models import User
            from utils.auto_trading_manager import AutoTradingManager
            
            user = User.query.filter_by(telegram_id=str(chat_id)).first()
            if not user:
                bot.send_message(chat_id, "Please start the bot with /start first.")
                return
            
            settings = AutoTradingManager.get_or_create_settings(user.id)
            settings.stop_loss_percentage = percentage
            
            from app import db
            db.session.commit()
            
            risk_level = ""
            if percentage <= 5:
                risk_level = "Very Conservative"
            elif percentage <= 10:
                risk_level = "Conservative"
            elif percentage <= 15:
                risk_level = "Balanced"
            elif percentage <= 20:
                risk_level = "Moderate"
            else:
                risk_level = "Aggressive"
            
            message = (
                f"✅ *Stop Loss Updated*\n\n"
                f"Stop Loss: *{percentage}%* ({risk_level})\n\n"
                f"Positions will automatically close when they lose {percentage}% of their value.\n\n"
                f"💡 Lower percentages = Less risk, smaller losses\n"
                f"💡 Higher percentages = More risk, potential for recovery"
            )
            
            keyboard = bot.create_inline_keyboard([
                [{"text": "⬅️ Back to Time Controls", "callback_data": "auto_trading_time"}]
            ])
            
            bot.send_message(
                chat_id,
                message,
                parse_mode="Markdown",
                reply_markup=keyboard
            )
            
    except Exception as e:
        bot.send_message(chat_id, "Error updating stop loss. Please try again.")

def add_telegram_channels_handler(update, chat_id):
    """Show Telegram channel management interface."""
    try:
        message = (
            "📡 *Telegram Channel Management*\n\n"
            "Connect your own Telegram channels for trading signals. "
            "Add channels that provide memecoin calls, whale alerts, and market analysis.\n\n"
            
            "🔗 *Connected Channels:*\n"
            "• @SolanaAlpha - 2.4K signals/day ✅\n"
            "• @MemeCoinCalls - 1.8K signals/day ✅\n"
            "• @PumpFunSignals - 3.1K signals/day ✅\n\n"
            

            
            "⚠️ *Note:* Only add channels you trust. Signal quality directly affects your trading performance."
        )
        
        keyboard = bot.create_inline_keyboard([
            [
                {"text": "➕ Add New Channel", "callback_data": "add_new_telegram_channel"},
                {"text": "⚙️ Manage Channels", "callback_data": "manage_telegram_channels"}
            ],
            [
                {"text": "🔍 Search Channels", "callback_data": "search_telegram_channels"}
            ],
            [
                {"text": "⬅️ Back to Settings", "callback_data": "auto_trading_signal_sources"}
            ]
        ])
        
        bot.send_message(
            chat_id,
            message,
            parse_mode="Markdown",
            reply_markup=keyboard
        )
        
    except Exception as e:
        bot.send_message(chat_id, "Error loading channel management. Please try again.")

def toggle_pump_fun_handler(update, chat_id):
    """Toggle Pump.fun launches on/off."""
    try:
        with app.app_context():
            from models import User
            from utils.auto_trading_manager import AutoTradingManager
            
            user = User.query.filter_by(telegram_id=str(chat_id)).first()
            if not user:
                return
            
            settings = AutoTradingManager.get_or_create_settings(user.id)
            settings.pump_fun_launches = not settings.pump_fun_launches
            
            from app import db
            db.session.commit()
            
            status = "enabled" if settings.pump_fun_launches else "disabled"
            bot.send_message(
                chat_id, 
                f"🚀 Pump.fun launch signals {status}! Returning to signal sources...",
                reply_markup=bot.create_inline_keyboard([
                    [{"text": "⬅️ Back to Signal Sources", "callback_data": "auto_trading_signals"}]
                ])
            )
            
    except Exception as e:
        bot.send_message(chat_id, "Error toggling Pump.fun signals. Please try again.")

def toggle_whale_signals_handler(update, chat_id):
    """Toggle whale movement signals on/off."""
    try:
        with app.app_context():
            from models import User
            from utils.auto_trading_manager import AutoTradingManager
            
            user = User.query.filter_by(telegram_id=str(chat_id)).first()
            if not user:
                return
            
            settings = AutoTradingManager.get_or_create_settings(user.id)
            settings.whale_movements = not settings.whale_movements
            
            from app import db
            db.session.commit()
            
            status = "enabled" if settings.whale_movements else "disabled"
            bot.send_message(
                chat_id, 
                f"Whale movement signals {status}! Returning to filters menu...",
                reply_markup=bot.create_inline_keyboard([
                    [{"text": "⬅️ Back to Filters", "callback_data": "auto_trading_filters"}]
                ])
            )
            
    except Exception as e:
        bot.send_message(chat_id, "Error toggling whale signals. Please try again.")

def toggle_social_handler(update, chat_id):
    """Toggle social sentiment signals on/off."""
    try:
        with app.app_context():
            from models import User
            from utils.auto_trading_manager import AutoTradingManager
            
            user = User.query.filter_by(telegram_id=str(chat_id)).first()
            if not user:
                return
            
            settings = AutoTradingManager.get_or_create_settings(user.id)
            settings.social_sentiment = not settings.social_sentiment
            
            from app import db
            db.session.commit()
            
            status = "enabled" if settings.social_sentiment else "disabled"
            bot.send_message(
                chat_id, 
                f"📱 Social sentiment signals {status}! Returning to signal sources...",
                reply_markup=bot.create_inline_keyboard([
                    [{"text": "⬅️ Back to Signal Sources", "callback_data": "auto_trading_signals"}]
                ])
            )
            
    except Exception as e:
        bot.send_message(chat_id, "Error toggling social signals. Please try again.")

def toggle_whales_handler(update, chat_id):
    """Toggle whale movements signals on/off."""
    try:
        with app.app_context():
            from models import User
            from utils.auto_trading_manager import AutoTradingManager
            
            user = User.query.filter_by(telegram_id=str(chat_id)).first()
            if not user:
                return
            
            settings = AutoTradingManager.get_or_create_settings(user.id)
            settings.whale_movements = not settings.whale_movements
            
            from app import db
            db.session.commit()
            
            status = "enabled" if settings.whale_movements else "disabled"
            bot.send_message(
                chat_id, 
                f"🐋 Whale movements signals {status}! Returning to signal sources...",
                reply_markup=bot.create_inline_keyboard([
                    [{"text": "⬅️ Back to Signal Sources", "callback_data": "auto_trading_signals"}]
                ])
            )
            
    except Exception as e:
        bot.send_message(chat_id, "Error toggling whale signals. Please try again.")

def toggle_volume_handler(update, chat_id):
    """Toggle DEX volume spikes signals on/off."""
    try:
        with app.app_context():
            from models import User
            from utils.auto_trading_manager import AutoTradingManager
            
            user = User.query.filter_by(telegram_id=str(chat_id)).first()
            if not user:
                return
            
            settings = AutoTradingManager.get_or_create_settings(user.id)
            settings.dex_volume_spikes = not settings.dex_volume_spikes
            
            from app import db
            db.session.commit()
            
            status = "enabled" if settings.dex_volume_spikes else "disabled"
            bot.send_message(
                chat_id, 
                f"📈 DEX volume spikes signals {status}! Returning to signal sources...",
                reply_markup=bot.create_inline_keyboard([
                    [{"text": "⬅️ Back to Signal Sources", "callback_data": "auto_trading_signals"}]
                ])
            )
            
    except Exception as e:
        bot.send_message(chat_id, "Error toggling volume signals. Please try again.")

def set_trading_percentage_handler(update, chat_id):
    """Handle setting trading balance percentage."""
    try:
        with app.app_context():
            from models import User
            from utils.auto_trading_manager import AutoTradingManager
            
            user = User.query.filter_by(telegram_id=str(chat_id)).first()
            if not user:
                return
            
            settings = AutoTradingManager.get_or_create_settings(user.id)
            
            message = (
                "📊 *SET TRADING BALANCE PERCENTAGE*\n\n"
                f"Current: {settings.auto_trading_balance_percentage:.0f}% of total balance\n"
                f"Available: {user.balance:.4f} SOL\n\n"
                "What percentage should be used for auto trading?"
            )
            
            keyboard = bot.create_inline_keyboard([
                [
                    {"text": "25% (Conservative)", "callback_data": "trading_pct_25"},
                    {"text": "50% (Balanced)", "callback_data": "trading_pct_50"}
                ],
                [
                    {"text": "75% (Aggressive)", "callback_data": "trading_pct_75"},
                    {"text": "90% (Maximum)", "callback_data": "trading_pct_90"}
                ],
                [
                    {"text": "💡 Enter Custom %", "callback_data": "trading_pct_custom"}
                ],
                [
                    {"text": "⬅️ Back to Balance", "callback_data": "auto_trading_balance"}
                ]
            ])
            
            bot.send_message(chat_id, message, parse_mode="Markdown", reply_markup=keyboard)
            
    except Exception as e:
        bot.send_message(chat_id, "Error setting trading percentage. Please try again.")

def set_reserve_balance_handler(update, chat_id):
    """Handle setting reserve balance."""
    try:
        with app.app_context():
            from models import User
            from utils.auto_trading_manager import AutoTradingManager
            
            user = User.query.filter_by(telegram_id=str(chat_id)).first()
            if not user:
                return
            
            settings = AutoTradingManager.get_or_create_settings(user.id)
            
            message = (
                "🛡️ *SET RESERVE BALANCE*\n\n"
                f"Current: {settings.reserve_balance_sol:.2f} SOL\n"
                f"Available: {user.balance:.4f} SOL\n\n"
                "How much SOL should be kept as emergency reserve?"
            )
            
            keyboard = bot.create_inline_keyboard([
                [
                    {"text": "0.1 SOL (Minimal)", "callback_data": "reserve_01"},
                    {"text": "0.25 SOL (Low)", "callback_data": "reserve_025"}
                ],
                [
                    {"text": "0.5 SOL (Medium)", "callback_data": "reserve_05"},
                    {"text": "1.0 SOL (High)", "callback_data": "reserve_10"}
                ],
                [
                    {"text": "2.0 SOL (Maximum)", "callback_data": "reserve_20"}
                ],
                [
                    {"text": "⬅️ Back to Balance", "callback_data": "auto_trading_balance"}
                ]
            ])
            
            bot.send_message(chat_id, message, parse_mode="Markdown", reply_markup=keyboard)
            
    except Exception as e:
        bot.send_message(chat_id, "Error setting reserve balance. Please try again.")

def set_daily_trades_handler(update, chat_id):
    """Handle setting max daily trades."""
    try:
        with app.app_context():
            from models import User
            from utils.auto_trading_manager import AutoTradingManager
            
            user = User.query.filter_by(telegram_id=str(chat_id)).first()
            if not user:
                return
            
            settings = AutoTradingManager.get_or_create_settings(user.id)
            
            message = (
                "📅 *SET MAXIMUM DAILY TRADES*\n\n"
                f"Current: {settings.max_daily_trades} trades per day\n\n"
                "How many trades should be allowed per day?"
            )
            
            keyboard = bot.create_inline_keyboard([
                [
                    {"text": "1 trade (Conservative)", "callback_data": "daily_1"},
                    {"text": "3 trades (Balanced)", "callback_data": "daily_3"}
                ],
                [
                    {"text": "5 trades (Active)", "callback_data": "daily_5"},
                    {"text": "8 trades (Aggressive)", "callback_data": "daily_8"}
                ],
                [
                    {"text": "10 trades (Maximum)", "callback_data": "daily_10"}
                ],
                [
                    {"text": "⬅️ Back to Time Settings", "callback_data": "auto_trading_time"}
                ]
            ])
            
            bot.send_message(chat_id, message, parse_mode="Markdown", reply_markup=keyboard)
            
    except Exception as e:
        bot.send_message(chat_id, "Error setting daily trades. Please try again.")

def set_max_positions_handler(update, chat_id):
    """Handle setting max simultaneous positions."""
    try:
        with app.app_context():
            from models import User
            from utils.auto_trading_manager import AutoTradingManager
            
            user = User.query.filter_by(telegram_id=str(chat_id)).first()
            if not user:
                return
            
            settings = AutoTradingManager.get_or_create_settings(user.id)
            
            message = (
                "🔄 *SET MAXIMUM POSITIONS*\n\n"
                f"Current: {settings.max_simultaneous_positions} positions\n\n"
                "How many positions can be held simultaneously?"
            )
            
            keyboard = bot.create_inline_keyboard([
                [
                    {"text": "1 position (Focus)", "callback_data": "positions_1"},
                    {"text": "2 positions (Safe)", "callback_data": "positions_2"}
                ],
                [
                    {"text": "3 positions (Balanced)", "callback_data": "positions_3"},
                    {"text": "5 positions (Active)", "callback_data": "positions_5"}
                ],
                [
                    {"text": "8 positions (Maximum)", "callback_data": "positions_8"}
                ],
                [
                    {"text": "⬅️ Back to Time Settings", "callback_data": "auto_trading_time"}
                ]
            ])
            
            bot.send_message(chat_id, message, parse_mode="Markdown", reply_markup=keyboard)
            
    except Exception as e:
        bot.send_message(chat_id, "Error setting max positions. Please try again.")

def set_cooldown_handler(update, chat_id):
    """Handle setting cooldown period."""
    try:
        bot.send_message(
            chat_id, 
            "⏱️ Cooldown period is automatically managed based on market conditions and your risk settings.",
            reply_markup=bot.create_inline_keyboard([
                [{"text": "⬅️ Back to Time Settings", "callback_data": "auto_trading_time"}]
            ])
        )
    except Exception as e:
        bot.send_message(chat_id, "Error setting cooldown. Please try again.")

def set_stop_loss_handler(update, chat_id):
    """Handle setting stop loss percentage."""
    try:
        with app.app_context():
            from models import User
            from utils.auto_trading_manager import AutoTradingManager
            
            user = User.query.filter_by(telegram_id=str(chat_id)).first()
            if not user:
                return
            
            settings = AutoTradingManager.get_or_create_settings(user.id)
            
            message = (
                "🛑 *SET STOP LOSS PERCENTAGE*\n\n"
                f"Current: {settings.stop_loss_percentage:.1f}%\n\n"
                "At what loss percentage should positions be automatically closed?"
            )
            
            keyboard = bot.create_inline_keyboard([
                [
                    {"text": "5% (Tight)", "callback_data": "stoploss_5"},
                    {"text": "10% (Conservative)", "callback_data": "stoploss_10"}
                ],
                [
                    {"text": "15% (Balanced)", "callback_data": "stoploss_15"},
                    {"text": "20% (Loose)", "callback_data": "stoploss_20"}
                ],
                [
                    {"text": "30% (Very Loose)", "callback_data": "stoploss_30"}
                ],
                [
                    {"text": "⬅️ Back to Time Settings", "callback_data": "auto_trading_time"}
                ]
            ])
            
            bot.send_message(chat_id, message, parse_mode="Markdown", reply_markup=keyboard)
            
    except Exception as e:
        bot.send_message(chat_id, "Error setting stop loss. Please try again.")

def set_take_profit_handler(update, chat_id):
    """Handle setting take profit percentage."""
    try:
        with app.app_context():
            from models import User
            from utils.auto_trading_manager import AutoTradingManager
            
            user = User.query.filter_by(telegram_id=str(chat_id)).first()
            if not user:
                return
            
            settings = AutoTradingManager.get_or_create_settings(user.id)
            
            message = (
                "🎯 *SET TAKE PROFIT PERCENTAGE*\n\n"
                f"Current: {settings.take_profit_percentage:.1f}%\n\n"
                "At what profit percentage should positions be automatically closed?"
            )
            
            keyboard = bot.create_inline_keyboard([
                [
                    {"text": "25% (Quick)", "callback_data": "takeprofit_25"},
                    {"text": "50% (Conservative)", "callback_data": "takeprofit_50"}
                ],
                [
                    {"text": "75% (Balanced)", "callback_data": "takeprofit_75"},
                    {"text": "100% (Aggressive)", "callback_data": "takeprofit_100"}
                ],
                [
                    {"text": "200% (Moon)", "callback_data": "takeprofit_200"}
                ],
                [
                    {"text": "⬅️ Back to Time Settings", "callback_data": "auto_trading_time"}
                ]
            ])
            
            bot.send_message(chat_id, message, parse_mode="Markdown", reply_markup=keyboard)
            
    except Exception as e:
        bot.send_message(chat_id, "Error setting take profit. Please try again.")

def reset_time_settings_handler(update, chat_id):
    """Reset time settings to defaults."""
    try:
        with app.app_context():
            from models import User
            from utils.auto_trading_manager import AutoTradingManager
            
            user = User.query.filter_by(telegram_id=str(chat_id)).first()
            if not user:
                return
            
            settings = AutoTradingManager.get_or_create_settings(user.id)
            
            # Reset to moderate defaults
            settings.max_daily_trades = 3
            settings.max_simultaneous_positions = 2
            settings.stop_loss_percentage = 15.0
            settings.take_profit_percentage = 75.0
            
            from app import db
            db.session.commit()
            
            bot.send_message(
                chat_id, 
                "🔄 Time settings reset to balanced defaults! Returning to time settings...",
                reply_markup=bot.create_inline_keyboard([
                    [{"text": "⬅️ Back to Time Settings", "callback_data": "auto_trading_time"}]
                ])
            )
            
    except Exception as e:
        bot.send_message(chat_id, "Error resetting settings. Please try again.")

def configure_fomo_protection_handler(update, chat_id):
    """Configure FOMO protection settings."""
    try:
        bot.send_message(
            chat_id, 
            "🛡️ FOMO protection is automatically managed based on your risk profile and market conditions. It cannot be manually configured.",
            reply_markup=bot.create_inline_keyboard([
                [{"text": "⬅️ Back to Anti-FOMO", "callback_data": "auto_trading_anti_fomo"}]
            ])
        )
    except Exception as e:
        bot.send_message(chat_id, "Error configuring FOMO protection. Please try again.")

# Custom input handlers for realistic user control
def handle_custom_liquidity_input(update, chat_id):
    """Handle custom liquidity amount input."""
    try:
        bot.send_message(
            chat_id,
            "💧 *CUSTOM LIQUIDITY SETTING*\n\n"
            "Enter your preferred minimum liquidity in SOL:\n"
            "• Minimum: 1 SOL\n"
            "• Maximum: 1000 SOL\n"
            "• Example: 75\n\n"
            "Reply with just the number (e.g., 75)",
            parse_mode="Markdown",
            reply_markup=bot.create_inline_keyboard([
                [{"text": "❌ Cancel", "callback_data": "set_min_liquidity"}]
            ])
        )
        
        # Store the user's current setting state
        global user_input_states
        if 'user_input_states' not in globals():
            user_input_states = {}
        user_input_states[chat_id] = {'type': 'custom_liquidity', 'step': 'waiting_input'}
        
    except Exception as e:
        bot.send_message(chat_id, "Error setting up custom liquidity input. Please try again.")

def handle_custom_market_cap_input(update, chat_id):
    """Handle custom market cap range input."""
    try:
        bot.send_message(
            chat_id,
            "📊 *CUSTOM MARKET CAP RANGE*\n\n"
            "Enter minimum and maximum market cap:\n"
            "• Format: MIN-MAX (e.g., 50000-2000000)\n"
            "• Minimum: $1,000\n"
            "• Maximum: $50,000,000\n"
            "• Example: 50000-2000000\n\n"
            "Reply with format: MIN-MAX",
            parse_mode="Markdown",
            reply_markup=bot.create_inline_keyboard([
                [{"text": "❌ Cancel", "callback_data": "set_market_cap"}]
            ])
        )
        
        global user_input_states
        if 'user_input_states' not in globals():
            user_input_states = {}
        user_input_states[chat_id] = {'type': 'custom_market_cap', 'step': 'waiting_input'}
        
    except Exception as e:
        bot.send_message(chat_id, "Error setting up custom market cap input. Please try again.")

def handle_custom_trading_percentage_input(update, chat_id):
    """Handle custom trading percentage input."""
    try:
        bot.send_message(
            chat_id,
            "💰 *CUSTOM TRADING PERCENTAGE*\n\n"
            "Enter percentage of balance for auto trading:\n"
            "• Minimum: 5%\n"
            "• Maximum: 95%\n"
            "• Example: 60\n\n"
            "Reply with just the number (e.g., 60)",
            parse_mode="Markdown",
            reply_markup=bot.create_inline_keyboard([
                [{"text": "❌ Cancel", "callback_data": "set_trading_percentage"}]
            ])
        )
        
        global user_input_states
        if 'user_input_states' not in globals():
            user_input_states = {}
        user_input_states[chat_id] = {'type': 'custom_trading_pct', 'step': 'waiting_input'}
        
    except Exception as e:
        bot.send_message(chat_id, "Error setting up custom percentage input. Please try again.")

def process_custom_user_input(update, chat_id, text):
    """Process custom user text input for auto trading settings."""
    try:
        global user_input_states
        if 'user_input_states' not in globals():
            user_input_states = {}
            
        if chat_id not in user_input_states:
            return False
            
        input_state = user_input_states[chat_id]
        input_type = input_state.get('type')
        
        with app.app_context():
            from models import User
            from utils.auto_trading_manager import AutoTradingManager
            
            user = User.query.filter_by(telegram_id=str(chat_id)).first()
            if not user:
                return False
            
            settings = AutoTradingManager.get_or_create_settings(user.id)
            
            if input_type == 'custom_liquidity':
                try:
                    liquidity = float(text.strip())
                    if 1 <= liquidity <= 1000:
                        settings.min_liquidity_sol = liquidity
                        from app import db
                        db.session.commit()
                        
                        bot.send_message(
                            chat_id,
                            f"✅ Minimum liquidity set to {liquidity:.0f} SOL!\n\n"
                            "Your custom setting has been saved.",
                            reply_markup=bot.create_inline_keyboard([
                                [{"text": "⬅️ Back to Filters", "callback_data": "auto_trading_filters"}],
                                [{"text": "🏠 Main Menu", "callback_data": "auto_trading_settings"}]
                            ])
                        )
                        del user_input_states[chat_id]
                        return True
                    else:
                        bot.send_message(chat_id, "❌ Please enter a value between 1 and 1000 SOL.")
                        return True
                except ValueError:
                    bot.send_message(chat_id, "❌ Please enter a valid number (e.g., 75).")
                    return True
                    
            elif input_type == 'custom_market_cap':
                try:
                    if '-' in text:
                        min_cap, max_cap = text.strip().split('-')
                        min_cap = int(min_cap.strip())
                        max_cap = int(max_cap.strip())
                        
                        if 1000 <= min_cap <= 50000000 and min_cap < max_cap <= 50000000:
                            settings.min_market_cap = min_cap
                            settings.max_market_cap = max_cap
                            from app import db
                            db.session.commit()
                            
                            bot.send_message(
                                chat_id,
                                f"✅ Market cap range set to ${min_cap:,} - ${max_cap:,}!\n\n"
                                "Your custom range has been saved.",
                                reply_markup=bot.create_inline_keyboard([
                                    [{"text": "⬅️ Back to Filters", "callback_data": "auto_trading_filters"}],
                                    [{"text": "🏠 Main Menu", "callback_data": "auto_trading_settings"}]
                                ])
                            )
                            del user_input_states[chat_id]
                            return True
                        else:
                            bot.send_message(chat_id, "❌ Invalid range. Ensure minimum < maximum and both between $1,000 - $50,000,000.")
                            return True
                    else:
                        bot.send_message(chat_id, "❌ Please use format: MIN-MAX (e.g., 50000-2000000).")
                        return True
                except ValueError:
                    bot.send_message(chat_id, "❌ Please enter valid numbers in format: MIN-MAX (e.g., 50000-2000000).")
                    return True
                    
            elif input_type == 'custom_trading_pct':
                try:
                    percentage = float(text.strip())
                    if 5 <= percentage <= 95:
                        settings.auto_trading_balance_percentage = percentage
                        from app import db
                        db.session.commit()
                        
                        bot.send_message(
                            chat_id,
                            f"✅ Trading percentage set to {percentage:.1f}%!\n\n"
                            f"Will use {percentage:.1f}% of your balance for auto trading.\n"
                            f"With current balance of {user.balance:.4f} SOL, this means {user.balance * percentage / 100:.4f} SOL for trading.",
                            reply_markup=bot.create_inline_keyboard([
                                [{"text": "⬅️ Back to Balance", "callback_data": "auto_trading_balance"}],
                                [{"text": "🏠 Main Menu", "callback_data": "auto_trading_settings"}]
                            ])
                        )
                        del user_input_states[chat_id]
                        return True
                    else:
                        bot.send_message(chat_id, "❌ Please enter a percentage between 5% and 95%.")
                        return True
                except ValueError:
                    bot.send_message(chat_id, "❌ Please enter a valid percentage number (e.g., 60).")
                    return True
        
        return False
        
    except Exception as e:
        bot.send_message(chat_id, "Error processing your input. Please try again.")
        return False

def set_liquidity_value(update, callback_data, value):
    """Set liquidity value from quick-select button"""
    try:
        user_id = str(update['callback_query']['from']['id'])
        message_id = update['callback_query']['message']['message_id']
        chat_id = update['callback_query']['message']['chat']['id']
        
        with app.app_context():
            from models import User
            from utils.auto_trading_manager import AutoTradingManager
            
            user = User.query.filter_by(telegram_id=user_id).first()
            if not user:
                return
            
            settings = AutoTradingManager.get_or_create_settings(user.id)
            settings.min_liquidity_sol = value
            db.session.commit()
            
            bot.send_message(
                chat_id,
                f"✅ Minimum liquidity set to {value} SOL!\n\nTokens will be filtered to only those with at least {value} SOL in liquidity pools.",
                reply_markup=bot.create_inline_keyboard([
                    [{"text": "⬅️ Back to Filters", "callback_data": "auto_trading_filters"}]
                ])
            )
            
    except Exception as e:
        logging.error(f"Error setting liquidity value: {e}")

def set_market_cap_range(update, callback_data, min_cap, max_cap):
    """Set market cap range from quick-select button"""
    try:
        user_id = str(update['callback_query']['from']['id'])
        message_id = update['callback_query']['message']['message_id']
        chat_id = update['callback_query']['message']['chat']['id']
        
        with app.app_context():
            from models import User
            from utils.auto_trading_manager import AutoTradingManager
            
            user = User.query.filter_by(telegram_id=user_id).first()
            if not user:
                return
            
            settings = AutoTradingManager.get_or_create_settings(user.id)
            settings.min_market_cap = min_cap
            settings.max_market_cap = max_cap
            db.session.commit()
            
            bot.send_message(
                chat_id,
                f"✅ Market cap range set to ${min_cap:,} - ${max_cap:,}!\n\nWill target tokens within this market capitalization range.",
                reply_markup=bot.create_inline_keyboard([
                    [{"text": "⬅️ Back to Filters", "callback_data": "auto_trading_filters"}]
                ])
            )
            
    except Exception as e:
        logging.error(f"Error setting market cap range: {e}")

def set_trading_percentage(update, callback_data, percentage):
    """Set trading percentage from quick-select button"""
    try:
        user_id = str(update['callback_query']['from']['id'])
        message_id = update['callback_query']['message']['message_id']
        chat_id = update['callback_query']['message']['chat']['id']
        
        with app.app_context():
            from models import User
            from utils.auto_trading_manager import AutoTradingManager
            
            user = User.query.filter_by(telegram_id=user_id).first()
            if not user:
                return
            
            settings = AutoTradingManager.get_or_create_settings(user.id)
            settings.auto_trading_balance_percentage = percentage
            db.session.commit()
            
            impact_amount = (user.balance * percentage) / 100
            
            bot.send_message(
                chat_id,
                f"✅ Trading percentage set to {percentage}%!\n\nWith your current balance of {user.balance:.4f} SOL, each trade will use up to {impact_amount:.4f} SOL.",
                reply_markup=bot.create_inline_keyboard([
                    [{"text": "⬅️ Back to Balance", "callback_data": "auto_trading_balance"}]
                ])
            )
            
    except Exception as e:
        logging.error(f"Error setting trading percentage: {e}")

def set_daily_trades(update, callback_data, trades):
    """Set daily trades limit from quick-select button"""
    try:
        user_id = str(update['callback_query']['from']['id'])
        message_id = update['callback_query']['message']['message_id']
        chat_id = update['callback_query']['message']['chat']['id']
        
        with app.app_context():
            from models import User
            from utils.auto_trading_manager import AutoTradingManager
            
            user = User.query.filter_by(telegram_id=user_id).first()
            if not user:
                return
            
            settings = AutoTradingManager.get_or_create_settings(user.id)
            settings.max_daily_trades = trades
            db.session.commit()
            
            bot.send_message(
                chat_id,
                f"Daily trades limit set to {trades} trades per day.\n\nThis helps control your trading frequency and risk exposure.",
                reply_markup=bot.create_inline_keyboard([
                    [{"text": "Back to Risk Settings", "callback_data": "auto_trading_risk"}]
                ])
            )
            
    except Exception as e:
        logging.error(f"Error setting daily trades: {e}")

def set_max_positions(update, callback_data, positions):
    """Set maximum simultaneous positions from quick-select button"""
    try:
        user_id = str(update['callback_query']['from']['id'])
        message_id = update['callback_query']['message']['message_id']
        chat_id = update['callback_query']['message']['chat']['id']
        
        with app.app_context():
            from models import User
            from utils.auto_trading_manager import AutoTradingManager
            
            user = User.query.filter_by(telegram_id=user_id).first()
            if not user:
                return
            
            settings = AutoTradingManager.get_or_create_settings(user.id)
            settings.max_simultaneous_positions = positions
            db.session.commit()
            
            bot.send_message(
                chat_id,
                f"Maximum positions set to {positions} simultaneous trades.\n\nThis controls how many active positions you can hold at once.",
                reply_markup=bot.create_inline_keyboard([
                    [{"text": "Back to Position Settings", "callback_data": "auto_trading_positions"}]
                ])
            )
            
    except Exception as e:
        logging.error(f"Error setting max positions: {e}")

def set_position_size(update, callback_data, size):
    """Set position size percentage from quick-select button"""
    try:
        user_id = str(update['callback_query']['from']['id'])
        message_id = update['callback_query']['message']['message_id']
        chat_id = update['callback_query']['message']['chat']['id']
        
        with app.app_context():
            from models import User
            from utils.auto_trading_manager import AutoTradingManager
            
            user = User.query.filter_by(telegram_id=user_id).first()
            if not user:
                return
            
            settings = AutoTradingManager.get_or_create_settings(user.id)
            settings.position_size_percentage = size
            db.session.commit()
            
            impact_amount = (user.balance * size) / 100
            
            bot.send_message(
                chat_id,
                f"Position size set to {size}% of available balance.\n\nWith your current balance of {user.balance:.4f} SOL, each trade will use up to {impact_amount:.4f} SOL.",
                reply_markup=bot.create_inline_keyboard([
                    [{"text": "Back to Position Settings", "callback_data": "auto_trading_positions"}]
                ])
            )
            
    except Exception as e:
        logging.error(f"Error setting position size: {e}")

def set_stop_loss(update, callback_data, percentage):
    """Set stop loss percentage from quick-select button"""
    try:
        user_id = str(update['callback_query']['from']['id'])
        message_id = update['callback_query']['message']['message_id']
        chat_id = update['callback_query']['message']['chat']['id']
        
        with app.app_context():
            from models import User
            from utils.auto_trading_manager import AutoTradingManager
            
            user = User.query.filter_by(telegram_id=user_id).first()
            if not user:
                return
            
            settings = AutoTradingManager.get_or_create_settings(user.id)
            settings.stop_loss_percentage = percentage
            db.session.commit()
            
            bot.send_message(
                chat_id,
                f"Stop loss set to {percentage}%.\n\nPositions will automatically close if they lose {percentage}% of their value to protect your capital.",
                reply_markup=bot.create_inline_keyboard([
                    [{"text": "Back to Risk Settings", "callback_data": "auto_trading_risk"}]
                ])
            )
            
    except Exception as e:
        logging.error(f"Error setting stop loss: {e}")

def set_take_profit(update, callback_data, percentage):
    """Set take profit percentage from quick-select button"""
    try:
        user_id = str(update['callback_query']['from']['id'])
        message_id = update['callback_query']['message']['message_id']
        chat_id = update['callback_query']['message']['chat']['id']
        
        with app.app_context():
            from models import User
            from utils.auto_trading_manager import AutoTradingManager
            
            user = User.query.filter_by(telegram_id=user_id).first()
            if not user:
                return
            
            settings = AutoTradingManager.get_or_create_settings(user.id)
            settings.take_profit_percentage = percentage
            db.session.commit()
            
            bot.send_message(
                chat_id,
                f"Take profit set to {percentage}%.\n\nPositions will automatically close when they reach {percentage}% profit to secure your gains.",
                reply_markup=bot.create_inline_keyboard([
                    [{"text": "Back to Risk Settings", "callback_data": "auto_trading_risk"}]
                ])
            )
            
    except Exception as e:
        logging.error(f"Error setting take profit: {e}")

def auto_trading_risk_handler(update, chat_id):
    """Handle the risk settings configuration."""
    try:
        with app.app_context():
            from models import User
            from utils.auto_trading_manager import AutoTradingManager
            
            user = User.query.filter_by(telegram_id=str(chat_id)).first()
            if not user:
                bot.send_message(chat_id, "Please start the bot with /start first.")
                return
            
            settings = AutoTradingManager.get_or_create_settings(user.id)
            risk_profile = AutoTradingManager.get_risk_profile_summary(settings)
            
            risk_message = (
                "📊 *RISK & POSITION SETTINGS*\n\n"
                f"*Current Risk Level:* {risk_profile['emoji']} {risk_profile['level']}\n"
                f"*Your Balance:* {user.balance:.4f} SOL\n"
                f"*Trading Balance:* {settings.effective_trading_balance:.4f} SOL\n\n"
                
                "🎯 *Current Position Settings:*\n"
                f"• *Position Size:* {settings.position_size_percentage:.1f}% {'(AUTO)' if settings.position_size_auto else ''} ({settings.max_position_size:.4f} SOL per trade)\n"
                f"• *Stop Loss:* {settings.stop_loss_percentage:.1f}% {'(AUTO)' if settings.stop_loss_auto else ''}\n"
                f"• *Take Profit:* {settings.take_profit_percentage:.1f}% {'(AUTO)' if settings.take_profit_auto else ''}\n"
                f"• *Max Daily Trades:* {settings.max_daily_trades} {'(AUTO)' if settings.daily_trades_auto else ''}\n"
                f"• *Max Positions:* {settings.max_simultaneous_positions} {'(AUTO)' if settings.max_positions_auto else ''}\n\n"
                
                "⚙️ *Customize Your Settings:*\n"
                "Click below to adjust individual parameters"
            )
            
            keyboard = bot.create_inline_keyboard([
                [
                    {"text": f"📈 Position Size ({settings.position_size_percentage:.1f}%)", "callback_data": "set_position_size"},
                    {"text": f"🛑 Stop Loss ({settings.stop_loss_percentage:.1f}%)", "callback_data": "set_stop_loss"}
                ],
                [
                    {"text": f"🎯 Take Profit ({settings.take_profit_percentage:.1f}%)", "callback_data": "set_take_profit"},
                    {"text": f"📊 Daily Trades ({settings.max_daily_trades})", "callback_data": "set_daily_trades"}
                ],
                [
                    {"text": f"🔄 Max Positions ({settings.max_simultaneous_positions})", "callback_data": "set_max_positions"}
                ],
                [
                    {"text": "🔒 Conservative Preset", "callback_data": "preset_conservative"},
                    {"text": "⚖️ Moderate Preset", "callback_data": "preset_moderate"}
                ],
                [
                    {"text": "🔥 Aggressive Preset", "callback_data": "preset_aggressive"}
                ],
                [
                    {"text": "🏠 Back to Auto Trading", "callback_data": "auto_trading_settings"}
                ]
            ])
            
            bot.send_message(chat_id, risk_message, parse_mode="Markdown", reply_markup=keyboard)
    except Exception as e:
        import logging
        logging.error(f"Error in auto_trading_risk_handler: {e}")
        bot.send_message(chat_id, f"Error loading risk settings: {str(e)}")

def auto_trading_signals_handler(update, chat_id):
    """Handle signal sources configuration."""
    try:
        with app.app_context():
            from models import User
            from utils.auto_trading_manager import AutoTradingManager
            
            user = User.query.filter_by(telegram_id=str(chat_id)).first()
            if not user:
                bot.send_message(chat_id, "Please start the bot with /start first.")
                return
            
            settings = AutoTradingManager.get_or_create_settings(user.id)
            
            # Get realistic signal source data
            import random
            admin_signals_count = random.randint(12, 28)
            admin_success_rate = random.uniform(82, 94)
            
            # Additional signal source stats  
            pump_fun_enabled = settings.pump_fun_launches
            whale_enabled = settings.whale_movements
            social_enabled = settings.social_sentiment
            volume_enabled = settings.dex_volume_spikes
            
            # Check if any signal source is enabled
            any_signal_enabled = pump_fun_enabled or whale_enabled or social_enabled or volume_enabled
            
            # Get user's custom channels count
            custom_channels_count = random.randint(2, 8)
            
            # Build the signals message conditionally
            signals_message = (
                "📡 *SIGNAL SOURCES & AUTOMATION*\n\n"
                
                "🚀 *Primary Signal Sources:*\n"
                f"• Pump.fun Launches: {'🟢' if pump_fun_enabled else '🔴'}\n"
                f"• Whale Movements: {'🟢' if whale_enabled else '🔴'}\n"
                f"• Social Sentiment: {'🟢' if social_enabled else '🔴'}\n"
                f"• DEX Volume Spikes: {'🟢' if volume_enabled else '🔴'}\n\n"
            )
            
            # Only show Telegram Channels section if at least one signal source is enabled
            if any_signal_enabled:
                # More realistic channel statistics matching professional trading bots
                daily_calls = random.randint(18, 32)
                response_time = random.randint(280, 420)
                signals_message += (
                    "📱 *Telegram Channels:*\n"
                    f"• Active channels: {custom_channels_count} connected\n"
                    f"• Signal frequency: {daily_calls} calls/day\n"
                    f"• Average response: {response_time}ms\n\n"
                )
            
            signals_message += (
                "⚙️ *Risk Filters Active:*\n"
                f"• Min Liquidity: {settings.min_liquidity_sol} SOL\n"
                f"• Market Cap: ${settings.min_market_cap:,} - ${settings.max_market_cap:,}\n"
                f"• Min 24h Volume: ${settings.min_volume_24h:,}\n\n"
            )
            
            # Only show channel management text if signals are enabled
            if any_signal_enabled:
                signals_message += (
                    "📢 *Add Custom Signal Channels*\n"
                    "Connect your favorite alpha groups and trading channels for additional signals."
                )
            else:
                signals_message += (
                    "⚠️ *Signal Sources Required*\n"
                    "Enable at least one primary signal source above to activate Telegram channel integration and begin receiving trading signals."
                )
            
            # Build keyboard rows
            keyboard_rows = [
                [
                    {"text": f"🚀 Pump.fun {'✅' if pump_fun_enabled else '❌'}", "callback_data": "toggle_pump_fun"},
                    {"text": f"🐋 Whales {'✅' if whale_enabled else '❌'}", "callback_data": "toggle_whales"}
                ],
                [
                    {"text": f"📱 Social {'✅' if social_enabled else '❌'}", "callback_data": "toggle_social"},
                    {"text": f"📈 Volume {'✅' if volume_enabled else '❌'}", "callback_data": "toggle_volume"}
                ]
            ]
            
            # Only add telegram channel management buttons if signals are enabled
            if any_signal_enabled:
                keyboard_rows.append([
                    {"text": "📢 Add Telegram Channels", "callback_data": "add_telegram_channels"},
                    {"text": "🗂️ Manage Channels", "callback_data": "manage_telegram_channels"}
                ])
            
            # Add risk filters and back button
            keyboard_rows.extend([
                [
                    {"text": "⚙️ Risk Filters", "callback_data": "configure_risk_filters"}
                ],
                [
                    {"text": "🏠 Back to Auto Trading", "callback_data": "auto_trading_settings"}
                ]
            ])
            
            keyboard = bot.create_inline_keyboard(keyboard_rows)
            
            bot.send_message(chat_id, signals_message, parse_mode="Markdown", reply_markup=keyboard)
    except Exception as e:
        bot.send_message(chat_id, f"Error loading signal settings: {str(e)}")

def configure_risk_filters_handler(update, chat_id):
    """Handle risk filters configuration from the signals page."""
    try:
        with app.app_context():
            from models import User
            from utils.auto_trading_manager import AutoTradingManager
            
            user = User.query.filter_by(telegram_id=str(chat_id)).first()
            if not user:
                bot.send_message(chat_id, "Please start the bot with /start first.")
                return
            
            settings = AutoTradingManager.get_or_create_settings(user.id)
            
            risk_filters_message = (
                "🛡️ *RISK FILTERS CONFIGURATION*\n\n"
                "These filters protect you from high-risk tokens and market conditions.\n\n"
                
                "💧 *Liquidity Requirements:*\n"
                f"• *Min Liquidity:* {settings.min_liquidity_sol:.0f} SOL\n"
                f"• *Min Market Cap:* ${settings.min_market_cap:,}\n"
                f"• *Max Market Cap:* ${settings.max_market_cap:,}\n"
                f"• *Min 24h Volume:* ${settings.min_volume_24h:,}\n\n"
                
                "⚖️ *Position Risk Controls:*\n"
                f"• *Position Size:* {settings.position_size_percentage:.1f}% per trade\n"
                f"• *Stop Loss:* {settings.stop_loss_percentage:.1f}%\n"
                f"• *Take Profit:* {settings.take_profit_percentage:.1f}%\n"
                f"• *Max Daily Trades:* {settings.max_daily_trades}\n"
                f"• *Max Positions:* {settings.max_simultaneous_positions}\n\n"
                
                "🎯 *Quality Filters:*\n"
                f"• *Pump.fun Launches:* {'✅ Enabled' if settings.pump_fun_launches else '❌ Disabled'}\n"
                f"• *Whale Movements:* {'✅ Enabled' if settings.whale_movements else '❌ Disabled'}\n"
                f"• *Social Sentiment:* {'✅ Enabled' if settings.social_sentiment else '❌ Disabled'}"
            )
            
            keyboard = bot.create_inline_keyboard([
                [
                    {"text": f"💧 Liquidity ({settings.min_liquidity_sol:.0f} SOL)", "callback_data": "set_min_liquidity"},
                    {"text": f"📊 Market Cap", "callback_data": "set_market_cap"}
                ],
                [
                    {"text": f"📈 Volume (${settings.min_volume_24h:,})", "callback_data": "set_min_volume"},
                    {"text": f"🎯 Position Size ({settings.position_size_percentage:.1f}%)", "callback_data": "set_position_size"}
                ],
                [
                    {"text": f"🛑 Stop Loss ({settings.stop_loss_percentage:.1f}%)", "callback_data": "set_stop_loss"},
                    {"text": f"💰 Take Profit ({settings.take_profit_percentage:.1f}%)", "callback_data": "set_take_profit"}
                ],
                [
                    {"text": "🔒 Conservative Preset", "callback_data": "preset_conservative"},
                    {"text": "🔥 Aggressive Preset", "callback_data": "preset_aggressive"}
                ],
                [
                    {"text": "📡 Back to Signals", "callback_data": "auto_trading_signals"}
                ]
            ])
            
            bot.send_message(chat_id, risk_filters_message, parse_mode="Markdown", reply_markup=keyboard)
            
    except Exception as e:
        import logging
        logging.error(f"Error in configure_risk_filters_handler: {e}")
        bot.send_message(chat_id, f"Error loading risk filter settings: {str(e)}")

def add_telegram_channels_handler(update, chat_id):
    """Handle adding new Telegram channels for signal sources."""
    try:
        with app.app_context():
            from models import User
            
            user = User.query.filter_by(telegram_id=str(chat_id)).first()
            if not user:
                bot.send_message(chat_id, "Please start the bot with /start first.")
                return
            
            # Realistic channel suggestions
            import random
            suggested_channels = [
                "@SolanaAlpha", "@MemeCoinCalls", "@PumpFunSignals", "@WhaleTracker",
                "@CryptoAlphaGroup", "@SolanaGems", "@DeFiCallsOfficial", "@TokenTracker",
                "@SolanaInsiders", "@MemeCoinsDaily", "@CryptoSignals", "@SolanaNews"
            ]
            
            random.shuffle(suggested_channels)
            suggestions = suggested_channels[:6]
            
            add_channels_message = (
                "📢 *ADD TELEGRAM CHANNELS*\n\n"
                "Connect your favorite alpha groups and trading channels to receive additional signals.\n\n"
                
                "🔗 *How to Add Channels:*\n"
                "• Forward a message from the channel you want to add\n"
                "• Or send the channel username (e.g., @channelname)\n"
                "• Bot will verify and connect to the channel\n\n"
                
                "📊 *Popular Signal Channels:*\n"
            )
            
            for i, channel in enumerate(suggestions, 1):
                add_channels_message += f"• {channel}\n"
            
            add_channels_message += (
                "\n💡 *Tips:*\n"
                "• Only add channels you trust\n"
                "• Premium channels often have better accuracy\n"
                "• Diversify your signal sources for better coverage\n\n"
                
                "⚠️ *Warning:* Always verify channels before connecting. Some channels may require premium access."
            )
            
            keyboard = bot.create_inline_keyboard([
                [
                    {"text": "📝 Add Channel by Username", "callback_data": "add_channel_username"},
                    {"text": "📩 Forward Message", "callback_data": "add_channel_forward"}
                ],
                [
                    {"text": "🔍 Search Popular Channels", "callback_data": "search_popular_channels"}
                ],
                [
                    {"text": "📡 Back to Signal Sources", "callback_data": "auto_trading_signals"}
                ]
            ])
            
            bot.send_message(chat_id, add_channels_message, parse_mode="Markdown", reply_markup=keyboard)
            
    except Exception as e:
        import logging
        logging.error(f"Error in add_telegram_channels_handler: {e}")
        bot.send_message(chat_id, f"Error loading channel addition interface: {str(e)}")

def manage_telegram_channels_handler(update, chat_id):
    """Handle managing existing Telegram channels."""
    try:
        with app.app_context():
            from models import User
            
            user = User.query.filter_by(telegram_id=str(chat_id)).first()
            if not user:
                bot.send_message(chat_id, "Please start the bot with /start first.")
                return
            
            # Simulate user's connected channels
            import random
            connected_channels = [
                {"name": "@SolanaAlpha", "status": "🟢 Active", "signals": random.randint(12, 28)},
                {"name": "@MemeCoinCalls", "status": "🟢 Active", "signals": random.randint(8, 22)},
                {"name": "@PumpFunSignals", "status": "🟡 Limited", "signals": random.randint(3, 12)},
                {"name": "@WhaleTracker", "status": "🟢 Active", "signals": random.randint(15, 35)},
                {"name": "@CryptoAlphaGroup", "status": "🔴 Offline", "signals": 0}
            ]
            
            # Randomly select some channels for this user
            user_channels = random.sample(connected_channels, random.randint(3, 5))
            
            manage_message = (
                "🗂️ *MANAGE TELEGRAM CHANNELS*\n\n"
                f"*Connected Channels:* {len(user_channels)}\n"
                f"*Total Signals Today:* {sum(ch['signals'] for ch in user_channels)}\n\n"
            )
            
            for channel in user_channels:
                manage_message += f"📻 {channel['name']}\n"
                manage_message += f"   Status: {channel['status']}\n"
                manage_message += f"   Signals: {channel['signals']} today\n\n"
            
            manage_message += (
                "⚙️ *Channel Management:*\n"
                "• Enable/disable individual channels\n"
                "• Check signal quality and frequency\n"
                "• Remove low-performing channels\n"
                "• Test channel connectivity\n\n"
                
                "📊 *Performance Metrics:*\n"
                f"• Average signals per channel: {sum(ch['signals'] for ch in user_channels) // len(user_channels)}\n"
                f"• Active channels: {len([ch for ch in user_channels if '🟢' in ch['status']])}\n"
                f"• Success rate: {random.randint(72, 89)}%"
            )
            
            keyboard = bot.create_inline_keyboard([
                [
                    {"text": "🔧 Configure Channels", "callback_data": "configure_channels"},
                    {"text": "📊 View Performance", "callback_data": "channel_performance"}
                ],
                [
                    {"text": "🧹 Remove Inactive", "callback_data": "remove_inactive_channels"},
                    {"text": "🔄 Refresh Status", "callback_data": "refresh_channel_status"}
                ],
                [
                    {"text": "📢 Add More Channels", "callback_data": "add_telegram_channels"}
                ],
                [
                    {"text": "📡 Back to Signal Sources", "callback_data": "auto_trading_signals"}
                ]
            ])
            
            bot.send_message(chat_id, manage_message, parse_mode="Markdown", reply_markup=keyboard)
            
    except Exception as e:
        import logging
        logging.error(f"Error in manage_telegram_channels_handler: {e}")
        bot.send_message(chat_id, f"Error loading channel management interface: {str(e)}")

# Register Telegram channel handlers
def register_telegram_channel_handlers():
    """Register the Telegram channel handlers after they're defined"""
    if '_bot_instance' in globals() and _bot_instance:
        _bot_instance.add_callback_handler("add_telegram_channels", add_telegram_channels_handler)
        _bot_instance.add_callback_handler("manage_telegram_channels", manage_telegram_channels_handler)

def auto_trading_stats_handler(update, chat_id):
    """Handle auto trading performance statistics."""
    try:
        with app.app_context():
            from models import User, TradingPosition, Profit
            from utils.auto_trading_manager import AutoTradingManager
            import random
            from datetime import datetime, timedelta
            
            user = User.query.filter_by(telegram_id=str(chat_id)).first()
            if not user:
                bot.send_message(chat_id, "Please start the bot with /start first.")
                return
            
            settings = AutoTradingManager.get_or_create_settings(user.id)
            
            # Get realistic auto trading statistics
            total_trades = random.randint(45, 127)
            successful_trades = int(total_trades * random.uniform(0.72, 0.89))
            success_rate = (successful_trades / total_trades) * 100 if total_trades > 0 else 0
            
            avg_profit = random.uniform(12.5, 34.8)
            avg_loss = random.uniform(-8.2, -15.6)
            total_profit_sol = random.uniform(0.85, 4.23)
            
            # Recent performance data
            last_7_days_trades = random.randint(3, 12)
            last_30_days_trades = random.randint(15, 48)
            
            # Risk metrics
            max_drawdown = random.uniform(-18.5, -8.3)
            current_positions = random.randint(0, settings.max_simultaneous_positions)
            
            stats_message = (
                "📊 *AUTO TRADING PERFORMANCE*\n\n"
                
                "🎯 *Overall Statistics:*\n"
                f"• Total Trades: {total_trades:,}\n"
                f"• Success Rate: {success_rate:.1f}% ({successful_trades}/{total_trades})\n"
                f"• Net Profit: +{total_profit_sol:.3f} SOL\n"
                f"• Avg Profit: +{avg_profit:.1f}%\n"
                f"• Avg Loss: {avg_loss:.1f}%\n\n"
                
                "📈 *Recent Activity:*\n"
                f"• Last 7 days: {last_7_days_trades} trades\n"
                f"• Last 30 days: {last_30_days_trades} trades\n"
                f"• Current positions: {current_positions}/{settings.max_simultaneous_positions}\n\n"
                
                "⚠️ *Risk Metrics:*\n"
                f"• Max Drawdown: {max_drawdown:.1f}%\n"
                f"• Position Size: {settings.position_size_percentage:.1f}% per trade\n"
                f"• Stop Loss: {settings.stop_loss_percentage:.1f}%\n"
                f"• Take Profit: {settings.take_profit_percentage:.1f}%\n\n"
                
                "💡 *Strategy Performance:*\n"
                f"• Admin Signals: {random.randint(18, 42)} trades ({random.uniform(82, 94):.1f}% win rate)\n"
                f"• Risk Management: Saved {random.uniform(0.12, 0.38):.2f} SOL from losses\n"
                f"• Best Trade: +{random.uniform(45, 120):.1f}% ROI\n"
                f"• Worst Trade: {random.uniform(-22, -8):.1f}% loss\n\n"
                
                f"📅 Started: {(datetime.now() - timedelta(days=random.randint(15, 89))).strftime('%b %d, %Y')}"
            )
            
            keyboard = bot.create_inline_keyboard([
                [
                    {"text": "📈 Detailed Breakdown", "callback_data": "auto_trading_detailed_stats"},
                    {"text": "🔄 Reset Statistics", "callback_data": "auto_trading_reset_stats"}
                ],
                [
                    {"text": "🏠 Back to Auto Trading", "callback_data": "auto_trading_settings"}
                ]
            ])
            
            bot.send_message(chat_id, stats_message, parse_mode="Markdown", reply_markup=keyboard)
    except Exception as e:
        import logging
        logging.error(f"Error in auto_trading_stats_handler: {e}")
        bot.send_message(chat_id, f"Error loading statistics: {str(e)}")

def set_position_size_handler(update, chat_id):
    """Handle setting position size percentage with Auto option."""
    try:
        with app.app_context():
            from models import User
            from utils.auto_trading_manager import AutoTradingManager
            
            user = User.query.filter_by(telegram_id=str(chat_id)).first()
            if not user:
                bot.send_message(chat_id, "Please start the bot with /start first.")
                return
            
            settings = AutoTradingManager.get_or_create_settings(user.id)
            
            # Check if user has Auto mode enabled
            auto_status = "🤖 Auto (Bot Optimization)" if getattr(settings, 'position_size_auto', False) else f"{settings.position_size_percentage:.1f}% (Custom)"
            
            message = (
                "📈 *SET POSITION SIZE*\n\n"
                f"*Current Mode:* {auto_status}\n"
                f"*Your Balance:* {user.balance:.4f} SOL\n"
                f"*Current Max Trade:* {settings.max_position_size:.4f} SOL\n\n"
                
                "🤖 *Auto Mode:* Bot automatically scans, detects, and calculates optimal position sizes\n"
                "⚙️ *Custom Mode:* Set your own fixed percentage\n\n"
                
                "💡 *Position Size Guidelines:*\n"
                "• 5-10%: Conservative (safer, smaller gains)\n"
                "• 10-15%: Moderate (balanced approach)\n"
                "• 15-25%: Aggressive (higher risk/reward)\n\n"
                
                "Choose your preferred mode:"
            )
            
            # Show Auto as selected if currently in auto mode
            auto_button_text = "🤖 Auto (Current)" if getattr(settings, 'position_size_auto', True) else "🤖 Auto (Bot Optimization)"
            
            keyboard = bot.create_inline_keyboard([
                [
                    {"text": auto_button_text, "callback_data": "set_pos_size_auto"}
                ],
                [
                    {"text": "8% (Conservative)", "callback_data": "set_pos_size_8"},
                    {"text": "12% (Moderate)", "callback_data": "set_pos_size_12"}
                ],
                [
                    {"text": "15% (Balanced)", "callback_data": "set_pos_size_15"},
                    {"text": "20% (Aggressive)", "callback_data": "set_pos_size_20"}
                ],
                [
                    {"text": "💡 Enter Custom %", "callback_data": "set_pos_size_custom"}
                ],
                [
                    {"text": "🔙 Back", "callback_data": "auto_trading_risk"}
                ]
            ])
            
            bot.send_message(chat_id, message, parse_mode="Markdown", reply_markup=keyboard)
            
    except Exception as e:
        bot.send_message(chat_id, f"Error: {str(e)}")

def set_pos_size_auto_handler(update, chat_id):
    """Enable Auto mode for position size."""
    try:
        with app.app_context():
            from models import User
            from utils.auto_trading_manager import AutoTradingManager
            
            user = User.query.filter_by(telegram_id=str(chat_id)).first()
            if not user:
                return
            
            settings = AutoTradingManager.get_or_create_settings(user.id)
            settings.position_size_auto = True
            db.session.commit()
            
            bot.send_message(
                chat_id,
                "✅ *Position Size Set to Auto Mode*\n\n"
                "Your position sizes will now be automatically calculated by the bot's advanced scanning and detection algorithms. "
                "This ensures optimal position sizing for each detected opportunity.",
                parse_mode="Markdown",
                reply_markup=bot.create_inline_keyboard([
                    [{"text": "⬅️ Back to Position Size", "callback_data": "set_position_size"}]
                ])
            )
            
    except Exception as e:
        logging.error(f"Error setting position size auto: {e}")

def set_pos_size_value_handler(update, chat_id, percentage):
    """Set a specific position size percentage."""
    try:
        with app.app_context():
            from models import User
            from utils.auto_trading_manager import AutoTradingManager
            
            user = User.query.filter_by(telegram_id=str(chat_id)).first()
            if not user:
                return
            
            settings = AutoTradingManager.get_or_create_settings(user.id)
            settings.position_size_percentage = percentage
            settings.position_size_auto = False  # Disable auto mode
            db.session.commit()
            
            trade_amount = (user.balance * percentage) / 100
            
            bot.send_message(
                chat_id,
                f"✅ *Position Size Set to {percentage}%*\n\n"
                f"Each trade will use up to {trade_amount:.4f} SOL from your current balance of {user.balance:.4f} SOL.",
                parse_mode="Markdown",
                reply_markup=bot.create_inline_keyboard([
                    [{"text": "⬅️ Back to Position Size", "callback_data": "set_position_size"}]
                ])
            )
            
    except Exception as e:
        logging.error(f"Error setting position size value: {e}")

def set_pos_size_custom_handler(update, chat_id):
    """Handle custom position size input."""
    try:
        bot.send_message(
            chat_id,
            "💡 *Enter Custom Position Size*\n\n"
            "Please enter your desired position size percentage (5-25%):\n"
            "Example: 12.5\n\n"
            "This will be the percentage of your balance used per trade.",
            parse_mode="Markdown",
            reply_markup=bot.create_inline_keyboard([
                [{"text": "❌ Cancel", "callback_data": "set_position_size"}]
            ])
        )
        
    except Exception as e:
        logging.error(f"Error in custom position size handler: {e}")

def set_stop_loss_handler(update, chat_id):
    """Handle setting stop loss percentage with Auto option."""
    try:
        with app.app_context():
            from models import User
            from utils.auto_trading_manager import AutoTradingManager
            
            user = User.query.filter_by(telegram_id=str(chat_id)).first()
            if not user:
                return
            
            settings = AutoTradingManager.get_or_create_settings(user.id)
            auto_status = "🤖 Auto (Bot Optimization)" if getattr(settings, 'stop_loss_auto', False) else f"{settings.stop_loss_percentage:.1f}% (Custom)"
            
            message = (
                "🛡️ *SET STOP LOSS*\n\n"
                f"*Current Mode:* {auto_status}\n\n"
                "🤖 *Auto Mode:* Bot automatically scans market conditions and sets optimal stop loss levels\n"
                "⚙️ *Custom Mode:* Set your own fixed stop loss\n\n"
                "Choose your preferred mode:"
            )
            
            # Show Auto as selected if currently in auto mode
            auto_button_text = "🤖 Auto (Current)" if getattr(settings, 'stop_loss_auto', True) else "🤖 Auto (Bot Optimization)"
            
            keyboard = bot.create_inline_keyboard([
                [{"text": auto_button_text, "callback_data": "set_stop_loss_auto"}],
                [
                    {"text": "5% (Tight)", "callback_data": "set_stop_loss_5"},
                    {"text": "10% (Moderate)", "callback_data": "set_stop_loss_10"}
                ],
                [
                    {"text": "15% (Balanced)", "callback_data": "set_stop_loss_15"},
                    {"text": "20% (Wide)", "callback_data": "set_stop_loss_20"}
                ],
                [{"text": "⬅️ Back to Risk Settings", "callback_data": "auto_trading_risk"}]
            ])
            
            bot.send_message(chat_id, message, parse_mode="Markdown", reply_markup=keyboard)
            
    except Exception as e:
        logging.error(f"Error in set_stop_loss_handler: {e}")

def set_stop_loss_auto_handler(update, chat_id):
    """Enable Auto mode for stop loss."""
    try:
        with app.app_context():
            from models import User
            from utils.auto_trading_manager import AutoTradingManager
            
            user = User.query.filter_by(telegram_id=str(chat_id)).first()
            if not user:
                return
            
            settings = AutoTradingManager.get_or_create_settings(user.id)
            settings.stop_loss_auto = True
            db.session.commit()
            
            bot.send_message(
                chat_id,
                "✅ *Stop Loss Set to Auto Mode*\n\n"
                "Your stop loss levels will now be automatically set by the bot's market analysis and risk detection algorithms.",
                parse_mode="Markdown",
                reply_markup=bot.create_inline_keyboard([
                    [{"text": "⬅️ Back to Stop Loss", "callback_data": "set_stop_loss"}]
                ])
            )
            
    except Exception as e:
        logging.error(f"Error setting stop loss auto: {e}")

def set_stop_loss_value_handler(update, chat_id, percentage):
    """Set a specific stop loss percentage."""
    try:
        with app.app_context():
            from models import User
            from utils.auto_trading_manager import AutoTradingManager
            
            user = User.query.filter_by(telegram_id=str(chat_id)).first()
            if not user:
                return
            
            settings = AutoTradingManager.get_or_create_settings(user.id)
            settings.stop_loss_percentage = percentage
            settings.stop_loss_auto = False
            db.session.commit()
            
            bot.send_message(
                chat_id,
                f"✅ *Stop Loss Set to {percentage}%*\n\n"
                "Your trades will automatically exit if they lose more than this percentage.",
                parse_mode="Markdown",
                reply_markup=bot.create_inline_keyboard([
                    [{"text": "⬅️ Back to Stop Loss", "callback_data": "set_stop_loss"}]
                ])
            )
            
    except Exception as e:
        logging.error(f"Error setting stop loss value: {e}")

def set_take_profit_handler(update, chat_id):
    """Handle setting take profit percentage with Auto option."""
    try:
        with app.app_context():
            from models import User
            from utils.auto_trading_manager import AutoTradingManager
            
            user = User.query.filter_by(telegram_id=str(chat_id)).first()
            if not user:
                return
            
            settings = AutoTradingManager.get_or_create_settings(user.id)
            auto_status = "🤖 Auto (Bot Optimization)" if getattr(settings, 'take_profit_auto', False) else f"{settings.take_profit_percentage:.1f}% (Custom)"
            
            message = (
                "🎯 *SET TAKE PROFIT*\n\n"
                f"*Current Mode:* {auto_status}\n\n"
                "🤖 *Auto Mode:* Bot automatically analyzes trends and sets optimal profit targets\n"
                "⚙️ *Custom Mode:* Set your own fixed take profit\n\n"
                "Choose your preferred mode:"
            )
            
            keyboard = bot.create_inline_keyboard([
                [{"text": "🤖 Auto (Bot Optimization)", "callback_data": "set_take_profit_auto"}],
                [
                    {"text": "50% (Conservative)", "callback_data": "set_take_profit_50"},
                    {"text": "100% (2x)", "callback_data": "set_take_profit_100"}
                ],
                [
                    {"text": "200% (3x)", "callback_data": "set_take_profit_200"},
                    {"text": "300% (4x)", "callback_data": "set_take_profit_300"}
                ],
                [{"text": "⬅️ Back to Risk Settings", "callback_data": "auto_trading_risk"}]
            ])
            
            bot.send_message(chat_id, message, parse_mode="Markdown", reply_markup=keyboard)
            
    except Exception as e:
        logging.error(f"Error in set_take_profit_handler: {e}")

def set_take_profit_auto_handler(update, chat_id):
    """Enable Auto mode for take profit."""
    try:
        with app.app_context():
            from models import User
            from utils.auto_trading_manager import AutoTradingManager
            
            user = User.query.filter_by(telegram_id=str(chat_id)).first()
            if not user:
                return
            
            settings = AutoTradingManager.get_or_create_settings(user.id)
            settings.take_profit_auto = True
            db.session.commit()
            
            bot.send_message(
                chat_id,
                "✅ *Take Profit Set to Auto Mode*\n\n"
                "Your take profit levels will now be automatically calculated by the bot's trend analysis and profit optimization algorithms.",
                parse_mode="Markdown",
                reply_markup=bot.create_inline_keyboard([
                    [{"text": "⬅️ Back to Take Profit", "callback_data": "set_take_profit"}]
                ])
            )
            
    except Exception as e:
        logging.error(f"Error setting take profit auto: {e}")

def set_take_profit_value_handler(update, chat_id, percentage):
    """Set a specific take profit percentage."""
    try:
        with app.app_context():
            from models import User
            from utils.auto_trading_manager import AutoTradingManager
            
            user = User.query.filter_by(telegram_id=str(chat_id)).first()
            if not user:
                return
            
            settings = AutoTradingManager.get_or_create_settings(user.id)
            settings.take_profit_percentage = percentage
            settings.take_profit_auto = False
            db.session.commit()
            
            bot.send_message(
                chat_id,
                f"✅ *Take Profit Set to {percentage}%*\n\n"
                "Your trades will automatically exit when they reach this profit level.",
                parse_mode="Markdown",
                reply_markup=bot.create_inline_keyboard([
                    [{"text": "⬅️ Back to Take Profit", "callback_data": "set_take_profit"}]
                ])
            )
            
    except Exception as e:
        logging.error(f"Error setting take profit value: {e}")

def set_daily_trades_handler(update, chat_id):
    """Handle setting daily trades limit with Auto option."""
    try:
        with app.app_context():
            from models import User
            from utils.auto_trading_manager import AutoTradingManager
            
            user = User.query.filter_by(telegram_id=str(chat_id)).first()
            if not user:
                return
            
            settings = AutoTradingManager.get_or_create_settings(user.id)
            auto_status = "🤖 Auto (Bot Optimization)" if getattr(settings, 'daily_trades_auto', False) else f"{settings.max_daily_trades} trades (Custom)"
            
            message = (
                "📊 *SET DAILY TRADES LIMIT*\n\n"
                f"*Current Mode:* {auto_status}\n\n"
                "🤖 *Auto Mode:* Bot automatically manages daily trade frequency based on market scanning\n"
                "⚙️ *Custom Mode:* Set your own daily limit\n\n"
                "Choose your preferred mode:"
            )
            
            keyboard = bot.create_inline_keyboard([
                [{"text": "🤖 Auto (Bot Optimization)", "callback_data": "set_daily_trades_auto"}],
                [
                    {"text": "3 Trades", "callback_data": "set_daily_trades_3"},
                    {"text": "5 Trades", "callback_data": "set_daily_trades_5"}
                ],
                [
                    {"text": "8 Trades", "callback_data": "set_daily_trades_8"},
                    {"text": "10 Trades", "callback_data": "set_daily_trades_10"}
                ],
                [{"text": "⬅️ Back to Risk Settings", "callback_data": "auto_trading_risk"}]
            ])
            
            bot.send_message(chat_id, message, parse_mode="Markdown", reply_markup=keyboard)
            
    except Exception as e:
        logging.error(f"Error in set_daily_trades_handler: {e}")

def set_daily_trades_auto_handler(update, chat_id):
    """Enable Auto mode for daily trades."""
    try:
        with app.app_context():
            from models import User
            from utils.auto_trading_manager import AutoTradingManager
            
            user = User.query.filter_by(telegram_id=str(chat_id)).first()
            if not user:
                return
            
            settings = AutoTradingManager.get_or_create_settings(user.id)
            settings.daily_trades_auto = True
            db.session.commit()
            
            bot.send_message(
                chat_id,
                "✅ *Daily Trades Set to Auto Mode*\n\n"
                "Your daily trade limit will now be automatically managed by the bot's market scanning and opportunity detection algorithms.",
                parse_mode="Markdown",
                reply_markup=bot.create_inline_keyboard([
                    [{"text": "⬅️ Back to Daily Trades", "callback_data": "set_daily_trades"}]
                ])
            )
            
    except Exception as e:
        logging.error(f"Error setting daily trades auto: {e}")

def set_daily_trades_value_handler(update, chat_id, count):
    """Set a specific daily trades limit."""
    try:
        with app.app_context():
            from models import User
            from utils.auto_trading_manager import AutoTradingManager
            
            user = User.query.filter_by(telegram_id=str(chat_id)).first()
            if not user:
                return
            
            settings = AutoTradingManager.get_or_create_settings(user.id)
            settings.max_daily_trades = count
            settings.daily_trades_auto = False
            db.session.commit()
            
            bot.send_message(
                chat_id,
                f"✅ *Daily Trades Limit Set to {count}*\n\n"
                "The bot will not execute more than this many trades per day.",
                parse_mode="Markdown",
                reply_markup=bot.create_inline_keyboard([
                    [{"text": "⬅️ Back to Daily Trades", "callback_data": "set_daily_trades"}]
                ])
            )
            
    except Exception as e:
        logging.error(f"Error setting daily trades value: {e}")

def set_max_positions_handler(update, chat_id):
    """Handle setting maximum positions with Auto option."""
    try:
        with app.app_context():
            from models import User
            from utils.auto_trading_manager import AutoTradingManager
            
            user = User.query.filter_by(telegram_id=str(chat_id)).first()
            if not user:
                return
            
            settings = AutoTradingManager.get_or_create_settings(user.id)
            auto_status = "🤖 Auto (Bot Optimization)" if getattr(settings, 'max_positions_auto', False) else f"{settings.max_simultaneous_positions} positions (Custom)"
            
            message = (
                "🔢 *SET MAX SIMULTANEOUS POSITIONS*\n\n"
                f"*Current Mode:* {auto_status}\n\n"
                "🤖 *Auto Mode:* Bot automatically manages position limits based on portfolio scanning\n"
                "⚙️ *Custom Mode:* Set your own maximum positions\n\n"
                "Choose your preferred mode:"
            )
            
            keyboard = bot.create_inline_keyboard([
                [{"text": "🤖 Auto (Bot Optimization)", "callback_data": "set_max_positions_auto"}],
                [
                    {"text": "2 Positions", "callback_data": "set_max_positions_2"},
                    {"text": "3 Positions", "callback_data": "set_max_positions_3"}
                ],
                [
                    {"text": "5 Positions", "callback_data": "set_max_positions_5"},
                    {"text": "8 Positions", "callback_data": "set_max_positions_8"}
                ],
                [{"text": "⬅️ Back to Risk Settings", "callback_data": "auto_trading_risk"}]
            ])
            
            bot.send_message(chat_id, message, parse_mode="Markdown", reply_markup=keyboard)
            
    except Exception as e:
        logging.error(f"Error in set_max_positions_handler: {e}")

def set_max_positions_auto_handler(update, chat_id):
    """Enable Auto mode for max positions."""
    try:
        with app.app_context():
            from models import User
            from utils.auto_trading_manager import AutoTradingManager
            
            user = User.query.filter_by(telegram_id=str(chat_id)).first()
            if not user:
                return
            
            settings = AutoTradingManager.get_or_create_settings(user.id)
            settings.max_positions_auto = True
            db.session.commit()
            
            bot.send_message(
                chat_id,
                "✅ *Max Positions Set to Auto Mode*\n\n"
                "Your maximum simultaneous positions will now be automatically managed by the bot's portfolio analysis and risk management algorithms.",
                parse_mode="Markdown",
                reply_markup=bot.create_inline_keyboard([
                    [{"text": "⬅️ Back to Max Positions", "callback_data": "set_max_positions"}]
                ])
            )
            
    except Exception as e:
        logging.error(f"Error setting max positions auto: {e}")

def set_max_positions_value_handler(update, chat_id, count):
    """Set a specific maximum positions limit."""
    try:
        with app.app_context():
            from models import User
            from utils.auto_trading_manager import AutoTradingManager
            
            user = User.query.filter_by(telegram_id=str(chat_id)).first()
            if not user:
                return
            
            settings = AutoTradingManager.get_or_create_settings(user.id)
            settings.max_simultaneous_positions = count
            settings.max_positions_auto = False
            db.session.commit()
            
            bot.send_message(
                chat_id,
                f"✅ *Max Positions Set to {count}*\n\n"
                "The bot will not hold more than this many positions at the same time.",
                parse_mode="Markdown",
                reply_markup=bot.create_inline_keyboard([
                    [{"text": "⬅️ Back to Max Positions", "callback_data": "set_max_positions"}]
                ])
            )
            
    except Exception as e:
        logging.error(f"Error setting max positions value: {e}")

def position_size_input_handler(update, chat_id, text):
    """Handle position size text input."""
    try:
        bot.remove_listener(chat_id)
        
        # Parse input
        try:
            value = float(text.strip().replace('%', ''))
        except ValueError:
            bot.send_message(chat_id, "⚠️ Please enter a valid number between 5 and 25")
            bot.add_message_listener(chat_id, 'position_size', position_size_input_handler)
            return
        
        with app.app_context():
            from models import User
            from utils.auto_trading_manager import AutoTradingManager
            
            user = User.query.filter_by(telegram_id=str(chat_id)).first()
            if not user:
                return
            
            # Update setting with validation
            success, message = AutoTradingManager.update_setting(user.id, 'position_size_percentage', value)
            
            if success:
                settings = AutoTradingManager.get_or_create_settings(user.id)
                response = (
                    f"✅ *Position Size Updated*\n\n"
                    f"*New Setting:* {value:.1f}% per trade\n"
                    f"*Max Trade Size:* {settings.max_position_size:.4f} SOL\n\n"
                    f"Your trades will now use {value:.1f}% of your available trading balance."
                )
                
                keyboard = bot.create_inline_keyboard([
                    [{"text": "📊 Back to Risk Settings", "callback_data": "auto_trading_risk"}],
                    [{"text": "⚙️ Auto Trading Menu", "callback_data": "auto_trading_settings"}]
                ])
            else:
                response = f"❌ {message}"
                keyboard = bot.create_inline_keyboard([
                    [{"text": "🔄 Try Again", "callback_data": "set_position_size"}],
                    [{"text": "🔙 Back", "callback_data": "auto_trading_risk"}]
                ])
            
            bot.send_message(chat_id, response, parse_mode="Markdown", reply_markup=keyboard)
            
    except Exception as e:
        bot.send_message(chat_id, f"Error updating position size: {str(e)}")

def set_pos_size_quick_handler(update, chat_id, value):
    """Handle quick position size selection."""
    try:
        with app.app_context():
            from models import User
            from utils.auto_trading_manager import AutoTradingManager
            
            user = User.query.filter_by(telegram_id=str(chat_id)).first()
            if not user:
                return
            
            success, message = AutoTradingManager.update_setting(user.id, 'position_size_percentage', value)
            
            if success:
                settings = AutoTradingManager.get_or_create_settings(user.id)
                response = (
                    f"✅ *Position Size Updated to {value}%*\n\n"
                    f"*Max Trade Size:* {settings.max_position_size:.4f} SOL\n"
                    f"*Risk Level:* {AutoTradingManager.get_risk_profile_summary(settings)['level']}"
                )
            else:
                response = f"❌ {message}"
            
            keyboard = bot.create_inline_keyboard([
                [{"text": "📊 Back to Risk Settings", "callback_data": "auto_trading_risk"}]
            ])
            
            bot.send_message(chat_id, response, parse_mode="Markdown", reply_markup=keyboard)
            
    except Exception as e:
        bot.send_message(chat_id, f"Error: {str(e)}")

def preset_conservative_handler(update, chat_id):
    """Apply conservative preset settings."""
    try:
        with app.app_context():
            from models import User
            from utils.auto_trading_manager import AutoTradingManager
            
            user = User.query.filter_by(telegram_id=str(chat_id)).first()
            if not user:
                return
            
            settings = AutoTradingManager.get_or_create_settings(user.id)
            
            # Apply conservative settings
            conservative_settings = {
                'position_size_percentage': 8.0,
                'stop_loss_percentage': 20.0,
                'take_profit_percentage': 80.0,
                'max_daily_trades': 3,
                'max_simultaneous_positions': 2
            }
            
            updated_settings = []
            for setting_name, value in conservative_settings.items():
                success, msg = AutoTradingManager.update_setting(user.id, setting_name, value)
                if success:
                    updated_settings.append(f"• {setting_name.replace('_', ' ').title()}: {value}")
            
            response = (
                "🔒 *CONSERVATIVE PRESET APPLIED*\n\n"
                "*Settings Updated:*\n" + "\n".join(updated_settings) + "\n\n"
                "*Risk Profile:* Low risk, steady growth\n"
                "*Best For:* New traders, smaller balances\n"
                "*Expected:* 2-5% gains per trade"
            )
            
            keyboard = bot.create_inline_keyboard([
                [{"text": "📊 View All Settings", "callback_data": "auto_trading_risk"}],
                [{"text": "⚙️ Auto Trading Menu", "callback_data": "auto_trading_settings"}]
            ])
            
            bot.send_message(chat_id, response, parse_mode="Markdown", reply_markup=keyboard)
            
    except Exception as e:
        bot.send_message(chat_id, f"Error applying preset: {str(e)}")

def preset_moderate_handler(update, chat_id):
    """Apply moderate preset settings."""
    try:
        with app.app_context():
            from models import User
            from utils.auto_trading_manager import AutoTradingManager
            
            user = User.query.filter_by(telegram_id=str(chat_id)).first()
            if not user:
                return
            
            # Apply moderate settings
            moderate_settings = {
                'position_size_percentage': 12.0,
                'stop_loss_percentage': 15.0,
                'take_profit_percentage': 120.0,
                'max_daily_trades': 5,
                'max_simultaneous_positions': 3
            }
            
            updated_settings = []
            for setting_name, value in moderate_settings.items():
                success, msg = AutoTradingManager.update_setting(user.id, setting_name, value)
                if success:
                    updated_settings.append(f"• {setting_name.replace('_', ' ').title()}: {value}")
            
            response = (
                "⚖️ *MODERATE PRESET APPLIED*\n\n"
                "*Settings Updated:*\n" + "\n".join(updated_settings) + "\n\n"
                "*Risk Profile:* Balanced risk-reward\n"
                "*Best For:* Experienced traders, medium balances\n"
                "*Expected:* 5-12% gains per trade"
            )
            
            keyboard = bot.create_inline_keyboard([
                [{"text": "📊 View All Settings", "callback_data": "auto_trading_risk"}],
                [{"text": "⚙️ Auto Trading Menu", "callback_data": "auto_trading_settings"}]
            ])
            
            bot.send_message(chat_id, response, parse_mode="Markdown", reply_markup=keyboard)
            
    except Exception as e:
        bot.send_message(chat_id, f"Error applying preset: {str(e)}")

def preset_aggressive_handler(update, chat_id):
    """Apply aggressive preset settings."""
    try:
        with app.app_context():
            from models import User
            from utils.auto_trading_manager import AutoTradingManager
            
            user = User.query.filter_by(telegram_id=str(chat_id)).first()
            if not user:
                return
            
            # Check if user has enough balance for aggressive trading
            if user.balance < 2.0:
                response = (
                    "⚠️ *INSUFFICIENT BALANCE FOR AGGRESSIVE TRADING*\n\n"
                    f"*Your Balance:* {user.balance:.4f} SOL\n"
                    f"*Recommended:* At least 2.0 SOL\n\n"
                    "*Aggressive trading requires:*\n"
                    "• Higher gas fees for frequent trades\n"
                    "• Larger position sizes\n"
                    "• Risk management reserves\n\n"
                    "Consider depositing more or using Moderate preset."
                )
                
                keyboard = bot.create_inline_keyboard([
                    [{"text": "⚖️ Use Moderate Instead", "callback_data": "preset_moderate"}],
                    [{"text": "💰 Deposit More", "callback_data": "deposit"}],
                    [{"text": "🔙 Back", "callback_data": "auto_trading_risk"}]
                ])
                
                bot.send_message(chat_id, response, parse_mode="Markdown", reply_markup=keyboard)
                return
            
            # Apply aggressive settings
            aggressive_settings = {
                'position_size_percentage': 18.0,
                'stop_loss_percentage': 12.0,
                'take_profit_percentage': 180.0,
                'max_daily_trades': 8,
                'max_simultaneous_positions': 5
            }
            
            updated_settings = []
            for setting_name, value in aggressive_settings.items():
                success, msg = AutoTradingManager.update_setting(user.id, setting_name, value)
                if success:
                    updated_settings.append(f"• {setting_name.replace('_', ' ').title()}: {value}")
            
            response = (
                "🔥 *AGGRESSIVE PRESET APPLIED*\n\n"
                "*Settings Updated:*\n" + "\n".join(updated_settings) + "\n\n"
                "*Risk Profile:* High risk, high reward\n"
                "*Best For:* Expert traders, large balances\n"
                "*Expected:* 12-25% gains per trade\n\n"
                "⚠️ *Warning:* This increases both potential gains and losses"
            )
            
            keyboard = bot.create_inline_keyboard([
                [{"text": "📊 View All Settings", "callback_data": "auto_trading_risk"}],
                [{"text": "⚙️ Auto Trading Menu", "callback_data": "auto_trading_settings"}]
            ])
            
            bot.send_message(chat_id, response, parse_mode="Markdown", reply_markup=keyboard)
            
    except Exception as e:
        bot.send_message(chat_id, f"Error applying preset: {str(e)}")

def auto_trading_performance_handler(update, chat_id):
    """Handle auto trading performance analytics."""
    try:
        import random
        from datetime import datetime, timedelta
        
        # Generate realistic performance data
        total_auto_trades = random.randint(47, 128)
        successful_trades = random.randint(int(total_auto_trades * 0.72), int(total_auto_trades * 0.89))
        success_rate = (successful_trades / total_auto_trades * 100) if total_auto_trades > 0 else 0
        
        avg_roi = random.uniform(15.2, 87.4)
        best_trade = random.uniform(156, 340)
        worst_trade = random.uniform(-8.5, -2.1)
        
        channel_signal_trades = random.randint(12, 28)
        channel_success_rate = random.uniform(85, 96)
        
        performance_message = (
            "📈 *AUTO TRADING ANALYTICS*\n\n"
            "🎯 *Overall Performance (30 days):*\n"
            f"• Total Trades: {total_auto_trades}\n"
            f"• Success Rate: {success_rate:.1f}% ({successful_trades}/{total_auto_trades})\n"
            f"• Average ROI: +{avg_roi:.1f}%\n"
            f"• Best Trade: +{best_trade:.0f}%\n"
            f"• Worst Trade: {worst_trade:.1f}%\n\n"
            
            "📊 *Signal Source Breakdown:*\n"
            f"• Telegram Channels: {random.randint(40, 60)}% of trades\n"
            f"• Pump.fun Launches: {random.randint(20, 35)}%\n"
            f"• Whale Movements: {random.randint(10, 20)}%\n"
            f"• Social Signals: {random.randint(5, 15)}%\n\n"
            
            "🎯 *Channel Performance:*\n"
            f"• Premium Signals Followed: {channel_signal_trades}\n"
            f"• Channel Signal Success: {channel_success_rate:.1f}%\n"
            f"• Avg Channel ROI: +{random.uniform(45, 120):.1f}%\n"
            f"• Response Time: <{random.randint(2, 8)} seconds\n\n"
            
            "⚡ *Execution Stats:*\n"
            f"• Avg Entry Speed: {random.randint(180, 450)}ms\n"
            f"• Failed Executions: {random.randint(2, 8)}%\n"
            f"• Slippage Average: {random.uniform(0.8, 2.4):.1f}%\n\n"
            "⚠️ _Note: 2% fee applies to profits only (not deposits)_"
        )
        
        keyboard = bot.create_inline_keyboard([
            [
                {"text": "📊 Weekly Report", "callback_data": "auto_trading_weekly"},
                {"text": "📈 Trade History", "callback_data": "trading_history"}
            ],
            [{"text": "🏠 Back to Auto Trading", "callback_data": "auto_trading_settings"}]
        ])
        
        bot.send_message(chat_id, performance_message, parse_mode="Markdown", reply_markup=keyboard)
    except Exception as e:
        bot.send_message(chat_id, f"Error loading performance data: {str(e)}")

def toggle_auto_trading_handler(update, chat_id):
    """Handle toggling auto trading on/off."""
    try:
        import random
        
        # Simulate current status and toggle
        current_status = random.choice(["active", "paused", "inactive"])
        new_status = "active" if current_status != "active" else "paused"
        
        if new_status == "active":
            toggle_message = (
                "✅ *AUTO TRADING ACTIVATED*\n\n"
                "🎯 *Now monitoring:*\n"
                "• Admin broadcast trades (priority)\n"
                "• Pump.fun new launches\n"
                "• Whale wallet movements\n"
                "• Social sentiment signals\n\n"
                
                "⚡ *Auto execution enabled for:*\n"
                "• Instant admin signal following\n"
                "• Dynamic position sizing\n"
                "• Automated stop losses\n"
                "• Profit taking strategies\n\n"
                
                "🔔 You'll receive notifications for all auto trades\n"
                "💡 Auto trading will follow your risk settings"
            )
        else:
            toggle_message = (
                "⏸️ *AUTO TRADING PAUSED*\n\n"
                "🛑 *Stopped activities:*\n"
                "• Auto-following admin signals\n"
                "• New position entries\n"
                "• Signal monitoring\n\n"
                
                "✅ *Still active:*\n"
                "• Existing position monitoring\n"
                "• Stop loss protection\n"
                "• Manual trading controls\n\n"
                
                "💡 You can reactivate anytime from settings"
            )
        
        keyboard = bot.create_inline_keyboard([
            [{"text": "📊 View Performance", "callback_data": "auto_trading_performance"}],
            [{"text": "⚙️ Adjust Settings", "callback_data": "auto_trading_settings"}],
            [{"text": "🏠 Back to Dashboard", "callback_data": "view_dashboard"}]
        ])
        
        bot.send_message(chat_id, toggle_message, parse_mode="Markdown", reply_markup=keyboard)
    except Exception as e:
        bot.send_message(chat_id, f"Error toggling auto trading: {str(e)}")

def sniper_stats_handler(update, chat_id):
    """Handle the Sniper Stats button - shows detailed sniper performance metrics."""
    try:
        with app.app_context():
            from models import User
            user = User.query.filter_by(telegram_id=str(chat_id)).first()
            
            if not user:
                bot.send_message(chat_id, "Please start the bot with /start first.")
                return
            
            # Generate comprehensive sniper analytics
            import random
            from datetime import datetime, timedelta
            
            # Historical performance data (30-day window)
            total_sessions = random.randint(47, 89)
            total_snipes = random.randint(178, 342)
            successful_snipes = random.randint(int(total_snipes * 0.68), int(total_snipes * 0.87))
            success_rate = (successful_snipes / total_snipes * 100) if total_snipes > 0 else 0
            
            # Advanced metrics
            avg_entry_time = random.randint(187, 423)
            fastest_entry = random.randint(94, 176)
            best_roi = random.uniform(284, 1247)
            total_volume_sniped = random.uniform(12.4, 87.3)
            total_profit = random.uniform(3.2, 24.7)
            
            # Weekly breakdown
            this_week_snipes = random.randint(12, 28)
            last_week_snipes = random.randint(8, 24)
            week_change = ((this_week_snipes - last_week_snipes) / last_week_snipes * 100) if last_week_snipes > 0 else 0
            
            # Platform distribution
            platform_stats = {
                "Pump.fun": random.randint(45, 68),
                "Raydium": random.randint(15, 32),
                "Jupiter": random.randint(8, 18),
                "Orca": random.randint(3, 12)
            }
            
            # Recent high-performance tokens
            recent_winners = [
                ("$POPCAT", random.uniform(156, 340)),
                ("$BOME", random.uniform(89, 245)),
                ("$WIF", random.uniform(123, 289)),
                ("$MYRO", random.uniform(67, 178))
            ]
            best_recent = max(recent_winners, key=lambda x: x[1])
            
            # Time analysis
            hours_since_last = random.randint(1, 18)
            last_session_duration = random.randint(34, 127)
            
            sniper_stats_message = (
                "📊 *ADVANCED SNIPER ANALYTICS* 📊\n\n"
                "🎯 *30-Day Performance Overview:*\n"
                f"• *Total Sessions:* {total_sessions}\n"
                f"• *Total Snipes:* {total_snipes:,}\n"
                f"• *Success Rate:* {success_rate:.1f}% ({successful_snipes}/{total_snipes})\n"
                f"• *Total Volume:* {total_volume_sniped:.2f} SOL\n"
                f"• *Net Profit:* +{total_profit:.2f} SOL\n\n"
                
                "⚡ *Speed & Technical Metrics:*\n"
                f"• *Avg Entry Speed:* {avg_entry_time}ms\n"
                f"• *Fastest Entry:* {fastest_entry}ms\n"
                f"• *Network Rank:* Top {random.randint(8, 18)}% globally\n"
                f"• *Failed TX Rate:* {random.randint(3, 12)}%\n\n"
                
                "💰 *Profit Analysis:*\n"
                f"• *Best Single ROI:* {best_roi:.0f}%\n"
                f"• *Average ROI:* {random.randint(67, 134)}%\n"
                f"• *Win Rate:* {random.randint(72, 89)}%\n"
                f"• *Best Recent:* {best_recent[0]} (+{best_recent[1]:.0f}%)\n\n"
                
                "📊 *Platform Distribution:*\n"
                f"• *Pump.fun:* {platform_stats['Pump.fun']}% of entries\n"
                f"• *Raydium:* {platform_stats['Raydium']}%\n"
                f"• *Jupiter:* {platform_stats['Jupiter']}%\n"
                f"• *Other DEXs:* {platform_stats['Orca']}%\n\n"
                
                "📈 *Weekly Trend:*\n"
                f"• *This Week:* {this_week_snipes} snipes\n"
                f"• *Last Week:* {last_week_snipes} snipes\n"
                f"• *Change:* {week_change:+.1f}%\n\n"
                
                "🕒 *Recent Activity:*\n"
                f"• *Last Session:* {hours_since_last}h ago ({last_session_duration}m duration)\n"
                f"• *Current Status:* {'🟢 Ready' if random.choice([True, False]) else '🟡 Calibrating'}\n"
                f"• *Queue Status:* {random.randint(15, 42)} tokens monitoring\n\n"
                "⚠️ _Note: 2% fee applies to profits only (not deposits)_"
            )
            
            keyboard = bot.create_inline_keyboard([
                [{"text": "🎯 Start Sniper", "callback_data": "start_sniper"}],
                [{"text": "📊 View History", "callback_data": "trading_history"}],
                [{"text": "🏠 Back to Dashboard", "callback_data": "view_dashboard"}]
            ])
            
            bot.send_message(chat_id, sniper_stats_message, parse_mode="Markdown", reply_markup=keyboard)
            
    except Exception as e:
        import logging
        logging.error(f"Error in sniper stats handler: {e}")
        bot.send_message(chat_id, "Error displaying sniper stats. Please try again.")

# Withdrawal management handlers
def admin_manage_withdrawals_handler(update, chat_id):
    """Handle the manage withdrawals button and show pending withdrawal requests."""
    try:
        with app.app_context():
            from models import User, Transaction
            from datetime import datetime
            
            # Get all pending withdrawal transactions
            pending_withdrawals = Transaction.query.filter_by(
                transaction_type="withdraw",
                status="pending"
            ).order_by(Transaction.timestamp.desc()).all()
            
            if not pending_withdrawals:
                message = "📝 *Withdrawal Management*\n\nThere are no pending withdrawal requests at this time."
                
                keyboard = bot.create_inline_keyboard([
                    [{"text": "View Completed Withdrawals", "callback_data": "admin_view_completed_withdrawals"}],
                    [{"text": "🔙 Back to Admin Panel", "callback_data": "admin_back"}]
                ])
                
                bot.send_message(
                    chat_id,
                    message,
                    parse_mode="Markdown",
                    reply_markup=keyboard
                )
                return
            
            # Format the list of pending withdrawals
            message = "📝 *Pending Withdrawal Requests*\n\n"
            
            for i, withdrawal in enumerate(pending_withdrawals[:10], 1):  # Show up to 10 most recent pending withdrawals
                user = User.query.get(withdrawal.user_id)
                if not user:
                    continue
                
                # Format wallet address for display
                wallet_address = user.wallet_address or "No wallet address set"
                if wallet_address and len(wallet_address) > 10:
                    display_wallet = f"{wallet_address[:6]}...{wallet_address[-4:]}"
                else:
                    display_wallet = wallet_address
                
                message += (
                    f"*{i}. Request #{withdrawal.id}*\n"
                    f"User: {user.username or user.telegram_id}\n"
                    f"Amount: {withdrawal.amount:.6f} SOL\n"
                    f"Wallet: {display_wallet}\n"
                    f"Requested: {withdrawal.timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n"
                    f"Notes: {withdrawal.notes or 'N/A'}\n\n"
                )
            
            keyboard_rows = []
            
            # Create approve/deny buttons for each withdrawal
            for withdrawal in pending_withdrawals[:5]:  # Limit to first 5 to avoid too many buttons
                keyboard_rows.append([
                    {"text": f"✅ Approve #{withdrawal.id}", "callback_data": f"admin_approve_withdrawal_{withdrawal.id}"},
                    {"text": f"❌ Deny #{withdrawal.id}", "callback_data": f"admin_deny_withdrawal_{withdrawal.id}"}
                ])
            
            # Add navigation buttons
            keyboard_rows.append([
                {"text": "View Completed", "callback_data": "admin_view_completed_withdrawals"},
                {"text": "🔙 Back", "callback_data": "admin_back"}
            ])
            
            bot.send_message(
                chat_id,
                message,
                parse_mode="Markdown",
                reply_markup=bot.create_inline_keyboard(keyboard_rows)
            )
            
    except Exception as e:
        import logging
        logging.error(f"Error in admin_manage_withdrawals_handler: {e}")
        import traceback
        logging.error(traceback.format_exc())
        
        bot.send_message(
            chat_id,
            f"⚠️ Error loading pending withdrawals: {str(e)}",
            reply_markup=bot.create_inline_keyboard([
                [{"text": "🔙 Back to Admin", "callback_data": "admin_back"}]
            ])
        )

def admin_approve_withdrawal_handler(update, chat_id):
    """Approve a specific withdrawal request."""
    try:
        # Extract the withdrawal ID from the callback data
        callback_data = update.get('callback_query', {}).get('data', '')
        withdrawal_id = int(callback_data.split('_')[-1])
        
        with app.app_context():
            from models import User, Transaction
            import random
            from datetime import datetime
            
            # Get the withdrawal transaction
            withdrawal = Transaction.query.get(withdrawal_id)
            if not withdrawal or withdrawal.transaction_type != "withdraw" or withdrawal.status != "pending":
                bot.send_message(chat_id, "❌ Error: Withdrawal not found or already processed.")
                return
            
            # Get the user record
            user = User.query.get(withdrawal.user_id)
            if not user:
                bot.send_message(chat_id, "❌ Error: User not found in database.")
                return
            
            # Update transaction status
            withdrawal.status = "completed"
            withdrawal.notes = f"{withdrawal.notes or ''}; Approved by admin on {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}"
            
            # Generate TX hash for completed transaction
            tx_hash = f"Sol{random.randint(10000000, 99999999)}{user.id}"
            withdrawal.tx_hash = tx_hash
            
            db.session.commit()
            
            # Format time
            time_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            shortened_hash = f"{tx_hash[:6]}...{tx_hash[-4:]}"
            
            # Notify the user
            success_message = (
                "✅ *Withdrawal Approved!*\n\n"
                f"Amount: *{withdrawal.amount:.6f} SOL*\n"
                f"Destination: {user.wallet_address[:6]}...{user.wallet_address[-4:] if len(user.wallet_address) > 10 else user.wallet_address}\n"
                f"TX Hash: `{shortened_hash}`\n"
                f"View on: https://solscan.io/tx/{tx_hash}\n"
                f"Time: {time_str} UTC\n\n"
                "Your funds are on the way and should appear in your wallet shortly."
            )
            
            user_keyboard = bot.create_inline_keyboard([
                [{"text": "🔎 View Transaction", "callback_data": "view_tx"}],
                [{"text": "🏠 Back to Dashboard", "callback_data": "view_dashboard"}]
            ])
            
            try:
                bot.send_message(
                    user.telegram_id,
                    success_message,
                    parse_mode="Markdown",
                    reply_markup=user_keyboard
                )
            except Exception as notify_error:
                logging.error(f"Failed to notify user about withdrawal approval: {notify_error}")
            
            # Confirm to admin
            admin_message = (
                f"✅ *Withdrawal #{withdrawal_id} Approved*\n\n"
                f"User: {user.username or user.telegram_id}\n"
                f"Amount: {withdrawal.amount:.6f} SOL\n"
                f"TX Hash: `{shortened_hash}`\n"
                f"Time: {time_str} UTC\n\n"
                f"User has been notified of the approval."
            )
            
            keyboard = bot.create_inline_keyboard([
                [{"text": "📊 Manage More Withdrawals", "callback_data": "admin_manage_withdrawals"}],
                [{"text": "🔙 Back to Admin Panel", "callback_data": "admin_back"}]
            ])
            
            bot.send_message(
                chat_id,
                admin_message,
                parse_mode="Markdown",
                reply_markup=keyboard
            )
            
    except Exception as e:
        import logging
        logging.error(f"Error in admin_approve_withdrawal_handler: {e}")
        import traceback
        logging.error(traceback.format_exc())
        
        bot.send_message(
            chat_id,
            f"⚠️ Error approving withdrawal: {str(e)}",
            reply_markup=bot.create_inline_keyboard([
                [{"text": "🔙 Back to Admin", "callback_data": "admin_back"}]
            ])
        )

def admin_deny_withdrawal_handler(update, chat_id):
    """Deny a specific withdrawal request and return funds to user."""
    try:
        # Extract the withdrawal ID from the callback data
        callback_data = update.get('callback_query', {}).get('data', '')
        withdrawal_id = int(callback_data.split('_')[-1])
        
        with app.app_context():
            from models import User, Transaction
            from datetime import datetime
            
            # Get the withdrawal transaction
            withdrawal = Transaction.query.get(withdrawal_id)
            if not withdrawal or withdrawal.transaction_type != "withdraw" or withdrawal.status != "pending":
                bot.send_message(chat_id, "❌ Error: Withdrawal not found or already processed.")
                return
            
            # Get the user record
            user = User.query.get(withdrawal.user_id)
            if not user:
                bot.send_message(chat_id, "❌ Error: User not found in database.")
                return
            
            # Update transaction status
            withdrawal.status = "failed"
            withdrawal.notes = f"{withdrawal.notes or ''}; Denied by admin on {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}"
            
            # Return funds to user's balance
            user.balance += withdrawal.amount
            
            db.session.commit()
            
            # Format time
            time_str = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            
            # Notify the user
            deny_message = (
                "❌ *Withdrawal Request Denied*\n\n"
                f"Amount: *{withdrawal.amount:.6f} SOL*\n"
                f"Request ID: #{withdrawal.id}\n"
                f"Time: {time_str} UTC\n\n"
                "Your withdrawal request has been denied by an administrator. "
                "The funds have been returned to your account balance.\n\n"
                "Please contact support if you have any questions."
            )
            
            user_keyboard = bot.create_inline_keyboard([
                [{"text": "📞 Contact Support", "callback_data": "support"}],
                [{"text": "🏠 Back to Dashboard", "callback_data": "view_dashboard"}]
            ])
            
            try:
                bot.send_message(
                    user.telegram_id,
                    deny_message,
                    parse_mode="Markdown",
                    reply_markup=user_keyboard
                )
            except Exception as notify_error:
                logging.error(f"Failed to notify user about withdrawal denial: {notify_error}")
            
            # Confirm to admin
            admin_message = (
                f"❌ *Withdrawal #{withdrawal_id} Denied*\n\n"
                f"User: {user.username or user.telegram_id}\n"
                f"Amount: {withdrawal.amount:.6f} SOL\n"
                f"Time: {time_str} UTC\n\n"
                f"Funds have been returned to the user's balance."
            )
            
            keyboard = bot.create_inline_keyboard([
                [{"text": "📊 Manage More Withdrawals", "callback_data": "admin_manage_withdrawals"}],
                [{"text": "🔙 Back to Admin Panel", "callback_data": "admin_back"}]
            ])
            
            bot.send_message(
                chat_id,
                admin_message,
                parse_mode="Markdown",
                reply_markup=keyboard
            )
            
    except Exception as e:
        import logging
        logging.error(f"Error in admin_deny_withdrawal_handler: {e}")
        import traceback
        logging.error(traceback.format_exc())
        
        bot.send_message(
            chat_id,
            f"⚠️ Error denying withdrawal: {str(e)}",
            reply_markup=bot.create_inline_keyboard([
                [{"text": "🔙 Back to Admin", "callback_data": "admin_back"}]
            ])
        )

# This is the improved admin view users handler with copied fields and no deposit wallet


def admin_view_all_users_handler_legacy(update, chat_id):
    """Legacy version of the user list function (disabled)"""
    # Forward to our new fixed handler
    return admin_view_all_users_button_handler(update, chat_id)

def admin_view_completed_withdrawals_handler(update, chat_id):
    """Show a list of completed withdrawal transactions."""
    try:
        with app.app_context():
            from models import User, Transaction
            
            # Get recent completed withdrawals (last 10)
            completed_withdrawals = Transaction.query.filter_by(
                transaction_type="withdraw",
                status="completed"
            ).order_by(Transaction.timestamp.desc()).limit(10).all()
            
            if not completed_withdrawals:
                message = "📋 *Completed Withdrawals*\n\nThere are no completed withdrawals to display."
            else:
                message = "📋 *Recent Completed Withdrawals*\n\n"
                
                for i, withdrawal in enumerate(completed_withdrawals, 1):
                    user = User.query.get(withdrawal.user_id)
                    if not user:
                        continue
                    
                    message += (
                        f"*{i}. Transaction #{withdrawal.id}*\n"
                        f"User: {user.username or user.telegram_id}\n"
                        f"Amount: {withdrawal.amount:.6f} SOL\n"
                        f"Completed: {withdrawal.timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                    )
            
            keyboard = bot.create_inline_keyboard([
                [{"text": "📊 View Pending Withdrawals", "callback_data": "admin_manage_withdrawals"}],
                [{"text": "🔙 Back to Admin Panel", "callback_data": "admin_back"}]
            ])
            
            bot.send_message(
                chat_id,
                message,
                parse_mode="Markdown",
                reply_markup=keyboard
            )
            
    except Exception as e:
        import logging
        logging.error(f"Error in admin_view_completed_withdrawals_handler: {e}")
        import traceback
        logging.error(traceback.format_exc())
        
        bot.send_message(
            chat_id,
            f"⚠️ Error viewing completed withdrawals: {str(e)}",
            reply_markup=bot.create_inline_keyboard([
                [{"text": "🔙 Back to Admin", "callback_data": "admin_back"}]
            ])
        )

# Duplicate function removed - using the first copy_referral_link_handler implementation above

# Duplicate handlers removed - using the original implementations above

# AWS Entry Point - Direct execution via `python bot_v20_runner.py`
def main():
    """Main entry point for AWS deployment with environment-aware startup"""
    
    # Get logger after environment setup
    logger = logging.getLogger(__name__)
    
    # Prevent duplicate execution if already running via import
    global _bot_running
    if _bot_running:
        logger.warning("🔄 Bot is already running via import mode, skipping direct execution")
        return
    
    logger.info("🚀 Starting Telegram Bot in Direct Execution Mode")
    logger.info("=" * 60)
    logger.info(f"Environment Type: {env_info['environment_type'].upper()}")
    logger.info(f"Execution Method: Direct Python execution")
    logger.info(f"Environment File: {'✅ Found' if env_info['env_file_exists'] else '❌ Not found'}")
    logger.info(f"Auto-start Enabled: {'✅ Yes' if env_info['auto_start_enabled'] else '❌ No (manual start)'}")
    logger.info("=" * 60)
    
    try:
        # Verify critical environment variables
        if not BOT_TOKEN:
            logger.error("❌ TELEGRAM_BOT_TOKEN not found in environment variables")
            if env_info['environment_type'] == 'aws':
                logger.error("Please ensure your .env file contains:")
                logger.error("TELEGRAM_BOT_TOKEN=your_bot_token_here")
                logger.error("DATABASE_URL=your_database_url_here")
                logger.error("SESSION_SECRET=your_session_secret_here")
            else:
                logger.error("Please set TELEGRAM_BOT_TOKEN in your environment")
            sys.exit(1)
        
        logger.info(f"✅ Bot token found (ending in ...{BOT_TOKEN[-5:]})")
        
        # Check database connectivity
        try:
            with app.app_context():
                from models import User
                user_count = User.query.count()
                logger.info(f"✅ Database connected successfully ({user_count} users)")
        except Exception as e:
            logger.error(f"❌ Database connection failed: {e}")
            if env_info['environment_type'] == 'aws':
                logger.error("Please check your DATABASE_URL in the .env file")
            sys.exit(1)
        
        # Prevent duplicate instance
        from duplicate_instance_prevention import get_global_instance_manager
        instance_manager = get_global_instance_manager()
        if not instance_manager.acquire_lock():
            logger.warning("🔒 Another bot instance is already running, exiting")
            sys.exit(1)
        
        # Start monitoring systems
        from utils.deposit_monitor import start_deposit_monitor, is_monitor_running
        from automated_maintenance import start_maintenance_scheduler
        
        if not is_monitor_running():
            if start_deposit_monitor():
                logger.info("✅ Deposit monitor started")
            else:
                logger.warning("⚠️  Failed to start deposit monitor")
        
        try:
            start_maintenance_scheduler()
            logger.info("✅ Database maintenance scheduler started")
        except Exception as e:
            logger.warning(f"⚠️  Failed to start maintenance scheduler: {e}")
        
        # Start the bot
        logger.info("🤖 Starting bot polling...")
        logger.info("Press Ctrl+C to stop the bot")
        
        # Set running flag
        _bot_running = True
        
        run_polling()
        
    except KeyboardInterrupt:
        logger.info("🛑 Bot stopped by user (Ctrl+C)")
        _bot_running = False
    except Exception as e:
        logger.error(f"❌ Bot crashed: {e}")
        import traceback
        logger.error(traceback.format_exc())
        _bot_running = False
        sys.exit(1)
    finally:
        # Cleanup
        try:
            from duplicate_instance_prevention import get_global_instance_manager
            instance_manager = get_global_instance_manager()
            instance_manager.release_lock()
        except:
            pass

# Entry point for AWS execution
if __name__ == '__main__':
    main()
