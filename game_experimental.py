import string, random, sys, math, copy
import config
from const import *
from utils import *
from types import *

from chain import Chain
from board import Board
from pos_cache import *

class GameExperimental:
    def __init__(self):
        pass

    def find_different_positions(self):
        self.diff_fp = open("diff.log", "w")
        self.different_positions = {}
        self.diff_positions_max_depth = 0
        key = self.plain_key()
        self.different_positions[key] = True
        new_list = [key]
        prev_length = 0
        while new_list:
            print self.diff_positions_max_depth, len(new_list), len(self.different_positions)
            self.diff_positions_max_depth = self.diff_positions_max_depth + 1
            old_list = new_list
            new_list = []
            for key in old_list:
                self.set_board_from_plain_key(key)
                for move in self.iterate_moves():
                    self.make_move(move)
                    key = self.plain_key()
                    if key not in self.different_positions:
                        self.different_positions[key] = True
                        new_list.append(key)
                        self.diff_fp.write(key+"\n")
                    self.undo_move()
        self.diff_fp.close()

    def search(self, max_depth):
        self.search_trace.write("\nstart iteration: %s\n" % max_depth)
        return self.search_recursively(max_depth, 0, WORST_SCORE, BEST_SCORE)

    def search_recursively(self, max_depth, depth, alpha, beta):
        #print depth, self.node_count, alpha, beta, self.move_history[-depth:]
        best_score = WORST_SCORE
        best_variation = []
        if depth>=max_depth or self.has_2_passes():
            #return self.current_board.stone_score(), []
            return self.current_board.chinese_score_position(), []
        self.current_board.score_position()
        forbidden_moves = self.current_board.territory_as_dict()
        move_list = list(self.iterate_moves())
        key = self.current_board.key()
        if key in self.search_cache:
            old_entry = self.search_cache[key]
            if old_entry.move in move_list:
                move_list.remove(old_entry.move)
                move_list.insert(0, old_entry.move)
        old_alpha = alpha
        for move in move_list:
            if move in forbidden_moves:
                continue
            if best_score > beta:
                break
            if best_score==self.size**2:
                break #no need to search inferior moves, can't get better score than whole board win ;-)
            self.make_move(move)
            score, variation = self.search_recursively(max_depth, depth+1, -beta, -alpha)
            score = -score
            self.undo_move()
            if score > best_score:
                best_score = score
                best_variation = [move] + variation
                if score > alpha:
                    alpha = score
                #print ">", depth+1, self.node_count, best_score, alpha, beta, best_variation
                #print ">", self.move_history
        #store to cache
        self.search_trace.write("\n%smoves=%s\nscore=%s\nalpha=%s\nbeta=%s\nvariation=%s\nnodes=%s\n" % (self.current_board, self.move_history, best_score, old_alpha, beta, best_variation, self.node_count))
        exact = old_alpha < score < beta
        search_depth = max_depth - depth
        if key==-417640481:
            import pdb; pdb.set_trace()
        if best_variation:
            best_move = best_variation[0]
            new_entry = PositionCache(key, best_score, best_move, search_depth, exact)
            if key in self.search_cache:
                self.search_trace.write("old cache: %s\n" % self.search_cache[key])
                if new_entry > self.search_cache[key]:
                    self.search_cache[key] = new_entry
                    self.search_trace.write("new cache: %s\n" % new_entry)
            else:
                self.search_cache[key] = new_entry
        return best_score, best_variation


    def form_chains(self):
        self.chains = []
        cboard = self.current_board
        for color in (BLACK, WHITE):
            for block in cboard.iterate_blocks(color):
                block.chain = None

            for block1 in cboard.iterate_blocks(color):
                if block1.chain: continue
                chain = Chain()
                self.chains.append(chain)
                chain.add_block(block1)
                block_added = True
                while block_added:
                    block_added = False
                    for block2 in cboard.iterate_blocks(color):
                        if block2.chain: continue
                        for block3 in chain.blocks.values():
                            if len(cboard.block_connection_status(block3.get_origin(), block2.get_origin()))>=2:
                                chain.add_block(block2)
                                block_added = True
                                break

    def score_chain(self, chain):
        cboard = self.current_board
        
        chain_status = UNCONDITIONAL_UNKNOWN

        for block in chain.blocks.values():
            if block.status==UNCONDITIONAL_LIVE:
                chain_status = UNCONDITIONAL_LIVE
                unconditional_value = 1.0
                break
            elif block.status==UNCONDITIONAL_DEAD:
                chain_status = UNCONDITIONAL_DEAD
                unconditional_value = -1.0
                break

        score = 0
        #if is unconditionally decided? well if part of chain is unconditionally alive, it doesn't mean all of it is: we just assume so
        if chain_status in (UNCONDITIONAL_LIVE, UNCONDITIONAL_DEAD):
            for block in chain.blocks.values():
                score = score + unconditional_value * block.size()
        else: #not unconditionally decided
            liberties_dict = {}
            chain_size = 0
            for block in chain.blocks.values():
                chain_size = chain_size + block.size()
                if block.status==TACTICALLY_DEAD:
                    value_ratio = dead_stone_value_ratio
                elif block.status==TACTICALLY_CRITICAL:
                    if block.color==cboard.side:
                        value_ratio = our_critical_stone_value
                    else:
                        value_ratio = other_critical_stone_value
                else:
                    value_ratio = normal_stone_value_ratio
                for liberty in cboard.list_block_liberties(block):
                    liberties_dict[liberty] = min(liberties_dict.get(liberty, 1.0), value_ratio)
            liberty_value = sum(liberties_dict.values())
            liberty_ratio = liberty_value / (chain_size * 2 + 2)
            score = chain_size * liberty_ratio
            
        if chain.get_color()!=cboard.side:
            score = -score
        print "chain:", self.move_as_string(chain.get_origin()), score
        return score

