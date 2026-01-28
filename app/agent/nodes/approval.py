"""
Approval Node - Validates constraints before execution
"""
from agent.state import OpsState
from agent.tools.constraint_manager import ConstraintManager
from langgraph.errors import NodeInterrupt
from database import SessionLocal

def approval_node(state: OpsState):
    """Validate and merge all constraints"""
    
    db = SessionLocal()
    
    try:
        # Get user constraints from state
        user_constraints = state.get("display_constraints", [])
        
        if not user_constraints:
            # No user constraints - just fetch MongoDB constraints
            state["merged_constraints"] = {}
            state["constraint_conflicts"] = []
            db.close()
            return state
        
        # Convert user constraints to dict format
        constraint_dicts = [
            {
                "movie": c["movie"],
                "min_shows_per_day": c.get("min_shows_per_day"),
                "max_shows_per_day": c.get("max_shows_per_day"),
                "prime_show_quota": c.get("prime_show_quota")
            }
            for c in user_constraints
        ]
        
        # Validate constraints
        manager = ConstraintManager(db)
        merged_map, conflicts = manager.validate_all_constraints(constraint_dicts)
        
        # Check for hard conflicts (errors)
        hard_conflicts = [c for c in conflicts if c.startswith("❌")]
        
        if hard_conflicts:
            # Raise interrupt with conflicts
            conflict_msg = "\n".join(hard_conflicts)
            raise NodeInterrupt(
                f"Constraint validation failed:\n\n{conflict_msg}\n\n"
                f"Please resolve these conflicts before proceeding."
            )
        
        # Store merged constraints in state
        state["merged_constraints"] = {
            k: v.dict() for k, v in merged_map.items()
        }
        state["constraint_conflicts"] = conflicts
        
        # Log warnings
        warnings = [c for c in conflicts if c.startswith("⚠️")]
        if warnings:
            print("Constraint warnings:")
            for w in warnings:
                print(f"  {w}")
        
        state["output"] = (
            f"Constraints validated: {len(merged_map)} movies, "
            f"{len(hard_conflicts)} errors, {len(warnings)} warnings"
        )
        
    finally:
        db.close()
    
    return state