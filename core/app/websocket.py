"""
🌐 WebSocket Management for JARVIS Ultimate AI System
Real-time communication layer för AI-HUD integration
"""
from __future__ import annotations

import asyncio
import json
import logging
from typing import Dict, List, Set
from datetime import datetime

from fastapi import WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

class ConnectionManager:
    """Advanced WebSocket connection manager för JARVIS"""
    
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.connection_metadata: Dict[WebSocket, Dict] = {}
        
    async def connect(self, websocket: WebSocket, client_info: Dict = None):
        """Accept new WebSocket connection"""
        await websocket.accept()
        self.active_connections.add(websocket)
        
        # Store connection metadata
        self.connection_metadata[websocket] = {
            "connected_at": datetime.now().isoformat(),
            "client_info": client_info or {},
            "message_count": 0
        }
        
        logger.info(f"New WebSocket connection established. Total: {len(self.active_connections)}")
        
    def disconnect(self, websocket: WebSocket):
        """Remove WebSocket connection"""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            
        if websocket in self.connection_metadata:
            metadata = self.connection_metadata.pop(websocket)
            logger.info(f"WebSocket disconnected. Duration: {metadata.get('connected_at')}, "
                       f"Messages: {metadata.get('message_count', 0)}")
    
    async def send_personal_message(self, message: Dict, websocket: WebSocket):
        """Send message to specific connection"""
        try:
            await websocket.send_text(json.dumps(message, ensure_ascii=False))
            
            # Update message count
            if websocket in self.connection_metadata:
                self.connection_metadata[websocket]["message_count"] += 1
                
        except Exception as e:
            logger.error(f"Failed to send personal message: {e}")
            self.disconnect(websocket)
    
    async def broadcast(self, message: Dict):
        """Broadcast message to all connected clients"""
        if not self.active_connections:
            logger.debug("No active connections for broadcast")
            return
            
        message_str = json.dumps(message, ensure_ascii=False)
        disconnected = set()
        
        for connection in self.active_connections:
            try:
                await connection.send_text(message_str)
                
                # Update message count
                if connection in self.connection_metadata:
                    self.connection_metadata[connection]["message_count"] += 1
                    
            except Exception as e:
                logger.error(f"Failed to broadcast to connection: {e}")
                disconnected.add(connection)
        
        # Clean up disconnected connections
        for connection in disconnected:
            self.disconnect(connection)
            
        logger.debug(f"Broadcasted message to {len(self.active_connections)} connections")
    
    async def get_connection_stats(self) -> Dict:
        """Get connection statistics"""
        return {
            "total_connections": len(self.active_connections),
            "connections": [
                {
                    "connected_at": metadata.get("connected_at"),
                    "message_count": metadata.get("message_count", 0),
                    "client_info": metadata.get("client_info", {})
                }
                for metadata in self.connection_metadata.values()
            ]
        }

# Global connection manager instance
manager = ConnectionManager()

async def handle_websocket(websocket: WebSocket):
    """
    Advanced WebSocket handler för JARVIS AI communication
    Hanterar AI-kommandon, tool calling och real-time responses
    """
    from .advanced_ai_brain import advanced_ai
    
    client_info = {
        "user_agent": websocket.headers.get("user-agent", "Unknown"),
        "origin": websocket.headers.get("origin", "Unknown")
    }
    
    await manager.connect(websocket, client_info)
    
    try:
        while True:
            # Receive message from client
            data = await websocket.receive_text()
            
            try:
                message = json.loads(data)
                
                # Extract AI command details
                message_type = message.get("type", "unknown")
                prompt = message.get("prompt", "")
                context = message.get("context", {})
                
                if message_type == "ai_command" and prompt:
                    # Send acknowledgment
                    await manager.send_personal_message({
                        "type": "processing",
                        "message": "JARVIS är i process av att förstå ditt kommando...",
                        "timestamp": datetime.now().isoformat()
                    }, websocket)
                    
                    # Process with Advanced AI Brain
                    try:
                        ai_result = await advanced_ai.process_advanced_command(prompt, context)
                        
                        # Send AI response
                        await manager.send_personal_message({
                            "type": "ai_response",
                            "data": ai_result,
                            "timestamp": datetime.now().isoformat()
                        }, websocket)
                        
                        # If there were tool calls or commands, broadcast to all clients
                        if ai_result.get("tool_calls") or ai_result.get("commands"):
                            await manager.broadcast({
                                "type": "system_update",
                                "message": "JARVIS utförde actions på systemet",
                                "details": {
                                    "tool_calls": len(ai_result.get("tool_calls", [])),
                                    "commands": len(ai_result.get("commands", [])),
                                    "success": ai_result.get("success", False)
                                },
                                "timestamp": datetime.now().isoformat()
                            })
                            
                    except Exception as ai_error:
                        logger.error(f"AI processing error: {ai_error}")
                        await manager.send_personal_message({
                            "type": "error",
                            "message": f"JARVIS AI error: {str(ai_error)}",
                            "timestamp": datetime.now().isoformat()
                        }, websocket)
                
                elif message_type == "ping":
                    # Health check
                    await manager.send_personal_message({
                        "type": "pong",
                        "timestamp": datetime.now().isoformat(),
                        "status": "JARVIS is alive and learning"
                    }, websocket)
                
                elif message_type == "get_stats":
                    # Send connection statistics
                    stats = await manager.get_connection_stats()
                    await manager.send_personal_message({
                        "type": "stats",
                        "data": stats,
                        "timestamp": datetime.now().isoformat()
                    }, websocket)
                
                else:
                    # Unknown message type
                    await manager.send_personal_message({
                        "type": "error",
                        "message": f"Unknown message type: {message_type}",
                        "supported_types": ["ai_command", "ping", "get_stats"],
                        "timestamp": datetime.now().isoformat()
                    }, websocket)
                    
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON received: {e}")
                await manager.send_personal_message({
                    "type": "error",
                    "message": "Invalid JSON format",
                    "timestamp": datetime.now().isoformat()
                }, websocket)
                
    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected normally")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
    finally:
        manager.disconnect(websocket)