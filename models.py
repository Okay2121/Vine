from datetime import datetime
from app import db
from sqlalchemy import Enum, ForeignKey
import enum
import random
import string


class UserStatus(enum.Enum):
    ONBOARDING = "onboarding"  # New user, hasn't deposited
    DEPOSITING = "depositing"  # Started deposit process but not completed
    ACTIVE = "active"          # Has deposited and bot is trading
    INACTIVE = "inactive"      # Paused or stopped trading


class CycleStatus(enum.Enum):
    NOT_STARTED = "not_started"  # Cycle hasn't started yet
    IN_PROGRESS = "in_progress"  # Cycle is running
    COMPLETED = "completed"      # Cycle completed successfully
    PAUSED = "paused"            # Cycle temporarily paused


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    telegram_id = db.Column(db.String(64), unique=True, nullable=False)
    username = db.Column(db.String(64))
    first_name = db.Column(db.String(64))
    last_name = db.Column(db.String(64))
    joined_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(Enum(UserStatus), default=UserStatus.ONBOARDING)
    
    # Trading info
    wallet_address = db.Column(db.String(64), unique=True)  # Payout wallet
    deposit_wallet = db.Column(db.String(64), nullable=True)  # Deposit wallet (shared global address)
    balance = db.Column(db.Float, default=0.0)
    initial_deposit = db.Column(db.Float, default=0.0)
    last_activity = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Referral system
    referrer_code_id = db.Column(db.Integer, db.ForeignKey('referral_code.id'), nullable=True)
    referral_bonus = db.Column(db.Float, default=0.0)  # Accumulated bonus from referrals
    
    # Sniper system
    sniper_active = db.Column(db.Boolean, default=False)  # Track if sniper mode is active
    
    # Bot will track transactions and profit for each user
    transactions = db.relationship('Transaction', backref='user', lazy=True)
    profits = db.relationship('Profit', backref='user', lazy=True)
    referral_code = db.relationship('ReferralCode', backref='owner', lazy=True, foreign_keys='ReferralCode.user_id')
    referrer = db.relationship('ReferralCode', foreign_keys=[referrer_code_id])
    
    def __repr__(self):
        return f'<User {self.telegram_id}>'


class Transaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    transaction_type = db.Column(db.String(20), nullable=False)  # deposit, withdraw, buy, sell, admin_credit, admin_debit, trade_profit, trade_loss
    amount = db.Column(db.Float, nullable=False)
    token_name = db.Column(db.String(64))  # For buy/sell transactions
    price = db.Column(db.Float, nullable=True)  # Token price for buy/sell transactions
    timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)  # Indexed for faster lookups
    status = db.Column(db.String(20), default='pending')  # pending, completed, failed
    notes = db.Column(db.Text, nullable=True)  # For storing reasons or additional information
    tx_hash = db.Column(db.String(128), nullable=True, unique=True, index=True)  # Unique to prevent duplicate processing
    processed_at = db.Column(db.DateTime, nullable=True)  # When the transaction was actually processed
    related_trade_id = db.Column(db.Integer, nullable=True)  # Link to the TradingPosition that generated this transaction
    
    # Create indexes for common query patterns
    __table_args__ = (
        db.Index('idx_transaction_user_type', 'user_id', 'transaction_type'),
        db.Index('idx_transaction_status', 'status'),
    )
    
    def __repr__(self):
        return f'<Transaction {self.transaction_type} {self.amount}>'


class Profit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    percentage = db.Column(db.Float, nullable=False)
    date = db.Column(db.Date, nullable=False)
    
    def __repr__(self):
        return f'<Profit {self.amount} SOL ({self.percentage}%)>'


class TradingPosition(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    token_name = db.Column(db.String(64), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    entry_price = db.Column(db.Float, nullable=False)
    current_price = db.Column(db.Float, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='open')  # open, closed
    trade_type = db.Column(db.String(20), nullable=True)  # scalp, snipe, dip, reversal
    buy_tx_hash = db.Column(db.String(128), nullable=True)  # Transaction hash for the buy
    sell_tx_hash = db.Column(db.String(128), nullable=True)  # Transaction hash for the sell
    buy_timestamp = db.Column(db.DateTime, nullable=True)  # When the buy was executed
    sell_timestamp = db.Column(db.DateTime, nullable=True)  # When the sell was executed
    roi_percentage = db.Column(db.Float, nullable=True)  # Calculated ROI percentage
    paired_position_id = db.Column(db.Integer, nullable=True)  # For linking related buy/sell positions
    admin_id = db.Column(db.String(64), nullable=True)  # Admin who created this position
    exit_price = db.Column(db.Float, nullable=True)  # Price at exit (sell)
    
    def __repr__(self):
        return f'<TradingPosition {self.token_name} {self.amount}>'


class MilestoneTracker(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    milestone_type = db.Column(db.String(20), nullable=False)  # profit_percentage, streak
    value = db.Column(db.Float, nullable=False)
    achieved_at = db.Column(db.DateTime, default=datetime.utcnow)
    acknowledged = db.Column(db.Boolean, default=False)
    
    def __repr__(self):
        return f'<Milestone {self.milestone_type} {self.value}>'


class ReferralCode(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    code = db.Column(db.String(20), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Stats
    total_referrals = db.Column(db.Integer, default=0)
    total_earned = db.Column(db.Float, default=0.0)  # Total earnings from referrals
    
    # Users who signed up with this code
    referred_users = db.relationship('User', foreign_keys='User.referrer_code_id', backref='referred_by')
    
    def __repr__(self):
        return f'<ReferralCode {self.code}>'
    
    @staticmethod
    def generate_code():
        """Generate a unique referral code"""
        prefix = "SOL"
        random_part = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        return f"{prefix}{random_part}"


class SenderWallet(db.Model):
    """Model for tracking sender wallet addresses linked to users for the single-wallet deposit system"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    wallet_address = db.Column(db.String(64), unique=True, nullable=False)  # Sender's Solana wallet address
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_used = db.Column(db.DateTime, default=datetime.utcnow)
    is_primary = db.Column(db.Boolean, default=True)  # Whether this is the primary sender wallet for the user
    
    # Relationship to user
    user = db.relationship('User', backref='sender_wallets')
    
    def __repr__(self):
        return f'<SenderWallet {self.wallet_address[:10]}... - User {self.user_id}>'


class ReferralReward(db.Model):
    """Model for tracking individual referral rewards"""
    id = db.Column(db.Integer, primary_key=True)
    referrer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # User who receives the reward
    referred_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # User who generated the profit
    amount = db.Column(db.Float, nullable=False)  # Reward amount (in SOL)
    source_profit = db.Column(db.Float, nullable=False)  # Original profit amount that generated this reward
    percentage = db.Column(db.Float, default=5.0)  # Percentage of profit (usually 5%)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    referrer = db.relationship('User', foreign_keys=[referrer_id], backref='referral_rewards_received')
    referred = db.relationship('User', foreign_keys=[referred_id], backref='referral_rewards_generated')
    
    def __repr__(self):
        return f'<ReferralReward {self.amount} SOL - Referrer {self.referrer_id} - Referred {self.referred_id}>'


class SupportTicket(db.Model):
    """Model for support tickets"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    subject = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    status = db.Column(db.String(20), default='open')  # open, in_progress, closed
    priority = db.Column(db.String(20), default='normal')  # low, normal, high, urgent
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship to user
    user = db.relationship('User', backref='support_tickets')
    
    def __repr__(self):
        return f'<SupportTicket {self.id} - {self.subject[:20]}... - {self.status}>'


class TradingCycle(db.Model):
    """Model for tracking the 7-day 2x ROI trading cycle for each user"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    start_date = db.Column(db.DateTime, default=datetime.utcnow)
    end_date = db.Column(db.DateTime, nullable=True)
    initial_balance = db.Column(db.Float, nullable=False)  # Locked balance at start of cycle
    target_balance = db.Column(db.Float, nullable=False)  # 2x initial balance
    current_balance = db.Column(db.Float, nullable=False)  # Current balance in cycle
    status = db.Column(Enum(CycleStatus), default=CycleStatus.IN_PROGRESS)
    daily_roi_percentage = db.Column(db.Float, default=28.57)  # Default ~28.57% per day to reach 2x in 7 days
    total_profit_amount = db.Column(db.Float, default=0.0)  # Total profit generated in this cycle
    total_roi_percentage = db.Column(db.Float, default=0.0)  # Total ROI percentage achieved
    is_auto_roi = db.Column(db.Boolean, default=True)  # Whether to use auto-calculated ROI
    
    # Relationship to user
    user = db.relationship('User', backref='trading_cycles')
    
    def __repr__(self):
        return f'<TradingCycle {self.id} - User {self.user_id} - {self.status.value}>'
    
    @property
    def days_elapsed(self):
        """Calculate days elapsed in the cycle"""
        now = datetime.utcnow()
        return (now - self.start_date).days
    
    @property
    def days_remaining(self):
        """Calculate days remaining in the cycle"""
        return max(0, 7 - self.days_elapsed)
    
    @property
    def progress_percentage(self):
        """Calculate progress percentage toward 2x target"""
        if self.initial_balance <= 0:
            return 0
        profit = self.current_balance - self.initial_balance
        target_profit = self.initial_balance  # Target profit is equal to initial balance (for 2x)
        if target_profit <= 0:
            return 0
        return min(100, (profit / target_profit) * 100)
        
    @property
    def is_on_track(self):
        """Check if the cycle is on track to reach 2x in 7 days"""
        if self.days_elapsed == 0:
            return True
        
        expected_progress = (self.days_elapsed / 7) * 100
        return self.progress_percentage >= expected_progress


class BroadcastMessage(db.Model):
    """Model for tracking broadcast messages sent by admins"""
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    message_type = db.Column(db.String(20), nullable=False)  # text, image, announcement
    created_by = db.Column(db.String(64), nullable=False)  # Admin's telegram_id
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    sent_at = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), default='draft')  # draft, pending, sending, sent, failed
    sent_count = db.Column(db.Integer, default=0)  # Number of users the message was sent to
    failed_count = db.Column(db.Integer, default=0)  # Number of users the message failed to send to
    
    def __repr__(self):
        return f'<BroadcastMessage {self.id} - {self.message_type} - {self.status}>'


class AdminMessage(db.Model):
    """Model for tracking direct messages sent by admins"""
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    message_type = db.Column(db.String(20), nullable=False)  # text, image
    recipient_id = db.Column(db.String(64), nullable=False)  # Recipient's telegram_id
    sent_by = db.Column(db.String(64), nullable=False)  # Admin's telegram_id
    sent_at = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.String(20), default='sent')  # sent, failed
    
    def __repr__(self):
        return f'<AdminMessage {self.id} - {self.message_type} - To: {self.recipient_id}>'


class SystemSettings(db.Model):
    """Global system settings for the bot"""
    id = db.Column(db.Integer, primary_key=True)
    setting_name = db.Column(db.String(64), unique=True, nullable=False)
    setting_value = db.Column(db.Text, nullable=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = db.Column(db.String(64), nullable=True)  # Admin's telegram_id
    
    def __repr__(self):
        return f'<SystemSettings {self.setting_name}>'


class UserMetrics(db.Model):
    """Real-time performance metrics for dashboard"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    current_streak = db.Column(db.Integer, default=0)
    best_streak = db.Column(db.Integer, default=0)
    last_streak_update = db.Column(db.DateTime, default=datetime.utcnow)
    next_milestone = db.Column(db.Float, default=10.0)
    milestone_progress = db.Column(db.Float, default=0.0)
    current_goal = db.Column(db.Float, default=100.0)
    goal_progress = db.Column(db.Float, default=0.0)
    trading_mode = db.Column(db.String(20), default='autopilot')
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship to user
    user = db.relationship('User', backref='metrics')
    
    def __repr__(self):
        return f'<UserMetrics {self.user_id} - Streak: {self.current_streak}>'


class DailySnapshot(db.Model):
    """Daily balance and performance snapshot for accurate performance tracking"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow().date)
    starting_balance = db.Column(db.Float, nullable=False)
    ending_balance = db.Column(db.Float, nullable=True)  # Will be set at end of day
    profit_amount = db.Column(db.Float, nullable=True)  # Will be calculated at end of day
    profit_percentage = db.Column(db.Float, nullable=True)  # Will be calculated at end of day
    trades_count = db.Column(db.Integer, default=0)
    winning_trades = db.Column(db.Integer, default=0)
    
    # Relationship to user
    user = db.relationship('User', backref='daily_snapshots')
    
    def __repr__(self):
        return f'<DailySnapshot {self.date} - User {self.user_id}>'


class AutoTradingSettings(db.Model):
    """User auto trading configuration and preferences"""
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, unique=True)
    
    # Auto Trading Status
    is_enabled = db.Column(db.Boolean, default=True)
    external_signals_enabled = db.Column(db.Boolean, default=True)  # Follow external market signals
    
    # Risk Management Settings
    position_size_percentage = db.Column(db.Float, default=10.0)  # % of balance per trade (5-25%)
    stop_loss_percentage = db.Column(db.Float, default=15.0)  # Stop loss % (5-50%)
    take_profit_percentage = db.Column(db.Float, default=100.0)  # Take profit % (20-500%)
    max_daily_trades = db.Column(db.Integer, default=5)  # Maximum trades per day (1-10)
    max_simultaneous_positions = db.Column(db.Integer, default=3)  # Max open positions (1-8)
    
    # Auto Mode Settings - Use broadcast values instead of fixed values
    position_size_auto = db.Column(db.Boolean, default=True)  # Use broadcast position sizes
    stop_loss_auto = db.Column(db.Boolean, default=True)  # Use broadcast stop loss values
    take_profit_auto = db.Column(db.Boolean, default=True)  # Use broadcast take profit values
    daily_trades_auto = db.Column(db.Boolean, default=True)  # Use broadcast trade frequency
    max_positions_auto = db.Column(db.Boolean, default=True)  # Use broadcast position limits
    
    # Balance Allocation
    auto_trading_balance_percentage = db.Column(db.Float, default=50.0)  # % of total balance to use (20-80%)
    reserve_balance_sol = db.Column(db.Float, default=0.1)  # SOL to keep as reserve
    
    # Signal Sources (Secondary - Admin signals are always enabled)
    pump_fun_launches = db.Column(db.Boolean, default=True)
    whale_movements = db.Column(db.Boolean, default=True) 
    social_sentiment = db.Column(db.Boolean, default=False)
    dex_volume_spikes = db.Column(db.Boolean, default=False)
    
    # Quality Filters
    min_liquidity_sol = db.Column(db.Float, default=50.0)  # Minimum liquidity required
    min_market_cap = db.Column(db.Integer, default=10000)  # Minimum market cap in USD
    max_market_cap = db.Column(db.Integer, default=5000000)  # Maximum market cap in USD
    min_volume_24h = db.Column(db.Integer, default=30000)  # Minimum 24h volume in USD
    min_social_mentions = db.Column(db.Integer, default=100)  # Minimum social mentions per hour
    
    # Timing Controls
    trading_hours_enabled = db.Column(db.Boolean, default=False)  # Enable time restrictions
    trading_start_hour = db.Column(db.Integer, default=0)  # UTC hour to start trading (0-23)
    trading_end_hour = db.Column(db.Integer, default=23)  # UTC hour to stop trading (0-23)
    weekend_trading = db.Column(db.Boolean, default=True)  # Trade on weekends
    pause_during_high_volatility = db.Column(db.Boolean, default=False)
    
    # Anti-FOMO Controls
    min_time_between_trades_minutes = db.Column(db.Integer, default=10)  # Minimum time between trades
    fomo_cooldown_minutes = db.Column(db.Integer, default=30)  # Cooldown after failed trades
    enable_anti_rug_protection = db.Column(db.Boolean, default=True)
    
    # Advanced Settings
    enable_portfolio_rebalancing = db.Column(db.Boolean, default=False)
    enable_dynamic_position_sizing = db.Column(db.Boolean, default=True)
    enable_trailing_stop_loss = db.Column(db.Boolean, default=False)
    trailing_stop_distance_percentage = db.Column(db.Float, default=5.0)
    
    # Performance Tracking
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_trade_at = db.Column(db.DateTime, nullable=True)
    total_auto_trades = db.Column(db.Integer, default=0)
    successful_auto_trades = db.Column(db.Integer, default=0)
    
    # Relationship to user  
    user = db.relationship('User', backref='auto_trading_settings')
    
    def __repr__(self):
        return f'<AutoTradingSettings User {self.user_id} - Enabled: {self.is_enabled}>'
    
    @property
    def success_rate(self):
        """Calculate auto trading success rate"""
        if self.total_auto_trades == 0:
            return 0
        return (self.successful_auto_trades / self.total_auto_trades) * 100
    
    @property
    def effective_trading_balance(self):
        """Calculate effective trading balance based on settings"""
        if not self.user:
            return 0
        available_balance = max(0, self.user.balance - self.reserve_balance_sol)
        return available_balance * (self.auto_trading_balance_percentage / 100)
    
    @property
    def max_position_size(self):
        """Calculate maximum position size in SOL"""
        return self.effective_trading_balance * (self.position_size_percentage / 100)
    
    def get_default_settings(self):
        """Get recommended default settings based on user balance"""
        if not self.user:
            return {}
            
        balance = self.user.balance
        
        if balance < 1.0:  # Small balance - Conservative
            return {
                'position_size_percentage': 8.0,
                'stop_loss_percentage': 20.0,
                'take_profit_percentage': 80.0,
                'max_daily_trades': 3,
                'max_simultaneous_positions': 2
            }
        elif balance < 5.0:  # Medium balance - Moderate  
            return {
                'position_size_percentage': 12.0,
                'stop_loss_percentage': 15.0,
                'take_profit_percentage': 120.0,
                'max_daily_trades': 5,
                'max_simultaneous_positions': 3
            }
        else:  # Large balance - Aggressive
            return {
                'position_size_percentage': 15.0,
                'stop_loss_percentage': 12.0,
                'take_profit_percentage': 150.0,
                'max_daily_trades': 8,
                'max_simultaneous_positions': 5
            }
