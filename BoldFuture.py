# StarCraft II Bot AI
# AI Class is Protoss
import sc2
import random
from sc2 import run_game, maps, Race, Difficulty
from sc2.player import Bot, Computer
from sc2.constants import *
import random
import cv2
import time
import math
import numpy as np
import os
import keras


HEADLESS = False


class Botty(sc2.BotAI):

    def __init__(self, use_model=False, title=1):
        self.maxWorkers = 60
        self.use_model = use_model
        self.title = title
        self.scoutingReport = {}

        # Bot's possible choices
        self.choice = {
            0: self.build_workers,
            1: self.build_pylons,
            2: self.attack_known_enemy_unit,
            3: self.attack_known_enemy_structure,
            4: self.expand,
            5: self.build_gateway,
            6: self.build_zealot,
            7: self.build_stalker,
            8: self.build_voidray,
            9: self.build_assimilators,
            10: self.build_robotics_facility,
            11: self.build_observer,
            12: self.defend_nexus,
            13: self.build_stargate,
            14: self.build_cybernetics,
            15: self.build_colossus
        }
        self.trainingData = []

        if self.use_model:
            self.model = keras.model.load_model("Starcraft_Protoss_Model")
    

    # Record wins and losses
    def on_end(self, game_result):
        print('---Game On End Called---')
        print(game_result, self.use_model)
        with open("gameout-random-vs-medium.txt", 'a') as f:
            if self.use_model:
                f.write("Model {} - {}\n".format(game_result, int(time.time())))
            else:
                f.write("Random {} -{}\n".format(game_result, int(time.time())))

    
    async def on_step(self, iteration):
        self.time = (seld.state.game_loop/22.4) / 60 # helps keep track of time (even if not in real time)
        # As each step occurs do the following:
        await self.distribute_workers()  # Will take workers and distribute them.
        await self.scout()
        await self.intel()
        await self.do_stuff()


    # Function will take a location add variance to it "Randomly" then return the point
    def random_location_variance(self, location):
        x = location[0]
        y = location[1]

        x += random.randrange(-5,5)
        y += random.randrange(-5,5)

        if x < 0:
            x = 0  # Because we can't have negative coordinates or we get happy errors
        if x > self.game_info.map_size[0]:
            x = self.game_info.map_size[0]  # Beacause we have to stay on the map or we get happy errors
        
        if y < 0:
            y = 0
        if y > self.game_info.map_size[1]:
            y = self.game_info.map_size[1]
        
        randPos = position.Point2(position.Pointlike((x,y)))
        return randPos
        
    
    async def scout(self):
        self.expand_dis_dir = {}
        for i in self.expansion_locations:
            distance_to_enemy_start = i.distance_to(self.enemy_start_locations[0])
            self.expand_dis_dir[distance_to_enemy_start] = i
        
        self.ordered_exp_distances = sorted(k for k in self.expand_dis_dir)

        existing_ids = [unit.tag for unit in self.units]
        removed_units = []
        for scouts in self.scoutingReport:
            if scouts not in existing_ids:
                removed_units.append(scouts)
        
        for scout in removed_units:
            del self.scoutingReport[scout]
        
        # Check if we can use observers
        if len(self.units(ROBOTICSFACILITY).ready) == 0:
            unit_type = PROBE
            unit_limit = 1
        else:
            unit_type = OBSERVER
            unit_limit = 15
        
        assign_scout = True

        # Assign scout tag as false to all probes before drafting one into service.  We only want one after all.
        if unit_type == PROBE:
            for unit in self.units(PROBE):
                if unit.tag in self.scoutingReport:
                    assign_scout = False
        
        if assign_scout:
            if len(self.units(unit_type).idle) > 0:
                for obs in self.units(unit_type).idle[:unit_limit]:
                    if obs.tag not in self.scoutingReport:
                        for dist in self.ordered_exp_distances:
                            try:
                                location = next(value for key in self.expand_dis_dir.items() if key == dist)
                                active_locations = [self.scoutingReport[k] for k in self.scoutingReport]

                                if location not in active_locations:
                                    if unit_type == PROBE:
                                        for unit in self.units(PROBE):
                                            if unit.tag in self.scoutingReport:
                                                continue

                                    await self.do(obs.move(location))
                                    self.scoutingReport[obs.tag] = location
                                    break
                            except Exception as e:
                                print(e)
                                pass

        for obs in self.units(unit_type):
            if obs.tag in self.scoutingReport:
                if obs in [probe for probe in self.units(PROBE)]:
                    await self.do(obs.move(self.random_location_variance(self.scoutingReport[obs.tag])))
    

    async def intel(self):

        game_data = np.zeros((self.game_info.map_size[1], self.game_info.map_size[0], 3), np.uint8)

        draw_dict = {
            NEXUS: [15, (0,255,0)],
            PYLON: [3, (20,235,0)],
            PROBE: [1, (55,200,0)],
            ASSIMILATOR: [2, (55,170,0)],
            GATEWAY: [3, (200,100,0)],
            CYBERNETICSCORE: [3, (150,150,0)],
            STARGATE: [5, (255,0,0)],
            ROBOTICSFACILITY: [5, (215,155,0)],
            #TODO Add friendly offensive units?
        }

        for unit_type in draw_dict:
            for i in self.units(unit_type).ready:
                position = i.position
                cv2.circle(game_data, (int(position[0]), int(position[1])), draw_dict[unit_type][0], draw_dict[unit_type][1], -1 )
        
        bases = ['nexus', 'orbitalcommand', 'planetaryfortress', 'hatchery']
        for enemy_building in self.known_enemy_structures:
            position = enemy_building.position
            if enemy_building.name.lower() not in bases:
                cv.circle(game_data, (int(position[0]), int(position[1])), 5, (200, 50, 212), -1)
        
        for enemy_building in self.known_enemy_structures:
            position = enemy_building.position
            if enemy_building.name.lower() in bases:
                cv2.circle(game_data, (int(position[0]), int(position[1])), 15, (0,0,255), -1)
        
        for enemy_unit in self.known_enemy_units:
            if enemy_unit.is_structure:
                worker_names = ['probe', 'scv', 'drone']
                position = enemy_unit.position
                if enemy_unit.name.lower() in worker_names:
                    cv2.circle(game_data, (int(position[0]), int(position[1])), 1, (55, 0, 155), -1)
                else:
                    cv2.circle(game_data, (int(position[0]), int(position[1])), 3, (255, 100, 0), -1)
        
        for obs in self.units(OBSERVER).ready:
            position = obs.position
            cv2.circle(game_data, (int(position[0]), int(position[1])), 1, (255, 255, 255), -1)
        
        self.flipped = cv2.flip(game_data, 0)
        resized = cv2.resize(self.flipped, dsize=None, fx=2, fy=2)


        if not HEADLESS:
            cv2.imshow(str(self.title), resized)
            cv2.waitKey(1)


    # Function to build workers
    async def build_workers(self):
        for cmdCenter in self.units(NEXUS).ready.noqueue:
            if self.can_afford(PROBE) and self.units(PROBE).amount < 50: #Spam SCVs if under 50
                await self.do(cmdCenter.train(PROBE))
               
    

    # Function to build supply depots
    async def build_pylons(self):
        if self.supply_left < 5 and not self.already_pending(PYLON): 
            cmdCenter = self.units(NEXUS).ready
            if cmdCenter.exists:
                if self.can_afford(PYLON):
                    cmdCenter = self.units(NEXUS).ready.random
                    await self.build(PYLON, near=cmdCenter.position.towards(self.game_info.map_center, 15)) #potentially better strategy for placement?
                        
   
    # Function to trigger an expansion of the base
    async def expand(self):
        try:
            if self.can_afford(NEXUS):
                await self.expand_now()
        except Exception as e:
            print(str(e))
            pass

    
    # Function to evaluate location and build assimilator on vespene gas drops
    async def build_assimilators(self):
        for cc in self.units(NEXUS).ready:
            vespeneGas = self.state.vespene_geyser.closer_than(15.0, cc)  # 15 is totally a made up number
            for i in vespeneGas:
                if not self.can_afford(ASSIMILATOR):
                    break
                workers = self.select_build_worker(i.position)
                if workers is None:
                    break
                if not self.units(ASSIMILATOR).closer_than(1.0, i). exists:
                    await self.do(workers.build(ASSIMILATOR, i))
                    
        

    # Function to build a gateway so we can train offensive units
    async def build_gateway(self):
        if self.units(PYLON).ready.exists:
            pylons = self.units(PYLON).ready.random # pick a random supply depot to build by
            if self.can_afford(GATEWAY) and not self.already_pending(GATEWAY):
                await self.build(GATEWAY, near=pylons) #.position.towards(self.game_info.map_center,-3)


    async def build_cybernetics(self):
        if self.units(GATEWAY).ready.exists: 
            pylon = self.units(PYLON).ready.random # pick a random pylon to build by
            if self.can_afford(CYBERNETICSCORE) and not self.already_pending(CYBERNETICSCORE):
                await self.build(CYBERNETICSCORE, near=pylon)


    async def build_stargate(self):
        if self.units(CYBERNETICSCORE).ready.exists:  
            pylon = self.units(PYLON).ready.random # pick a random supply depot to build by
            if self.can_afford(STARGATE) and not self.already_pending(STARGATE):
                await self.build(STARGATE, near=pylon)
    

    async def build_robotics_facility(self):
        if self.units(CYBERNETICSCORE).ready.exists:
            pylon = self.units(PYLON).ready.random
            if self.can_afford(ROBOTICSFACILITY) and not self.already_pending(ROBOTICSFACILITY):
                await self.build(ROBOTICSFACILITY, near=pylon)


    # Functions to start generating offensive units
    async def build_stalker(self):
        gateway = self.units(GATEWAY).ready
        if gateway.exists:
            if self.can_afford(STALKER) and self.supply_left > 0:
                await self.do(random.choice(gateway).train(STALKER))
    
    
    async def build_zealot(self):
        gateway = self.units(GATEWAY).ready
        if gateway.exists:
            if self.can_afford(ZEALOT) and self.supply_left > 0:
                await self.do(random.choice(gateway).train(ZEALOT))

        
    async def build_voidray(self):
        stargate = self.units(STARTGATE).ready
        if stargate.exists:
            if self.can_afford(VOIDRAY) and supply_left > 0:            
                await self.do(random.choice(stargate).train(VOIDRAY))


    async def build_colossus(self):
        robotics = self.units(ROBOTICSFACILITY).ready
        if robotics.exits:
            if self.can_afford(COLOSSUS) and supply_left > 0:
                await self.do(random.choice(robotics).train(COLOSSUS))
    
    
    # builds a scout type unit
    async def build_observer(self):
        robotics = self.units(ROBOTICSFACILITY).ready
        if robotics.exits:
            if self.can_afford(OBSERVER) and supply_left > 0:
                await self.do(random.choice(robotics).train(OBSERVER))


    #Attacking choices (nothing, defend, attack units, attack structure)
    async def do_nothing(self):
        waiting_time = random.randrange(7, 100) / 100
        self.do_something_after = self.time + waiting_time
    

    async def defend_nexus(self):
        if len(self.known_enemy_units) > 0:
            target = self.known_enemy_units.closest_to(random.choice(self.units(NEXUS)))
            total_zealots = self.units(ZEALOT).amount
            total_stalkers = self.units(STALKER).amount
            total_voidray = self.units(VOIDRAY).amount
            total_colossus = self.units(COLOSSUS).amount
            total_army = total_zealots + total_stalkers + total_voidray + total_colossus
            
            #If there is nothing left go attack with everything you have
            if total_army == 0:
                for workers in self.units(PROBE):
                    await self.do(workers.attack(target))
            if total_army > 0:
                for zealot in self.units(ZEALOT).idle:
                    await self.do(zealot.attack(target))
                for stalker in self.units(STALKER).idle:
                    await self.do(stalker.attack(target))
                for voidray in self.units(VOIDRAY).idle:
                    await self.do(voidray.attack(target))
                for colossus in self.units(COLOSSUS).idle:
                    await self.do(colossus.attack(target))
    

    async def attack_known_enemy_structure(self):
        if len(self.known_enemy_structures) > 0:
            target = random.choice(self.known_enemy_structures)
            for zealot in self.units(ZEALOT).idle:
                await self.do(zealot.attack(target))
            for stalker in self.units(STALKER).idle:
                await self.do(stalker.attack(target))
            for voidray in self.units(VOIDRAY).idle:
                await self.do(voidray.attack(target))
            for colossus in self.units(COLOSSUS).idle:
                await self.do(colossus.attack(target))
    

    async def attack_known_enemy_unit(self):
        if len(self.known_enemy_units) > 0:
            target = self.known_enemy_units.closest_to(random.choice(self.units(NEXUS)))
            for zealot in self.units(ZEALOT).idle:
                await self.do(zealot.attack(target))
            for stalker in self.units(STALKER).idle:
                await self.do(stalker.attack(target))
            for voidray in self.units(VOIDRAY).idle:
                await self.do(voidray.attack(target))
            for colossus in self.units(COLOSSUS).idle:
                await self.do(colossus.attack(target))


    async def do_stuff(self):
        if self.time > self.do_something_after:
            if self.use_model:
                decision = self.model.predict([self.flipped.reshape([-1, 176, 200, 3])])
                choice = np.argmax(decision[0])
            else:
                choice = random.randrange(0,16)
            try:
                await self.choices[choice]()
            except Exception as e:
                print(str(e))
            y = np.zeros(16)
            y[choice] = 1
            self.trainingData.append([y,self.flipped])



run_game(maps.get("Abyssal Reef LE"), [
    Bot(Race.Protoss, Botty(use_model=False, title=1)), Computer(Race.Terran, Difficulty.Medium)
], realtime=False)