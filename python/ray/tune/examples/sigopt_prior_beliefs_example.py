"""This test checks that SigOpt is functional.

It also checks that it is usable with a separate scheduler.
"""
import time

import ray
import numpy as np
from ray import tune

from ray.tune.schedulers import FIFOScheduler
from ray.tune.suggest.sigopt import SigOptSearch

np.random.seed(0)
vector1 = np.random.normal(0.0, 0.1, 100)
vector2 = np.random.normal(0.0, 0.1, 100)
vector3 = np.random.normal(0.0, 0.1, 100)


def evaluate(w1, w2, w3):
    total = w1 * vector1 + w2 * vector2 + w3 * vector3
    return total.mean(), total.std()


def easy_objective(config):
    # Hyperparameters
    w1 = config["w1"]
    w2 = config["w2"]
    total = (w1 + w2)
    if total > 1:
        w3 = 0
        w1 /= total
        w2 /= total
    else:
        w3 = 1 - total

    average, std = evaluate(w1, w2, w3)
    tune.report(average=average, std=std)
    time.sleep(0.1)


if __name__ == "__main__":
    import argparse
    import os
    from sigopt import Connection

    assert "SIGOPT_KEY" in os.environ, \
        "SigOpt API key must be stored as environment variable at SIGOPT_KEY"

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--smoke-test", action="store_true", help="Finish quickly for testing")
    args, _ = parser.parse_known_args()
    ray.init()

    samples = 10 if args.smoke_test else 1000

    conn = Connection(client_token=os.environ["SIGOPT_KEY"])
    experiment = conn.experiments().create(
        name="prior experiment example",
        parameters=[{
            "name": "w1",
            "bounds": {
                "max": 1,
                "min": 0
            },
            "prior": {
                "mean": 1 / 3,
                "name": "normal",
                "scale": 0.2
            },
            "type": "double"
        }, {
            "name": "w2",
            "bounds": {
                "max": 1,
                "min": 0
            },
            "prior": {
                "mean": 1 / 3,
                "name": "normal",
                "scale": 0.2
            },
            "type": "double"
        }],
        metrics=[
            dict(name="std", objective="minimize", strategy="optimize"),
            dict(name="average", strategy="store")
        ],
        observation_budget=samples,
        parallel_bandwidth=1)

    config = {"num_samples": samples, "config": {}}

    algo = SigOptSearch(
        connection=conn,
        experiment_id=experiment.id,
        name="SigOpt Example Existing Experiment",
        max_concurrent=1,
        metric=["average", "std"],
        mode=["obs", "min"])

    scheduler = FIFOScheduler()

    tune.run(
        easy_objective,
        name="my_exp",
        search_alg=algo,
        scheduler=scheduler,
        **config)
