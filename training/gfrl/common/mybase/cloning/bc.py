import os
import time
import numpy as np
import os.path as osp
from baselines import logger
from collections import deque
from baselines.common import explained_variance, set_global_seeds
from baselines.common.policies import build_policy
try:
    from mpi4py import MPI
except ImportError:
    MPI = None
from baselines.ppo2.runner import Runner


def constfn(val):
    def f(_):
        return val
    return f

"""
def learn(*, network, env, dataset=None, eval_env = None, seed=None, nsteps=2048, lr=3e-4,
            log_interval=10, nminibatches=4, n_epochs = 2,
            save_interval=0, load_path=None, model_fn=None, update_fn=None, init_fn=None, mpi_rank_weight=1, comm=None, eval_interval=1, **network_kwargs):

def learn(*, network, env, total_timesteps, dataset=None, eval_env = None, seed=None, nsteps=2048, ent_coef=0.0, lr=3e-4,
            vf_coef=0.5,  max_grad_norm=0.5, gamma=0.99, lam=0.95,
            log_interval=10, nminibatches=4, noptepochs=4, cliprange=0.2,
            save_interval=0, load_path=None, model_fn=None, update_fn=None, init_fn=None, mpi_rank_weight=1, comm=None, eval_interval=1, **network_kwargs):
"""
def learn(*, network, env, total_timesteps=0, n_epochs = 2, dataset=None, eval_env = None, seed=None, batch_size = 512, 
            nsteps=2048, ent_coef=0.0, lr=3e-4,
            vf_coef=0.5,  max_grad_norm=0.5, gamma=0.99, lam=0.95,
            log_interval=10, nminibatches=4, noptepochs=4, cliprange=0.2,
            save_interval=0, load_path=None, model_fn=None, update_fn=None, init_fn=None, mpi_rank_weight=1, comm=None, 
            eval_interval=1, eval_timesteps=100, validation_dataset=None, **network_kwargs):

    set_global_seeds(seed)
    
    policy = build_policy(env, network, **network_kwargs)

    # Get the nb of env
    nenvs = env.num_envs

    # Get state_space and action_space
    ob_space = env.observation_space
    ac_space = env.action_space


    is_mpi_root = (MPI is None or MPI.COMM_WORLD.Get_rank() == 0)

    
    # Instantiate the model object (that creates act_model and train_model)

    #from baselines.ppo2.model import Model
    from gfrl.common.mybase.cloning.bc_model import BCModel

    model = BCModel(policy=policy, ob_space=ob_space, ac_space=ac_space, nbatch_act=nenvs, nbatch_train=batch_size,
                    nsteps=nsteps, ent_coef=ent_coef, vf_coef=vf_coef,
                    max_grad_norm=max_grad_norm, comm=comm, mpi_rank_weight=mpi_rank_weight)

    if load_path is not None:
        model.load(load_path)

    # Instantiate the runner object
    # runner = Runner(env=env, model=model, nsteps=nsteps, gamma=gamma, lam=lam)
    if eval_env is not None:
        eval_runner = Runner(env = eval_env, model = model, nsteps = eval_timesteps, gamma = gamma, lam= lam)


    #epinfobuf = deque(maxlen=100)
    #if eval_env is not None:
    #    eval_epinfobuf = deque(maxlen=100)

    if init_fn is not None:
        init_fn()

    # Start total timer
    tfirststart = time.perf_counter()

    print("Training BC")

    nupdates = dataset.num_pairs * n_epochs // batch_size
    print(f"Dataset Size: {dataset.num_pairs}")
    print(f"NEpochs: {n_epochs} NUpdates: {nupdates} Batch Size: {batch_size}")

    mean_dataset_rew = np.nan
    if hasattr(dataset, "mean_reward"): mean_dataset_rew = dataset.mean_reward
    ds_size = dataset.obs.shape[0]

    logger.logkv('dataset/mean_reward', mean_dataset_rew)
    logger.logkv('dataset/timesteps', ds_size)

    if hasattr(dataset, "policy_mean_reward"):
        logger.logkv('dataset/policy_mean_reward', dataset.policy_mean_reward)

    if hasattr(dataset, "policy_total_trajectories:"):
        logger.logkv('dataset/policy_total_trajectories:', dataset.policy_total_trajectories)
    
    if validation_dataset is not None: 
        logger.logkv('param/validation_datasize', validation_dataset.size)


    logger.logkv('param/batch_size', batch_size)

    best_eval_rew = 0

    val_loss_interval = 1

    for update in range(1, nupdates+1):
        obs, acts = dataset.get_next_batch(batch_size=batch_size)
        loss = model.train_bc(obs=obs, actions=acts, lr=lr)[0]

        print(f"step: {update}/{nupdates} bc loss: {loss}")
        logger.logkv("_train/loss", loss)

        
        if (update % val_loss_interval == 0 or update == 1 or update==nupdates) and validation_dataset.size>batch_size:
            
            
            val_losses = []

            for _ in range(int(validation_dataset.size/batch_size)):
                val_obs, val_acts = validation_dataset.get_next_batch(batch_size=batch_size)
                val_loss = model.evaluate_bc_loss(obs = val_obs, actions=val_acts, lr=lr)[0]
                val_losses.append(val_loss)
            
            logger.logkv("_train/val_loss", np.mean(val_losses))
            #logger.logkv("_train/val_loss", np.mean(val_losses))
            



        if eval_env is not None:
            if update % eval_interval == 0 or update == 1 or update==nupdates:
                print("Running Evaluation")
                eval_obs, eval_returns, eval_masks, eval_actions, eval_values, eval_neglogpacs, eval_states, eval_epinfos = eval_runner.run()

                eval_rew = safemean([epinfo['r'] for epinfo in eval_epinfos])
                logger.logkv('_eval/reward_mean',  eval_rew)
                logger.logkv('_eval/score_mean', safemean([epinfo['score_reward'] for epinfo in eval_epinfos]) )
                logger.logkv('_eval/ep_len_mean', safemean([epinfo['l'] for epinfo in eval_epinfos]) )


                if eval_rew>best_eval_rew and logger.get_dir():
                    best_eval_rew = eval_rew 
                    checkdir = osp.join(logger.get_dir(), 'checkpoints')
                    os.makedirs(checkdir, exist_ok=True)
                    savepath = osp.join(checkdir, 'test_best')
                    model.save(savepath)

        
                    

        logger.dumpkvs()

        #if update==nupdates and logger.get_dir() and is_mpi_root:
        if save_interval and (update % save_interval == 0 or update == 1 or update==nupdates) and logger.get_dir():
            checkdir = osp.join(logger.get_dir(), 'checkpoints')
            os.makedirs(checkdir, exist_ok=True)

            if update == nupdates-1: savepath = osp.join(checkdir, 'bc_final_%.5i'%update)
            else: savepath = osp.join(checkdir, 'bc_%.5i'%update)
            print('Saving to', savepath)
            model.save(savepath)

    return model


def safemean(xs):
    return np.nan if len(xs) == 0 else np.mean(xs)


