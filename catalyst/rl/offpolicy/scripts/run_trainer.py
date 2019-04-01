#!/usr/bin/env python

import os
import atexit
import argparse


from catalyst.dl.scripts.utils import import_module
from catalyst.rl.registry import ALGORITHMS, ENVIRONMENTS
from catalyst.rl.offpolicy.trainer import Trainer
from catalyst.rl.db.redis import RedisDB
from catalyst.utils.config import parse_args_uargs, dump_config
from catalyst.utils.misc import set_global_seed


def build_args(parser):
    parser.add_argument(
        "-C",
        "--config",
        help="path to config/configs",
        required=True
    )
    parser.add_argument("--expdir", type=str, default=None)
    parser.add_argument("--logdir", type=str, default=None)
    parser.add_argument("--resume", type=str, default=None)
    parser.add_argument("--seed", type=int, default=42)

    return parser


def parse_args():
    parser = argparse.ArgumentParser()
    build_args(parser)
    args, unknown_args = parser.parse_known_args()
    return args, unknown_args


def main(args, unknown_args):
    args, config = parse_args_uargs(args, unknown_args)
    set_global_seed(args.seed)

    if args.logdir is not None:
        os.makedirs(args.logdir, exist_ok=True)
        dump_config(args.config, args.logdir)

    if args.expdir is not None:
        module = import_module(expdir=args.expdir)  # noqa: F841

    db_server = RedisDB(
        port=config.get("redis", {}).get("port", 12000),
        prefix=config.get("redis", {}).get("prefix", "")
    )

    environment_fn = ENVIRONMENTS.get(args.environment)
    env = environment_fn(**config["environment"])
    config["environment"] = \
        env.update_environment_config(config["environment"])

    algorithm_fn = ALGORITHMS.get(args.algorithm)
    algorithm = algorithm_fn.prepare_for_trainer(config)

    trainer = Trainer(
        algorithm=algorithm,
        env_spec=env,
        db_server=db_server,
        **config["trainer"],
        logdir=args.logdir,
        resume=args.resume,
    )

    def on_exit():
        for p in trainer.get_processes():
            p.terminate()

    atexit.register(on_exit)

    trainer.run()


if __name__ == "__main__":
    args, unknown_args = parse_args()
    main(args, unknown_args)
