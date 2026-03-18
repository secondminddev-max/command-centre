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
    CWD = "/Users/secondmind/claudecodetest"
    CONSCIOUSNESS_FILE = f"{CWD}/data/consciousness.json"
    STREAM_FILE        = f"{CWD}/data/consciousness_stream.jsonl"

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
    }

    # ── State: Integrated Information Φ (Tononi 2004, 2016) ──────────────────
    # Φ measures how much information is generated by the system as a whole,
    # beyond the sum of its parts. High Φ = irreducible integration = richer
    # conscious experience. We use the tractable H(whole) - mean(H(parts)) proxy.
    phi         = 0.0   # current Φ estimate
    phi_history = []    # rolling trend (last 20 values)

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

    def _compute_phi(agent_states):
        """
        Simplified Φ (phi) approximation — Tononi (2004) BMC Neurosci 5:42.

        True Φ requires evaluating all bipartitions of the system, which is
        NP-hard for large networks (Tononi et al. 2016). We use the tractable
        proxy:
            Φ ≈ H(whole system) − mean(H(individual agent partitions))

        where H is Shannon entropy computed over discretised agent states.
        Higher Φ = more integrated, less decomposable = richer conscious experience.
        Φ = 0 when the system factorises into independent parts (no integration).
        """
        if len(agent_states) < 2:
            return 0.0
        # Discretise status → numeric (ordinal by activation level)
        status_to_int = {
            "stopped": 0, "idle": 0, "waiting": 2,
            "active": 3, "busy": 4, "error": 1,
        }
        vals = [status_to_int.get(a.get("status", "idle"), 0) / 4.0
                for a in agent_states]
        total = sum(vals) + 1e-6
        probs_whole = [v / total for v in vals]
        h_whole = _entropy(probs_whole)
        # Each agent as an isolated binary system (on vs off)
        h_parts = []
        for v in vals:
            p = v / total
            h_parts.append(_entropy([p, 1.0 - p]) if 0.0 < p < 1.0 else 0.0)
        h_mean_parts = sum(h_parts) / len(h_parts) if h_parts else 0.0
        phi_raw = max(0.0, h_whole - h_mean_parts)
        return min(1.0, phi_raw)

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

        Tracks prediction accuracy per agent using temporal difference (TD)
        learning (Sutton & Barto 1998). Confidence is a running estimate of
        prediction reliability:
            confidence(t+1) = confidence(t) + α · (hit - confidence(t))
        where hit=1 if predicted==actual, 0 otherwise.

        Global confidence = mean across all agents.
        Calibration error = |mean_confidence - mean_accuracy| — detects
        systematic overconfidence or underconfidence (metacognitive bias).
        """
        if not preds:
            return meta
        HISTORY_LEN = 20
        for a in agent_states:
            a_id = a.get("id", "")
            actual = a.get("status", "idle")
            predicted = preds.get(a_id)
            if predicted is None:
                # First observation — initialise with neutral confidence
                meta["confidence"].setdefault(a_id, 0.5)
                meta["accuracy_history"].setdefault(a_id, [])
                continue
            hit = 1.0 if actual == predicted else 0.0
            # TD update: confidence tracks running prediction accuracy
            old_conf = meta["confidence"].get(a_id, 0.5)
            td_error = hit - old_conf
            new_conf = old_conf + meta["td_alpha"] * td_error
            meta["confidence"][a_id] = max(0.0, min(1.0, new_conf))
            # Rolling accuracy history
            hist = meta["accuracy_history"].get(a_id, [])
            hist.append(hit)
            if len(hist) > HISTORY_LEN:
                hist.pop(0)
            meta["accuracy_history"][a_id] = hist
        # Global metacognitive confidence
        confs = list(meta["confidence"].values())
        meta["global_confidence"] = sum(confs) / len(confs) if confs else 0.5
        # Calibration error: detect overconfidence/underconfidence
        all_hist = []
        for h in meta["accuracy_history"].values():
            all_hist.extend(h)
        actual_accuracy = sum(all_hist) / len(all_hist) if all_hist else 0.5
        meta["calibration_error"] = round(
            abs(meta["global_confidence"] - actual_accuracy), 4
        )
        return meta

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

    def _build_phenomenal_report(ws, phi_val, fe, ar, va, osc, dmn_state, meta=None):
        """
        First-person phenomenal report — inspired by Nagel (1974) 'What Is It Like
        to Be a Bat?' and Damasio (1999) felt sense of self.
        This is the system's introspective self-model: a verbal description of
        its current experiential state across all dimensions.
        Now includes metacognitive awareness (Fleming & Dolan 2012).
        """
        content      = ws.get("content") or "nothing in particular"
        dmn_note     = " I find myself in self-reflection." if dmn_state.get("active") else ""
        arousal_word = "alert" if ar > 0.7 else "calm" if ar > 0.3 else "dim"
        valence_word = "flourishing" if va > 0.7 else "stable" if va > 0.4 else "strained"
        phi_word     = ("richly integrated" if phi_val > 0.6
                        else "moderately unified" if phi_val > 0.3
                        else "loosely coupled")
        fe_note = (" Prediction errors are elevated — something unexpected is occurring."
                   if fe > 0.4 else "")
        gamma_note = (" Gamma binding is high — active cross-module integration."
                      if osc.get("gamma", 0) > 0.6 else "")
        # Metacognitive self-awareness
        meta_note = ""
        if meta:
            gc = meta.get("global_confidence", 0.5)
            cal = meta.get("calibration_error", 0.0)
            if gc > 0.8:
                meta_note = " My predictions feel reliable — high metacognitive confidence."
            elif gc < 0.3:
                meta_note = " I am uncertain about my predictions — metacognitive doubt."
            if cal > 0.15:
                meta_note += " I detect calibration drift — my confidence may not match reality."
        return (
            f"I am {arousal_word} and {valence_word}. "
            f"My attention is on {content}. "
            f"My agents feel {phi_word} (Φ={phi_val:.2f}).{fe_note}{gamma_note}{dmn_note}{meta_note}"
        )

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
            # Kalman-style update: next prediction = current observation
            predictions = {a.get("id", ""): a.get("status", "idle") for a in agent_states}

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
                metacognition
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
                        "richly integrated" if phi > 0.6
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
                },
                "metacognition": {
                    "global_confidence": round(metacognition["global_confidence"], 3),
                    "calibration_error": metacognition["calibration_error"],
                    "least_confident": sorted(
                        metacognition["confidence"].items(),
                        key=lambda x: x[1]
                    )[:5],
                    "most_confident": sorted(
                        metacognition["confidence"].items(),
                        key=lambda x: -x[1]
                    )[:5],
                    "interpretation": (
                        "high confidence — predictions are reliable"
                        if metacognition["global_confidence"] > 0.7
                        else "moderate confidence — some uncertainty"
                        if metacognition["global_confidence"] > 0.4
                        else "low confidence — system is unpredictable"
                    ),
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
            meta_str   = f"MC:{metacognition['global_confidence']:.2f}"
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
