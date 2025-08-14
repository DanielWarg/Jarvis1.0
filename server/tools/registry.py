from __future__ import annotations

from typing import Any, Callable, Dict, Optional, Tuple, Type

from pydantic import BaseModel, Field, model_validator


class EmptyArgs(BaseModel):
    """Tomma parametrar för verktyg som inte kräver input."""
    pass


class SetVolumeArgs(BaseModel):
    level: Optional[int] = Field(default=None, description="Målnivå 0-100")
    delta: Optional[int] = Field(default=None, description="Relativ justering -100..100")

    @model_validator(mode="after")
    def validate_level_or_delta(self) -> "SetVolumeArgs":
        if self.level is None and self.delta is None:
            raise ValueError("Ange antingen 'level' eller 'delta'.")
        if self.level is not None:
            if not isinstance(self.level, int) or self.level < 0 or self.level > 100:
                raise ValueError("'level' måste vara ett heltal 0-100.")
        if self.delta is not None:
            if not isinstance(self.delta, int) or self.delta < -100 or self.delta > 100:
                raise ValueError("'delta' måste vara ett heltal mellan -100 och 100.")
        return self


class SayArgs(BaseModel):
    text: str = Field(..., min_length=1, max_length=500, description="Text att säga/visa")


class DisplayArgs(BaseModel):
    text: str = Field(..., min_length=1, max_length=1000, description="Text att visa i HUD")


# Verktygsspecifikationer
# Namngivning anpassad till jarvis-tools router (PLAY/PAUSE/SET_VOLUME) + SAY/DISPLAY
ToolModel = Type[BaseModel]
ExecutorFn = Callable[[Dict[str, Any], Optional[Any]], Dict[str, Any]]


def _exec_play(_args: Dict[str, Any], _memory: Optional[Any]) -> Dict[str, Any]:
    return {"ok": True, "tool": "PLAY", "result": {"status": "playing"}}


def _exec_pause(_args: Dict[str, Any], _memory: Optional[Any]) -> Dict[str, Any]:
    return {"ok": True, "tool": "PAUSE", "result": {"status": "paused"}}


def _exec_set_volume(args: Dict[str, Any], _memory: Optional[Any]) -> Dict[str, Any]:
    level = args.get("level")
    delta = args.get("delta")
    return {"ok": True, "tool": "SET_VOLUME", "result": {"level": level, "delta": delta}}


def _exec_say(args: Dict[str, Any], _memory: Optional[Any]) -> Dict[str, Any]:
    return {"ok": True, "tool": "SAY", "result": {"spoken": args.get("text", "")}}


def _exec_display(args: Dict[str, Any], _memory: Optional[Any]) -> Dict[str, Any]:
    return {"ok": True, "tool": "DISPLAY", "result": {"shown": args.get("text", "")}}


REGISTRY: Dict[str, Tuple[ToolModel, ExecutorFn, str]] = {
    "PLAY": (EmptyArgs, _exec_play, "Starta/fortsätt uppspelning"),
    "PAUSE": (EmptyArgs, _exec_pause, "Pausa uppspelning"),
    "SET_VOLUME": (SetVolumeArgs, _exec_set_volume, "Ställ volym (level 0-100) eller justera (delta -100..100)"),
    "SAY": (SayArgs, _exec_say, "Säg en kort fras (TTS eller textrespons)"),
    "DISPLAY": (DisplayArgs, _exec_display, "Visa en kort text i HUD"),
}


def list_tool_specs() -> Dict[str, Any]:
    """Returnera namn, beskrivning och JSON-schema för parametrar för varje verktyg."""
    out: Dict[str, Any] = {}
    for name, (model, _exec, desc) in REGISTRY.items():
        schema = model.schema() if hasattr(model, "schema") else {}
        out[name] = {"description": desc, "schema": schema}
    return out


def validate_and_execute_tool(name: str, args: Dict[str, Any], memory: Optional[Any] = None) -> Dict[str, Any]:
    """Validera argument med Pydantic och exekvera verktyg. No-tool-if-unsure policy: kasta på valideringsfel."""
    if not isinstance(name, str) or name.upper() not in REGISTRY:
        return {"ok": False, "error": "unknown_tool"}
    model, exec_fn, _desc = REGISTRY[name.upper()]
    try:
        payload = model.model_validate(args or {})
    except Exception as e:
        return {"ok": False, "error": "invalid_args", "message": str(e)}
    try:
        res = exec_fn(payload.model_dump(), memory)
        return res
    except Exception as e:
        return {"ok": False, "error": "execution_failed", "message": str(e)}


