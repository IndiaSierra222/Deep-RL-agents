#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thu Sep 14 17:02:53 2017

@author: jaromir janish
"""

# OpenGym MountainCar-v0
# -------------------
#

import random
import numpy
import gym
from math import exp
import matplotlib.pyplot as plt


# -------------------- BRAIN ---------------------------
from keras.models import Sequential
from keras.layers import Dense
from keras.optimizers import RMSprop


class Brain:

    def __init__(self, state_size, action_size):
        self.state_size = state_size
        self.action_size = action_size

        self.model = Sequential()
        self.model.add(Dense(units=64, activation='relu',
                             input_dim=state_size))
        self.model.add(Dense(units=action_size, activation='linear'))

        opt = RMSprop(lr=0.00025)
        self.model.compile(loss='mse', optimizer=opt)

    def train(self, x, y, epoch=1, verbose=0):
        self.model.fit(x, y, batch_size=64, epochs=epoch, verbose=verbose)

    def predict(self, s):
        return self.model.predict(s)

    def predictOne(self, s):
        return self.predict(s.reshape(1, self.state_size)).flatten()


# -------------------- MEMORY --------------------------
class Memory:   # stored as ( s, a, r, s_ )

    def __init__(self, capacity):
        self.samples = []
        self.capacity = capacity

    def add(self, sample):
        self.samples.append(sample)

        if len(self.samples) > self.capacity:
            self.samples.pop(0)

    def sample(self, n):
        n = min(n, len(self.samples))
        return random.sample(self.samples, n)

    def is_full(self):
        return len(self.samples) >= self.capacity


# -------------------- AGENT ---------------------------
MEMORY_CAPACITY = 100000
BATCH_SIZE = 64

GAMMA = 0.99

MAX_EPSILON = 1
MIN_EPSILON = 0.01
LAMBDA = 0.001      # speed of decay


class Agent:
    steps = 0
    epsilon = MAX_EPSILON

    def __init__(self, state_size, action_size):
        self.state_size = state_size
        self.action_size = action_size

        self.brain = Brain(state_size, action_size)
        self.memory = Memory(MEMORY_CAPACITY)

        self.rewards = []

    def save(self, R):
        self.rewards.append(R)

    def disp(self):
        plt.plot(self.rewards)

    def act(self, s):
        if random.random() < self.epsilon:
            return random.randint(0, self.action_size-1)
        else:
            return numpy.argmax(self.brain.predictOne(s))

    def observe(self, sample):  # in (s, a, r, s_) format
        self.memory.add(sample)

        # slowly decrease Epsilon based on our eperience
        self.steps += 1
        self.epsilon = MIN_EPSILON + (MAX_EPSILON - MIN_EPSILON) *\
            exp(-LAMBDA * self.steps)

    def replay(self):
        batch = self.memory.sample(BATCH_SIZE)
        batchLen = len(batch)

        no_state = numpy.zeros(self.state_size)

        states = numpy.array([obs[0] for obs in batch])
        states_ = numpy.array([(no_state if obs[3] is None else obs[3])
                               for obs in batch])

        p = agent.brain.predict(states)
        p_ = agent.brain.predict(states_)

        x = numpy.zeros((batchLen, self.state_size))
        y = numpy.zeros((batchLen, self.action_size))

        for i in range(batchLen):
            s, a, r, s_ = batch[i]

            Q_target = p[i]
            if s_ is None:
                Q_target[a] = r
            else:
                Q_target[a] = r + GAMMA * numpy.amax(p_[i])

            x[i] = s
            y[i] = Q_target

        self.brain.train(x, y)


class RandomAgent(Agent):

    def act(self, s):
        return random.randint(0, self.action_size-1)

    def replay(self):
        pass


# -------------------- ENVIRONMENT ---------------------
class Environment:

    def __init__(self, problem):
        self.env = gym.make(problem)

    def run(self, agent, render=False):
        s = self.env.reset()
        R = 0
        done = False

        while not done:
            # self.env.render()

            a = agent.act(s)

            s_, r, done, info = self.env.step(a)
            if render:
                self.env.render()

            if done:      # terminal state
                s_ = None

            agent.observe((s, a, r, s_))
            agent.replay()

            s = s_
            R += r

        print("Total reward:", R)
        agent.save(R)

    def end(self):
        self.env.render(close=True)
        self.env.close()


# -------------------- MAIN ----------------------------
PROBLEM = 'MountainCar-v0'
environment = Environment(PROBLEM)

state_size = environment.env.observation_space.shape[0]
action_size = environment.env.action_space.n

agent = Agent(state_size, action_size)
randomAgent = RandomAgent(state_size, action_size)

try:
    while not randomAgent.memory.is_full():
        environment.run(randomAgent)
    print("RandomAgent memory is full")
    agent.memory = randomAgent.memory

    i = 0
    while i < 1000 and (i == 0 or
                        not all([r == 200 for r in agent.rewards[-10:]])):
        environment.run(agent, ((i+1) % 100 == 0))
        i += 1
except KeyboardInterrupt:
    print("Arret de la session")
finally:
    agent.brain.model.save("results/DQN-MountainCar_results.h5")
    environment.end()