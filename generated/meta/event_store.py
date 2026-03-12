import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List

class EventStore:
    """
    Log Epistêmico Imutável.
    A Fase 6 (Alinhamento Core ESAA) exige um vocabulário estrito de eventos.
    Todo append gera um `activity_event` com controle tipado de `action` e `event_seq` monotônico.
    """
    
    def __init__(self, log_dir: Path):
        self.log_file = log_dir / "activity.jsonl"
        self.log_dir = log_dir
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger("ACO_EventStore")
        
    def _get_next_seq(self) -> int:
        """Lê o último event_seq do ledger ou inicia em 1."""
        if not self.log_file.exists():
            return 1
        last_seq = 0
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        data = json.loads(line)
                        if "activity_event" in data:
                            last_seq = data["activity_event"].get("event_seq", last_seq)
        except Exception as e:
            self.logger.error(f"Erro lendo Ledger: {e}")
        return last_seq + 1

    def append_event(self, action: str, task_id: str, payload: Dict[str, Any], file_updates: Optional[List[Dict[str, str]]] = None) -> str:
        """
        Emite um evento padronizado ESAA (e.g. 'orchestrator.file.write', 'verify.fail').
        Garante a monotonicidade do event_seq.
        """
        import uuid
        from datetime import datetime, timezone
        
        event_id = str(uuid.uuid4())
        event_seq = self._get_next_seq()
        
        envelope = {
            "activity_event": {
                "schema_version": "0.4.0",
                "event_id": event_id,
                "event_seq": event_seq,
                "ts": datetime.now(timezone.utc).isoformat(),
                "actor": "orchestrator",
                "action": action,
                "task_id": task_id,
                "payload": payload
            }
        }
        
        if file_updates:
            envelope["file_updates"] = file_updates

        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(envelope) + '\n')
            return event_id
        except Exception as e:
            self.logger.error(f"Failed to append ESAA event {action} for {task_id}: {e}")
            return ""

    def query_history(self) -> list[Dict[str, Any]]:
        if not self.log_file.exists():
            return []
        with open(self.log_file, 'r', encoding='utf-8') as f:
            return [json.loads(line) for line in f if line.strip()]
