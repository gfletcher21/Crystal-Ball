#!/usr/bin/env python
# coding: utf-8

# # Optimization - January 2018
# 
# ## Data
# 
# ### Demand

# In[1]:


import pandas as pd
import numpy as np
import csv
demand = pd.read_csv('JanWeeklyDemand.csv')
demand2 = pd.read_csv('JanWeeklyDemand.csv')
demand2['Inventory Date'] = pd.to_datetime(demand2['Inventory Date']).astype('datetime64[D]')
demand = demand.fillna(0)
demand['Inventory Date'] = pd.to_datetime(demand['Inventory Date']).astype('datetime64[D]')
#
demand['ItemCode'] = demand['ItemCode'].str.lstrip('0')
demand2['ItemCode'] = demand2['ItemCode'].str.lstrip('0')
#
demand = demand.set_index([demand['Inventory Date'],demand['ItemCode'],demand['Branch']])
demand = demand.drop(['Inventory Date','ItemCode','Branch'], axis = 1)
demand = demand.T
columnlist = []
for c in demand.columns:
    x, y, z = c
    x = np.datetime64(x)
    x = x.astype('datetime64[D]')
    if y[0:2] == 'SR':
        y = y[2:]
        c2 = (x,y,z)
    else:
        c2 = (x,y,z)
    columnlist.append(c2)
demand.columns = columnlist
demand = demand.groupby(by = demand.columns,axis=1).sum()
# Example selection: 
# demand[weeks[1],'271','Toronto F&S']['Weekly Demand']


# In[2]:


demand


# ### Branch-to-Branch Cost

# In[3]:


# costs = pd.read_csv('RandomCosts.csv')
# costs['Cost'].apply(lambda x: float(x))
# #
# costs['Item'] = costs['Item'].str.lstrip('0')
# #
# costs = costs.set_index(['From','To','Item'])
# costs = costs.T.to_dict()
# # Example of selection: 
# #costs['Atlanta F&S','Atlanta F&S','200600']['Cost']


# In[4]:


regression={'Mileage':0.3328,'Weight':0.09408,'OLinden':- 99.8,'OBaltimore F&S':179.3,'OAtlanta F&S':258.7,'OTampa F&S':111.0,
           'O43302':325.1,'OGreat Lakes CC':335.3,'OHouston F&S':245.2,'OFontana':- 55.1,'OSacramento Main':- 218.4,'OSeattle F&S':38.9,'OToronto F&S':532.6,
           'DLinden':-17.8,'DBaltimore F&S':59.1,'DAtlanta F&S':-138.2,'DTampa F&S':107.7,
           'D43302':190.2,'DGreat Lakes CC':- 5.6,'DHouston F&S':- 348.5,'DFontana':431.5,'DSacramento Main':558.7,'DSeattle F&S':635.2,'DToronto F&S':407.6,
           'MM':- 0.000060,'WW':- 0.000002,'MW':0.000041}

import csv
reader = csv.reader(open('weights.csv', 'r',encoding = 'utf8'))
weights = {}
for row in reader:
    x, item,y, weight = row
    weights[item] = weight

miles = {}

with open("distance_df.csv", "r") as infile:
    reader = csv.reader(infile)
    headers = next(reader)[1:]
    for row in reader:
        miles[row[0]] = {key: float(value) for key, value in zip(headers, row[1:])}
def cost(i,j,k):
    jx=j
    kx=k
    if i not in weights.keys():
        if '0'+i in weights.keys():
            i='0'+i
        
        elif 'SR'+i in weights.keys():
            i='SR'+i
            
        else:
            print(i)
            weights[i]=1
    if jx in ['Edmonton F&S','Vancouver F&S','Montreal F&S']:
        jx='Toronto F&S'
    if kx in ['Edmonton F&S','Vancouver F&S','Montreal F&S']:
        kx='Toronto F&S'
    c=(float(weights[i])/40000)*(-286.0 + 0.3328*miles[k][j]+regression['O'+jx]+regression['D'+kx]+0.09408*float(40000)- 0.000060*(miles[k][j])**2 - 0.000002*float(40000)**2+0.000041*float(40000)*miles[k][j])
    return c


# ### Total Units in System

# In[5]:


totaldata = pd.read_csv('2018InventoryTotals.csv')
#
nosr = []
totaldata['ItemCode'] = totaldata['ItemCode'].str.lstrip('0')
for c in totaldata['ItemCode']:
    if c[0:2] == 'SR':
        c2 = c[2:]
    else:
        c2 = c
    nosr.append(c2)
totaldata['ItemCode'] = nosr    
totaldata = totaldata.groupby(by = 'ItemCode').sum()
# Example selection: totaldata['TotalUnits']['4004']


# ### Dealing with Missing Data

# In[6]:


w = pd.read_csv('DiscrepanciesNoSR2.csv')
w.set_index('Item Code')
bad = w['Item Code']
bad = bad.tolist()
bad


# ## Gurobi Model

# In[7]:


from gurobipy import GRB, Model, quicksum
m = Model('AlumaJan')


# In[8]:


plist = demand2['ItemCode'].unique()
partlist=[]
for p in plist:
    if p[0:2] == 'SR':
        p2 = p[2:]
    else:
        p2 = p
    partlist.append(p2.lstrip('0'))
partlist = pd.Series(partlist)
partlist = partlist.unique()
partlist = list(filter(lambda a: a not in bad,partlist))


# In[9]:


branchlist = demand2['Branch'].unique()
branchlist = pd.Series(branchlist)
branchlist = branchlist.sort_values()
weeks = demand2['Inventory Date'].unique()
weeks = weeks.astype('datetime64[D]')


# In[10]:


indexlist = []
for part in partlist:
    for frombranch in branchlist:
        for tobranch in branchlist:
            for week in weeks:
                indexlist.append((part,frombranch,tobranch,week))
indexlist2 = []
for part in partlist:
    for branch in branchlist:
        for week in weeks:
            indexlist2.append((part,branch,week))


# In[11]:


x = m.addVars(indexlist, name ='x')
y = m.addVars(indexlist2, name = "y")


# ### Constraining y values when t = 1
# ***

# In[12]:


y1 = pd.read_csv('2018 - January 7 Inventory Totals.csv')
y1['InventoryDate'] = weeks[0]
nosr2 = []
for g in y1['ItemCode']:
    g = str(g)
    if g[0:2] == 'SR':
        g2 = g[2:]
    else:
        g2 = g
    nosr2.append(g2)
y1['ItemCode'] = nosr2 
y1 = y1[y1.Branch != 'USD Region Offices']
y1 = y1.groupby(by = ['ItemCode','Branch','InventoryDate']).sum()
# Example Selection: y1['InventoryQuantity']['11','Atlanta F&S', weeks[0]]
for idx,r in y1.iterrows():
    if idx in indexlist2:
        try:
            m.addConstr(y[idx[0],idx[1],weeks[0]] == np.maximum(r, demand[weeks[0],idx[0],idx[1]]['Weekly Demand'])) #y1['InventoryQuantity'][idx[0],idx[1],weeks[0]])
        except KeyError:
            m.addConstr(y[idx[0],idx[1],weeks[0]] == r)      
    else:
        pass
                               


# ***

# In[13]:


for i in partlist:
    for j in branchlist:
        for t in weeks:
            m.addConstrs(x[i,j,k,t] == 0 for k in branchlist if k == j)
            try:
                m.addConstr(y[i,j,t] >= demand[t,i,j]['Weekly Demand'])
            except KeyError:
                pass
            m.addConstr(y[i,j,t] >= 0)
        for t in weeks[0:len(weeks)-1]:
            try:
                m.addConstr(y[i,j,t+np.timedelta64(7,'D')] == y[i,j,t] + 
                            quicksum(x[i,k,j,t] for k in branchlist) - 
                            quicksum(x[i,j,k,t+np.timedelta64(7,'D')] for k in branchlist))
            except KeyError:
                pass
           
for i in partlist:
        for t in weeks:
            try:
                m.addConstr(quicksum(y[i,g,t] for g in branchlist) + quicksum(x[i,q,w,t] for q in branchlist for w in branchlist) <= totaldata['TotalUnits'][i])
            except KeyError:
                pass


# In[14]:


m.setObjective(quicksum(cost(i,j,k)*
                        x[i,j,k,t]
                        for i in partlist
                        for j in branchlist
                        for k in branchlist
                        for t in weeks),
               GRB.MINIMIZE)


# In[15]:


m.optimize()
#m.computeIIS()
#m.write("model.ilp")


# In[16]:


status_code = {1:'LOADED', 2:'OPTIMAL', 3:'INFEASIBLE', 4:'INF_OR_UNBD', 5:'UNBOUNDED'}
status = m.status
               
print('The optimization status is {}'.format(status_code[status]))
if status == 2:  
     print('Optimal solution:')
     print('Optimal objective value:\n{}'.format(m.objVal))
     for v in m.getVars():
            if v.x != 0:
                print('%s = %g' % (v.varName, v.x))
     

