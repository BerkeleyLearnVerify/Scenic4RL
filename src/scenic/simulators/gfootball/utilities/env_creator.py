from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import gfootball
import gym
import pygame
from gfootball.env import config
from gfootball.env import football_env
from gfootball.env import observation_preprocessing
from gfootball.env import wrappers

"""
Modified from gfootball/env/__init__.py/create_environment
"""

"""
A wrapper which saves the raw state for scenic, the simulator can access `latest_raw_observation` field to read the latest raw observation after reset or step
"""
class ScenicWrapper(gym.ObservationWrapper):

    def __init__(self, env):
        gym.ObservationWrapper.__init__(self, env)
        #self.simulation_obj = simulation_obj

    def observation(self, observation):
        self.latest_raw_observation = observation
        return observation

def create_environment(env_name='',
                       settings={},
                       render = False):
    """Creates a Google Research Football environment.

    Args:
      env_name: a name of a scenario to run, e.g. "11_vs_11_stochastic".
        The list of scenarios can be found in directory "scenarios".
      stacked: If True, stack 4 observations, otherwise, only the last
        observation is returned by the environment.
        Stacking is only possible when representation is one of the following:
        "pixels", "pixels_gray" or "extracted".
        In that case, the stacking is done along the last (i.e. channel)
        dimension.
      representation:
          None: Do not apply wrapper
        String to define the representation used to build
        the observation. It can be one of the following:
        'pixels': the observation is the rendered view of the football field
          downsampled to 'channel_dimensions'. The observation size is:
          'channel_dimensions'x3 (or 'channel_dimensions'x12 when "stacked" is
          True).
        'pixels_gray': the observation is the rendered view of the football field
          in gray scale and downsampled to 'channel_dimensions'. The observation
          size is 'channel_dimensions'x1 (or 'channel_dimensions'x4 when stacked
          is True).
        'extracted': also referred to as super minimap. The observation is
          composed of 4 planes of size 'channel_dimensions'.
          Its size is then 'channel_dimensions'x4 (or 'channel_dimensions'x16 when
          stacked is True).
          The first plane P holds the position of players on the left
          team, P[y,x] is 255 if there is a player at position (x,y), otherwise,
          its value is 0.
          The second plane holds in the same way the position of players
          on the right team.
          The third plane holds the position of the ball.
          The last plane holds the active player.
        'simple115'/'simple115v2': the observation is a vector of size 115.
          It holds:
           - the ball_position and the ball_direction as (x,y,z)
           - one hot encoding of who controls the ball.
             [1, 0, 0]: nobody, [0, 1, 0]: left team, [0, 0, 1]: right team.
           - one hot encoding of size 11 to indicate who is the active player
             in the left team.
           - 11 (x,y) positions for each player of the left team.
           - 11 (x,y) motion vectors for each player of the left team.
           - 11 (x,y) positions for each player of the right team.
           - 11 (x,y) motion vectors for each player of the right team.
           - one hot encoding of the game mode. Vector of size 7 with the
             following meaning:
             {NormalMode, KickOffMode, GoalKickMode, FreeKickMode,
              CornerMode, ThrowInMode, PenaltyMode}.
           Can only be used when the scenario is a flavor of normal game
           (i.e. 11 versus 11 players).
      rewards: Comma separated list of rewards to be added.
         Currently supported rewards are 'scoring' and 'checkpoints'.
      write_goal_dumps: whether to dump traces up to 200 frames before goals.
      write_full_episode_dumps: whether to dump traces for every episode.
      render: whether to render game frames.
         Must be enable when rendering videos or when using pixels
         representation.
      write_video: whether to dump videos when a trace is dumped.
      dump_frequency: how often to write dumps/videos (in terms of # of episodes)
        Sub-sample the episodes for which we dump videos to save some disk space.
      logdir: directory holding the logs.
      extra_players: A list of extra players to use in the environment.
          Each player is defined by a string like:
          "$player_name:left_players=?,right_players=?,$param1=?,$param2=?...."
      number_of_left_players_agent_controls: Number of left players an agent
          controls.
      number_of_right_players_agent_controls: Number of right players an agent
          controls.
      channel_dimensions: (width, height) tuple that represents the dimensions of
         SMM or pixels representation.
      settings: dict that allows directly setting other options in
         the Config
    Returns:
      Google Research Football environment.
    """


    #simulation_obj=None
    #stacked=False
    #representation=None
    #rewards='scoring'
    """For now keep it fixed, would need to change once multi agent training is started"""
    #number_of_left_players_agent_controls=1
    #number_of_right_players_agent_controls=0
    """"""

    channel_dimensions=(
           observation_preprocessing.SMM_WIDTH,
           observation_preprocessing.SMM_HEIGHT)
    assert env_name

    settings["level"]=env_name
    #render = settings["render"]
    if "representation" in settings:
        representation = settings["representation"]
    else: representation=None

    rewards = settings["rewards"]
    stacked = settings["stacked"]
    dump_frequency = settings["dump_frequency"]

    number_of_left_players_agent_controls = settings["internal_control_left"]
    number_of_right_players_agent_controls = settings["internal_control_right"]

    #scenario_config = config.Config({'level': env_name}).ScenarioConfig()
    """
    players = [('agent:left_players=%d,right_players=%d' % (
        number_of_left_players_agent_controls,
        number_of_right_players_agent_controls))]
    
    # Enable MultiAgentToSingleAgent wrapper?
    multiagent_to_singleagent = False
    if scenario_config.control_all_players:
        if (number_of_left_players_agent_controls in [0, 1] and
                number_of_right_players_agent_controls in [0, 1]):
            multiagent_to_singleagent = True
            players = [('agent:left_players=%d,right_players=%d' %
                        (scenario_config.controllable_left_players
                         if number_of_left_players_agent_controls else 0,
                         scenario_config.controllable_right_players
                         if number_of_right_players_agent_controls else 0))]
    

    if extra_players is not None:
        players.extend(extra_players)
    
    config_values = {
        'dump_full_episodes': write_full_episode_dumps,
        'dump_scores': write_goal_dumps,
        'players': players,
        'level': env_name,
        'tracesdir': logdir,
        'write_video': write_video,
    }
    """
    config_values = {}
    config_values.update(settings)
    c = config.Config(config_values)

    env = football_env.FootballEnv(c)

    env = ScenicWrapper(env)
    scenic_wrapper = env
    """
    if multiagent_to_singleagent:
        env = wrappers.MultiAgentToSingleAgent(
            env, number_of_left_players_agent_controls,
            number_of_right_players_agent_controls)
    """
    if dump_frequency > 1:
        env = wrappers.PeriodicDumpWriter(env, dump_frequency, render)
    #elif render:
    #    env.render()

    if representation is not None:
        env = gfootball.env._apply_output_wrappers(
            env, rewards, representation, channel_dimensions,
            (number_of_left_players_agent_controls +
             number_of_right_players_agent_controls == 1), stacked)


    if render:
        pygame.display.set_mode((1, 1), pygame.NOFRAME)
        env.render()
        pygame.display.set_mode((1, 1), pygame.NOFRAME)

    return env, scenic_wrapper
