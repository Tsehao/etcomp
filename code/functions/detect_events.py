#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue May  8 16:42:55 2018

@author: tknapen https://github.com/tknapen/hedfpy/blob/master/hedfpy/EyeSignalOperator.py
"""

import numpy as np
from scipy.interpolate import PchipInterpolator
import pandas as pd
import numpy.linalg as LA
import time

import os

#%% WRAPPER TO DETECT SACCADES   (IN THE CASE OF PL INTERPOLATE SAMPLES FIRST)

def detect_saccades_engbert_mergenthaler(etsamples,fs = None, subject=None, recalculate=True, save=True, date='2018-05-11'):
    # Input:      etsamples
    #             fs:   sampling frequency
    # Output:     saccades (df) with expanded / raw
    #             amplitude, duration, start_time, end_time, peak_velocity
    
    # if you specify a sampling frequency, the samples get interpolated
    # to have regular sampled data in order to apply the saccade detection algorithm
    etsamples = etsamples.copy()
    print('removing blink-samples for saccade detection')
    etsamples.loc[etsamples['blink'],'gx'] = np.nan
    etsamples.loc[etsamples['blink'],'gy'] = np.nan

    
    print('TODO: removing bad-samples for saccade detection')
    
    if fs:
        interpgaze = interpolate_gaze(etsamples, subject=subject, fs=fs, recalculate=recalculate, save=save, date=date)
    else:
         # Eyelink is already interpolated
         interpgaze = etsamples
         fs = 500
         
    # apply the saccade detection algorithm     
    saccades = apply_engbert_mergenthaler(xy_data = interpgaze[['gx','gy']],vel_data = None,sample_rate=fs)
    #sacsave = saccades.copy()
    #saccades = sacsave
    
    # convert samples of data back to sample time
    for fn in ['raw_start_time','raw_end_time']:
        saccades[fn]=np.array(interpgaze.smpl_time.iloc[np.array(saccades[fn])])
        
    # TODO  what does it mean to use brackets here?
    return(saccades)


#%% INTERPOLATE

def interpolate_gaze(etsamples, fs=None, subject=None, recalculate=True, save=False, date=time.strftime, datapath='/net/store/nbp/projects/etcomp/pilot'): 
    # TODO implement recalculate / save
    # Input:         etsamples
    # Output:        gazeInt (df)

    # filepath for preprocessed folder
    preprocessed_path = os.path.join(datapath, subject, 'preprocessed')
    

    if recalculate:
    
        print('Start.... Interpolating Samples')
            
        # find the time range
        fromT = etsamples.smpl_time.iloc[0]    # find the first sample
        toT   = etsamples.smpl_time.iloc[-1]   # find the last sample
        # we find the new index
        timeIX = np.linspace(np.floor(fromT),np.ceil(toT),np.ceil(toT-fromT)*fs+1)
        
        def interp(x,y):
            f = PchipInterpolator(x,y)    
            return(f(timeIX))
        
        
        #GazeInt for GazeInterpolated
        gazeInt = pd.DataFrame()
        gazeInt['smpl_time']  = timeIX
        gazeInt['gx']  = interp(etsamples.smpl_time,etsamples.gx)
        gazeInt['gy']  = interp(etsamples.smpl_time,etsamples.gy)
        
        print('Done.... Interpolating Samples')
        
        # save interpolated samples into csv files
        if save:
            print('Saving.... Interpolated Samples')
            # create new folder if there is none
            if not os.path.exists(preprocessed_path):
                os.makedirs(preprocessed_path)
    
            # dump interpolated_samples df in csv
            if 'confidence' in etsamples:
                filename_interp = str(time.strftime("%Y-%m-%d")) + '_interpolated_plsamples.csv'
            else:
                filename_interp = str(time.strftime("%Y-%m-%d")) + '_interpolated_elsamples.csv'
            
            gazeInt.to_csv(os.path.join(preprocessed_path, filename_interp), index=False)
        
        return gazeInt
        
    # load preprocessed data from csv file
    # (from folder preprocessed)
    else:
        try:
            if 'confidence' in etsamples:
                filename_interp = str(date) + '_interpolated_plsamples.csv'
            else:
                filename_interp = str(date) + '_interpolated_elsamples.csv'
            
            gazeInt = pd.read_csv(os.path.join(preprocessed_path,filename_interp))
        except FileNotFoundError as e:
            print(e)
            raise('Error: Could not read file')
        
        return gazeInt


#%%  SACCADE DETECTION ALGORITHM


def apply_engbert_mergenthaler(xy_data = None, vel_data = None, l = 5, sample_rate=None, minimum_saccade_duration = 0.0075):
    """Uses the engbert & mergenthaler algorithm (PNAS 2006) to detect saccades.
    
    This function expects a sequence (N x 2) of xy gaze position or velocity data. 
    
    Arguments:
        xy_data (numpy.ndarray, optional): a sequence (N x 2) of xy gaze (float/integer) positions. Defaults to None
        vel_data (numpy.ndarray, optional): a sequence (N x 2) of velocity data (float/integer). Defaults to None.
        l (float, optional):determines the threshold. Defaults to 5 median-based standard deviations from the median
        sample_rate (float, optional) - the rate at which eye movements were measured per second). Defaults to 1000.0
        minimum_saccade_duration (float, optional) - the minimum duration for something to be considered a saccade). Defaults to 0.0075
    
    Returns:
        list of dictionaries, which each correspond to a saccade.
        
        The dictionary contains the following items:
            
    Raises:
        ValueError: If neither xy_data and vel_data were passed to the function.
    
    """
    #TODO: expanded means: taking more sampls as looking at accelartion values as well
    
    print('Start.... Detecting Saccades')
    
    # If xy_data and vel_data are both None, function can't continue
    if xy_data is None and vel_data is None:
        raise ValueError("Supply either xy_data or vel_data")    
        
    #If xy_data is given, process it
    if not xy_data is None:
        xy_data = np.array(xy_data)

    # Calculate velocity data if it has not been given to function
    if vel_data is None:
        # # Check for shape of xy_data. If x and y are ordered in columns, transpose array.
        # # Should be 2 x N array to use np.diff namely (not Nx2)
        # rows, cols = xy_data.shape
        # if rows == 2:
        #     vel_data = np.diff(xy_data)
        # if cols == 2:
        #     vel_data = np.diff(xy_data.T)
        vel_data = np.zeros(xy_data.shape)
        vel_data[1:] = np.diff(xy_data, axis = 0)
    else:
        vel_data = np.array(vel_data)
        
    inspect_vel = pd.DataFrame(vel_data)
    inspect_vel.describe()

    # median-based standard deviation, for x and y separately
    med = np.nanmedian(vel_data, axis = 0)
     
    scaled_vel_data = vel_data / np.nanmean(np.array(np.sqrt((vel_data - med)**2)), axis = 0) # scale by the standard deviation
    # normalize and to acceleration and its sign
    if (float(np.__version__.split('.')[1]) == 1.0) and (float(np.__version__.split('.')[1]) > 6):
        normed_scaled_vel_data = LA.norm(scaled_vel_data, axis = 1)
        normed_vel_data = LA.norm(vel_data, axis = 1)
    else:
        normed_scaled_vel_data = np.array([LA.norm(svd) for svd in np.array(scaled_vel_data)])
        normed_vel_data = np.array([LA.norm(vd) for vd in np.array(vel_data)])
        
    normed_acc_data = np.r_[0,np.diff(normed_scaled_vel_data)]
    signed_acc_data = np.sign(normed_acc_data)
    
    # when are we above the threshold, and when were the crossings
    over_threshold = (normed_scaled_vel_data > l)
    # integers instead of bools preserve the sign of threshold transgression
    over_threshold_int = np.array(over_threshold, dtype = np.int16)
    
    # crossings come in pairs
    threshold_crossings_int = np.concatenate([[0], np.diff(over_threshold_int)])
    threshold_crossing_indices = np.arange(threshold_crossings_int.shape[0])[threshold_crossings_int != 0]
    
    valid_threshold_crossing_indices = []
    
    # if no saccades were found, then we'll just go on and record an empty saccade
    if threshold_crossing_indices.shape[0] > 1:
        # the first saccade cannot already have started now
        if threshold_crossings_int[threshold_crossing_indices[0]] == -1:
            threshold_crossings_int[threshold_crossing_indices[0]] = 0
            threshold_crossing_indices = threshold_crossing_indices[1:]
    
        # the last saccade cannot be in flight at the end of this data
        if threshold_crossings_int[threshold_crossing_indices[-1]] == 1:
            threshold_crossings_int[threshold_crossing_indices[-1]] = 0
            threshold_crossing_indices = threshold_crossing_indices[:-1]
        
        # if threshold_crossing_indices.shape == 0:
        # break
        # check the durations of the saccades
        threshold_crossing_indices_2x2 = threshold_crossing_indices.reshape((-1,2))
        raw_saccade_durations = np.diff(threshold_crossing_indices_2x2, axis = 1).squeeze()
    
        # and check whether these saccades were also blinks...
        # blinks_during_saccades = np.ones(threshold_crossing_indices_2x2.shape[0], dtype = bool)
        # for i in range(blinks_during_saccades.shape[0]):
        #    if np.sum(xy_data_zeros[threshold_crossing_indices_2x2[i,0]-20:threshold_crossing_indices_2x2[i,1]+20]) > 0:
        #        blinks_during_saccades[i] = False
    
        # and are they too close to the end of the interval?
        right_times = threshold_crossing_indices_2x2[:,1] < xy_data.shape[0]-30
    
        valid_saccades_bool = ((raw_saccade_durations / float(sample_rate) > minimum_saccade_duration)) * right_times
        if type(valid_saccades_bool) != np.ndarray:
            valid_threshold_crossing_indices = threshold_crossing_indices_2x2
        else:
            valid_threshold_crossing_indices = threshold_crossing_indices_2x2[valid_saccades_bool]
    
        # print threshold_crossing_indices_2x2, valid_threshold_crossing_indices, blinks_during_saccades, ((raw_saccade_durations / sample_rate) > minimum_saccade_duration), right_times, valid_saccades_bool
        # print raw_saccade_durations, sample_rate, minimum_saccade_duration        
    
    saccades = []
    for i, cis in enumerate(valid_threshold_crossing_indices):
        if i%100 == 0:
            print(i)
        # find the real start and end of the saccade by looking at when the acceleleration reverses sign before the start and after the end of the saccade:
        # sometimes the saccade has already started?
        expanded_saccade_start = np.arange(cis[0])[np.r_[0,np.diff(signed_acc_data[:cis[0]] != 1)] != 0]
        if expanded_saccade_start.shape[0] > 0:
            expanded_saccade_start = expanded_saccade_start[-1]
        else:
            expanded_saccade_start = 0
            
        expanded_saccade_end = np.arange(cis[1],np.min([cis[1]+50, xy_data.shape[0]]))[np.r_[0,np.diff(signed_acc_data[cis[1]:np.min([cis[1]+50, xy_data.shape[0]])] != -1)] != 0]
        # sometimes the deceleration continues crazily, we'll just have to cut it off then. 
        if expanded_saccade_end.shape[0] > 0:
            expanded_saccade_end = expanded_saccade_end[0]
        else:
            expanded_saccade_end = np.min([cis[1]+50, xy_data.shape[0]])
        
        try:
            this_saccade = {
                'expanded_start_time': expanded_saccade_start,
                'expanded_end_time': expanded_saccade_end,
                'expanded_duration': (expanded_saccade_end - expanded_saccade_start)*1./sample_rate,
                'expanded_start_point': xy_data[expanded_saccade_start],
                'expanded_end_point': xy_data[expanded_saccade_end],
                'expanded_vector': xy_data[expanded_saccade_end] - xy_data[expanded_saccade_start],
                'expanded_amplitude': np.sum(normed_vel_data[expanded_saccade_start:expanded_saccade_end]),
                'expanded_peak_velocity': np.max(normed_vel_data[expanded_saccade_start:expanded_saccade_end])*sample_rate,

                'raw_start_time': cis[0],
                'raw_end_time': cis[1],
                'raw_duration': (cis[1] - cis[0])*1./sample_rate,
                'raw_start_point': xy_data[cis[1]],
                'raw_end_point': xy_data[cis[0]],
                'raw_vector': xy_data[cis[1]] - xy_data[cis[0]],
                'raw_amplitude': np.sum(normed_vel_data[cis[0]:cis[1]]),
                'raw_peak_velocity': np.max(normed_vel_data[cis[0]:cis[1]]) * sample_rate,

            }
            saccades.append(this_saccade)
        except IndexError:
            pass
        
    
    # if this fucker was empty
    if len(valid_threshold_crossing_indices) == 0:
        this_saccade = {
            'expanded_start_time': 0,
            'expanded_end_time': 0,
            'expanded_duration': 0.0,
            'expanded_start_point': [0.0,0.0],
            'expanded_end_point': [0.0,0.0],
            'expanded_vector': [0.0,0.0],
            'expanded_amplitude': 0.0,
            'expanded_peak_velocity': 0.0,

            'raw_start_time': 0,
            'raw_end_time': 0,
            'raw_duration': 0.0,
            'raw_start_point': [0.0,0.0],
            'raw_end_point': [0.0,0.0],
            'raw_vector': [0.0,0.0],
            'raw_amplitude': 0.0,
            'raw_peak_velocity': 0.0,
        }
        saccades.append(this_saccade)

    # shell()
    
    print('Done... Detecting Saccades')
    
    return pd.DataFrame(saccades)