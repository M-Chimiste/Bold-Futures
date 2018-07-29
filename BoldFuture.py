# StarCraft II Bot AI
# AI Class is Terran
import sc2
from sc2 import run_game, maps, Race, Difficulty
from sc2.player import Bot, Computer
from sc2.constants import COMMANDCENTER, SUPPLYDEPOT, REFINERY, BARRACKS, SCV


class TerrBot(sc2.BotAI):
    
    async def on_step(self, iteration):
        # As each step occurs do the following:
        await self.distribute_workers() # Will take workers and distribute them.
        await self.build_workers() # Start making new workers
        await self.build_supplydepots() # Start making supply depots to allow for more units
        await self.expand()
        await self.build_refinery()
    

    # Function to build workers (SCVs)
    async def build_workers(self):
        for cmdCenter in self.units(COMMANDCENTER).ready.noqueue:
            if self.can_afford(SCV):
                await self.do(cmdCenter.train(SCV))
    

    async def build_supplydepots(self):
        if self.supply_left < 5 and not self.already_pending(SUPPLYDEPOT):
            cmdCenter = self.units(COMMANDCENTER).ready
            if cmdCenter.exists:
                if self.can_afford(SUPPLYDEPOT):
                    await self.build(SUPPLYDEPOT, near=cmdCenter.first)

    
    async def expand(self):
        if self.units(COMMANDCENTER).amount < 2 and self.can_afford(COMMANDCENTER):
            await self.expand_now()
    

    async def build_refinery(self):
        for cmdCenter in self.units(COMMANDCENTER).ready:
            vespeneGas = self.state.vespene_geyser.closer_than(25.0, cmdCenter)
            for vespene in vespeneGas:
                if not self.can_afford(REFINERY):
                    break
                worker = self.select_build_worker(vespene.position)
                if worker is None:
                    break
                if not self.units(REFINERY).closer_than(1.0, vespene).exists:
                    await self.do(worker.build(REFINERY, vespene))



run_game(maps.get("Abyssal Reef LE"), [
    Bot(Race.Terran, TerrBot()), Computer(Race.Protoss, Difficulty.Easy)
], realtime=False)