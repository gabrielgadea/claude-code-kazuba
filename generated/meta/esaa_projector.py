import json
import hashlib
from typing import List, Dict, Any

class ESAAProjector:
    """
    Motor Híbrido Causal: Transforma Event Sourcing num "Read Model" snapshot.
    Projectos determinísticos para roadmap.json (A "Visão Purificada").
    """

    @staticmethod
    def project_events(events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Função Pura. Aplica os eventos cronologicamente num snapshot de estado.
        """
        state: Dict[str, Any] = {
            "meta": {"schema_version": "0.4.0", "run": {}},
            "project": {},
            "tasks": [],
            "indexes": {}
        }

        # Para cada evento emitido pelo orquestrador MCTS e validado
        for entry in events:
            if "activity_event" not in entry:
                continue
                
            event = entry["activity_event"]
            action = event.get("action")
            task_id = event.get("task_id")
            payload = event.get("payload", {})
            
            # Rebobina causalidade básica
            if action == "task.create":
                state["tasks"].append({"id": task_id, "status": "todo", "details": payload})
            
            elif action == "verify.ok":
                # Find the task and mark it success
                for t in state["tasks"]:
                    if t["id"] == task_id:
                        t["status"] = "done"
                        if "n0_result" in payload:
                            t["last_success"] = payload["n0_result"]
                            
            elif action == "verify.fail" or action == "output.rejected":
                for t in state["tasks"]:
                    if t["id"] == task_id:
                        t["status"] = "failed"
                        t["fail_reason"] = payload.get("reason", "Unknown failure")

        return state

    @staticmethod
    def compute_sha256(state: Dict[str, Any]) -> str:
        """
        Gera a Assinatura ESAA Canonical.
        Exclui `meta.run` do hash para evitar auto-referências e ciclos.
        """
        hash_input = {
            "schema_version": state.get("meta", {}).get("schema_version", "0.4.0"),
            "project": state.get("project", {}),
            "tasks": state.get("tasks", []),
            "indexes": state.get("indexes", {})
        }
        
        # O GitHub orienta: JSON UTF-8, sorted keys, no spaces com newline no fim
        canonical_json = json.dumps(hash_input, sort_keys=True, separators=(',', ':')) + '\n'
        return hashlib.sha256(canonical_json.encode('utf-8')).hexdigest()

    @staticmethod
    def esaa_verify(events: List[Dict[str, Any]], roadmap_json: Dict[str, Any]) -> Dict[str, str]:
        """
        A prova matemática de imutabilidade.
        esaa verify == true se a causalidade temporal na trilha de fato gera o snapshot roadmap.json garantido na raiz.
        """
        projected = ESAAProjector.project_events(events)
        computed_hash = ESAAProjector.compute_sha256(projected)
        
        stored_hash = roadmap_json.get("meta", {}).get("run", {}).get("projection_hash_sha256")
        
        if computed_hash == stored_hash:
            return {"verify_status": "ok", "hash": computed_hash}
        else:
            return {"verify_status": "mismatch", "expected": stored_hash, "computed": computed_hash}
