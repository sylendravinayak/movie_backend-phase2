from langgraph.graph import StateGraph
from utils.movie_scheduler.states import SchedulerState
from utils.movie_scheduler.nodes import (
    fetch_movies_node,
    imdb_signals_node,
    optimize_node,
    persist_node,
)

graph = StateGraph(SchedulerState)

graph.add_node("fetch_movies", fetch_movies_node)
graph.add_node("imdb", imdb_signals_node)
graph.add_node("optimize", optimize_node)
graph.add_node("persist", persist_node)

graph.set_entry_point("fetch_movies")

graph.add_edge("fetch_movies", "imdb")
graph.add_edge("imdb", "optimize")
graph.add_edge("optimize", "persist")



app = graph.compile()
