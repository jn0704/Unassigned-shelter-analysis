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
f = open('', 'w')
f.write(json_dict_coorToNum)
f.close()

json_dict_numToCoor = json.dumps(dict_numToCoor)
f = open('', 'w')
f.write(json_dict_numToCoor)
f.close()

road_df.to_json('location')

## Save the graph into a json file
js_graph = json.dumps(json_graph.node_link_data(G))
f = open('', 'w')
f.write(js_graph)
f.close()

"""
Notice!
If we already have dataset as jsonfiles, we just read these files
"""
# read data for analysis
dict_coorToNum = json.load(open(
    'location'))
dict_numToCoor = json.load(open(
    'location'))
js_G = json.load(open(
    'location', "r"))
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
The first module calculates the shortest path between population point and shleter point.
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
## save the results
shortest_df.to_json('')
shortest_df.to_csv('')

"""
Next, we calculate distances between shelters.
"""

shelter_df = pd.DataFrame(columns=['SHELTER_ID_1', 'SHELTER_ID_2', 'SHELTER_NODE1', 'SHELTER_NODE2', 
                                   'LEN', 'HAZARD'])

## Start creating matrix
num = 0
for shelter1 in shel_point :
    ## load population information
    snode1 = dict_coorToNum[shelter1[0]]
    sid1 = shelter1[1]
    for shelter2 in shel_point :
        ## load shelter information
        snode2 = dict_coorToNum[shelter2[0]]
        sid2 = shelter2[1]
        ## calculate the shortest path
        shortest_path = nx.dijkstra_path(G, snode1, snode2, weight='LEN')
        shortest_len = nx.shortest_path_length(G, snode1, snode2,  weight='LEN')
        shortest_hazard = 0
        for i in range(0, len(shortest_path)-1) :
            shortest_hazard += G[shortest_path[i]][shortest_path[i+1]]['HAZARD']
        row = [sid1, sid2, snode1, snode2, shortest_len, shortest_hazard]
        shelter_df.loc[num] = row
        num += 1
        if num % 10 == 0 :
            print(num)
        
## save the results
shelter_df.to_json('.json')
shelter_df.to_csv('csv')

"""
Notice!
If we have already the results of the first and second module, we just read the files
"""
shortest_df = pd.read_json('.json')
shelter_df = pd.read_json('.json')

"""
The second module simulates for pedestrians to find shelters.
In the situation, pedestrians never know the capacity of shelter and how many people will enter the shelter.
When they arrive the shelter and the shelter is full, they go to other shelter that has the shortest path from the shelter.
The information people know is the distance between they and shelters as well as each shelter.
"""
"""
We will create a matrix and assign pedestirnas using shortest path method.
"""
## Assings the matrix considering only the shortest path
## Convert dataframe for analysis
shortest_df['ASSIGN'] = 0
# pop_df = shortest_df.drop_duplicates('POP_ID', keep='first')
# shel_df = shortest_df.drop_duplicates('SHELTER_ID', keep='first')
# pop_df.reset_index(drop=True, inplace=True)
# shel_df.reset_index(drop=True, inplace=True)
shortest_df['POP_COPY'] = shortest_df['POP']
shortest_df['CAP_COPY'] = shortest_df['CAP']
shortest_df['LEN_COPY'] = shortest_df['LEN']
shortest_df['HAZARD_COPY'] = shortest_df['HAZARD']

## get column index
pop_id_index = list(shortest_df.columns).index('POP_ID')
shel_id_index = list(shortest_df.columns).index('SHELTER_ID')
pop_node_index = list(shortest_df.columns).index('POP_NODE')
shel_node_index = list(shortest_df.columns).index('SHELTER_NODE')
pop_index = list(shortest_df.columns).index('POP')
cap_index = list(shortest_df.columns).index('CAP')
assign_index = list(shortest_df.columns).index('ASSIGN')
pop_copy_index = list(shortest_df.columns).index('POP_COPY')
cap_copy_index = list(shortest_df.columns).index('CAP_COPY')
len_copy_index = list(shortest_df.columns).index('LEN_COPY')
hazard_copy_index = list(shortest_df.columns).index('HAZARD_COPY')

### Start assigning populations to shelters
while True :
    print('--------------------')
    ## find the shortest path
    min_cost = shortest_df[(shortest_df['POP_COPY']>0) & (shortest_df['CAP_COPY']>0)]['LEN_COPY'].min() # select the population that has the shortest path
    print('cost: ' + str(min_cost))
    index = shortest_df.loc[(shortest_df['POP_COPY']>0) & (shortest_df['CAP_COPY']>0) &
                            (shortest_df['LEN_COPY'] == min_cost)].index.values[0] # get row index
    print('index: ' + str(index))
    
    ## get values
    pop = float(shortest_df.iloc[index]['POP_COPY'])
    cap = float(shortest_df.iloc[index]['CAP_COPY'])
    pop_id = shortest_df.iloc[index]['POP_ID']
    print('pop id: ' + str(pop_id))
    shel_id = shortest_df.iloc[index]['SHELTER_ID']
    print('shel_id: ' + str(shel_id))
    pop_node = int(shortest_df.iloc[index]['POP_NODE'])
    shel_node = int(shortest_df.iloc[index]['SHELTER_NODE'])
    length = shortest_df.iloc[index]['LEN_COPY']
    hazard = shortest_df.iloc[index]['HAZARD_COPY']
    shortest_path = nx.dijkstra_path(G, pop_node, shel_node, weight='LEN')
    
    ## assigning
    if cap >= pop :
        shortest_df.iloc[shortest_df[shortest_df['POP_ID']==pop_id].index.values, pop_copy_index] = 0
        shortest_df.iloc[shortest_df[shortest_df['SHELTER_ID']==shel_id].index.values, cap_copy_index] = cap - pop
        shortest_df.iloc[index, assign_index] = pop
        shortest_df.iloc[index, add_shel_index] = pop
            
        total_pop = total_pop - pop
        total_cap = total_cap - pop
    else :
        shortest_df.iloc[index, assign_index] = cap
        shortest_df.iloc[index, pop_copy_index] = 0
        ids = shortest_df[shortest_df['POP_ID'] == pop_id].index.values.tolist()
        for i in ids :
            if shortest_df.iloc[i, pop_copy_index] != 0 :
                shortest_df.iloc[i, pop_copy_index] = pop - cap            
                shortest_df.iloc[i, len_copy_index] = shortest_df.iloc[i, len_copy_index] + length
                shortest_df.iloc[i, hazard_copy_index] = shortest_df.iloc[i, hazard_copy_index] + hazard
            else :
                continue
        shortest_df.iloc[shortest_df[shortest_df['SHELTER_ID']==shel_id].index.values, cap_copy_index] = 0

        total_pop = total_pop - cap
        total_cap = total_cap - cap
    print('total pop: ' + str(total_pop))
    print('total cap: ' + str(total_cap))
    if shortest_df['POP_COPY'].sum() <= 0 :
        print('assigning is finish!')
        break
    if shortest_df['CAP_COPY'].sum() <= 0 :
        print('capacity issue!')
        break
 
## save the results
shortest_df.to_json('.json')
shortest_df.to_csv('.csv')

cd = shortest_df.loc[asd["ASSIGN"] > 0]
cd.to_json('.json')
cd.to_csv('.csv')

"""
In this module, we create line features as evacuation routes from the dataframe.
"""
"""
First, we load the dataframe.
"""
assigned_df = pd.read_json('location')
## get column index
pop_id_index = list(assigned_df.columns).index('POP_ID')
shel_id_index = list(assigned_df.columns).index('SHELTER_ID')
pop_node_index = list(assigned_df.columns).index('POP_NODE')
shel_node_index = list(assigned_df.columns).index('SHELTER_NODE')
assign_index = list(assigned_df.columns).index('ASSIGN')
pop_copy_index = list(assigned_df.columns).index('POP_COPY')
cap_copy_index = list(assigned_df.columns).index('CAP_COPY')
len_copy_index = list(assigned_df.columns).index('LEN_COPY')
hazard_copy_index = list(assigned_df.columns).index('HAZARD_COPY')
"""
In this module we create an empty shapefile to write line features
"""
## Create shapefile
driver = ogr.GetDriverByName('ESRI Shapefile')
data_source = driver.CreateDataSource('.shp')
create_lyr = data_source.CreateLayer('shortest_path', road_lyr.GetSpatialRef(), ogr.wkbMultiLineString)
data_source.Destroy()
## Create shortest path as linestring
## read shapefile
path_ds = ogr.Open('.shp', 1)
path_lyr = path_ds.GetLayer('shortest_path')
path_defn = path_lyr.GetLayerDefn()
print(path_lyr.GetGeomType() == ogr.wkbLineString)

## set field
field_name = ['POP_ID', 'SHEL_ID', 'POP_NODE', 'SHEL_NODE', 'POP', 'CAP', 'LEN', 'HAZARD']
path_lyr.CreateField(ogr.FieldDefn('POP_ID', ogr.OFTInteger))
path_lyr.CreateField(ogr.FieldDefn('SHEL_ID', ogr.OFTInteger))
path_lyr.CreateField(ogr.FieldDefn('POP_NODE', ogr.OFTInteger))
path_lyr.CreateField(ogr.FieldDefn('SHEL_NODE', ogr.OFTInteger))
path_lyr.CreateField(ogr.FieldDefn('POP', ogr.OFTReal))
path_lyr.CreateField(ogr.FieldDefn('CAP', ogr.OFTReal))
path_lyr.CreateField(ogr.FieldDefn('LEN', ogr.OFTReal))
path_lyr.CreateField(ogr.FieldDefn('HAZARD', ogr.OFTReal))

## Start assinging
ids = assigned_df['POP_ID'].values.tolist()
ids = list(set(ids))

for i in ids :
    df = assigned_df[assigned_df['POP_ID']==i]
    if len(df) == 1 :
        pop_id = df.iloc[0, pop_id_index]
        shel_id = df.iloc[0, shel_id_index]
        pop_node = df.iloc[0, pop_node_index]
        shel_node = df.iloc[0, shel_node_index]
        pop = df.iloc[0, assign_index]
        cap = df.iloc[0, cap_copy_index]
        shortest_len = df.iloc[0, len_copy_index]
        shortest_hazard = df.iloc[0, hazard_copy_index]
        shortest_path = nx.dijkstra_path(G, pop_node, shel_node, weight='LEN')
        geom = ogr.Geometry(ogr.wkbLineString)
        for i in range(0,len(shortest_path)):
            x = float(dict_numToCoor[str(shortest_path[i])].split(',')[0])
            y = float(dict_numToCoor[str(shortest_path[i])].split(',')[1])
            geom.AddPoint(x, y)
        feat = ogr.Feature(path_defn)
        feat.SetField('POP_ID', int(pop_id))
        feat.SetField('SHEL_ID', int(shel_id))
        feat.SetField('POP_NODE', int(pop_node))
        feat.SetField('SHEL_NODE', int(shel_node))
        feat.SetField('POP', pop)
        feat.SetField('CAP',cap)
        feat.SetField('LEN', shortest_len)
        feat.SetField('HAZARD', shortest_hazard)
        feat.SetGeometry(geom)
        path_lyr.CreateFeature(feat)
    elif len(df) == 2 :
        df = df.sort_values(by='LEN_COPY', ascending=True)
        pop_id = df.iloc[1, pop_id_index]
        shel_id = df.iloc[1, shel_id_index]
        pop_node = df.iloc[1, pop_node_index]
        shel_node = df.iloc[1, shel_node_index]
        pop = df.iloc[1, assign_index]
        cap = df.iloc[1, cap_copy_index]
        shortest_len = df.iloc[1, len_copy_index]
        shortest_hazard = df.iloc[1, hazard_copy_index]
        path = []
        shortest_path1 = nx.dijkstra_path(G, df.iloc[0, pop_node_index], df.iloc[0, shel_node_index], weight='LEN')[:-1]
        shortest_path2 = nx.dijkstra_path(G, df.iloc[0, shel_node_index], df.iloc[1, shel_node_index], weight='LEN')
        shortest_path = shortest_path1 + shortest_path2
        geom = ogr.Geometry(ogr.wkbLineString)
        for i in range(0,len(shortest_path)):
            x = float(dict_numToCoor[str(shortest_path[i])].split(',')[0])
            y = float(dict_numToCoor[str(shortest_path[i])].split(',')[1])
            geom.AddPoint(x, y)
        feat = ogr.Feature(path_defn)
        feat.SetField('POP_ID', int(pop_id))
        feat.SetField('SHEL_ID', int(shel_id))
        feat.SetField('POP_NODE', int(pop_node))
        feat.SetField('SHEL_NODE', int(shel_node))
        feat.SetField('POP', pop)
        feat.SetField('CAP',cap)
        feat.SetField('LEN', shortest_len)
        feat.SetField('HAZARD', shortest_hazard)
        feat.SetGeometry(geom)
        path_lyr.CreateFeature(feat)
    else :
        df = df.sort_values(by='LEN_COPY', ascending=True)
        shortest_path = []
        shortest_path = shortest_path + nx.dijkstra_path(G, df.iloc[0, pop_node_index], df.iloc[0, shel_node_index], weight='LEN')[:-1]
        for index in range(1, len(df)) :
            shortest_path = shortest_path + nx.dijkstra_path(G, df.iloc[index, shel_node_index], df.iloc[index-1, shel_node_index], weight='LEN')[:-1]
        shortest_path = shortest_path + nx.dijkstra_path(G, df.iloc[len(df)-1, pop_node_index], df.iloc[len(df)-1, shel_node_index], weight='LEN')
        geom = ogr.Geometry(ogr.wkbLineString)
        for i in range(0,len(shortest_path)):
            x = float(dict_numToCoor[str(shortest_path[i])].split(',')[0])
            y = float(dict_numToCoor[str(shortest_path[i])].split(',')[1])
            geom.AddPoint(x, y)
        feat = ogr.Feature(path_defn)
        feat.SetField('POP_ID', int(pop_id))
        feat.SetField('SHEL_ID', int(shel_id))
        feat.SetField('POP_NODE', int(pop_node))
        feat.SetField('SHEL_NODE', int(shel_node))
        feat.SetField('POP', pop)
        feat.SetField('CAP',cap)
        feat.SetField('LEN', shortest_len)
        feat.SetField('HAZARD', shortest_hazard)
        feat.SetGeometry(geom)
        path_lyr.CreateFeature(feat)

"""
In thos analysis, we calculate the shortest path between population points and shelter.
We assign the population fo the shelter without considering shelter capacity.
In addition, we create line features to visualize the results as a shapefile.
"""
"""
The first module calculates the shortest path between population point and shleter point.
The length of the dataframe is the product of the number of population and shelter.
The dataframe saves id of population and shelter, population number, shleter capacity, and costs.
"""

## Create a empty dataframe
shortest_df = pd.DataFrame(columns=['POP_ID', 'SHELTER_ID', 'POP_NODE', 'SHELTER_NODE', 
                                    'POP', 'CAP', 'LEN', 'HAZARD'])

## Create shapefile
driver = ogr.GetDriverByName('ESRI Shapefile')
data_source = driver.CreateDataSource('.shp')
create_lyr = data_source.CreateLayer('shortest_path', road_lyr.GetSpatialRef(), ogr.wkbMultiLineString)
data_source.Destroy()

## Create shortest path as linestring
## read shapefile
path_ds = ogr.Open('.shp', 1)
path_lyr = path_ds.GetLayer('shortest_path')
path_defn = path_lyr.GetLayerDefn()
print(path_lyr.GetGeomType() == ogr.wkbLineString)

## set field
field_name = ['POP_ID', 'SHEL_ID', 'POP_NODE', 'SHEL_NODE', 'POP', 'CAP', 'LEN', 'HAZARD']
path_lyr.CreateField(ogr.FieldDefn('POP_ID', ogr.OFTInteger))
path_lyr.CreateField(ogr.FieldDefn('SHEL_ID', ogr.OFTInteger))
path_lyr.CreateField(ogr.FieldDefn('POP_NODE', ogr.OFTInteger))
path_lyr.CreateField(ogr.FieldDefn('SHEL_NODE', ogr.OFTInteger))
path_lyr.CreateField(ogr.FieldDefn('POP', ogr.OFTReal))
path_lyr.CreateField(ogr.FieldDefn('CAP', ogr.OFTReal))
path_lyr.CreateField(ogr.FieldDefn('LEN', ogr.OFTReal))
path_lyr.CreateField(ogr.FieldDefn('HAZARD', ogr.OFTReal))

## Start creating matrix and line features
num = 0
error = []
for pop in pop_point :
    ## load population information
    pop_node = dict_coorToNum[pop[0]]
    pop_id = pop[1]
    pop_num = pop[2]
    shelters = {} # set an empty dictionary to assign the population
    for shelter in shel_point :
        ## load shelter information
        shelter_node = dict_coorToNum[shelter[0]]
        shelter_id = shelter[1]
        shelter_cap = shelter[2]
        ## calculate the shortest path
        try :
            shortest_len = nx.shortest_path_length(G, pop_node, shelter_node, weight='LEN')
            ## save the results in the dictionaty
            shelters[shortest_len] = [shelter_id, shelter_node, shelter_cap]
        except :
            ## if the algorithm cannot find the shortest path, it saves the results and skip the process
            print('error: ' + str(pop_id) + '/' + str(shelter_id))
            error.append([pop_id, shelter_id])
    if len(shelters) == 0 :
        continue
    else :
        ## find the shelter that has the shortest distance from the population
        lists = list(shelters.keys())
        short_shelter = shelters[min(lists)]
        ## re-calculate the chortest path
        shortest_path = nx.dijkstra_path(G, pop_node, short_shelter[1], weight='LEN')
        shortest_len = nx.shortest_path_length(G, pop_node, short_shelter[1], weight='LEN')
        shortest_hazard = 0
        for i in range(0, len(shortest_path)-1) :
            shortest_hazard += G[shortest_path[i]][shortest_path[i+1]]['HAZARD']
        ## save the results in the dataframe
        row = [pop_id, short_shelter[0], pop_node, short_shelter[1], pop_num, 
               short_shelter[2], shortest_len, shortest_hazard]
        shortest_df.loc[num] = row
        ## create line features of the shortest path
        geom = ogr.Geometry(ogr.wkbLineString)
        for i in range(0,len(shortest_path)):
            x = float(dict_numToCoor[str(shortest_path[i])].split(',')[0])
            y = float(dict_numToCoor[str(shortest_path[i])].split(',')[1])
            geom.AddPoint(x, y)
        feat = ogr.Feature(path_defn)
        feat.SetField('POP_ID', int(pop_id))
        feat.SetField('SHEL_ID', int(short_shelter[0]))
        feat.SetField('POP_NODE', int(pop_node))
        feat.SetField('SHEL_NODE', int(short_shelter[1]))
        feat.SetField('POP', pop_num)
        feat.SetField('CAP', short_shelter[2])
        feat.SetField('LEN', shortest_len)
        feat.SetField('HAZARD', shortest_hazard)
        feat.SetGeometry(geom)
        path_lyr.CreateFeature(feat)
        num += 1
        if num % 500 == 0 :
            print(num)
    
## close path
path_ds.Destroy()
## save the results
shortest_df.to_json('.json')
shortest_df.to_csv('.json')

print('finish')
