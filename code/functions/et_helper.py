#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import math
import os
import numpy as np
from numpy import pi,cos,sin

import pandas as pd

import logging


#%% put PUPIL LABS data into PANDAS DF

def gaze_to_pandas(gaze):
        # Input: gaze data as dictionary
        # Output: pandas dataframe with gx, gy, confidence, smpl_time pupillabsdata, diameter and (calculated) pupil area (pa)
        import pandas as pd
        
        list_diam= []
        list_pa= []
        for idx,p in enumerate(gaze):
            
            if p:
               if 'surface' in gaze[0]['topic']:
                    # we have a surface mapped dictionairy. We have to get the real base_data
                    # the schachtelung is: surfacemapped => base_data World Mapped => base_data pupil
                    p_basedata = p['base_data']['base_data']
               else:
                    p_basedata = p['base_data']


               # take the mean over all pupil-diameters
               diam = 0
               pa = 0
               for idx_bd,bd in enumerate(p_basedata):
                   pa = convert_diam_to_pa(bd['ellipse']['axes'][0], bd['ellipse']['axes'][1])
                   diam = diam + bd['diameter']
               diam = diam/(idx_bd+1)

               list_diam.append(diam)
               list_pa.append(pa)

                 
                
        df = pd.DataFrame({'gx':[p['norm_pos'][0] for p in gaze if p],
                           'gy':[p['norm_pos'][1] for p in gaze if p],
                           'confidence': [p['confidence'] for p in gaze if p],
                           'smpl_time':[p['timestamp'] for p in gaze if p],
                           'diameter':list_diam,
                           'pa': list_pa
                           })
        return df
        
        
def convert_diam_to_pa(axes1, axes2):
    return math.pi * float(axes1) * float(axes2) * 0.25


#%% adding information to dfs

def add_msg_to_event(etevents,etmsgs,timefield = 'start_time', direction='backward'):
    # combine the event df with the msg df          
    etevents = etevents.sort_values('start_time')
    etmsgs   = etmsgs.sort_values('msg_time')
    # make a merge on the msg time and the start time of the events
    merged_etevents = pd.merge_asof(etevents,etmsgs,left_on='start_time',right_on='msg_time',direction=direction)
    
    return merged_etevents
    

                
def add_events_to_samples(etsamples, etevents):
    # Calls append_eventtype_to_sample for each event
    # Also adds blink_id
    
    for evt in etevents.type.unique():
        etsamples = append_eventtype_to_sample(etsamples,etevents,eventtype=evt)
        
        # add blink id
        if evt == 'blink':
            # counts up the blink_id
            # Pure Magic
            etsamples['blink_id'] = (1*(etsamples['type']=='blink')) * ((1*(etsamples['type']=='blink')).diff()==1).cumsum()
    
    return(etsamples)
        
        
    
def append_eventtype_to_sample(etsamples,etevents,eventtype,timemargin=None):
    # get a logger
    logger = logging.getLogger(__name__)
     
    logger.debug('Appending eventtype: %s to samples',eventtype)
    if timemargin is None:
        
        if eventtype== 'blink':
            logger.info('Taking Default value for timemargin (blink = -0.1s/0.1s)')
            timemargin = [-.1,.1]
        else:
            logger.info('Taking Default value for timemargin (fix/saccade = 0s)')
            timemargin = [0,0]
        
               
    # get index of the rows that have that eventtype
    ix_event = etevents['type']==eventtype
    
    # get list of start and end indeces in the etsamples df
    startix = np.searchsorted(etsamples.smpl_time,etevents.loc[ix_event].start_time+float(timemargin[0]))
    endix = np.searchsorted(etsamples.smpl_time,etevents.loc[ix_event].end_time+float(timemargin[1]))
    
    # make a list of ranges to have all indices in between the startix and endix
    ranges = [list(range(s,e)) for s,e in zip(startix,endix)]
    flat_ranges = [item for sublist in ranges for item in sublist]
    
    
    flat_ranges = np.intersect1d(flat_ranges,range(etsamples.shape[0]))
    # all etsamples with ix in ranges , will the eventype in the column type
    etsamples.loc[etsamples.index[flat_ranges], 'type'] = eventtype

    return etsamples


#%% last fixation (e.g. for large GRID)

def only_last_fix(merged_etevents, next_stim = ['condition','block', 'element']):
    # we group by  block and element and then take the last fixation
       
    # use only fixation events and group by block and element and then take the last one of it
    large_grid_df = merged_etevents[merged_etevents.type == 'fixation'].groupby(next_stim).last()
    large_grid_df.reset_index(level= next_stim, inplace=True)

    return large_grid_df


#%% everything related to VISUAL DEGREES

def px2deg(px, orientation, pxPerDeg=0.276,distance=600):
    # VD
    # "gx_px - gx_px-midpoint"
    # subtract center of our BENQ

    if orientation == 'horizontal':
        center_x = 1920 / 2
        px       = px - center_x
    
    if orientation == 'vertical':
        center_y = 1080 / 2
        px       = px - center_y
           
    deg = 2*np.arctan2(px*pxPerDeg,distance)*180/np.pi

    return deg


def sph2cart(theta_sph,phi_sph,rho_sph=1):
    xyz_sph = np.asarray([rho_sph * sin(theta_sph) * cos(phi_sph), 
           rho_sph * sin(theta_sph) * sin(phi_sph), 
           rho_sph * cos(theta_sph)])

    return xyz_sph




#%% LOAD & SAVE & FIND file
    
def load_file(et,subject,datapath):
    
    # filepath for preprocessed folder
    preprocessed_path = os.path.join(datapath, subject, 'preprocessed')
    
    try:
        filename_samples = str(et)  + '_cleaned_samples.csv'
        filename_msgs    = str(et)  + '_msgs.csv'
        filename_events  = str(et)  + '_events.csv'
        
        etsamples = pd.read_csv(os.path.join(preprocessed_path,filename_samples))
        etmsgs    = pd.read_csv(os.path.join(preprocessed_path,filename_msgs))
        etevents  = pd.read_csv(os.path.join(preprocessed_path,filename_events))

    except FileNotFoundError as e:
        print(e)
        raise('Error: Could not read file')

    return etsamples,etmsgs,etevents



def save_file(data,et,subject,datapath):
    
    # filepath for preprocessed folder
    preprocessed_path = os.path.join(datapath, subject, 'preprocessed')
    
    # create new folder if there is none
    if not os.path.exists(preprocessed_path):
        os.makedirs(preprocessed_path)
    
    # dump data in csv
    filename_samples = str(et) + '_samples.csv'
    filename_cleaned_samples = str(et) + '_cleaned_samples.csv'
    filename_msgs = str(et)  + '_msgs.csv'
    filename_events = str(et)  + '_events.csv'
    
    # make separate csv file for every df 
    data[0].to_csv(os.path.join(preprocessed_path, filename_samples), index=False)
    data[1].to_csv(os.path.join(preprocessed_path, filename_cleaned_samples), index=False)
    data[2].to_csv(os.path.join(preprocessed_path, filename_msgs), index=False)
    data[3].to_csv(os.path.join(preprocessed_path, filename_events), index=False)
    



def findFile(path,ftype):
    # finds file for el edf
    out = [edf for edf in os.listdir(path) if edf.endswith(ftype)]
    return(out)
    
    
    
def get_subjectnames(datapath='/net/store/nbp/projects/etcomp/'):
    return os.listdir(datapath)
   