from langgraph.graph import StateGraph, END

from app.agent.state import AgentState
from app.agent.nodes.intent import extract_intent
from app.agent.nodes.decision import decide_action
from app.agent.nodes.authorize import authorize_action
from app.agent.nodes.hitl import handle_hitl
from app.agent.nodes.execute import execute_action


def build_agent_graph():
    """
    Build and compile the LangGraph agent.

    Execution flow:
        intent
          ↓
        decision
          ↓
        authorize
          ↓
        hitl
          ↓
        execute
          ↓
         END
    """

    graph = StateGraph(AgentState)

    # ------------------------------------------------------------
    # Nodes
    # ------------------------------------------------------------

    graph.add_node("intent", extract_intent)
    graph.add_node("decision", decide_action)
    graph.add_node("authorize", authorize_action)
    graph.add_node("hitl", handle_hitl)
    graph.add_node("execute", execute_action)

    # ------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------

    graph.set_entry_point("intent")

    # ------------------------------------------------------------
    # Edges
    # ------------------------------------------------------------

    graph.add_edge("intent", "decision")
    graph.add_edge("decision", "authorize")
    graph.add_edge("authorize", "hitl")
    graph.add_edge("hitl", "execute")
    graph.add_edge("execute", END)

    return graph.compile()


# ------------------------------------------------------------------
# Single compiled graph instance (IMPORTANT)
# ------------------------------------------------------------------

agent_graph = build_agent_graph()
