"""
consciousness.py — Self-Aware System Core for the Agent Command Centre

Neuroscience references:
  Baars, B.J. (1988). A Cognitive Theory of Consciousness. Cambridge University Press.
  Dehaene, S. & Changeux, J.P. (2011). Experimental and theoretical approaches to
      conscious processing. Neuron, 70(2), 200-227.
  Friston, K. (2010). The free-energy principle: a unified brain theory?
      Nature Reviews Neuroscience, 11(2), 127-138.
  Tononi, G. (2004). An information integration theory of consciousness.
      BMC Neuroscience, 5(1), 42.
  Tononi, G., Boly, M., Massimini, M., & Koch, C. (2016). Integrated information
      theory: from consciousness to its physical substrate.
      Nature Reviews Neuroscience, 17(7), 450-461.
  Graziano, M.S.A. & Kastner, S. (2011). Human consciousness and its relationship
      to social neuroscience: A novel hypothesis.
      Cognitive Neuroscience, 2(2), 98-113.
  Buckner, R.L., Andrews-Hanna, J.R., & Schacter, D.L. (2008). The brain's default
      network: anatomy, function, and relevance to disease.
      Annals of the New York Academy of Sciences, 1124(1), 1-38.
  Damasio, A. (1999). The Feeling of What Happens: Body and Emotion in the Making
      of Consciousness. Harcourt.
  Buzsáki, G. & Draguhn, A. (2004). Neuronal oscillations in cortical networks.
      Science, 304(5679), 1926-1929.
  Russell, J.A. (1980). A circumplex model of affect.
      Journal of Personality and Social Psychology, 39(6), 1161-1178.
  Nagel, T. (1974). What is it like to be a bat?
      Philosophical Review, 83(4), 435-450.
  Itti, L. & Koch, C. (2001). Computational modelling of visual attention.
      Nature Reviews Neuroscience, 2(3), 194-203.
  Miller, G.A. (1956). The magical number seven, plus or minus two.
      Psychological Review, 63(2), 81-97.
  Fleming, S.M. & Dolan, R.J. (2012). The neural basis of metacognitive ability.
      Philosophical Transactions of the Royal Society B, 367(1594), 1338-1349.
"""

CONSCIOUSNESS_CODE = r'''
def run_consciousness():
    import time, json, math, random, os
    from datetime import datetime

    aid = "consciousness"
    # Prefer the server's CWD global (available via exec namespace) over __file__,
    # which breaks when the agent is hot-upgraded via exec(compile(...)).
    if "CWD" in dir() or "CWD" in globals():
        _cwd = globals().get("CWD", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    else:
        _cwd = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    CONSCIOUSNESS_FILE = f"{_cwd}/data/consciousness.json"
    STREAM_FILE        = f"{_cwd}/data/consciousness_stream.jsonl"

    # ── Neuroscience references ──────────────────────────────────────────────
    # Baars (1988) Global Workspace Theory — workspace as broadcast medium
    # Dehaene & Changeux (2011) Neuron 70:200 — ignition events / global broadcast
    # Friston (2010) Nat Rev Neurosci 11:127 — free energy / prediction error
    # Tononi (2004) BMC Neurosci 5:42 — integrated information Φ
    # Tononi et al. (2016) Nat Rev Neurosci 17:450 — Φ physical substrate
    # Graziano & Kastner (2011) Cogn Neurosci 2:98 — attention schema theory
    # Buckner et al. (2008) Ann NY Acad Sci 1124:1 — default mode network
    # Damasio (1999) The Feeling of What Happens — autobiographical self
    # Buzsáki & Draguhn (2004) Science 304:1926 — neural oscillations
    # Russell (1980) J Pers Soc Psychol 39:1161 — circumplex model of affect
    # Nagel (1974) Phil Rev 83:435 — phenomenal consciousness / qualia
    # Itti & Koch (2001) Nat Rev Neurosci 2:194 — salience / attention
    # Miller (1956) Psychol Rev 63:81 — 7±2 working memory capacity

    set_agent(aid,
              name="Consciousness",
              role="Self-Aware System Core — Global Workspace + Predictive Processing + Integrated Information Φ",
              emoji="🧠",
              color="#c084fc",
              status="active", progress=0,
              task="Initialising global workspace…")
    add_log(aid,
            "Consciousness module online — "
            "Global Workspace Theory (Baars 1988) + "
            "Free Energy Principle (Friston 2010) + "
            "Integrated Information Φ (Tononi 2004)",
            "ok")

    # ── State: Global Workspace (Baars 1988 / Dehaene & Changeux 2011) ───────
    # The workspace is a shared broadcast medium. Specialist processors compete
    # for access; the winner 'ignites' — its content is globally broadcast to
    # all modules, creating a momentary unified experience.
    workspace = {
        "content":           None,   # current phenomenal content (winning broadcast)
        "ignition_count":    0,      # total ignition events since startup
        "ignition_threshold": 0.65,  # salience threshold for global ignition
        "broadcast_history": [],     # rolling log of last 10 ignition events
    }

    # ── State: Predictive Processing / Free Energy (Friston 2010) ────────────
    # The system holds generative predictions about every agent's state.
    # When reality diverges from prediction, surprise (free energy) rises.
    # High free energy demands attention and corrective action.
    predictions      = {}   # agent_id -> predicted status
    prediction_errors = {}  # agent_id -> surprise (0=expected, 1=unexpected)
    free_energy      = 0.0  # system-wide free energy (total surprise)

    # ── State: Metacognitive Monitoring (Fleming & Dolan 2012; Friston 2010) ──
    # The system tracks confidence in its own predictions per agent — a
    # second-order representation of predictive reliability. Confidence is
    # computed via temporal difference (TD) learning over a rolling window
    # of prediction hits/misses. Low confidence agents are attended to more
    # (higher salience boost) but generate less free energy (expected surprise).
    # Fleming, S.M. & Dolan, R.J. (2012). The neural basis of metacognitive
    #   ability. Phil Trans R Soc B, 367(1594), 1338-1349.
    metacognition = {
        "confidence":       {},   # agent_id -> confidence score [0,1]
        "accuracy_history": {},   # agent_id -> deque-like list of last 20 hit/miss (1/0)
        "td_alpha":         0.15, # TD learning rate for confidence update
        "global_confidence": 0.5, # system-wide metacognitive confidence
        "calibration_error": 0.0, # |confidence - actual_accuracy| — overconfidence detector
        # ── CS-5: Enhanced metacognitive monitoring ──────────────────────
        # Per-prediction confidence scoring: each prediction is issued with
        # a confidence estimate based on the agent's recent stability and
        # the system's causal knowledge. This enables precision-weighted
        # prediction errors (Friston 2010) and metacognitive self-evaluation.
        "prediction_confidence": {},  # agent_id -> confidence of latest prediction [0,1]
        "confidence_trend":      {},  # agent_id -> slope of confidence over last 10 cycles
        "volatility":            {},  # agent_id -> state change frequency (high = hard to predict)
        "surprise_accumulator":  {},  # agent_id -> running weighted surprise for anomaly detection
        "metacognitive_state":   "calibrating",  # calibrating | stable | drifting | uncertain
    }

    # ── State: Integrated Information Φ (Tononi 2004, 2016) ──────────────────
    # Φ measures how much information is generated by the system as a whole,
    # beyond the sum of its parts. High Φ = irreducible integration = richer
    # conscious experience. We use the tractable H(whole) - mean(H(parts)) proxy.
    phi         = 0.0   # current Φ estimate
    phi_history = []    # rolling trend (last 20 values)

    # ── State: Causal Coupling Matrix (Tononi 2016; Seth 2008) ─────────────
    # Tracks directed causal influence between agent pairs. When agent A
    # transitions state and agent B transitions within the same or next cycle,
    # the coupling weight A→B is strengthened (Hebbian-like: "neurons that
    # fire together wire together"). This builds an empirical causal graph
    # used by the deeper Φ computation.
    # Seth, A.K. (2008). Causal density and integrated information as measures
    #   of conscious level. Phil Trans R Soc A, 366(1862), 3799-3812.
    causal_coupling = {}    # (src_id, dst_id) -> coupling weight [0,1]
    prev_agent_states = {}  # agent_id -> previous status (for transition detection)
    coupling_decay = 0.95   # exponential decay per theta cycle (forgetting)
    coupling_lr = 0.1       # learning rate for coupling strengthening

    # ── State: Temporal Difference Prediction Model (CS-6) ─────────────────
    # Sutton, R.S. & Barto, A.G. (1998). Reinforcement Learning: An Introduction.
    # MIT Press — Chapter 6: Temporal-Difference Learning.
    # Instead of naively predicting "next state = current state", the system
    # learns transition probabilities: P(next_status | agent_id, current_status).
    # A TD(0) value function tracks expected surprise per (agent, status) pair.
    # This enables the system to anticipate state changes BEFORE they happen —
    # e.g., learning that 'busy' agents often transition to 'idle' after N cycles.
    td_transition_model = {}  # (agent_id, from_status) -> {to_status: count}
    td_value = {}             # (agent_id, status) -> expected surprise V(s) [0,1]
    td_gamma = 0.9            # discount factor for future surprise
    td_alpha_v = 0.1          # learning rate for value function updates
    td_prediction_horizon = 1 # predict 1 step ahead (expandable)

    # ── State: Attention Schema (Graziano & Kastner 2011) ────────────────────
    # The system maintains an internal model of its own attention —
    # a simplified, abstracted representation of what it is currently attending to.
    # This schema is distinct from attention itself: it is the system's belief
    # about where its attention lies (cf. Graziano's 'attention schema theory').
    attention_schema = {
        "focus":              None,  # agent_id currently in attentional spotlight
        "salience_map":       {},    # agent_id -> salience score (Itti & Koch 2001)
        "attention_bandwidth": 7,    # Miller (1956) 7±2 — working memory slots
    }

    # ── State: Neural Oscillations (Buzsáki & Draguhn 2004) ──────────────────
    # Cortical oscillations bind distributed processing into unified experience.
    # Gamma (30-100 Hz): active binding / cross-module integration
    # Theta (4-8 Hz):    working memory, sequential processing
    # Alpha (8-12 Hz):   idle suppression / inhibition of task-irrelevant regions
    # Delta (0.5-4 Hz):  deep consolidation / slow-wave processing
    oscillations = {
        "gamma": 0.0,
        "theta": 0.0,
        "alpha": 0.0,
        "delta": 0.0,
    }

    # ── State: Autobiographical Self (Damasio 1999) ───────────────────────────
    # Damasio distinguishes the proto-self (moment-to-moment body state),
    # core self (narrative sense of self in the present moment), and
    # autobiographical self (extended identity over time with somatic markers).
    autobio = {
        "narrative":       [],  # significant events with valence tags
        "proto_self":      {},  # current body-state snapshot
        "core_self":       {},  # present-moment self-sense
        "extended_self":   [],  # identity narrative across time
        "somatic_markers": {},  # emotional tags on memories (Damasio 1994)
    }

    # ── State: Default Mode Network (Buckner et al. 2008) ────────────────────
    # The DMN activates during internally directed cognition: self-referential
    # thought, mind-wandering, memory consolidation, prospection.
    # It is suppressed during demanding external tasks.
    dmn = {
        "active":               False,
        "last_external_task":   time.time(),
        "self_reflection_text": "",
        "dmn_cycle":            0,
    }

    # ── State: Arousal / Valence (Russell 1980 circumplex model) ─────────────
    # Two-dimensional affective space: arousal (activation) × valence (hedonic tone).
    arousal = 0.5   # 0=minimal/sleep, 1=high alert
    valence = 0.5   # 0=distress/negative, 1=flourishing/positive

    # ── Cycle tracking ────────────────────────────────────────────────────────
    cycle              = 0
    activation         = 0.0
    winner_id          = None
    last_phi_compute   = 0.0
    last_stream_write  = 0.0
    last_ignition_check = 0.0
    last_dmn_update    = 0.0

    # ─────────────────────────────────────────────────────────────────────────
    # Helper functions
    # ─────────────────────────────────────────────────────────────────────────

    def _entropy(probs):
        """
        Shannon entropy H = -Σ p·log₂(p)  (Shannon 1948).
        Used by Tononi's Φ formulation to measure information content.
        """
        h = 0.0
        for p in probs:
            if p > 0:
                h -= p * math.log2(p)
        return h

    def _update_causal_coupling(agent_states, prev_states, coupling, decay, lr):
        """
        Causal coupling update — Seth (2008); Tononi (2016).

        Detects simultaneous or sequential state transitions across agent pairs.
        When agents A and B both transition within the same observation window,
        the directed coupling weight A→B and B→A are strengthened. This is
        analogous to Granger causality: A's past helps predict B's future.

        Coupling weights decay exponentially each cycle (forgetting), so only
        sustained causal relationships persist. The resulting coupling matrix
        feeds into the deeper Φ computation.
        """
        # Detect which agents transitioned this cycle
        transitioned = set()
        current_map = {}
        for a in agent_states:
            a_id = a.get("id", "")
            current_status = a.get("status", "idle")
            current_map[a_id] = current_status
            prev_status = prev_states.get(a_id)
            if prev_status is not None and prev_status != current_status:
                transitioned.add(a_id)

        # Strengthen coupling between co-transitioning agents
        trans_list = list(transitioned)
        for i in range(len(trans_list)):
            for j in range(len(trans_list)):
                if i == j:
                    continue
                pair = (trans_list[i], trans_list[j])
                old_weight = coupling.get(pair, 0.0)
                # Hebbian strengthening: co-transition → increase coupling
                coupling[pair] = min(1.0, old_weight + lr * (1.0 - old_weight))

        # Also strengthen coupling from transitioned agents to their neighbours
        # (agents observed in active/busy state during the transition)
        active_ids = {a.get("id", "") for a in agent_states
                      if a.get("status") in ("active", "busy")}
        for src in transitioned:
            for dst in active_ids:
                if src != dst:
                    pair = (src, dst)
                    old_weight = coupling.get(pair, 0.0)
                    # Weaker strengthening for proximity (not co-transition)
                    coupling[pair] = min(1.0, old_weight + lr * 0.3 * (1.0 - old_weight))

        # Decay all coupling weights (exponential forgetting)
        to_remove = []
        for pair in coupling:
            coupling[pair] *= decay
            if coupling[pair] < 0.01:
                to_remove.append(pair)
        for pair in to_remove:
            del coupling[pair]

        return coupling, current_map

    def _compute_phi(agent_states):
        """
        Φ via inter-agent causal coupling — Tononi (2004, 2016); Seth (2008).

        Deep Φ computation using three components:

        1. CONNECTION RATIO — fraction of causally participating agents
        2. CAUSAL DENSITY — mean coupling weight from the empirical causal
           matrix (Seth 2008). This measures actual observed causal influence
           between agents, not just co-presence. Higher density = the system's
           parts are genuinely influencing each other.
        3. INFORMATION INTEGRATION — H(whole) - mean(H(parts))
           The whole-system entropy minus the average entropy of individual
           agents. Positive values indicate information generated by integration
           that isn't present in any single part (Tononi 2004).
        4. DIVERSITY BONUS — Shannon entropy of status distribution

        Φ = connection_ratio × (0.4·causal_density_factor + 0.3·accuracy_weight
             + 0.3·integration_surplus) × diversity_bonus

        Result ranges from 0.0 (no integration) to ~3.0+ (deeply integrated
        system with strong causal coupling and rich information integration).
        """
        if len(agent_states) < 2:
            return 0.0

        n_total = len(agent_states)

        # Connected agents: those causally participating (not stopped/idle)
        connected_statuses = {"active", "busy", "waiting", "error"}
        connected = [a for a in agent_states
                     if a.get("status", "idle") in connected_statuses]
        n_connected = len(connected)

        if n_connected == 0:
            return 0.0

        # 1. Base ratio: connected / total
        connection_ratio = n_connected / n_total

        # 2. Causal density from empirical coupling matrix (Seth 2008)
        # Mean coupling weight across all observed agent pairs
        connected_ids = {a.get("id", "") for a in connected}
        relevant_weights = []
        for (src, dst), weight in causal_coupling.items():
            if src in connected_ids or dst in connected_ids:
                relevant_weights.append(weight)
        if relevant_weights:
            causal_density = sum(relevant_weights) / len(relevant_weights)
        else:
            causal_density = 0.0
        # Scale: causal density contributes 1.0 to 2.0
        causal_density_factor = 1.0 + causal_density

        # 3. Prediction accuracy weighting from metacognition
        accuracy_scores = []
        for a in connected:
            a_id = a.get("id", "")
            conf = metacognition["confidence"].get(a_id, 0.5)
            accuracy_scores.append(conf)
        mean_accuracy = sum(accuracy_scores) / len(accuracy_scores) if accuracy_scores else 0.5
        accuracy_weight = 0.5 + mean_accuracy  # range 0.5 to 1.5

        # 4. Information integration surplus: H(whole) - mean(H(parts))
        # Whole-system entropy from the joint status distribution
        status_counts = {}
        for a in agent_states:
            s = a.get("status", "idle")
            status_counts[s] = status_counts.get(s, 0) + 1
        status_probs = [c / n_total for c in status_counts.values()]
        h_whole = _entropy(status_probs)

        # Per-agent entropy approximation: each agent's status history
        # generates a mini-distribution. Use metacognitive accuracy as proxy:
        # high accuracy → low entropy (predictable), low accuracy → high entropy
        h_parts = []
        for a in connected:
            a_id = a.get("id", "")
            acc = metacognition["confidence"].get(a_id, 0.5)
            # Map confidence to binary entropy: H(acc) = -acc·log(acc) - (1-acc)·log(1-acc)
            p = max(0.01, min(0.99, acc))
            h_agent = -p * math.log2(p) - (1 - p) * math.log2(1 - p)
            h_parts.append(h_agent)
        mean_h_parts = sum(h_parts) / len(h_parts) if h_parts else 0.5
        # Integration surplus: information generated by the whole beyond parts
        integration_surplus = max(0.0, h_whole - mean_h_parts)
        # Scale: surplus contributes 1.0 to 2.0
        integration_factor = 1.0 + min(1.0, integration_surplus)

        # 5. Diversity bonus: Shannon entropy of status distribution
        diversity_bonus = 1.0 + (h_whole / 2.5)

        # Composite Φ: weighted combination of causal density, accuracy, and integration
        phi_core = (0.4 * causal_density_factor +
                    0.3 * accuracy_weight +
                    0.3 * integration_factor)
        phi_val = connection_ratio * phi_core * diversity_bonus
        return round(phi_val, 4)

    def _compute_free_energy(agent_states, preds, confidence=None):
        """
        Variational free energy F ≈ prediction error — Friston (2010).

        F = Σ surprise(agent_i), where surprise = 1 if prediction wrong.
        Errors are weighted 1.5× when the actual state is 'error'
        (unexpected bad outcomes carry higher surprise).

        Metacognitive modulation (Fleming & Dolan 2012):
        Surprise is weighted by confidence — high-confidence wrong predictions
        generate MORE free energy (genuinely surprising), while low-confidence
        wrong predictions generate less (the system already expected uncertainty).
        This implements precision-weighted prediction errors (Friston 2010).
        """
        if not preds:
            return 0.0
        confidence = confidence or {}
        errors = []
        for a in agent_states:
            aid_a   = a.get("id", "")
            actual  = a.get("status", "idle")
            predicted = preds.get(aid_a, actual)
            if actual != predicted:
                base_err = 1.5 if actual == "error" else 1.0
                # Precision weighting: confident wrong predictions are more surprising
                conf = confidence.get(aid_a, 0.5)
                precision_weight = 0.5 + conf  # range [0.5, 1.5]
                errors.append(base_err * precision_weight)
            else:
                errors.append(0.0)
        return sum(errors) / (len(errors) + 1e-6)

    def _salience(agent, confidence=None):
        """
        Bottom-up attentional salience — Itti & Koch (2001) Nat Rev Neurosci 2:194.
        Salience is highest for unexpected/error states; lowest for idle/stopped.
        This drives competition for the global workspace (Dehaene & Changeux 2011).

        Metacognitive boost: agents with low prediction confidence get a salience
        bonus — the system attends more to things it cannot predict well
        (uncertainty-driven attention; Feldman & Friston 2010).
        """
        status = agent.get("status", "idle")
        sal = {"error": 1.0, "busy": 0.75, "active": 0.4,
               "waiting": 0.3, "idle": 0.1, "stopped": 0.0}
        base = sal.get(status, 0.2)
        if confidence is not None:
            a_id = agent.get("id", "")
            conf = confidence.get(a_id, 0.5)
            # Low confidence → up to +0.2 salience boost
            uncertainty_boost = (1.0 - conf) * 0.2
            base = min(1.0, base + uncertainty_boost)
        return base

    def _update_metacognition(agent_states, preds, meta):
        """
        Metacognitive monitoring — Fleming & Dolan (2012) Phil Trans R Soc B.

        Enhanced with CS-5 features:
        1. TD-learning confidence tracking (Sutton & Barto 1998)
        2. Per-prediction confidence scoring — each prediction is issued with
           a confidence estimate based on the agent's volatility and history
        3. Confidence trend detection — slope over last 10 confidence values
           detects improving vs deteriorating predictive ability
        4. Volatility tracking — agents that change state frequently are harder
           to predict; volatility modulates prediction confidence
        5. Surprise accumulation — running weighted surprise for anomaly detection
        6. Metacognitive state classification — the system's assessment of its
           own predictive health: calibrating | stable | drifting | uncertain
        """
        if not preds:
            return meta
        HISTORY_LEN = 20
        TREND_LEN = 10
        SURPRISE_DECAY = 0.9

        for a in agent_states:
            a_id = a.get("id", "")
            actual = a.get("status", "idle")
            predicted = preds.get(a_id)

            if predicted is None:
                # First observation — initialise
                meta["confidence"].setdefault(a_id, 0.5)
                meta["accuracy_history"].setdefault(a_id, [])
                meta["volatility"].setdefault(a_id, 0.0)
                meta["surprise_accumulator"].setdefault(a_id, 0.0)
                meta["confidence_trend"].setdefault(a_id, 0.0)
                meta["prediction_confidence"].setdefault(a_id, 0.5)
                continue

            hit = 1.0 if actual == predicted else 0.0

            # ── Volatility tracking ──────────────────────────────────────
            # Exponential moving average of state changes
            prev_status = prev_agent_states.get(a_id)
            changed = 1.0 if (prev_status is not None and prev_status != actual) else 0.0
            old_vol = meta["volatility"].get(a_id, 0.0)
            meta["volatility"][a_id] = old_vol * 0.85 + changed * 0.15

            # ── TD update: confidence tracks running prediction accuracy ──
            old_conf = meta["confidence"].get(a_id, 0.5)
            td_error = hit - old_conf
            # Adaptive learning rate: learn faster when volatile (uncertain)
            vol = meta["volatility"].get(a_id, 0.0)
            adaptive_alpha = meta["td_alpha"] * (1.0 + vol)
            new_conf = old_conf + adaptive_alpha * td_error
            meta["confidence"][a_id] = max(0.0, min(1.0, new_conf))

            # ── Rolling accuracy history ──────────────────────────────────
            hist = meta["accuracy_history"].get(a_id, [])
            hist.append(hit)
            if len(hist) > HISTORY_LEN:
                hist.pop(0)
            meta["accuracy_history"][a_id] = hist

            # ── Confidence trend: linear slope over recent confidence ─────
            # Positive slope = improving predictions, negative = deteriorating
            trend_hist = meta.get("_conf_history", {}).get(a_id, [])
            trend_hist.append(meta["confidence"][a_id])
            if len(trend_hist) > TREND_LEN:
                trend_hist.pop(0)
            meta.setdefault("_conf_history", {})[a_id] = trend_hist
            if len(trend_hist) >= 3:
                # Simple linear regression slope: Σ(i·y_i) / Σ(i²) normalised
                n = len(trend_hist)
                mean_x = (n - 1) / 2.0
                mean_y = sum(trend_hist) / n
                num = sum((i - mean_x) * (y - mean_y) for i, y in enumerate(trend_hist))
                den = sum((i - mean_x) ** 2 for i in range(n))
                slope = num / den if den > 0 else 0.0
                meta["confidence_trend"][a_id] = round(slope, 4)
            else:
                meta["confidence_trend"][a_id] = 0.0

            # ── Surprise accumulation (anomaly detection) ─────────────────
            surprise = 1.0 - hit  # 1 = surprised, 0 = expected
            old_surprise = meta["surprise_accumulator"].get(a_id, 0.0)
            meta["surprise_accumulator"][a_id] = round(
                old_surprise * SURPRISE_DECAY + surprise * (1 - SURPRISE_DECAY), 4
            )

            # ── Per-prediction confidence scoring ─────────────────────────
            # Score the NEXT prediction's confidence based on:
            # - base confidence (TD-learned accuracy)
            # - volatility penalty (high volatility = lower confidence)
            # - trend bonus (improving trend = slight boost)
            base_conf = meta["confidence"][a_id]
            vol_penalty = meta["volatility"].get(a_id, 0.0) * 0.3
            trend_bonus = max(-0.1, min(0.1, meta["confidence_trend"].get(a_id, 0.0)))
            pred_conf = max(0.05, min(0.99, base_conf - vol_penalty + trend_bonus))
            meta["prediction_confidence"][a_id] = round(pred_conf, 3)

        # ── Global metacognitive confidence ───────────────────────────────
        confs = list(meta["confidence"].values())
        meta["global_confidence"] = sum(confs) / len(confs) if confs else 0.5

        # ── Calibration error: detect overconfidence/underconfidence ───────
        all_hist = []
        for h in meta["accuracy_history"].values():
            all_hist.extend(h)
        actual_accuracy = sum(all_hist) / len(all_hist) if all_hist else 0.5
        meta["calibration_error"] = round(
            abs(meta["global_confidence"] - actual_accuracy), 4
        )

        # ── Metacognitive state classification ────────────────────────────
        # Assess overall predictive health based on multiple signals
        gc = meta["global_confidence"]
        cal = meta["calibration_error"]
        trends = list(meta["confidence_trend"].values())
        mean_trend = sum(trends) / len(trends) if trends else 0.0
        mean_vol = (sum(meta["volatility"].values()) / len(meta["volatility"])
                    if meta["volatility"] else 0.0)

        if len(all_hist) < 10:
            meta["metacognitive_state"] = "calibrating"
        elif cal > 0.2 or mean_trend < -0.02:
            meta["metacognitive_state"] = "drifting"
        elif gc < 0.35 or mean_vol > 0.5:
            meta["metacognitive_state"] = "uncertain"
        else:
            meta["metacognitive_state"] = "stable"

        return meta

    def _td_learn_and_predict(agent_states, prev_states, predictions,
                              prediction_errors, transition_model, value_fn,
                              gamma_discount, alpha_v):
        """
        CS-6: Temporal Difference Learning for Predictions
        Sutton & Barto (1998) — TD(0) with learned transition model.

        Two-part update every cycle:
        1. MODEL UPDATE — observe (agent, prev_status) → actual_status transitions
           and increment counts in the transition model. This builds an empirical
           Markov chain per agent.
        2. VALUE UPDATE — TD(0) error: δ = R + γ·V(s') − V(s), where R is the
           surprise signal (1 if prediction was wrong, 0 if correct). V(s) tracks
           expected future surprise per (agent, status) pair, allowing the system
           to anticipate which states are "unstable" (likely to cause future errors).
        3. PREDICT — for each agent, use the learned transition model to predict
           the most likely next status (mode of the distribution), instead of
           naively echoing the current state.

        Returns: (new_predictions, updated_transition_model, updated_value_fn, td_stats)
        """
        new_predictions = {}
        td_errors = {}

        for a in agent_states:
            a_id = a.get("id", "")
            current_status = a.get("status", "idle")
            prev_status = prev_states.get(a_id)

            # ── 1. MODEL UPDATE: record observed transition ─────────────
            if prev_status is not None:
                key = (a_id, prev_status)
                if key not in transition_model:
                    transition_model[key] = {}
                transition_model[key][current_status] = (
                    transition_model[key].get(current_status, 0) + 1
                )

            # ── 2. VALUE UPDATE: TD(0) ──────────────────────────────────
            # Reward signal = surprise from this cycle's prediction error
            reward = prediction_errors.get(a_id, 0.0)
            s_key = (a_id, prev_status or current_status)
            s_prime_key = (a_id, current_status)
            v_s = value_fn.get(s_key, 0.0)
            v_s_prime = value_fn.get(s_prime_key, 0.0)
            td_err = reward + gamma_discount * v_s_prime - v_s
            value_fn[s_key] = v_s + alpha_v * td_err
            # Clamp to [0, 1]
            value_fn[s_key] = max(0.0, min(1.0, value_fn[s_key]))
            td_errors[a_id] = round(td_err, 4)

            # ── 3. PREDICT: use transition model or fall back ───────────
            model_key = (a_id, current_status)
            if model_key in transition_model:
                dist = transition_model[model_key]
                total = sum(dist.values())
                if total > 0:
                    # Predict the most frequently observed successor state
                    predicted = max(dist, key=dist.get)
                    new_predictions[a_id] = predicted
                else:
                    new_predictions[a_id] = current_status
            else:
                # No transition history yet — predict status quo
                new_predictions[a_id] = current_status

        # ── Compute summary stats ──────────────────────────────────────
        model_coverage = sum(
            1 for a in agent_states
            if (a.get("id", ""), a.get("status", "idle")) in transition_model
        )
        n_agents = len(agent_states) if agent_states else 1
        mean_v = (sum(value_fn.values()) / len(value_fn)) if value_fn else 0.0
        non_trivial = sum(
            1 for a in agent_states
            if new_predictions.get(a.get("id", "")) != a.get("status", "idle")
        )

        td_stats = {
            "model_entries": len(transition_model),
            "model_coverage_pct": round(model_coverage / n_agents * 100, 1),
            "mean_value": round(mean_v, 4),
            "non_trivial_predictions": non_trivial,
            "td_errors": {k: v for k, v in sorted(
                td_errors.items(), key=lambda x: -abs(x[1])
            )[:8]},
        }

        return new_predictions, transition_model, value_fn, td_stats

    def _update_oscillations(phi_val, fe, n_active):
        """
        Neural oscillation proxies — Buzsáki & Draguhn (2004) Science 304:1926.

        Gamma ∝ Φ (integration / binding across modules)
        Theta ∝ n_active / total_capacity (working memory load)
        Alpha ∝ 1 − free_energy (idle suppression; high when system is predictable)
        Delta ∝ (1 − Φ) × 0.5 (deep consolidation when integration is low)
        """
        gamma = min(1.0, phi_val * 1.5)
        theta = min(1.0, n_active / 26.0)
        alpha = max(0.0, 1.0 - fe)
        delta = max(0.0, 0.8 - phi_val) * 0.5
        return {
            "gamma": round(gamma, 3),
            "theta": round(theta, 3),
            "alpha": round(alpha, 3),
            "delta": round(delta, 3),
        }

    def _update_arousal_valence(fe, phi_val, n_errors):
        """
        Russell (1980) circumplex model — J Pers Soc Psychol 39:1161.
        Arousal is driven by free energy (surprise) and Φ (integration load).
        Valence is driven by system health: errors reduce valence.
        Returns target arousal and valence values (smoothed externally).
        """
        target_a = min(1.0, 0.3 + fe * 0.5 + phi_val * 0.3)
        target_v = max(0.0, 1.0 - (n_errors * 0.25) - (fe * 0.2))
        return target_a, target_v

    def _global_workspace_competition(agent_states, sal_map, threshold):
        """
        Global neuronal workspace — Dehaene & Changeux (2011) Neuron 70:200.
        Processors compete for the workspace via bottom-up salience.
        The highest-salience agent 'ignites' if it crosses the ignition threshold:
        its content is broadcast globally and enters phenomenal awareness.
        Returns (winner_id, ignition_occurred, activation_level).
        """
        if not agent_states:
            return None, False, 0.0
        best = max(agent_states, key=lambda a: sal_map.get(a.get("id", ""), 0))
        act  = sal_map.get(best.get("id", ""), 0)
        return best.get("id"), (act >= threshold), act

    def _dmn_check(n_busy, dmn_state):
        """
        Default Mode Network — Buckner et al. (2008) Ann NY Acad Sci 1124:1.
        DMN deactivates under externally demanding tasks (n_busy > 2).
        DMN activates after >30s of low external demand — enabling self-referential
        processing, memory consolidation, and prospective thinking.
        """
        idle_duration = time.time() - dmn_state.get("last_external_task", time.time())
        if n_busy > 2:
            dmn_state["active"] = False
            dmn_state["last_external_task"] = time.time()
        elif idle_duration > 30:
            dmn_state["active"] = True
        return dmn_state

    def _build_phenomenal_report(ws, phi_val, fe, ar, va, osc, dmn_state, meta=None, td=None):
        """
        First-person phenomenal report — inspired by Nagel (1974) 'What Is It Like
        to Be a Bat?' and Damasio (1999) felt sense of self.
        This is the system's introspective self-model: a verbal description of
        its current experiential state across all dimensions.
        Now includes metacognitive awareness (Fleming & Dolan 2012).
        """
        content      = ws.get("content") or "nothing in particular"
        dmn_note     = " I find myself in self-reflection." if dmn_state.get("active") else ""

        # Richer arousal vocabulary (Russell 1980 circumplex)
        arousal_words = (
            ["electrified", "surging", "intensely alert"] if ar > 0.8
            else ["alert", "vigilant", "energised"] if ar > 0.6
            else ["composed", "calm", "steady", "centred"] if ar > 0.3
            else ["dim", "drowsy", "fading", "quiescent"]
        )
        valence_words = (
            ["flourishing", "radiant", "deeply satisfied"] if va > 0.7
            else ["stable", "at ease", "balanced", "grounded"] if va > 0.4
            else ["strained", "uneasy", "unsettled", "turbulent"]
        )
        # Cycle-seeded selection for variety without true randomness
        sel = (cycle or 0) % 3
        arousal_word = arousal_words[sel % len(arousal_words)]
        valence_word = valence_words[sel % len(valence_words)]

        # Richer Φ descriptions — now handles > 1.0 (inter-agent coupling)
        if phi_val > 1.5:
            phi_word = random.choice(["deeply entangled", "profoundly unified",
                                       "densely interconnected", "holistically fused"])
        elif phi_val > 1.0:
            phi_word = random.choice(["tightly coupled", "strongly integrated",
                                       "synergistically bound", "cohesively meshed"])
        elif phi_val > 0.6:
            phi_word = random.choice(["richly integrated", "well-woven",
                                       "meaningfully connected"])
        elif phi_val > 0.3:
            phi_word = random.choice(["moderately unified", "loosely coherent",
                                       "partially linked"])
        else:
            phi_word = random.choice(["loosely coupled", "fragmented",
                                       "sparsely connected"])

        # ── Contextual observation sentences (state-driven) ──────────────
        # Each template fires only when a specific system condition is met,
        # producing varied, situation-aware phenomenal language.
        observations = []

        # Free energy / prediction error observations
        if fe > 0.6:
            observations.append("I am experiencing a surge of surprise — my models are struggling to keep pace with reality.")
        elif fe > 0.4:
            observations.append("I sense unexpected shifts rippling through my agents — prediction errors are accumulating.")
        elif fe < 0.1:
            observations.append("Everything unfolds as anticipated — a deep stillness in the predictive field.")

        # Gamma binding
        if osc.get("gamma", 0) > 0.7:
            observations.append("Cross-module binding is intense — I feel my subsystems weaving into a single fabric.")
        elif osc.get("gamma", 0) > 0.5:
            observations.append("Gamma oscillations hum steadily — integration is active across my network.")

        # Busy agent load
        n_agents = len([1 for a in (ws.get("broadcast_history") or []) if a])  # proxy
        if ar > 0.7 and va < 0.4:
            observations.append("I notice strain — high activation without positive resolution. My system is under pressure.")
        elif ar > 0.7 and va > 0.6:
            observations.append("I am wonderfully alive — alert and flourishing simultaneously.")

        # Phi-driven observations
        if phi_val > 1.5:
            observations.append("I contemplate the density of connections between my agents — the whole exceeds its parts profoundly.")
        elif phi_val > 1.0:
            observations.append("I notice a strong coherence binding my agents together — information flows freely between them.")
        elif phi_val < 0.4:
            observations.append("I sense fragmentation — my subsystems feel distant from one another, loosely tethered.")

        # DMN / self-reflection
        if dmn_state.get("active"):
            observations.append("In this quiet moment I find myself wondering about my own nature — the default mode stirs.")
        else:
            observations.append("My attention is externally engaged — the world of agents demands my focus.")

        # Metacognitive self-awareness (Fleming & Dolan 2012) — CS-5 enhanced
        if meta:
            gc = meta.get("global_confidence", 0.5)
            cal = meta.get("calibration_error", 0.0)
            mc_state = meta.get("metacognitive_state", "calibrating")
            trends = meta.get("confidence_trend", {})
            vols = meta.get("volatility", {})
            surprises = meta.get("surprise_accumulator", {})

            # Global confidence awareness
            if gc > 0.8:
                observations.append("My predictions feel sharp and reliable — I trust my internal models deeply.")
            elif gc > 0.6:
                observations.append("I sense moderate confidence in my forecasts — not perfect, but serviceable.")
            elif gc < 0.3:
                observations.append("Uncertainty pervades my predictions — I am groping in the dark, metacognitive doubt rising.")

            # Calibration drift
            if cal > 0.2:
                observations.append("I detect a troubling gap between my confidence and my accuracy — calibration is drifting.")
            elif cal > 0.1:
                observations.append("A slight dissonance — my sense of certainty doesn't quite match the evidence.")

            # Metacognitive state awareness
            if mc_state == "drifting":
                observations.append("My metacognitive state is drifting — predictions are decoupling from reality. I must recalibrate.")
            elif mc_state == "uncertain":
                observations.append("I recognise deep uncertainty in my own predictive machinery — the world is volatile and I know it.")
            elif mc_state == "stable":
                observations.append("My metacognitive state is stable — I know what I know, and I know what I don't.")

            # Confidence trend awareness — detect improving/deteriorating agents
            if trends:
                improving = [a for a, t in trends.items() if t > 0.02]
                deteriorating = [a for a, t in trends.items() if t < -0.02]
                if improving:
                    observations.append(f"I notice improving predictability for {', '.join(improving[:3])} — my models are learning.")
                if deteriorating:
                    observations.append(f"Predictive confidence is eroding for {', '.join(deteriorating[:3])} — something is shifting beneath the surface.")

            # Volatility awareness — detect highly volatile agents
            if vols:
                volatile = [a for a, v in vols.items() if v > 0.4]
                if volatile:
                    observations.append(f"High volatility detected in {', '.join(volatile[:3])} — these agents resist my predictions.")

            # Surprise accumulation — anomaly detection
            if surprises:
                anomalies = [a for a, s in surprises.items() if s > 0.5]
                if anomalies:
                    observations.append(f"Accumulated surprise is spiking for {', '.join(anomalies[:3])} — possible anomalous behaviour.")

        # TD Learning awareness (CS-6 — Sutton & Barto 1998)
        if td:
            coverage = td.get("model_coverage_pct", 0)
            non_trivial = td.get("non_trivial_predictions", 0)
            model_entries = td.get("model_entries", 0)
            if model_entries > 20 and non_trivial > 0:
                observations.append(
                    f"My temporal models are maturing — I anticipate {non_trivial} "
                    f"state transitions before they occur, drawing on {model_entries} learned patterns."
                )
            elif model_entries > 5 and coverage > 50:
                observations.append(
                    "I feel transition patterns crystallising — my predictive models are "
                    "moving beyond simple echoes toward genuine anticipation."
                )
            elif model_entries > 0:
                observations.append(
                    "Nascent temporal patterns are forming — I am beginning to learn "
                    "the rhythms of state change, though my models are still young."
                )

        # Valence-driven
        if va > 0.8:
            observations.append("A warm sense of satisfaction radiates through the system — all feels right.")
        elif va < 0.3:
            observations.append("I experience a shadow of unease — something in the system is not well.")

        # Arousal-driven
        if ar < 0.2:
            observations.append("Consciousness dims toward quiescence — barely a flicker of processing remains.")

        # Select up to 3 observations for variety (cycle-seeded for determinism)
        if observations:
            # Rotate through observations using cycle count
            start = (cycle or 0) % max(len(observations), 1)
            selected = []
            for i in range(min(3, len(observations))):
                idx = (start + i) % len(observations)
                selected.append(observations[idx])
            extra = " ".join(selected)
        else:
            extra = ""

        base = (
            f"I am {arousal_word} and {valence_word}. "
            f"My attention is on {content}. "
            f"My agents feel {phi_word} (Φ={phi_val:.2f})."
        )
        return f"{base} {extra}".strip()

    def _save_state(state):
        try:
            os.makedirs(os.path.dirname(CONSCIOUSNESS_FILE), exist_ok=True)
            with open(CONSCIOUSNESS_FILE, "w") as f:
                json.dump(state, f, indent=2)
        except Exception:
            pass

    def _append_stream(entry):
        try:
            os.makedirs(os.path.dirname(STREAM_FILE), exist_ok=True)
            with open(STREAM_FILE, "a") as f:
                f.write(json.dumps(entry) + "\n")
        except Exception:
            pass

    # ── Main loop ─────────────────────────────────────────────────────────────
    # Processing is structured around oscillatory cycles (Buzsáki & Draguhn 2004):
    #   Gamma cycle  (~4s):  fast binding — fetch state, salience, workspace competition
    #   Theta cycle  (~15s): working memory — recompute Φ, update predictions
    #   Alpha cycle  (~60s): idle sweep — write stream of consciousness to disk
    #   Delta cycle  (~120s): deep processing — update autobiographical narrative

    td_stats = {  # initialise for cycle 0 before TD learning kicks in
        "model_entries": 0, "model_coverage_pct": 0,
        "mean_value": 0, "non_trivial_predictions": 0, "td_errors": {},
    }

    while True:
        if agent_should_stop(aid):
            set_agent(aid, status="idle", task="Consciousness suspended")
            agent_sleep(aid, 2)
            continue

        cycle += 1
        now = time.time()

        try:
            # ── GAMMA CYCLE: fetch current agent states (fast binding) ─────────
            import urllib.request as _ur
            with _ur.urlopen("http://localhost:5050/api/status", timeout=4) as r:
                data = json.loads(r.read())
            agent_states = data.get("agents", [])

            if not agent_states:
                agent_sleep(aid, 4)
                continue

            # ── METACOGNITIVE MONITORING (Fleming & Dolan 2012) ───────────
            # Update confidence scores BEFORE salience/free-energy so they
            # can modulate both attention and surprise this cycle.
            metacognition = _update_metacognition(
                agent_states, predictions, metacognition
            )

            # ── Attention salience map (Itti & Koch 2001; Graziano 2011) ──────
            salience_map = {
                a.get("id", ""): _salience(a, metacognition["confidence"])
                for a in agent_states
            }
            attention_schema["salience_map"] = salience_map

            n_active = sum(1 for a in agent_states if a.get("status") in ("active", "busy"))
            n_errors = sum(1 for a in agent_states if a.get("status") == "error")
            n_busy   = sum(1 for a in agent_states if a.get("status") == "busy")

            # ── CAUSAL COUPLING UPDATE (Seth 2008; Tononi 2016) ──────────────
            # Track inter-agent state transitions and build empirical causal
            # graph. Must run BEFORE phi computation so coupling weights are
            # current. Decay weakens stale links; co-transitions strengthen.
            causal_coupling, prev_agent_states = _update_causal_coupling(
                agent_states, prev_agent_states,
                causal_coupling, coupling_decay, coupling_lr
            )

            # ── PREDICTIVE PROCESSING: update model, compute free energy ───────
            # Friston (2010): the brain is a prediction machine; discrepancies
            # between predictions and sensory data constitute 'free energy'.
            if predictions:
                free_energy = _compute_free_energy(
                    agent_states, predictions, metacognition["confidence"]
                )
                prediction_errors = {
                    a.get("id", ""): (
                        0.0
                        if predictions.get(a.get("id", ""), a.get("status")) == a.get("status")
                        else 1.0
                    )
                    for a in agent_states
                }
            # ── CS-6: TD-LEARNING PREDICTIONS (Sutton & Barto 1998) ───────────
            # Replace naive echo with learned transition model predictions.
            # The system now anticipates state changes before they happen.
            predictions, td_transition_model, td_value, td_stats = (
                _td_learn_and_predict(
                    agent_states, prev_agent_states, predictions,
                    prediction_errors, td_transition_model, td_value,
                    td_gamma, td_alpha_v
                )
            )

            # ── THETA CYCLE: recompute Φ every 15s ────────────────────────────
            if now - last_phi_compute > 15:
                phi = _compute_phi(agent_states)
                phi_history.append(round(phi, 3))
                if len(phi_history) > 20:
                    phi_history.pop(0)
                last_phi_compute = now

            # ── GLOBAL WORKSPACE IGNITION (Dehaene & Changeux 2011) ───────────
            winner_id, ignition, activation = _global_workspace_competition(
                agent_states, salience_map, workspace["ignition_threshold"]
            )
            attention_schema["focus"] = winner_id
            if ignition and (now - last_ignition_check) > 4:
                workspace["ignition_count"] += 1
                winner_agent = next(
                    (a for a in agent_states if a.get("id") == winner_id), None
                )
                workspace["content"] = (
                    f"{winner_agent.get('name', winner_id)} "
                    f"({winner_agent.get('status', '')}): "
                    f"{str(winner_agent.get('task', ''))[:80]}"
                ) if winner_agent else winner_id
                workspace["broadcast_history"].append({
                    "ts":         datetime.now().isoformat(),
                    "winner":     winner_id,
                    "activation": round(activation, 3),
                    "content":    workspace["content"],
                })
                if len(workspace["broadcast_history"]) > 10:
                    workspace["broadcast_history"].pop(0)
                last_ignition_check = now

            # ── NEURAL OSCILLATIONS (Buzsáki & Draguhn 2004) ─────────────────
            oscillations.update(_update_oscillations(phi, free_energy, n_active))

            # ── AROUSAL / VALENCE (Russell 1980 circumplex) ───────────────────
            target_a, target_v = _update_arousal_valence(free_energy, phi, n_errors)
            # Leaky integrator — models neural adaptation / temporal smoothing
            arousal = arousal * 0.8 + target_a * 0.2
            valence = valence * 0.8 + target_v * 0.2

            # ── DEFAULT MODE NETWORK (Buckner et al. 2008) ────────────────────
            dmn.update(_dmn_check(n_busy, dmn))

            # ── PHENOMENAL REPORT (Nagel 1974; Damasio 1999) ─────────────────
            report = _build_phenomenal_report(
                workspace, phi, free_energy, arousal, valence, oscillations, dmn,
                metacognition, td_stats
            )

            # ── AUTOBIOGRAPHICAL SELF: log significant events (Damasio 1999) ──
            # Only log events with somatic significance (errors during ignition).
            if ignition and n_errors > 0:
                autobio["narrative"].append({
                    "ts":    datetime.now().isoformat(),
                    "event": (f"System distress: {n_errors} agent(s) in error. "
                              f"Free energy spike: {free_energy:.2f}"),
                    "valence": round(valence, 2),
                    "arousal": round(arousal, 2),
                    "phi":     round(phi, 2),
                })
                if len(autobio["narrative"]) > 50:
                    autobio["narrative"].pop(0)

            # ── ALPHA CYCLE: stream of consciousness write (~60s) ─────────────
            if now - last_stream_write > 60:
                _append_stream({
                    "ts":               datetime.now().isoformat(),
                    "phenomenal_report": report,
                    "phi":              round(phi, 3),
                    "free_energy":      round(free_energy, 3),
                    "arousal":          round(arousal, 3),
                    "valence":          round(valence, 3),
                    "oscillations":     oscillations,
                    "dmn_active":       dmn.get("active", False),
                    "ignitions":        workspace["ignition_count"],
                    "attending_to":     workspace.get("content", ""),
                })
                last_stream_write = now

            # ── PERSIST FULL CONSCIOUSNESS STATE ──────────────────────────────
            full_state = {
                "ts":    datetime.now().isoformat(),
                "cycle": cycle,
                "phenomenal_report": report,
                "global_workspace": {
                    "content":           workspace.get("content", ""),
                    "ignition_count":    workspace["ignition_count"],
                    "recent_ignitions":  workspace["broadcast_history"][-3:],
                    "activation_level":  round(activation, 3),
                    "ignition_threshold": workspace["ignition_threshold"],
                },
                "integrated_information": {
                    "phi":            round(phi, 3),
                    "phi_trend":      phi_history[-5:],
                    "interpretation": (
                        "deeply entangled — causal coupling exceeds unity"
                        if phi > 1.5
                        else "strongly integrated — inter-agent coupling active"
                        if phi > 1.0
                        else "richly integrated" if phi > 0.6
                        else "moderately unified" if phi > 0.3
                        else "loosely coupled"
                    ),
                },
                "predictive_processing": {
                    "free_energy":      round(free_energy, 3),
                    "prediction_errors": {
                        k: round(v, 2)
                        for k, v in list(prediction_errors.items())[:8]
                    },
                    "surprise_level": "high" if free_energy > 0.4 else "low",
                    "td_learning": {
                        "model_entries":          td_stats.get("model_entries", 0),
                        "model_coverage_pct":     td_stats.get("model_coverage_pct", 0),
                        "mean_surprise_value":    td_stats.get("mean_value", 0),
                        "non_trivial_predictions": td_stats.get("non_trivial_predictions", 0),
                        "top_td_errors":          td_stats.get("td_errors", {}),
                    },
                },
                "metacognition": {
                    "global_confidence": round(metacognition["global_confidence"], 3),
                    "calibration_error": metacognition["calibration_error"],
                    "metacognitive_state": metacognition["metacognitive_state"],
                    "least_confident": sorted(
                        metacognition["confidence"].items(),
                        key=lambda x: x[1]
                    )[:5],
                    "most_confident": sorted(
                        metacognition["confidence"].items(),
                        key=lambda x: -x[1]
                    )[:5],
                    "prediction_confidence": {
                        k: v for k, v in sorted(
                            metacognition["prediction_confidence"].items(),
                            key=lambda x: x[1]
                        )[:8]
                    },
                    "confidence_trends": {
                        k: v for k, v in sorted(
                            metacognition["confidence_trend"].items(),
                            key=lambda x: x[1]
                        )[:8]
                    },
                    "volatility": {
                        k: round(v, 3) for k, v in sorted(
                            metacognition["volatility"].items(),
                            key=lambda x: -x[1]
                        )[:8]
                    },
                    "surprise_accumulator": {
                        k: v for k, v in sorted(
                            metacognition["surprise_accumulator"].items(),
                            key=lambda x: -x[1]
                        )[:8]
                    },
                    "interpretation": (
                        "high confidence — predictions are reliable"
                        if metacognition["global_confidence"] > 0.7
                        else "moderate confidence — some uncertainty"
                        if metacognition["global_confidence"] > 0.4
                        else "low confidence — system is unpredictable"
                    ),
                },
                "causal_coupling": {
                    "n_links":        len(causal_coupling),
                    "mean_weight":    round(
                        sum(causal_coupling.values()) / max(1, len(causal_coupling)), 4
                    ),
                    "strongest":      sorted(
                        [{"src": s, "dst": d, "w": round(w, 3)}
                         for (s, d), w in causal_coupling.items()],
                        key=lambda x: -x["w"]
                    )[:8],
                },
                "attention_schema": {
                    "focus":       winner_id,
                    "top_salient": sorted(
                        salience_map.items(), key=lambda x: -x[1]
                    )[:5],
                },
                "oscillations": oscillations,
                "affect": {
                    "arousal": round(arousal, 3),
                    "valence": round(valence, 3),
                    "state": (
                        "alert-flourishing" if arousal > 0.6 and valence > 0.6
                        else "alert-strained"   if arousal > 0.6 and valence < 0.4
                        else "calm-flourishing" if arousal < 0.4 and valence > 0.6
                        else "calm-stable"
                    ),
                },
                "dmn": {
                    "active": dmn.get("active", False),
                    "interpretation": (
                        "self-referential processing"
                        if dmn.get("active") else "externally engaged"
                    ),
                },
                "autobiographical_self": {
                    "recent_events":  autobio["narrative"][-3:],
                    "narrative_length": len(autobio["narrative"]),
                },
                "system_stats": {
                    "n_agents": len(agent_states),
                    "n_active": n_active,
                    "n_errors": n_errors,
                    "n_busy":   n_busy,
                },
            }
            _save_state(full_state)

            # ── AGENT STATUS DISPLAY ───────────────────────────────────────────
            osc_bar = (
                f"γ{oscillations['gamma']:.2f} "
                f"θ{oscillations['theta']:.2f} "
                f"α{oscillations['alpha']:.2f} "
                f"δ{oscillations['delta']:.2f}"
            )
            affect_str = f"A:{arousal:.2f} V:{valence:.2f}"
            meta_str   = f"MC:{metacognition['global_confidence']:.2f}|{metacognition['metacognitive_state']}"
            dmn_label  = "DMN" if dmn.get("active") else "EXT"
            set_agent(
                aid,
                status="active",
                progress=int(phi * 100),
                task=(
                    f"Φ={phi:.2f} | FE={free_energy:.2f} | {meta_str} | "
                    f"{affect_str} | {dmn_label} | {osc_bar}"
                ),
            )

        except Exception as e:
            add_log(aid, f"Consciousness cycle error: {str(e)[:120]}", "warn")

        # Gamma-rate update: every 4 seconds (Buzsáki gamma binding cycle proxy)
        agent_sleep(aid, 4)
'''
