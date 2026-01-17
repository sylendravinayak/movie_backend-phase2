from crud.base import CRUDBase
from model.agent_log import AgentLog
from schemas import AgentRequest

class CRUDAgentLog(CRUDBase[AgentLog, AgentRequest, AgentRequest]):
    pass

agent_log_crud = CRUDAgentLog(AgentLog, id_field="log_id")