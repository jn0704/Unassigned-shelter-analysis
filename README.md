# Unassigned-shelter-analysis

The unassigned shelter analysis (USA) assumes that citizens receive no instructions on which shelter to go to after the earthquake. The only information they have are shelter locations and the road network. In the model, each individual evacuates to the nearest shelter along the shortest available path through the road network. However, if someone arrives at a shelter that is already fully occupied, they must move to the next nearest shelter, and their evacuation distance increases. We assume a shelter capacity of 1 square meter per individual. 

* Step 1: Identify the shortest path from population node i to shelter node j, where P_i > 0
* Step 2: If C_j = 0, identify the shortest path from the shelter node to another shelter node j
* Step 3: If C_j = 0, iterate at step 2
* Step 4: If C_j ≥ P_i, assign P_i to the path. Next, C_j = C_j - P_i and P_i = 0
* Step 5: If C_j < P_i, Assign P_i - C_j to the path. Next, C_j = 0 and P_i = P_i - C_j
* Step 6: If the sum of populations or shelter capacities is zero, end the process. If not, we return to step 1
