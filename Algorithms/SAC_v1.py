#Soft Actor-Critic: Off-Policy Maximum Entropy Deep Reinforcement Learning with a Stochastic Actor, Haarnoja et al, 2018.

import tensorflow as tf
import numpy as np

from Common.Buffer import Buffer
from Common.Utils import copy_weight, soft_update
from Networks.Basic_Networks import Q_network, V_network
from Networks.Gaussian_Actor import Squashed_Gaussian_Actor

class SAC_v1:
    def __init__(self, state_dim, action_dim, hidden_dim=256, training_step=1,
                 batch_size=128, buffer_size=1e6, tau=0.005, learning_rate=0.0003, gamma=0.99, alpha=0.2, reward_scale=1, training_start = 500):

        self.buffer = Buffer(buffer_size)

        self.actor_optimizer = tf.keras.optimizers.Adam(learning_rate)
        self.critic1_optimizer = tf.keras.optimizers.Adam(learning_rate)
        self.critic2_optimizer = tf.keras.optimizers.Adam(learning_rate)
        self.v_network_optimizer = tf.keras.optimizers.Adam(learning_rate)

        self.state_dim = state_dim
        self.action_dim = action_dim

        self.batch_size = batch_size
        self.tau = tau
        self.gamma = gamma
        self.alpha = alpha
        self.reward_scale = reward_scale
        self.training_start = training_start
        self.training_step = training_step

        self.actor = Squashed_Gaussian_Actor(self.state_dim, self.action_dim, (hidden_dim, hidden_dim))
        self.critic1 = Q_network(self.state_dim, self.action_dim, (hidden_dim, hidden_dim))
        self.critic2 = Q_network(self.state_dim, self.action_dim, (hidden_dim, hidden_dim))
        self.v_network = V_network(self.state_dim, (hidden_dim, hidden_dim))
        self.target_v_network = V_network(self.state_dim, (hidden_dim, hidden_dim))

        copy_weight(self.v_network, self.target_v_network)

        self.network_list = {'Actor': self.actor, 'Critic1': self.critic1, 'Critic2': self.critic2, 'V_network': self.v_network, 'Target_V_network': self.target_v_network}
        self.name = 'SAC_v1'

    def get_action(self, state):
        state = np.expand_dims(np.array(state), axis=0)

        action = self.actor(state).numpy()[0]

        return action


    def train(self, training_num):
        for i in range(training_num):
            s, a, r, ns, d = self.buffer.sample(self.batch_size)

            min_aq = tf.minimum(self.critic1(s, self.actor(s)), self.critic2(s, self.actor(s)))

            target_v = tf.stop_gradient(min_aq - self.alpha * self.actor.log_pi(s))
            #v_network training
            with tf.GradientTape(persistent=True) as tape1:
                v_loss = 0.5 * tf.reduce_mean(tf.square(self.v_network(s) - target_v))

            v_gradients = tape1.gradient(v_loss, self.v_network.trainable_variables)
            self.v_network_optimizer.apply_gradients(zip(v_gradients, self.v_network.trainable_variables))

            del tape1

            target_q = tf.stop_gradient(r + self.gamma * (1 - d) * self.target_v_network(ns))
            #critic training
            with tf.GradientTape(persistent=True) as tape2:

                critic1_loss = 0.5 * tf.reduce_mean(tf.square(self.critic1(s, a) - target_q))
                critic2_loss = 0.5 * tf.reduce_mean(tf.square(self.critic2(s, a) - target_q))

            critic1_gradients = tape2.gradient(critic1_loss, self.critic1.trainable_variables)
            self.critic1_optimizer.apply_gradients(zip(critic1_gradients, self.critic1.trainable_variables))

            critic2_gradients = tape2.gradient(critic2_loss, self.critic2.trainable_variables)
            self.critic2_optimizer.apply_gradients(zip(critic2_gradients, self.critic2.trainable_variables))

            del tape2
            #actor training
            with tf.GradientTape() as tape3:
                mu, sigma = self.actor.mu_sigma(s)
                output = mu + tf.random.normal(shape=sigma.shape) * sigma

                min_aq_rep = tf.minimum(self.critic1(s, output), self.critic2(s, output))

                actor_loss = tf.reduce_mean(self.alpha * self.actor.log_pi(s) - min_aq_rep)

            actor_grad = tape3.gradient(actor_loss, self.actor.trainable_variables)
            self.actor_optimizer.apply_gradients(zip(actor_grad, self.actor.trainable_variables))

            del tape3

            soft_update(self.v_network, self.target_v_network, self.tau)





