"""
Command Bus Architecture for JARVIS HUD Control
AI-generated commands → Command Bus → HUD Actions
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Type, TypeVar, Union
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Command Types
T = TypeVar('T', bound='Command')

class Command(ABC):
    """Base command interface"""
    command_type: str
    timestamp: datetime
    
    def __init__(self):
        self.timestamp = datetime.now()

class CommandHandler(ABC):
    """Base command handler interface"""
    
    @abstractmethod
    async def handle(self, command: Command) -> Dict[str, Any]:
        """Handle the command and return result"""
        pass

class CommandResult:
    """Result of command execution"""
    
    def __init__(self, success: bool, data: Dict[str, Any] = None, message: str = ""):
        self.success = success
        self.data = data or {}
        self.message = message
        self.timestamp = datetime.now()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "data": self.data,
            "message": self.message,
            "timestamp": self.timestamp.isoformat()
        }

# ============================================================================
# HUD COMMANDS - Specific commands for controlling the HUD
# ============================================================================

@dataclass
class OpenModuleCommand(Command):
    """Open a specific HUD module"""
    command_type = "open_module"
    module: str  # "calendar", "mail", "finance"
    
@dataclass
class CloseModuleCommand(Command):
    """Close current active module"""
    command_type = "close_module"

@dataclass
class SystemStatusCommand(Command):
    """Show system status information"""
    command_type = "system_status"
    detailed: bool = False

@dataclass
class AddTodoCommand(Command):
    """Add a new todo item"""
    command_type = "add_todo"
    text: str
    priority: str = "normal"  # "low", "normal", "high"

@dataclass
class ToggleTodoCommand(Command):
    """Toggle todo completion"""
    command_type = "toggle_todo"
    todo_id: str

@dataclass
class SetThemeCommand(Command):
    """Change HUD theme/colors"""
    command_type = "set_theme"
    theme: str  # "cyan", "red", "green", "purple"

@dataclass
class ShowWeatherCommand(Command):
    """Display weather information"""
    command_type = "show_weather"
    location: Optional[str] = None

@dataclass
class PlayMediaCommand(Command):
    """Control media playback"""
    command_type = "play_media"
    action: str  # "play", "pause", "next", "previous"
    
@dataclass
class SetVolumeCommand(Command):
    """Set system volume"""
    command_type = "set_volume"
    level: int  # 0-100

@dataclass
class ShowNotificationCommand(Command):
    """Display notification to user"""
    command_type = "show_notification"
    title: str
    message: str
    type: str = "info"  # "info", "warning", "error", "success"
    duration: int = 5000  # ms

@dataclass
class VoiceResponseCommand(Command):
    """AI voice response to user"""
    command_type = "voice_response"
    text: str
    voice: str = "sv-SE"

@dataclass
class AnimateElementCommand(Command):
    """Animate HUD element"""
    command_type = "animate_element"
    element: str  # "core", "particles", "statusbar"
    animation: str  # "pulse", "rotate", "glow"
    duration: int = 1000

@dataclass
class UpdateMetricsCommand(Command):
    """Update system metrics display"""
    command_type = "update_metrics"
    cpu: Optional[float] = None
    memory: Optional[float] = None
    network: Optional[float] = None

@dataclass
class SearchCommand(Command):
    """Perform search operation"""
    command_type = "search"
    query: str
    type: str = "general"  # "general", "files", "web"

# ============================================================================
# COMMAND BUS - Central command processing system
# ============================================================================

class CommandBus:
    """Central command bus for processing AI-generated commands"""
    
    def __init__(self):
        self.handlers: Dict[str, CommandHandler] = {}
        self.middleware: List[callable] = []
        self.execution_log: List[Dict] = []
    
    def register_handler(self, command_type: str, handler: CommandHandler):
        """Register a command handler"""
        self.handlers[command_type] = handler
        logger.info(f"Registered handler for command: {command_type}")
    
    def add_middleware(self, middleware: callable):
        """Add middleware for command processing"""
        self.middleware.append(middleware)
    
    async def execute(self, command: Command) -> CommandResult:
        """Execute a command through the bus"""
        try:
            # Log command execution
            log_entry = {
                "command_type": command.command_type,
                "timestamp": command.timestamp.isoformat(),
                "command_data": command.__dict__
            }
            
            # Apply middleware (e.g., logging, validation, auth)
            for middleware in self.middleware:
                await middleware(command)
            
            # Find and execute handler
            handler = self.handlers.get(command.command_type)
            if not handler:
                error_msg = f"No handler registered for command: {command.command_type}"
                logger.error(error_msg)
                log_entry["result"] = "error"
                log_entry["error"] = error_msg
                self.execution_log.append(log_entry)
                return CommandResult(False, message=error_msg)
            
            # Execute command
            result_data = await handler.handle(command)
            result = CommandResult(True, result_data, f"Command {command.command_type} executed successfully")
            
            log_entry["result"] = "success"
            log_entry["result_data"] = result_data
            self.execution_log.append(log_entry)
            
            logger.info(f"Command executed: {command.command_type}")
            return result
            
        except Exception as e:
            error_msg = f"Error executing command {command.command_type}: {str(e)}"
            logger.error(error_msg)
            
            log_entry["result"] = "error"
            log_entry["error"] = error_msg
            self.execution_log.append(log_entry)
            
            return CommandResult(False, message=error_msg)
    
    async def execute_batch(self, commands: List[Command]) -> List[CommandResult]:
        """Execute multiple commands in sequence"""
        results = []
        for command in commands:
            result = await self.execute(command)
            results.append(result)
            
            # Stop batch execution on critical errors
            if not result.success and command.command_type in ["system_status", "voice_response"]:
                logger.warning(f"Stopping batch execution due to critical error in {command.command_type}")
                break
        
        return results
    
    def get_execution_log(self, limit: int = 100) -> List[Dict]:
        """Get recent command execution log"""
        return self.execution_log[-limit:]
    
    def get_registered_commands(self) -> List[str]:
        """Get list of all registered command types"""
        return list(self.handlers.keys())

# ============================================================================
# AI COMMAND PARSER - Convert AI responses to Commands
# ============================================================================

class AICommandParser:
    """Parse AI responses and convert to executable commands"""
    
    def __init__(self):
        self.command_mapping = {
            "open_module": OpenModuleCommand,
            "close_module": CloseModuleCommand,
            "system_status": SystemStatusCommand,
            "add_todo": AddTodoCommand,
            "toggle_todo": ToggleTodoCommand,
            "set_theme": SetThemeCommand,
            "show_weather": ShowWeatherCommand,
            "play_media": PlayMediaCommand,
            "set_volume": SetVolumeCommand,
            "show_notification": ShowNotificationCommand,
            "voice_response": VoiceResponseCommand,
            "animate_element": AnimateElementCommand,
            "update_metrics": UpdateMetricsCommand,
            "search": SearchCommand,
        }
    
    def parse_ai_response(self, ai_message: str, ai_commands: List[Dict]) -> List[Command]:
        """Parse AI response and extract commands"""
        commands = []
        
        # Parse explicit JSON commands from AI
        for cmd_data in ai_commands:
            command = self._create_command_from_dict(cmd_data)
            if command:
                commands.append(command)
        
        # Parse implicit commands from text
        text_commands = self._extract_text_commands(ai_message)
        commands.extend(text_commands)
        
        # Always add voice response for AI message
        if ai_message.strip():
            voice_cmd = VoiceResponseCommand()
            voice_cmd.text = ai_message.strip()
            commands.append(voice_cmd)
        
        return commands
    
    def _create_command_from_dict(self, cmd_data: Dict) -> Optional[Command]:
        """Create command object from dictionary"""
        try:
            action = cmd_data.get("action")
            command_class = self.command_mapping.get(action)
            
            if not command_class:
                logger.warning(f"Unknown command action: {action}")
                return None
            
            # Create command with parameters
            if action == "open_module":
                return OpenModuleCommand(module=cmd_data.get("module", ""))
            elif action == "add_todo":
                return AddTodoCommand(
                    text=cmd_data.get("text", ""),
                    priority=cmd_data.get("priority", "normal")
                )
            elif action == "show_notification":
                return ShowNotificationCommand(
                    title=cmd_data.get("title", "JARVIS"),
                    message=cmd_data.get("message", ""),
                    type=cmd_data.get("type", "info")
                )
            elif action == "play_media":
                return PlayMediaCommand(action=cmd_data.get("media_action", "play"))
            elif action == "set_volume":
                return SetVolumeCommand(level=cmd_data.get("level", 50))
            elif action == "search":
                return SearchCommand(
                    query=cmd_data.get("query", ""),
                    type=cmd_data.get("search_type", "general")
                )
            else:
                # Simple commands without parameters
                return command_class()
                
        except Exception as e:
            logger.error(f"Error creating command from dict: {e}")
            return None
    
    def _extract_text_commands(self, text: str) -> List[Command]:
        """Extract commands from natural language text"""
        commands = []
        text_lower = text.lower()
        
        # Pattern matching for Swedish commands
        patterns = [
            (["öppna kalender", "visa kalender"], lambda: OpenModuleCommand(module="calendar")),
            (["öppna mail", "visa mail", "öppna e-post"], lambda: OpenModuleCommand(module="mail")),
            (["öppna ekonomi", "visa ekonomi"], lambda: OpenModuleCommand(module="finance")),
            (["stäng modul", "stäng fönster"], lambda: CloseModuleCommand()),
            (["systemstatus", "visa system", "hur mår systemet"], lambda: SystemStatusCommand(detailed=True)),
            (["visa väder", "hur är vädret"], lambda: ShowWeatherCommand()),
            (["spela musik", "starta musik"], lambda: PlayMediaCommand(action="play")),
            (["pausa musik", "stoppa musik"], lambda: PlayMediaCommand(action="pause")),
            (["nästa låt", "nästa spår"], lambda: PlayMediaCommand(action="next")),
        ]
        
        for keywords, command_factory in patterns:
            if any(keyword in text_lower for keyword in keywords):
                try:
                    command = command_factory()
                    commands.append(command)
                except Exception as e:
                    logger.error(f"Error creating command from text pattern: {e}")
        
        return commands

# Global instances
command_bus = CommandBus()
ai_parser = AICommandParser()
