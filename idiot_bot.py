# -*- coding: cp1252 -*-
#! /usr/bin/env python

#IdiotBot at KGS

#This plays mostly randomly using these rules:
#1) If can capture/extend group in atari: select one randomly
#2) If not, then select move that doesn't fill single space 'eye'
#3) If not, then pass
#basically, but for scoring and potentially few moves before it: Uses SimpleBot v0.1.X engine
#For handicap placement also using SimpleBot v0.1.X engine

import sys, os
import play_gtp
import simple_go

class IdiotBot(play_gtp.GTP_player):
    # Class members:
    #    slave          GTP_connection
    #    master         GTP_controller

    def __init__(self):
        self.engine = simple_go.Game(19)
        self.master = play_gtp.GTP_controller(sys.stdin, sys.stdout)
        self.version = "0.0.2"
        self.name = "IdiotBot: I play mostly randomly: if I'm too easy, try WeakBot50k. Its maybe 60 stones stronger. 30k humans are often 80 stones stronger. My info contains links to my source code: "
        self.komi = 0.0
        self.handicap = 0
        # total number of gtpc-logfiles
        for i in range(1000):
            log_name = "gtpc%03i.log" % i
            if not os.path.exists(log_name):
                break
        self.log_fp = open(log_name, "w")

    
    def genmove_plain(self, color, remove_opponent_dead=False, pass_allowed=True):
        self.check_side2move(color)
        move = self.engine.select_random_no_eye_fill_move(remove_opponent_dead, pass_allowed)
        move = simple_go.move_as_string(move, self.engine.size)
        self.play_plain(color, move)
        return move


if __name__=="__main__":
    player = IdiotBot()
    player.loop()
    
