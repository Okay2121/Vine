"""
Test Suite for Duplicate Protection System
Comprehensive testing to verify the graceful handling of duplicate responses
"""
import requests
import time
import json
import logging
from graceful_duplicate_handler import duplicate_manager, handle_telegram_api_error

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_duplicate_update_detection():
    """Test that duplicate updates are properly detected and blocked"""
    print("Testing duplicate update detection...")
    
    # Simulate the same update being processed twice
    test_update_id = 12345
    
    # First time should not be blocked
    is_duplicate_1 = duplicate_manager.is_duplicate_update(test_update_id)
    assert not is_duplicate_1, "First occurrence should not be marked as duplicate"
    
    # Second time should be blocked
    is_duplicate_2 = duplicate_manager.is_duplicate_update(test_update_id)
    assert is_duplicate_2, "Second occurrence should be marked as duplicate"
    
    print("✅ Duplicate update detection working correctly")

def test_duplicate_callback_detection():
    """Test that duplicate callbacks are properly detected and blocked"""
    print("Testing duplicate callback detection...")
    
    # Simulate the same callback being processed twice
    test_callback_id = "callback_67890"
    
    # First time should not be blocked
    is_duplicate_1 = duplicate_manager.is_duplicate_callback(test_callback_id)
    assert not is_duplicate_1, "First occurrence should not be marked as duplicate"
    
    # Second time should be blocked
    is_duplicate_2 = duplicate_manager.is_duplicate_callback(test_callback_id)
    assert is_duplicate_2, "Second occurrence should be marked as duplicate"
    
    print("✅ Duplicate callback detection working correctly")

def test_rate_limiting():
    """Test that rate limiting is working correctly"""
    print("Testing rate limiting...")
    
    user_id = "test_user_123"
    
    # First request should not be rate limited
    is_limited_1 = duplicate_manager.is_rate_limited(user_id, "message", 2.0)
    assert not is_limited_1, "First request should not be rate limited"
    
    # Immediate second request should be rate limited
    is_limited_2 = duplicate_manager.is_rate_limited(user_id, "message", 2.0)
    assert is_limited_2, "Immediate second request should be rate limited"
    
    print("✅ Rate limiting working correctly")

def test_message_deduplication():
    """Test that duplicate messages are properly detected"""
    print("Testing message deduplication...")
    
    # Create test message data
    test_message = {
        'from': {'id': 123456},
        'chat': {'id': 789012},
        'text': 'Hello world test message',
        'date': int(time.time())
    }
    
    # First time should not be blocked
    is_duplicate_1 = duplicate_manager.is_duplicate_message(test_message)
    assert not is_duplicate_1, "First occurrence should not be marked as duplicate"
    
    # Second time should be blocked
    is_duplicate_2 = duplicate_manager.is_duplicate_message(test_message)
    assert is_duplicate_2, "Second occurrence should be marked as duplicate"
    
    print("✅ Message deduplication working correctly")

def test_http_409_handling():
    """Test that HTTP 409 responses are handled gracefully"""
    print("Testing HTTP 409 error handling...")
    
    # Mock a response object with 409 status
    class MockResponse:
        def __init__(self, status_code):
            self.status_code = status_code
            self.text = "Conflict"
    
    # Test handling of 409 response
    response_409 = MockResponse(409)
    result = handle_telegram_api_error(response_409, "test operation")
    
    assert result["ok"] == True, "HTTP 409 should be handled gracefully"
    assert "Duplicate request handled gracefully" in result["result"]["message"]
    
    print("✅ HTTP 409 error handling working correctly")

def simulate_bot_interactions():
    """Simulate real bot interactions to test the system under load"""
    print("Simulating bot interactions...")
    
    # Simulate multiple users sending messages
    for user_id in range(1001, 1006):
        # First message from each user
        message = {
            'from': {'id': user_id},
            'chat': {'id': user_id + 1000},
            'text': f'Test message from user {user_id}',
            'date': int(time.time())
        }
        
        # Should not be duplicate
        is_duplicate = duplicate_manager.is_duplicate_message(message)
        assert not is_duplicate, f"First message from user {user_id} should not be duplicate"
        
        # Simulate rapid duplicate message
        is_duplicate_2 = duplicate_manager.is_duplicate_message(message)
        assert is_duplicate_2, f"Duplicate message from user {user_id} should be blocked"
        
        # Test rate limiting
        is_limited = duplicate_manager.is_rate_limited(user_id, "message", 1.0)
        assert not is_limited, f"First rate limit check for user {user_id} should pass"
        
        is_limited_2 = duplicate_manager.is_rate_limited(user_id, "message", 1.0)
        assert is_limited_2, f"Second rate limit check for user {user_id} should be blocked"
    
    print("✅ Bot interaction simulation completed successfully")

def test_cache_management():
    """Test that caches are properly managed and don't grow indefinitely"""
    print("Testing cache management...")
    
    initial_update_cache_size = len(duplicate_manager.processed_updates)
    initial_callback_cache_size = len(duplicate_manager.processed_callbacks)
    
    # Add many entries to test cache limits
    for i in range(1200):
        duplicate_manager.is_duplicate_update(10000 + i)
        duplicate_manager.is_duplicate_callback(f"callback_{10000 + i}")
    
    # Check that caches were trimmed
    final_update_cache_size = len(duplicate_manager.processed_updates)
    final_callback_cache_size = len(duplicate_manager.processed_callbacks)
    
    assert final_update_cache_size <= 1000, "Update cache should be trimmed to reasonable size"
    assert final_callback_cache_size <= 1000, "Callback cache should be trimmed to reasonable size"
    
    print("✅ Cache management working correctly")

def run_comprehensive_test():
    """Run all tests to verify the duplicate protection system"""
    print("🔍 Starting Comprehensive Duplicate Protection Test")
    print("=" * 60)
    
    try:
        test_duplicate_update_detection()
        test_duplicate_callback_detection()
        test_rate_limiting()
        test_message_deduplication()
        test_http_409_handling()
        simulate_bot_interactions()
        test_cache_management()
        
        print("\n" + "=" * 60)
        print("🎉 ALL TESTS PASSED! Duplicate protection system is working correctly.")
        print("\nSystem Features Verified:")
        print("• ✅ Duplicate update detection")
        print("• ✅ Duplicate callback detection") 
        print("• ✅ Rate limiting")
        print("• ✅ Message deduplication")
        print("• ✅ HTTP 409 error handling")
        print("• ✅ Cache management")
        print("• ✅ Multi-user interaction handling")
        
        return True
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = run_comprehensive_test()
    
    if success:
        print("\n🚀 The duplicate protection system is ready for production use!")
        print("The bot should now gracefully handle:")
        print("• HTTP 409 Conflict errors from Telegram API")
        print("• Duplicate messages and callbacks")
        print("• Rate limiting to prevent spam")
        print("• Efficient memory management")
    else:
        print("\n⚠️ Some tests failed. Please review the system before deployment.")