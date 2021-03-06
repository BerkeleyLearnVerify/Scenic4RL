#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright 2019 Google LLC
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Runs football_env on OpenAI's ppo2."""

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import multiprocessing
import os
from absl import app
from absl import flags
from baselines import logger
#from baselines.bench import monitor
from gfrl.common.mybase import monitor

from baselines.common.vec_env.subproc_vec_env import SubprocVecEnv
#from baselines.ppo2 import ppo2
import gfootball.env as football_env
from gfootball.examples import models

FLAGS = flags.FLAGS

flags.DEFINE_string('level', 'academy_empty_goal_close',
                    'Defines type of problem being solved')
flags.DEFINE_string('env_mode', 'version of environment',
                    'v1 -> default AI, v2 -> Scenic Behavior')
flags.DEFINE_string('eval_level', '',
                    'Defines type of problem being solved')
flags.DEFINE_string('load_path', None,
                    'Path to load initial checkpoint from.')

flags.DEFINE_enum('state', 'extracted_stacked', ['extracted',
                  'extracted_stacked'],
                  'Observation to be used for training.')

flags.DEFINE_enum('reward_experiment', 'scoring', ['scoring',
                  'scoring,checkpoints'],
                  'Reward to be used for training.')
flags.DEFINE_enum('policy', 'cnn', ['cnn', 'lstm', 'mlp', 'impala_cnn',
                  'gfootball_impala_cnn'], 'Policy architecture')
flags.DEFINE_integer('num_timesteps', int(0),
                     'Number of timesteps to run for.')
flags.DEFINE_integer('num_envs', 8,
                     'Number of environments to run in parallel.')
flags.DEFINE_integer('nsteps', 128,
                     'Number of environment steps per epoch; batch size is nsteps * nenv'
                     )
flags.DEFINE_integer('noptepochs', 4, 'Number of updates per epoch.')
flags.DEFINE_integer('nminibatches', 8,
                     'Number of minibatches to split one epoch to.')
flags.DEFINE_integer('save_interval', 100,
                     'How frequently checkpoints are saved.')
flags.DEFINE_integer('seed', -1, 'Random seed.')
flags.DEFINE_float('lr', 0.00008, 'Learning rate')
flags.DEFINE_float('ent_coef', 0.01, 'Entropy coeficient')
flags.DEFINE_float('gamma', 0.993, 'Discount factor')
flags.DEFINE_float('cliprange', 0.27, 'Clip range')
flags.DEFINE_float('max_grad_norm', 0.5, 'Max gradient norm (clipping)')
flags.DEFINE_bool('render', False,
                  'If True, environment rendering is enabled.')
flags.DEFINE_bool('dump_full_episodes', False,
                  'If True, trace is dumped after every episode.')
flags.DEFINE_bool('write_video', False,
                  'If True, trace is dumped after every episode.')
flags.DEFINE_bool('dump_scores', False,
                  'If True, sampled traces after scoring are dumped.')

flags.DEFINE_string('exp_root', "~/logs_ppo_gfootball/",
                    'Path to save logfiles, tb, and models.')
flags.DEFINE_string('exp_name', "dev",
                    'Name of Experiment')
flags.DEFINE_integer('eval_interval', 1,
                     'does evaluation after each eval_interval updates'
                     )
flags.DEFINE_bool('run_raw_gf', False,
                  'If True, Raw GFootball Environment will be used.')


def create_single_scenic_environment(iprocess, level):
    """Creates scenic gfootball environment."""
    from scenic.simulators.gfootball.rl_interface import GFScenicEnv
    import os
    from scenic.simulators.gfootball.utilities.scenic_helper import buildScenario

    #scenario_file = f"{os.getcwd()}/_scenarios/exp/pass_n_shoot.scenic"
    scenario_file = level
    print("Scenic Environment: ", scenario_file)

    gf_env_settings = {
        "stacked": True,
        "rewards": "scoring",
        "representation": 'extracted',
        "players": [f"agent:left_players=1"],
        "real_time": False,
        "action_set": "default",
        "dump_full_episodes": FLAGS.dump_full_episodes,
        "dump_scores": False,
        "write_video": FLAGS.write_video,
        "tracesdir": "dummy",
        "write_full_episode_dumps": FLAGS.dump_full_episodes,
        "write_goal_dumps": False,
        "render": False
    }

    scenario = buildScenario(scenario_file)
    from scenic.simulators.gfootball.rl.gfScenicEnv_v2 import GFScenicEnv_v2
    from scenic.simulators.gfootball.rl.gfScenicEnv_v1 import GFScenicEnv_v1

    if FLAGS.env_mode == "v1":
        env = GFScenicEnv_v1(initial_scenario=scenario, gf_env_settings=gf_env_settings, rank=iprocess)
    elif FLAGS.env_mode == "v2":
        env = GFScenicEnv_v2(initial_scenario=scenario, gf_env_settings=gf_env_settings, rank=iprocess)
    else:
        assert False, "ENVIRONMENT MODE MUST BE SELECTED!"

    #env = GFScenicEnv(initial_scenario=scenario, gf_env_settings=gf_env_settings, rank=iprocess)
    env = monitor.Monitor(env, logger.get_dir() and os.path.join(logger.get_dir(), str(iprocess)), info_keywords=("score_reward",))
    return env

def create_single_football_env(iprocess, level):
    """Creates gfootball environment."""
    
    env = football_env.create_environment(
        env_name=level,
        stacked='stacked' in FLAGS.state,
        rewards=FLAGS.reward_experiment,
        logdir=logger.get_dir(),
        write_goal_dumps=FLAGS.dump_scores and iprocess == 0,
        write_full_episode_dumps=FLAGS.dump_full_episodes and iprocess
            == 0,
        render=FLAGS.render and iprocess == 0,
        dump_frequency=(50 if FLAGS.render and iprocess == 0 else 0),
        )
    env = monitor.Monitor(env, logger.get_dir() and os.path.join(logger.get_dir(), str(iprocess)), info_keywords=("score_reward",))

    return env

    
def configure_logger(log_path, **kwargs):
    if log_path is not None:
        logger.configure(log_path)
    else:
        logger.configure(**kwargs)    


def train(_):

    assert FLAGS.env_mode is not None, "ENVIRONMENT MODE MUST BE SELECTED!"

    if FLAGS.seed == -1:
        import random
        import time
        FLAGS.seed = int(time.time())%1000

    assert FLAGS.num_timesteps==0, "For testing must be 0"
    print("Testing Model: ", FLAGS.load_path)
    assert FLAGS.load_path is not None, "Must provide load path of the model you want to test" 
    assert FLAGS.load_path != "", "Must provide load path of the model you want to test" 

    print("Using Seed: ", FLAGS.seed)
    
    """Trains a PPO2 policy."""

    #CREATE DIRECTORIES
    import os 
    from gfrl.common import utils

    cwd = os.getcwd()
    exp_root = FLAGS.exp_root
    exp_name = FLAGS.exp_name
    log_path = utils.get_incremental_dirname(exp_root, exp_name)

    #SAVE PARAMETERS
    utils.save_params(log_path, FLAGS)
    
    #print("Logging in ", log_path)
    #print("Log Arguement", FLAGS.log_path)
    os.environ['OPENAI_LOG_FORMAT'] = 'stdout,tensorboard,csv,log'
    configure_logger(log_path=log_path)

    run_raw_gf = FLAGS.run_raw_gf
    print("Run Raw GF: ", run_raw_gf)

    
    
    if run_raw_gf:
        print("Running experiment on Raw GFootball Environment")
        vec_env = SubprocVecEnv([lambda _i=i: \
                                create_single_football_env(_i, level) for i in
                                range(FLAGS.num_envs)], context=None)

    else:
        if FLAGS.eval_level != "":
            eval_env = SubprocVecEnv([lambda _i=i: \
                        create_single_scenic_environment(_i+FLAGS.num_envs, FLAGS.eval_level) for i in
                        range(FLAGS.num_envs)], context=None)
        else:
            eval_env = None
        
        
                         
    #eval_env = create_single_scenic_environment(0,FLAGS.level) 
    # Import tensorflow after we create environments. TF is not fork sake, and
    # we could be using TF as part of environment if one of the players is
     # controled by an already trained model.

    import tensorflow.compat.v1 as tf
    #import tensorflow as tf
    
    ncpu = multiprocessing.cpu_count()
    config = tf.ConfigProto(allow_soft_placement=True,
                            intra_op_parallelism_threads=ncpu,
                            inter_op_parallelism_threads=ncpu)
    config.gpu_options.allow_growth = True
    tf.Session(config=config).__enter__()
    
    print(tf.__version__)

    
    
    from gfrl.common.mybase.ppo2_eval import eval
    reward_mean, score_mean, ep_len_mean, num_test_epi, test_total_timesteps = eval(
        network=FLAGS.policy,
        total_timesteps=FLAGS.num_timesteps,
        env=None,
        eval_env = eval_env,
        seed=FLAGS.seed,
        nsteps=FLAGS.nsteps,
        nminibatches=FLAGS.nminibatches,
        noptepochs=FLAGS.noptepochs,
        max_grad_norm=FLAGS.max_grad_norm,
        gamma=FLAGS.gamma,
        ent_coef=FLAGS.ent_coef,
        lr=FLAGS.lr,
        log_interval=1,
        eval_interval=FLAGS.eval_interval,
        save_interval=FLAGS.save_interval,
        cliprange=FLAGS.cliprange,
        load_path=FLAGS.load_path
        )

    #print("reward_mean, score_mean, ep_len_mean, num_test_epi, test_total_timesteps")
    #print(reward_mean, score_mean, ep_len_mean, num_test_epi, test_total_timesteps)

    #fstr = "name, reward_mean, score_mean, ep_len_mean, num_test_epi, test_total_timesteps, FLAGS.eval_level, FLAGS.load_path\n"
    fstr = ""
    fstr += str((FLAGS.exp_name, reward_mean, score_mean, ep_len_mean, num_test_epi, test_total_timesteps, FLAGS.eval_level, FLAGS.load_path))[1:-1]
    fstr += "\n"

    print(fstr)
    
    res_file = os.path.join(exp_root, "test_perf.csv")
    with open(res_file, "a+") as res:
        res.write(fstr)


if __name__ == '__main__':
    #FLAGS.level = None
    #FLAGS.num_envs =  2
    #FLAGS.policy = "gfootball_impala_cnn"
    #FLAGS.eval_level = "/home/ubuntu/ScenicGFootBall/training/gfrl/_scenarios/sc4rl/ps_3v2_0.scenic"
    #FLAGS.load_path = "/home/ubuntu/ScenicGFootBall/training/gfrl/_res_bc/bc_ps_3v2_0_rand_8K_success_0/checkpoints/bc_00125"
    app.run(train)
