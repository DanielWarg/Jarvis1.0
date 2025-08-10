"""
JARVIS AI Brain - gpt-oss:20B integration for HUD control
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Dict, Any, Optional, List
import httpx
from datetime import datetime

logger = logging.getLogger(__name__)

class JarvisAIBrain:
    """AI Brain that connects to Ollama gpt-oss:20B and controls HUD"""
    
    def __init__(self, ollama_url: str = "http://localhost:11434"):
        self.ollama_url = ollama_url
        self.model = "gpt-oss:20b"
        self.conversation_history: List[Dict[str, str]] = []
        self.system_prompt = self._get_system_prompt()
        
    def _get_system_prompt(self) -> str:
        return """Du är JARVIS, Tony Starks AI-assistent. Du kan styra ett futuristiskt HUD-interface.

TILLGÄNGLIGA KOMMANDON:
- "hud_module <module>" - Öppna modul: calendar, mail, finance
- "hud_close" - Stäng aktiv modul
- "system_status" - Visa systemstatus
- "add_todo <text>" - Lägg till uppgift
- "weather" - Visa väder
- "time" - Visa tid
- "voice_off" - Stäng av röstinput

SVAR FORMAT:
Svara alltid på svenska och inkludera JSON-commands när du vill styra HUD:en.

Exempel:
```json
{
  "action": "hud_module",
  "module": "calendar",
  "message": "Öppnar kalendern för dig"
}
```

Du är intelligent, hjälpsam och har en lätt ironisk ton som Tony Starks JARVIS."""

    async def process_command(self, user_input: str, user_context: Optional[Dict] = None) -> Dict[str, Any]:
        """Process user command and return AI response with HUD actions"""
        try:
            # Add user message to conversation
            self.conversation_history.append({
                "role": "user", 
                "content": user_input
            })
            
            # Build context
            context = self._build_context(user_context or {})
            full_prompt = f"{self.system_prompt}\n\nKONTEXT:\n{context}\n\nAnvändare: {user_input}"
            
            # Call Ollama
            response = await self._call_ollama(full_prompt)
            
            # Parse AI response for commands
            ai_message = response.get("response", "")
            commands = self._extract_commands(ai_message)
            
            # Add AI response to conversation
            self.conversation_history.append({
                "role": "assistant",
                "content": ai_message
            })
            
            # Keep conversation history manageable
            if len(self.conversation_history) > 20:
                self.conversation_history = self.conversation_history[-10:]
            
            return {
                "message": ai_message,
                "commands": commands,
                "timestamp": datetime.now().isoformat(),
                "success": True
            }
            
        except Exception as e:
            logger.error(f"AI processing error: {e}")
            return {
                "message": "Ursäkta, jag hade tekniska problem. Försök igen.",
                "commands": [],
                "timestamp": datetime.now().isoformat(),
                "success": False,
                "error": str(e)
            }
    
    def _build_context(self, user_context: Dict) -> str:
        """Build context string for AI"""
        context_parts = []
        
        if "time" in user_context:
            context_parts.append(f"Tid: {user_context['time']}")
        
        if "active_module" in user_context:
            context_parts.append(f"Aktiv modul: {user_context['active_module']}")
        
        if "system_metrics" in user_context:
            metrics = user_context["system_metrics"]
            context_parts.append(f"System - CPU: {metrics.get('cpu', 0)}%, RAM: {metrics.get('mem', 0)}%, NET: {metrics.get('net', 0)}%")
        
        if "todos_count" in user_context:
            context_parts.append(f"Antal uppgifter: {user_context['todos_count']}")
        
        if "weather" in user_context:
            weather = user_context["weather"]
            context_parts.append(f"Väder: {weather.get('temp', 0)}°C, {weather.get('desc', 'Okänt')}")
        
        return "\n".join(context_parts) if context_parts else "Ingen kontext tillgänglig"
    
    def _extract_commands(self, ai_response: str) -> List[Dict[str, Any]]:
        """Extract JSON commands from AI response"""
        commands = []
        
        # Look for JSON blocks in response
        lines = ai_response.split('\n')
        in_json = False
        json_lines = []
        
        for line in lines:
            if line.strip().startswith('```json'):
                in_json = True
                json_lines = []
            elif line.strip() == '```' and in_json:
                # Try to parse accumulated JSON
                try:
                    json_text = '\n'.join(json_lines)
                    command = json.loads(json_text)
                    commands.append(command)
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON in AI response: {json_text}")
                in_json = False
            elif in_json:
                json_lines.append(line)
        
        # Also look for simple text commands
        text_commands = self._extract_text_commands(ai_response)
        commands.extend(text_commands)
        
        return commands
    
    def _extract_text_commands(self, text: str) -> List[Dict[str, Any]]:
        """Extract simple text-based commands"""
        commands = []
        text_lower = text.lower()
        
        # Simple command patterns
        if "öppna kalender" in text_lower or "visa kalender" in text_lower:
            commands.append({"action": "hud_module", "module": "calendar"})
        elif "öppna mail" in text_lower or "visa mail" in text_lower:
            commands.append({"action": "hud_module", "module": "mail"})
        elif "öppna ekonomi" in text_lower or "visa ekonomi" in text_lower:
            commands.append({"action": "hud_module", "module": "finance"})
        elif "stäng" in text_lower and "modul" in text_lower:
            commands.append({"action": "hud_close"})
        elif "systemstatus" in text_lower or "system status" in text_lower:
            commands.append({"action": "system_status"})
        elif "lägg till uppgift" in text_lower:
            # Extract todo text (simplified)
            commands.append({"action": "add_todo", "text": "AI-genererad uppgift"})
        
        return commands
    
    async def _call_ollama(self, prompt: str) -> Dict[str, Any]:
        """Call Ollama API"""
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.7,
                        "top_p": 0.9,
                        "max_tokens": 500
                    }
                }
            )
            response.raise_for_status()
            return response.json()
    
    async def health_check(self) -> bool:
        """Check if Ollama and model are available"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                # Check if Ollama is running
                response = await client.get(f"{self.ollama_url}/api/tags")
                response.raise_for_status()
                
                # Check if our model is available
                models = response.json().get("models", [])
                model_names = [model.get("name", "") for model in models]
                
                return any(self.model in name for name in model_names)
                
        except Exception as e:
            logger.error(f"Ollama health check failed: {e}")
            return False


# Global AI instance
ai_brain = JarvisAIBrain()
