from langgraph.checkpoint.postgres import PostgresSaver

CHECKPOINT_DB_URL = "postgresql://postgres:raja807@localhost:5432/agent_checkpoints"

_checkpointer_cm = None
checkpointer = None

def init_checkpointer():
    global _checkpointer_cm, checkpointer
    _checkpointer_cm = PostgresSaver.from_conn_string(CHECKPOINT_DB_URL)
    checkpointer = _checkpointer_cm.__enter__()
    checkpointer.setup()
    return checkpointer

def close_checkpointer():
    global _checkpointer_cm
    if _checkpointer_cm:
        _checkpointer_cm.__exit__(None, None, None)
