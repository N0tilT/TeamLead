import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl
from typing import Dict

class FuzzyEngine:
    def __init__(self):
        self._init_variables()
        self._init_membership_functions()
        self._init_rules()
        self.system = ctrl.ControlSystem(self.rules)

    def _init_variables(self):
        self.volume = ctrl.Antecedent(np.arange(0, 1001, 1), "volume")
        self.dependencies = ctrl.Antecedent(np.arange(0, 16, 1), "dependencies")
        self.expertise = ctrl.Antecedent(np.arange(1, 6, 0.1), "expertise")
        self.uncertainty = ctrl.Antecedent(np.arange(0, 101, 1), "uncertainty")
        self.complexity = ctrl.Consequent(np.arange(0, 101, 1), "complexity")
        self.risk = ctrl.Consequent(np.arange(0, 101, 1), "risk")

    def _init_membership_functions(self):
        self.volume["low"] = fuzz.trimf(self.volume.universe, [0, 0, 200])
        self.volume["med"] = fuzz.trimf(self.volume.universe, [100, 500, 800])
        self.volume["high"] = fuzz.trimf(self.volume.universe, [600, 1000, 1000])

        self.dependencies["low"] = fuzz.trapmf(self.dependencies.universe, [0, 0, 3, 6])
        self.dependencies["mod"] = fuzz.trimf(self.dependencies.universe, [4, 8, 12])
        self.dependencies["high"] = fuzz.trapmf(self.dependencies.universe, [9, 15, 15, 15])

        self.expertise["low"] = fuzz.gaussmf(self.expertise.universe, 2.0, 0.7)
        self.expertise["med"] = fuzz.gaussmf(self.expertise.universe, 3.5, 0.7)
        self.expertise["high"] = fuzz.gaussmf(self.expertise.universe, 5.0, 0.7)

        self.uncertainty["clear"] = fuzz.trimf(self.uncertainty.universe, [0, 0, 40])
        self.uncertainty["part"] = fuzz.trimf(self.uncertainty.universe, [30, 60, 80])
        self.uncertainty["blurry"] = fuzz.trimf(self.uncertainty.universe, [60, 100, 100])

        self.complexity["low"] = fuzz.trimf(self.complexity.universe, [0, 0, 30])
        self.complexity["med"] = fuzz.trimf(self.complexity.universe, [20, 50, 70])
        self.complexity["high"] = fuzz.trimf(self.complexity.universe, [60, 85, 100])
        self.complexity["crit"] = fuzz.trimf(self.complexity.universe, [85, 100, 100])

        self.risk["low"] = fuzz.trimf(self.risk.universe, [0, 0, 25])
        self.risk["med"] = fuzz.trimf(self.risk.universe, [15, 50, 70])
        self.risk["high"] = fuzz.trimf(self.risk.universe, [60, 85, 100])
        self.risk["crit"] = fuzz.trimf(self.risk.universe, [80, 100, 100])

    def _init_rules(self):
        self.rules = [
            ctrl.Rule(self.volume["high"] & self.expertise["low"], self.complexity["crit"]),
            ctrl.Rule(self.volume["high"] & self.expertise["low"], self.risk["high"]),
            
            ctrl.Rule(self.dependencies["mod"] & self.uncertainty["clear"], self.complexity["med"]),
            ctrl.Rule(self.dependencies["mod"] & self.uncertainty["clear"], self.risk["low"]),
            
            ctrl.Rule(self.uncertainty["blurry"] & self.expertise["med"], self.complexity["high"]),
            ctrl.Rule(self.uncertainty["blurry"] & self.expertise["med"], self.risk["high"]),
            
            ctrl.Rule(self.volume["low"] & self.expertise["high"], self.complexity["low"]),
            ctrl.Rule(self.volume["low"] & self.expertise["high"], self.risk["low"]),
            
            ctrl.Rule(self.dependencies["high"], self.complexity["high"]),
            ctrl.Rule(self.dependencies["high"], self.risk["med"]),
            
            ctrl.Rule(self.uncertainty["part"] & self.expertise["low"], self.complexity["high"]),
            ctrl.Rule(self.uncertainty["part"] & self.expertise["low"], self.risk["high"])
        ]

    def evaluate(self, inputs: Dict[str, float]) -> Dict[str, float]:
        sim = ctrl.ControlSystemSimulation(self.system)
        sim.input["volume"] = inputs["volume"]
        sim.input["dependencies"] = inputs["dependencies"]
        sim.input["expertise"] = inputs["expertise"]
        sim.input["uncertainty"] = inputs["uncertainty"]
        sim.compute()
        return {
            "complexity_score": sim.output["complexity"],
            "risk_score": sim.output["risk"]
        }

fuzzy_engine = FuzzyEngine()