#Simple Go playing program
#Goals are:
#1) Easy to understand:
#   If fully understanding GnuGo could be considered advanced,
#   then this should be beginner level Go playing program
#   Main focus is in understanding code, not in fancy stuff.
#   It should illustrate Go concepts using simple code.
#2) Plays enough well to get solid rating at KGS
#3) Small
#4) Dual license: GPL and license used at Senseis

#Why at Senseis?
#Goal is to illustrate Go programming and not to code another "GnuGo".
#Senseis looks like good place to co-operatively write text and 
#create diagrams to illustrate algorithms.
#So main focus is in explaining code.
#Also possibility is to crosslink between concepts and documented code.
#http://senseis.xmp.net/?SimpleGo

#v0.0:
#Select move randomly from all legal moves including pass move.

#v0.1:
#Its quite simple actually:
#Unconditionally alive groups and dead groups in those eyes and eyes are counted as 1/each intersection
#For other white/black blocks: (1 - (1 - (liberties/max_liberties)**2 ) ) * 0.7 * block size:
#    if group has maximum amount of liberties, it gets 0.7*amount of stones
#Try each move and score them: also atari replies to block and neighbour block are checked
#Thats about it.

#v0.1.1:
#Adding stone is now much faster.
#Groups completely surrounded by live blocks:
#ignore empty points adjacent to live block when counting potential eyes.

#v0.1.2:
#Can detect more unconditional life cases: hopefully now equivalent to Benson algorithm
#This mean less futile moves at end in some cases.

#v0.1.3:
#Can detect more unconditionally dead grops:
#It analyses false eyes. Then potential eye areas in previous unconditional life analysis consisting of empty points and
#opponent stones that don't have enough potential true eyes are also marked as unconditionally dead.

#v0.1.4:
#Handles big handicaps on small boards better: usually same as playing them.

#v0.1.5:
#Implemented Zobrist hashing: now 2-3x faster

#v0.1.6:
#Detects many groups that are unconditionally dead even if there are capturable opponent stones inside.

#v0.2:
#1-2 liberty tactics (not complete, but enough for ladders and many other things)
#make critical bonus global: if critical groups saved by move -> bonus for them
#playing into dead groups -> penalty
#if can't play live stones -> pass and can't have any tactically_live/critical
#update dead group listing to include tactically dead stones

#v0.2.1:
#use standard handicap placement for 2-9 stones on 9x9, 13x13 and 19x19 boards

#v0.2.2:
#Lambda search and quick scoring: no global search anymore
#Implementation not complete

#v0.2.3:
#various bugs fixed

#v0.2.4:
#proof number search+atari extension and various bugs fixed and various heuristical improvements

#v0.2.5:
#faster

#v0.2.6:
#danger detection: increase nodecounts when capture results are detected in proof number search
#bigger capture % compared to non capture proos means bigger increase in node limits

#v0.2.7:
#One case of marking dead stones incorrectly fixed and bigger than 25 size now partially supported.

#v0.2.8:
#In double threats look if simple capturing of some surrounding group can make threat futile.

#TODO: v0.3 and later:
#chain and dragon building
#influence: bouzy? maybe something else instead
#liberty counting: potential
#  eye counting part of above?
#  diagonal connction cut?

import string, random, sys, math
import config
from const import *
from utils import *

from block import Block
from eye import Eye
from gothread import Thread
from board import Board
from pos_cache import PositionCache
from game import Game

def main():
    """Play game against itself on 5x5 board.
       Print all positions and moves made while playing.
    """
    old_use_nth_order_liberties = config.use_nth_order_liberties
    #random.seed(1)
    size = 5
    g_white = Game(size)
    #old_lambda = config.use_lambda
    #old_tactics = config.use_tactics
    #config.use_lambda = False
    #config.use_tactics = False
    g_black = Game(size)
    #config.use_lambda = old_lambda
    #config.use_tactics = old_tactics
    while True:
        #move = g.select_random_no_eye_fill_move()
        
        #if g.current_board.side==BLACK:
        #    config.use_threads_scoring_system = False
        #else:
        #    config.use_threads_scoring_system = True
        
        #if g.current_board.side==BLACK:
        #    config.use_nth_order_liberties = False
        #else:
        #    config.use_nth_order_liberties = old_use_nth_order_liberties
        
        #if g.current_board.side==BLACK:
        #    config.use_oxygen = False
        #else:
        #    config.use_oxygen = True
        
        #if g.current_board.side==BLACK:
        #    config.use_tactics = False
        #    config.use_lambda = False
        #else:
        #    config.use_tactics = True
        #    config.use_lambda = True

        if g_black.current_board.side==BLACK:
            move = g_black.generate_move()
        else:
            move = g_white.generate_move()
        g_black.make_move(move)
        g_white.make_move(move)
        print move_as_string(move)
        print g_white.current_board
##        if config.use_tactics:
##            score = g_white.score_tactic_position()
##            print g_white.current_board.as_string_with_unconditional_status(analyze=False)
##            print score
##        else:
##            print g_white.current_board.as_string_with_unconditional_status()
##            print g_white.current_board.score_position()
        #print "PASS"
        #g.make_move(PASS_MOVE)
        fp = open("tmpW.sgf", "w")
        fp.write(str(g_white))
        fp.close()
        fp = open("tmpB.sgf", "w")
        fp.write(str(g_black))
        fp.close()
        #import pdb; pdb.set_trace()
        #if last 2 moves are pass moves: exit loop
        #if len(g.move_history)==10:
        #    break
        if g_white.has_2_passes():
            break
    return g_white, g_black

if __name__=="__main__":
    #If this file is executed directly it will play game against itself.
    main()
