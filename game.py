import string, random, sys, math, copy
import config
from const import *
from utils import *
from types import *

from chain import Chain
from board import Board
from pos_cache import *
from scored_move import ScoredMove

from game_search import GameSearch
from game_experimental import GameExperimental
from game_old import GameOld

class Game(GameSearch,GameExperimental,GameOld):
    """Game record and move generation

       Attributes:
       size: board size
       current_board: current board position
       move_history: past moves made
       undo_history: undo info for each past move
       position_seen: keeps track of position seen: this is used for super-ko detection
    """
    def __init__(self, size):
        """Initialize game:
           argument: size
        """
        self.size = size
        self.current_board = Board(size)
        self.move_history = []
        self.search_history = []
        self.status_history = []
        self.undo_history = []
        self.position_seen = {}
        self.position_seen[self.current_board.key()] = True
        GameSearch.__init__(self)
        GameExperimental.__init__(self)
        GameOld.__init__(self)

    def make_unchecked_move(self, move):
        """This is utility method.
           This does not check legality.
           It makes move in current_board and returns undo log and also key of new board
        """
        self.current_board.make_move(move)
        undo_log = self.current_board.undo_log[:]
        board_key = self.current_board.key()
        return undo_log, board_key

    def legal_move(self, move):
        """check whether move is legal
           return truth value
           first check move legality on current board
           then check for repetition (situational super-ko)
        """
        if move==PASS_MOVE:
            return True
        if not self.current_board.legal_move(move):
            return False
        undo_log, board_key = self.make_unchecked_move(move)
        self.current_board.undo_move(undo_log)
        if board_key in self.position_seen:
            return False
        return True

    def make_colored_move(self, color, move):
        if self.current_board.side!=color:
            self.make_move(PASS_MOVE)
        return self.make_move(move)
        
    def make_move(self, move):
        """make given move and return new board
           or return None if move is illegal
           First check move legality.
           This checks for move legality for itself to avoid extra make_move/make_undo.
           This is a bit more complex but maybe 2-3x faster.
           Then make move and update history.
        """
##        if hasattr(self, "ok_reading_shadow") and self.ok_reading_shadow!=self.reading_shadow['cut K16 N15 M15', (10, 16)]:
##            stop()
        if not self.current_board.legal_move(move):
            return None

        self.update_shadow(move)
        undo_log, board_key = self.make_unchecked_move(move)
        if move!=PASS_MOVE and board_key in self.position_seen:
            self.current_board.undo_move(undo_log)
            return None
        self.update_shadow(move)

        self.node_count = self.node_count + 1

        self.undo_history.append(undo_log)
        self.move_history.append(move)
        if hasattr(self, "search_dict"):
            self.search_history.append(self.search_dict)
        else:
            self.search_history.append({})
        if hasattr(self, "status_dict"):
            self.status_history.append(self.status_dict)
        else:
            self.status_history.append({})
        if move!=PASS_MOVE:
            self.position_seen[board_key] = True
        self.sgf_trace(move)
##        if hasattr(self, "ok_reading_shadow") and self.ok_reading_shadow!=self.reading_shadow['cut K16 N15 M15', (10, 16)]:
##            stop()
        return self.current_board

    def undo_move(self):
        """undo latest move and return current board
           or return None if at beginning.
           Update repetition history and make previous position current.
        """
##        if hasattr(self, "ok_reading_shadow") and self.ok_reading_shadow!=self.reading_shadow['cut K16 N15 M15', (10, 16)]:
##            stop()
        if not self.move_history: return None
        last_move = self.move_history.pop()
        self.search_history.pop()
        self.status_history.pop()
        if last_move!=PASS_MOVE:
            del self.position_seen[self.current_board.key()]
        last_undo_log = self.undo_history.pop()
        self.update_shadow(last_move)
        self.current_board.undo_move(last_undo_log)
        self.update_shadow(last_move)
        self.sgf_trace(UNDO_MOVE)
##        if hasattr(self, "ok_reading_shadow") and self.ok_reading_shadow!=self.reading_shadow[('cut K16 N15 M15'), (10, 16)]:
##            stop()
        return self.current_board

    def iterate_moves(self):
        """Go through all legal moves including pass move
        """
        yield PASS_MOVE
        for move in self.current_board.iterate_goban():
            if self.legal_move(move):
                yield move

    def move_as_string(self, move):
        return move_as_string(move, self.size)

    def move_list_as_string(self, move_list):
        return move_list_as_string(move_list, self.size)

    def move_dict_list_as_string(self, move_dict):
        s = []
        for move in move_dict:
            s.append("%s(%s)" % (self.move_as_string(move), self.move_list_as_string(move_dict[move])))
        return string.join(s)

    def symmetry_canonical_game_history(self):
        best = None
        best_func = None
        for ref in all_ref_coords:
            ref_moves = []
            for move in self.move_history:
                if move==PASS_MOVE:
                    ref_moves.append(move)
                else:
                    ref_moves.append(ref(move, self.size))
            if best==None or ref_moves < best:
                best = ref_moves
                best_func = ref
        return best, best_func
        

    def list_moves(self):
        """return all legal moves including pass move
        """
        all_moves = [PASS_MOVE]
        for move in self.current_board.iterate_goban():
            if self.legal_move(move):
                all_moves.append(move)
        return all_moves

    def has_2_passes(self):
        return len(self.move_history)>=2 and \
                   self.move_history[-1]==PASS_MOVE and \
                   self.move_history[-2]==PASS_MOVE
    
    def score_position(self):
        if self.use_tactics:
            return self.score_tactic_position()
        return self.current_board.score_position()

    def str_current_position(self):
        self.score_position()
        return self.current_board.as_string_with_unconditional_status(analyze=False)

    def analyse_dead_inside_dead(self, block):
        if block.status!=TACTICALLY_DEAD and block.status!=TACTICALLY_CRITICAL:
            return
        all_surrounding_dead = True
        origin = block.get_origin()
        opposite_color = other_side[block.color]
        for block2 in self.current_board.iterate_neighbour_blocks(block):
            if block2.color==EMPTY:
                for block3 in self.current_board.iterate_neighbour_blocks(block2):
                    if block3==block:
                        continue
                    if block3.color==opposite_color:
                        if block3.status!=TACTICALLY_DEAD:
                            all_surrounding_dead = False
                            break
                    elif block3.color==block.color:
                        if block3.status==TACTICALLY_DEAD:
                            all_surrounding_dead = False
                            break
            elif block2.color==opposite_color:
                if block2.status!=TACTICALLY_DEAD:
                    all_surrounding_dead = False
                    break
            elif block2.color==block.color:
                if block2.status==TACTICALLY_DEAD:
                    all_surrounding_dead = False
                    break
        if all_surrounding_dead:
            block.status = TACTICALLY_UNKNOWN
                

    def adjacent_to_interesting(self, pos, color):
        result = False
        cboard = self.current_board
        for pos2 in cboard.iterate_neighbour(pos):
            block = cboard.blocks[pos2]
            if block.color==color and self.status_dict[pos2]!=TACTICALLY_DEAD:
                result = True
        return result

    def select_tactically_scored_move(self, remove_opponent_dead=False, pass_allowed=True):
        """Go through all legal moves.
           Keep track of best score and all moves that achieve it.
           Select one move from best moves and return it.
        """
        node_count0 = self.node_count
        cboard = self.current_board
        territory_moves_forbidden = pass_allowed
        all_blocks_decided = True
        
        #tactical status
        base_score = self.score_tactic_position()
        if config.debug_flag:
            dprintnl(self.current_board.as_string_with_unconditional_status(analyze=False))
        attack_moves = {}
        reverse_attack_moves = {}
        defend_moves = {}
        danger_attack_moves = {}
        danger_defend_moves = {}
        undecided_liberties = {}
        self.status_dict = {}
        self.block_size_dict = {}
        self.search_dict = {}
        self.status_dict = {}
        for pos, status, attack_move, defend_move, danger_attack_score, danger_attack_move, danger_defend_score, danger_defend_move in self.status_list:
            block = cboard.blocks[pos]
            if (status in (TACTICALLY_CRITICAL, UNCONDITIONAL_UNKNOWN) and block.color in WHITE+BLACK) or \
                   (status in (TACTICALLY_LIVE, TACTICALLY_UNKNOWN) and block.color==cboard.side):
                all_blocks_decided = False
                for liberty in cboard.list_block_liberties(block):
                    undecided_liberties[liberty] = True
            for stone in block.stones:
                self.status_dict[stone] = status
                self.block_size_dict[stone] = block.size()
            if status==TACTICALLY_CRITICAL:
                if block.color==cboard.side:
                    defend_list = defend_moves.get(defend_move, [])
                    defend_list.append(block.get_origin())
                    defend_moves[defend_move] = defend_list
                else:
                    attack_list = attack_moves.get(attack_move, [])
                    attack_list.append(block.get_origin())
                    reverse_attack_moves[block.get_origin()] = attack_move
                    attack_moves[attack_move] = attack_list
            elif status in (TACTICALLY_LIVE, TACTICALLY_UNKNOWN):
                danger_attack_score, danger_attack_move, danger_defend_score, danger_defend_move
                if block.color==cboard.side:
                    defend_list = danger_defend_moves.get(danger_defend_move, [])
                    defend_list.append((block.get_origin(), danger_defend_score))
                    danger_defend_moves[danger_defend_move] = defend_list
                else:
                    attack_list = danger_attack_moves.get(danger_attack_move, [])
                    attack_list.append((block.get_origin(), danger_attack_score))
                    danger_attack_moves[danger_attack_move] = attack_list
        
        if config.debug_flag:
            dprintnl("?", base_score)
            dprintnl("defend_moves:", self.move_dict_list_as_string(defend_moves))
            dprintnl("attack_moves:", self.move_dict_list_as_string(attack_moves))
        #if abs(base_score)==self.size**2:
        #    import pdb; pdb.set_trace()
        has_unknown_status_block = cboard.has_block_status(WHITE+BLACK+EMPTY, UNCONDITIONAL_UNKNOWN)
        has_opponent_dead_block = cboard.has_block_status(other_side[cboard.side], UNCONDITIONAL_DEAD)

        #goal: blocks attacked
        self.target_blocks = []
        if len(self.move_history)>=3:
            prev_our_move = self.move_history[-2]
            if prev_our_move!=PASS_MOVE:
                for pos in self.current_board.iterate_neighbour(prev_our_move):
                    block = self.current_board.blocks[pos]
                    if block.get_origin() in self.target_blocks:
                        continue
                    if block.color==other_side[cboard.side] and block.status in (TACTICALLY_LIVE, TACTICALLY_UNKNOWN, TACTICALLY_CRITICAL):
                        self.target_blocks.append(block.get_origin())

        #has unsettled blocks
        if has_unknown_status_block and not self.use_tactics:
            pass_allowed = False
        #dead removal has been requested and there are dead opponent stones
        if remove_opponent_dead and has_opponent_dead_block:
            territory_moves_forbidden = False
            pass_allowed = False

        if territory_moves_forbidden:
            forbidden_moves = cboard.territory_as_dict()
        else:
            forbidden_moves = {}
        all_moves_dead = True
        move_values = []
        for move in self.iterate_moves():
            if move in forbidden_moves:
                continue
            if move==PASS_MOVE:
                continue
            score = cboard.quick_score_move(move, status_dict = self.status_dict)
            if config.debug_flag>1:
                dprintnl("Shape score:", move_as_string(move), score)
            is_urgent = False
            if move in attack_moves:
                is_urgent = True
                for origin in attack_moves[move]:
                    score += cboard.blocks[origin].size()
            save_extra_bonus = 1.5
            defend_list = []
            if move in defend_moves:
                is_urgent = True
                for origin in defend_moves[move]:
                    defend_list.append(origin)
                    score += cboard.blocks[origin].size() + save_extra_bonus
                    save_extra_bonus = 0 #give extra bonus only once for each move
            if move in danger_attack_moves:
                is_urgent = True
                for origin, ratio in danger_attack_moves[move]:
                    score += cboard.blocks[origin].size() * ratio
            if move in danger_defend_moves:
                is_urgent = True
                for origin, ratio in danger_defend_moves[move]:
                    score += cboard.blocks[origin].size() * ratio
                
            #consistency target bonus
            for origin in self.target_blocks:
                block = cboard.blocks[origin]
                if block.color==EMPTY:
                    continue
                if move in block.neighbour:
                    bonus = 2.0 / cboard.block_liberties(block)
                    if config.debug_flag:
                        dprintnl("goal bonus:", bonus, move_as_string(origin, self.size))
                    score = score + bonus
            #store
            smove = ScoredMove(move, score)
            smove.tactics_done = False
            smove.is_urgent = is_urgent
            smove.defend_list = defend_list
            move_values.append(smove)

        if config.debug_flag>1:
            move_values.sort()
            move_values.reverse()
            dprintsp("?")
            for smove in move_values:
                dprintsp(smove)
            dprintnl()
            dprintnl("total node count:", self.node_count - node_count0)
        #let only actual moves played on board affect reading shadow caching
        backup_reading_shadow = copy.deepcopy(self.reading_shadow)
        backup_reading_shadow_goban = copy.deepcopy(self.reading_shadow_goban)
        while move_values:
            move_values.sort()
            move_values.reverse()
            smove = move_values[0]
            if smove.tactics_done:
                break_flag = True
                #see if any neighbour point would be better...
                default_nodes = config.lambda_node_limit
                config.lambda_node_limit = default_nodes / 2
                moves_to_check = list(cboard.iterate_neighbour(smove.move))
                #search for attack points of surrounding groups
                for defend_pos in smove.defend_list:
                    block = cboard.blocks[defend_pos]
                    for block2 in cboard.iterate_neighbour_blocks(block):
                        origin2 = block2.get_origin()
                        if origin2 in reverse_attack_moves:
                            move = reverse_attack_moves[origin2]
                            if move not in moves_to_check:
                                moves_to_check.append(move)
##                for defend_pos in smove.defend_list:
##                    block = cboard.blocks[defend_pos]
##                    for block2 in cboard.iterate_neighbour_blocks(block):
##                        liberties = cboard.list_block_liberties(block2)
##                        if len(liberties)==1:
##                            if liberties[0] not in moves_to_check:
##                                moves_to_check.append(liberties[0])
                
                for pos in moves_to_check:
                    for smove2 in move_values:
                        if pos==smove2.move:
                            if smove2.defend_list:
                                save_extra_bonus = 0.0
                            else:
                                save_extra_bonus = 1.5
                            move2 = smove2.move
                            self.make_move(move2)
                            defend_additions = []
                            for defend_pos in smove.defend_list:
                                if defend_pos not in smove2.defend_list:
                                    if config.debug_flag:
                                        dprintnl("alternative defend?", move_list_as_string([smove.move, pos, defend_pos]))
                                    nodes0 = self.node_count
                                    status, attack_move, defend_move = self.all_block_tactic_status(defend_pos)
                                    nodes = self.node_count - nodes0
                                    smove2.nodes = smove2.nodes + nodes
                                    if status not in (TACTICALLY_LIVE, TACTICALLY_UNKNOWN):
                                        break
                                    defend_additions.append(defend_pos)
                            else:
                                if defend_additions:
                                    break_flag = False
                                    smove2.score = smove2.score + save_extra_bonus 
                                    for defend_pos in defend_additions:
                                        smove2.is_urgent = True
                                        smove2.defend_list.append(defend_pos)
                                        smove2.score = smove2.score + cboard.blocks[defend_pos].size()
                                        if smove2.move in cboard.blocks[defend_pos].stones:
                                            #don't give extra 1.0 bonus for contact moves: leads to bad shapes!
                                            smove2.score = smove2.score - 1
                            self.undo_move()
                config.lambda_node_limit = default_nodes
                if break_flag:
                    break
                else:
                    continue
            move = smove.move
            self.make_move(move)
            nodes0 = self.node_count
            status, attack_move, defend_move = self.all_block_tactic_status(move)
            nodes = self.node_count - nodes0
            smove.tactical_status = status
            smove.nodes = smove.nodes + nodes
            block = cboard.blocks[move]
            if status==TACTICALLY_DEAD:
                smove.score = smove.score - block.size() - 3.0
                if not smove.is_urgent:
                    if move in undecided_liberties:
                        smove.score = smove.score - 50.0
                    else:
                        smove.score = smove.score - 100.0
            elif status==TACTICALLY_CRITICAL:
                smove.score = smove.score - block.size() / 2.0 - 2.0
                if not smove.is_urgent:
                    if move in undecided_liberties:
                        smove.score = smove.score - 10.0
                    else:
                        smove.score = smove.score - 20.0
            self.undo_move()
            self.current_shadow_origin = PASS_MOVE
            if smove.tactical_status!=TACTICALLY_DEAD:
                all_moves_dead = False
            smove.tactics_done = True

            
        for smove in move_values:
            self.search_dict[smove.move] = smove.score, str(smove)
        self.reading_shadow = copy.deepcopy(backup_reading_shadow)
        self.reading_shadow_goban = copy.deepcopy(backup_reading_shadow_goban)
            
        if config.debug_flag:
            dprintsp("!")
            for smove in move_values:
                dprintsp(smove)
            dprintnl()
            dprintnl("total node count:", self.node_count - node_count0)
        self.available_moves = move_values
        if all_blocks_decided and all_moves_dead and pass_allowed:
            if config.debug_flag:
                dprintnl("!pass forced")
            return PASS_MOVE
        if len(move_values)==0:
            return PASS_MOVE

        #check for unconditional gains if no urgent moves
        #unconditional gain must be > 1 or adjacent to non dead opponent stone
        #if currently selected move is urgent or adjacent to non dead opponent stone this analysis is not done
        smove = move_values[0]
        if not smove.is_urgent and not self.adjacent_to_interesting(smove.move, other_side[cboard.side]):
            current_score = cboard.unconditional_score(cboard.side)
            best_score = WORST_SCORE
            best_move = PASS_MOVE
            for smove in move_values:
                move = smove.move
                has_nearby_our_stone = False
                for pos in cboard.iterate_neighbour_and_diagonal_neighbour(move):
                    if cboard.goban[pos]==cboard.side:
                        has_nearby_our_stone = True
                        break
                if has_nearby_our_stone and self.make_move(move):
                    score = cboard.unconditional_score(other_side[cboard.side]) - current_score
                    score2 = smove.score + score
                    if (score > 1 or (score==1 and self.adjacent_to_interesting(move, cboard.side))) and score2 > best_score:
                        best_score = score2
                        best_move = move
                    self.undo_move()
                    
            
            self.reading_shadow = copy.deepcopy(backup_reading_shadow)
            self.reading_shadow_goban = copy.deepcopy(backup_reading_shadow_goban)
            if best_move != PASS_MOVE:
                if config.debug_flag:
                    dprintnl("unconditional move:", move_as_string(best_move), best_score)
                return best_move

        return move_values[0].move

    def plain_key(self):
        cb = self.current_board
        key = [cb.side]
        stone_list = []
        for pos in cb.iterate_goban():
            stone_list.append(cb.goban[pos])
        key.append(string.join(stone_list, ""))
        key.append(move_as_string(cb.ko_flag, self.size))
        decided_score = cb.unconditional_score(WHITE + BLACK)
        key = key + map(str, decided_score)
        return string.join(key)

    def set_board_from_plain_key(self, key):
        cb = self.current_board
        cb.side = key[0]
        i = 2
        for pos in cb.iterate_goban():
            cb.add_stone(key[i], pos)
            i = i + 1
        

    def score_tactic_position(self):
        cboard = self.current_board
        #print cboard
        cboard.analyze_unconditional_status()
        if config.use_oxygen:
            cboard.oxygen = cboard.oxygen_influence()

        block_pos_lst = []
        for block in cboard.iterate_blocks(BLACK+WHITE+EMPTY):
            block_pos_lst.append([block.get_origin(), block.status, PASS_MOVE, PASS_MOVE, 0.0, PASS_MOVE, 0.0, PASS_MOVE])

        for i in range(len(block_pos_lst)):
            pos, status = block_pos_lst[i][:2]
            if status==UNCONDITIONAL_UNKNOWN and cboard.goban[pos]!=EMPTY:
                nodes0 = self.node_count
                status, attack_move, defend_move = self.block_tactic_status(pos)
                nodes_add = self.node_count-nodes0
                #if nodes_add:
                #    print self.move_as_string(pos), nodes_add, status, self.move_as_string(attack_move), self.move_as_string(defend_move)
                block_pos_lst[i][1] = status
                block_pos_lst[i][2] = attack_move
                block_pos_lst[i][3] = defend_move
                if self.use_lambda and self.block_extra_result:
                    block_pos_lst[i][4] = self.block_extra_result[1]
                    block_pos_lst[i][5] = self.block_extra_result[2]
                    block_pos_lst[i][6] = self.block_extra_result[3]
                    block_pos_lst[i][7] = self.block_extra_result[4]

        for pos, status, attack_move, defend_move, t1, t2, t3, t4 in block_pos_lst:
            block = cboard.blocks[pos]
            block.status = status
            block.attack_move = attack_move
            block.defend_move = defend_move

        #heuristical dead analysis
        if self.use_ld_search:
            result_dict = self.heuristical_dead_analysis()
            for i in range(len(block_pos_lst)):
                pos = block_pos_lst[i][0]
                if pos in result_dict:
                    status, attack_move, defend_move = result_dict[pos]
                    block_pos_lst[i][1] = status
                    block_pos_lst[i][2] = attack_move
                    block_pos_lst[i][3] = defend_move
                    block = cboard.blocks[pos]
                    block.status = status
                    block.attack_move = attack_move
                    block.defend_move = defend_move

        for block in cboard.iterate_blocks(BLACK+WHITE):
            self.analyse_dead_inside_dead(block)

        if config.use_chains:
            self.form_chains()
            score = 0
            for block in cboard.iterate_blocks(EMPTY):
                score = score + cboard.score_block(block)
            for chain in self.chains:
                score = score + self.score_chain(chain)
        else:
            score = 0
            for block in cboard.iterate_blocks(BLACK+WHITE+EMPTY):
                score = score + cboard.score_block(block)

        self.status_list = block_pos_lst
        return score
        

    def place_free_handicap(self, count):
        result = []
        handicap_stones = handicap_list(self.size, count)
        if handicap_stones:
            for move_str in handicap_stones:
                move = string_as_move(move_str, self.size)
                result.append(move)
                if self.current_board.side==WHITE:
                    self.make_move(PASS_MOVE)
                self.make_move(move)
            return result
        
        move_candidates = []
        for move in self.current_board.iterate_goban():
            if self.current_board.is_3x3_empty(move):
                move_candidates.append(move)

        while len(result) < count:
            if self.current_board.side==WHITE:
                self.make_move(PASS_MOVE)
            if move_candidates:
                move = random.choice(move_candidates)
            else:
                move = PASS_MOVE
            #check if heuristics is correct, if not, then we use normal move generation routine
            current_score = self.current_board.score_position()
            score_diff = -self.score_move(move) - current_score
            #0.001: because floating point math is inaccurate
            if score_diff + 0.001 < normal_stone_value_ratio:
                if config.debug_flag:
                    dprintnl(self.current_board)
                    dprintnl(move, score_diff)
                if self.use_lambda:
                    move = self.select_tactically_scored_move(pass_allowed=False)
                else:
                    move = self.select_scored_move(pass_allowed=False)
            if self.make_move(move):
                result.append(move)
            if move in move_candidates:
                move_candidates.remove(move)
        return result

    def place_free_handicap_new(self, count):
        result = []
        while len(result) < count:
            if self.current_board.side==WHITE:
                self.make_move(PASS_MOVE)
            self.current_board.calculate_distance_to_stones_or_edge()
            dist = self.current_board.liberty_distance
            max_dist = max(dist.values())
            moves = []
            for pos in dist:
                if dist[pos]==max_dist:
                    moves.append(pos)
            if moves:
                move = random.choice(moves)
            else:
                move = PASS_MOVE
            #check if heuristics is correct, if not, then we use normal move generation routine
            current_score = self.current_board.score_position()
            score_diff = -self.score_move(move) - current_score
            #0.001: because floating point math is inaccurate
            if score_diff + 0.001 < normal_stone_value_ratio:
                if config.debug_flag:
                    dprintnl(self.current_board)
                    dprintnl(move, score_diff)
                move = self.select_scored_move(pass_allowed=False)
            if self.make_move(move):
                result.append(move)
        return result
        

    def final_status_list(self, status):
        """list blocks with given color and status
        """
        result_list = []
        if self.use_tactics:
            self.score_position()
            for block in self.current_board.iterate_blocks(WHITE+BLACK):
                if status in block.status:
                    result_list.append(block.get_origin())
        else:
            self.current_board.analyze_unconditional_status()
            for block in self.current_board.iterate_blocks(WHITE+BLACK):
                if block.status==status:
                    result_list.append(block.get_origin())
        return result_list

    def select_random_move(self):
        """return randomly selected move from all legal moves
        """
        return random.choice(self.list_moves())

    def generate_move(self, remove_opponent_dead=False, pass_allowed=True):
        """generate move using scored move generator
        """
        #return self.select_random_move()
        if self.use_lambda:
            return self.select_tactically_scored_move(remove_opponent_dead, pass_allowed)
        else:
            return self.select_scored_move(remove_opponent_dead, pass_allowed)

    def as_image(self):
        cboard = self.current_board
        s = ["P2\n# CREATOR: SimpleGo Fast Idiot\n%i\n%i\n255\n" % (self.size, self.size)]
        for y in range(self.size, 0, -1):
            for x in range(1, self.size+1):
                pos = x,y
                color = 128
                if cboard.goban[pos]==WHITE:
                    color = 255
                elif cboard.goban[pos]==BLACK:
                    color = 0
                else:
                    for pos2 in cboard.iterate_neighbour(pos):
                        if cboard.goban[pos2]==WHITE:
                            color = 192
                            break
                        elif cboard.goban[pos2]==BLACK:
                            color = 64
                            break
                s.append("%i\n" % color)
        return string.join(s, "")

    def as_color_image(self):
        cboard = self.current_board
        s = ["P3\n# CREATOR: SimpleGo Fast Idiot\n%i\n%i\n255\n" % (self.size, self.size)]
        age = {}
        game_age = len(self.move_history)
        for i in range(game_age):
            move = self.move_history[i]
            age[move] = 1.0 * i / game_age

        def pos2color(pos, cboard=cboard):
            if cboard.goban[pos]==WHITE:
                r = 0
                g = age[pos] * 255
                b = 255
            elif cboard.goban[pos]==BLACK:
                r = 255
                g = age[pos] * 255
                b = 0
            else:
                r = g = b = 128
            return r,g,b

        for y in range(self.size, 0, -1):
            for x in range(1, self.size+1):
                pos = x,y
                if cboard.goban[pos]==EMPTY:
                    num = 0
                    r = g = b = 0
                    for pos2 in cboard.iterate_neighbour(pos):
                        r2, g2, b2 = pos2color(pos2)
                        num = num + 1
                        r = r + r2
                        g = g + g2
                        b = b + b2
                    r = r / num
                    g = g / num
                    b = b / num
                else:
                    r, g, b = pos2color(pos)
                s.append("%i\n%i\n%i\n" % (r, g, b))
        return string.join(s, "")

    def __str__(self):
        s = ["(;GM[1]SZ[%i]RU[Chinese]" % self.size]
        for i in range(len(self.move_history)):
            if i%2:
                color = ";W"
            else:
                color = ";B"
            move = self.move_history[i]
            scores = self.search_history[i]
            if i+1<len(self.move_history):
                status_dict = self.status_history[i+1]
            else:
                status_dict = self.status_history[i]
            sgf = move_as_sgf(move, self.size)
            if move==PASS_MOVE:
                s.append("%s[%s]" % (color, sgf))
            else:
                s.append("%s[%s]CR[%s]" % (color, sgf, sgf))
            slabel = ["LB"]
            scomment = ["C["]
            max_score = -1
            min_score = 1
            for pos in scores:
                max_score = max(max_score, scores[pos][0])
                min_score = min(min_score, scores[pos][0])
            if max_score<=0:
                if min_score>=0:
                    max_score = 1.0
                else:
                    max_score = -min_score / 0.99
            label_used = {}
            score_list = []
            for pos in scores:
                score_list.append((scores[pos][0], pos))
                score = 100.0 * scores[pos][0]/max_score
                if pos==PASS_MOVE:
                    scomment.append("Pass normalized: %s\n" % score)
                else:
                    if scores[pos][0]==max_score and pos==move:
                        scomment.append("Top move normalized: %s: %s\n" % (self.move_as_string(pos), score))
                    slabel.append("[%s:%s]" % (move_as_sgf(pos, self.size), score))
                    label_used[pos] = True
            score_list.sort()
            score_list.reverse()
            for score, pos in score_list:
                if scores[pos][1]:
                    if type(scores[pos][1])==StringType:
                        scomment.append("%s: %s\n" % (self.move_as_string(pos), scores[pos][1]))
                    else:
                        scomment.append("%s: %s\n" % (self.move_list_as_string(scores[pos][1]), score))
                else:
                    scomment.append("%s: %s\n" % (self.move_as_string(pos), score))
            
            for pos in status_dict:
                if pos in label_used:
                    continue
                status = status_dict[pos]
                lb = ""
                if status==UNCONDITIONAL_LIVE:
                    lb = "@"
                elif status==UNCONDITIONAL_DEAD:
                    lb = "."
                elif status==WHITE_UNCONDITIONAL_TERRITORY:
                    lb = "="
                elif status==BLACK_UNCONDITIONAL_TERRITORY:
                    lb = ":"
                elif status==TACTICALLY_LIVE:
                    lb = "*"
                elif status==TACTICALLY_DEAD:
                    lb = "X"
                elif status==TACTICALLY_CRITICAL:
                    lb = "!"
                if lb:
                    slabel.append("[%s:%s]" % (move_as_sgf(pos, self.size), lb))
            if len(slabel)>1:
                s.append(string.join(slabel, ""))
            if len(scomment)>1:
                scomment.append("]")
                s.append(string.join(scomment, ""))
        s.append(")")
        return string.join(s, "\n")
