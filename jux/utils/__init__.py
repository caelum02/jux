import gzip
import json
import os.path as osp
import urllib.request
from typing import Dict, Generator, Tuple

import jax
import jax.numpy as jnp
import luxai_s2
import numpy as np
from luxai_s2 import LuxAI_S2

INT32_MAX = jnp.iinfo(jnp.int32).max
INT16_MAX = jnp.iinfo(jnp.int32).max
INT8_MAX = jnp.iinfo(jnp.int8).max


def imax(dtype):
    if isinstance(dtype, np.dtype):
        return np.array(np.iinfo(dtype).max, dtype=dtype)
    elif isinstance(dtype, jax.Array):
        dtype = dtype.dtype
        return jnp.array(jnp.iinfo(dtype).max, dtype=dtype)
    else:
        return dtype(jnp.iinfo(dtype).max)


def _action_v1_to_v2(actions):
    for id, acts in actions.items():
        if not id.startswith('unit_'):
            continue
        for a in acts:
            repeat = a[4]
            assert repeat >= -1
            a[4] = (repeat == -1)
            a.append(max(1, repeat + 1))


def get_actions_from_replay(replay: Dict, replay_version: str) -> Generator[Dict, None, None]:
    for step in replay['steps'][1:]:
        player_0, player_1 = step

        # ensure compatibility with old 1.x.x replay format
        if replay_version.startswith('1.'):
            for actions in (player_0['action'], player_1['action']):
                _action_v1_to_v2(actions)

        yield {'player_0': player_0['action'], 'player_1': player_1['action']}


def load_replay(replay: str) -> Tuple[LuxAI_S2, Generator[Dict, None, None]]:
    if osp.splitext(replay)[-1] == '.gz':
        with gzip.open(replay) as f:
            replay = json.load(f)
    elif replay.startswith('https://') or replay.startswith('http://'):
        with urllib.request.urlopen(replay) as f:
            replay = json.load(f)
    else:
        with open(replay) as f:
            replay = json.load(f)
    seed = replay['configuration']['seed']
    env = LuxAI_S2()
    env.reset(seed=seed)
    actions = get_actions_from_replay(replay, replay['version'])

    return env, actions
