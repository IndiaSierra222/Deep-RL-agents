
import tensorflow as tf
import numpy as np
from collections import deque

from Model import build_actor, get_vars, copy_vars
from Environment import Environment

from Displayer import DISPLAYER
import GUI
from settings import *



class Actor:

    def __init__(self, sess, coord, n_actor, buffer):
        print("Initializing actor %i..." % n_actor)

        self.sess = sess
        self.coord = coord
        self.n_actor = n_actor
        self.env = Environment()
        self.buffer = buffer

        self.build_actor()
        self.build_update()

        print("Actor %i initialized !\n" % n_actor)

    def build_actor(self):

        scope = 'worker_actor_' + str(self.n_actor)
        self.state_ph = tf.placeholder(dtype=tf.float32,
                                       shape=[None, *STATE_SIZE],
                                       name='state_ph')

        # Get the policy prediction network
        self.policy = build_actor(self.state_ph, trainable=False, scope=scope)
        self.vars = get_vars(scope, trainable=False)

    def build_update(self):

        with self.sess.as_default(), self.sess.graph.as_default():

            self.network_vars = get_vars('learner_actor', trainable=True)
            self.update = copy_vars(self.network_vars, self.vars,
                                    1, 'update_actor_'+str(self.n_actor))

    def predict_action(self, s):
        return self.sess.run(self.policy, feed_dict={self.state_ph: s[None]})[0]

    def run(self):

        self.sess.run(self.update)

        total_eps = 1
        while not self.coord.should_stop():

            episode_reward = 0
            episode_step = 0
            done = False
            memory = deque()

            noise_scale = NOISE_SCALE * NOISE_DECAY**(total_eps//20)

            s = self.env.reset()

            render = (self.n_actor == 1 and GUI.render.get(total_eps))
            self.env.set_render(render)

            max_steps = MAX_STEPS + total_eps // 5

            while episode_step < max_steps and not done and not self.coord.should_stop():

                noise = np.random.normal(size=ACTION_SIZE)
                scaled_noise = noise_scale * noise

                a = np.clip(self.predict_action(s) + scaled_noise, *BOUNDS)

                s_, r, done, _ = self.env.act(a)

                episode_reward += r

                memory.append((s, a, r, s_, 0 if done else 1))

                if len(memory) >= N_STEP_RETURN:
                    s_mem, a_mem, discount_r, ss_mem, done_mem = memory.popleft()
                    for i, (si, ai, ri, s_i, di) in enumerate(memory):
                        discount_r += ri * DISCOUNT ** (i + 1)
                    self.buffer.add(s_mem, a_mem, discount_r, s_, 0 if done else 1)

                s = s_
                episode_step += 1

            # Periodically update actors on the network
            if total_eps % UPDATE_ACTORS_FREQ == 0:
                self.sess.run(self.update)

            if not self.coord.should_stop():
                if self.n_actor == 1 and GUI.ep_reward.get(total_eps):
                    print("Episode %i : reward %i, steps %i, noise scale %f" % (total_eps, episode_reward, episode_step, noise_scale))

                plot = (self.n_actor == 1 and GUI.plot.get(total_eps))
                DISPLAYER.add_reward(episode_reward, self.n_actor, plot)
            
                total_eps += 1

        self.env.close()
