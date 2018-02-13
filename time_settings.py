# -*- coding: cp1252 -*-
#! /usr/bin/env python

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# Copyright 1999, 2000, 2001, 2002, 2003 and 2004               #
# by the Free Software Foundation.                              #
#                                                               #
# This program is free software; you can redistribute it and/or #
# modify it under the terms of the GNU General Public License   #
# as published by the Free Software Foundation - version 2.     #
#                                                               #
# This program is distributed in the hope that it will be       #
# useful, but WITHOUT ANY WARRANTY; without even the implied    #
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR       #
# PURPOSE.  See the GNU General Public License in file COPYING  #
# for more details.                                             #
#                                                               #
# You should have received a copy of the GNU General Public     #
# License along with this program; if not, write to the Free    #
# Software Foundation, Inc., 59 Temple Place - Suite 330,       #
# Boston, MA 02111, USA.                                        #
# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #

import probstat
import config

class Timekeeper:
    def __init__(self):
        self.boardsize = 19
        self.num_moves = 0
        self.statistics = probstat.Probstat(config.statistics_limit)
        self.stat_limit_min = 10 
        self.node_adjustment = 0
        self.none = "none"
        self.absolute = "absolute"
        self.by = "byoyomi"
        self.cby = "canadian"
        self.main_time = "main_time"
        self.by_time = "by_time"
        self.stones = "stones"
        self.periods = "periods"
        self.time_settings = {self.none:False,
                              self.absolute:False,
                              self.by:False,
                              self.cby:False,
                              self.main_time:0,
                              self.by_time:0,
                              self.stones:0,
                              self.periods:0}
  
    def reset(self):
        """Resets all time settings to zero
        Resets boardsize to 19
        """
        
        for k in self.time_settings.keys():
            self.time_settings[k] = 0
        self.boardsize = 19
    
    def _max_moves(self):
        """Makes an estimate of the number of moves it will have 
        to play given the size of the board
        """
        
        return int(0.75 * (self.boardsize**2) / 2)
        
    def _can_get_statistics(self):
        """True if enough data has been stored
        """
        
        if self.statistics.size() <= self.stat_limit_min:
            return False
        else:
            return True
        
    def set_boardsize(self, size):
        """Sets the board size for determining the rate to adjust
        config.lambda_node_limit and to determine the approximate
        number of moves for games
        """
        
        self.boardsize = size
        self.node_adjustment = 1 + 38 / size
            
    def kgs_set_time(self, settings):
        """Handles the arguments passed from KGS's "kgs-time_settings"
        command.
        """
        
        #settings = ["type", main_time, by_time, stones/periods]
        self.reset()
        self.time_settings[settings[0]] = True
        self.num_moves = self._max_moves()
        if self.time_settings[self.none]:
            return self.none
        self.time_settings[self.main_time] = int(settings[1])
        if self.time_settings[self.absolute]:
            return self.absolute + " " + str(self.time_settings[self.main_time])
        self.time_settings[self.by_time] = int(settings[2])
        if self.time_settings[self.by]:
            self.time_settings[self.periods] = int(settings[3])
            return self.by + " " + str(self.time_settings[self.main_time]) + " " + str(self.time_settings[self.by_time]) + " " + str(self.time_settings[self.periods])
        else:
            self.time_settings[self.stones] = int(settings[3])
            return self.cby + " " + str(self.time_settings[self.main_time]) + " " + str(self.time_settings[self.by_time]) + " " + str(self.time_settings[self.stones])
        
    def time_left(self, parameters):
        """Handles the arguments passed by "time_left" command.
        Determines the time per move available. Stores data
        on the time it has taken per move.
        """
        
        # parameters is [color, maintime, stones]
        # but in kgs, periods is always zero, and when 
        # byo-yomi is reached, the "main time" will be the sum
        # of all periods
        
        #TODO remove? Will this ever be called?
        if self.time_settings[self.none]:
            return "no time"
        if not config.manage_time:
            return "time not managed"
        
        time = int(parameters[1])
        stones = int(parameters[2])
        default_message = "ok"
        
        if self.num_moves <= 0:
            self.num_moves = 10
        
        if self.time_settings[self.absolute]:
            config.time_per_move_limit = int(time / self.num_moves)
            difference = self.time_settings[main_time] - time
            if difference == 0:
                return default_message
            else:
                self.num_moves = self.num_moves - 1
            data = difference / float(config.lambda_node_limit)
            self.statistics.add_data(data)
            if not self._can_get_statistics():
                return default_message
            self.time_settings[self.main_time] = time
                
        if self.time_settings[self.by]:
            total_by_time = self.time_settings[self.by_time] * self.time_settings[self.periods]
            if time > total_by_time:
                difference = self.time_settings[main_time] - time
                data = difference / float(config.lambda_node_limit)
                self.statistics.add_data(data)
                config.time_per_move_limit = int(1.25 * self.time_settings[self.by_time])
                self.time_settings[self.main_time] = time
            else:
                starting_periods = self.time_settings[self.periods]
                periods_remaining = time / self.time_settings[self.by_time]
                difference = starting_periods - periods_remaining
                if difference == 0:
                    #assume we used most of one period
                    self.statistics.add_data( 0.95 * self.time_settings[self.by_time] / float(config.lambda_node_limit))
                else:
                    #assume we used just over one period
                    self.statistics.add_data(1.05 * difference / float(config.lambda_node_limit))
                self.time_settings[self.periods] = periods_remaining
                # while there are three periods left, not much urgency
                config.time_per_move_limit = int(self.time_settings[self.by_time] * self.time_settings[self.periods] / float(3))
        
        if self.time_settings[self.cby]:
            if stones == 0: # still in main time
                difference = self.time_settings[self.main_time] - time
                self.time_settings[self.main_time] = time
            else:
                difference = self.time_settings[self.by_time] - time
                self.time_settings[self.by_time] = time
                self.time_settings[self.stones] = stones
            time_per_stone = self.time_settings[self.by_time] / self.time_settings[self.stones]
            config.time_per_move_limit = time_per_stone
            if difference > 0:
                data = difference / float(config.lambda_node_limit)
                self.statistics.add_data(data)
            
        self._adjust_node_limit()            
        if not self._can_get_statistics():
            return "ok: node limit " + str(config.lambda_node_limit)
        return "ok: node limit " + str(config.lambda_node_limit) + " time per move per node mean is " + str(self.statistics.mean()) + " confidence interval is " + str(self.statistics.confidence_interval(2))
    
    def _adjust_node_limit(self):
        """Adjusts config.lambda_node_limit based on statistics of
        move history.
        """
        
        #if config.time_per_move_limit <= config.urgent_time_per_move_limit:
        #    config.lambda_node_limit = config.urgent_node_limit
        if self._can_get_statistics():
            tpmpn_interval = self.statistics.confidence_interval(2)
            config.lambda_node_limit = int(config.time_per_move_limit / tpmpn_interval[1]) + 1
