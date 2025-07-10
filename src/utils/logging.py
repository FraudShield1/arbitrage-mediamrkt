"""
Comprehensive logging system with structured logging and correlation IDs.
"""

import logging
import logging.handlers
import json
import uuid
import sys
import traceback
from typing import Dict, Any, Optional
from datetime import datetime
from pathlib import Path
import structlog
from contextvars import ContextVar

from src.config.settings import get_settings

settings = get_settings()

# Context variable for correlation ID
correlation_id_ctx: ContextVar[Optional[str]] = ContextVar('correlation_id', default=None)


class CorrelationIDProcessor:
    """Structlog processor to add correlation ID to log entries."""
    
    def __call__(self, logger, method_name, event_dict):
        correlation_id = correlation_id_ctx.get()
        if correlation_id:
            event_dict['correlation_id'] = correlation_id
        return event_dict


class TimestampProcessor:
    """Structlog processor to add consistent timestamps."""
    
    def __call__(self, logger, method_name, event_dict):
        event_dict['timestamp'] = datetime.utcnow().isoformat() + 'Z'
        return event_dict


class ServiceInfoProcessor:
    """Structlog processor to add service information."""
    
    def __call__(self, logger, method_name, event_dict):
        event_dict['service'] = 'arbitrage-tool'
        event_dict['version'] = '1.0.0'
        return event_dict


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging."""
    
    def format(self, record):
        """Format log record as JSON."""
        log_data = {
            'timestamp': datetime.utcfromtimestamp(record.created).isoformat() + 'Z',
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
            'service': 'arbitrage-tool',
            'version': '1.0.0'
        }
        
        # Add correlation ID if available
        correlation_id = correlation_id_ctx.get()
        if correlation_id:
            log_data['correlation_id'] = correlation_id
        
        # Add extra fields
        if hasattr(record, 'extra_data'):
            log_data.update(record.extra_data)
        
        # Add exception info if present
        if record.exc_info:
            log_data['exception'] = {
                'type': record.exc_info[0].__name__ if record.exc_info[0] else None,
                'message': str(record.exc_info[1]) if record.exc_info[1] else None,
                'traceback': traceback.format_exception(*record.exc_info)
            }
        
        return json.dumps(log_data, default=str)


class ColoredFormatter(logging.Formatter):
    """Colored formatter for console output."""
    
    # Color codes
    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
        'RESET': '\033[0m'       # Reset
    }
    
    def format(self, record):
        """Format log record with colors."""
        color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
        reset = self.COLORS['RESET']
        
        # Format timestamp
        timestamp = datetime.utcfromtimestamp(record.created).strftime('%Y-%m-%d %H:%M:%S')
        
        # Get correlation ID
        correlation_id = correlation_id_ctx.get()
        correlation_part = f" [{correlation_id[:8]}]" if correlation_id else ""
        
        # Format message
        formatted = (
            f"{color}[{timestamp}] {record.levelname:<8} "
            f"{record.name}:{record.lineno}{correlation_part} - "
            f"{record.getMessage()}{reset}"
        )
        
        # Add exception if present
        if record.exc_info:
            formatted += f"\n{reset}" + self.formatException(record.exc_info)
        
        return formatted


class LoggerAdapter(logging.LoggerAdapter):
    """Custom logger adapter with extra context."""
    
    def process(self, msg, kwargs):
        """Add extra context to log records."""
        if 'extra' not in kwargs:
            kwargs['extra'] = {}
        
        # Add correlation ID
        correlation_id = correlation_id_ctx.get()
        if correlation_id:
            kwargs['extra']['correlation_id'] = correlation_id
        
        # Merge with existing extra data
        if hasattr(self, 'extra_data'):
            kwargs['extra'].update(self.extra_data)
        
        return msg, kwargs


class LoggingManager:
    """Centralized logging configuration and management."""
    
    def __init__(self):
        self.configured = False
        self.loggers = {}
    
    def configure_logging(
        self,
        log_level: str = None,
        log_format: str = None,
        log_file: str = None,
        max_file_size: int = None,
        backup_count: int = None
    ):
        """Configure application logging."""
        if self.configured:
            return
        
        # Use settings defaults if not provided
        log_level = log_level or settings.LOG_LEVEL
        log_format = log_format or settings.LOG_FORMAT
        log_file = log_file or settings.LOG_FILE_PATH
        max_file_size = max_file_size or (10 * 1024 * 1024)  # 10MB default
        backup_count = backup_count or 5  # 5 backup files default
        
        # Configure structlog
        processors = [
            structlog.stdlib.filter_by_level,
            CorrelationIDProcessor(),
            TimestampProcessor(),
            ServiceInfoProcessor(),
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
        ]
        
        if log_format == 'json':
            processors.append(structlog.processors.JSONRenderer())
        else:
            processors.append(structlog.dev.ConsoleRenderer())
        
        structlog.configure(
            processors=processors,
            wrapper_class=structlog.stdlib.BoundLogger,
            logger_factory=structlog.stdlib.LoggerFactory(),
            context_class=dict,
            cache_logger_on_first_use=True,
        )
        
        # Configure standard library logging
        root_logger = logging.getLogger()
        root_logger.setLevel(getattr(logging, log_level.upper()))
        
        # Remove existing handlers
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        
        # Console handler
        console_handler = logging.StreamHandler(sys.stdout)
        if log_format == 'json':
            console_handler.setFormatter(JSONFormatter())
        else:
            console_handler.setFormatter(ColoredFormatter())
        root_logger.addHandler(console_handler)
        
        # File handler (if specified)
        if log_file:
            log_path = Path(log_file)
            log_path.parent.mkdir(parents=True, exist_ok=True)
            
            file_handler = logging.handlers.RotatingFileHandler(
                log_file,
                maxBytes=max_file_size,
                backupCount=backup_count,
                encoding='utf-8'
            )
            file_handler.setFormatter(JSONFormatter())
            root_logger.addHandler(file_handler)
        
        # Configure specific loggers
        self._configure_third_party_loggers()
        
        self.configured = True
    
    def _configure_third_party_loggers(self):
        """Configure third-party library loggers."""
        # Reduce noise from third-party libraries
        logging.getLogger('urllib3').setLevel(logging.WARNING)
        logging.getLogger('requests').setLevel(logging.WARNING)
        logging.getLogger('httpx').setLevel(logging.WARNING)
        logging.getLogger('celery').setLevel(logging.INFO)
        logging.getLogger('sqlalchemy.engine').setLevel(logging.WARNING)
        logging.getLogger('asyncio').setLevel(logging.WARNING)
    
    def get_logger(self, name: str, extra_context: Dict[str, Any] = None) -> structlog.BoundLogger:
        """Get a configured logger instance."""
        if not self.configured:
            self.configure_logging()
        
        logger = structlog.get_logger(name)
        
        if extra_context:
            logger = logger.bind(**extra_context)
        
        return logger
    
    def set_correlation_id(self, correlation_id: str = None) -> str:
        """Set correlation ID for current context."""
        if correlation_id is None:
            correlation_id = str(uuid.uuid4())
        
        correlation_id_ctx.set(correlation_id)
        return correlation_id
    
    def get_correlation_id(self) -> Optional[str]:
        """Get current correlation ID."""
        return correlation_id_ctx.get()
    
    def clear_correlation_id(self):
        """Clear correlation ID from current context."""
        correlation_id_ctx.set(None)


class SecurityLogger:
    """Specialized logger for security events."""
    
    def __init__(self):
        self.logger = get_logger(__name__ + '.security')
    
    def log_authentication_attempt(self, username: str, success: bool, ip_address: str = None, user_agent: str = None):
        """Log authentication attempts."""
        self.logger.info(
            "Authentication attempt",
            username=username,
            success=success,
            ip_address=ip_address,
            user_agent=user_agent,
            event_type="authentication"
        )
    
    def log_authorization_failure(self, username: str, resource: str, action: str, ip_address: str = None):
        """Log authorization failures."""
        self.logger.warning(
            "Authorization failure",
            username=username,
            resource=resource,
            action=action,
            ip_address=ip_address,
            event_type="authorization_failure"
        )
    
    def log_suspicious_activity(self, event: str, details: Dict[str, Any], ip_address: str = None):
        """Log suspicious activities."""
        self.logger.warning(
            "Suspicious activity detected",
            event=event,
            details=details,
            ip_address=ip_address,
            event_type="suspicious_activity"
        )
    
    def log_data_access(self, username: str, resource: str, action: str, record_count: int = None):
        """Log data access events."""
        self.logger.info(
            "Data access",
            username=username,
            resource=resource,
            action=action,
            record_count=record_count,
            event_type="data_access"
        )


class PerformanceLogger:
    """Specialized logger for performance monitoring."""
    
    def __init__(self):
        self.logger = get_logger(__name__ + '.performance')
    
    def log_request_timing(self, endpoint: str, method: str, duration_ms: float, status_code: int):
        """Log API request timing."""
        self.logger.info(
            "Request completed",
            endpoint=endpoint,
            method=method,
            duration_ms=duration_ms,
            status_code=status_code,
            event_type="request_timing"
        )
    
    def log_database_query(self, query_type: str, table: str, duration_ms: float, row_count: int = None):
        """Log database query performance."""
        self.logger.info(
            "Database query",
            query_type=query_type,
            table=table,
            duration_ms=duration_ms,
            row_count=row_count,
            event_type="database_query"
        )
    
    def log_external_api_call(self, service: str, endpoint: str, duration_ms: float, success: bool):
        """Log external API call performance."""
        self.logger.info(
            "External API call",
            service=service,
            endpoint=endpoint,
            duration_ms=duration_ms,
            success=success,
            event_type="external_api_call"
        )
    
    def log_task_execution(self, task_name: str, duration_ms: float, success: bool, items_processed: int = None):
        """Log background task execution."""
        self.logger.info(
            "Task execution",
            task_name=task_name,
            duration_ms=duration_ms,
            success=success,
            items_processed=items_processed,
            event_type="task_execution"
        )


# Global logging manager instance
logging_manager = LoggingManager()

# Convenience functions
def get_logger(name: str, extra_context: Dict[str, Any] = None) -> structlog.BoundLogger:
    """Get a configured logger instance."""
    return logging_manager.get_logger(name, extra_context)

def set_correlation_id(correlation_id: str = None) -> str:
    """Set correlation ID for current context."""
    return logging_manager.set_correlation_id(correlation_id)

def get_correlation_id() -> Optional[str]:
    """Get current correlation ID."""
    return logging_manager.get_correlation_id()

def configure_logging(**kwargs):
    """Configure application logging."""
    return logging_manager.configure_logging(**kwargs)

# Specialized loggers
security_logger = SecurityLogger()
performance_logger = PerformanceLogger() 