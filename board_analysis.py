import string, random, sys, math, copy
import config
from const import *
from utils import *

from block import Block
from eye import Eye
from gothread import Thread

class BoardAnalysis:
    """code to analyse positions: scoring, (unconditional) life & death
    """
    def __init__(self):
        self.assumed_unconditional_alive_list = []
    
    def block_connection_status(self, pos1, pos2):
        block1 = self.blocks[pos1]
        block2 = self.blocks[pos2]
        if block1.color!=block2.color or block1.color==EMPTY:
            return []
        liberties1 = self.list_block_liberties(block1)
        liberties2 = self.list_block_liberties(block2)
        #if same blocks, still works: all liberties then same
        common_liberties = union_list(liberties1, liberties2)
        return common_liberties

    def analyse_eye_point(self, pos, other_color):
        """Analyse one point for eye type.
           If not empty or adjacent to other color: return None.
           Otherwise analyse True/False status of eye.
           
           

           True(!) and false(?) eyes.
           XXX XXO XXO XXO OXO OXO
           X!X X!X X?X X?X X?X X?X
           XXX XXX OXX XXO XXO OXO
           
           --- --- --- +-- +--
           X!X X?X X?X |!X |?X
           XXX XXO OXO |XX |XO
           
           2 empty points: True(!) and false(?) eyes.
           This works just fine with normal (false) eye code.
           XXXX XXXO XXXO XXXO OXXO OXXO
           X!!X X!!X X!!X X!?X X!?X X??X
           XXXX XXXX OXXX XXXO XXXO OXXO
           
           ---- ---- ---- +--- +---
           X!!X X!?X X??X |!!X |!?X
           XXXX XXXO OXXO |XXX |XXO
           
           3 empty points in triangle formation: True(!) and false(?) eyes.
           This works just fine with normal (false) eye code.
           XXXX XXXO XXXO XXXO OXXO OXXO
           X!!X X!!X X!!X X!!X X!!X X?!X
           XX!X XX!X OX!X XX!X XX!X OX!X
            XXX  XXX  XXX  XXO  XXO  XXO
           
           XXXX XXXO XXXO XXXO OXXO OXXO
           X!!X X!!X X!!X X!!X X!!X X?!X
           XX!X XX!X OX!X XX?X XX?X OX?X
            OXX  OXX  OXX  OXO  OXO  OXO
        """
        if self.goban[pos]!=EMPTY:
            return None
        for pos2 in self.iterate_neighbour(pos):
            if self.goban[pos2]==other_color:
                return None
        total_count = 0
        other_count = 0
        for pos2 in self.iterate_diagonal_neighbour(pos):
            total_count = total_count + 1
            if self.goban[pos2]==other_color and self.blocks[pos2].status==UNCONDITIONAL_LIVE:
                other_count = other_count + 1
        if total_count==4:
            if other_count > 1:
                return False
            else:
                return True
        else:
            if other_count > 0:
                return False
            else:
                return True

    def analyse_opponent_stone_as_eye_point(self, pos):
        """Analyse one point for eye type.
           Otherwise analyse True/False status of eye.
           Only take into account live other color stones.
           

           True(O) and false(o) eyes.
           @ == unconditionally live O stone.
           XXX XX@ XX@ XX@ @X@ @X@
           .OX .OX .oX .oX .oX .oX
           XXX XXX @XX XX@ XX@ @X@
           
           --- --- --- +-- +--
           .OX .oX .oX |O. |o.
           XXX XX@ @X@ |XX |X@
           
        """
        total_count = 0
        other_count = 0
        color = self.goban[pos]
        for pos2 in self.iterate_diagonal_neighbour(pos):
            total_count = total_count + 1
            if self.goban[pos2]==color and self.blocks[pos2].status==UNCONDITIONAL_LIVE:
                other_count = other_count + 1
        if total_count==4:
            if other_count > 1:
                return False
            else:
                return True
        else:
            if other_count > 0:
                return False
            else:
                return True

    def analyze_color_unconditional_status(self, color):
        """1) List potential eyes (eyes: empty+opponent areas flood filled):
              all empty points must be adjacent to those neighbour blocks with given color it gives eye.
           2) List all blocks with given color
              that have at least 2 of above mentioned areas adjacent
              and has empty point from it as liberty.
           3) Go through all potential eyes. If there exists neighbour
              block with less than 2 eyes: remove this this eye from list.
           4) If any changes in step 3, go back to step 2.
           5) Remaining blocks of given color are unconditionally alive and
              and all opponent blocks inside eyes are unconditionally dead.
           6) Finally update status of those blocks we know.
           7) Analyse dead group status.

           See test.py for testcases
        """
        #find potential eyes
        eye_list = []
        not_ok_eye_list = [] #these might still contain dead groups if totally inside live group
        eye_colors = EMPTY + other_side[color]
        for block in self.iterate_blocks(EMPTY+WHITE+BLACK):
            block.eye = None
        for block in self.iterate_blocks(eye_colors):
            if block.eye: continue
            current_eye = Eye()
            eye_list.append(current_eye)
            blocks_to_process = [block]
            while blocks_to_process:
                block2 = blocks_to_process.pop()
                if block2.eye: continue
                block2.eye = current_eye
                current_eye.parts.append(block2)
                for pos in block2.neighbour:
                    block3 = self.blocks[pos]
                    if block3.color in eye_colors and not block3.eye:
                        blocks_to_process.append(block3)
        #check that all empty points are adjacent to our color
        ok_eye_list = []
        for eye in eye_list:
            prev_our_blocks = None
            eye_is_ok = False
            for stone in eye.iterate_stones():
                if self.goban[stone]!=EMPTY:
                    continue
                eye_is_ok = True
                our_blocks = []
                for pos in self.iterate_neighbour(stone):
                    block = self.blocks[pos]
                    if block.color==color and block not in our_blocks:
                        our_blocks.append(block)
                #list of blocks different than earlier
                if prev_our_blocks!=None and prev_our_blocks != our_blocks:
                    ok_our_blocks = []
                    for block in our_blocks:
                        if block in prev_our_blocks:
                            ok_our_blocks.append(block)
                    our_blocks = ok_our_blocks
                #this empty point was not adjacent to our block or there is no block that has all empty points adjacent to it
                if not our_blocks:
                    eye_is_ok = False
                    break
                    
                prev_our_blocks = our_blocks
            if eye_is_ok:
                ok_eye_list.append(eye)
                eye.our_blocks = our_blocks
            else:
                not_ok_eye_list.append(eye)
                #remove reference to eye that is not ok
                for block in eye.parts:
                    block.eye = None
        eye_list = ok_eye_list

        #first we assume all blocks to be ok
        for block in self.iterate_blocks(color):
            block.eye_count = 2

        #main loop: at end of loop check if changes
        while True:
            changed_count = 0
            for block in self.iterate_blocks(color):
                #not really needed but short and probably useful optimization
                if block.eye_count < 2:
                    continue
                #count eyes
                block_eye_list = []
                for stone in block.neighbour:
                    eye = self.blocks[stone].eye
                    if eye and eye not in block_eye_list:
                        block_eye_list.append(eye)
                #count only those eyespaces which have empty point(s) adjacent to this block
                block.eye_count = 0
                for eye in block_eye_list:
                    if block in eye.our_blocks:
                        block.eye_count = block.eye_count + 1
                if block.eye_count < 2:
                    changed_count = changed_count + 1
            #check eyes for required all groups 2 eyes
            ok_eye_list = []
            for eye in eye_list:
                eye_is_ok = True
                for block in self.iterate_neighbour_eye_blocks(eye):
                    if block.eye_count < 2:
                        eye_is_ok = False
                        break
                if eye_is_ok:
                    ok_eye_list.append(eye)
                else:
                    changed_count = changed_count + 1
                    not_ok_eye_list.append(eye)
                    #remove reference to eye that is not ok
                    for block in eye.parts:
                        block.eye = None
                eye_list = ok_eye_list
            if not changed_count:
                break

        #mark alive and dead blocks
        for block in self.iterate_blocks(color):
            if block.eye_count >= 2:
                block.status = UNCONDITIONAL_LIVE
        for eye in eye_list:
            eye.mark_status(color)

        #for heuristical death search
        if self.assumed_unconditional_alive_list:
            for pos in self.assumed_unconditional_alive_list:
                block = self.blocks[pos]
                block.status = UNCONDITIONAL_LIVE
                extend_color = block.color

            blocks2analyse = []
            for block in self.iterate_blocks(extend_color):
                if block.status==UNCONDITIONAL_LIVE:
                    blocks2analyse.append(block)
            while blocks2analyse:
                block1 = blocks2analyse.pop()
                for block2 in self.iterate_blocks(extend_color):
                    if block2.status==UNCONDITIONAL_UNKNOWN and \
                           len(self.block_connection_status(block1.get_origin(), block2.get_origin()))>=2:
                        blocks2analyse.append(block2)
                        block2.status = UNCONDITIONAL_LIVE

        #Unconditional dead part:
        #Mark all groups with only 1 potential empty point and completely surrounded by live groups as dead.
        #All empty points adjacent to live group are not counted.
        for eye_group in not_ok_eye_list:
            eye_group.dead_analysis_done = False
        for eye_group in not_ok_eye_list:
            if eye_group.dead_analysis_done: continue
            eye_group.dead_analysis_done = True
            true_eye_list = []
            false_eye_list = []
            eye_block = Block(eye_colors)
            #If this is true then creating 2 eyes is impossible or we need to analyse false eye status.
            #If this is false, then we are unsure and won't mark it as dead.
            two_eyes_impossible = True
            has_unconditional_neighbour_block = False
            maybe_dead_group = Eye()
            blocks_analysed = []
            blocks_to_analyse = eye_group.parts[:]
            while blocks_to_analyse and two_eyes_impossible:
                block = blocks_to_analyse.pop()
                if block.eye:
                    block.eye.dead_analysis_done = True
                blocks_analysed.append(block)
                if block.status==UNCONDITIONAL_LIVE:
                    if block.color==color:
                        has_unconditional_neighbour_block = True
                    else:
                        two_eyes_impossible = False
                    continue
                maybe_dead_group.parts.append(block)
                for pos in block.stones:
                    eye_block.add_stone(pos)
                    if block.color==EMPTY:
                        eye_type = self.analyse_eye_point(pos, color)
                    elif block.color==color:
                        eye_type = self.analyse_opponent_stone_as_eye_point(pos)
                    else:
                        continue
                    if eye_type==None:
                        continue
                    if eye_type==True:
                        if len(true_eye_list) == 2:
                            two_eyes_impossible = False
                            break
                        elif len(true_eye_list) == 1:
                            if self.are_adjacent_points(pos, true_eye_list[0]):
                                #Second eye point is adjacent to first one.
                                true_eye_list.append(pos)
                            else: #Second eye point is not adjacent to first one.
                                two_eyes_impossible = False
                                break
                        else: #len(empty_list) == 0
                            true_eye_list.append(pos)
                    else: #eye_type==False
                        false_eye_list.append(pos)
                if two_eyes_impossible:
                    #bleed to neighbour blocks that are at other side of blocking color block:
                    #consider whole area surrounded by unconditional blocks as one group
                    for pos in block.neighbour:
                        block = self.blocks[pos]
                        if block not in blocks_analysed and block not in blocks_to_analyse:
                            blocks_to_analyse.append(block)
                
            #must be have some neighbour groups:
            #for example board that is filled with stones except for one empty point is not counted as unconditionally dead
            if two_eyes_impossible and has_unconditional_neighbour_block:
                if (true_eye_list and false_eye_list) or \
                   len(false_eye_list) >= 2:
                    #Need to do false eye analysis to see if enough of them turn to true eyes.
                    both_eye_list = true_eye_list + false_eye_list
                    stone_block_list = []
                    #Add holes to eye points
                    for eye in both_eye_list:
                        eye_block.remove_stone(eye)

                    #Split group by eyes.
                    new_mark = 2 #When stones are added they get by default value True (==1)
                    for eye in both_eye_list:
                        for pos in self.iterate_neighbour(eye):
                            if pos in eye_block.stones:
                                self.flood_mark(eye_block, pos, new_mark)
                                splitted_block = self.split_marked_group(eye_block, new_mark)
                                stone_block_list.append(splitted_block)

                    #Add eyes to block neighbour.
                    for eye in both_eye_list:
                        for pos in self.iterate_neighbour(eye):
                            for block in stone_block_list:
                                if pos in block.stones:
                                    block.neighbour[eye] = True

                    #main false eye loop: at end of loop check if changes
                    while True:
                        changed_count = 0
                        #Remove actual false eyes from list.
                        for block in stone_block_list:
                            if len(block.neighbour)==1:
                                 neighbour_list = block.neighbour.keys()
                                 eye = neighbour_list[0]
                                 both_eye_list.remove(eye)
                                 #combine this block and eye into other blocks by 'filling' false eye
                                 block.add_stone(eye)
                                 for block2 in stone_block_list[:]:
                                     if block!=block2 and eye in block2.neighbour:
                                         block.add_block(block2)
                                         stone_block_list.remove(block2)
                                 del block.neighbour[eye]
                                 changed_count =  changed_count + 1
                                 break #we have changed stone_block_list, restart

                        if not changed_count:
                            break

                    #Check if we have enough eyes.
                    if len(both_eye_list) > 2:
                        two_eyes_impossible = False
                    elif len(both_eye_list) == 2:
                        if not self.are_adjacent_points(both_eye_list[0], both_eye_list[1]):
                            two_eyes_impossible = False
                #False eye analysis done: still surely dead
                if two_eyes_impossible:
                    maybe_dead_group.mark_status(color)

    def analyze_unconditional_status(self):
        """Analyze unconditional status for each color separately
        """
        #Initialize status to unknown for all blocks
        for block in self.iterate_blocks(BLACK+WHITE+EMPTY):
            block.status = UNCONDITIONAL_UNKNOWN
        #import pdb; pdb.set_trace()
        self.analyze_color_unconditional_status(BLACK)
        self.analyze_color_unconditional_status(WHITE)
        #cleanup
        for block in self.iterate_blocks(BLACK+WHITE+EMPTY):
            del block.eye

    def as_string_with_unconditional_status(self, analyze=True):
        """Convert position to string suitable for printing to screen.
           
           Each position gets corresponding character as defined here:
           Empty          : .
           Black          : X
           White          : O
           Alive black    : &
           Alive white    : @
           Dead black     : x
           Dead white     : o
           White territory: =
           Black territory: :
           
           Returns board as string.
        """
        color_and_status_to_character = {
           EMPTY + UNCONDITIONAL_UNKNOWN         : EMPTY,
           BLACK + UNCONDITIONAL_UNKNOWN         : BLACK,
           WHITE + UNCONDITIONAL_UNKNOWN         : WHITE,
           BLACK + UNCONDITIONAL_LIVE            : "&",
           WHITE + UNCONDITIONAL_LIVE            : "@",
           BLACK + UNCONDITIONAL_DEAD            : "x",
           WHITE + UNCONDITIONAL_DEAD            : "o",
           EMPTY + WHITE_UNCONDITIONAL_TERRITORY : "=",
           EMPTY + BLACK_UNCONDITIONAL_TERRITORY : ":",
           BLACK + TACTICALLY_UNKNOWN            : BLACK,
           WHITE + TACTICALLY_UNKNOWN            : WHITE,
           BLACK + TACTICALLY_LIVE               : "B",
           WHITE + TACTICALLY_LIVE               : "W",
           BLACK + TACTICALLY_DEAD               : "b",
           WHITE + TACTICALLY_DEAD               : "w",
           BLACK + TACTICALLY_CRITICAL           : "P",
           WHITE + TACTICALLY_CRITICAL           : "V",
        }
        if analyze:
            self.analyze_unconditional_status()
        s = self.side + " to move:\n"
        board_x_coords = "   " + x_coords_string[:self.size]
        s = s + board_x_coords + "\n"
        s = s + "  +" + "-"*self.size + "+\n"
        for y in range(self.size, 0, -1):
            if y < 10:
                board_y_coord = " " + str(y)
            else:
                board_y_coord = str(y)
            line = board_y_coord + "|"
            for x in range(1, self.size+1):
                pos_as_character = color_and_status_to_character[self.goban[x,y] + self.blocks[x,y].status]
                line = line + pos_as_character
            s = s + line + "|" + board_y_coord + "\n"
        s = s + "  +" + "-"*self.size + "+\n"
        s = s + board_x_coords + "\n"
        return s

    def save_block_status(self):
        status_dict = {}
        for block in self.iterate_blocks(EMPTY+WHITE+BLACK):
            if not hasattr(block, "status"):
                continue
            origin = block.get_origin()
            status_dict[origin] = block.status
        return status_dict

    def restore_block_status(self, status_dict):
        for origin in status_dict:
            block = self.blocks[origin]
            block.status = status_dict[origin]

    def find_eye_points(self):
        """this method is not used currently"""
        undecided_list = []
        for block in self.iterate_blocks(EMPTY+WHITE+BLACK):
            if block.status in (UNCONDITIONAL_LIVE, UNCONDITIONAL_DEAD, WHITE_UNCONDITIONAL_TERRITORY, BLACK_UNCONDITIONAL_TERRITORY):
                continue
            if block.color!=EMPTY:
                undecided_list.append(block.get_origin())
                continue
            lambda1_area = {}
            print move_as_string(block.get_origin()), block.color,
            for pos in block.stones:
                eye_type = self.analyse_eye_point(pos, WHITE)
                if eye_type:
                    print (move_as_string(pos), eye_type),
                    for pos2 in self.iterate_neighbour_and_diagonal_neighbour(pos):
                        if self.goban[pos2]==EMPTY:
                            lambda1_area[pos2] = True
            print move_list_as_string(lambda1_area.keys())
            print self.as_sgf_with_labels(lambda1_area)
            if lambda1_area:
                block.lambda1_area = lambda1_area
        for block in self.iterate_blocks(EMPTY):
            if not hasattr(block, "lambda1_area"):
                continue
            for pos in block.lambda1_area:
                pass

    def quick_score_move(self, move, status_dict = {}):
        if self.goban[move]!=EMPTY:
            return WORST_SCORE #Illegal move
        old_score = 0.0
        new_score = 0.0
        lib_dict = {}
        stone_count = 1
        blocks_seen = {}
        save_count = 0
        captured_stones = {}
        neighbour_stones = {}
        dead_dict = {}
        for pos in self.iterate_neighbour(move):
            stone = self.goban[pos]
            if stone==EMPTY:
                lib_dict[pos] = True
                continue
            block = self.blocks[pos]
            if status_dict.get(pos)==TACTICALLY_DEAD and stone==other_side[self.side]:
                dead_dict[pos] = True
            origin = block.get_origin()
            if origin in blocks_seen:
                continue
            blocks_seen[origin] = True
            old_stone_count = len(block.stones)
            if stone==self.side:
                stone_count = stone_count + old_stone_count
                old_liberties, stone_list = self.list_block_liberties_and_stones(block)
                if len(old_liberties)==1:
                    save_count = save_count + old_stone_count
                for lib in old_liberties:
                    lib_dict[lib] = True
                old_dead_dict = {}
                for stone in stone_list:
                    neighbour_stones[stone] = True
                    if status_dict.get(stone)==TACTICALLY_DEAD:
                        old_dead_dict[stone] = True
                        dead_dict[stone] = True
                old_score = old_score + shape_score(old_stone_count, len(old_liberties) + 0.9*len(old_dead_dict))
            else: #opposite
                old_liberties_count = self.block_liberties(block)
                if old_liberties_count==1:
                    captured_stones.update(block.stones)
                elif old_liberties_count==2:
                    new_score = new_score + 0.3
                elif old_liberties_count==3:
                    new_score = new_score + 0.2
                elif old_liberties_count==4:
                    new_score = new_score + 0.1
                if pos in dead_dict:
                    ratio = 0.1
                else:
                    ratio = 1.0
                old_score = old_score - ratio * shape_score(old_stone_count, old_liberties_count)
                new_score = new_score - ratio * shape_score(old_stone_count, old_liberties_count-1)

        if move in lib_dict:
            del lib_dict[move]

        real_lib_dict = lib_dict.copy()
        real_lib_dict.update(captured_stones)
        if captured_stones:
            for stone in captured_stones:
                if stone in neighbour_stones:
                    if stone not in dead_dict:
                        lib_dict[stone] = True
        new_score = new_score + shape_score(stone_count, len(lib_dict) + len(dead_dict)*0.9)
        new_score = new_score + save_count
        if not status_dict:
             new_score = new_score + len(captured_stones)
             if save_count:
                 new_score = new_score + 1.5
        if len(real_lib_dict)==1:
            new_score = new_score - stone_count #self atari
        return new_score - old_score

    def score_position(self):
        if config.use_threads_scoring_system:
            return self.score_position_with_thread_liberties()
        #return self.score_position_with_threads()
        return self.score_position_with_liberties()
        #return self.score_position_with_oxygen()
