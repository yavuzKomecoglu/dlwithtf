"""Adapted from DeepChem Examples by Peter Eastman and Karl Leswing."""

import copy
import random
import shutil
import numpy as np
import tensorflow as tf
import deepchem as dc
from environment import TicTacToeEnvironment
from a3c import Layer
from a3c import Adam
from a3c import Dense
from a3c import A3C


class Squeeze(Layer):

  def __init__(self, in_layers=None, squeeze_dims=None, **kwargs):
    self.squeeze_dims = squeeze_dims
    super(Squeeze, self).__init__(in_layers, **kwargs)
    try:
      parent_shape = self.in_layers[0].shape
      if squeeze_dims is None:
        self._shape = [i for i in parent_shape if i != 1]
      else:
        self._shape = [
            parent_shape[i] for i in range(len(parent_shape))
            if i not in squeeze_dims
        ]
    except:
      pass

  def create_tensor(self, in_layers=None, set_tensors=True, **kwargs):
    inputs = self._get_input_tensors(in_layers)
    parent_tensor = inputs[0]
    out_tensor = tf.squeeze(parent_tensor, squeeze_dims=self.squeeze_dims)
    if set_tensors:
      self.out_tensor = out_tensor
    return out_tensor

class BatchNorm(Layer):

  def __init__(self, in_layers=None, **kwargs):
    super(BatchNorm, self).__init__(in_layers, **kwargs)
    try:
      parent_shape = self.in_layers[0].shape
      self._shape = tuple(self.in_layers[0].shape)
    except:
      pass

  def create_tensor(self, in_layers=None, set_tensors=True, **kwargs):
    inputs = self._get_input_tensors(in_layers)
    parent_tensor = inputs[0]
    out_tensor = tf.layers.batch_normalization(parent_tensor)
    if set_tensors:
      self.out_tensor = out_tensor
    return out_tensor

class Squeeze(Layer):

  def __init__(self, in_layers=None, squeeze_dims=None, **kwargs):
    self.squeeze_dims = squeeze_dims
    super(Squeeze, self).__init__(in_layers, **kwargs)
    try:
      parent_shape = self.in_layers[0].shape
      if squeeze_dims is None:
        self._shape = [i for i in parent_shape if i != 1]
      else:
        self._shape = [
            parent_shape[i] for i in range(len(parent_shape))
            if i not in squeeze_dims
        ]
    except:
      pass

  def create_tensor(self, in_layers=None, set_tensors=True, **kwargs):
    inputs = self._get_input_tensors(in_layers)
    parent_tensor = inputs[0]
    out_tensor = tf.squeeze(parent_tensor, squeeze_dims=self.squeeze_dims)
    if set_tensors:
      self.out_tensor = out_tensor
    return out_tensor

class Flatten(Layer):
  """Flatten every dimension except the first"""

  def __init__(self, in_layers=None, **kwargs):
    super(Flatten, self).__init__(in_layers, **kwargs)
    try:
      parent_shape = self.in_layers[0].shape
      s = list(parent_shape[:2])
      for x in parent_shape[2:]:
        s[1] *= x
      self._shape = tuple(s)
    except:
      pass

  def create_tensor(self, in_layers=None, set_tensors=True, **kwargs):
    inputs = self._get_input_tensors(in_layers)
    if len(inputs) != 1:
      raise ValueError("Only One Parent to Flatten")
    parent = inputs[0]
    parent_shape = parent.get_shape()
    vector_size = 1
    for i in range(1, len(parent_shape)):
      vector_size *= parent_shape[i].value
    parent_tensor = parent
    out_tensor = tf.reshape(parent_tensor, shape=(-1, vector_size))
    if set_tensors:
      self.out_tensor = out_tensor
    return out_tensor

class SoftMax(Layer):

  def __init__(self, in_layers=None, **kwargs):
    super(SoftMax, self).__init__(in_layers, **kwargs)
    try:
      self._shape = tuple(self.in_layers[0].shape)
    except:
      pass

  def create_tensor(self, in_layers=None, set_tensors=True, **kwargs):
    inputs = self._get_input_tensors(in_layers)
    if len(inputs) != 1:
      raise ValueError("Must only Softmax single parent")
    parent = inputs[0]
    out_tensor = tf.contrib.layers.softmax(parent)
    if set_tensors:
      self.out_tensor = out_tensor
    return out_tensor


class TicTacToePolicy(dc.rl.Policy):
  def create_layers(self, state, **kwargs):
    d1 = Flatten(in_layers=state)
    d2 = Dense(
        in_layers=[d1],
        activation_fn=tf.nn.relu,
        normalizer_fn=tf.nn.l2_normalize,
        normalizer_params={"dim": 1},
        out_channels=64)
    d3 = Dense(
        in_layers=[d2],
        activation_fn=tf.nn.relu,
        normalizer_fn=tf.nn.l2_normalize,
        normalizer_params={"dim": 1},
        out_channels=32)
    d4 = Dense(
        in_layers=[d3],
        activation_fn=tf.nn.relu,
        normalizer_fn=tf.nn.l2_normalize,
        normalizer_params={"dim": 1},
        out_channels=16)
    d4 = BatchNorm(in_layers=[d4])
    d5 = Dense(in_layers=[d4], activation_fn=None, out_channels=9)
    value = Dense(in_layers=[d4], activation_fn=None, out_channels=1)
    value = Squeeze(squeeze_dims=1, in_layers=[value])
    probs = SoftMax(in_layers=[d5])
    return {'action_prob': probs, 'value': value}


def eval_tic_tac_toe(value_weight,
                     num_epoch_rounds=1,
                     games=10**4,
                     rollouts=10**5,
                     advantage_lambda=0.98):
  """
  Returns the average reward over 10k games after 100k rollouts
  
  Parameters
  ----------
  value_weight: float

  Returns
  ------- 
  avg_rewards
  """
  env = TicTacToeEnvironment()
  policy = TicTacToePolicy()
  model_dir = "/tmp/tictactoe"
  try:
    shutil.rmtree(model_dir)
  except:
    pass

  avg_rewards = []
  for j in range(num_epoch_rounds):
    print("Epoch round: %d" % j)
    a3c_engine = A3C(
        env,
        policy,
        entropy_weight=0.01,
        value_weight=value_weight,
        model_dir=model_dir,
        advantage_lambda=advantage_lambda,
        optimizer=Adam(learning_rate=0.001))
    try:
      a3c_engine.restore()
    except:
      print("unable to restore")
      pass
    a3c_engine.fit(rollouts)
    rewards = []
    for i in range(games):
      env.reset()
      reward = -float('inf')
      while not env.terminated:
        action = a3c_engine.select_action(env.state)
        reward = env.step(action)
      rewards.append(reward)
    print("Mean reward at round %d is %f" % (j+1, np.mean(rewards)))
    avg_rewards.append({(j + 1) * rollouts: np.mean(rewards)})
  return avg_rewards


def main():
  value_weight = 6.0
  score = eval_tic_tac_toe(value_weight=0.2, num_epoch_rounds=20,
                           advantage_lambda=0.,
                           games=10**4, rollouts=5*10**4)
  print(score)


if __name__ == "__main__":
  main()
