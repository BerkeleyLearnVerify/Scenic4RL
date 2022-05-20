from scenic.simulators.gfootball.model import *
from scenic.simulators.gfootball.simulator import GFootBallSimulator

param game_duration = 400
param deterministic = False
param offsides = False
param end_episode_on_score = True
param end_episode_on_out_of_play = True
param end_episode_on_possession_change = True


ego = Ball at 70 @ 28

LeftGK at -99 @ 0
LeftCB at 70 @ 0
LeftCB at 70 @ 30

RightGK at 99 @ 0
RightCB at 75 @ 30