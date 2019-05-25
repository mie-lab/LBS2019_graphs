# -*- coding: utf-8 -*-
"""
Created on Tue May  7 16:33:39 2019

@author: martinhe
"""
from http.client import IncompleteRead
import smopy
import networkx as nx
from trackintel.preprocessing import activity_graphs as tigraphs
import numpy as np
import datetime

def nx_coordinate_layout_smopy(G, smap):
    """"transforms WGS84 coordinates to pixel coordinates of a smopy map"""
    node_center = nx.get_node_attributes(G, 'center')
    pos = {key: (smap.to_pixels(geometry.y,geometry.x)) for key,geometry in node_center.items()}

    return pos


def draw_smopy_basemap(G, figsize=(8, 6), zoom=10, ax=None):
    
    pos_wgs = tigraphs.nx_coordinate_layout(G) 
    lon =  [ coords[0] for coords in pos_wgs.values() ]
    lat =  [ coords[1] for coords in pos_wgs.values() ]
    
    lon_min = min(lon)
    lon_max = max(lon)
    lat_min = min(lat)
    lat_max = max(lat)
    attempts = 0
    while attempts < 3:
        try:
            smap = smopy.Map(lat_min, lon_min, lat_max, lon_max, tileserver="http://tile.basemaps.cartocdn.com/light_all/{z}/{x}/{y}@2x.png", z=zoom)
            break
        except IncompleteRead as e:
            
            attempts += 1
    if attempts == 3:
        print(G.graph['user_id'],e)
        smap = smopy.Map(lat_min, lon_min, lat_max, lon_max)
            
    
    #map = smopy.Map((min_y, max_y-min_y, min_x, max_x-min_x), z=5)
    ax = smap.show_mpl(figsize=figsize, ax=ax)
    
    return ax, smap


def create_activity_graphs(staypoints, places, A_dict, temporal_bin_size=None):      
    
    if temporal_bin_size is None:
        G_list = list(tigraphs.generate_activity_graphs(places, A_dict).items())
    
    else:  
        # create graphs with temporal window
        
        start_date = min(staypoints['started_at'])
        end_date = max(staypoints['finished_at'])
        date_step = temporal_bin_size
        nb_days = (end_date - start_date).days
        
        end_date_list = [start_date + datetime.timedelta(days=int(x)) 
            for x in np.arange(date_step, nb_days, date_step)]
        
        A_dict = {}
        G_list = []
        start_date_this = end_date_list
        
        # todo deal with empty graphs/dicts
        # todo deal with missing user_ids in A_dict
        
        for end_date_this in end_date_list:
            sp_this = staypoints[(staypoints['started_at'] > start_date_this) &
                                 (staypoints['finished_at'] < end_date_this)]
            places_this = places[places['place_id'].isin(sp_this['place_id'])]
            
            A_dict = (tigraphs.weights_transition_count(sp_this))
            
            G_list = G_list + list(tigraphs.generate_activity_graphs(places_this, A_dict).items())
            
            start_date_this = end_date_this
        
        # save graphs to file
        pickle.dump( G_list, open( GRAPH_OUTPUT + "_{}days.pkl".format(date_step) , "wb" ) )