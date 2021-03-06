from scenic.simulators.gfootball.model import *
from scenic.simulators.gfootball.behaviors import *
from scenic.simulators.gfootball.simulator import GFootBallSimulator
from scenic.core.geometry import normalizeAngle
import pdb

param game_duration = 400
param deterministic = False
param offsides = False
param right_team_difficulty = 1
param end_episode_on_score = True
param end_episode_on_out_of_play = True
param end_episode_on_possession_change = True


behavior egoBehavior(destination_point):
	try:
		do dribbleToAndShoot(destination_point, reactionDistance=Range(1,5))
	interrupt when (distance from self to ball) > 2:
		do FollowObject(ball, sprint=True)
	do IdleBehavior()


RightGK
ego = RightCM on left_bottom_half_field, with behavior egoBehavior(-80 @ 0)
ball = Ball ahead of ego by 2

LeftGK with behavior HoldPosition()
left_defender = LeftCB left of ego by Range(5,10)

