from langgraph.graph import StateGraph, END
from movie_recommender.node.extract_generes import extract_genres
from movie_recommender.node.recommend_movies import recommend_movies
from movie_recommender.node.fetch_booked_movies import fetch_booked_movies
from movie_recommender.state import RecState

graph = StateGraph(RecState)

graph.add_node("history", fetch_booked_movies)
graph.add_node("genres", extract_genres)
graph.add_node("recommend", recommend_movies)

graph.set_entry_point("history")
graph.add_edge("history", "genres")
graph.add_edge("genres", "recommend")
graph.add_edge("recommend", END)

app_graph = graph.compile()
