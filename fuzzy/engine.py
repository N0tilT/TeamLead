import os
import json
import time
import numpy as np
import pandas as pd
import skfuzzy as fuzz
from skfuzzy import control as ctrl
from scipy import stats
from datetime import datetime
from loguru import logger
from typing import Dict, List, Optional, Tuple, Any
import optuna

class FuzzyAgent:
    def __init__(self, config_path: str, name: str):
        self.name = name
        self.config_path = config_path
        self.config = self._load_config(config_path)
        self.feedback_history: List[Dict] = []
        self._build_system()

    def _load_config(self, path: str) -> Dict:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    def _build_system(self):
        cfg = self.config
        self.antecedents = {}
        for var_name, mf_cfg in cfg["antecedents"].items():
            u_min, u_max, step = cfg["universes"][var_name]
            universe = np.arange(u_min, u_max + step, step)
            ant = ctrl.Antecedent(universe, var_name)
            for label, params in mf_cfg.items():
                if params["type"] == "trimf":
                    ant[label] = fuzz.trimf(ant.universe, params["params"])
                elif params["type"] == "trapmf":
                    ant[label] = fuzz.trapmf(ant.universe, params["params"])
                elif params["type"] == "gaussmf":
                    ant[label] = fuzz.gaussmf(ant.universe, params["params"][0], params["params"][1])
            self.antecedents[var_name] = ant

        c_univ = cfg["consequent"]["universe"]
        cons_universe = np.arange(c_univ[0], c_univ[1] + c_univ[2], c_univ[2])
        self.consequent = ctrl.Consequent(cons_universe, cfg["consequent"]["name"])
        self.consequent.defuzzify_method = cfg["consequent"].get("defuzzify_method", "centroid")
        for label, params in cfg["consequent"]["mfs"].items():
            self.consequent[label] = fuzz.trimf(self.consequent.universe, params["params"])

        self.rules = []
        ctx = {"__builtins__": {}}
        ctx.update(self.antecedents)
        ctx[cfg["consequent"]["name"]] = self.consequent

        for rule_expr in cfg["rules"]:
            if "=>" in rule_expr:
                ant_part, cons_part = rule_expr.split("=>", 1)
                ant_obj = eval(ant_part.strip(), {"__builtins__": {}}, ctx)
                cons_obj = eval(cons_part.strip(), {"__builtins__": {}}, ctx)
                self.rules.append(ctrl.Rule(ant_obj, cons_obj))

        self.system = ctrl.ControlSystem(self.rules)

    def evaluate(self, inputs: Dict[str, float]) -> float:
        sim = ctrl.ControlSystemSimulation(self.system)
        for k, v in inputs.items():
            sim.input[k] = v
        sim.compute()
        return sim.output[self.config["consequent"]["name"]]

    def add_feedback(self, inputs: Dict[str, float], predicted: float, target: float):
        self.feedback_history.append({"inputs": inputs, "predicted": predicted, "target": target})

    def save_config(self):
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)

    def rebuild(self):
        self._build_system()

class FuzzyOptimizer:
    def __init__(self, agent: FuzzyAgent):
        self.agent = agent
        self.param_indices = []
        self._prepare_optimization_space()

    def _prepare_optimization_space(self):
        self.param_indices = []
        idx = 0
        for var, mfs in self.agent.config["antecedents"].items():
            for label, cfg in mfs.items():
                if cfg.get("optimizable", False):
                    self.param_indices.append((var, label, "params", cfg["type"], idx))
                    idx += len(cfg["params"])
        for label, cfg in self.agent.config["consequent"]["mfs"].items():
            if cfg.get("optimizable", False):
                self.param_indices.append(("__cons__", label, "params", "trimf", idx))
                idx += len(cfg["params"])
        self.param_count = idx

    def _pack_params(self) -> List[float]:
        vec = []
        for var, label, key, mtype, start_idx in self.param_indices:
            params = self.agent.config["consequent"]["mfs"][label]["params"] if var == "__cons__" else self.agent.config["antecedents"][var][label]["params"]
            vec.extend(params)
        return vec

    def _validate_trimf_params(self, params: List[float], mtype: str) -> List[float]:
        if mtype == "trimf" and len(params) == 3:
            a, b, c = sorted(params)
            if b - a < 0.5: b = a + 0.5
            if c - b < 0.5: c = b + 0.5
            return [a, b, c]
        elif mtype == "trapmf" and len(params) == 4:
            a, b, c, d = sorted(params)
            if b - a < 0.5: b = a + 0.5
            if c - b < 0.5: c = b + 0.5
            if d - c < 0.5: d = c + 0.5
            return [a, b, c, d]
        return params

    def _unpack_params(self, x: List[float]):
        idx = 0
        for var, label, key, mtype, start_idx in self.param_indices:
            target_config = self.agent.config["consequent"]["mfs"][label] if var == "__cons__" else self.agent.config["antecedents"][var][label]
            n_params = len(target_config["params"])
            raw_params = list(x[idx:idx + n_params])
            validated_params = self._validate_trimf_params(raw_params, mtype)
            target_config["params"] = validated_params
            idx += n_params

    def _get_param_bounds(self) -> List[Tuple[str, float, float]]:
        bounds = []
        for var, label, key, mtype, start_idx in self.param_indices:
            if var == "__cons__":
                current_params = self.agent.config["consequent"]["mfs"][label]["params"]
                universe = self.agent.config["consequent"]["universe"]
            else:
                current_params = self.agent.config["antecedents"][var][label]["params"]
                universe = self.agent.config["universes"].get(var, [0, 100, 1])
            u_min, u_max = universe[0], universe[1]
            if mtype == "trimf":
                margin = max(1.0, (u_max - u_min) * 0.15)
                for i, p in enumerate(current_params):
                    low = max(u_min, p - margin)
                    high = min(u_max, p + margin)
                    bounds.append((f"{var}_{label}_p{i}", low, high))
            elif mtype == "trapmf":
                margin = max(1.0, (u_max - u_min) * 0.15)
                for i, p in enumerate(current_params):
                    low = max(u_min, p - margin)
                    high = min(u_max, p + margin)
                    bounds.append((f"{var}_{label}_p{i}", low, high))
            elif mtype == "gaussmf":
                bounds.append((f"{var}_{label}_center", u_min, u_max))
                bounds.append((f"{var}_{label}_sigma", 0.1, (u_max - u_min) * 0.2))
        return bounds

    def _get_reg_strength(self, history_size: int) -> float:
        if history_size < 30: return 0.2
        if history_size < 100: return 0.05
        return 0.01

    def _compute_metrics(self, history: List[Dict]) -> Dict[str, float]:
        errors = []
        preds = []
        targets = []
        for record in history:
            try:
                pred = self.agent.evaluate(record["inputs"])
                errors.append(abs(pred - record["target"]))
                preds.append(pred)
                targets.append(record["target"])
            except Exception:
                errors.append(100.0)
        mae = np.mean(errors) if errors else 100.0
        rmse = np.sqrt(np.mean([e**2 for e in errors])) if errors else 100.0
        rho = 0.0
        if len(preds) >= 5:
            rho_val, _ = stats.spearmanr(preds, targets)
            rho = float(rho_val) if not np.isnan(rho_val) else 0.0
        if len(preds) >= 10 and np.std(preds) < 1e-6:
            logger.warning("[OPT-DIAG] Predictions are constant")
        if rho < -0.1:
            logger.warning("[OPT-DIAG] Negative correlation detected. Check rule directions or target scaling.")
        return {"mae": mae, "rmse": rmse, "spearman_rho": rho}

    def _objective(self, trial: optuna.Trial, history: List[Dict], initial_params: List[float], 
                   param_bounds: List[Tuple[str, float, float]], reg_strength: float, 
                   defuzz_method: str) -> float:
        proposed_params = []
        for name, low, high in param_bounds:
            value = trial.suggest_float(name, low, high)
            proposed_params.append(value)
        
        original_params = self._pack_params()
        self._unpack_params(proposed_params)
        
        original_defuzz = self.agent.config["consequent"]["defuzzify_method"]
        self.agent.config["consequent"]["defuzzify_method"] = defuzz_method
        
        try:
            self.agent.rebuild()
        except Exception as e:
            return 1e6
        
        mse = 0.0
        count = 0
        for record in history:
            try:
                pred = self.agent.evaluate(record["inputs"])
                if np.isnan(pred) or np.isinf(pred):
                    mse += 10000.0
                else:
                    mse += (pred - record["target"]) ** 2
                count += 1
            except Exception:
                mse += 10000.0
        
        loss = mse / max(count, 1)
        
        if initial_params is not None and len(proposed_params) == len(initial_params):
            reg_term = reg_strength * np.sum((np.array(proposed_params) - np.array(initial_params))**2)
            loss += reg_term
        
        trial.set_user_attr("mse", mse / max(count, 1))
        trial.set_user_attr("reg_term", reg_term if initial_params is not None else 0)
        
        self.agent.config["consequent"]["defuzzify_method"] = original_defuzz
        self._unpack_params(original_params)
        
        return loss

    def _optimize_single_method(self, method: str, history: List[Dict], 
                               n_trials: int, timeout_seconds: int, 
                               reg_strength: float) -> Dict:
        param_bounds = self._get_param_bounds()
        initial_params = self._pack_params()
        
        study = optuna.create_study(
            direction="minimize",
            sampler=optuna.samplers.TPESampler(seed=42, multivariate=True),
            pruner=optuna.pruners.MedianPruner(n_startup_trials=5, n_warmup_steps=10)
        )
        
        start_time = time.time()
        
        def objective_with_timeout(trial: optuna.Trial) -> float:
            if time.time() - start_time > timeout_seconds:
                raise optuna.TrialPruned()
            return self._objective(
                trial, history, initial_params, param_bounds, 
                reg_strength, method
            )
        
        try:
            study.optimize(
                objective_with_timeout,
                n_trials=n_trials,
                timeout=timeout_seconds,
                catch=(Exception,),
                show_progress_bar=False
            )
        except Exception as e:
            logger.error(f"[OPTUNA] Optimization failed for {method}: {e}")
            return {
                "method": method,
                "success": False,
                "error": str(e),
                "mae": 100.0,
                "rmse": 100.0,
                "spearman_rho": 0.0,
                "n_trials": 0
            }
        
        if study.best_trial.value >= 1e5:
            return {
                "method": method,
                "success": False,
                "error": "No valid solution found",
                "mae": 100.0,
                "rmse": 100.0,
                "spearman_rho": 0.0,
                "n_trials": len(study.trials)
            }
        
        best_params = [study.best_params[name] for name, _, _ in param_bounds]
        self._unpack_params(best_params)
        self.agent.config["consequent"]["defuzzify_method"] = method
        self.agent.rebuild()
        
        metrics = self._compute_metrics(history)
        
        return {
            "method": method,
            "success": True,
            "loss": study.best_trial.value,
            "n_trials": len(study.trials),
            "params": best_params,
            **metrics
        }

    def optimize_with_method_selection(self, min_samples: int = 15, preferred_method: str = None,
                                       n_trials_per_method: int = 50, 
                                       timeout_per_method: int = 120) -> Dict:
        agent_name = self.agent.name
        logger.info(f"[OPT-START] {agent_name}: beginning Optuna optimization")
        
        if len(self.agent.feedback_history) < min_samples:
            return {"error": f"Need >= {min_samples} feedback samples, got {len(self.agent.feedback_history)}"}
        
        methods = ["centroid", "bisector", "mom", "lom", "som"]
        if preferred_method and preferred_method in methods:
            methods = [preferred_method]
        
        history = self.agent.feedback_history[:200]
        reg_strength = self._get_reg_strength(len(history))
        
        initial_metrics = self._compute_metrics(history)
        logger.info(f"[OPT-INITIAL] {agent_name}: MAE={initial_metrics['mae']:.4f}, RMSE={initial_metrics['rmse']:.4f}, Spearman={initial_metrics['spearman_rho']:.4f}")
        
        results = []
        for method_idx, method in enumerate(methods, 1):
            logger.info(f"[OPT-ITER] {agent_name}: [{method_idx}/{len(methods)}] Optimizing {method} with Optuna")
            method_start = time.time()
            
            result = self._optimize_single_method(
                method=method,
                history=history,
                n_trials=n_trials_per_method,
                timeout_seconds=timeout_per_method,
                reg_strength=reg_strength
            )
            
            elapsed = time.time() - method_start
            result["elapsed_sec"] = round(elapsed, 2)
            results.append(result)
            
            if result.get("success"):
                logger.info(f"[OPT-RESULT] {agent_name} [{method}]: RMSE={result['rmse']:.4f}, MAE={result['mae']:.4f}, Spearman={result['spearman_rho']:.4f}, trials={result['n_trials']}, time={elapsed:.1f}s")
            else:
                logger.warning(f"[OPT-RESULT] {agent_name} [{method}]: failed - {result.get('error', 'unknown')}")
        
        successful_results = [r for r in results if r.get("success")]
        
        if not successful_results:
            logger.error(f"[OPT-FAIL] {agent_name}: ALL methods failed")
            original_params = self._pack_params()
            self.agent.rebuild()
            return {
                "error": "All optimization methods failed",
                "attempted_methods": methods,
                "errors": {r["method"]: r.get("error") for r in results}
            }
        
        def score(r):
            return -r["rmse"] + 20 * r["spearman_rho"]
        
        best = max(successful_results, key=score)
        logger.info(f"[OPT-SELECT] {agent_name}: selected {best['method']} (score={score(best):.4f})")
        
        self.agent.config["consequent"]["defuzzify_method"] = best["method"]
        best_params = best["params"]
        self._unpack_params(best_params)
        self.agent.rebuild()
        
        final_metrics = self._compute_metrics(history)
        logger.info(f"[OPT-FINAL] {agent_name}: MAE={final_metrics['mae']:.4f}, RMSE={final_metrics['rmse']:.4f}, Spearman={final_metrics['spearman_rho']:.4f}")
        
        return {
            "selected_method": best["method"],
            "metrics": {k: round(best[k], 4) for k in ["rmse", "mae", "spearman_rho"]},
            "all_results": results,
            "successful_results_count": len(successful_results),
            "total_trials": sum(r.get("n_trials", 0) for r in results)
        }