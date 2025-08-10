"""
🎮 COMMAND HANDLERS - Execute AI commands on the HUD
These handlers bridge the gap between AI intent and HUD actions
"""
from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

from .commands import *
from .websocket import manager

logger = logging.getLogger(__name__)

# ============================================================================
# HUD COMMAND HANDLERS - Convert Commands to HUD Actions
# ============================================================================

class HUDModuleHandler(CommandHandler):
    """Handle HUD module operations"""
    
    async def handle(self, command: Command) -> Dict[str, Any]:
        if isinstance(command, OpenModuleCommand):
            return await self._open_module(command.module)
        elif isinstance(command, CloseModuleCommand):
            return await self._close_module()
        else:
            raise ValueError(f"Unsupported command type: {type(command)}")
    
    async def _open_module(self, module: str) -> Dict[str, Any]:
        """Open HUD module"""
        valid_modules = ["calendar", "mail", "finance"]
        
        if module not in valid_modules:
            return {
                "success": False,
                "error": f"Unknown module: {module}. Valid modules: {valid_modules}"
            }
        
        # Send WebSocket message to all connected clients
        await manager.broadcast({
            "type": "hud_command",
            "action": "open_module",
            "module": module,
            "timestamp": datetime.now().isoformat()
        })
        
        logger.info(f"Opened HUD module: {module}")
        return {
            "success": True,
            "action": "module_opened",
            "module": module,
            "message": f"Öppnade {module}-modulen"
        }
    
    async def _close_module(self) -> Dict[str, Any]:
        """Close active HUD module"""
        await manager.broadcast({
            "type": "hud_command",
            "action": "close_module",
            "timestamp": datetime.now().isoformat()
        })
        
        logger.info("Closed active HUD module")
        return {
            "success": True,
            "action": "module_closed",
            "message": "Stängde aktiv modul"
        }

class SystemStatusHandler(CommandHandler):
    """Handle system status commands"""
    
    async def handle(self, command: SystemStatusCommand) -> Dict[str, Any]:
        try:
            # Get system metrics
            import psutil
            
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            system_data = {
                "cpu": round(cpu_percent, 1),
                "memory": round(memory.percent, 1),
                "disk": round(disk.percent, 1),
                "status": "healthy" if cpu_percent < 80 and memory.percent < 85 else "warning"
            }
            
            if command.detailed:
                # Add detailed metrics
                network = psutil.net_io_counters()
                system_data.update({
                    "memory_total": round(memory.total / (1024**3), 2),  # GB
                    "memory_used": round(memory.used / (1024**3), 2),   # GB
                    "disk_total": round(disk.total / (1024**3), 2),     # GB
                    "disk_free": round(disk.free / (1024**3), 2),       # GB
                    "network_sent": round(network.bytes_sent / (1024**2), 2),  # MB
                    "network_recv": round(network.bytes_recv / (1024**2), 2),  # MB
                    "boot_time": datetime.fromtimestamp(psutil.boot_time()).isoformat()
                })
            
            # Send to HUD
            await manager.broadcast({
                "type": "system_update",
                "data": system_data,
                "detailed": command.detailed,
                "timestamp": datetime.now().isoformat()
            })
            
            return {
                "success": True,
                "data": system_data,
                "message": "Systemstatus uppdaterad"
            }
            
        except Exception as e:
            logger.error(f"System status error: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Kunde inte hämta systemstatus"
            }

class TodoHandler(CommandHandler):
    """Handle todo operations"""
    
    async def handle(self, command: Command) -> Dict[str, Any]:
        if isinstance(command, AddTodoCommand):
            return await self._add_todo(command.text, command.priority)
        elif isinstance(command, ToggleTodoCommand):
            return await self._toggle_todo(command.todo_id)
        else:
            raise ValueError(f"Unsupported command type: {type(command)}")
    
    async def _add_todo(self, text: str, priority: str) -> Dict[str, Any]:
        """Add new todo item"""
        if not text.strip():
            return {
                "success": False,
                "error": "Todo text cannot be empty"
            }
        
        todo_data = {
            "id": f"todo_{int(datetime.now().timestamp())}",
            "text": text.strip(),
            "priority": priority,
            "done": False,
            "created_at": datetime.now().isoformat()
        }
        
        # Send to HUD
        await manager.broadcast({
            "type": "todo_command",
            "action": "add",
            "todo": todo_data,
            "timestamp": datetime.now().isoformat()
        })
        
        logger.info(f"Added todo: {text}")
        return {
            "success": True,
            "action": "todo_added",
            "todo": todo_data,
            "message": f"Lade till uppgift: {text}"
        }
    
    async def _toggle_todo(self, todo_id: str) -> Dict[str, Any]:
        """Toggle todo completion status"""
        await manager.broadcast({
            "type": "todo_command",
            "action": "toggle",
            "todo_id": todo_id,
            "timestamp": datetime.now().isoformat()
        })
        
        return {
            "success": True,
            "action": "todo_toggled",
            "todo_id": todo_id,
            "message": "Ändrade uppgiftsstatus"
        }

class NotificationHandler(CommandHandler):
    """Handle notifications and alerts"""
    
    async def handle(self, command: ShowNotificationCommand) -> Dict[str, Any]:
        notification_data = {
            "id": f"notif_{int(datetime.now().timestamp())}",
            "title": command.title,
            "message": command.message,
            "type": command.type,
            "duration": command.duration,
            "timestamp": datetime.now().isoformat()
        }
        
        # Send to HUD
        await manager.broadcast({
            "type": "notification",
            "notification": notification_data
        })
        
        logger.info(f"Sent notification: {command.title} - {command.message}")
        return {
            "success": True,
            "notification": notification_data,
            "message": "Notification skickad"
        }

class VoiceResponseHandler(CommandHandler):
    """Handle AI voice responses"""
    
    async def handle(self, command: VoiceResponseCommand) -> Dict[str, Any]:
        voice_data = {
            "text": command.text,
            "voice": command.voice,
            "timestamp": datetime.now().isoformat()
        }
        
        # Send to HUD for text-to-speech
        await manager.broadcast({
            "type": "voice_response",
            "voice": voice_data
        })
        
        return {
            "success": True,
            "voice": voice_data,
            "message": "Röstrespons skickad"
        }

class AnimationHandler(CommandHandler):
    """Handle HUD animations"""
    
    async def handle(self, command: AnimateElementCommand) -> Dict[str, Any]:
        animation_data = {
            "element": command.element,
            "animation": command.animation,
            "duration": command.duration,
            "timestamp": datetime.now().isoformat()
        }
        
        # Send to HUD
        await manager.broadcast({
            "type": "animation_command",
            "animation": animation_data
        })
        
        logger.info(f"Animation triggered: {command.element} - {command.animation}")
        return {
            "success": True,
            "animation": animation_data,
            "message": f"Animation utförd: {command.animation}"
        }

class ThemeHandler(CommandHandler):
    """Handle theme changes"""
    
    async def handle(self, command: SetThemeCommand) -> Dict[str, Any]:
        valid_themes = ["cyan", "red", "green", "purple", "blue", "orange"]
        
        if command.theme not in valid_themes:
            return {
                "success": False,
                "error": f"Unknown theme: {command.theme}. Valid themes: {valid_themes}"
            }
        
        theme_data = {
            "theme": command.theme,
            "timestamp": datetime.now().isoformat()
        }
        
        # Send to HUD
        await manager.broadcast({
            "type": "theme_command",
            "theme": theme_data
        })
        
        logger.info(f"Theme changed to: {command.theme}")
        return {
            "success": True,
            "theme": theme_data,
            "message": f"Tema ändrat till: {command.theme}"
        }

class WeatherHandler(CommandHandler):
    """Handle weather display"""
    
    async def handle(self, command: ShowWeatherCommand) -> Dict[str, Any]:
        try:
            # Simplified weather data - in production, use real API
            import random
            
            location = command.location or "Göteborg"
            weather_data = {
                "location": location,
                "temperature": random.randint(-5, 25),
                "condition": random.choice(["Soligt", "Molnigt", "Regn", "Snö", "Dimma"]),
                "humidity": random.randint(30, 90),
                "wind_speed": random.randint(0, 15),
                "timestamp": datetime.now().isoformat()
            }
            
            # Send to HUD
            await manager.broadcast({
                "type": "weather_update",
                "weather": weather_data
            })
            
            return {
                "success": True,
                "weather": weather_data,
                "message": f"Väderdata uppdaterad för {location}"
            }
            
        except Exception as e:
            logger.error(f"Weather error: {e}")
            return {
                "success": False,
                "error": str(e),
                "message": "Kunde inte hämta väderdata"
            }

class MediaHandler(CommandHandler):
    """Handle media playback controls"""
    
    async def handle(self, command: PlayMediaCommand) -> Dict[str, Any]:
        valid_actions = ["play", "pause", "next", "previous", "stop"]
        
        if command.action not in valid_actions:
            return {
                "success": False,
                "error": f"Unknown media action: {command.action}"
            }
        
        media_data = {
            "action": command.action,
            "timestamp": datetime.now().isoformat()
        }
        
        # Send to HUD
        await manager.broadcast({
            "type": "media_command",
            "media": media_data
        })
        
        logger.info(f"Media command: {command.action}")
        return {
            "success": True,
            "media": media_data,
            "message": f"Media {command.action}"
        }

# ============================================================================
# HANDLER REGISTRATION - Register all handlers with command bus
# ============================================================================

def register_all_handlers():
    """Register all command handlers with the command bus"""
    from .commands import command_bus
    
    # Module handlers
    module_handler = HUDModuleHandler()
    command_bus.register_handler("open_module", module_handler)
    command_bus.register_handler("close_module", module_handler)
    
    # System handlers
    system_handler = SystemStatusHandler()
    command_bus.register_handler("system_status", system_handler)
    
    # Todo handlers
    todo_handler = TodoHandler()
    command_bus.register_handler("add_todo", todo_handler)
    command_bus.register_handler("toggle_todo", todo_handler)
    
    # UI handlers
    notification_handler = NotificationHandler()
    command_bus.register_handler("show_notification", notification_handler)
    
    voice_handler = VoiceResponseHandler()
    command_bus.register_handler("voice_response", voice_handler)
    
    animation_handler = AnimationHandler()
    command_bus.register_handler("animate_element", animation_handler)
    
    theme_handler = ThemeHandler()
    command_bus.register_handler("set_theme", theme_handler)
    
    # External data handlers
    weather_handler = WeatherHandler()
    command_bus.register_handler("show_weather", weather_handler)
    
    media_handler = MediaHandler()
    command_bus.register_handler("play_media", media_handler)
    
    logger.info("🎮 All command handlers registered successfully!")

# Auto-register handlers when module is imported
register_all_handlers()
