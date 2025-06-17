"""
Slow Query Monitor and Performance Tracker
==========================================
Real-time monitoring of database query performance with alerts and optimization suggestions.
"""

import time
import threading
import logging
from datetime import datetime, timedelta
from collections import deque, defaultdict
from app import db
from sqlalchemy import event, text
from sqlalchemy.engine import Engine

logger = logging.getLogger(__name__)

class SlowQueryMonitor:
    """Monitor and track slow database queries"""
    
    def __init__(self, slow_threshold=0.1):
        self.slow_threshold = slow_threshold  # 100ms threshold
        self.slow_queries = deque(maxlen=1000)
        self.query_patterns = defaultdict(list)
        self.monitoring_active = False
        self.lock = threading.Lock()
        
        # Performance statistics
        self.stats = {
            'total_queries': 0,
            'slow_queries': 0,
            'avg_query_time': 0,
            'queries_per_minute': 0,  
            'last_reset': datetime.now()
        }
        
        self.setup_monitoring()
    
    def setup_monitoring(self):
        """Setup SQLAlchemy event listeners for query monitoring"""
        
        @event.listens_for(Engine, "before_cursor_execute")
        def receive_before_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            context._query_start_time = time.time()
            context._query_statement = statement
        
        @event.listens_for(Engine, "after_cursor_execute")  
        def receive_after_cursor_execute(conn, cursor, statement, parameters, context, executemany):
            if hasattr(context, '_query_start_time'):
                duration = time.time() - context._query_start_time
                self.record_query(statement, duration, parameters)
        
        self.monitoring_active = True
        logger.info("Slow query monitoring activated")
    
    def record_query(self, statement, duration, parameters=None):
        """Record query execution for analysis"""
        with self.lock:
            self.stats['total_queries'] += 1
            
            # Update average query time
            current_avg = self.stats['avg_query_time']
            total_queries = self.stats['total_queries']
            self.stats['avg_query_time'] = ((current_avg * (total_queries - 1)) + duration) / total_queries
            
            # Track slow queries
            if duration > self.slow_threshold:
                self.stats['slow_queries'] += 1
                
                # Extract query type and table
                query_type = statement.strip().split()[0].upper()
                table_name = self._extract_table_name(statement)
                
                slow_query_info = {
                    'statement': statement[:500] + '...' if len(statement) > 500 else statement,
                    'duration': duration,
                    'timestamp': datetime.now(),
                    'query_type': query_type,
                    'table': table_name,
                    'parameters': str(parameters)[:200] if parameters else None
                }
                
                self.slow_queries.append(slow_query_info)
                self.query_patterns[f"{query_type}_{table_name}"].append(duration)
                
                # Log critical slow queries
                if duration > 1.0:  # 1 second+
                    logger.warning(f"Very slow query detected: {duration:.3f}s - {query_type} on {table_name}")
                elif duration > 0.5:  # 500ms+
                    logger.info(f"Slow query detected: {duration:.3f}s - {query_type} on {table_name}")
    
    def _extract_table_name(self, statement):
        """Extract table name from SQL statement"""
        statement_upper = statement.upper()
        
        # Common patterns to extract table names
        if 'FROM ' in statement_upper:
            parts = statement_upper.split('FROM ')[1].split()
            if parts:
                table = parts[0].strip('"').strip("'")
                return table.split('.')[1] if '.' in table else table
        elif 'UPDATE ' in statement_upper:
            parts = statement_upper.split('UPDATE ')[1].split()
            if parts:
                table = parts[0].strip('"').strip("'")
                return table.split('.')[1] if '.' in table else table
        elif 'INSERT INTO ' in statement_upper:
            parts = statement_upper.split('INSERT INTO ')[1].split()
            if parts:
                table = parts[0].strip('"').strip("'")
                return table.split('.')[1] if '.' in table else table
        
        return 'unknown'
    
    def get_slow_query_report(self, minutes=60):
        """Get report of slow queries from the last N minutes"""
        cutoff_time = datetime.now() - timedelta(minutes=minutes)
        
        with self.lock:
            recent_slow_queries = [
                q for q in self.slow_queries 
                if q['timestamp'] > cutoff_time
            ]
            
            # Group by query pattern
            pattern_analysis = {}
            for pattern, durations in self.query_patterns.items():
                if durations:
                    recent_durations = durations[-50:]  # Last 50 occurrences
                    pattern_analysis[pattern] = {
                        'count': len(recent_durations),
                        'avg_duration': sum(recent_durations) / len(recent_durations),
                        'max_duration': max(recent_durations),
                        'min_duration': min(recent_durations)
                    }
            
            return {
                'monitoring_period_minutes': minutes,
                'total_slow_queries': len(recent_slow_queries),
                'recent_slow_queries': recent_slow_queries[-20:],  # Last 20
                'pattern_analysis': pattern_analysis,
                'recommendations': self._generate_recommendations(pattern_analysis)
            }
    
    def _generate_recommendations(self, pattern_analysis):
        """Generate optimization recommendations based on query patterns"""
        recommendations = []
        
        for pattern, stats in pattern_analysis.items():
            if stats['avg_duration'] > 0.5:  # 500ms+
                query_type, table = pattern.split('_', 1)
                
                if query_type == 'SELECT' and table in ['user', 'transaction', 'trading_position']:
                    recommendations.append({
                        'severity': 'high',
                        'table': table,
                        'issue': f'Slow SELECT queries on {table}',
                        'suggestion': f'Consider adding indexes on frequently queried columns in {table} table',
                        'avg_duration': stats['avg_duration']
                    })
                
                elif query_type == 'UPDATE' and stats['count'] > 10:
                    recommendations.append({
                        'severity': 'medium',
                        'table': table,
                        'issue': f'Frequent slow UPDATE operations on {table}',
                        'suggestion': f'Consider batch updates or optimized WHERE clauses for {table}',
                        'avg_duration': stats['avg_duration']
                    })
        
        return recommendations
    
    def get_performance_stats(self):
        """Get current performance statistics"""
        with self.lock:
            slow_query_percentage = (
                (self.stats['slow_queries'] / self.stats['total_queries'] * 100) 
                if self.stats['total_queries'] > 0 else 0
            )
            
            # Calculate queries per minute
            time_elapsed = (datetime.now() - self.stats['last_reset']).total_seconds() / 60
            queries_per_minute = self.stats['total_queries'] / time_elapsed if time_elapsed > 0 else 0
            
            return {
                'monitoring_active': self.monitoring_active,
                'total_queries_monitored': self.stats['total_queries'],
                'slow_queries_detected': self.stats['slow_queries'],
                'slow_query_percentage': round(slow_query_percentage, 2),
                'average_query_time_ms': round(self.stats['avg_query_time'] * 1000, 2),
                'queries_per_minute': round(queries_per_minute, 1),
                'slow_threshold_ms': self.slow_threshold * 1000,
                'monitoring_since': self.stats['last_reset']
            }
    
    def reset_stats(self):
        """Reset monitoring statistics"""
        with self.lock:
            self.stats = {
                'total_queries': 0,
                'slow_queries': 0,
                'avg_query_time': 0,
                'queries_per_minute': 0,
                'last_reset': datetime.now()
            }
            self.slow_queries.clear()
            self.query_patterns.clear()
        
        logger.info("Query monitoring statistics reset")
    
    def get_top_slow_queries(self, limit=10):
        """Get the slowest queries recorded"""
        with self.lock:
            sorted_queries = sorted(
                self.slow_queries, 
                key=lambda x: x['duration'], 
                reverse=True
            )
            return sorted_queries[:limit]


# Global monitor instance
slow_query_monitor = None

def get_slow_query_monitor():
    """Get the global slow query monitor"""
    global slow_query_monitor
    if slow_query_monitor is None:
        slow_query_monitor = SlowQueryMonitor()
    return slow_query_monitor

def get_query_performance_report():
    """Get comprehensive query performance report"""
    monitor = get_slow_query_monitor()
    return {
        'stats': monitor.get_performance_stats(),
        'recent_slow_queries': monitor.get_slow_query_report(minutes=30),
        'top_slow_queries': monitor.get_top_slow_queries(limit=5)
    }