from langgraph.graph import StateGraph, END
from agent.state import OpsState
from agent.nodes.planner import planner_node
from agent.nodes.pricing import pricing_node
from agent.nodes.scheduling import scheduling_node
from agent.nodes.reschedule import reschedule_node
from agent.nodes.cancel import cancel_node
from agent.nodes.feedback import feedback_node
from agent.nodes.demand_forecast import demand_forecast_node
from agent.nodes.demand_distribution import demand_distribution_node
from agent.nodes.approval import approval_node
from agent.nodes.reflection import reflection_node
from langgraph.checkpoint.postgres import PostgresSaver
from agent.infra.checkpointer import checkpointer

# Initialize configuration


graph = StateGraph(OpsState)

# Add nodes
graph.add_node("planner", planner_node)
graph.add_node("approval", approval_node)
graph.add_node("forecast", demand_forecast_node)
graph.add_node("pricing", pricing_node)
graph.add_node("scheduling", scheduling_node)
graph.add_node("reflection", reflection_node)
graph.add_node("reschedule", reschedule_node)
graph.add_node("cancel", cancel_node)
graph.add_node("feedback", feedback_node)
graph.add_node("demand_distribution", demand_distribution_node)

# Set entry point
graph.set_entry_point("planner")

# Add edges
graph.add_edge("planner", "approval")
graph.add_edge("approval", "forecast")

# Conditional routing based on decision
graph.add_conditional_edges(
    "forecast",
    lambda state: state["decision"]["route"],
    {
        
        "pricing": "pricing",
        "scheduling": "demand_distribution",
        "optimize": "reschedule"
    }
)

# Add remaining edges
graph.add_edge("demand_distribution", "scheduling")
graph.add_edge("reschedule", "cancel")
graph.add_edge("cancel","pricing")
graph.add_edge("scheduling", "pricing")
graph.add_edge("pricing", "feedback")
graph.add_edge("feedback", END)

# Compile graph with checkpointer
agent_graph = graph.compile(checkpointer=checkpointer)

# Try to generate graph visualization
try:
    png_data = agent_graph.get_graph().draw_mermaid_png()
    
    with open("agent_graph.png", "wb") as f:
        f.write(png_data)
        
    print("Graph successfully saved as 'agent_graph.png'")

except Exception as e:
    print(f"Could not generate graph. Ensure you have 'pygraphviz' installed. Error: {e}")