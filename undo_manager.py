from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass
from datetime import datetime
import json
import os

@dataclass
class UndoAction:
    timestamp: float
    description: str
    old_state: Dict[Tuple[int, int], str]
    new_state: Dict[Tuple[int, int], str]

class UndoManager:
    def __init__(self, max_history: int = 50):
        self.max_history = max_history
        self.undo_stack: List[UndoAction] = []
        self.redo_stack: List[UndoAction] = []
        self._backup_file = os.path.join(os.path.expanduser("~"), ".ttsdeck_backup.json")

    def push(self, description: str, old_state: Dict[Tuple[int, int], str], 
            new_state: Dict[Tuple[int, int], str]):
        """Push a new action onto the undo stack."""
        action = UndoAction(
            timestamp=datetime.now().timestamp(),
            description=description,
            old_state=dict(old_state),
            new_state=dict(new_state)
        )
        self.undo_stack.append(action)
        self.redo_stack.clear()  # Clear redo stack when new action is added
        
        # Trim history if needed
        if len(self.undo_stack) > self.max_history:
            self.undo_stack.pop(0)
            
        self._backup_current_state()

    def undo(self) -> Optional[Dict[Tuple[int, int], str]]:
        """Undo the last action and return the previous state."""
        if not self.undo_stack:
            return None
            
        action = self.undo_stack.pop()
        self.redo_stack.append(action)
        return action.old_state

    def redo(self) -> Optional[Dict[Tuple[int, int], str]]:
        """Redo the last undone action and return the new state."""
        if not self.redo_stack:
            return None
            
        action = self.redo_stack.pop()
        self.undo_stack.append(action)
        return action.new_state

    def can_undo(self) -> bool:
        return bool(self.undo_stack)

    def can_redo(self) -> bool:
        return bool(self.redo_stack)

    def _backup_current_state(self):
        """Create a backup of the current state."""
        try:
            if self.undo_stack:
                latest = self.undo_stack[-1]
                backup = {
                    "timestamp": latest.timestamp,
                    "state": {f"{k[0]},{k[1]}": v for k, v in latest.new_state.items()}
                }
                with open(self._backup_file, 'w') as f:
                    json.dump(backup, f, indent=2)
        except Exception:
            pass

    def restore_backup(self) -> Optional[Dict[Tuple[int, int], str]]:
        """Restore state from backup file if it exists."""
        try:
            if os.path.exists(self._backup_file):
                with open(self._backup_file, 'r') as f:
                    backup = json.load(f)
                    state = {
                        tuple(map(int, k.split(','))): v 
                        for k, v in backup["state"].items()
                    }
                    return state
        except Exception:
            pass
        return None