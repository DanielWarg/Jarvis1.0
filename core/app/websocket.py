"""
WebSocket handler for real-time AI communication
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Dict, Any, List
from fastapi import WebSocket, WebSocketDisconnect
from datetime import datetime

from .ai_brain import ai_brain

logger = logging.getLogger(__name__)

class ConnectionManager:
    """Manage WebSocket connections"""
    
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.connection_data: Dict[WebSocket, Dict] = {}
    
    async def connect(self, websocket: WebSocket):
        """Accept new connection"""
        await websocket.accept()
        self.active_connections.append(websocket)
        self.connection_data[websocket] = {
            "connected_at": datetime.now(),
            "user_id": None
        }
        logger.info(f"New WebSocket connection. Total: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        """Remove connection"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        if websocket in self.connection_data:
            del self.connection_data[websocket]
        logger.info(f"WebSocket disconnected. Total: {len(self.active_connections)}")
    
    async def send_personal_message(self, message: Dict[str, Any], websocket: WebSocket):
        """Send message to specific client"""
        try:
            await websocket.send_text(json.dumps(message))
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            self.disconnect(websocket)
    
    async def broadcast(self, message: Dict[str, Any]):
        """Send message to all connected clients"""
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(json.dumps(message))
            except Exception as e:
                logger.error(f"Error broadcasting to connection: {e}")
                disconnected.append(connection)
        
        # Clean up disconnected clients
        for connection in disconnected:
            self.disconnect(connection)

# Global connection manager
manager = ConnectionManager()

async def handle_websocket(websocket: WebSocket):
    """Main WebSocket handler"""
    await manager.connect(websocket)
    
    # Send welcome message
    await manager.send_personal_message({
        "type": "system",
        "message": "JARVIS är online och redo att ta emot kommandon",
        "timestamp": datetime.now().isoformat()
    }, websocket)
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Process different message types
            if message.get("type") == "ai_command":
                await handle_ai_command(message, websocket)
            elif message.get("type") == "system_update":
                await handle_system_update(message, websocket)
            elif message.get("type") == "ping":
                await manager.send_personal_message({
                    "type": "pong",
                    "timestamp": datetime.now().isoformat()
                }, websocket)
            else:
                logger.warning(f"Unknown message type: {message.get('type')}")
                
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)

async def handle_ai_command(message: Dict[str, Any], websocket: WebSocket):
    """Handle AI command from client"""
    try:
        user_input = message.get("prompt", "")
        user_context = message.get("context", {})
        
        if not user_input.strip():
            await manager.send_personal_message({
                "type": "error",
                "message": "Inget kommando mottaget"
            }, websocket)
            return
        
        # Send "thinking" status
        await manager.send_personal_message({
            "type": "ai_thinking",
            "message": "JARVIS tänker...",
            "timestamp": datetime.now().isoformat()
        }, websocket)
        
        # Process with AI brain
        ai_response = await ai_brain.process_command(user_input, user_context)
        
        # Send AI response back to client
        await manager.send_personal_message({
            "type": "ai_response",
            "message": ai_response["message"],
            "commands": ai_response["commands"],
            "success": ai_response["success"],
            "timestamp": ai_response["timestamp"]
        }, websocket)
        
        # If there are commands, also broadcast them for system-wide updates
        if ai_response["commands"]:
            await manager.broadcast({
                "type": "system_command",
                "commands": ai_response["commands"],
                "timestamp": ai_response["timestamp"]
            })
        
    except Exception as e:
        logger.error(f"Error handling AI command: {e}")
        await manager.send_personal_message({
            "type": "error",
            "message": f"AI-fel: {str(e)}",
            "timestamp": datetime.now().isoformat()
        }, websocket)

async def handle_system_update(message: Dict[str, Any], websocket: WebSocket):
    """Handle system status updates from client"""
    try:
        # Store system context for AI
        update_type = message.get("update_type")
        data = message.get("data", {})
        
        # Broadcast system updates to other clients if needed
        if update_type in ["metrics", "module_change", "todo_update"]:
            await manager.broadcast({
                "type": "system_sync",
                "update_type": update_type,
                "data": data,
                "timestamp": datetime.now().isoformat()
            })
        
    except Exception as e:
        logger.error(f"Error handling system update: {e}")

async def send_system_alert(alert_type: str, message: str, data: Dict[str, Any] = None):
    """Send system alert to all clients"""
    await manager.broadcast({
        "type": "system_alert",
        "alert_type": alert_type,
        "message": message,
        "data": data or {},
        "timestamp": datetime.now().isoformat()
    })
