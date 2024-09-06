#!/usr/bin/env python
#coding=utf-8

import json
import numpy as np
import pandas as pd
with open("citation_map.json",'r') as f:
    txt=f.read()
dt = json.loads(txt)
nodes = dt["nodes"]
links = dt["links"]
count_list = np.zeros(len(nodes)) # a list for counting link number of each paper
for link in links:
    s = link["source"]
    t = link["target"]
    count_list[s] += 1
    count_list[t] += 1
paper_index_df = pd.DataFrame({"index":np.arange(len(count_list)),"count":count_list})
node_df = pd.DataFrame(nodes)
merged_df = pd.concat([paper_index_df,node_df],axis=1)
merged_df_sorted = merged_df.sort_values(by="count",ascending=False)
merged_df_sorted.to_csv("result_exported.tsv",sep="\t")



