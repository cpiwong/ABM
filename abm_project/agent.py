from mesa import Agent

import numpy as np
import operator
import random


class CarAgent(Agent):
    def __init__(self, model, unique_id, pos, speed, velocity, destination):
        super().__init__(unique_id, model)
        self.pos = pos
        self.speed = speed
        self.directions = ["s", "l", "r"]
        self.vectors = [(0, 1), (1, 0), (0, -1), (-1, 0)]
        
        self.velocity = velocity
        self.destination = destination # not being used yet

        self.turning = False
        self.turning_counter = 0

    def step(self):
        if self.turning:
            if self.turning_counter == 0:
                self.turn = random.choice(self.directions)
                for i in range(len(self.vectors)):
                    if self.vectors[i] == self.velocity:
                        if self.turn == "r":
                            self.new_vector = self.vectors[(i+1)%len(self.vectors)]
                        elif self.turn == "l":
                            self.new_vector = self.vectors[i-1]
                        else:
                            self.new_vector = self.velocity
            elif self.turning_counter == 1:
                self.speed = 1
            elif self.turning_counter == 2:
                if self.turn == "r":
                    self.velocity = self.new_vector
                    self.turning = False
            elif self.turning_counter == 3:
                if self.turn == "l":
                    self.velocity = self.new_vector
                else:
                    self.turning = False
            elif self.turning_counter == 4:
                self.turning = False

            self.turning_counter += 1
                
        if self.speed != 0:
            change = tuple([x * self.speed for x in self.velocity])
            next_pos = tuple(map(operator.add, self.pos, change))

            if not self.turning:
                intersection = False
                while next_pos in self.model.intersections:
                    intersection = True
                    self.speed -= 1 # if speed increases > 1
                    change = tuple([x * self.speed for x in self.velocity])
                    next_pos = tuple(map(operator.add, self.pos, change))
            
                if intersection:
                    self.speed = 0
                    self.turning = True
                    self.turning_counter = 0

            if self.model.grid.is_cell_empty(next_pos):
                if self.turning:
                    self.turning_counter -= 1
                
                # if agent moves outside of grid remove agent
                if next_pos[0] < 0 or next_pos[0] > self.model.grid.width-2 or next_pos[1] < 0 or next_pos[1] > self.model.grid.width-2:
                    self.model.remove_agent(self)
                else:
                    self.model.grid.move_agent(self, next_pos)
            else:
                if self.turning:
                    self.turning_counter -= 1
    
class BuildingAgent(Agent):
    def __init__(self, unique_id, model, pos):
        super().__init__(unique_id, model)
        self.pos = pos
