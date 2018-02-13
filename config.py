import sys
debug_flag = True
debug_output = sys.stderr

use_threads_scoring_system = False
use_nth_order_liberties = 3 #10
use_nth_order_liberties = 0
use_oxygen = False

use_tactics = True
use_lambda = use_tactics and True
debug_tactics = False
sgf_trace_tactics = False
use_shadow_cache = True
#slower settings
#lambda_node_limit = 100
#lambda_slow_node_limit = 3
#lambda_connection_node_limit = 30
#faster setting
lambda_node_limit = 50
lambda_slow_node_limit = 1
lambda_connection_node_limit = 10
capture_lambda1_factor_limit = 10 #multiplied with above gives 1000
min_capture_lambda1_nodes = 5000 #needed, sometimes 1000 nodes is not enough and this is fatal
other_lambda1_factor_limit = 2

# time management settings
time_per_move_limit = 25
manage_time = False
statistics_limit = 20

lambda_limit = 10
use_pn_search = True #Proof number search
use_ld_search = True #Life and death search
lambda_depth_limit = 10001
danger_move_limit = 5

use_chains = False

purely_random_no_eye_fill = False
always_remove_opponent_dead = False
