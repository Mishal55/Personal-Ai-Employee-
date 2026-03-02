#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WhatsApp Watcher - Silver Tier Feature
Uses Playwright to monitor WhatsApp Web for new messages and create action items.

Configuration:
- Set WHATSAPP_PHONE environment variable for sending messages (optional)
- Messages are saved to AI_Employee_Vault/Inbox/ for processing

Usage:
    python whatsapp_watcher.py --watch     # Continuous monitoring
    python whatsapp_watcher.py --check     # Single check
    python whatsapp_watcher.py --send      # Send a message (requires phone config)
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional
from playwright.sync_api import sync_playwright, Page, TimeoutError as PlaywrightTimeout


# Configuration
VAULT_PATH = Path(os.environ.get('AI_VAULT_PATH', r'D:\Personal Ai Employee\AI_Employee_Vault'))
WATCHER_STATE_FILE = VAULT_PATH / 'watchers' / 'whatsapp' / 'state.json'
LOG_FILE = VAULT_PATH / 'Logs' / 'whatsapp_watcher.log'
INBOX_PATH = VAULT_PATH / 'Inbox'

# Ensure directories exist
WATCHER_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
INBOX_PATH.mkdir(parents=True, exist_ok=True)


def log_message(message: str, level: str = "INFO"):
    """Log a message to the log file."""
    timestamp = datetime.now().isoformat()
    log_entry = f"[{timestamp}] [{level}] {message}\n"
    with open(LOG_FILE, 'a', encoding='utf-8') as f:
        f.write(log_entry)
    print(log_entry.strip())


def load_state() -> dict:
    """Load the watcher state from file."""
    if WATCHER_STATE_FILE.exists():
        with open(WATCHER_STATE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"last_message_time": None, "processed_chats": [], "session_data": None}


def save_state(state: dict):
    """Save the watcher state to file."""
    with open(WATCHER_STATE_FILE, 'w', encoding='utf-8') as f:
        json.dump(state, f, indent=2, default=str)


def create_inbox_item(message: dict) -> str:
    """Create an inbox item for a new WhatsApp message."""
    timestamp = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    contact_name = message.get('contact', 'Unknown').replace(' ', '_')
    filename = f"WHATSAPP_{contact_name}_{timestamp}.md"
    filepath = INBOX_PATH / filename
    
    content = f"""---
source: whatsapp
contact: {message.get('contact', 'Unknown')}
received_at: {message.get('timestamp', datetime.now().isoformat())}
chat_id: {message.get('chat_id', 'unknown')}
processed: false
---

# WhatsApp Message

**From:** {message.get('contact', 'Unknown')}
**Received:** {message.get('timestamp', datetime.now().isoformat())}

---

## Message Content

{message.get('content', '')}

---

## AI Employee Actions

- [ ] Categorize message intent
- [ ] Determine if response needed
- [ ] Draft response if needed (requires approval)
- [ ] Archive after processing

---

*Created by WhatsApp Watcher (Silver Tier)*
"""
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    log_message(f"Created inbox item: {filename}")
    return filename


def wait_for_qr(page: Page, timeout: int = 60000) -> bool:
    """Wait for QR code to appear and be scanned."""
    log_message("Waiting for QR code scan...")
    try:
        # Wait for the main chat interface (indicates successful login)
        page.wait_for_selector('div[data-testid="default-user"]', timeout=timeout)
        log_message("WhatsApp Web loaded successfully")
        return True
    except PlaywrightTimeout:
        log_message("QR code scan timeout. Please restart and scan QR code.")
        return False


def extract_messages(page: Page) -> list:
    """Extract recent messages from the current chat."""
    messages = []
    try:
        # Find message elements
        message_elements = page.query_selector_all('div[data-testid="message-in"]')
        
        for msg_el in message_elements[-10:]:  # Last 10 messages
            try:
                content_el = msg_el.query_selector('div[data-testid="message-content"]')
                if content_el:
                    content = content_el.inner_text()
                    
                    # Get timestamp
                    time_el = msg_el.query_selector('span[data-testid="message-timestamp"]')
                    timestamp = time_el.inner_text() if time_el else datetime.now().isoformat()
                    
                    messages.append({
                        'content': content.strip(),
                        'timestamp': timestamp,
                        'direction': 'incoming'
                    })
            except Exception as e:
                log_message(f"Error extracting message: {e}", "WARNING")
                
    except Exception as e:
        log_message(f"Error extracting messages: {e}", "WARNING")
    
    return messages


def get_chat_list(page: Page) -> list:
    """Get list of chats from the sidebar."""
    chats = []
    try:
        chat_elements = page.query_selector_all('div[data-testid="chat-list"] div[role="row"]')
        
        for chat_el in chat_elements[:20]:  # Top 20 chats
            try:
                name_el = chat_el.query_selector('span[dir="auto"]')
                if name_el:
                    chats.append({
                        'name': name_el.inner_text(),
                        'element': chat_el
                    })
            except Exception:
                continue
    except Exception as e:
        log_message(f"Error getting chat list: {e}", "WARNING")
    
    return chats


def check_new_messages(page: Page, state: dict) -> list:
    """Check for new messages since last check."""
    new_messages = []
    
    try:
        # Get current chat messages
        messages = extract_messages(page)
        
        if messages and state.get('last_message_time'):
            # Check if any messages are newer than last check
            for msg in messages:
                if msg['content'] not in state.get('processed_messages', []):
                    # Get current contact name
                    chat_elements = page.query_selector_all('div[data-testid="chat-list"] div[role="row"]')
                    contact_name = "Unknown"
                    
                    new_messages.append({
                        'contact': contact_name,
                        'content': msg['content'],
                        'timestamp': datetime.now().isoformat(),
                        'chat_id': f"chat_{len(new_messages)}"
                    })
                    
                    state.setdefault('processed_messages', []).append(msg['content'])
                    
    except Exception as e:
        log_message(f"Error checking new messages: {e}", "WARNING")
    
    return new_messages


def send_message(page: Page, contact: str, message: str) -> bool:
    """Send a WhatsApp message to a contact."""
    try:
        # Search for contact
        search_box = page.query_selector('div[data-testid="oxalq_224"] input, [data-testid="search"] input')
        if not search_box:
            log_message("Search box not found", "ERROR")
            return False
        
        search_box.fill(contact)
        time.sleep(2)  # Wait for search results
        
        # Click on contact
        contact_el = page.query_selector('div[role="row"] span[dir="auto"]')
        if contact_el:
            contact_el.click()
            time.sleep(1)
            
            # Type and send message
            message_box = page.query_selector('div[data-testid="compose-box-input"]')
            if message_box:
                message_box.fill(message)
                time.sleep(0.5)
                
                send_btn = page.query_selector('button[data-testid="compose-btn-send"]')
                if send_btn:
                    send_btn.click()
                    log_message(f"Message sent to {contact}")
                    return True
                    
        log_message("Could not send message - contact or message box not found", "WARNING")
        return False
        
    except Exception as e:
        log_message(f"Error sending message: {e}", "ERROR")
        return False


def run_watcher(check_interval: int = 60, max_duration: int = 0):
    """Run the WhatsApp watcher in continuous mode."""
    log_message(f"Starting WhatsApp Watcher (check interval: {check_interval}s)")
    
    state = load_state()
    start_time = time.time()
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=['--disable-gpu'])
        context = browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        )
        page = context.new_page()
        
        # Navigate to WhatsApp Web
        log_message("Navigating to WhatsApp Web...")
        page.goto('https://web.whatsapp.com', wait_until='networkidle')
        
        # Wait for QR scan / login
        if not wait_for_qr(page):
            log_message("Failed to load WhatsApp Web", "ERROR")
            browser.close()
            return
        
        # Save session state
        state['session_active'] = True
        state['last_check'] = datetime.now().isoformat()
        save_state(state)
        
        try:
            while True:
                # Check for new messages
                new_msgs = check_new_messages(page, state)
                
                for msg in new_msgs:
                    create_inbox_item(msg)
                    log_message(f"New message from {msg['contact']}")
                
                state['last_check'] = datetime.now().isoformat()
                save_state(state)
                
                # Check if we should stop
                if max_duration > 0 and (time.time() - start_time) > max_duration:
                    log_message(f"Max duration ({max_duration}s) reached, stopping watcher")
                    break
                
                time.sleep(check_interval)
                
        except KeyboardInterrupt:
            log_message("Watcher stopped by user")
        finally:
            state['session_active'] = False
            save_state(state)
            browser.close()
            log_message("WhatsApp Watcher stopped")


def run_single_check():
    """Run a single check for new messages."""
    log_message("Running single WhatsApp check...")
    
    state = load_state()
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=['--disable-gpu'])
        context = browser.new_context()
        page = context.new_page()
        
        page.goto('https://web.whatsapp.com', wait_until='networkidle')
        
        if wait_for_qr(page, timeout=30000):
            new_msgs = check_new_messages(page, state)
            for msg in new_msgs:
                create_inbox_item(msg)
            log_message(f"Check complete. Found {len(new_msgs)} new messages.")
        else:
            log_message("Could not access WhatsApp - not logged in", "WARNING")
        
        browser.close()


def main():
    parser = argparse.ArgumentParser(description='WhatsApp Watcher for AI Employee')
    parser.add_argument('--watch', action='store_true', help='Run in continuous watch mode')
    parser.add_argument('--check', action='store_true', help='Run a single check')
    parser.add_argument('--interval', type=int, default=60, help='Check interval in seconds (for watch mode)')
    parser.add_argument('--max-duration', type=int, default=0, help='Max run duration in seconds (0 = unlimited)')
    
    args = parser.parse_args()
    
    if args.watch:
        run_watcher(check_interval=args.interval, max_duration=args.max_duration)
    elif args.check:
        run_single_check()
    else:
        parser.print_help()
        print("\nExamples:")
        print("  python whatsapp_watcher.py --watch --interval 120")
        print("  python whatsapp_watcher.py --check")
        print("  python whatsapp_watcher.py --watch --max-duration 3600")


if __name__ == '__main__':
    main()
