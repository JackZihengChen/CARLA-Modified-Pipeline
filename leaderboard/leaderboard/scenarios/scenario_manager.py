#!/usr/bin/env python

# Copyright (c) 2018-2020 Intel Corporation
#
# This work is licensed under the terms of the MIT license.
# For a copy, see <https://opensource.org/licenses/MIT>.

"""
This module provides the ScenarioManager implementations.
It must not be modified and is for reference only!
"""

from __future__ import print_function
import signal
import sys
import time

import py_trees
import carla

from srunner.scenariomanager.carla_data_provider import CarlaDataProvider
from srunner.scenariomanager.timer import GameTime
from srunner.scenariomanager.watchdog import Watchdog

from leaderboard.autoagents.agent_wrapper import AgentWrapper, AgentError
from leaderboard.envs.sensor_interface import SensorReceivedNoData
from leaderboard.utils.result_writer import ResultOutputProvider


class ScenarioManager(object):

    """
    Basic scenario manager class. This class holds all functionality
    required to start, run and stop a scenario.

    The user must not modify this class.

    To use the ScenarioManager:
    1. Create an object via manager = ScenarioManager()
    2. Load a scenario via manager.load_scenario()
    3. Trigger the execution of the scenario manager.run_scenario()
       This function is designed to explicitly control start and end of
       the scenario execution
    4. If needed, cleanup with manager.stop_scenario()
    """


    def __init__(self, timeout, debug_mode=False, control_log_path=None):
        """
        Setups up the parameters, which will be filled at load_scenario()
        """
        self.scenario = None
        self.scenario_tree = None
        self.scenario_class = None
        self.ego_vehicles = None
        self.other_actors = None

        self._debug_mode = debug_mode
        self._agent = None
        self._running = False
        self._timestamp_last_run = 0.0
        self._timeout = float(timeout)

        # Used to detect if the simulation is down
        watchdog_timeout = max(5, self._timeout - 2)
        self._watchdog = Watchdog(watchdog_timeout)

        # Avoid the agent from freezing the simulation
        agent_timeout = watchdog_timeout - 1
        self._agent_watchdog = Watchdog(agent_timeout)

        self.scenario_duration_system = 0.0
        self.scenario_duration_game = 0.0
        self.start_system_time = None
        self.end_system_time = None
        self.end_game_time = None

        # Register the scenario tick as callback for the CARLA world
        # Use the callback_id inside the signal handler to allow external interrupts
        signal.signal(signal.SIGINT, self.signal_handler)

        # create the control log file that overwrites the old file and write the header row
        self.control_log_path = control_log_path
        self.trajectory_log_path = control_log_path
        self.cvip_log_path = control_log_path
        self.points_log_path = control_log_path
        self.pid_delta_log_path = control_log_path
        self.unclipped_control_log_path = control_log_path
        if self.control_log_path:
            control_log_path_base = control_log_path.split(".")[0]
            self.control_log_path = control_log_path_base + "_ctl.csv"
            print("\ncreating control dump file at:", self.control_log_path)
            with open(self.control_log_path, 'w') as control_log_file:
                control_log_file.write("ts,agent_id,throttle,steer,brake\n")

            self.trajectory_log_path = control_log_path_base + "_traj.csv"
            print("\ncreating ego trajectory dump file at:", self.trajectory_log_path)
            with open(self.trajectory_log_path, 'w') as trajectory_log_file:
                trajectory_log_file.write("ts,agent_id,x,y,z,v\n")

            self.cvip_log_path = control_log_path_base + "_cvip.csv"
            print("\ncreating cvip dump file at:", self.cvip_log_path)
            with open(self.cvip_log_path, 'w') as cvip_log_file:
                cvip_log_file.write("ts,agent_id,cvip,cvip_x,cvip_y,cvip_z\n")
            
            print("\ndone creating dump files.")

    def signal_handler(self, signum, frame):
        """
        Terminate scenario ticking when receiving a signal interrupt
        """
        self._running = False

    def cleanup(self):
        """
        Reset all parameters
        """
        self._timestamp_last_run = 0.0
        self.scenario_duration_system = 0.0
        self.scenario_duration_game = 0.0
        self.start_system_time = None
        self.end_system_time = None
        self.end_game_time = None

    def load_scenario(self, scenario, agent, rep_number):
        """
        Load a new scenario
        """

        GameTime.restart()
        self._agent = AgentWrapper(agent)
        self.scenario_class = scenario
        self.scenario = scenario.scenario
        self.scenario_tree = self.scenario.scenario_tree
        self.ego_vehicles = scenario.ego_vehicles
        self.other_actors = scenario.other_actors
        self.repetition_number = rep_number

        # To print the scenario tree uncomment the next line
        # py_trees.display.render_dot_tree(self.scenario_tree)

        self._agent.setup_sensors(self.ego_vehicles[0], self._debug_mode)

    def run_scenario(self):
        """
        Trigger the start of the scenario and wait for it to finish/fail
        """
        self.start_system_time = time.time()
        self.start_game_time = GameTime.get_time()

        self._watchdog.start()
        self._running = True

        while self._running:
            timestamp = None
            world = CarlaDataProvider.get_world()
            if world:
                snapshot = world.get_snapshot()
                if snapshot:
                    timestamp = snapshot.timestamp
            if timestamp:
                self._tick_scenario(timestamp)

    def _find_cvip(self, actor_list):
        if len(actor_list) == 1 and self.ego_vehicles[0] in actor_list:
            return None, None, None, None
        ego_location = CarlaDataProvider.get_location(self.ego_vehicles[0])
        cvip = float('inf')
        x = float('inf')
        y = float('inf')
        z = float('inf')
        for actor in actor_list:
            if self.ego_vehicles[0] != actor:
                actor_location = CarlaDataProvider.get_location(actor)
                dist = (ego_location.x - actor_location.x)**2 + (ego_location.y - actor_location.y)**2 + (ego_location.z - actor_location.z)**2
                dist = dist ** 0.5
                if dist < cvip:
                    cvip = dist
                    x = actor_location.x
                    y = actor_location.y
                    z = actor_location.z
        return cvip, x, y, z
    
    def _tick_scenario(self, timestamp):
        """
        Run next tick of scenario and the agent and tick the world.
        """

        if self._timestamp_last_run < timestamp.elapsed_seconds and self._running:
            self._timestamp_last_run = timestamp.elapsed_seconds

            self._watchdog.update()
            # Update game time and actor information
            GameTime.on_carla_tick(timestamp)
            CarlaDataProvider.on_carla_tick()

            try:
                ego_action = self._agent()
                agent = 0
                
                # log agent control signal
                if self.control_log_path:
                    with open(self.control_log_path, "a") as control_log_file:
                        control_log_file.write("{},{},{},{},{}\n".format(timestamp.frame, agent,
                                                                            ego_action.throttle,
                                                                            ego_action.steer,
                                                                            ego_action.brake))

                # also dumping agent trojectory
                live_actors = CarlaDataProvider._carla_actor_pool.values()
                if self.trajectory_log_path:
                    ego_location = CarlaDataProvider.get_location(self.ego_vehicles[0])
                    ego_velocity = CarlaDataProvider.get_velocity(self.ego_vehicles[0])
                    with open(self.trajectory_log_path, "a") as trajectory_log_file:
                        trajectory_log_file.write("{},{},{},{},{},{}\n".format(timestamp.frame, agent,
                                                                               ego_location.x,
                                                                               ego_location.y,
                                                                               ego_location.z,
                                                                               ego_velocity))
                
                # calculate the closest vehicle in path
                cvip, cvip_x, cvip_y, cvip_z = self._find_cvip(CarlaDataProvider._carla_actor_pool.values())
                if self.cvip_log_path and cvip:
                    with open(self.cvip_log_path, "a") as cvip_log_file:
                        cvip_log_file.write("{},{},{},{},{},{}\n".format(timestamp.frame, agent, cvip, cvip_x, cvip_y, cvip_z))

            # Special exception inside the agent that isn't caused by the agent
            except SensorReceivedNoData as e:
                raise RuntimeError(e)

            except Exception as e:
                raise AgentError(e)

            self.ego_vehicles[0].apply_control(ego_action)

            # Tick scenario
            self.scenario_tree.tick_once()

            if self._debug_mode:
                print("\n")
                py_trees.display.print_ascii_tree(
                    self.scenario_tree, show_status=True)
                sys.stdout.flush()

            if self.scenario_tree.status != py_trees.common.Status.RUNNING:
                self._running = False

            spectator = CarlaDataProvider.get_world().get_spectator()
            ego_trans = self.ego_vehicles[0].get_transform()
            spectator.set_transform(carla.Transform(ego_trans.location + carla.Location(z=50),
                                                        carla.Rotation(pitch=-90)))

        if self._running and self.get_running_status():
            CarlaDataProvider.get_world().tick(self._timeout)

    def get_running_status(self):
        """
        returns:
           bool: False if watchdog exception occured, True otherwise
        """
        return self._watchdog.get_status()

    def stop_scenario(self):
        """
        This function triggers a proper termination of a scenario
        """
        self._watchdog.stop()

        self.end_system_time = time.time()
        self.end_game_time = GameTime.get_time()

        self.scenario_duration_system = self.end_system_time - self.start_system_time
        self.scenario_duration_game = self.end_game_time - self.start_game_time

        if self.get_running_status():
            if self.scenario is not None:
                self.scenario.terminate()

            if self._agent is not None:
                self._agent.cleanup()
                self._agent = None

            self.analyze_scenario()

    def analyze_scenario(self):
        """
        Analyzes and prints the results of the route
        """
        global_result = '\033[92m'+'SUCCESS'+'\033[0m'

        for criterion in self.scenario.get_criteria():
            if criterion.test_status != "SUCCESS":
                global_result = '\033[91m'+'FAILURE'+'\033[0m'

        if self.scenario.timeout_node.timeout:
            global_result = '\033[91m'+'FAILURE'+'\033[0m'

        ResultOutputProvider(self, global_result)
