from undo_manager import UndoManager


def test_undo_redo_and_backup(tmp_path):
    backup = tmp_path / "backup.json"
    manager = UndoManager(max_history=2, backup_file=backup)
    manager.push("first", {}, {(0, 0): "A"})
    manager.push("second", {(0, 0): "A"}, {(0, 0): "B"})
    manager.push("third", {(0, 0): "B"}, {(0, 0): "C"})

    assert len(manager.undo_stack) == 2
    assert manager.undo() == {(0, 0): "B"}
    assert manager.redo() == {(0, 0): "C"}
    assert manager.restore_backup() == {(0, 0): "C"}
