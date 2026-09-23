from typing import TypedDict, Annotated, List , Optional
from langchain.core.messages import BaseMessage
from langgraph.core.messages import add_messages


class TraceEntry(TypedDict):
    step: int
    agent: str
    action: str
    result: str


class State(TypedDict):
    prompt:str
    messages = Annotated[List[BaseMessage],add_messages]
    user_api:str
    execution_trace:List[TraceEntry]

def add_trace(state:State,agent:str,action:str,result:str)->List[TraceEntry]:
    trace = state.get('execution_trace')

    entry_trace:TraceEntry = {
        'step':
        
    }


