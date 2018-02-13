# -*- coding: cp1252 -*-
#! /usr/bin/env python

# # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # # #
# This program is distributed with GNU Go, a Go program.        #
#                                                               #
# Write gnugo@gnu.org or see http://www.gnu.org/software/gnugo/ #
# for more information.                                         #
#                                                               #
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

# some comments (like above) and
# lots of code copied from twogtp.py from gnugo-3.6-pre4
# additions/changes by Aloril 2004

# minor changes by Blubb Fallo 2004

# Alori modified to work with simple_go.py

#try:
#    import psyco
#    from psyco.classes import *
#    psyco.full()
#except:
#    pass

import simple_go
import version

import popen2
import sys
import string
import time
import random
import os
import traceback
import config
import getopt
import time_settings

debug = 1

class Logger:
    def __init__(self):
        self.fp = open("game2.log", "a")

    def __getattr__(self, name):
        return getattr(self.fp, name)

    def write(self, s):
        self.fp.write(s)
        self.fp.flush()

logger = Logger()
config.debug_output = logger

def log(s):
    logger.write(s)
##    fp = open("game2.log", "a")
##    fp.write(s)
##    fp.close()

def coords_to_sgf(size, board_coords):
    global debug
    
    board_coords = string.lower(board_coords)
    if board_coords == "pass":
        return ""
    letter = board_coords[0]
    digits = board_coords[1:]
    if letter > "i":
        sgffirst = chr(ord(letter) - 1)
    else:
        sgffirst = letter
    sgfsecond = chr(ord("a") + int(size) - int(digits))
    return sgffirst + sgfsecond
        
def sgf_to_coords(size, sgf_coords):
    #print sgf_coords
    if len(sgf_coords)==0: return "PASS"
    letter = string.upper(sgf_coords[0])
    if letter>="I":
        letter = chr(ord(letter)+1)
    digit = str(ord('a') + int(size) - ord(sgf_coords[1]))
    return letter+digit


class GTP_controller:

    #
    # Class members:
    #   outfile         File to write to
    #   infile          File to read from

    def __init__(self, infile, outfile):
        self.infile  = infile
        self.outfile = outfile
        # total number of gtpb-logfiles
        for i in range(1000):
            log_name = "gtpb%03i.log" % i
            if not os.path.exists(log_name):
                break
        self.log_fp = open(log_name, "w")

    def get_cmd(self):
        global debug
        result = ""
        while 1:
            line = self.infile.readline()
            if not line: break
            if self.log_fp:
                self.log_fp.write(">" + line)
                self.log_fp.flush()
            if line=="\n": continue
            result = result + line
            break
        return result
        

    def set_result(self, result):
        global debug
        if debug:
            self.log_fp.write("<"+result)
            self.log_fp.flush()
        self.outfile.write(result)
        self.outfile.flush()
        


class GTP_player:

    # Class members:
    #    slave          GTP_connection
    #    master         GTP_controller

    def __init__(self):
        self.engine = simple_go.Game(19)
        self.master = GTP_controller(sys.stdin, sys.stdout)
        self.version = version.number
        self.name = version.name + version.message
        self.komi = 0.0
        self.handicap = 0
        self.sgf_number = 1
        # total number of gtpc-logfiles
        for i in range(1000):
            log_name = "gtpc%03i.log" % i
            if not os.path.exists(log_name):
                break
        self.log_fp = open(log_name, "w")
        self.clock = time_settings.Timekeeper()
        
        # note formatting: follow newline with tab
        self.cmd_options = {"help":"Can also use '-h'. Displays this message.",
                            "message=":"Message robot gives on new games\n\tQuotes required for spaces.",
                            "node_limit=":"Positive integer\n\tSpecifies the normal depth of the search.",
                            "manage_time":"If passed to program, uses time management.",
                            "urgent_time=":"Positive integer\n\tIf this is how long it has per move,\n\tradically adjusts node limit.",
                            "urgent_node=":"Positive integer\n\tWhen urgent time per move is reached, this is the number of nodes used."}

    def get_cmd_options(self):
        return self.cmd_options.keys()
    
    def help_with_cmd_options(self):
        result = "\n\n"
        for i in self.cmd_options.keys():
            result = result + "--" + string.strip(i, "=") + "\n\t" + self.cmd_options[i] + "\n\n"
        self.master.set_result(result)
    
    def handle_options(self, options):
        for opt, arg in options:
            if opt == "--message":
                self.name = version.name + " " + arg
            if opt == "--node_limit":
                try:
                    newval = string.atoi(arg)
                    config.lambda_node_limit = newval
                except string.atoi_error:
                    self.master.set_result("\n" + opt + " given is not a number, default used.\n\n")
            if opt =="--urgent_time":
                try:
                    newval = string.atoi(arg)
                    config.urgent_time_per_move_limit = newval
                except string.atoi_error:
                    self.master.set_result("\n" + opt + " given is not a number, default used.\n\n")
            if opt == "--urgent_node":
                try:
                    newval = string.atoi(arg)
                    config.urgen_node_limit = newval
                except string.atoi_error:
                    self.master.set_result("\n" + opt + " given is not a number, default used.\n\n")
            if opt == "-h" or opt == "--help":
                self.help_with_cmd_options()
            if opt == "--manage_time":
                config.manage_time = True

    def ok(self, result=None):
        if result==None: result = ""
        return "= " + result + "\n\n"

    def error(self, msg):
        return "? " + msg + "\n\n"

    def boardsize(self, size):
        #if size > simple_go.max_size:
        #    return self.error("Too big size")
        fp = open("size%03i.sgf" % self.sgf_number, "w")
        fp.write(str(self.engine))
        fp.close()
        self.sgf_number = self.sgf_number + 1
        self.engine = simple_go.Game(size)
        self.handicap = 0.0
##        if size<=9:
##            #config.debug_tactics = True
##            config.lambda_node_limit = 100
##        elif size<=13:
##            config.lambda_node_limit = 75
##        else:
##            config.lambda_node_limit = 50
        log("="*60 + "\n")
        log("boardsize: %s\n" % size)
        if os.path.exists("break.flag"):
            sys.exit(1)
        return self.ok("")

    def clear_board(self):
        return self.boardsize(self.engine.size)

    def check_side2move(self, color):
        if (self.engine.current_board.side==simple_go.BLACK) != (string.upper(color[0])=="B"):
            if self.handicap==0:
                handicap_change = 2
            else:
                handicap_change = 1
            if string.upper(color[0])=="B":
                self.handicap = self.handicap + handicap_change
            else:
                self.handicap = self.handicap - handicap_change
            self.engine.make_move(simple_go.PASS_MOVE)

    def genmove_plain(self, color, remove_opponent_dead=False, pass_allowed=True):
        if config.always_remove_opponent_dead:
            remove_opponent_dead = True
        self.check_side2move(color)
        move = self.engine.generate_move(remove_opponent_dead, pass_allowed)
        move = simple_go.move_as_string(move, self.engine.size)
        self.play_plain(color, move)
        return move

    def genmove(self, color):
        return self.ok(self.genmove_plain(color, remove_opponent_dead=False, pass_allowed=True))

    def play_plain(self, color, move):
        self.check_side2move(color)
        self.engine.make_move(simple_go.string_as_move(string.upper(move), self.engine.size))
        log("move made: %s %s\n" % (color, move))
        log("-"*60 + "\n")
        #log(str(self.engine.current_board))
##        self.engine.score_position()
##        log(self.engine.current_board.as_string_with_unconditional_status(analyze=False))
##        log("move: " + move + "\n")
##        log("score: %s unconditional score: W:%i B:%i\n" % (
##            self.final_score_as_string(),
##            self.engine.current_board.unconditional_score(simple_go.WHITE),
##            self.engine.current_board.unconditional_score(simple_go.BLACK)))
##        fp = open("game%03i.sgf" % self.sgf_number, "w")
##        fp.write(str(self.engine))
##        fp.close()

    def play(self, color, move):
        return self.ok(self.play_plain(color, move))

    def place_free_handicap(self, count):
        self.handicap = count
        result = []
        for move in self.engine.place_free_handicap(count):
            move = simple_go.move_as_string(move, self.engine.size)
            result.append(move)
        return self.ok(string.join(result))

    def set_free_handicap(self, stones):
        self.handicap = len(stones)
        for i in range(len(stones)):
            if i: self.play_plain("white", "PASS")
            self.play_plain("black", stones[i])
        return self.ok("")

    def final_status_list(self, status):
        fp = open("status%03i.sgf" % self.sgf_number, "w")
        fp.write(str(self.engine))
        fp.close()
        lst = self.engine.final_status_list(status)
        str_lst = []
        for pos in lst:
            str_lst.append(simple_go.move_as_string(pos, self.engine.size))
        return self.ok(string.join(str_lst, "\n"))

    def final_score_as_string(self):
        score = self.engine.current_board.score_position()
        if self.engine.current_board.side==simple_go.BLACK:
            score = -score
        score = score + self.komi + self.handicap
        if score>=0:
            result = "W+%.1f" % score
        else:
            result = "B+%.1f" % -score
        return result

    def final_score(self):
        fp = open("score%03i.sgf" % self.sgf_number, "w")
        fp.write(str(self.engine))
        fp.close()
        return self.ok(self.final_score_as_string())

    def genmove_cleanup(self, color):
        return self.ok(self.genmove_plain(color, remove_opponent_dead=True))

    def showboard(self):
        return self.ok(str(self.engine.current_board))

    def list_commands(self):
        result = string.join(("list_commands",
                              "boardsize",
                              "name",
                              "version",
                              "quit",
                              "clear_board",
                              "place_free_handicap",
                              "fixed_handicap",
                              "set_free_handicap",
                              "play",
                              "final_status_list",
                              "kgs-genmove_cleanup",
                              "showboard",
                              "protocol_version",
                              "komi",
                              "final_score",
                              "kgs-time_settings",
                              "time_left",
                              ), "\n")
        return self.ok(result)
        
    def relay_cmd_and_reply(self):
        cmd_line = self.master.get_cmd()
        if not cmd_line: return 0
        cmd_lst = string.split(cmd_line)
        cmd = cmd_lst[0]     #Ctrl-C cancelling shows "list index out of range" error here in the log (keep this comment)
        if cmd and cmd[0] in string.digits:
            reply_no = cmd
            cmd_lst = cmd_lst[1:]
            if not cmd_lst: return 0
            cmd = cmd_lst[0]
        else:
            reply_no = ""
        if cmd=="version":                              
            result = "= " + self.version + "\n\n"
        elif cmd=="name":
            result = "= " + self.name + "\n\n"
        elif cmd=="protocol_version":
            result = "= 2\n\n"
        elif cmd=="komi":
            self.komi = float(cmd_lst[1])
            result = "=\n\n"
        elif cmd=="genmove_white":
            result = self.genmove("white")
        elif cmd=="genmove_black":
            result = self.genmove("black")
        elif cmd=="genmove":
            result = self.genmove(cmd_lst[1])
        elif cmd=="boardsize":
            result = self.boardsize(int(cmd_lst[1]))
            self.clock.set_boardsize(int(cmd_lst[1]))
        elif cmd=="list_commands":
            result = self.list_commands()
        elif cmd=="play":
            result = self.play(cmd_lst[1], cmd_lst[2])
        elif cmd=="clear_board":
            result = self.clear_board()
        elif cmd=="place_free_handicap":
            result = self.place_free_handicap(int(cmd_lst[1]))
        elif cmd=="fixed_handicap":
            result = self.place_free_handicap(int(cmd_lst[1]))
        elif cmd=="set_free_handicap":
            result = self.set_free_handicap(cmd_lst[1:])
        elif cmd=="final_status_list":
            result = self.final_status_list(cmd_lst[1])
        elif cmd=="kgs-genmove_cleanup":
            result = self.genmove_cleanup(cmd_lst[1])
        elif cmd=="showboard":
            result = self.showboard()
        elif cmd=="final_score":
            result = self.final_score()
        elif cmd=="time_left":
            result = self.ok(self.clock.time_left(cmd_lst[1:]))
        elif cmd=="kgs-time_settings":
            result = self.ok(self.clock.kgs_set_time(cmd_lst[1:]))
        elif cmd=="quit":
            result = "=\n\n"
        else:
            self.log_fp.write("Unhandled command:" + cmd_line)
            self.log_fp.flush()
            result = self.error("Unknown command")
        if reply_no:
            result = result[0] + reply_no + result[1:]
        self.master.set_result(result)
        return cmd!="quit"
    def loop(self):
        try:
            while self.relay_cmd_and_reply():
                pass
        except:
            traceback.print_exc(None, self.log_fp)
            self.log_fp.flush()
            raise

if __name__=="__main__":
    player = GTP_player()
    try:
        options, args = getopt.getopt(sys.argv[1:], "h", player.get_cmd_options())
        player.handle_options(options)
    except getopt.GetoptError:
        print "Invalid option"
        player.help_with_cmd_options()
        sys.exit(2)
    player.loop()
    
