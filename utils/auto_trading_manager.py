"""
Auto Trading Settings Manager
Handles all user auto trading configuration, validation, and processing
"""
import logging
from datetime import datetime
from typing import Dict, Optional, Tuple, Any
from app import db
from models import User, AutoTradingSettings

# Configure logging
logger = logging.getLogger(__name__)

class AutoTradingManager:
    """Manages user auto trading settings and validation"""
    
    @staticmethod
    def get_or_create_settings(user_id: int) -> AutoTradingSettings:
        """Get existing settings or create default settings for a user"""
        try:
            settings = AutoTradingSettings.query.filter_by(user_id=user_id).first()
            
            if not settings:
                # Create default settings based on user balance
                user = User.query.get(user_id)
                if not user:
                    raise ValueError(f"User {user_id} not found")
                
                settings = AutoTradingSettings()
                settings.user_id = user_id
                
                # Apply balance-based defaults
                defaults = settings.get_default_settings()
                for key, value in defaults.items():
                    if hasattr(settings, key):
                        setattr(settings, key, value)
                
                db.session.add(settings)
                db.session.commit()
                logger.info(f"Created default auto trading settings for user {user_id}")
            
            return settings
            
        except Exception as e:
            logger.error(f"Error getting/creating auto trading settings for user {user_id}: {e}")
            raise
    
    @staticmethod
    def update_setting(user_id: int, setting_name: str, value: Any) -> Tuple[bool, str]:
        """Update a specific auto trading setting with validation"""
        try:
            settings = AutoTradingManager.get_or_create_settings(user_id)
            
            # Validate the setting and value
            validation_result = AutoTradingManager.validate_setting(user_id, setting_name, value)
            if not validation_result[0]:
                return validation_result
            
            # Apply the update
            if hasattr(settings, setting_name):
                setattr(settings, setting_name, value)
                settings.updated_at = datetime.utcnow()
                db.session.commit()
                
                logger.info(f"Updated {setting_name} to {value} for user {user_id}")
                return True, f"Successfully updated {setting_name}"
            else:
                return False, f"Invalid setting name: {setting_name}"
                
        except Exception as e:
            logger.error(f"Error updating setting {setting_name} for user {user_id}: {e}")
            return False, f"Error updating setting: {str(e)}"
    
    @staticmethod
    def validate_setting(user_id: int, setting_name: str, value: Any) -> Tuple[bool, str]:
        """Validate a setting value with balance and risk checks"""
        try:
            user = User.query.get(user_id)
            if not user:
                return False, "User not found"
            
            balance = user.balance
            
            # Position size validation
            if setting_name == 'position_size_percentage':
                if not isinstance(value, (int, float)) or value < 5 or value > 25:
                    return False, "Position size must be between 5% and 25%"
                
                # Check if user has enough balance for this position size
                min_balance_needed = 0.1 / (value / 100)  # Need at least 0.1 SOL position
                if balance < min_balance_needed:
                    return False, f"Your balance ({balance:.3f} SOL) is too low for {value}% position size. Need at least {min_balance_needed:.3f} SOL"
            
            # Stop loss validation
            elif setting_name == 'stop_loss_percentage':
                if not isinstance(value, (int, float)) or value < 5 or value > 50:
                    return False, "Stop loss must be between 5% and 50%"
            
            # Take profit validation
            elif setting_name == 'take_profit_percentage':
                if not isinstance(value, (int, float)) or value < 20 or value > 500:
                    return False, "Take profit must be between 20% and 500%"
            
            # Daily trades validation
            elif setting_name == 'max_daily_trades':
                if not isinstance(value, int) or value < 1 or value > 10:
                    return False, "Max daily trades must be between 1 and 10"
                
                # Warn about gas costs for high frequency
                if value > 6 and balance < 2.0:
                    return False, f"Your balance ({balance:.3f} SOL) is too low for {value} daily trades. Need at least 2.0 SOL for gas fees"
            
            # Simultaneous positions validation
            elif setting_name == 'max_simultaneous_positions':
                if not isinstance(value, int) or value < 1 or value > 8:
                    return False, "Max simultaneous positions must be between 1 and 8"
            
            # Balance allocation validation
            elif setting_name == 'auto_trading_balance_percentage':
                if not isinstance(value, (int, float)) or value < 20 or value > 80:
                    return False, "Auto trading balance allocation must be between 20% and 80%"
            
            # Reserve balance validation
            elif setting_name == 'reserve_balance_sol':
                if not isinstance(value, (int, float)) or value < 0.05 or value > balance * 0.5:
                    return False, f"Reserve balance must be between 0.05 SOL and {balance * 0.5:.3f} SOL"
            
            # Liquidity filter validation
            elif setting_name == 'min_liquidity_sol':
                if not isinstance(value, (int, float)) or value < 10 or value > 1000:
                    return False, "Minimum liquidity must be between 10 and 1000 SOL"
            
            # Market cap validation
            elif setting_name in ['min_market_cap', 'max_market_cap']:
                if not isinstance(value, int) or value < 1000:
                    return False, "Market cap must be at least $1,000"
                
                if setting_name == 'min_market_cap' and value > 100000:
                    return False, "Minimum market cap too high - won't find many opportunities"
                
                if setting_name == 'max_market_cap' and value < 50000:
                    return False, "Maximum market cap too low - very risky"
            
            # Time validation
            elif setting_name in ['trading_start_hour', 'trading_end_hour']:
                if not isinstance(value, int) or value < 0 or value > 23:
                    return False, "Trading hours must be between 0 and 23 (UTC)"
            
            # Timing validation
            elif setting_name == 'min_time_between_trades_minutes':
                if not isinstance(value, int) or value < 1 or value > 120:
                    return False, "Time between trades must be between 1 and 120 minutes"
            
            elif setting_name == 'fomo_cooldown_minutes':
                if not isinstance(value, int) or value < 5 or value > 240:
                    return False, "FOMO cooldown must be between 5 and 240 minutes"
            
            return True, "Setting is valid"
            
        except Exception as e:
            logger.error(f"Error validating setting {setting_name}: {e}")
            return False, f"Validation error: {str(e)}"
    
    @staticmethod
    def get_risk_profile_summary(settings: AutoTradingSettings) -> Dict[str, Any]:
        """Generate a risk profile summary for the user"""
        try:
            # Determine risk level
            risk_score = 0
            
            # Position size scoring
            if settings.position_size_percentage >= 20:
                risk_score += 3
            elif settings.position_size_percentage >= 15:
                risk_score += 2
            else:
                risk_score += 1
            
            # Stop loss scoring (lower stop loss = higher risk)
            if settings.stop_loss_percentage <= 10:
                risk_score += 3
            elif settings.stop_loss_percentage <= 15:
                risk_score += 2
            else:
                risk_score += 1
            
            # Daily trades scoring
            if settings.max_daily_trades >= 7:
                risk_score += 2
            elif settings.max_daily_trades >= 4:
                risk_score += 1
            
            # Determine risk level
            if risk_score <= 3:
                risk_level = "Conservative"
                risk_emoji = "🔒"
                risk_description = "Low risk, steady growth approach"
            elif risk_score <= 5:
                risk_level = "Moderate"
                risk_emoji = "⚖️"
                risk_description = "Balanced risk-reward strategy"
            else:
                risk_level = "Aggressive"
                risk_emoji = "🔥"
                risk_description = "High risk, high reward trading"
            
            return {
                'level': risk_level,
                'emoji': risk_emoji,
                'description': risk_description,
                'score': risk_score
            }
            
        except Exception as e:
            logger.error(f"Error generating risk profile: {e}")
            return {
                'level': 'Unknown',
                'emoji': '❓',
                'description': 'Unable to determine risk level',
                'score': 0
            }
    
    @staticmethod
    def get_balance_impact_warning(user_id: int, settings: AutoTradingSettings) -> Optional[str]:
        """Get warnings about balance impact of current settings"""
        try:
            user = User.query.get(user_id)
            if not user:
                return None
            
            balance = user.balance
            effective_balance = settings.effective_trading_balance
            max_position = settings.max_position_size
            
            warnings = []
            
            # Check if balance is too low for settings
            if balance < 0.5:
                warnings.append("⚠️ Very low balance - consider depositing more for better performance")
            
            # Check if position size might be too large
            if max_position > balance * 0.3:
                warnings.append("⚠️ Large position sizes increase risk - consider reducing position percentage")
            
            # Check if too many daily trades for balance
            daily_gas_estimate = settings.max_daily_trades * 0.01  # Rough gas estimate
            if daily_gas_estimate > balance * 0.1:
                warnings.append("⚠️ High trade frequency may consume significant gas fees")
            
            # Check if effective trading balance is too small
            if effective_balance < 0.2:
                warnings.append("⚠️ Low trading allocation - consider increasing auto trading percentage")
            
            return " | ".join(warnings) if warnings else None
            
        except Exception as e:
            logger.error(f"Error generating balance warning: {e}")
            return "Unable to analyze balance impact"
    
    @staticmethod
    def check_admin_signal_eligibility(user_id: int) -> Tuple[bool, str]:
        """Check if user is eligible to receive admin signals"""
        try:
            settings = AutoTradingManager.get_or_create_settings(user_id)
            user = User.query.get(user_id)
            
            if not user:
                return False, "User not found"
            
            if not settings.is_enabled:
                return False, "Auto trading is disabled"
            
            if not settings.admin_signals_enabled:
                return False, "Admin signals are disabled"
            
            if user.balance < 0.1:
                return False, f"Insufficient balance ({user.balance:.3f} SOL) - need at least 0.1 SOL"
            
            if settings.effective_trading_balance < 0.05:
                return False, "Effective trading balance too low"
            
            return True, "Eligible for admin signals"
            
        except Exception as e:
            logger.error(f"Error checking admin signal eligibility: {e}")
            return False, f"Error checking eligibility: {str(e)}"