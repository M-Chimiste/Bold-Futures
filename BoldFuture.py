# StarCraft II Bot AI
# AI Class is Terran
import sc2
import random
from sc2 import run_game, maps, Race, Difficulty
from sc2.player import Bot, Computer
from sc2.constants import *


class Botty(sc2.BotAI):
    
    async def on_step(self, iteration):
        # As each step occurs do the following:
        await self.distribute_workers()  # Will take workers and distribute them.
        await self.build_workers()  # Start making new workers
        await self.build_supplydepots()  # Start making supply depots to allow for more units
        await self.expand()  # Expands the AI base
        await self.build_refinery()  # Builds a refinery on a vespene gas drop
        await self.build_offensive_bldgs() #
        await self.build_army()   # Start making marines and tanks
        await self.attack_baddies()  # Take the army and go attack bad guys/ TODO make more robust
        await self.upgrade_building()
    

    # quick and dirty function that will allow for checking if things are upgraded...
    def add_on_name(self, structure):
        if structure.add_on_tag != 0:
            return self.units.find_by_tag(structure.add_on_tag).add_on_name
        else:
            return "None"

    # Function to build workers (SCVs)
    async def build_workers(self):
        for cmdCenter in self.units(COMMANDCENTER).ready.noqueue:
            if self.can_afford(SCV) and self.units(SCV).amount < 50: #Spam SCVs if under 50
                await self.do(cmdCenter.train(SCV))
    

    # Function to build supply depots
    async def build_supplydepots(self):
        if self.supply_left < 5 and not self.already_pending(SUPPLYDEPOT): 
            cmdCenter = self.units(COMMANDCENTER).ready
            if cmdCenter.exists:
                if self.can_afford(SUPPLYDEPOT):
                    await self.build(SUPPLYDEPOT, near=cmdCenter.towards(self.game_info.map_center, 15)) #potentially better strategy for placement?

    
    # Function to trigger an expansion of the base
    #TODO will need to evaluate logic for when to expand
    async def expand(self):
        if self.units(COMMANDCENTER).amount < 3 and self.can_afford(COMMANDCENTER):  # 3-4 is made up, may not make sense....  Maybe a random number that is used for learning?
            await self.expand_now()
    

    # Function to evaluate location and build refinery on vespene gas drops
    async def build_refinery(self):
        for cc in self.units(COMMANDCENTER).ready:
            vespeneGas = self.state.vespene_geyser.closer_than(15.0, cc)  # 15 is totally a made up number
            for i in vespeneGas:
                if not self.can_afford(REFINERY):
                    break
                SCVs = self.select_build_worker(i.position)
                if SCVs is None:
                    break
                if not self.units(REFINERY).closer_than(1.0, i). exists:
                    await self.do(SCVs.build(REFINERY, i))
        

    # Function to build a Barracks so we can train soldiers
    async def build_offensive_bldgs(self):
        # build a barracks first
        if self.units(SUPPLYDEPOT).ready.exists:
            supplyDepot = self.units(SUPPLYDEPOT).ready.random # pick a random supply depot to build by
            if not self.units(BARRACKS).exists or self.units(BARRACKS).amount < 3:
                if self.can_afford(BARRACKS) and not self.already_pending(BARRACKS):
                    await self.build(BARRACKS, near=supplyDepot.position.towards(self.game_info.map_center,-3))

        if self.units(BARRACKS).ready.exists:  #Invalid syntax error TODO FIX... why?
            barracks = self.units(SUPPLYDEPOT).ready.random # pick a random supply depot to build by
            if not self.units(FACTORY).exists or self.units(BARRACKS).amount < 3:
                if self.can_afford(FACTORY) and not self.already_pending(FACTORY):
                    await self.build(FACTORY, near=barracks.position.towards(self.game_info.map_center,-10))
            

    async def upgrade_building(self):
        if self.units(BARRACKS).ready.exists:
            for barracks in self.units(BARRACKS).ready.noqueue:
                if self.already_pending(BARRACKSTECHLAB) or not self.can_afford(BARRACKSTECHLAB):
                    break
                if self.can_afford(BARRACKSTECHLAB) and barracks.add_on_tag == 0:
                    await self.do(barracks.build(BARRACKSTECHLAB))
        if self.units(FACTORY).ready.exists:    
            for factory in self.units(FACTORY).ready.noqueue:
                if self.already_pending(FACTORYTECHLAB) or not self.can_afford(FACTORYTECHLAB):
                    break
                if self.can_afford(FACTORYTECHLAB) and factory.add_on_tag == 0:
                    await self.do(factory.build(FACTORYTECHLAB))
        

    # Function to start generating offensive units
    async def build_army(self):
        marines = float(len(self.units(MARINE)))
        tanks = float(len(self.units(SIEGETANK)))
        if self.units(BARRACKS).ready.exists:
            for barracks in self.units(BARRACKS).ready.noqueue:
                if not self.can_afford(MARINE):
                    break
                if self.can_afford(MARINE) and self.supply_left > 0:
                    await self.do(barracks.train(MARINE))
        if self.units(FACTORY).ready.exists and self.can_afford(HELLION):
            for factory in self.units(FACTORY).ready.noqueue:
                if (tanks/marines) < 0.33:  # May need tweaking, randomly assigned
                    if self.can_afford(HELLION) and self.supply_left > 0:
                        await self.do(factory.train(HELLION))

    # Function to find baddies
    def find_target(self, state):
        if len(self.known_enemy_units) > 0:
            return random.choice(self.known_enemy_units)
        elif len(self.known_enemy_structures) > 0:
            return random.choice(self.known_enemy_structures)
        else:
            return self.enemy_start_locations[0]


    # Function to attack bad guys
    async def attack_baddies(self):
        # Conduct a raid
        if self.units(MARINE).amount > 3 and self.units(HELLION).amount >= 0:
            if len(self.known_enemy_units) > 0:
                for m in self.units(MARINE).idle:
                    await self.do(m.attack(self.find_target(self.state)))
                for t in self.units(HELLION):
                    await self.do(t.attack(self.find_target(self.state)))
        
        # Conduct a battle
        if self.units(MARINE).amount > 5 and self.units(HELLION).amount > 1:
            for m in self.units(MARINE).idle:
                    await self.do(m.attack(self.find_target(self.state)))
            for t in self.units(HELLION):
                await self.do(t.attack(self.find_target(self.state)))
    




run_game(maps.get("Abyssal Reef LE"), [
    Bot(Race.Terran, Botty()), Computer(Race.Protoss, Difficulty.Easy)
], realtime=True)