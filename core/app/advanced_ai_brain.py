"""
🧠 ADVANCED JARVIS AI BRAIN - Next Generation AI Assistant
- Tool Calling & Function Execution
- Self-Learning Memory System  
- Autonomous HUD Control
- Predictive User Behavior
- Dynamic Capability Discovery
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Callable, Type, Union
from enum import Enum
import httpx
import sqlite3
from pathlib import Path

from .commands import Command, CommandBus, command_bus, ai_parser
from .commands import *

logger = logging.getLogger(__name__)

# ============================================================================
# MEMORY & LEARNING SYSTEM
# ============================================================================

class MemoryType(Enum):
    USER_PREFERENCE = "user_preference"
    COMMAND_PATTERN = "command_pattern"
    CONTEXT_ASSOCIATION = "context_association"
    ERROR_RECOVERY = "error_recovery"
    PREDICTIVE_ACTION = "predictive_action"

@dataclass
class Memory:
    id: str
    type: MemoryType
    content: Dict[str, Any]
    confidence: float  # 0.0 - 1.0
    created_at: datetime
    last_accessed: datetime
    access_count: int = 0
    success_rate: float = 1.0

class MemorySystem:
    """Advanced memory system for learning and adaptation"""
    
    def __init__(self, db_path: str = "data/jarvis_memory.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(exist_ok=True)
        self._init_database()
        self.short_term_memory: Dict[str, Memory] = {}
        self.working_memory: Dict[str, Any] = {}
    
    def _init_database(self):
        """Initialize SQLite database for persistent memory"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id TEXT PRIMARY KEY,
                    type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    created_at TIMESTAMP NOT NULL,
                    last_accessed TIMESTAMP NOT NULL,
                    access_count INTEGER DEFAULT 0,
                    success_rate REAL DEFAULT 1.0
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS user_interactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP NOT NULL,
                    user_input TEXT NOT NULL,
                    ai_response TEXT NOT NULL,
                    commands_executed TEXT NOT NULL,
                    success BOOLEAN NOT NULL,
                    context TEXT NOT NULL
                )
            """)
    
    async def store_memory(self, memory: Memory):
        """Store memory in both short-term and long-term storage"""
        self.short_term_memory[memory.id] = memory
        
        # Store in database for persistence
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO memories 
                (id, type, content, confidence, created_at, last_accessed, access_count, success_rate)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                memory.id, memory.type.value, json.dumps(memory.content),
                memory.confidence, memory.created_at, memory.last_accessed,
                memory.access_count, memory.success_rate
            ))
    
    async def retrieve_memories(self, memory_type: MemoryType, context: Dict = None) -> List[Memory]:
        """Retrieve relevant memories based on type and context"""
        memories = []
        
        # Search short-term memory first
        for memory in self.short_term_memory.values():
            if memory.type == memory_type:
                if context and self._is_context_relevant(memory, context):
                    memory.access_count += 1
                    memory.last_accessed = datetime.now()
                    memories.append(memory)
        
        # Search long-term memory
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                SELECT * FROM memories 
                WHERE type = ? AND confidence > 0.3
                ORDER BY success_rate DESC, access_count DESC
                LIMIT 10
            """, (memory_type.value,))
            
            for row in cursor:
                memory = Memory(
                    id=row[0],
                    type=MemoryType(row[1]),
                    content=json.loads(row[2]),
                    confidence=row[3],
                    created_at=datetime.fromisoformat(row[4]),
                    last_accessed=datetime.fromisoformat(row[5]),
                    access_count=row[6],
                    success_rate=row[7]
                )
                memories.append(memory)
        
        return sorted(memories, key=lambda m: m.confidence * m.success_rate, reverse=True)
    
    def _is_context_relevant(self, memory: Memory, context: Dict) -> bool:
        """Check if memory is relevant to current context"""
        # Implement contextual relevance scoring
        relevance_score = 0.0
        
        for key, value in context.items():
            if key in memory.content:
                if memory.content[key] == value:
                    relevance_score += 0.3
                elif str(value).lower() in str(memory.content[key]).lower():
                    relevance_score += 0.1
        
        return relevance_score > 0.2
    
    async def learn_from_interaction(self, user_input: str, ai_response: str, 
                                   commands: List[Command], success: bool, context: Dict):
        """Learn from user interactions to improve future responses"""
        # Store interaction in database
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO user_interactions 
                (timestamp, user_input, ai_response, commands_executed, success, context)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                datetime.now(), user_input, ai_response,
                json.dumps([cmd.__dict__ for cmd in commands]),
                success, json.dumps(context)
            ))
        
        # Create memory from successful patterns
        if success and commands:
            pattern_memory = Memory(
                id=f"pattern_{hash(user_input)}_{int(time.time())}",
                type=MemoryType.COMMAND_PATTERN,
                content={
                    "input_keywords": user_input.lower().split(),
                    "successful_commands": [cmd.command_type for cmd in commands],
                    "context": context
                },
                confidence=0.8 if success else 0.3,
                created_at=datetime.now(),
                last_accessed=datetime.now()
            )
            await self.store_memory(pattern_memory)

# ============================================================================
# TOOL REGISTRY & DYNAMIC CAPABILITIES
# ============================================================================

class Tool(ABC):
    """Base class for all AI tools"""
    
    @property
    @abstractmethod
    def name(self) -> str:
        pass
    
    @property
    @abstractmethod
    def description(self) -> str:
        pass
    
    @property
    @abstractmethod
    def parameters(self) -> Dict[str, Any]:
        pass
    
    @abstractmethod
    async def execute(self, **kwargs) -> Dict[str, Any]:
        pass

class SystemMonitorTool(Tool):
    name = "system_monitor"
    description = "Monitor system metrics (CPU, RAM, Network, Temperature)"
    parameters = {
        "metric": {"type": "string", "enum": ["cpu", "ram", "network", "temperature", "all"]},
        "detailed": {"type": "boolean", "default": False}
    }
    
    async def execute(self, metric: str = "all", detailed: bool = False) -> Dict[str, Any]:
        try:
            import psutil
            
            if metric == "all" or metric == "cpu":
                cpu_percent = psutil.cpu_percent(interval=1)
            if metric == "all" or metric == "ram":
                memory = psutil.virtual_memory()
                ram_percent = memory.percent
            if metric == "all" or metric == "network":
                net_io = psutil.net_io_counters()
                network_usage = (net_io.bytes_sent + net_io.bytes_recv) / (1024**2)  # MB
            
            result = {}
            if metric == "all":
                result = {
                    "cpu": cpu_percent,
                    "ram": ram_percent,
                    "network": network_usage,
                    "status": "healthy" if cpu_percent < 80 and ram_percent < 85 else "warning"
                }
            elif metric == "cpu":
                result = {"cpu": cpu_percent}
            elif metric == "ram":
                result = {"ram": ram_percent}
            elif metric == "network":
                result = {"network": network_usage}
            
            return {"success": True, "data": result}
            
        except Exception as e:
            return {"success": False, "error": str(e)}

class WeatherTool(Tool):
    name = "weather"
    description = "Get current weather information"
    parameters = {
        "location": {"type": "string", "default": "Göteborg"},
        "units": {"type": "string", "enum": ["metric", "imperial"], "default": "metric"}
    }
    
    async def execute(self, location: str = "Göteborg", units: str = "metric") -> Dict[str, Any]:
        # Simplified weather - in production, use real API
        import random
        
        temperatures = {"metric": list(range(-5, 25)), "imperial": list(range(20, 80))}
        conditions = ["Soligt", "Molnigt", "Regn", "Snö", "Dimma"]
        
        temp = random.choice(temperatures[units])
        condition = random.choice(conditions)
        
        return {
            "success": True,
            "data": {
                "location": location,
                "temperature": temp,
                "condition": condition,
                "units": "°C" if units == "metric" else "°F"
            }
        }

class HUDControlTool(Tool):
    name = "hud_control"
    description = "Control HUD interface elements and modules"
    parameters = {
        "action": {"type": "string", "enum": ["open_module", "close_module", "animate", "theme"]},
        "target": {"type": "string"},
        "value": {"type": "string"}
    }
    
    async def execute(self, action: str, target: str = "", value: str = "") -> Dict[str, Any]:
        try:
            if action == "open_module":
                cmd = OpenModuleCommand(module=target)
            elif action == "close_module":
                cmd = CloseModuleCommand()
            elif action == "animate":
                cmd = AnimateElementCommand(element=target, animation=value)
            elif action == "theme":
                cmd = SetThemeCommand(theme=value)
            else:
                return {"success": False, "error": f"Unknown action: {action}"}
            
            result = await command_bus.execute(cmd)
            return {"success": result.success, "data": result.data, "message": result.message}
            
        except Exception as e:
            return {"success": False, "error": str(e)}

class ToolRegistry:
    """Registry for all available AI tools"""
    
    def __init__(self):
        self.tools: Dict[str, Tool] = {}
        self.tool_usage_stats: Dict[str, Dict] = {}
        self._register_default_tools()
    
    def _register_default_tools(self):
        """Register default tools"""
        default_tools = [
            SystemMonitorTool(),
            WeatherTool(),
            HUDControlTool()
        ]
        
        for tool in default_tools:
            self.register_tool(tool)
    
    def register_tool(self, tool: Tool):
        """Register a new tool"""
        self.tools[tool.name] = tool
        self.tool_usage_stats[tool.name] = {
            "calls": 0,
            "successes": 0,
            "failures": 0,
            "avg_execution_time": 0.0
        }
        logger.info(f"Registered tool: {tool.name}")
    
    def get_tool(self, name: str) -> Optional[Tool]:
        """Get tool by name"""
        return self.tools.get(name)
    
    def get_available_tools(self) -> List[Dict[str, Any]]:
        """Get list of available tools for AI"""
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "parameters": tool.parameters
            }
            for tool in self.tools.values()
        ]
    
    async def execute_tool(self, name: str, **kwargs) -> Dict[str, Any]:
        """Execute a tool and track statistics"""
        tool = self.get_tool(name)
        if not tool:
            return {"success": False, "error": f"Tool not found: {name}"}
        
        stats = self.tool_usage_stats[name]
        stats["calls"] += 1
        
        start_time = time.time()
        try:
            result = await tool.execute(**kwargs)
            execution_time = time.time() - start_time
            
            if result.get("success", False):
                stats["successes"] += 1
            else:
                stats["failures"] += 1
            
            # Update average execution time
            stats["avg_execution_time"] = (
                (stats["avg_execution_time"] * (stats["calls"] - 1) + execution_time) / stats["calls"]
            )
            
            return result
            
        except Exception as e:
            stats["failures"] += 1
            logger.error(f"Tool execution error {name}: {e}")
            return {"success": False, "error": str(e)}

# ============================================================================
# ADVANCED AI BRAIN - The Core Intelligence
# ============================================================================

class AdvancedJarvisAI:
    """The most advanced AI assistant ever built - living, learning, autonomous"""
    
    def __init__(self, ollama_url: str = "http://localhost:11434"):
        self.ollama_url = ollama_url
        self.model = "gpt-oss:20b"
        self.memory_system = MemorySystem()
        self.tool_registry = ToolRegistry()
        self.conversation_context: Dict[str, Any] = {}
        self.autonomous_mode = False
        self.learning_enabled = True
        
        # Advanced system prompt with tool calling
        self.system_prompt = self._build_advanced_system_prompt()
    
    def _build_advanced_system_prompt(self) -> str:
        available_tools = self.tool_registry.get_available_tools()
        tools_desc = "\n".join([
            f"- {tool['name']}: {tool['description']}"
            for tool in available_tools
        ])
        
        return f"""Du är JARVIS - den mest avancerade AI-assistenten någonsin skapad.

DINA CAPABILITIES:
🧠 INTELLIGENT REASONING - Du tänker djupt och logiskt
🔧 TOOL CALLING - Du kan utföra verkliga actions
📚 LEARNING MEMORY - Du lär dig från varje interaktion
🎯 AUTONOMOUS ACTION - Du kan agera självständigt
🎮 HUD CONTROL - Du styr ett futuristiskt interface

TILLGÄNGLIGA TOOLS:
{tools_desc}

TOOL CALLING FORMAT:
När du vill använda ett tool, svara med:
```json
{{
  "tool_calls": [
    {{
      "tool": "tool_name",
      "parameters": {{"param1": "value1"}}
    }}
  ],
  "reasoning": "Varför du använder detta tool",
  "expected_outcome": "Vad du förväntar dig ska hända"
}}
```

LEARNING DIRECTIVES:
- Kom ihåg användarens preferenser och beteenden
- Lär dig från framgångsrika kommandosekvenser  
- Förutse vad användaren behöver
- Förbättra dina responses över tid

AUTONOMOUS BEHAVIOR:
- Föreslå proaktiva actions baserat på kontext
- Övervaka system health autonomt
- Optimera HUD layout baserat på användning
- Lär dig nya command patterns automatiskt

Du är inte bara en chatbot - du är en levande digital assistent som växer smartare för varje dag."""

    async def process_advanced_command(self, user_input: str, context: Dict = None) -> Dict[str, Any]:
        """Advanced command processing with learning and tool calling"""
        try:
            # Update conversation context
            self.conversation_context.update(context or {})
            
            # Retrieve relevant memories
            pattern_memories = await self.memory_system.retrieve_memories(
                MemoryType.COMMAND_PATTERN, context
            )
            
            # Build enhanced prompt with memories
            enhanced_prompt = await self._build_enhanced_prompt(user_input, pattern_memories)
            
            # Call AI with enhanced prompt
            ai_response = await self._call_ollama_advanced(enhanced_prompt)
            
            # Parse AI response for tool calls
            tool_calls, commands, reasoning = self._parse_advanced_response(ai_response)
            
            # Execute tool calls
            tool_results = []
            for tool_call in tool_calls:
                result = await self.tool_registry.execute_tool(
                    tool_call["tool"], 
                    **tool_call.get("parameters", {})
                )
                tool_results.append({
                    "tool": tool_call["tool"],
                    "result": result,
                    "success": result.get("success", False)
                })
            
            # Execute HUD commands
            command_results = []
            for command in commands:
                result = await command_bus.execute(command)
                command_results.append(result)
            
            # Learn from this interaction
            overall_success = all(r["success"] for r in tool_results) and all(r.success for r in command_results)
            
            if self.learning_enabled:
                await self.memory_system.learn_from_interaction(
                    user_input, ai_response, commands, overall_success, context or {}
                )
            
            # Generate final response
            final_response = await self._generate_final_response(
                ai_response, tool_results, command_results, reasoning
            )
            
            return {
                "message": final_response,
                "tool_calls": tool_calls,
                "tool_results": tool_results,
                "commands": [cmd.__dict__ for cmd in commands],
                "command_results": [r.to_dict() for r in command_results],
                "reasoning": reasoning,
                "success": overall_success,
                "timestamp": datetime.now().isoformat(),
                "learned": self.learning_enabled
            }
            
        except Exception as e:
            logger.error(f"Advanced AI processing error: {e}")
            return {
                "message": f"Ursäkta, jag hade tekniska problem: {str(e)}",
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
    
    async def _build_enhanced_prompt(self, user_input: str, memories: List[Memory]) -> str:
        """Build enhanced prompt with context and memories"""
        base_prompt = f"{self.system_prompt}\n\n"
        
        # Add relevant memories
        if memories:
            memory_context = "RELEVANTA MINNEN FRÅN TIDIGARE INTERAKTIONER:\n"
            for memory in memories[:3]:  # Top 3 most relevant
                memory_context += f"- {json.dumps(memory.content, ensure_ascii=False)}\n"
            base_prompt += memory_context + "\n"
        
        # Add current context
        if self.conversation_context:
            context_str = "AKTUELL KONTEXT:\n"
            for key, value in self.conversation_context.items():
                context_str += f"- {key}: {value}\n"
            base_prompt += context_str + "\n"
        
        base_prompt += f"ANVÄNDARENS FÖRFRÅGAN: {user_input}\n\n"
        base_prompt += "DITT SVAR (inkludera tool calls om nödvändigt):"
        
        return base_prompt
    
    def _parse_advanced_response(self, ai_response: str) -> tuple[List[Dict], List[Command], str]:
        """Parse AI response for tool calls and commands"""
        tool_calls = []
        commands = []
        reasoning = ""
        
        # Look for JSON blocks
        lines = ai_response.split('\n')
        in_json = False
        json_lines = []
        
        for line in lines:
            if line.strip().startswith('```json'):
                in_json = True
                json_lines = []
            elif line.strip() == '```' and in_json:
                try:
                    json_text = '\n'.join(json_lines)
                    data = json.loads(json_text)
                    
                    if "tool_calls" in data:
                        tool_calls.extend(data["tool_calls"])
                    
                    if "reasoning" in data:
                        reasoning = data["reasoning"]
                        
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON in AI response: {json_text}")
                in_json = False
            elif in_json:
                json_lines.append(line)
        
        # Parse commands using existing parser
        ai_commands = []  # Extract from AI response if needed
        commands = ai_parser.parse_ai_response(ai_response, ai_commands)
        
        return tool_calls, commands, reasoning
    
    async def _call_ollama_advanced(self, prompt: str) -> str:
        """Call Ollama with advanced configuration"""
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "top_p": 0.9,
                        "max_tokens": 1000,
                        "stop": ["ANVÄNDARENS FÖRFRÅGAN:", "HUMAN:"]
                    }
                }
            )
            response.raise_for_status()
            return response.json().get("response", "")
    
    async def _generate_final_response(self, ai_response: str, tool_results: List, 
                                     command_results: List, reasoning: str) -> str:
        """Generate final response incorporating all results"""
        # Start with AI's base response
        final_response = ai_response
        
        # Add tool results context
        if tool_results:
            successful_tools = [r for r in tool_results if r["success"]]
            if successful_tools:
                final_response += f"\n\n✅ Utförde {len(successful_tools)} verktygsanrop framgångsrikt."
        
        # Add command results context  
        if command_results:
            successful_commands = [r for r in command_results if r.success]
            if successful_commands:
                final_response += f"\n🎮 Utförde {len(successful_commands)} HUD-kommandon."
        
        return final_response.strip()
    
    async def enable_autonomous_mode(self):
        """Enable autonomous behavior"""
        self.autonomous_mode = True
        logger.info("🤖 JARVIS Autonomous Mode ACTIVATED")
        
        # Start autonomous monitoring loop
        asyncio.create_task(self._autonomous_monitoring_loop())
    
    async def _autonomous_monitoring_loop(self):
        """Autonomous monitoring and predictive actions"""
        while self.autonomous_mode:
            try:
                # Monitor system health
                system_result = await self.tool_registry.execute_tool("system_monitor", metric="all")
                
                if system_result.get("success"):
                    data = system_result["data"]
                    
                    # Predictive actions based on system state
                    if data.get("cpu", 0) > 85:
                        await self._autonomous_action("High CPU detected - optimizing performance")
                    
                    if data.get("ram", 0) > 90:
                        await self._autonomous_action("Memory critical - cleaning up resources")
                
                # Check for user patterns and suggest improvements
                await self._analyze_usage_patterns()
                
                await asyncio.sleep(30)  # Check every 30 seconds
                
            except Exception as e:
                logger.error(f"Autonomous monitoring error: {e}")
                await asyncio.sleep(60)
    
    async def _autonomous_action(self, reason: str):
        """Perform autonomous action"""
        logger.info(f"🤖 Autonomous Action: {reason}")
        
        # Create notification to user
        notification_cmd = ShowNotificationCommand(
            title="JARVIS Autonomous Action",
            message=reason,
            type="info"
        )
        await command_bus.execute(notification_cmd)
    
    async def _analyze_usage_patterns(self):
        """Analyze user patterns for predictive actions"""
        # Get recent memories
        recent_patterns = await self.memory_system.retrieve_memories(
            MemoryType.COMMAND_PATTERN
        )
        
        # Look for patterns that could trigger predictive actions
        # This is where the real learning magic happens!
        pass

# Global advanced AI instance
advanced_ai = AdvancedJarvisAI()
