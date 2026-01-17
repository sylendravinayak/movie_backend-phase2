import math

def pricing_policy(
    forecast_demand: float,
    occupancy: float,
    current_price: float,
    base_price: float
):
 
    forecast_demand = max(forecast_demand, 0.0)
    occupancy = min(max(occupancy, 0.0), 1.0)

  
    demand_mid = 2.5
    demand_sensitivity = 0.18
    demand_factor = 1 + demand_sensitivity * math.tanh((forecast_demand - demand_mid) / demand_mid)

   
    occ_mid = 0.5
    occ_sensitivity = 0.12
    occ_factor = 1 + occ_sensitivity * math.tanh((occupancy - occ_mid) / occ_mid)

   
    raw_price = base_price * demand_factor * occ_factor

  
    alpha = 0.3  
    new_price = (alpha * raw_price) + ((1 - alpha) * current_price)

    
    min_price = base_price * 0.8
    max_price = base_price * 1.5

    new_price = max(min_price, min(new_price, max_price))

    return round(new_price, 2)
