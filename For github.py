import osmnx as ox
import networkx as nx
import matplotlib.pyplot as plt
import pandas as pd
from osgeo import ogr
import json
from networkx.readwrite import json_graph

"""
In this module, we read shapefiles for the anlaysis and check the information
"""
### Road files and read information

## read shapefiles
pop_ds = ogr.Open('population point layer')
pop_lyr = pop_ds.GetLayer()
shelter_ds = ogr.Open('shelter location point layer')
shelter_lyr = shelter_ds.GetLayer()
road_ds = ogr.Open('road network line layer')
road_lyr = road_ds.GetLayer()

## Get field name of road network
rfn = [] #road field name
road_field = road_lyr.GetLayerDefn()
for n in range(road_field.GetFieldCount()) :
        name = road_field.GetFieldDefn(n).name
        rfn.append(name)
rfn.append('Y')
rfn.append('X')

## Get field name and type of pop layer
pfn = [] #road field name
pop_field = pop_lyr.GetLayerDefn()
for n in range(pop_field.GetFieldCount()) :
        name = pop_field.GetFieldDefn(n).name
        pfn.append(name)

## Get field name of shelter layer
sfn = [] #road field name
shelter_field = shelter_lyr.GetLayerDefn()
for n in range(shelter_field.GetFieldCount()) :
        name = shelter_field.GetFieldDefn(n).name
        sfn.append(name)

"""
In this module, we create a dataset for the analysis
The algorithm converts the shapefiles into a graph and a set of dataframes
If we have done this part before, we do not have to do this
"""
### Create a graph from road network
### Create dictionaries for refering node's coordinates

## create empty graph
G = nx.Graph()

## Create data frame for saving road information
road_df = pd.DataFrame(columns=['START_NODE', 'END_NODE', 'COORDINATES', 'LEN', 'HAZARD'])

## Prepare empty dataset to save an information
dict_coorToNum = {} # the dictionary to find a node number from coordinates
dict_numToCoor = {} # the dictionary to find a coordinates from a node number
key = 0 # row of matrix
value = 0 # column of matrix
num = 0

## add node and edge in the enpy graph
for feat in road_lyr : # call features from a road mayer
    geom = feat.geometry() # get a geometry from the feature
    if geom is None :
        continue
    attr = [] #attributes
    l = geom.GetPointCount() # get the number of points of each line
    x_start = geom.GetX(0) # get the first and last points' coordinates of line
    x_end = geom.GetX(l-1)
    y_start = geom.GetY(0)
    y_end = geom.GetY(l-1)
    start = str(x_start)+','+str(y_start) # combine the coordinates to save as string
    end = str(x_end)+','+str(y_end)
    # if the node (coordinates) is new in the matrix, add it in the matrix
    if start not in list(dict_coorToNum.keys()) :
        dict_coorToNum[start] = key # and save the information in the dictionaries
        dict_numToCoor[key] = start
        key += 1 # and add the key number
    if end not in list(dict_coorToNum.keys()) :
        dict_coorToNum[end] = key
        dict_numToCoor[key] = end
        key += 1
    length = feat.GetField('LEN')
    hazard = feat.GetField('HAZARD')
    f_id = feat.GetField('NUM')
    # add the edge in the matrix
    G.add_edge(dict_coorToNum[start], dict_coorToNum[end], fid = f_id, LEN = length, HAZARD = hazard, 
               START= (y_start, x_start), END=(y_end, x_end))
    # get the coordinates of all points of line feature
    geom_list = [] 
    for i in range(geom.GetPointCount()) : # call the coordiantes and concatnate them as a string to save
        geom_list.append(str(geom.GetY(i)) + ',' + str(geom.GetX(i)))
    geoms = '|'.join(geom_list)
    # add coordinates information in the data frame
    row = [dict_coorToNum[start], dict_coorToNum[end], geoms, length, hazard]
    road_df.loc[num] = row
    if num % 500 == 0 :
        print(num)
    num += 1
    
"""
In this module, we save the results of above cell
"""
## Save the dictionaris as json files
json_dict_coorToNum = json.dumps(dict_coorToNum)
f = open(r'F:\01. Jn\01. KAIA\01. Evacuation considering road hazard\the whole network\Advenced_shortest_path\matrix\dict_coorToNum.json', 'w')
f.write(json_dict_coorToNum)
f.close()

json_dict_numToCoor = json.dumps(dict_numToCoor)
f = open(r'F:\01. Jn\01. KAIA\01. Evacuation considering road hazard\the whole network\Advenced_shortest_path\matrix\dict_numToCoor.json', 'w')
f.write(json_dict_numToCoor)
f.close()

road_df.to_json(r'F:\01. Jn\01. KAIA\01. Evacuation considering road hazard\the whole network\Advenced_shortest_path\matrix\road_df.json')

## Save the graph into a json file
js_graph = json.dumps(json_graph.node_link_data(G))
f = open(r'F:\01. Jn\01. KAIA\01. Evacuation considering road hazard\the whole network\Advenced_shortest_path\matrix\network_graph.json', 'w')
f.write(js_graph)
f.close()

"""
Notice!
If we already have dataset as jsonfiles, we just read these files
"""
# read data for analysis
dict_coorToNum = json.load(open(
    r'F:\01. Jn\01. KAIA\01. Evacuation considering road hazard\the whole network\Advenced_shortest_path\matrix\dict_coorToNum.json'))
dict_numToCoor = json.load(open(
    r'F:\01. Jn\01. KAIA\01. Evacuation considering road hazard\the whole network\Advenced_shortest_path\matrix\dict_numToCoor.json'))
js_G = json.load(open(
    r'F:\01. Jn\01. KAIA\01. Evacuation considering road hazard\the whole network\Advenced_shortest_path\matrix\network_graph.json', "r"))
G = json_graph.node_link_graph(js_G)

"""
In this cell, we convert the shapefiles into lists of start and end nodes
The data saves their coordinates, id, and population number, and capacity area
"""
## Get start node information (pop)
total_pop = 0
pop_point = []
for feat in pop_lyr :
    geom = feat.geometry()
    x = geom.GetX()
    y = geom.GetY()
    coor = str(x)+','+str(y)
    pid = int(feat.GetField('PID'))
    pop = feat.GetField('TMST_20_su')
    if pop is None :
        total_pop += float(0)
        pop_point.append([coor, pid, 0])
    else :
        total_pop += float(pop)
        pop_point.append([coor, pid, pop])    

## Get end node information (shelter)
total_cap = 0
shel_point = []
for feat in shelter_lyr :
    geom = feat.geometry()
    x = geom.GetX()
    y = geom.GetY()
    coor = str(x)+','+str(y)
    sid = int(feat.GetField('SID'))
    cap = feat.GetField('AREA')
    if cap is None :
        total_cap += float(0)
        shel_point.append([coor, sid, 0])
    else :
        total_cap += float(cap)
        shel_point.append([coor, sid, cap])

"""
This module calculates the shortest path between population point and shleter point.
The length of the dataframe is the product of the number of population and shelter.
The dataframe saves id of population and shelter, population number, shleter capacity, and costs.
"""
## Create a empty dataframe
shortest_df = pd.DataFrame(columns=['POP_ID', 'SHELTER_ID', 'POP_NODE', 'SHELTER_NODE', 
                                    'POP', 'CAP', 'LEN', 'HAZARD'])

## Start creating matrix
num = 0
for pop in pop_point :
    ## load population information
    pop_node = dict_coorToNum[pop[0]]
    pop_id = pop[1]
    pop_num = pop[2]
    for shelter in shel_point :
        ## load shelter information
        shelter_node = dict_coorToNum[shelter[0]]
        shelter_id = shelter[1]
        shelter_cap = shelter[2]
        ## calculate the shortest path
        shortest_path = nx.dijkstra_path(G, pop_node, shelter_node, weight='LEN')
        shortest_len = nx.shortest_path_length(G, pop_node, shelter_node, weight='LEN')
        shortest_hazard = 0
        for i in range(0, len(shortest_path)-1) :
            shortest_hazard += G[shortest_path[i]][shortest_path[i+1]]['HAZARD']
        row = [pop_id, shelter_id, pop_node, shelter_node, pop_num, 
               shelter_cap, shortest_len, shortest_hazard]
        shortest_df.loc[num] = row
        num += 1
        if num % 500 == 0 :
            print(num)
