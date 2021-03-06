from mesa import Agent

import numpy as np

'''
This module describes the main agents used in CityModel:

- CarAgent
- BuildingAgent
- TrafficLightAgent
- IntersectionAgent

'''


class CarAgent(Agent):
    '''
    Creates a car agent inside the model grid.

    Arguments:
        - unique_id: car identifier
        - path: random optimal path calculated at birth
        - max_velocity: model level maximum velocity
        - tolerance: model level congestion tolerance

    Aditionally the folllowing parameters will be modified during execution:
        - congestion: congestion level calculated as velocity_sum/max_velocity_sum at each step
        - haste: 0 if not hasty, 1 if hasty
        - steps: amount of step an agent resides within the grid

    '''
    def __init__(self, model, unique_id, path, max_velocity, tolerance):
        super().__init__(unique_id, model)
        self.path = path
        self.pos_i = 0
        self.pos = path[self.pos_i]
        self.max_velocity = max_velocity
        self.velocity = max_velocity
        self.velocity_sum = 0
        self.max_velocity_sum = 0
        self.congestion = self.velocity/self.max_velocity

        self.haste = 0
        self.steps = 0
        self.tolerance = tolerance
        self.type = 0  # self.update_type()

    def accelerate(self, amount):
        self.velocity += int(amount)

    def decelerate(self, distance):
        if distance > 0:
            self.velocity = int(np.ceil(distance / 2))
        else:
            self.velocity = 0

    def destroy(self):
        self.model.grid.remove_agent(self)
        self.model.schedule.remove(self)
        self.model.num_car_agents -= 1

    def step(self):
        '''
        At each step the car agent updates its congestion level, checks if it is to become hasty
        and retrieves its next position in the path.

        Aditionally, the agent checks if there is a red traffic light agent, if True the agent stops; if False, the agent
        accelerates.

        Next the agent checks its distance relative to surrounding cars, if it is closer to a neighbouring car
        than it's velocity, the agent will decelarate.

        Finally, if the agent has not been stopped, it moves to its next position.
        '''
        self.update_congestion()
        self.update_haste()
        next_path = self.path[self.pos_i + 1:self.pos_i + self.max_velocity + 1]
        content: [TrafficLightAgent,
                  CarAgent] = self.model.grid.get_cell_list_contents(next_path)
        current = self.model.grid.get_cell_list_contents(self.pos)
        traffic_light = False

        # check if traffic light on current cell
        if isinstance(current[0], TrafficLightAgent):
            if current[0].state != 0:
                self.velocity = 0
                return
            else:
                self.accelerate(int(np.ceil(self.max_velocity - self.velocity)/2))

        # if object on next_path, act accordingly
        if content:
            next_obj = content[0]
            distance_to_next = next_path.index(next_obj.pos)
            if isinstance(next_obj, TrafficLightAgent):
                if len(content) > 1:
                    next_car = content[1]
                    if next_car.pos == next_obj.pos:
                        distance_to_next -= 1
                traffic_light = True

            if self.velocity > 0 and distance_to_next <= self.velocity:
                if traffic_light:
                    distance_to_next += 1
                self.decelerate(distance_to_next)
            elif self.velocity < self.max_velocity:
                if traffic_light:
                    distance_to_next += 1
                self.accelerate(np.ceil((self.max_velocity - self.velocity) / 2))
                if self.velocity > distance_to_next:
                    self.velocity = distance_to_next
                elif self.velocity > self.max_velocity:
                    self.velocity = self.max_velocity
            else:
                pass
        self.move(next_path)

    def move(self, next_path):
        """
        Moves agent velocity amount of steps, if end of grid reached, remove agent
        """
        if self.pos_i + self.velocity >= len(self.path):
            self.destroy()
        elif self.velocity > 0:
            self.model.grid.move_agent(self, next_path[self.velocity-1])
            self.pos_i += self.velocity
        else:
            pass

    def update_congestion(self):
        """
        Update congestion parameter for data collection
        """
        self.velocity_sum += self.velocity
        self.max_velocity_sum += self.max_velocity
        self.congestion = self.velocity_sum/self.max_velocity_sum
        self.steps += 1

    def update_haste(self):
        """
        Update haste parameter of agent
        """
        haste_probability = (self.velocity_sum/self.steps)/self.max_velocity

        if self.steps > 10:
            if self.congestion < self.tolerance and np.random.uniform() < haste_probability:
                # agent is hasty, increase max velocity
                self.haste = 1
                self.max_velocity = self.max_velocity + int(np.ceil(self.max_velocity * 0.25))
                if self.velocity > self.max_velocity:
                    self.velocity = self.max_velocity
            else:
                if self.haste != 0:
                    # agent is "normal" again, decrease velocity
                    self.haste = 0
                    self.max_velocity = 5
                    if self.velocity > self.max_velocity:
                        self.velocity = self.max_velocity

    def update_type(self):
        """
        Update type of agent
        """
        if np.random.uniform() < 0.10:
            if np.random.uniform() < 0.3:
                # patient
                self.max_velocity = self.max_velocity - 1
                self.tolerance_1 = self.tolerance_1 + 0.1
                self.tolerance_2 = self.tolerance_2 + 0.15
                if self.velocity > self.max_velocity:
                        self.velocity = self.max_velocity
                return 1
            else:
                # inpatient
                self.max_velocity = self.max_velocity + 2
                self.tolerance_1 = self.tolerance_1 - 0.1
                self.tolerance_2 = self.tolerance_2 - 0.15
                if self.velocity > self.max_velocity:
                        self.velocity = self.max_velocity
                return 2
        else:
            return 0


class BuildingAgent(Agent):
    ''' 
    Creates a building agent whose only attributes are a unique_id and its position:
        - pos: (x,y) coordinates in the model grid
    '''
    def __init__(self, unique_id, model, pos):
        super().__init__(unique_id, model)
        self.pos = pos


class IntersectionAgent(Agent):
    '''
    Creates an intersection agent, where the traffic lights live.

    Arguments:
     - unique_id: agents' identifier
     - pos: (x,y) coordinates in the model grid
     - green_light_duration: duration of green/red light for a given TrafficLightAgent inside the IntersectionAgent

    '''
    def __init__(self, unique_id, model, pos, green_light_duration):
        super().__init__(unique_id, model)
        self.model = model
        self.unique_id = unique_id
        self.pos = pos
        self.counter = 0
        traffic_light_positions = [(pos[0] - 1, pos[1]),
                                   (pos[0] + 1, pos[1] - 1),
                                   (pos[0] + 2, pos[1] + 1),
                                   (pos[0], pos[1] + 2)]
        self.traffic_lights = []
        for i in range(2):
            tlight1 = TrafficLightAgent(self.model.get_new_unique_id(
            ), self.model, traffic_light_positions[2*i], state=2)
            tlight2 = TrafficLightAgent(self.model.get_new_unique_id(
            ), self.model, traffic_light_positions[2*i+1], state=0)
            self.traffic_lights.append(tlight1)
            self.traffic_lights.append(tlight2)

        self.green_duration = green_light_duration
        self.yellow_duration = 2

    def step(self):
        if self.yellow_duration > 0:
            if self.counter == self.green_duration:
                for tl in self.traffic_lights:
                    if tl.state == 0:
                        tl.switch()
            elif self.counter == self.green_duration + self.yellow_duration:
                for tl in self.traffic_lights:
                    tl.switch()
                self.counter = 0
        else:
            if self.counter == self.green_duration:
                for tl in self.traffic_lights:
                    tl.switch(include_yellow=False)
                self.counter = 0
        self.counter += 1


class TrafficLightAgent(Agent):
    '''
    Creates a traffic light inside the model grid.

    Arguments:
        - unique_id: agents' identifier
        - pos: (x,y) coordinates in the model grid
        - state: 0 if green, 1 if yellow, 2 if red
    '''
    def __init__(self, unique_id, model, pos, state):
        super().__init__(unique_id, model)
        self.colors = {0: 'green', 1: 'yellow', 2: 'red'}
        self.state = state
        self.pos = pos

    def switch(self, include_yellow=True):
        if include_yellow:
            if self.state == 2:
                self.state = 0
            else:
                self.state += 1
        else:
            if self.state == 2:
                self.state = 0
            else:
                self.state = 2