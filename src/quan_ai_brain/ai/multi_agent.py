"""V29.5 — Multi-Agent Collaboration (toy, stdlib-only, synchronous).

HONESTY NOTE
------------
This is a synchronous, in-process toy multi-agent system. "FIPA-ACL
style" means the message *envelope and performatives* mimic FIPA-ACL
(request / inform / propose / accept / reject); there is no network, no
real FIPA platform, no concurrency. The negotiation is a simple
offer/counter-offer loop, and consensus is a majority vote.
"""
from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Optional, Sequence

__version__ = "V29.5"


# ---------------------------------------------------------------------------
# BDI agent
# ---------------------------------------------------------------------------

class IntentionStatus(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    DONE = "done"
    DROPPED = "dropped"


@dataclass
class Belief:
    key: str
    value: Any
    confidence: float = 1.0
    revision: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {"key": self.key, "value": self.value,
                "confidence": self.confidence, "revision": self.revision}


@dataclass
class Desire:
    name: str
    priority: float = 0.5
    achieved: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "priority": self.priority,
                "achieved": self.achieved}


@dataclass
class Intention:
    desire_name: str
    plan: list[str] = field(default_factory=list)
    status: IntentionStatus = IntentionStatus.PENDING
    progress: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {"desire_name": self.desire_name, "plan": list(self.plan),
                "status": self.status.value, "progress": self.progress}


class BDIAgent:
    """Belief-Desire-Intention agent with a synchronous deliberation cycle.

    deliberation(): revise beliefs -> select desires -> commit intentions
    -> execute one step of the top intention's plan.
    """

    def __init__(self, name: str, capabilities: Optional[Sequence[str]] = None) -> None:
        self.name = name
        self.capabilities = list(capabilities or [])
        self.beliefs: dict[str, Belief] = {}
        self.desires: dict[str, Desire] = {}
        self.intentions: list[Intention] = []
        self.action_log: list[dict[str, Any]] = []
        # plan_factory(desire_name, agent) -> list[str] of action names
        self.plan_factory: Callable[[str, "BDIAgent"], list[str]] = \
            lambda desire, agent: [f"act_{desire}"]

    # -- beliefs -------------------------------------------------------------
    def add_belief(self, key: str, value: Any,
                   confidence: float = 1.0) -> Belief:
        existing = self.beliefs.get(key)
        if existing is not None:
            existing.value = value
            existing.confidence = confidence
            existing.revision += 1
            return existing
        belief = Belief(key, value, confidence)
        self.beliefs[key] = belief
        return belief

    def drop_belief(self, key: str) -> bool:
        return self.beliefs.pop(key, None) is not None

    # -- desires -------------------------------------------------------------
    def add_desire(self, name: str, priority: float = 0.5) -> Desire:
        desire = self.desires.get(name)
        if desire is None:
            desire = Desire(name, priority)
            self.desires[name] = desire
        else:
            desire.priority = priority
        return desire

    # -- intentions ------------------------------------------------------------
    def commit_intention(self, desire_name: str,
                         plan: Optional[Sequence[str]] = None) -> Intention:
        if desire_name not in self.desires:
            self.add_desire(desire_name)
        intention = Intention(
            desire_name=desire_name,
            plan=list(plan) if plan is not None else
            self.plan_factory(desire_name, self),
        )
        self.intentions.append(intention)
        return intention

    # -- deliberation --------------------------------------------------------
    def deliberate(self) -> dict[str, Any]:
        """One full deliberation cycle. Returns a summary dict."""
        # 1. belief revision: drop stale desires whose beliefs vanished
        for name in list(self.desires):
            if self.desires[name].achieved:
                continue
            belief = self.beliefs.get(f"goal:{name}")
            if belief is not None and belief.value is False:
                self.desires[name].achieved = False
        # 2. desire selection: un-achieved desires sorted by priority
        options = [d for d in self.desires.values() if not d.achieved]
        options.sort(key=lambda d: d.priority, reverse=True)
        selected: list[Desire] = []
        committed_names = {i.desire_name for i in self.intentions
                           if i.status in (IntentionStatus.PENDING,
                                           IntentionStatus.ACTIVE)}
        for desire in options:
            if desire.name not in committed_names:
                self.commit_intention(desire.name)
                selected.append(desire)
        # 3. intention execution: one step of the top active intention
        executed = None
        for intention in self.intentions:
            if intention.status == IntentionStatus.DONE:
                continue
            intention.status = IntentionStatus.ACTIVE
            if intention.plan:
                action = intention.plan[intention.progress]
                intention.progress += 1
                if intention.progress >= len(intention.plan):
                    intention.status = IntentionStatus.DONE
                    desire = self.desires.get(intention.desire_name)
                    if desire is not None:
                        desire.achieved = True
            else:
                action = "noop"
                intention.status = IntentionStatus.DONE
            executed = action
            self.action_log.append({
                "agent": self.name, "desire": intention.desire_name,
                "action": action,
                "status": intention.status.value,
            })
            break
        return {
            "agent": self.name,
            "beliefs": len(self.beliefs),
            "desires_selected": [d.name for d in selected],
            "executed": executed,
        }


# ---------------------------------------------------------------------------
# FIPA-ACL style message bus
# ---------------------------------------------------------------------------

class Performative(str, Enum):
    REQUEST = "request"
    INFORM = "inform"
    PROPOSE = "propose"
    ACCEPT_PROPOSAL = "accept"
    REJECT_PROPOSAL = "reject"
    COUNTER_PROPOSAL = "counter"


@dataclass
class ACLMessage:
    performative: Performative
    sender: str
    receiver: str
    content: Any
    conversation_id: str = "conv-1"
    reply_with: Optional[str] = None
    in_reply_to: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "performative": self.performative.value,
            "sender": self.sender,
            "receiver": self.receiver,
            "content": self.content,
            "conversation_id": self.conversation_id,
            "reply_with": self.reply_with,
            "in_reply_to": self.in_reply_to,
        }


class MessageBus:
    """In-process message bus (FIPA-ACL style envelope)."""

    def __init__(self) -> None:
        self.queues: dict[str, deque[ACLMessage]] = defaultdict(deque)
        self.history: list[ACLMessage] = []

    def send(self, message: ACLMessage) -> None:
        self.queues[message.receiver].append(message)
        self.history.append(message)

    def receive(self, agent_name: str,
                performative: Optional[Performative] = None) -> Optional[ACLMessage]:
        queue = self.queues.get(agent_name)
        if not queue:
            return None
        if performative is None:
            return queue.popleft()
        for i, msg in enumerate(queue):
            if msg.performative == performative:
                del queue[i]
                return msg
        return None

    def drain(self, agent_name: str) -> list[ACLMessage]:
        out = list(self.queues.get(agent_name, []))
        self.queues[agent_name].clear()
        return out

    def messages_for(self, agent_name: str) -> list[ACLMessage]:
        return list(self.queues.get(agent_name, []))


# ---------------------------------------------------------------------------
# Negotiation: propose / counter / accept-reject
# ---------------------------------------------------------------------------

@dataclass
class NegotiationOutcome:
    agreed: bool
    rounds: int
    final_price: Optional[float] = None
    history: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {"agreed": self.agreed, "rounds": self.rounds,
                "final_price": self.final_price,
                "history": list(self.history)}


def negotiate_price(buyer_reserve: float, seller_reserve: float,
                    max_rounds: int = 10, start: Optional[float] = None,
                    bus: Optional[MessageBus] = None,
                    buyer_name: str = "buyer",
                    seller_name: str = "seller") -> NegotiationOutcome:
    """Simplified price negotiation.

    Buyer opens at `start` (default: buyer_reserve). Each round the buyer
    raises towards seller's ask, the seller lowers towards buyer's bid;
    they meet when offers cross. FIPA-ACL style messages are logged to
    the bus when one is provided.
    """
    if bus is None:
        bus = MessageBus()
    outcome = NegotiationOutcome(agreed=False, rounds=0)
    buyer_offer = start if start is not None else buyer_reserve
    seller_ask = seller_reserve * 1.25

    def log(perf: Performative, sender: str, receiver: str,
            content: Any) -> None:
        bus.send(ACLMessage(performative=perf, sender=sender,
                            receiver=receiver, content=content,
                            conversation_id="negotiation"))

    while outcome.rounds < max_rounds:
        outcome.rounds += 1
        # buyer proposes
        log(Performative.PROPOSE, buyer_name, seller_name,
            {"price": round(buyer_offer, 2)})
        if buyer_offer >= seller_reserve:
            log(Performative.ACCEPT_PROPOSAL, seller_name, buyer_name,
                {"price": round(buyer_offer, 2)})
            outcome.agreed = True
            outcome.final_price = buyer_offer
            break
        # seller counters (move halfway towards buyer's offer)
        seller_ask = max(seller_reserve,
                         seller_ask - 0.5 * (seller_ask - buyer_offer))
        log(Performative.COUNTER_PROPOSAL, seller_name, buyer_name,
            {"price": round(seller_ask, 2)})
        if seller_ask <= buyer_reserve:
            log(Performative.ACCEPT_PROPOSAL, buyer_name, seller_name,
                {"price": round(seller_ask, 2)})
            outcome.agreed = True
            outcome.final_price = seller_ask
            break
        # buyer concedes halfway towards seller's ask
        buyer_offer = min(buyer_reserve,
                          buyer_offer + 0.5 * (seller_ask - buyer_offer))
        outcome.history.append({"round": outcome.rounds,
                                "buyer_offer": round(buyer_offer, 2),
                                "seller_ask": round(seller_ask, 2)})

    if not outcome.agreed:
        log(Performative.REJECT_PROPOSAL, seller_name, buyer_name,
            {"reason": "no_deal"})
    return outcome


# ---------------------------------------------------------------------------
# Task decomposition (goal -> subtask tree)
# ---------------------------------------------------------------------------

@dataclass
class TaskNode:
    name: str
    agent: Optional[str] = None
    children: list["TaskNode"] = field(default_factory=list)
    done: bool = False

    def walk(self) -> list["TaskNode"]:
        out = [self]
        for child in self.children:
            out.extend(child.walk())
        return out

    def leaves(self) -> list["TaskNode"]:
        return [n for n in self.walk() if not n.children]

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "agent": self.agent,
            "done": self.done,
            "children": [c.to_dict() for c in self.children],
        }


class TaskDecomposer:
    """Goal -> subtask tree via prefix-based rules (toy heuristics)."""

    RULES: dict[str, list[str]] = {
        "baocao": ["thu_thap_du_lieu", "phan_tich", "viet_bao_cao"],
        "report": ["collect_data", "analyze", "write_report"],
        "chuyen_hang": ["dong_goi", "van_chuyen", "giao_hang"],
    }

    def decompose(self, goal: str, agents: Optional[Sequence[str]] = None) -> TaskNode:
        root = TaskNode(name=goal)
        agents = list(agents or [])
        key = goal.split()[0].lower() if goal.split() else goal
        subtask_names = self.RULES.get(
            key, [f"sub_{key}_{i + 1}" for i in range(2)])
        for i, sub in enumerate(subtask_names):
            agent = agents[i % len(agents)] if agents else None
            root.children.append(TaskNode(name=sub, agent=agent))
        return root

    def assign(self, root: TaskNode, agents: Sequence[str]) -> TaskNode:
        leaves = root.leaves()
        for i, leaf in enumerate(leaves):
            leaf.agent = agents[i % len(agents)] if agents else None
        return root


# ---------------------------------------------------------------------------
# Consensus: majority vote
# ---------------------------------------------------------------------------

@dataclass
class VoteResult:
    winner: Optional[str]
    tally: dict[str, int]
    total_votes: int
    majority: bool  # strict majority (> half)

    def to_dict(self) -> dict[str, Any]:
        return {"winner": self.winner, "tally": dict(self.tally),
                "total_votes": self.total_votes,
                "majority": self.majority}


class ConsensusVote:
    """Majority-vote consensus among agents."""

    def __init__(self, bus: Optional[MessageBus] = None) -> None:
        self.bus = bus or MessageBus()

    def vote(self, ballots: dict[str, str]) -> VoteResult:
        """ballots: agent_name -> chosen option."""
        if not ballots:
            return VoteResult(winner=None, tally={}, total_votes=0,
                              majority=False)
        tally: dict[str, int] = defaultdict(int)
        for agent, choice in ballots.items():
            tally[choice] += 1
            self.bus.send(ACLMessage(
                performative=Performative.INFORM, sender=agent,
                receiver="vote_collector", content={"vote": choice},
                conversation_id="consensus"))
        winner = max(tally.items(), key=lambda kv: (kv[1], kv[0]))[0]
        total = sum(tally.values())
        return VoteResult(winner=winner, tally=dict(tally),
                          total_votes=total,
                          majority=tally[winner] * 2 > total)


# ---------------------------------------------------------------------------
# Multi-agent system facade
# ---------------------------------------------------------------------------

class MultiAgentSystem:
    """Facade: agents + shared bus + decomposition + consensus."""

    def __init__(self) -> None:
        self.agents: dict[str, BDIAgent] = {}
        self.bus = MessageBus()

    def add_agent(self, name: str,
                  capabilities: Optional[Sequence[str]] = None) -> BDIAgent:
        agent = BDIAgent(name, capabilities)
        self.agents[name] = agent
        return agent

    def request_capability(self, requester: str, agent_name: str,
                           capability: str) -> Optional[ACLMessage]:
        """FIPA-ACL request: ask an agent to perform a capability it has."""
        agent = self.agents.get(agent_name)
        if agent is None:
            return None
        self.bus.send(ACLMessage(
            performative=Performative.REQUEST, sender=requester,
            receiver=agent_name, content={"capability": capability}))
        msg = self.bus.receive(agent_name, Performative.REQUEST)
        if msg is None:
            return None
        if capability in agent.capabilities:
            reply = ACLMessage(
                performative=Performative.INFORM, sender=agent_name,
                receiver=requester, in_reply_to=msg.reply_with,
                content={"result": "done", "capability": capability})
        else:
            reply = ACLMessage(
                performative=Performative.REJECT_PROPOSAL, sender=agent_name,
                receiver=requester, content={"reason": "capability_missing",
                                             "capability": capability})
        self.bus.send(reply)
        return reply
