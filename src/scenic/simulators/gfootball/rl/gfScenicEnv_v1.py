from random import randint

import gfootball
import gym
# from scenic.simulators.gfootball.rl import pfrl_training

from gfootball.env import football_action_set

# Curriculum Learning usinf rllib: https://docs.ray.io/en/latest/rllib-training.html#curriculum-learning
from scenic.simulators.gfootball.utilities import scenic_helper
from scenic.simulators.gfootball.utilities.scenic_helper import buildScenario

"""Single Agent Interface"""
class GFScenicEnv_v1(gym.Env):
	metadata = {'render.modes': ['human']}

	def __init__(self, initial_scenario, gf_env_settings={}, allow_render = False, compute_scenic_behavior=False, rank=0):
		super(GFScenicEnv_v1, self).__init__()

		self.compute_scenic_behavior = compute_scenic_behavior
		self.gf_env_settings = gf_env_settings
		self.allow_render = allow_render
		self.scenario = initial_scenario
		self.rank = rank

		from gym.spaces.discrete import Discrete
		from gym.spaces import Box
		from numpy import uint8

		#assert self.gf_env_settings["action_set"] == "default" or use_scenic_behavior_in_step
		assert self.gf_env_settings["representation"] == "extracted"
		assert self.gf_env_settings["stacked"] == True

		self.observation_space = Box(low=0, high=255, shape=(72, 96, 16), dtype=uint8)

		#if self.compute_scenic_behavior:
		self.action_space = Discrete(19)



	def reset(self):
		self.scene, _ = scenic_helper.generateScene(self.scenario)

		if hasattr(self, "simulation"): self.simulation.get_underlying_gym_env().close()

		from scenic.simulators.gfootball.simulator import GFootBallSimulation
		self.simulation = GFootBallSimulation(scene=self.scene, settings={}, for_gym_env=True,
											  render=self.allow_render, verbosity=1,
											  env_type="v1",
											  gf_env_settings=self.gf_env_settings,
											  tag=str(self.rank))

		self.gf_gym_env = self.simulation.get_underlying_gym_env()

		obs = self.simulation.reset()
		#player_idx = self.simulation.get_controlled_player_idx()[0]

		if self.compute_scenic_behavior:
			self.simulation.pre_step()

		return obs

	#def filter_obs(self, obs):


	def step(self, action):
		# Execute one time step within the environment

		#assert isinstance(action, int), "action must be int"
		assert action != 19, "Cannot take built in ai action for rl!"
		#if action == 19: print("Using BUILT IN AI!!!!!")

		obs, rew, done, info = self.simulation.step(action)

		if self.compute_scenic_behavior:
			self.simulation.post_step()
			if not done: self.simulation.pre_step() #For computing the actions before step is called

		return obs, rew, done, info

	def render(self, mode='human', close=False):
		# Render the environment to the screen
		# For weird pygame rendering issue on Mac, rendering must be called in utilities/env_creator/create_environment
		return None


def read_single_obs(obs):

	import numpy as np


	def get_pos(plane):
		pos = []
		nz = np.nonzero(plane)
		n = int(nz[0].shape[0])
		for i in range(n):
			x = nz[0][i]
			y = nz[1][i]
			pos.append((x,y))
		return pos

	last_frame = obs[:, :, -4:]

	left_plane = last_frame[:, :, 0]
	left_team = get_pos(left_plane)

	right_team = get_pos(last_frame[:,:,1])
	ball = get_pos(last_frame[:,:,2])
	active_player = get_pos(last_frame[:,:,3])

	def convert_to_scenic_coordinate(points, frame_x = 96, frame_y = 72):

		cpoints = []
		for point in points:
			y = -1*84.0/frame_y*(point[0]+0.5) + 42
			x = 200.0/frame_x*(point[1]+0.5) -100.0
			cpoints.append((x,y))


		return cpoints

	left_team = convert_to_scenic_coordinate(left_team)
	right_team = convert_to_scenic_coordinate(right_team)
	active_player = convert_to_scenic_coordinate(active_player)
	ball = convert_to_scenic_coordinate(ball)

	frame_y=72
	frame_x=96
	dx = 84.0 / frame_y / 2
	dy = 200.0 / frame_x / 2
	dxdy = (dx,dy)

	return  left_team, right_team, ball, active_player, dxdy



def test_observation():
	pass

	import os

	cwd = os.getcwd()

	gf_env_settings = {
		"stacked": True,
		"rewards": 'scoring',
		"representation": 'extracted',
		"players": [f"agent:left_players=1"],
		"real_time": True
	}

	from scenic.simulators.gfootball.rl.gfScenicEnv_v2 import GFScenicEnv_v2

	num_trials = 1
	scenario_file = f"/Users//codebase/scenic/examples/gfootball/monologue.scenic"
	scenario = buildScenario(scenario_file)

	compute_scenic_behavior = True

	env = GFScenicEnv_v1(initial_scenario=scenario, gf_env_settings=gf_env_settings, allow_render=True, compute_scenic_behavior=compute_scenic_behavior)

	from scenic.simulators.gfootball.rl import utils

	def pretty_floats(ls):
		s = ""
		i=0
		while i<len(ls):
			x = ls[i][0]
			y = ls[i][1]
			s += f"({x:.2f}, {y:.2f})  "
			i+=1
		return s

	#import numpy as np
	#np.set_printoptions(precision=2)
	num_epi = 0
	total_r = 0
	from tqdm import tqdm
	for i in tqdm(range(0, num_trials)):
		obs = env.reset()
		assert obs.shape == (72,96,16)
		done = False
		# input("Enter")
		while not done:

			if not compute_scenic_behavior:
				action = env.action_space.sample()
			else:
				action = env.simulation.get_scenic_designated_player_action()

			obs, reward, done, info = env.step(action)
			assert obs.shape == (72, 96, 16)
			left_team, right_team, ball, active_player, dxdy = read_single_obs(obs)

			print("Active Player: ", pretty_floats(active_player))
			#print("Left Team: ", pretty_floats(left_team))
			#print("Right Team: ", pretty_floats(right_team))
			print()
			# env.render()
			total_r += reward
			if done:
				obs = env.reset()
				num_epi += 1

	perf =  total_r / num_epi
	print("random agent performance: ", perf)



if __name__=="__main__":
	test_observation()