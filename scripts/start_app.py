#!/usr/bin/env python3
"""
Application Startup Script

Comprehensive startup script for the Cross-Market Arbitrage Tool.
Handles database initialization, health checks, and service startup.
"""

import asyncio
import sys
import logging
import subprocess
import signal
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor

# Add src to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.config.settings import get_settings
from src.utils.health_checks import HealthCheckManager
from src.utils.logging import configure_logging, get_logger

# Configure logging
configure_logging()
logger = get_logger(__name__)

settings = get_settings()


class ApplicationManager:
    """Manages the startup and shutdown of all application services."""
    
    def __init__(self):
        """Initialize the application manager."""
        self.processes = {}
        self.running = False
        self.health_manager = HealthCheckManager()
        
    async def check_dependencies(self) -> bool:
        """Check if all required dependencies are available."""
        logger.info("Checking system dependencies...")
        
        try:
            # Check database connectivity
            health_results = await self.health_manager.run_all_checks()
            
            if not health_results.get('database', {}).get('healthy', False):
                logger.error("Database is not accessible")
                return False
            
            # Check Redis connectivity
            if not health_results.get('redis', {}).get('healthy', False):
                logger.error("Redis is not accessible")
                return False
            
            logger.info("✓ All dependencies are available")
            return True
            
        except Exception as e:
            logger.error(f"Dependency check failed: {str(e)}")
            return False
    
    async def initialize_database(self) -> bool:
        """Initialize the database if needed."""
        logger.info("Initializing database...")
        
        try:
            # Run database initialization script
            result = subprocess.run(
                [sys.executable, "scripts/init_db.py"],
                cwd=project_root,
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes timeout
            )
            
            if result.returncode == 0:
                logger.info("✓ Database initialization completed")
                return True
            else:
                logger.error(f"Database initialization failed: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error("Database initialization timed out")
            return False
        except Exception as e:
            logger.error(f"Database initialization error: {str(e)}")
            return False
    
    def start_celery_worker(self):
        """Start Celery worker process."""
        logger.info("Starting Celery worker...")
        
        try:
            cmd = [
                "celery", "-A", "src.tasks", "worker",
                "--loglevel=info",
                "--concurrency=4",
                "--prefetch-multiplier=1"
            ]
            
            process = subprocess.Popen(
                cmd,
                cwd=project_root,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True
            )
            
            self.processes['celery_worker'] = process
            logger.info(f"✓ Celery worker started (PID: {process.pid})")
            
        except Exception as e:
            logger.error(f"Failed to start Celery worker: {str(e)}")
    
    def start_celery_beat(self):
        """Start Celery beat scheduler."""
        logger.info("Starting Celery beat scheduler...")
        
        try:
            cmd = [
                "celery", "-A", "src.tasks", "beat",
                "--loglevel=info",
                "--schedule=/tmp/celerybeat-schedule"
            ]
            
            process = subprocess.Popen(
                cmd,
                cwd=project_root,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True
            )
            
            self.processes['celery_beat'] = process
            logger.info(f"✓ Celery beat started (PID: {process.pid})")
            
        except Exception as e:
            logger.error(f"Failed to start Celery beat: {str(e)}")
    
    def start_api_server(self):
        """Start FastAPI server."""
        logger.info("Starting FastAPI server...")
        
        try:
            cmd = [
                "uvicorn", "src.main:app",
                "--host", settings.API_HOST,
                "--port", str(settings.API_PORT),
                "--workers", "1" if settings.DEBUG else "4",
                "--access-log",
                "--reload" if settings.DEBUG else "--no-reload"
            ]
            
            process = subprocess.Popen(
                cmd,
                cwd=project_root,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True
            )
            
            self.processes['api_server'] = process
            logger.info(f"✓ FastAPI server started (PID: {process.pid})")
            
        except Exception as e:
            logger.error(f"Failed to start FastAPI server: {str(e)}")
    
    def start_dashboard(self):
        """Start Streamlit dashboard."""
        if not settings.DEBUG:
            logger.info("Skipping dashboard in production mode")
            return
            
        logger.info("Starting Streamlit dashboard...")
        
        try:
            cmd = [
                "streamlit", "run", "src/dashboard/main.py",
                "--server.port", "8501",
                "--server.address", "0.0.0.0",
                "--server.headless", "true",
                "--browser.gatherUsageStats", "false"
            ]
            
            process = subprocess.Popen(
                cmd,
                cwd=project_root,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True
            )
            
            self.processes['dashboard'] = process
            logger.info(f"✓ Streamlit dashboard started (PID: {process.pid})")
            
        except Exception as e:
            logger.error(f"Failed to start dashboard: {str(e)}")
    
    def monitor_processes(self):
        """Monitor running processes and restart if needed."""
        while self.running:
            time.sleep(30)  # Check every 30 seconds
            
            for name, process in list(self.processes.items()):
                if process.poll() is not None:  # Process has terminated
                    logger.warning(f"Process {name} has terminated (exit code: {process.returncode})")
                    
                    # Restart critical processes
                    if name in ['api_server', 'celery_worker']:
                        logger.info(f"Restarting {name}...")
                        del self.processes[name]
                        
                        if name == 'api_server':
                            self.start_api_server()
                        elif name == 'celery_worker':
                            self.start_celery_worker()
    
    async def health_check_loop(self):
        """Periodic health checks."""
        while self.running:
            try:
                health_results = await self.health_manager.run_all_checks()
                
                # Log any unhealthy services
                for service, result in health_results.items():
                    if not result.get('healthy', False):
                        logger.warning(f"Health check failed for {service}: {result.get('error', 'Unknown')}")
                
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Health check error: {str(e)}")
                await asyncio.sleep(60)
    
    def setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown."""
        def signal_handler(signum, frame):
            logger.info(f"Received signal {signum}, shutting down...")
            self.shutdown()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
    
    def shutdown(self):
        """Gracefully shutdown all services."""
        logger.info("Shutting down application...")
        self.running = False
        
        # Terminate all processes
        for name, process in self.processes.items():
            logger.info(f"Stopping {name}...")
            
            try:
                process.terminate()
                
                # Wait for graceful shutdown
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    logger.warning(f"Force killing {name}...")
                    process.kill()
                    
            except Exception as e:
                logger.error(f"Error stopping {name}: {str(e)}")
        
        logger.info("Application shutdown complete")
    
    async def start(self):
        """Start the complete application."""
        logger.info("🚀 Starting Cross-Market Arbitrage Tool...")
        
        # Setup signal handlers
        self.setup_signal_handlers()
        
        # Check dependencies
        if not await self.check_dependencies():
            logger.error("❌ Dependency check failed")
            return False
        
        # Initialize database
        if not await self.initialize_database():
            logger.error("❌ Database initialization failed")
            return False
        
        # Start services
        self.running = True
        
        # Start background services first
        self.start_celery_worker()
        self.start_celery_beat()
        
        # Wait a bit for Celery to start
        await asyncio.sleep(5)
        
        # Start web services
        self.start_api_server()
        self.start_dashboard()
        
        # Start monitoring tasks
        with ThreadPoolExecutor() as executor:
            # Start process monitor in background thread
            monitor_future = executor.submit(self.monitor_processes)
            
            # Start health check loop
            health_future = asyncio.create_task(self.health_check_loop())
            
            logger.info("🎉 All services started successfully!")
            logger.info(f"📊 API Server: http://{settings.API_HOST}:{settings.API_PORT}")
            if settings.DEBUG:
                logger.info("📈 Dashboard: http://localhost:8501")
            logger.info("📖 API Docs: http://localhost:8000/docs")
            
            try:
                # Wait for health check task to complete (it runs forever)
                await health_future
            except KeyboardInterrupt:
                logger.info("Received keyboard interrupt")
            finally:
                self.shutdown()
                monitor_future.cancel()
        
        return True


async def main():
    """Main startup function."""
    app_manager = ApplicationManager()
    
    try:
        success = await app_manager.start()
        if not success:
            sys.exit(1)
    except Exception as e:
        logger.error(f"Application startup failed: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main()) 