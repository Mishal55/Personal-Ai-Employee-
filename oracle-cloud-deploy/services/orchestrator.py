#!/usr/bin/env python3
"""
AI Employee Orchestrator
Main orchestration service that coordinates all watchers and tasks
Runs 24/7 on Oracle Cloud VM
"""

import os
import sys
import time
import json
import signal
import logging
import argparse
from pathlib import Path
from datetime import datetime
from typing import Dict, Optional
import subprocess

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/var/log/ai-employee/orchestrator.log')
    ]
)
logger = logging.getLogger('orchestrator')


class Orchestrator:
    """Main orchestrator for AI Employee services"""
    
    def __init__(self, config_path: str = None):
        self.base_dir = Path('/home/oracle/ai-employee')
        self.config_path = Path(config_path) if config_path else self.base_dir / 'config' / 'orchestrator.json'
        self.config = self.load_config()
        self.running = True
        self.services = {}
        
        # Setup signal handlers
        signal.signal(signal.SIGTERM, self.handle_signal)
        signal.signal(signal.SIGINT, self.handle_signal)
        
        logger.info(f"Orchestrator initialized. Base dir: {self.base_dir}")
    
    def load_config(self) -> dict:
        """Load orchestrator configuration"""
        default_config = {
            'watchers': {
                'enabled': True,
                'restart_on_failure': True,
                'health_check_interval': 30
            },
            'vault_sync': {
                'enabled': True,
                'sync_interval': 300,
                'auto_push': True,
                'auto_pull': True
            },
            'tasks': {
                'ceo_briefing': {
                    'enabled': True,
                    'schedule': '0 7 * * 1'  # Monday 7 AM
                },
                'invoice_processing': {
                    'enabled': True,
                    'schedule': '*/30 * * * *'  # Every 30 minutes
                },
                'data_backup': {
                    'enabled': True,
                    'schedule': '0 2 * * *'  # Daily 2 AM
                }
            },
            'logging': {
                'level': 'INFO',
                'retention_days': 30
            }
        }
        
        if self.config_path.exists():
            try:
                with open(self.config_path, 'r') as f:
                    user_config = json.load(f)
                    # Deep merge
                    for key, value in user_config.items():
                        if isinstance(value, dict) and key in default_config:
                            default_config[key].update(value)
                        else:
                            default_config[key] = value
            except Exception as e:
                logger.warning(f"Could not load config: {e}. Using defaults.")
        
        return default_config
    
    def handle_signal(self, signum, frame):
        """Handle shutdown signals gracefully"""
        logger.info(f"Received signal {signum}. Shutting down gracefully...")
        self.running = False
    
    def check_services(self) -> Dict[str, bool]:
        """Check status of all managed services"""
        status = {}
        
        services_to_check = [
            ('ai-employee-watcher', 'Watcher'),
            ('ai-employee-orchestrator', 'Orchestrator'),
            ('ai-employee-vault-sync', 'Vault Sync')
        ]
        
        for service_name, display_name in services_to_check:
            try:
                result = subprocess.run(
                    ['systemctl', 'is-active', service_name],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                status[display_name] = result.stdout.strip() == 'active'
            except Exception as e:
                logger.error(f"Error checking {display_name}: {e}")
                status[display_name] = False
        
        return status
    
    def restart_service(self, service_name: str) -> bool:
        """Restart a systemd service"""
        try:
            logger.info(f"Restarting service: {service_name}")
            subprocess.run(
                ['sudo', 'systemctl', 'restart', service_name],
                check=True,
                timeout=30
            )
            logger.info(f"Service {service_name} restarted successfully")
            return True
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to restart {service_name}: {e}")
            return False
        except Exception as e:
            logger.error(f"Error restarting {service_name}: {e}")
            return False
    
    def run_scheduled_task(self, task_name: str) -> bool:
        """Run a scheduled task"""
        task_config = self.config.get('tasks', {}).get(task_name, {})
        
        if not task_config.get('enabled', True):
            logger.info(f"Task {task_name} is disabled. Skipping.")
            return True
        
        logger.info(f"Running scheduled task: {task_name}")
        
        task_scripts = {
            'ceo_briefing': 'ceo_briefing.py',
            'invoice_processing': 'process_invoices.py',
            'data_backup': 'backup.sh'
        }
        
        script = task_scripts.get(task_name)
        if not script:
            logger.warning(f"Unknown task: {task_name}")
            return False
        
        script_path = self.base_dir / 'scripts' / script
        
        if not script_path.exists():
            logger.warning(f"Script not found: {script_path}")
            return False
        
        try:
            result = subprocess.run(
                ['python3', str(script_path)],
                capture_output=True,
                text=True,
                timeout=3600,
                cwd=str(self.base_dir)
            )
            
            if result.returncode == 0:
                logger.info(f"Task {task_name} completed successfully")
                return True
            else:
                logger.error(f"Task {task_name} failed: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            logger.error(f"Task {task_name} timed out")
            return False
        except Exception as e:
            logger.error(f"Error running task {task_name}: {e}")
            return False
    
    def health_check(self) -> bool:
        """Perform health check on all services"""
        logger.info("Performing health check...")
        
        status = self.check_services()
        all_healthy = all(status.values())
        
        for service, healthy in status.items():
            status_icon = "✓" if healthy else "✗"
            logger.info(f"  {status_icon} {service}: {'Healthy' if healthy else 'Unhealthy'}")
        
        # Auto-restart unhealthy services
        if self.config.get('watchers', {}).get('restart_on_failure', True):
            for service, healthy in status.items():
                if not healthy:
                    service_name = f"ai-employee-{service.lower().replace(' ', '-')}"
                    self.restart_service(service_name)
        
        return all_healthy
    
    def run(self):
        """Main orchestrator loop"""
        logger.info("Starting orchestrator main loop...")
        
        health_check_interval = self.config.get('watchers', {}).get('health_check_interval', 30)
        last_health_check = 0
        
        while self.running:
            try:
                current_time = time.time()
                
                # Periodic health check
                if current_time - last_health_check >= health_check_interval:
                    self.health_check()
                    last_health_check = current_time
                
                # Sync vault if enabled
                if self.config.get('vault_sync', {}).get('enabled', True):
                    sync_interval = self.config.get('vault_sync', {}).get('sync_interval', 300)
                    # Vault sync daemon handles this, just log status
                    logger.debug("Vault sync daemon is running")
                
                time.sleep(10)  # Main loop sleep
                
            except Exception as e:
                logger.error(f"Error in orchestrator loop: {e}")
                time.sleep(5)
        
        logger.info("Orchestrator shutdown complete")


def main():
    parser = argparse.ArgumentParser(description='AI Employee Orchestrator')
    parser.add_argument('--config', '-c', type=str, help='Path to config file')
    parser.add_argument('--check', action='store_true', help='Run health check and exit')
    parser.add_argument('--status', action='store_true', help='Show service status')
    parser.add_argument('--daemon', '-d', action='store_true', help='Run as daemon')
    
    args = parser.parse_args()
    
    orchestrator = Orchestrator(config_path=args.config)
    
    if args.check:
        healthy = orchestrator.health_check()
        sys.exit(0 if healthy else 1)
    
    if args.status:
        status = orchestrator.check_services()
        print(json.dumps(status, indent=2))
        sys.exit(0)
    
    if args.daemon:
        # Daemonize
        try:
            pid = os.fork()
            if pid > 0:
                sys.exit(0)
        except OSError as e:
            logger.error(f"Fork failed: {e}")
            sys.exit(1)
        
        os.setsid()
        os.umask(0)
        
        try:
            pid = os.fork()
            if pid > 0:
                sys.exit(0)
        except OSError as e:
            logger.error(f"Second fork failed: {e}")
            sys.exit(1)
    
    orchestrator.run()


if __name__ == '__main__':
    main()
